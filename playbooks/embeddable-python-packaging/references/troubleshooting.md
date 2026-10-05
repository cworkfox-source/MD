# Troubleshooting — Embeddable Python Packaging

Read this when something in the main SOP doesn't work. Each section is a
real failure mode, its root cause, and the fix.

## `.bat` file fails with garbled "not recognized as an internal or
external command" errors

**Symptom**: double-clicking the launcher `.bat` produces a wall of
nonsense errors, often with fragments of real path names mixed into
garbage characters, e.g. broken pieces of "python_embed" or
"SCRIPT_PATH" appearing inside otherwise-unreadable strings.

**Root cause**: the `.bat` file was saved as UTF-8 and contains non-ASCII
text (e.g. Chinese echo messages), while the target system's default
console codepage is something else (e.g. Big5/950 on Traditional Chinese
Windows). Adding `chcp 65001` at the top does **not** fix this: that line
itself must first be parsed using the *old* codepage before it can take
effect, and during that parse, the multi-byte UTF-8 sequences that make up
the Chinese characters elsewhere in the file get misread byte-by-byte
under the old codepage, corrupting the byte alignment for every line that
follows — including lines that are otherwise pure ASCII (paths, variable
names). The result is that the whole batch file becomes unparseable.

**Fix**: keep the `.bat` file's internal text content 100% ASCII. Don't
use `chcp` at all. This is the only fix that's robust regardless of the
end user's Windows display language / system codepage — you often won't
know or control what codepage the recipient's machine defaults to.
`assets/start.bat.template` in this skill already follows this rule.

Note this only applies to the file's *content*. The file's *name* can
freely use non-ASCII characters (e.g. `啟動.bat`) — Windows/NTFS file names
are Unicode-safe, and this is a completely separate mechanism from how
`cmd.exe` parses the bytes inside the file.

**How to verify before shipping**: run `file start.bat` (or equivalent) —
it should report `ASCII text`, not `UTF-8 Unicode text` or `Unicode text,
UTF-8 text`. If Chinese/emoji output is still wanted somewhere, put it in
the Python script's own `print()` calls instead — Python's console output
on Windows uses a wide-character API (`WriteConsoleW`) for real consoles
and handles Unicode (including emoji) correctly regardless of the active
codepage, completely independent of how `.bat` files are parsed.

## Packages installed with pip can't be imported (`ModuleNotFoundError`)
even though `pip install` reported success

**Root cause**: the `python<XXX>._pth` file still has `import site`
commented out, and/or is missing the `Lib\site-packages` path entry. The
embeddable package disables the `site` module and restricts `sys.path` to
exactly what's listed in `._pth` unless you explicitly re-enable it — this
is by design (it's meant to be usable as an isolated, minimal runtime), but
it means a default, unmodified `._pth` file will silently ignore anything
pip installs.

**Fix**: edit `python<XXX>._pth`, uncomment `#import site` → `import site`,
and add a line with `Lib\site-packages`. See Step 2 in SKILL.md.

## `python.exe` fails to start at all on the target machine, or a `.pyd`
import fails with a missing DLL error

**Root cause**: the target machine is missing the Visual C++ runtime DLLs
(`vcruntime140.dll` / `vcruntime140_1.dll`) that `python.exe` and many
compiled extension modules depend on. Most Windows installations already
have these (they're an extremely common dependency), but very minimal,
locked-down, or freshly-imaged machines sometimes don't.

**Fix**: copy `vcruntime140.dll` and `vcruntime140_1.dll` from your own
`C:\Windows\System32\` into the `python_embed\` folder, right next to
`python.exe`. Cheap insurance, no downside.

## `import tkinter` fails

**Root cause**: the official Embeddable Package deliberately strips out
`tcl`/`tk` (the GUI toolkit tkinter depends on) to keep the download small.
It is not included by default and there's no `pip install` for it since
it's a bundled native library, not a PyPI package.

**Fix options**, roughly in order of effort:
1. Manually copy the `tcl`/`tk` DLLs and library folders from a full
   (non-embeddable) Python install of the same version into
   `python_embed\` — works but is fiddly and version-sensitive.
2. If the GUI need is simple, consider swapping tkinter for a pure-Python
   or web-based UI approach instead of fighting the embeddable package.
3. If the project truly needs a rich native GUI, this may be a sign this
   project doesn't fit this packaging method — reconsider Nuitka
   `--standalone` (folder mode, not `--onefile`) with a code-signing
   certificate instead.

## A dependency has a `.pyd`/C extension with no matching wheel

**Root cause**: some packages ship compiled extensions and only publish
pre-built wheels for specific Python version + platform combinations. If
`pip install` on the embeddable interpreter tries to build from source
(you'll see it invoke a compiler, or fail outright because there's no
compiler available), that package doesn't have a wheel for this exact
combination.

**Fix**: check `references/compatibility-check.md` for how to verify wheel
availability before starting. If no wheel exists, this packaging method
isn't a good fit for that dependency — either find an alternative package,
pin to an older version of the dependency that does have a wheel, or fall
back to a different packaging strategy for this project.

## Antivirus still flags the `.bat` or `python.exe` at runtime

**Root cause**: this method eliminates the *static* red flags (unsigned,
self-extracting, high-entropy single exe), but a behavior-monitoring AV can
still flag *what the program actually does* — e.g. driving a browser
automatically, simulating clicks, or other automation patterns that
overlap with malware techniques regardless of how it's packaged.

**Fix**: there is no way to fully eliminate this risk through packaging
alone. Prepare a short, plain-language instruction sheet for end users on
how to add the tool's folder to their antivirus's exception/allow list —
this is the most reliable practical mitigation, and should be considered
part of the deliverable, not an afterthought.
