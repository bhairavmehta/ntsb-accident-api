"""Build the web UI: inlines synthetic demo data into the template.

Writes ntsb_api/static/index.html (served at / by the API) and dist/explorer-preview.html
(a standalone preview fragment that runs entirely on the synthetic sample data).
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ntsb_api.mock import MOCK_CASES  # noqa: E402
from ntsb_api.normalize import normalize_case  # noqa: E402

tpl = (ROOT / "scripts/ui_template.html").read_text()
demo = [normalize_case(c, include_raw=False) for c in MOCK_CASES]
for d in demo:
    d.pop("links", None)
body = tpl.replace("__DEMO_DATA__", json.dumps(demo, separators=(",", ":")).replace("</", "<\\/"))
page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '</head>\n<body>\n' + body + '\n</body>\n</html>\n')
(ROOT / "ntsb_api/static/index.html").write_text(page)
(ROOT / "dist").mkdir(exist_ok=True)
(ROOT / "dist/explorer-preview.html").write_text(body)
print("built", len(page), "bytes")
