"""Data models for daily brief pipeline v2."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class RawArticle:
    title: str
    url: str
    source_name: str
    source_id: str
    section_label: str
    section_type: str = "finance"
    credibility: str = "A"
    publish_date: str = ""
    body: str = ""
    snippet: str = ""


@dataclass
class ScoredArticle:
    news_id: str
    title: str
    url: str
    original_url: str
    source_name: str
    digest_section: str
    catalog_summary: str
    paragraphs: list[str]
    topic_tags: list[str]
    importance_score: int
    relevance_score: int
    actionability_score: int
    credibility_score: int
    total_score: float
    business_implication: str
    image_asset: str = ""
    screenshot_path: str = ""
    selected: bool = False
    sort_order: int = 0
    monthly_candidate: bool = False
    monthly_reason: str = ""
    region: str = "全港/宏觀"
    publish_date: str = ""
    source_id: str = ""
    body: str = ""
    body_paragraphs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ScoredArticle:
        return cls(
            news_id=d.get("news_id", ""),
            title=d.get("title", ""),
            url=d.get("url", ""),
            original_url=d.get("original_url", d.get("url", "")),
            source_name=d.get("source_name", ""),
            digest_section=d.get("digest_section", ""),
            catalog_summary=d.get("catalog_summary", ""),
            paragraphs=d.get("paragraphs", []),
            topic_tags=d.get("topic_tags", []),
            importance_score=d.get("importance_score", 0),
            relevance_score=d.get("relevance_score", 0),
            actionability_score=d.get("actionability_score", 0),
            credibility_score=d.get("credibility_score", 0),
            total_score=d.get("total_score", 0.0),
            business_implication=d.get("business_implication", ""),
            image_asset=d.get("image_asset", ""),
            screenshot_path=d.get("screenshot_path", ""),
            selected=d.get("selected", False),
            sort_order=d.get("sort_order", 0),
            monthly_candidate=d.get("monthly_candidate", False),
            monthly_reason=d.get("monthly_reason", ""),
            region=d.get("region", "全港/宏觀"),
            publish_date=d.get("publish_date", ""),
            source_id=d.get("source_id", ""),
            body=d.get("body", ""),
            body_paragraphs=d.get("body_paragraphs", d.get("paragraphs", [])),
        )


@dataclass
class DailyReport:
    date: str
    weekday_label: str
    headline: str
    date_start: str = ""
    date_end: str = ""
    sections: dict[str, list[ScoredArticle]] = field(default_factory=dict)
    monthly_candidates: list[ScoredArticle] = field(default_factory=list)
    archived: list[ScoredArticle] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "date_start": self.date_start or self.date,
            "date_end": self.date_end or self.date,
            "weekday_label": self.weekday_label,
            "headline": self.headline,
            "sections": {
                k: [a.to_dict() for a in v] for k, v in self.sections.items()
            },
            "monthly_candidates": [a.to_dict() for a in self.monthly_candidates],
            "archived": [a.to_dict() for a in self.archived],
            "meta": self.meta,
        }
