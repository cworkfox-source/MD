# Log Rotation (archive ≠ delete)

> Split out of `AGENTS.md` so it is not loaded every session.
> Read this file ONLY when the trigger below actually fires.

Keeps the active `docs/change_log.md` small enough to read in full every
session, while preserving history forever in archive files.

- **Trigger**: active `docs/change_log.md` exceeds **400 lines**
  (the line count `L` printed by the Startup command).
- **Entry** = one `## ` heading block (full format) or one `- YYYY-MM-DD |` line (solo-small).
- **Action**: move ALL entries except the **newest 10** into
  `docs/logs/change_log_<YYYY>.md`, where `<YYYY>` is the year of the moved
  entries (create the folder/file if missing; if moved entries span years,
  split them into one archive file per year). Append to the end of the
  archive, keeping original order.
- **Mechanical move only**: archived entries must remain **byte-identical** —
  no editing, summarizing, merging, or reordering. Rotation relocates
  history; it never rewrites it.
- **Pointer line**: the active file's header must contain
  `> Older entries: docs/logs/ (archive, do not load at startup)`.
- **Record it**: log the rotation itself as a 1-line change_log entry
  (e.g. `- YYYY-MM-DD | Docs | Rotated N entries to docs/logs/change_log_2026.md | verify: wc -l`).
- **Scope**: applies to `change_log.md` ONLY. `decision_log.md` is never
  rotated — its titles are the permanent index and must stay in one file.
  `project_status.md` does not accumulate (obsolete content is removed, not
  appended), so it needs no rotation.
