"""Keyword-based scoring aligned with 03-scoring-rules.md."""



from __future__ import annotations



import re

from pathlib import Path



import yaml



from app.models import RawArticle, ScoredArticle



WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]



CREDIBILITY_MAP = {"A": 5, "B": 4, "C": 2}



_STOCK_CODE_RE = re.compile(r"[（(]\d{4,5}[）)]")





def load_keywords_config() -> dict:

    path = Path(__file__).resolve().parent.parent / "config" / "keywords.yaml"

    with open(path, encoding="utf-8") as f:

        return yaml.safe_load(f)





def _text_blob(article: RawArticle) -> str:

    return f"{article.title} {article.snippet} {article.body}".lower()





def _title_blob(title: str) -> str:

    return (title or "").lower()





def _count_hits(text: str, keywords: list[str]) -> int:

    hits = 0

    for kw in keywords:

        if kw.lower() in text:

            hits += 1

    return hits





def _matches_any(text: str, patterns: list[str]) -> bool:

    low = text.lower()

    return any(p.lower() in low for p in patterns)





def is_opinion_content(title: str, text: str = "", url: str = "") -> bool:

    """True for commentary/column pieces, not straight news."""

    cfg = load_keywords_config()

    blob = f"{title} {text} {url}".lower()

    if _matches_any(blob, cfg.get("opinion_patterns", [])):

        return True

    low_url = (url or "").lower()

    for frag in ("/opinion", "/column", "/comment", "financial-comment", "/author"):

        if frag in low_url:

            return True

    return False





def is_individual_stock_news(title: str, text: str = "") -> bool:

    """True when headline is mainly single-stock price movement."""

    cfg = load_keywords_config()

    blob = f"{title} {text}".lower()

    if _STOCK_CODE_RE.search(title or ""):

        if _count_hits(blob, cfg.get("macro_keywords", [])) == 0:

            if _count_hits(blob, cfg.get("hk_policy_keywords", [])) == 0:

                if _count_hits(blob, cfg.get("topic_boost", [])) == 0:

                    return True

    if _matches_any(title, cfg.get("stock_exclude_patterns", [])):

        macro_hits = _count_hits(blob, cfg.get("macro_keywords", []))

        policy_hits = _count_hits(blob, cfg.get("hk_policy_keywords", []))

        topic_hits = _count_hits(blob, cfg.get("topic_boost", []))

        if macro_hits + policy_hits + topic_hits == 0:

            return True

    return False





def title_passes_listing_gate(

    title: str,

    section_type: str = "finance",

    cfg: dict | None = None,

) -> bool:

    """Pre-fetch gate: skip low-value listing titles (e.g. HKET instant news)."""

    cfg = cfg or load_keywords_config()

    title = (title or "").strip()

    if len(title) < 6:

        return False

    if is_opinion_content(title):

        return False

    if section_type == "finance" and is_individual_stock_news(title):

        return False

    positive = (

        cfg.get("title_prefilter_keywords", [])

        + cfg.get("topic_boost", [])

        + cfg.get("macro_keywords", [])

        + cfg.get("hk_policy_keywords", [])

    )

    if section_type == "property":

        positive = positive + cfg.get("section_keywords", {}).get("建築與地產", [])

    else:

        positive = positive + cfg.get("section_keywords", {}).get("金融與經濟", [])

    if _count_hits(_title_blob(title), positive) >= 1:

        return True

    if any(k in title for k in ("政策", "立法", "億", "注資", "破產", "債務", "規劃", "批出")):

        return True

    return False





def _importance(text: str, cfg: dict) -> int:

    boost = _count_hits(text, cfg.get("topic_boost", []))

    macro = _count_hits(text, cfg.get("macro_keywords", []))

    policy = _count_hits(text, cfg.get("hk_policy_keywords", []))

    if any(k in text for k in ["政策", "立法", "重大", "億", "注資", "破產", "債務"]):

        return min(5, 4 + (1 if boost or macro or policy else 0))

    if macro >= 2 or policy >= 2 or boost >= 2:

        return 4

    if macro >= 1 or policy >= 1 or boost == 1:

        return 3

    if any(k in text for k in ["成交", "新盤", "租金", "PMI", "利率"]):

        return 3

    return 2





def _relevance(text: str, cfg: dict) -> int:

    boost = _count_hits(text, cfg.get("topic_boost", []))

    macro = _count_hits(text, cfg.get("macro_keywords", []))

    policy = _count_hits(text, cfg.get("hk_policy_keywords", []))

    if boost >= 2:

        return 5

    if boost == 1 or macro >= 2 or policy >= 2:

        return 4

    if macro >= 1 or policy >= 1:

        return 4

    if any(k in text for k in cfg.get("section_keywords", {}).get("建築與地產", [])):

        return 3

    if any(k in text for k in cfg.get("section_keywords", {}).get("金融與經濟", [])):

        return 3

    return 2





