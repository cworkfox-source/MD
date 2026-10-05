# Bootstrap (first session in a new project)

> Split out of `AGENTS.md` so it is not loaded every session.
> Read this file ONLY when "Project Facts" in `AGENTS.md` is empty,
> or when `docs/spec.md` is missing.

## Step 0 — Requirements Interview (when spec is missing or goals are unclear)

If `docs/spec.md` does not exist, OR the user's stated goal is vague
(e.g. "幫我做一個抓資料的工具" without input/output/acceptance criteria):

**Do NOT start coding. Do NOT invent requirements. Interview the user first.**

Ask in the user's language, ONE ROUND at a time, max 3 questions per round,
prefer multiple-choice options over open questions. Cover, in this order:

1. **目標**:這個專案完成後,你會用它做什麼?一句話描述。
2. **輸入/輸出**:資料從哪裡來(檔案/網站/API)?最終產物是什麼(檔案格式/畫面/報表)?
3. **驗收條件**:怎樣算「做完了」?請給至少 1 個可實際驗證的條件。
4. **明確排除**:有什麼是這個專案「不做」的?(防止過度工程)
5. **環境限制**:執行環境(OS)、不能安裝的東西、機敏資料限制。
6. **規模判定**:單人小工具 / 單人長期專案 / 多人協作?(填入 Project Profile 的 Scale)

Stop asking as soon as items 1–3 are answered clearly; items 4–6 may be filled
with marked assumptions (`[假設]` prefix) that the user can correct later.

Then: create `docs/spec.md` from the template in `docs/templates.md`,
show it to the user for confirmation, and only proceed after confirmation.

## Step 1 — Fill Project Facts

1. Read `docs/spec.md` (now guaranteed to exist).
2. Fill in the "Project Facts" section of `AGENTS.md` from the spec and the actual codebase.
   **Verify every command by actually running it. Record the full command WITH flags**
   (e.g. `pytest tests/test_scraper.py -v`, not just `pytest`). Never guess.
3. If a command cannot be determined or verified, ASK the user — never invent facts.
4. Create `docs/project_status.md`, `docs/change_log.md`, `docs/decision_log.md`
   from `docs/templates.md` if missing, and log the initialization in the change log.
5. (Optional, recommended for hand-over safety) Create a 5-line `README.md`:
   one-sentence purpose + "See docs/spec.md and AGENTS.md". Nothing more.
