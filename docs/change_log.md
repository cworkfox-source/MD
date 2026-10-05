# Change Log (append-only)

> Older entries: docs/logs/ (archive, do not load at startup)

## 2026-07-06 00:00

### Type
Docs

### Summary
Initialized governance docs (project_status / change_log / decision_log) from
`docs/templates.md`, and filled the "Project Facts" section of `AGENTS.md`.

### Files Changed
- docs/project_status.md (created)
- docs/change_log.md (created)
- docs/decision_log.md (created)
- AGENTS.md (Project Facts filled)

### Reason
AGENTS.md Bootstrap / Startup procedure requires these files; they were missing.

### Implementation Details
Created from the templates in `docs/templates.md`, content derived from the
actual repo contents (docs-only template repo, no build/test commands).

### Impact Analysis
Documentation only; no behavior change.

### Verification Result
PASS

## 2026-07-06 00:10

### Type
Docs

### Summary
Packaging playbook now requires a clean venv to lock dependencies, so only
necessary components are installed into the embeddable Python distribution.

### Files Changed
- playbooks/embeddable-python-packaging/PLAYBOOK.md
  - Step 3 rewritten: create throwaway `venv_pack`, install only the direct
    dependencies actually imported by the shipped source, `pip freeze` to
    `requirements-embed.txt`, and install into `python_embed` exclusively via
    `pip install -r requirements-embed.txt` (never by copying the dev venv or
    global site-packages, never ad-hoc installs).
  - Step 0 folder layout now includes `requirements-embed.txt`.
- playbooks/embeddable-python-packaging/references/compatibility-check.md
  - Step 1 now says to run the dependency/.pyd checks against `venv_pack`
    instead of the day-to-day development venv.

### Reason
User request: packaging must go through a venv so only necessary components
are bundled. Dev venvs and the global environment accumulate unused packages;
copying them bloats the distribution.

### Implementation Details
See PLAYBOOK.md step 3 (sub-steps 3-1 to 3-4).

### Impact Analysis
Affects future packaging sessions in any repo using this playbook; no impact
on already-shipped distributions.

### Verification Result
PASS (document review; no executable code in this repo)

## 2026-07-27 13:30

### Type
Docs

### Summary
Split the two conditional procedures out of `AGENTS.md` into `docs/bootstrap.md`
and `docs/log_rotation.md`, filled Project Facts / Scale, created the mandatory
`docs/spec.md`, and corrected stale content in `docs/project_status.md`.

### Files Changed
- AGENTS.md (Bootstrap + Log Rotation replaced by pointers; Project Facts and
  Profile Scale filled)
- docs/bootstrap.md, docs/log_rotation.md (created — verbatim moved sections)
- docs/spec.md (created), docs/project_status.md, docs/change_log.md (header)

### Reason
`AGENTS.md` loaded ~2.4k est. tokens every session including two sections needed
only on first-run / >400-line conditions. Empty Project Facts + missing
`docs/spec.md` also made every session trigger Bootstrap. Correction: the
2026-07-06 entry above stated Project Facts was filled; it was not — filled now.

### Implementation Details
Moved sections are byte-identical inside the new files; kept as plain docs (not
Claude skills) because AGENTS.md must stay readable by Codex/Cursor/Antigravity.

### Impact Analysis
~833 est. tokens/session less always-loaded context. No rule was removed or
weakened; conditional rules now load on demand.

### Verification Result
PASS (document review; no executable code in this repo)

## 2026-08-28

- Docs: 將既有的 `playbooks/resurvey-source-files/`(地籍重測原始檔讀取 skill)註冊進 `AGENTS.md` 的 Reusable Playbooks 清單;入口檔命名放寬為 `PLAYBOOK.md` / `SKILL.md`;把 SKILL.md 與 references/ 內指向來源專案的 `docs/file_formats/`、`.claude/skills/...` 路徑改為 playbook 相對路徑,其餘來源專案路徑加註說明;同步更新 `docs/spec.md` 驗收條件 2 與 `docs/project_status.md`。驗證:文件審閱(本 repo 無可執行程式)。
- Chore: 刪除 `playbooks/resurvey-source-files/scripts/__pycache__/read_resurvey.cpython-314.pyc`(編譯殘留,無任何文件引用)。驗證:全 repo grep 無殘留引用。

- 2026-09-02 | Docs | 治理範本 v3.1→v3.2:Startup 改單一指令+回執、change_log 只讀 tail 30、AGENTS.md 去重、solo-small 一行文法、指標檔不重讀、playbooks 補絕對路徑;templates/log_rotation/project_status 同步,歷史未改 | verify: Startup 指令(bash)實跑 PASS、全 repo grep 無舊節名殘留、文件審閱
- 2026-10-05 | Docs | 初始化本機 Git 儲存庫並連線至遠端 GitHub (https://github.com/cworkfox-source/MD.git)，推送 main 分支 | verify: git push -u origin main PASS

