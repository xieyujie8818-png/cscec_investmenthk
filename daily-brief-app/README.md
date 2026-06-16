# 香港簡訊 · 日報系統 v2



单栈自动化日报：**抓取候选 → 人工审核 → 生成 Markdown 定稿**。



## 工作流



```

登录四报（首次）→ 选择日期或日期区间 → 抓取列表标题 → 标题预筛 → 匹配者抓正文

        ↓

人工在 UI 勾选调序 → 保存 → 生成定稿（15–20 条，去重）

        ↓

                              daily-brief.md + daily-brief.html + daily-brief.docx

                              + feishu.txt + monthly.md + report.json

```



**多日选取：** 如 6/13–6/15，候選與定稿 **匯總為同一份**，目錄名 `2026-06-13_2026-06-15`。



工作日 **10:00 HKT** 仅自动 **抓取候选**（不自动生成定稿）。



## 安装



```powershell

cd daily-brief-app

.\install.ps1

.\start.ps1

```



浏览器：http://127.0.0.1:8765



## .env 配置



```env

HKEJ_EMAIL=

HKEJ_PASSWORD=

MINGPAO_USERNAME=

MINGPAO_PASSWORD=

HKET_USERNAME=

HKET_PASSWORD=



HOST=127.0.0.1

PORT=8765

ENABLE_SCHEDULER=true

SCHEDULE_HOUR=10

```



> 日報正文直接使用 **原文全文**，不做 AI 改寫；對外定稿 **不含原文鏈接**。



## 来源（官网列表主栏 + 正文，无 flipbook）



| 报纸 | 列表页 |

|------|--------|

| HKET | 要聞、地產、**即時新聞** `https://inews.hket.com/sran001/%E5%85%A8%E9%83%A8` |

| 信报 | dailynews/headline、property |

| 明报 | 經濟版 section 列表 |

| 文汇报 | wenweipo.com/business、finance、real-estate、investment（**不含財評**） |



**筛选规则：**

- 仅列表 **主栏**；禁止侧栏/点击排行/热门推荐

- **标题优先：** 所有列表先匹配标题，通过预筛才抓正文

- 金融栏避开个股短讯，侧重宏观与香港政策

- 只要新闻稿，剔除评论/专栏

- 候选与定稿建议 **15–20 条**，评分 **≥70**，去重



## 产出文件



`data/output/YYYY-MM-DD/` 或 `data/output/YYYY-MM-DD_YYYY-MM-DD/`：



| 文件 | 说明 |

|------|------|

| `candidates.json` | 抓取+打分+去重后各栏 Top 20 候选 |

| `selection.json` | 人工勾选结果 |

| **`daily-brief.md`** | **主定稿**（目录锚点 + 原文首句摘要 + 原文全文） |

| **`daily-brief.html`** | **HTML 定稿**（标题跳转锚点） |

| **`daily-brief.docx`** | **Word 定稿**（以 `templates/brief-template.docx` 663期樣式為模板；目錄頁碼開啟後按 **F9** 更新） |

| `feishu.txt` | 飞书群简讯（无原文链接） |

| `monthly.md` | 月报素材 |

| `report.json` | 结构化数据 |



## candidates.json schema



```json

{

  "date_start": "2026-06-13",

  "date_end": "2026-06-15",

  "report_key": "2026-06-13_2026-06-15",

  "sections": {

    "金融與經濟": [{ "news_id", "title", "total_score", "publish_date", ... }],

    "建築與地產": [],

    "北都專題": []

  },

  "selection": { "target_total_min": 15, "target_total_max": 20, "min_total_score": 70 }

}

```



## API



| 方法 | 路径 |

|------|------|

| POST | `/api/fetch-candidates?date_start=&date_end=` |

| GET | `/api/candidates/{report_key}` |

| PUT | `/api/candidates/{report_key}/selection` |

| POST | `/api/generate-brief?report_key_str=` |

| GET | `/report/{report_key}/brief` |



## 业务规则



对齐 `news-intelligence-mvp/01-scope-taxonomy.md`、`02-source-list.md`、`03-scoring-rules.md`。


