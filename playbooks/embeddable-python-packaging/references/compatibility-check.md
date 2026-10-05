# Compatibility Check — does this project fit this packaging method?

Run this check before starting the SOP in SKILL.md, so you don't discover
a blocker halfway through.

## Step 1: enumerate third-party dependencies

If the project has a `venv`, list what's actually installed and filter out
the packaging tooling that isn't a real runtime dependency:

```
ls venv/Lib/site-packages | grep -viE '^(pip|setuptools|wheel|_distutils_hack|pkg_resources|distutils-precedence)'
```

If there's a `requirements.txt` or `pyproject.toml`, cross-check against
that too — a venv can accumulate packages that aren't actually imported by
the project.

Preferred: run this check against the clean `venv_pack` created in SOP
step 3 of `PLAYBOOK.md` (a fresh venv holding only the deps the program
actually imports), not the day-to-day development venv — the dev venv
over-reports, and only `venv_pack` reflects what will really be shipped.

## Step 2: find compiled extensions

```
find venv/Lib/site-packages -iname "*.pyd"
```

Every `.pyd` file belongs to some package that has a compiled component.
Pure-Python packages (the vast majority of small/medium dependencies —
`requests`, `urllib3`, `attrs`, most `selenium` transitive deps, etc.)
won't show up here at all, which is the easy case.

For each package that *does* show up:
- Note the filename pattern, e.g. `_cffi_backend.cp311-win_amd64.pyd` —
  the `cp311-win_amd64` part is the ABI tag: CPython 3.11, Windows amd64.
- This tells you pip will need a wheel tagged `cp311-win_amd64` (or a
  compatible `abi3`/universal tag) for that package on PyPI. As long as
  the embeddable package you download matches the same major.minor
  (e.g. also 3.11.x) and same architecture (amd64), pip will find and
  download that exact pre-built wheel — no local compilation needed.

## Step 3: spot-check wheel availability (only needed for less common
packages)

For mainstream packages (cffi, cryptography, numpy, pandas, pillow, lxml,
grpcio, etc.) pre-built Windows wheels are essentially guaranteed for any
actively-supported Python version. For obscure or narrowly-maintained
packages, check the project's PyPI page → "Download files" for that
version, and look for a `.whl` filename containing `win_amd64` (or
`win32`) and the right `cpXXX` tag. If all you see is a `.tar.gz` source
distribution with no matching wheel, that package will try to compile
from source on `pip install` — which will fail on the embeddable
interpreter (no compiler, no build tooling by design).

## Step 4: GUI framework check

- **No GUI / pure console script**: ideal case, proceed with the SOP as-is.
- **tkinter**: not included in the embeddable package by default. See the
  tkinter section in `references/troubleshooting.md`.
- **PyQt5/PyQt6/PySide2/PySide6**: these ship substantial pre-built wheels
  and generally do work via `pip install`, but expect the resulting folder
  to be much larger (tens to 100+ MB) and budget extra smoke-testing time,
  since Qt has more moving native parts than a typical console-script
  dependency stack.
- **wxPython, Kivy, etc.**: check wheel availability per Step 3; these are
  less universally pre-built than Qt and more likely to need source builds
  on less common Python versions.

## Step 5: runtime network dependencies

Some libraries download or manage external binaries at runtime, separate
from `pip install` (Selenium's `selenium-manager` auto-fetching
`chromedriver` is the example this skill was originally built around).
This isn't a blocker, but note it in the deliverable's documentation: the
target machine needs internet access on first run for that specific
library's own auto-download step, independent of whatever the main
program itself does over the network.

## Decision

- **All dependencies pure Python, or all compiled deps have matching
  wheels** → proceed with the SOP in `SKILL.md`, no caveats.
- **One or more compiled deps have no matching wheel for the target
  Python version/platform** → this method won't work for that dependency
  as-is. Options: pin to an older version of the dependency that does
  have a wheel, replace it with an alternative package, or fall back to
  a different packaging strategy (e.g. Nuitka `--standalone` folder mode
  with a purchased code-signing certificate) for this specific project.
- **Uses a GUI framework not covered above** → research that specific
  framework's embeddable-package compatibility before committing to this
  approach; don't assume it'll work by analogy to tkinter or Qt.
