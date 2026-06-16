"""Pipeline entry points for v2 workflow."""

from __future__ import annotations

from datetime import date

from app.brief_generator import generate_brief_from_selection
from app.candidates import OUTPUT_DIR, fetch_and_score_candidates

__all__ = ["OUTPUT_DIR", "fetch_and_score_candidates", "generate_brief_from_selection"]