def _actionability(text: str) -> int:

    if any(k in text for k in ["招標", "推盤", "申請", "強拍", "合作", "投資", "跟進"]):

        return 4

    if any(k in text for k in ["成交", "租金", "政策", "規劃"]):

        return 3

    return 2





def _assign_section(text: str, section_type: str, cfg: dict, title: str = "") -> str:

    """Assign digest section using primary storyline, not incidental keywords.

    Editorial rules: app/cursoragent/規則.md
    """

    sk = cfg.get("section_keywords", {})

    sa = cfg.get("section_assignment", {})

    blob = f"{title} {text}".lower()

    title_blob = (title or "").lower()

    lead = blob[:500]



    beidu_primary = sa.get("beidu_primary_keywords", sk.get("北都專題", []))

    exclude_zones = sa.get("beidu_exclude_zones", [])

    finance_policy = sa.get("finance_policy_keywords", [])

    beidu_lead = sa.get("beidu_lead_keywords", beidu_primary)



    primary_hits = _count_hits(blob, beidu_primary)

    exclude_hits = _count_hits(blob, exclude_zones)

    lead_primary_hits = _count_hits(lead, beidu_lead)



    # Cross-border / State Council policy → finance (e.g. GBA yacht scheme)

    if _count_hits(blob, finance_policy) >= 1:

        if lead_primary_hits == 0 and _count_hits(title_blob, beidu_primary) == 0:

            return "金融與經濟"



    # Non-NM zones (East Kowloon transit, etc.) without NM storyline → property

    if exclude_hits >= 1 and primary_hits == 0 and lead_primary_hits == 0:

        return "建築與地產"



    # NM as primary subject (title/lead or strong body signal)

    if lead_primary_hits >= 1:

        return "北都專題"

    if primary_hits >= 2:

        return "北都專題"

    if primary_hits == 1 and exclude_hits == 0:

        return "北都專題"

    if _count_hits(blob, sk.get("北都專題", [])) >= 1 and exclude_hits == 0:

        return "北都專題"



    if section_type == "property":

        return "建築與地產"

    if _count_hits(blob, sk.get("建築與地產", [])) >= 1:

        return "建築與地產"

    return "金融與經濟"





def _total(importance: int, relevance: int, actionability: int, credibility: int) -> float:

    return round(

        (importance * 0.35 + relevance * 0.35 + actionability * 0.20 + credibility * 0.10)

        * 20,

        1,

    )





def _first_summary_line(body: str, snippet: str) -> str:

    for candidate in (body, snippet):

        if not candidate:

            continue

        for line in candidate.splitlines():

            s = re.sub(r"\s+", " ", line).strip()

            if len(s) < 15:

                continue

            if s.startswith("文章：") or s.startswith("文章:"):

                continue

            if s in ("全文", "關注", "儲存文章"):

                continue

            return s

        parts = re.split(r"(?<=[。！？])\s*", candidate.strip())

        for p in parts:

            s = re.sub(r"\s+", " ", p).strip()

            if len(s) >= 15 and not s.startswith("文章"):

                return s

    return ""





def _first_sentence(text: str) -> str:

    if not text:

        return ""

    s = re.sub(r"\s+", " ", text).strip()

    parts = re.split(r"(?<=[。！？])\s*", s)

    for p in parts:

        p = p.strip()

        if len(p) >= 8:

            return p

    return s[:100] if len(s) > 100 else s





def extract_body_paragraphs(body: str, snippet: str = "") -> list[str]:

    """Split fetched article body into paragraphs for verbatim reproduction."""

    text = (body or snippet or "").strip()

    if not text:

        return []

    chunks = [p.strip() for p in re.split(r"\n{2,}", text) if len(p.strip()) >= 10]

    if len(chunks) >= 2:

        return chunks

    lines = [ln.strip() for ln in text.splitlines() if len(ln.strip()) >= 10]

    if len(lines) >= 2:

        return lines

    parts = re.split(r"(?<=[。！？])\s*", text)

    return [p.strip() for p in parts if len(p.strip()) >= 10] or [text]





def _split_sentences(text: str, max_count: int = 2) -> list[str]:
    s = re.sub(r"\s+", " ", (text or "").strip())
    if not s:
        return []
    parts = re.split(r"(?<=[。！？])\s*", s)
    result: list[str] = []
    for p in parts:
        p = p.strip()
        if len(p) >= 8:
            result.append(p)
        if len(result) >= max_count:
            break
    return result or ([s] if len(s) >= 8 else [])


def catalog_summary_from_body(
    body: str,
    snippet: str = "",
    title: str = "",
    max_sentences: int = 2,
) -> str:
    """TOC summary: first 1–2 sentences from original text, verbatim (no AI rewrite)."""
    line = _first_summary_line(body, snippet)
    if line:
        sents = _split_sentences(line, max_sentences)
        if sents:
            return "".join(sents)
    paras = extract_body_paragraphs(body, snippet)
    if paras:
        sents = _split_sentences(paras[0], max_sentences)
        if sents:
            return "".join(sents)
    return title


