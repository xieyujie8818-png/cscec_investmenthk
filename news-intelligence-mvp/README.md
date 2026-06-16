# 海外投資部行業新聞篩選與推送MVP

本目錄是一套可直接試運行的MVP交付物，用於支持海外投資部每日 HKET 新聞篩選、**《香港簡訊》** 編制、飛書推送及月報素材沉澱。

## 使用順序

1. 先閱讀 `01-scope-taxonomy.md`，確認固定專題、日報三欄目和推送對象。
2. 按 `02-source-list.md` 使用固定 HKET 來源。
3. 按 `03-scoring-rules.md` 對候選新聞做內部評分（不對外展示）。
4. 按 `04-daily-pilot-runbook.md` 每日運行（參考6月2日試點節奏）。
5. 用 `templates/daily-leadership-brief.md` 編制呈領導的完整日報。
6. 用 `templates/daily-feishu-digest.md` 發送飛書群簡訊（**不含月報素材標記**）。
7. 用 `templates/daily-internal-monthly-markers.md` 發送市場部負責日報/月報的同事。
8. 與IT按 `05-feishu-it-requirements.md` 對接飛書機器人。
9. 月報撰寫時參考 `07-monthly-insight-method.md` 與素材池（無單獨月報Word模板文件）。
10. **Agent 自動編制：** 見 `08-daily-agent-workflow.md`，每日複製 `templates/agent-daily-prompt.md` 到 Cursor 對話執行。

## 每日交付物（雙軌）

| 文件 | 用途 | 發給誰 |
| --- | --- | --- |
| `daily-leadership-brief.md` | 《香港簡訊》完整稿（目錄錨點+摘要+原文全文） | 領導呈報 / 部門存檔 |
| `daily-feishu-digest.md` | 飛書群短訊 | 部門同事（眾人） |
| `daily-internal-monthly-markers.md` | 月報素材與跟進 | 市場部負責日報月報者 |

## MVP原則

- 先人工可控，再逐步自動化。
- 先保證內容準確和對業務有用，再追求覆蓋量。
- 固定專題 + 固定四報列表來源；對外日報欄目固定為【金融與經濟】【建築與地產】【北都專題】。
- 定稿約 **15–20 條**；正文為原文全文照錄；對外產出不含原文鏈接。

## 建議試點節奏

- 每日編制時間約30-45分鐘。
- 對外簡訊約 **15–20 條**（去重、評分≥70）。
- 每週復盤一次命中率與HKET有效版面。
- 月報由市場部負責人從素材池整理，方法見 `07-monthly-insight-method.md`。
