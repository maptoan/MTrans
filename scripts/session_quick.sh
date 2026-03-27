#!/bin/bash
# Novel Translator Session Quick Start
# ======================================

set -euo pipefail

PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$PROJECT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     Novel Translator Session - Quick Start          ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"

# Check existing files
echo ""
echo -e "${GREEN}📂 Session Files:${NC}"
echo "  - Todo files: $(ls tasks/todo_*.md 2>/dev/null | wc -l)"
echo "  - Lessons: $([ -f tasks/lessons.md ] && echo '✓' || echo '✗')"
echo "  - AGENTS.md: $([ -f AGENTS.md ] && echo '✓' || echo '✗')"

# Quick commands
echo ""
echo -e "${YELLOW}🚀 Quick Commands:${NC}"
if command -v python3 >/dev/null 2>&1; then
  PY_CMD="python3"
else
  PY_CMD="python"
fi
echo "  $PY_CMD scripts/init_session.py                    # Interactive"
echo "  $PY_CMD scripts/init_session.py --task HMQT        # Quick start"
echo "  $PY_CMD scripts/init_session.py --init             # Create lessons.md"
echo "  $PY_CMD scripts/init_session.py --review           # Show workflow"
echo "  $PY_CMD scripts/init_session.py --lessons          # Show recent lessons"
echo ""
echo -e "${YELLOW}📋 Workflow:${NC}"
echo "  1. Plan:   Edit tasks/todo_[PROJECT]_[DATE].md"
echo "  2. Run:    $PY_CMD main.py"
echo "  3. Learn:  Update tasks/lessons.md"
echo ""
echo -e "${GREEN}👉 Ready! Run one of the commands above.${NC}"
