
import cProfile
import io
import os
import pstats
import shutil
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, PROJECT_ROOT)

import pytesseract
from PIL import Image

import src.utils.logger  # Patches logging.Logger
from src.preprocessing.ocr_reader import _ensure_dependencies, _parse_pages, load_ocr_config

DUMMY_IMAGE = "data/profiling_dummy/dummy_page.png"

def profile_tesseract(image_path, config):
    print("\n--- Profiling Tesseract OCR (PSM 3) ---")
    start = time.time()
    
    # Check if Tesseract is available
    tesseract_cmd = shutil.which("tesseract")
    if not tesseract_cmd:
        # Check standard Windows path
        win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(win_path):
            tesseract_cmd = win_path
            
    if not tesseract_cmd:
        print("Tesseract not found! Profiling skipped.")
        print("Please ensure Tesseract is installed or in your PATH.")
        return

    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    
    try:
        text = pytesseract.image_to_string(
            Image.open(image_path),
            lang="chi_sim+eng", # Or 'eng' if chinese pack missing
            config="--psm 3"
        )
        end = time.time()
        print(f"Text extracted ({len(text)} chars)")
        print(f"Time taken: {end - start:.4f}s")
    except pytesseract.TesseractError as e:
        print(f"Tesseract Error: {e}")
        # Fallback to eng 
        print("Retrying with English only...")
        text = pytesseract.image_to_string(
            Image.open(image_path),
            lang="eng",
            config="--psm 3"
        )
        print(f"Text extracted (fallback): {len(text)} chars")


def main():
    if not os.path.exists(DUMMY_IMAGE):
        print(f"Error: {DUMMY_IMAGE} not found. Run generate_dummy_data.py first.")
        return

    # cProfile
    pr = None
    if "--internal" in sys.argv:
        try:
            pr = cProfile.Profile()
            pr.enable()
        except ValueError:
            print("Warning: Could not start internal cProfile.")
            pr = None

    profile_tesseract(DUMMY_IMAGE, {})

    if pr:
        pr.disable()

        # Stats
        s = io.StringIO()
        sortby = pstats.SortKey.CUMULATIVE
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats(20)
        
        print("\n=== TOP 20 CUMULATIVE TIME (OCR) ===")
        print(s.getvalue())
        pr.dump_stats("scripts/profiling/profile_ocr.stats")
        print("Saved stats to scripts/profiling/profile_ocr.stats")
    else:
        print("\nInternal cProfile skipped. Use --internal to force it, or use external profilers.")

if __name__ == "__main__":
    main()