def _catalog_summary(title: str, snippet: str, body: str) -> str:
    return catalog_summary_from_body(body, snippet, title)





def _paragraphs(title: str, snippet: str, body: str, source_name: str) -> list[str]:

    paras = extract_body_paragraphs(body, snippet)

    if paras:

        return paras

    return [f"報道指出，{title}。詳情可參閱{source_name}原文。"]





def _business_implication(section: str, text: str) -> str:

    if section == "北都專題":

        return "與北都產業、土地或片區發展研判相關，值得項目條線持續跟蹤。"

    if section == "建築與地產":

        return "對樓市成交、租金、新盤或改建判斷具參考價值。"

    return "對宏觀環境、政策及企業財政背景具參考價值。"





def _monthly_flag(total: float, importance: int, text: str) -> tuple[bool, str]:

    if total >= 65 and importance >= 4:

        if any(k in text for k in ["政策", "北都", "產業", "立法", "成交", "債務"]):

            return True, "具政策/專題延續性，建議納入月報素材"

    return False, ""





def _rejected_article(

    article: RawArticle, news_id: str = ""

) -> ScoredArticle:

    return ScoredArticle(

        news_id=news_id,

        title=article.title,

        url=article.url,

        original_url=article.url,

        source_name=article.source_name,

        source_id=article.source_id,

        publish_date=article.publish_date,

        digest_section="剔除",

        catalog_summary="",

        paragraphs=[],

        topic_tags=[],

        importance_score=1,

        relevance_score=1,

        actionability_score=1,

        credibility_score=CREDIBILITY_MAP.get(article.credibility, 4),

        total_score=20.0,

        business_implication="",

    )





def score_article(

    article: RawArticle,

    section_type: str,

    cfg: dict | None = None,

    news_id: str = "",

) -> ScoredArticle:

    cfg = cfg or load_keywords_config()

    text = _text_blob(article)



    for pat in cfg.get("exclude_patterns", []):

        if pat in article.title:

            return _rejected_article(article, news_id)



    if is_opinion_content(article.title, text, article.url):

        return _rejected_article(article, news_id)



    section = _assign_section(text, section_type, cfg, article.title)

    if section == "金融與經濟" and is_individual_stock_news(article.title, text):

        return _rejected_article(article, news_id)



    importance = _importance(text, cfg)

    relevance = _relevance(text, cfg)

    actionability = _actionability(text)

    cred = CREDIBILITY_MAP.get(article.credibility, 4)

    total = _total(importance, relevance, actionability, cred)



    tags = [kw for kw in cfg.get("topic_boost", []) if kw.lower() in text][:5]

    monthly, reason = _monthly_flag(total, importance, text)



    return ScoredArticle(

        news_id=news_id,

        title=article.title,

        url=article.url,

        original_url=article.url,

        source_name=article.source_name,

        source_id=article.source_id,

        publish_date=article.publish_date,

        digest_section=section,

        catalog_summary=_catalog_summary(article.title, article.snippet, article.body),

        body=(article.body or article.snippet or "").strip(),

        paragraphs=_paragraphs(article.title, article.snippet, article.body, article.source_name),

        topic_tags=tags or [section[:4]],

        importance_score=importance,

        relevance_score=relevance,

        actionability_score=actionability,

        credibility_score=cred,

        total_score=total,

        business_implication=_business_implication(section, text),

        monthly_candidate=monthly,

        monthly_reason=reason,

    )





def extract_paragraphs(title: str, snippet: str, body: str, source_name: str) -> list[str]:

    return _paragraphs(title, snippet, body, source_name)





def select_for_report(

    scored: list[ScoredArticle], quotas: dict[str, int], min_score: float = 60.0

) -> tuple[dict[str, list[ScoredArticle]], list[ScoredArticle], list[ScoredArticle]]:

    usable = [s for s in scored if s.digest_section != "剔除" and s.total_score >= min_score]

    usable.sort(key=lambda x: x.total_score, reverse=True)



    picked: dict[str, list[ScoredArticle]] = {k: [] for k in quotas}

    used_urls: set[str] = set()



    for section, limit in quotas.items():

        pool = [u for u in usable if u.digest_section == section and u.url not in used_urls]

        for item in pool[:limit]:

            picked[section].append(item)

            used_urls.add(item.url)



    for section, limit in quotas.items():

        while len(picked[section]) < limit:

            remaining = [u for u in usable if u.url not in used_urls]

            if not remaining:

                break

            item = remaining[0]

            item.digest_section = section

            picked[section].append(item)

            used_urls.add(item.url)



    selected = [a for sec in picked.values() for a in sec]

    monthly = [a for a in selected if a.monthly_candidate]

    archived = [u for u in usable if u.url not in used_urls][:10]

    return picked, monthly, archived


