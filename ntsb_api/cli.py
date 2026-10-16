"""Command line interface.

    ntsb search --make Boeing --airline-only --from 2020-01-01 --limit 10
    ntsb case DCA24MA063
    ntsb report DCA24MA063 -o report.pdf
    ntsb docket DCA24MA063 --download ./docs
    ntsb export --make Airbus --airline-only -o airbus.csv
    ntsb serve --port 8000
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

from .client import NTSBClient
from .normalize import normalize_case
from .query import CaseFilters


def _filters(a: argparse.Namespace) -> CaseFilters:
    return CaseFilters(
        text=a.text, make=a.make, model=a.model, operator_name=a.operator, state=a.state,
        ntsb_number=a.ntsb, probable_cause=a.cause, finding=a.finding,
        date_from=date.fromisoformat(a.date_from) if a.date_from else None,
        date_to=date.fromisoformat(a.date_to) if a.date_to else None,
        highest_injury=a.injury, airline_only=a.airline_only,
    )


def _add_filters(p: argparse.ArgumentParser) -> None:
    p.add_argument("--text", help="free text in factual narrative")
    p.add_argument("--make"); p.add_argument("--model"); p.add_argument("--operator")
    p.add_argument("--state"); p.add_argument("--ntsb", help="NTSB number contains")
    p.add_argument("--cause", help="text in probable cause"); p.add_argument("--finding")
    p.add_argument("--from", dest="date_from"); p.add_argument("--to", dest="date_to")
    p.add_argument("--injury", choices=["Fatal", "Serious", "Minor", "None"])
    p.add_argument("--airline-only", action="store_true", help="14 CFR Part 121 only")


async def _run(a: argparse.Namespace) -> int:
    async with NTSBClient() as c:
        if a.cmd == "search":
            page = await c.search(_filters(a).to_rules(), limit=a.limit, offset=a.offset)
            if a.json:
                print(json.dumps(page, indent=1, default=str)); return 0
            print(f"{page['total']} matching cases (showing {len(page['items'])})\n")
            for x in page["items"]:
                print(f"{x['ntsb_number'] or '-':<14} {x['event_date'] or '':<10}  "
                      f"{(x['make'] or '')[:10]:<10} {(x['model'] or '')[:12]:<12} "
                      f"{(x['city'] or '')[:16]:<16} {x['state'] or '':<3} {x['highest_injury'] or ''}")
        elif a.cmd == "case":
            case = await c.get_case(a.ntsb_number)
            if not case:
                print("not found", file=sys.stderr); return 1
            case.pop("raw", None)
            print(json.dumps(case, indent=1, default=str))
        elif a.cmd == "report":
            case = await c.get_case(a.ntsb_number)
            if not case or not case.get("mkey"):
                print("case not found", file=sys.stderr); return 1
            out = Path(a.output or f"{a.ntsb_number.upper()}.pdf")
            with out.open("wb") as fh:
                async for chunk in await c.stream_report_pdf(case["mkey"]):
                    fh.write(chunk)
            print(f"saved {out}")
        elif a.cmd == "docket":
            d = await c.docket(a.ntsb_number)
            for i, it in enumerate(d["items"], 1):
                print(f"{i:>3}. {it['title']}  [{it['file_type'] or '?'}]  {it['url']}")
            if d["note"]:
                print(d["note"])
            if a.download:
                folder = Path(a.download); folder.mkdir(parents=True, exist_ok=True)
                for i, it in enumerate(d["items"], 1):
                    r = await c._request("GET", it["url"])
                    name = f"{i:03d}_{''.join(ch if ch.isalnum() else '_' for ch in it['title'])[:80]}"
                    (folder / f"{name}.{(it['file_type'] or 'bin').lower()}").write_bytes(r.content)
                print(f"downloaded {len(d['items'])} files to {folder}")
        elif a.cmd == "export":
            rules = _filters(a).to_rules()
            out = Path(a.output)
            if out.suffix.lower() == ".json":
                cases = [normalize_case(r, include_raw=False) for r in await c.export(rules, limit=a.limit)]
                out.write_text(json.dumps(cases, indent=1, default=str))
            else:
                out.write_bytes(await c.export_csv(rules, limit=a.limit))
            print(f"saved {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ntsb", description="NTSB aviation accident data")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); _add_filters(s)
    s.add_argument("--limit", type=int, default=25); s.add_argument("--offset", type=int, default=0)
    s.add_argument("--json", action="store_true")
    sub.add_parser("case").add_argument("ntsb_number")
    r = sub.add_parser("report"); r.add_argument("ntsb_number"); r.add_argument("-o", "--output")
    d = sub.add_parser("docket"); d.add_argument("ntsb_number"); d.add_argument("--download", metavar="DIR")
    e = sub.add_parser("export"); _add_filters(e)
    e.add_argument("-o", "--output", default="ntsb_export.csv"); e.add_argument("--limit", type=int, default=500)
    sv = sub.add_parser("serve"); sv.add_argument("--host", default="127.0.0.1"); sv.add_argument("--port", type=int, default=8000)
    a = ap.parse_args(argv)
    if a.cmd == "serve":
        import uvicorn
        uvicorn.run("ntsb_api.server:app", host=a.host, port=a.port)
        return 0
    return asyncio.run(_run(a))


if __name__ == "__main__":
    raise SystemExit(main())
