# AGENTS.md — Universal AI Governance Template (v3.2)

Single source of truth for ALL AI coding agents (Claude Code, Antigravity, Codex, Cursor, ...).
Tool-specific files (`CLAUDE.md`, `.antigravity_rules.md`, `.cursor/rules/*.mdc`) only point here.
Project-agnostic: copy into any repo unchanged; only "Project Profile" and "Project Facts"
are filled per project.

## Project Profile (set once at bootstrap)

- Scale: `solo-small`          <!-- solo-small | solo-large | team — selects the Completion tier -->
- Spec file: `docs/spec.md`    <!-- mandatory; created by Bootstrap if missing -->

## Project Facts (agent-maintained — keep under 15 lines)

**Bootstrap**: if this section is empty or `docs/spec.md` is missing, read `docs/bootstrap.md`
and run it before anything else. Otherwise never open that file.

<!-- FILLED BY AGENT DURING BOOTSTRAP. Update whenever it drifts from reality.
     This repo is the template's own home: blank this section when copying AGENTS.md elsewhere. -->
- Spec source: docs/spec.md
- Stack: Markdown only (no runtime, no package manifest)
- Build / Test / Lint / Run: N/A — docs-only repo; verification is document review
- Key directories: `docs/` governance docs + templates + split procedures;
  `playbooks/` reusable cross-project playbooks (one folder each)

## Boundaries

- **NEVER**: force push or rewrite git history; print, log, or hardcode any API key,
  password, or personal data; run deploy/publish commands inside an agent session;
  delete, edit, or rewrite entries in `docs/change_log.md` / `docs/decision_log.md`
  (the only permitted move-out is the verbatim archive in `docs/log_rotation.md`);
  remove documentation or change records silently; add undocumented shortcuts,
  hidden dependencies, or magic values.
- **ASK FIRST**: delete files; add a third-party dependency; change database schema
  or file formats other tools depend on; any action outside the repo directory;
  any task that conflicts with `docs/spec.md` (scope creep or contradiction) —
  STOP and ask whether to update the spec first.
- **ALWAYS**: after code changes, run the Test command from Project Facts;
  state clearly when a change was NOT verified.

## Startup (once per session; re-run only if context was trimmed)

Run ONE command and work from its output. Do NOT open these files with a file reader;
do NOT read `docs/logs/`. Never infer project state from memory or chat history —
the repo docs are the context source; a fresh session must be able to continue without loss.

Git Bash / sh:
```
head -n 10 docs/project_status.md; echo ---; grep -E '^## ' docs/decision_log.md; echo ---; tail -n 30 docs/change_log.md; echo ---; wc -l < docs/change_log.md
```
PowerShell:
```
gc docs/project_status.md -TotalCount 10; '---'; (sls '^## ' docs/decision_log.md).Line; '---'; gc docs/change_log.md -Tail 30; '---'; (gc docs/change_log.md).Count
```

Then print exactly one line before starting the task:
`Startup OK | status: <first sentence of TL;DR> | decisions: <N titles> | change_log: <L> lines`

- L > 400 → read `docs/log_rotation.md` and run it before the task (the only time to open it).
- Any of the four docs missing → create it from `docs/templates.md` (the only time to open it).
- Open a full `decision_log.md` entry only when the task touches that area; never undo a
  recorded decision. History older than the last 30 lines → `grep` the active change_log
  by keyword; open `docs/logs/<year>.md` only if the task explicitly needs it.

## While Working

- Prefer incremental changes over large refactors; verify structural changes against
  `docs/decision_log.md` first.
- Bug fix: find the root cause → fix → verify. The root cause goes into the change_log summary.
- Refactor: confirm behavior is unchanged, assess compatibility/migration impact,
  record old vs. new design + risks (decision_log entry + change_log line).
- Before solving a new class of problem from scratch, check Reusable Playbooks below.

## Completion (tiered by Project Profile → Scale)

A task is NOT complete until its documentation tier is written. Any file created / deleted /
renamed, feature added / removed, or API / DB / architecture change requires it. No exceptions.

| Scale | change_log | project_status | decision_log | End-of-task report |
|---|---|---|---|---|
| solo-small | one line per task (grammar below) | TL;DR block only | architecture / API / DB / security / deploy changes only | the change_log line itself + the new TL;DR |
| solo-large | full entry (template in `docs/templates.md`) | affected sections | same trigger list | short report (format in `docs/templates.md`) |
| team | full entry | full update | same trigger list | full report (format in `docs/templates.md`) |

solo-small change_log grammar — one entry = one line, appended at the end, greppable:
`- YYYY-MM-DD | Feature|Fix|Refactor|Docs|Test | one-sentence summary (Fix: include root cause) | verify: <method> or NOT VERIFIED`

If the spec or project understanding changed, update `docs/spec.md` and "Project Facts" above.

## Source of Truth Priority

Source code > `docs/spec.md` > `docs/decision_log.md` > `docs/project_status.md` >
`docs/change_log.md` > conversation context. On conflict: verify the code first, then fix the docs.
Every project MUST have a `docs/spec.md`, even if only 10 lines.

## Reusable Playbooks

Tool-agnostic playbooks live in the template repo's `playbooks/` folder. In a repo that has
no `playbooks/`, they are at
`C:\Users\BASS000025\AppData\Local\Programs\Python\Python314\@project\@@MD規則\playbooks\`.
Read the entry file (`PLAYBOOK.md` or `SKILL.md`) in full before acting on it.

- Packaging a Python script for non-technical users, or antivirus false-positives on a
  compiled exe (Nuitka, PyInstaller, 打包成exe被防毒誤判, 趨勢科技)
  → `embeddable-python-packaging/PLAYBOOK.md`
- 讀取「地籍圖重測資料處理系統」重測原始檔、重建宗地環／面積(段目錄 `.Dxx`／`.NTX`,
  交換檔 `.PTM`／`.BNI`／`.CNT`／`.PAR`／`.BNP`／`.COA`,測量檔 `.MAC`／`.CTL`)
  → `resurvey-source-files/SKILL.md`

<!-- One line + path per playbook. -->
