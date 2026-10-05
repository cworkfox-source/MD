# Documentation Templates

Load this file ONLY when creating a missing doc file. Do not load it on every session.

## Template: docs/spec.md (MANDATORY — created via Bootstrap Step 0 interview)

```markdown
# 專案規格

## 目標(一句話)
<!-- 完成後使用者會用它做什麼 -->

## 輸入 / 輸出
<!-- 資料來源(檔案/網站/API)→ 最終產物(格式/畫面/報表) -->

## 驗收條件(每條都必須可實際驗證)
<!-- 例:headless 模式下能截到含地籍圖層的完整截圖 -->
1.

## 不做什麼(明確排除範圍,防止過度工程)
-

## 環境限制
<!-- OS、Python/Node 版本、不能安裝的東西、機敏資料限制 -->
-

## 未確認假設(agent 標註,待使用者確認後移除)
- [假設]
```

Rules: agent may only fill "未確認假設" without asking; all other sections
require user input or explicit user confirmation. When an assumption is
confirmed, move it into the proper section and delete the `[假設]` tag.

## Template: docs/project_status.md

```markdown
# Project Overview

## Current State TL;DR (max 5 lines — Startup reads ONLY this block)
<!-- 現在做到哪、下一步是什麼、有無 blocker。Startup 用 head -n 10 讀:此區塊必須在檔案前 10 行內 -->

## Current Version
## Project Goals
## Core Features
## Completed Features
## Features In Development
## Planned Features
## Known Issues
## Technical Architecture
## Data Structure
## API Structure
## Deployment Process
## Dependencies
## Future Roadmap
```

Rules: always reflect actual implementation; remove obsolete information;
the TL;DR block MUST be updated after every task; other sections per Scale tier.

## Template: docs/change_log.md (append-only, rotated per `docs/log_rotation.md`)

### Scale `solo-small` (default) — one task = one line, appended at the end

```markdown
# Change Log (append-only)

> Older entries: docs/logs/ (archive, do not load at startup)

- YYYY-MM-DD | Fix | 修正登入 selector 失效(根因:網站改版換了 id) | verify: pytest tests/test_login.py PASS
- YYYY-MM-DD | Docs | 補 README 安裝步驟 | verify: NOT VERIFIED
```

Grammar (greppable, no exceptions):
`- YYYY-MM-DD | Feature|Fix|Refactor|Docs|Test | one-sentence summary (Fix: include root cause) | verify: <method> or NOT VERIFIED`

### Scale `solo-large` / `team` — one task = one entry

```markdown
## YYYY-MM-DD HH:MM

### Type
Feature | Fix | Refactor | Docs | Test

### Summary
### Files Changed
### Reason
### Implementation Details
### Impact Analysis
### Verification Result
PASS / FAIL / PARTIAL
```

Rules: preserve history forever; **each field max 3 lines** — logs are indexes, not essays.

## Template: End-of-task report (solo-large / team only; solo-small = the change_log line + new TL;DR)

```
Task Summary:
Files Modified:
Documents Updated:
Tests Performed:
Known Risks:
Recommended Next Steps:
```

solo-large: fill only the lines that apply. team: fill every line.

## Template: docs/logs/change_log_YYYY.md (rotation archive)

```markdown
# Change Log Archive — YYYY

> Rotated out of docs/change_log.md per docs/log_rotation.md.
> Entries below are verbatim, in original order. Do not edit.
```

Rules: append-only; entries moved here must be byte-identical to the
originals; one file per calendar year; never loaded at Startup.

## Template: docs/decision_log.md

```markdown
## Decision ID — <short title (Startup reads titles only)>

### Date
### Topic
### Context
### Alternatives Considered
### Selected Solution
### Reason
### Consequences
### Future Review Conditions
```

Required for: architecture, database, API, framework selection, major refactoring,
security strategy, deployment strategy.

## Template: README.md (optional, hand-over safety only)

```markdown
# <專案名稱>

<一句話目的>

規格與使用方式見 `docs/spec.md`;AI agent 規則見 `AGENTS.md`。
```
