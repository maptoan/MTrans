# Baseline truoc cai to workspace

Tai lieu nay ghi lai trang thai baseline de doi chieu trong qua trinh cai to workspace theo nguyen tac zero-impact.

## 1) Entrypoint va smoke check

- `python main.py --help`: PASS
- `python ocr_app/main.py --help`: FAIL (`ModuleNotFoundError: No module named 'src'`)

Ghi chu:
- Loi OCR app da ton tai o baseline, khong phai regression do cai to.
- Trong cac phase tiep theo, neu can sua de on dinh entrypoint OCR, se sua co fallback va kiem chung lai.

## 2) Runtime path contract hien tai (tu config chinh)

Nguon: `config/config.yaml`

- `input.novel_path`: `data/input/Best Loser Wins - Tom Hougaard.epub`
- `metadata.style_profile_path`: `data/metadata/Best Loser Wins - Tom Hougaard/style_profile.json`
- `metadata.glossary_path`: `data/metadata/Best Loser Wins - Tom Hougaard/glossary.csv`
- `metadata.character_relations_path`: `data/metadata/Best Loser Wins - Tom Hougaard/character_relations.csv`
- `storage.progress_path`: `data/progress/`
- `storage.cache_path`: `data/cache/`
- `output.output_path`: `data/output/`
- `output.epub_reinject.epub_output_dir`: `\"\"` (de trong -> dung `output_path`)
- `output.epub_options.cover_image_path`: `data/input/Best Loser Wins - Tom Hougaard.png`

## 3) Invariant de bao toan trong qua trinh cai to

- Khong doi contract `config/config.yaml` trong giai doan dau.
- Cac module runtime chinh phai tiep tuc doc duoc cac path tren.
- Neu doi cau truc noi bo, bat buoc co fallback tuong thich nguoc.

## 4) Muc tieu doi chieu sau moi phase

- Khong phat sinh regression so voi baseline.
- Staging an toan truoc commit/push (khong co data nhay cam/artefact lon ngoai policy).
