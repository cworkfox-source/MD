"""
Smoke test template for an Embeddable Python Package build.

Run this with the embedded interpreter itself, NOT your dev-machine venv:

    python_embed\\python.exe scripts\\smoke_test.py

Edit the IMPORTS list below to match every top-level import your actual
project script uses (copy them straight from the top of the file), then
run this before shipping. A clean run here catches the two most common
embeddable-package failures: (1) forgot to enable `import site` /
`Lib\\site-packages` in the ._pth file, so nothing installed via pip can be
found, and (2) a dependency got pruned during the size-reduction cleanup
step that turned out to be needed at runtime after all.
"""
import importlib
import sys

# Replace with your project's actual imports, e.g.:
# IMPORTS = ["selenium", "selenium.webdriver", "requests"]
IMPORTS = [
    # "your_package_here",
]

failed = []
for name in IMPORTS:
    try:
        importlib.import_module(name)
        print(f"OK   {name}")
    except Exception as e:
        print(f"FAIL {name}: {e}")
        failed.append(name)

if failed:
    print(f"\n{len(failed)} import(s) failed: {failed}")
    sys.exit(1)

print("\nAll imports OK.")

# --------------------------------------------------------------------
# Optional: if the project drives a browser via Selenium, uncomment this
# block to also confirm Selenium Manager can auto-resolve a matching
# chromedriver and actually launch/close Chrome. This is the step that
# proves the whole embeddable-package + selenium combination works, not
# just that the import succeeds.
# --------------------------------------------------------------------
# from selenium import webdriver
# options = webdriver.ChromeOptions()
# options.add_experimental_option("excludeSwitches", ["enable-automation"])
# options.page_load_strategy = "eager"
# driver = webdriver.Chrome(options=options)
# print("Chrome launched, version:", driver.capabilities.get("browserVersion"))
# driver.quit()
# print("Chrome closed cleanly.")
