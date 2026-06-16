# 香港簡訊



**{{ report.weekday_label }}**



**海外與投資部 編制**



---



## 目 錄



{% for section_name, items in report.sections.items() %}

**【{{ section_name }}】**



{% for item in items %}

- [{{ item.title }}](#{{ item.news_id }})



【{{ item.catalog_summary }}】



{% endfor %}

{% endfor %}



---



## 正文



{% for section_name, items in report.sections.items() %}

{% for item in items %}

<a id="{{ item.news_id }}"></a>



### {{ item.title }}



[來源：{{ item.source_name }}]



{{ item_dateline(item) }}



{% for para in item.body_paragraphs %}

{{ para }}



{% endfor %}

---



{% endfor %}

{% endfor %}


