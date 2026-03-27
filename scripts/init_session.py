#!/usr/bin/env python3
"""
Novel Translator Session Initializer
====================================
Auto-generates session files based on workflow_orchestration.md

Usage:
    python scripts/init_session.py                    # Interactive mode
    python scripts/init_session.py --task "Task description"  # Quick mode
    python scripts/init_session.py --review           # Review mode
"""

import argparse
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"
CHECK = "[OK]"
CROSS = "[X]"

TASKS_DIR = PROJECT_ROOT / "tasks"
LESSONS_FILE = TASKS_DIR / "lessons.md"


def print_header():
    print(f"""
{BOLD}{BLUE}╔══════════════════════════════════════════════════════════════╗
║     Novel Translator Session Initializer v1.0              ║
║     Pipeline: Trifecta v7.0 | Version: v8.2                 ║
╚══════════════════════════════════════════════════════════════╝{RESET}
""")


def print_step(num, text):
    print(f"{CYAN}  [{num}]{RESET} {text}")


def check_existing_files():
    """Check what files already exist."""
    files = {}

    # Check for existing todo files
    todo_files = list(TASKS_DIR.glob("todo_*.md"))
    files["todos"] = todo_files

    # Check for lessons file
    files["lessons"] = LESSONS_FILE.exists()

    # Check for AGENTS.md
    files["agents"] = (PROJECT_ROOT / "AGENTS.md").exists()

    return files


def init_lessons():
    """Initialize lessons.md if it doesn't exist."""
    if LESSONS_FILE.exists():
        return False, "File already exists"

    template = TASKS_DIR / "lessons_template.md"
    if template.exists():
        shutil.copy(template, LESSONS_FILE)
        return True, "Created from template"

    # Create basic lessons file
    content = f"""# Lessons Learned - Novel Translator

> *Template from workflow_orchestration.md | Novel Translator v8.2*
> *Created: {datetime.now().strftime("%Y-%m-%d")}*

---

## 📌 Quick Reference Rules - Novel Translator

### Pre-Translation
- [ ] Verify glossary.csv is up-to-date
- [ ] Verify style_profile.json reflects target tone
- [ ] Check API key count vs chunk count
- [ ] Ensure input encoding is UTF-8

### During Translation
- [ ] Monitor for 429/503 errors
- [ ] Watch CJK residual count per chunk
- [ ] Track dialogue quote consistency

### Post-Translation
- [ ] ALWAYS verify no CJK characters remain
- [ ] Check glossary terms appear correctly
- [ ] Verify output length is reasonable

### Quality Thresholds
| Metric | Min Acceptable | Target |
|--------|----------------|--------|
| CJK residual | 0 | 0 |
| Dialogue match | 80% | 95%+ |
| Glossary compliance | 100% | 100% |
| Chunk success rate | 95% | 100% |

---

## 🔄 Review Checklist (Start of each session)
- [ ] Check AGENTS.md for recent updates
- [ ] Review lessons from last session
- [ ] Verify config.yaml settings
- [ ] Check for new API keys if needed

---

*Last updated: {datetime.now().strftime("%Y-%m-%d")}*
"""
    LESSONS_FILE.write_text(content, encoding="utf-8")
    return True, "Created new file"


def create_todo(project_name: Optional[str] = None, task_desc: Optional[str] = None) -> Path:
    """Create a new todo file for the session."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    if not project_name:
        project_name = input(f"{YELLOW}  Project name (e.g., HMQT, TDTTT): {RESET}").strip() or "project"

    todo_file = TASKS_DIR / f"todo_{project_name}_{timestamp}.md"

    template = TASKS_DIR / "todo_template.md"
    if template.exists():
        content = template.read_text(encoding="utf-8")
    else:
        content = f"""# Project: Novel Translator - {project_name}
# Date: {datetime.now().strftime("%Y-%m-%d")}
# Pipeline: Trifecta v7.0 (Auto-Healing)

## 🎯 Task Overview
**Novel:** {project_name}
**Input:** data/input/{project_name}.txt
**Target:** Vietnamese
**Purpose:** [Draft/Release/Review]

