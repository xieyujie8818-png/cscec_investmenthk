# Agent 每日指令（複製到 Cursor 對話）



將下方 `---BEGIN---` 到 `---END---` 整段複製發給 Agent。把 `{DATE}` 換成編制日或日期區間（如 `2026-06-13` 或 `2026-06-13 至 2026-06-15`）。



---BEGIN---



請按 `news-intelligence-mvp/08-daily-agent-workflow.md` 編制 **{DATE}** 的《香港簡訊》。



## 前置



1. **優先** 使用 `daily-brief-app` 已抓取的 `data/output/{日期或區間}/candidates.json`（若存在）。

2. 若需補抓 HKET：登入 https://paper.hket.com ，等我說「好了」再繼續。

3. 閱讀：`01-scope-taxonomy.md`、`02-source-list.md`、`03-scoring-rules.md`、**`app/cursoragent/規則.md`**（欄目分配）。

4. 在 `news-intelligence-mvp/output/{日期或區間}/` 建立目錄。



## 多日匯總



若 `{DATE}` 為 **多個日期**，將區間內所有候選 **去重、評分** 後，匯總產出 **同一份** 定稿（非每日各一份）。



## 採集範圍（嚴格）



**只允許** 四報官網**列表頁主欄**新聞（及內鏈 `article` 正文）：



| 來源 | 允許入口 |

| --- | --- |

| HKET | 要聞列表、地產列表、**即時新聞** `https://inews.hket.com/sran001/%E5%85%A8%E9%83%A8` |

| 信報 | `dailynews/headline`、`dailynews/property` |

| 明報 | 經濟版列表 |

| 文匯網 | 經濟、財經、地產、投資（**不含財評**） |



**禁止（不要執行）：**



- ❌ HKET 電子報 flipbook（`web-flip`、A0/D0）

- ❌ `service.hket.com/search` 全站搜索

- ❌ `ps.hket.com` 地產站

- ❌ 側邊欄、點擊排行、熱門推薦

- ❌ 評論、專欄、樓評、社評等時事評論稿

- ❌ 金融欄個股短訊（除非同時涉及宏觀/政策）



**標題優先：** 所有列表先掃標題做關鍵詞匹配，**僅通過預篩者**才點入 `article` 取正文；禁止逐篇無差別爬取。



## 篩選



- 候選池與定稿建議 **15–20 條**；**去重**；評分 **≥70**。

- 【金融與經濟】— **宏觀經濟、香港政策**，避開個股

- 【建築與地產】、【北都專題】— 按 `01-scope-taxonomy.md` 及 **`app/cursoragent/規則.md`**（主線優先，見易錯對照表）

- 定稿前逐條核對欄目；自動評分結果與編輯準則衝突時，**以編輯準則為準**。

- 只要**新聞稿**，不要評論類文章。

- 某欄缺稿時標明「缺稿」，勿用禁止來源補位。



## 會員全文採集（必須）



- 信報、HKET、明報等 **會員牆** 正文，須在 **Cursor 瀏覽器已登入會員** 狀態下逐篇打開 `article` 頁抓取 **原文全文**。

- **禁止** 以「原文鏈接」、摘要或節錄代替正文；**禁止** 用未登入的 WebFetch / curl 代替瀏覽器採集會員稿。

- 可參考 `scripts/extract-article-browser.js` 抽取標題、正文與文內配圖 URL。



## 輸出（基於 templates/ 填寫）



1. `output/{日期或區間}/daily-leadership-brief.md`

2. `output/{日期或區間}/daily-leadership-brief.html`（與 md 同內容；**原文有配圖時須在 HTML 內嵌展示**）

3. `output/{日期或區間}/daily-leadership-brief.docx`（以 `daily-brief-app/templates/brief-template.docx` 為模板；目錄頁碼開啟後按 **F9** 更新）

4. `output/{日期或區間}/daily-feishu-digest.md`

5. `output/{日期或區間}/daily-internal-monthly-markers.md`

6. `output/{日期或區間}/news-register.csv`



## 定稿格式



- 目錄：標題錨點鏈接 + **一至兩句摘要**（取自原文首句，照錄）；**不含**原文鏈接

- 正文：`【本報M月D日消息】`（用該文發佈日）後接 **原文全文**，不做 AI 改寫

- 對外產出（md、html、飛書群版）**均不含**原文鏈接；內部登記可用 URL，但不得寫入領導簡訊正文



## 約束



- 不得編造金額、參與方；不足處標「需查證」。

- 不得自動發飛書。

- 不要向我索要密碼。



完成後簡要匯報：候選幾條、定稿幾條、各欄目幾條、是否去重、是否用過禁止來源（應為「否」）。



---END---


