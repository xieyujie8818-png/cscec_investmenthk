# 【內部 · 月報素材標記】{{ report.date }}

**收件人：** 市場部負責日報/月報的同事

---

## 今日建議納入月報

| 序號 | 新聞標題 | 日報欄目 | 標記原因 | news_id |
| --- | --- | --- | --- | --- |
{% for item in report.monthly_candidates %}
| {{ loop.index }} | {{ item.title }} | {{ item.digest_section }} | {{ item.monthly_reason }} | {{ item.news_id }} |
{% else %}
| - | （今日無自動標記；可人工從 daily-brief.md 補充） | | | |
{% endfor %}

## 定稿條目

{% for section_name, items in report.sections.items() %}
### {{ section_name }}
{% for item in items %}
- **{{ item.title }}**（{{ item.total_score }}分）— {{ item.business_implication }}
{% endfor %}
{% endfor %}
