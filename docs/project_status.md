# Project Overview

## Current State TL;DR (max 5 lines — Startup reads ONLY this block)
治理範本 v3.2:Startup 改為單一指令 + 回執行(Git Bash / PowerShell 兩版)、
change_log 只讀最後 30 行、AGENTS.md 去重、solo-small 改一行文法、
指標檔改為「已在 context 就不重讀」、playbooks 補範本 repo 絕對路徑。
已註冊 playbook 兩個(embeddable-python-packaging、resurvey-source-files)。
無 blocker;下一步:在下游 repo 實跑一次驗證回執與工具呼叫次數。

## Current Version
AGENTS.md governance template v3.2

## Project Goals
Single source of truth for AI-agent governance rules (`AGENTS.md`), plus reusable
cross-project playbooks under `playbooks/`. Docs-only repo — no runnable code.

## Core Features
- `AGENTS.md` — universal governance template, copied unchanged into other repos
- `playbooks/embeddable-python-packaging/` — packaging playbook (PLAYBOOK.md,
  references/compatibility-check.md, references/troubleshooting.md,
  assets/start.bat.template, scripts/smoke_test.py)
- `playbooks/resurvey-source-files/` — 台灣地籍重測原始檔讀取 playbook
  (SKILL.md, references/ ×4, file_formats/ 欄位表, scripts/read_resurvey.py)
- `docs/templates.md` — templates for the governance doc files
- `docs/bootstrap.md`, `docs/log_rotation.md` — conditional procedures split
  out of `AGENTS.md` so they are not loaded every session

## Completed Features
- Packaging playbook now mandates a clean throwaway venv (`venv_pack`) to lock
  the dependency list (`requirements-embed.txt`) so only necessary components
  are shipped (2026-07-06).

## Features In Development
(none)

## Planned Features
(none)

## Known Issues
(none)

## Technical Architecture
Markdown documents only. `CLAUDE.md` / `.antigravity_rules.md` /
`.cursor/rules/000-agents-md-entry.mdc` are thin pointers to `AGENTS.md`.
`AGENTS.md` keeps only always-needed rules inline; Startup is a single shell
command whose output is the whole session context. Conditional procedures
(`docs/bootstrap.md`, `docs/log_rotation.md`) and all templates
(`docs/templates.md`) are read only when their trigger condition holds.

## Data Structure
N/A

## API Structure
N/A

## Deployment Process
Copy `AGENTS.md` (and needed playbooks) into target repos.

## Dependencies
None.

## Future Roadmap
Add more playbooks as recurring problems get solved.
