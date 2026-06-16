# 08 每日編制《香港簡訊》工作流



本文件描述如何用 **daily-brief-app 日報系統** 或 **Cursor Agent** 編制《香港簡訊》。採集來源為四報官網**列表頁主欄 + 正文**；**不再使用** HKET 電子報 flipbook（A0/D0 翻頁版）。



## 目標產出



| 文件 | 說明 |

| --- | --- |

| `output/{日期或日期區間}/daily-leadership-brief.md` | 《香港簡訊》完整稿（Markdown） |

| `output/{日期或日期區間}/daily-leadership-brief.html` | 同內容 HTML 版；原文配圖須內嵌展示 |

| `output/{日期或日期區間}/daily-leadership-brief.docx` | Word 定稿（`daily-brief-app/templates/brief-template.docx`） |

| `output/{日期或日期區間}/daily-feishu-digest.md` | 飛書群版（無月報標記） |

| `output/{日期或日期區間}/daily-internal-monthly-markers.md` | 僅市場部負責人 |

| `output/{日期或日期區間}/news-register.csv` | 候選與定稿登記 |



模板來源：`templates/` 下同名文件。



**多日匯總：** 若選取多個日期，上述文件只產出 **一份** 匯總定稿，目錄以 `YYYY-MM-DD`（單日）或 `YYYY-MM-DD_YYYY-MM-DD`（區間）命名。



## 架構（推薦：daily-brief-app）



```

登入四報會員（首次）

        ↓

選擇日期或日期區間 → 抓取列表標題 → 標題預篩 → 僅匹配者抓正文 → 評分去重

        ↓

人工在 UI 勾選、調序 → 生成定稿（15–20 條）

        ↓

人工審核 → 飛書推送

```



**不做：** HKET 全站搜索、地產站首頁、flipbook 翻頁、側邊欄推薦文、時事評論/專欄。



## 採集範圍（系統硬性規則）



| 允許 | 禁止 |

| --- | --- |

| HKET 要聞/地產/即時新聞列表主欄 + 正文 | `web-flip` 電子報 A0/D0 |

| 信報、明報、文匯網列表主欄 | `service.hket.com/search` |

| 列表主欄內鏈 `article` 正文 | 側邊欄、點擊排行、熱門文章 |

| 標題預篩通過後才抓正文 | 評論、專欄、樓評、社評 |

| | `ps.hket.com` 地產站（默認） |



### HKET 固定 URL（見 `daily-brief-app/config/sources.yaml`）



| 版塊 | URL |

| --- | --- |

| 要聞 | `https://paper.hket.com/srap001/要聞?dis=YYYYMMDD` |

| 地產 | `https://paper.hket.com/srap007/地產?dis=YYYYMMDD` |

| **即時新聞** | `https://inews.hket.com/sran001/%E5%85%A8%E9%83%A8` |



**標題優先：** 所有列表先讀標題做關鍵詞匹配，僅通過預篩者才點入正文；禁止逐篇無差別爬取。



## 定稿格式要點



| 項目 | 規則 |

| --- | --- |

| 條數 | 候選池與定稿建議 **15–20 條**；去重；評分 **≥70** |

| 目錄 | 標題錨點鏈接 + **一至兩句摘要**（取自原文首句，照錄）；**不含**原文鏈接 |

| 正文 | `【本報M月D日消息】` 後接 **原文全文**（逐段照錄），不做 AI 改寫或摘要 |

| 對外產出 | **不含**原文鏈接欄位 |



## 登入



HKET / 信報 / 明報會員賬密 **不得** 寫入代碼或文檔。在 `daily-brief-app` 首頁點「登入」，或 Cursor 內瀏覽器手動登入。



## Agent 執行步驟（手動補漏時）



完整指令：`templates/agent-daily-prompt.md`。欄目分配準則：`app/cursoragent/規則.md`。



1. **確認日期或日期區間** → 對照 `02-source-list.md` 與 `sources.yaml`。

2. **優先使用 daily-brief-app** 已抓取的 `data/output/{日期或區間}/candidates.json`（若存在）。

3. **篩選** 15–20 條（見 `01-scope-taxonomy.md`）；金融欄避開個股短訊，只要新聞不要評論；去重且評分要高。

4. **會員全文採集**：在 Cursor 瀏覽器已登入狀態下，逐篇打開定稿 `article` 頁，抓取 **原文全文** 與文內配圖 URL（見 `scripts/extract-article-browser.js`）。不得以摘要、節錄或「原文鏈接」代替正文。

5. **成稿** 至 `output/{日期或區間}/`：`daily-leadership-brief.md` + **`daily-leadership-brief.html`**（HTML 須內嵌原文配圖）；多日匯總為 **一份** 定稿。

6. **人工審核** 後推送。



## 缺稿處理



- 在匯報中標明「缺稿」；

- **不要** 用 flipbook、全站搜索或地產站補位（除非業務負責人明確要求）；

- 見 `02-source-list.md` 人工補充來源。



## 自動化：daily-brief-app



倉庫根目錄 **`daily-brief-app/`**：



- 網頁控制台：登入四報會員 → 選日期區間 → 一鍵抓取候選 → 人工勾選 → 生成定稿

- 週一至五 **10:00 HKT** 自動抓取當日候選

- 來源：HKET（要聞+地產+即時）+ 信報 + 明報 + 文匯報

- 安裝與使用見 `daily-brief-app/README.md`



## 相關文件



- 範圍：`01-scope-taxonomy.md`

- 來源：`02-source-list.md`

- 評分：`03-scoring-rules.md`

- 人工手冊：`04-daily-pilot-runbook.md`

- 每日指令：`templates/agent-daily-prompt.md`


