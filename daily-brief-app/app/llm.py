"""LLM polish — disabled; returns source text unchanged."""

from __future__ import annotations


def polish_paragraphs(title: str, paragraphs: list[str]) -> list[str]:
    """No-op: daily brief uses verbatim article body, not LLM rewriting."""
    return paragraphs
