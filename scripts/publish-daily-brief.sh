#!/usr/bin/env bash
# Publish today's Hong Kong brief to GitHub Pages.
# Usage:
#   ./scripts/publish-daily-brief.sh              # today (local date)
#   ./scripts/publish-daily-brief.sh 2026-06-17   # specific issue date
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATE="${1:-$(date +%Y-%m-%d)}"
ISSUE="$ROOT/docs/brief/slides/$DATE"
PAGES_BASE="https://xieyujie8818-png.github.io/cscec_investmenthk"

cd "$ROOT"

echo "==> Date: $DATE"
echo "==> Issue folder: docs/brief/slides/$DATE/"

# Build / refresh B-consulting slide deck + sync Word if present locally
python news-intelligence-mvp/scripts/build_b_consulting_slides.py "$DATE"

# If brief.html not yet in issue folder, try publishing from local app output
if [[ ! -f "$ISSUE/brief.html" && -f "$ROOT/daily-brief-app/data/output/$DATE/daily-brief.html" ]]; then
  echo "==> Publishing brief.html + brief.docx from daily-brief-app output"
  python - <<PY
from pathlib import Path
import sys
sys.path.insert(0, str(Path("$ROOT/daily-brief-app")))
from app.brief_publish import publish_issue_bundle

html = Path("$ROOT/daily-brief-app/data/output/$DATE/daily-brief.html").read_text(encoding="utf-8")
assets = Path("$ROOT/daily-brief-app/data/output/$DATE/assets")
word = Path("$ROOT/daily-brief-app/data/output/$DATE/daily-brief.docx")
publish_issue_bundle(
    html,
    "$DATE",
    word_path=word if word.is_file() else None,
    source_assets_dir=assets if assets.is_dir() else None,
    build_slides=False,
)
PY
fi

echo ""
echo "Issue bundle:"
ls -la "$ISSUE" 2>/dev/null || true

echo ""
echo "==> Git commit & push (triggers GitHub Pages deploy)"
git add docs/brief/
if git diff --staged --quiet; then
  echo "No changes under docs/brief/ — nothing to publish."
  exit 0
fi
git commit -m "Publish Hong Kong brief $DATE"
git push

echo ""
echo "Done. After GitHub Actions finishes (~1–2 min), share these links:"
echo "  Slides:  $PAGES_BASE/brief/slides/$DATE/"
echo "  Article: $PAGES_BASE/brief/slides/$DATE/brief.html"
echo "  Word:    $PAGES_BASE/brief/slides/$DATE/brief.docx"
echo "  Latest:  $PAGES_BASE/brief/slides/"