{task_desc if task_desc else "**Task:** [Description]"}
"""

    # Update project name in content
    content = content.replace("[PROJECT_NAME]", project_name)
    content = content.replace("[NOVEL_NAME]", project_name)

    todo_file.write_text(content, encoding="utf-8")
    return todo_file


def show_context_summary():
    """Show current project context."""
    print(f"\n{BOLD}{GREEN}📊 PROJECT CONTEXT:{RESET}")

    # Check AGENTS.md
    agents = PROJECT_ROOT / "AGENTS.md"
    if agents.exists():
        lines = agents.read_text(encoding="utf-8").split("\n")
        for line in lines[:20]:
            if any(kw in line for kw in ["Project", "Pipeline", "Version", "Active", "Last Task"]):
                print(f"  {line.strip()}")

    # Check config for API keys
    config = PROJECT_ROOT / "config/config.yaml"
    if config.exists():
        content = config.read_text(encoding="utf-8")
        if "api_keys:" in content:
            # Count keys (rough estimate)
            key_count = content.count('- "AIza')
            print(f"  {GREEN}API Keys available: {key_count}{RESET}")

    # Check recent translations
    progress = PROJECT_ROOT / "data/progress"
    if progress.exists():
        states = list(progress.glob("*_state.json"))
        print(f"  {GREEN}Recent projects: {len(states)}{RESET}")


def show_lessons_summary():
    """Show recent lessons."""
    if not LESSONS_FILE.exists():
        print(f"\n{YELLOW}  No lessons file found. Run with --init to create.{RESET}")
        return

    content = LESSONS_FILE.read_text(encoding="utf-8")

    # Extract recent issues
    issues = []
    for line in content.split("\n"):
        if "### ❌ Issue:" in line:
            issues.append(line.replace("### ❌ Issue:", "").strip())

    if issues:
        print(f"\n{BOLD}{YELLOW}[LESSONS] Recent ({len(issues)}):{RESET}")
        for issue in issues[-5:]:  # Show last 5
            print(f"  - {issue}")
    else:
        print(f"\n{GREEN}  No lessons recorded yet.{RESET}")


def review_workflow():
    """Show workflow summary."""
    print(f"""
{BOLD}{CYAN}[CHECKLIST] WORKFLOW:{RESET}

{BOLD}Before Session:{RESET}
  {GREEN}CHECK{RESET} Check AGENTS.md for updates
  {GREEN}CHECK{RESET} Review recent lessons (tasks/lessons.md)
  {GREEN}CHECK{RESET} Verify config.yaml settings

{BOLD}During Session:{RESET}
  {GREEN}CHECK{RESET} Plan first (tasks/todo_*.md)
  {GREEN}CHECK{RESET} Verify at each step
  {GREEN}CHECK{RESET} Update todo.md progress

{BOLD}After Session:{RESET}
  {GREEN}CHECK{RESET} Verify final output
  {GREEN}CHECK{RESET} Update lessons.md with new learnings
  {GREEN}CHECK{RESET} Summary to user

{BOLD}{CYAN}[QUICK COMMANDS]:{RESET}
  python main.py                    # Run translation
  python scripts/init_session.py    # Init new session
  cat tasks/lessons.md              # Review lessons
  cat AGENTS.md                     # Check context
""")


def interactive_mode():
    """Interactive session initialization."""
    print_header()

    # Check existing files
    files = check_existing_files()

    print(f"\n{GREEN}Current session files:{RESET}")
    print(f"  - Todo files: {len(files.get('todos', []))}")
    print(f"  - Lessons file: {'CHECK' if files.get('lessons') else 'CROSS (run --init)'}")
    print(f"  - AGENTS.md: {'CHECK' if files.get('agents') else 'CROSS'}")

    # Show context
    show_context_summary()

    # Show lessons
    show_lessons_summary()

    print(f"\n{BOLD}{GREEN}Session Options:{RESET}")
    print_step(1, "Start new translation task")
    print_step(2, "Create/freshen lessons.md")
    print_step(3, "Show workflow summary")
    print_step(4, "Review AGENTS.md")
    print_step(0, "Exit")

    choice = input(f"\n{YELLOW}  Select option: {RESET}")

    if choice == "1":
        project = input(f"{YELLOW}  Project name: {RESET}").strip()
        task = input(f"{YELLOW}  Task description (optional): {RESET}").strip()
        task = task if task else None
        todo_file = create_todo(project, task)
        print(f"\n{GREEN}CHECK Created: {todo_file}{RESET}")
        print(f"{GREEN}→ Edit this file to plan your task{RESET}")

    elif choice == "2":
        created, msg = init_lessons()
        print(f"\n{GREEN}CHECK {msg}: {LESSONS_FILE}{RESET}")

    elif choice == "3":
        review_workflow()

    elif choice == "4":
        if (PROJECT_ROOT / "AGENTS.md").exists():
            os.system(f"cat \"{PROJECT_ROOT / 'AGENTS.md'}\"")
        else:
            print(f"{YELLOW}  AGENTS.md not found{RESET}")

    else:
        print(f"\n{GREEN}👋 Goodbye!{RESET}")


def quick_mode(task_name: str):
    """Quick session init with task name."""
    todo_file = create_todo(task_name)
    print(f"""
{GREEN}CHECK Session initialized!{RESET}

Files created:
  - {todo_file}

Next steps:
  1. Edit {todo_file.name} with your plan
  2. Run: python main.py
  3. After completion: update tasks/lessons.md
""")


def main():
    parser = argparse.ArgumentParser(description="Novel Translator Session Initializer")
    parser.add_argument("--task", "-t", help="Quick start with task name")
    parser.add_argument("--init", "-i", action="store_true", help="Initialize lessons.md")
    parser.add_argument("--review", "-r", action="store_true", help="Show workflow summary")
    parser.add_argument("--lessons", "-l", action="store_true", help="Show recent lessons")

    args = parser.parse_args()

    if args.task:
        quick_mode(args.task)
    elif args.init:
        created, msg = init_lessons()
        print(f"{GREEN}CHECK {msg}: {LESSONS_FILE}{RESET}")
    elif args.lessons:
        show_lessons_summary()
    elif args.review:
        review_workflow()
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
