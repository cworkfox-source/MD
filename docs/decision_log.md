# Decision Log

Required for: architecture, database, API, framework selection, major refactoring,
security strategy, deployment strategy. Append entries using the template in
`docs/templates.md`.

## D-001 — v3.3: 規則採負向約束、工具層強制、只記不可推得事實

### Date
2026-10-05

### Topic
AGENTS.md 治理範本依 2026 年實證研究與工具原生支援修訂。

### Context
- Gloaguen et al. (ETH, arXiv 2602.11988):context file 使推論成本增加 20% 以上;
  LLM 產生的檔案略降成功率,人寫的只有微幅改善。建議只寫最小必要要求。
- Guardrails Beat Guidance (arXiv 2604.11088):個別有益的規則全是負向約束
  ("do not refactor unrelated code"),有害的都是正向指示("follow code style")。
- Instruction Adherence factorial study (arXiv 2605.10039, 1,650 sessions):
  檔案長度/位置/架構無穩定效果;遵循率隨 session 推進下降(每步 OR≈0.944)。
- Two-agent ablation (arXiv 2607.27250):context file 對正確率無可測影響。
- Rule Taxonomy study (arXiv 2606.12231):規則更新後產物遵循率 49%→72%;
  開發者多以新增負向約束修正 AI 錯誤。
- Claude Code 官方文件:CLAUDE.md 是 context 而非強制設定,要強制請用 hook;
  v2.1.277+ 在無 CLAUDE.md 時原生讀 AGENTS.md,既有 `@AGENTS.md` 匯入可保留。
- Antigravity 1.20.3(2026-03-05)起原生讀 AGENTS.md;Cursor 現行版本亦自動載入。

### Alternatives Considered
1. 維持 v3.2 不動。
2. 大幅擴寫 AGENTS.md(加入架構概覽、風格指南)。
3. 小幅修訂:加 ENFORCE、負向約束、內容規則、壓縮後重跑、完成前重讀。

### Selected Solution
方案 3。AGENTS.md 仍約 120 行,遠低於 Claude Code 建議的 200 行。

### Reason
研究一致指出:內容越少越好、負向約束有效、文字規則會隨 session 衰退。
方案 2 與證據相反;方案 1 漏掉可低成本取得的改善。

### Consequences
- 下游專案需自行設定 permission deny / hook / CI 以強制 NEVER 項目
  (本 repo 依 spec 不提供自動化工具)。
- 指標檔降為備援;`.antigravity_rules.md` 可能已無作用,待使用者決定是否刪除。

### Future Review Conditions
出現與上述結論相反的對照實驗;或各工具改變 AGENTS.md 載入行為時重新檢視。
