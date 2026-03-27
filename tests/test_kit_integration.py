import sys
from pathlib import Path

# Fix for Windows Unicode issues
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def test_kit_integrity():
    base_dir = Path(".agent")

    components = {
        "agents": [
            "backend-specialist.md", "debugger.md", "performance-optimizer.md",
            "test-engineer.md", "code-archaeologist.md", "documentation-writer.md"
        ],
        "skills": [
            "python-patterns", "systematic-debugging", "clean-code",
            "tdd-workflow", "api-patterns", "intelligent-routing",
            "lint-and-validate", "parallel-agents"
        ],
        "workflows": [
            "debug.md", "enhance.md", "test.md", "plan.md", "status.md"
        ],
        "rules": [
            "GEMINI.md"
        ],
        "scripts": [
            "session_manager.py"
        ]
    }

    results = []
    all_passed = True

    # Use plain text for headers to avoid encoding issues
    print("--- Verifying Antigravity Kit Integration ---\n")

    for category, items in components.items():
        print(f"--- {category.upper()} ---")
        for item in items:
            item_path = base_dir / category / item
            exists = item_path.exists()
            status = "[OK]" if exists else "[FAIL]"
            if not exists:
                all_passed = False
            print(f"{status} {item}")
        print()

    if all_passed:
        print("Integration Test: PASSED (100%)")
    else:
        print("Integration Test: FAILED (Some components missing)")
        sys.exit(1)

if __name__ == "__main__":
    test_kit_integrity()
