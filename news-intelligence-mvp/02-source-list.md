# 02 新聞來源清單



本清單用於 MVP 試點。**日報系統**（`daily-brief-app/`）與 **Cursor Agent** 均採用四報官網**列表頁主欄 + 正文**；**不再使用** HKET 電子報 flipbook（A0/D0）。



## 來源分級



| 等級 | 定義 | 使用方式 |

| --- | --- | --- |

| A | 指定報社官網列表主欄內鏈正文 | 主來源，優先摘取 |

| B | 業務負責人臨時指定的補充來源 | 只在 A 級未覆蓋但專題重要時使用 |

| C | 搜索結果、社交平台、二手轉載 | 不採納，只作查找線索 |



## 日報系統固定來源（daily-brief-app）



| 來源 | 版塊 | 可信度 | 更新 | 監測重點 |

| --- | --- | --- | --- | --- |

| 香港經濟日報 HKET | 要聞、地產、**即時新聞** | A | 每日 | 金融、政策、樓市、北都 |

| 信報 HKEJ | 要聞、地產 | A | 每日 | 宏觀、地產、政策 |

| 明報 | 經濟版 | A | 每日 | 綜合要聞、地產 |

| 香港文匯報 | 經濟、財經、地產、投資 | A | 每日 | 綜合要聞、地產 |



**僅讀各報列表頁主欄**，不使用側邊欄、點擊排行、熱門推薦、全站搜索、地產子站或社交轉載。



### HKET（Agent 與系統共用）



| 版塊 | URL |

| --- | --- |

| 要聞 | `https://paper.hket.com/srap001/要聞?dis=YYYYMMDD` |

| 地產 | `https://paper.hket.com/srap007/地產?dis=YYYYMMDD` |

| **即時新聞** | `https://inews.hket.com/sran001/%E5%85%A8%E9%83%A8` |



- 會員文章正文：`paper.hket.com/article/…`、`invest.hket.com/article/…`、`inews.hket.com/article/…`

- **禁止：** flipbook（`web-flip`、A0/D0）、`service.hket.com/search`、`ps.hket.com` 地產站



### 信報 / 明報 / 文匯報



- 需各自會員登入；Cookie 由 `daily-brief-app` 本機保存（`data/browser_profiles/`）

- URL 模板見 `daily-brief-app/config/sources.yaml`

- 首次由有會員的同事在系統首頁點「登入」完成授權



### 人工補充（非默認）



| 來源 | URL | 說明 |

| --- | --- | --- |

| HKET 地產站 | [ps.hket.com](https://ps.hket.com/?mtc=70058) | 僅列表主欄缺稿時人工使用 |

| HKET 站內搜索 | [service.hket.com/search](https://service.hket.com/search/result?dis=basic&keyword=) | Agent / 系統均不使用 |



## 採集與評分流程（標題優先）



為提高效率並減少無關正文抓取，**所有列表頁**均採用兩階段流程：



1. **列表階段：** 僅讀取主欄標題與鏈接；排除側邊欄、點擊排行、熱門文章、評論專欄入口。

2. **標題匹配：** 用 `01-scope-taxonomy.md` 關鍵詞與 `03-scoring-rules.md` 規則，對標題做預篩（宏觀/政策/專題相關、非個股短訊、非評論）。

3. **正文抓取：** **僅對標題通過預篩的候選** 點入 `article` 正文頁取全文；不通過者跳過，不逐篇爬取正文。



即時新聞列表更新頻繁，標題預篩尤其重要；要聞/地產列表同樣適用上述規則。



配置：`daily-brief-app/config/sources.yaml`（`title_prefilter`）、`daily-brief-app/config/keywords.yaml`。



## 篩選關鍵詞



固定入口：各報 **列表主欄**（見上表）。



| 專題 | 檢索詞 |

| --- | --- |

| 今日金融與經濟 | 財政、金融、利率、港股、經濟、PMI、貿易、金管局、立法會、政策、企業財政 |

| 建築與地產 | 地產、建築、樓市、成交、租金、酒店、商廈、改建、學生宿舍、啟德、北都 |

| 北都/洪水橋 | 北都、北部都會區、洪水橋、新田科技城、河套、產業園 |

| HKU學生宿舍 | 港大、學生宿舍、酒店改裝、商廈改裝、宿位 |

| 啟德交通 | 啟德、綠色智慧交通、集體運輸 |

| 樓市改建 | 深水埗、清水灣、改建、共居、呎租 |

| 新世界財政 | 新世界、11 SKIES、機管局、債務、融資 |



完整關鍵詞配置：`daily-brief-app/config/keywords.yaml`



## 來源擴展規則



- 四報 A 級來源由日報系統自動採集；評分與去重見 `03-scoring-rules.md`

- 補充 B 級來源須業務負責人確認後更新 `config/sources.yaml`

- 任何補充來源不得取代四報主口徑，只作查漏補缺


