# NTSB Aviation Accident API

A typed REST API, Python client, CLI, MCP tool server and interactive web UI over the
NTSB's public aviation investigation data (CAROL, report PDFs, public dockets).

```
             ┌──────────────── ntsb-accident-api ────────────────┐
 Browser UI ─┤  FastAPI  /api/v1/*   (OpenAPI → /docs, /redoc)    │
 CLI (ntsb) ─┤  NTSBClient: payload builder · retries · pacing ·  ├──► data.ntsb.gov
 MCP agents ─┤  TTL cache · normalizer · docket parser            │    • carol-main-public/api/Query/{Main,FileExport}
             └────────────────────────────────────────────────────┘    • carol-repgen/api/Aviation/ReportMain/.../pdf
                                                                         • Docket/?NTSBNumber=...
```

## Quick start

```bash
pip install -e ".[dev]"          # add ,mcp for the MCP server
ntsb serve                        # → http://127.0.0.1:8000  (UI), /docs (Swagger), /redoc
NTSB_MOCK=1 ntsb serve            # offline: built-in synthetic data, no NTSB calls
pytest                            # runs against mocked NTSB responses
```

Docker: `docker build -t ntsb-api . && docker run -p 8000:8000 ntsb-api`

## Deploying on localhost

Requires Python 3.10+ (or Docker). Commands are shown for Windows PowerShell; on
macOS/Linux use `source .venv/bin/activate` and `.venv/bin/...` instead of `.venv\Scripts\...`.

**1. Get the code and install it into a virtual environment**

```powershell
git clone <repo-url> ntsb-accident-api
cd ntsb-accident-api
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```

**2. Start the server**

```powershell
.venv\Scripts\ntsb serve --host 127.0.0.1 --port 8000
```

If port 8000 is already used by something else, pick another one (e.g. `--port 8001`).
To work offline with synthetic data instead of calling data.ntsb.gov:

```powershell
$env:NTSB_MOCK = "1"; .venv\Scripts\ntsb serve --port 8000
```

**3. Open it**

| URL | What |
|---|---|
| http://127.0.0.1:8000/ | Web UI |
| http://127.0.0.1:8000/docs | Swagger (try the API in the browser) |
| http://127.0.0.1:8000/redoc | ReDoc reference |
| http://127.0.0.1:8000/api/v1/cases?make=Boeing&limit=5 | Sample API call |

**4. Verify (optional)**

```powershell
.venv\Scripts\pytest
curl.exe "http://127.0.0.1:8000/api/v1/fields"
```

Stop the server with `Ctrl+C`. The server binds to `127.0.0.1` only; use
`--host 0.0.0.0` if other machines on your network should reach it.

**Alternative: Docker**

```powershell
docker build -t ntsb-api .
docker run --rm -p 8000:8000 ntsb-api            # add -e NTSB_MOCK=1 for offline mode
```

Then open http://127.0.0.1:8000/. Map a different host port with `-p 8001:8000` if 8000 is taken.

## Endpoints

| Method | Path | What it does |
|---|---|---|
| GET  | `/api/v1/cases` | Search with friendly filters (`make`, `model`, `operator_name`, `date_from`, `date_to`, `highest_injury`, `event_type`, `finding`, `probable_cause`, `text`, `state`, `airport`, `airline_only`, …) + `limit`/`offset` |
| POST | `/api/v1/cases/query` | Advanced: any CAROL column/operator, matched `all` or `any` |
| GET  | `/api/v1/cases/{ntsb_number}` | Full case: narratives, probable cause, findings (cause/factor), aircraft, links; `include_raw=true` for the untouched record |
| GET  | `/api/v1/cases/{ntsb_number}/report` | Streams the NTSB-generated report PDF |
| GET  | `/api/v1/cases/{ntsb_number}/docket` | Lists public docket documents with download URLs |
| GET  | `/api/v1/stats` | Aggregates for a filter: by year, make, injury, FAR part, state, top findings |
| GET  | `/api/v1/export` | Bulk download: `fmt=csv` / `json` (normalized) or `ntsb-csv` (CAROL's own summary) |
| GET  | `/api/v1/fields` | Every searchable CAROL column with operators and allowed values |
| POST | `/api/v1/debug/payload` | Shows the exact JSON that would be sent to NTSB |

Examples:

```bash
# Part 121 airline accidents on Boeing aircraft since 2020
curl "localhost:8000/api/v1/cases?make=Boeing&airline_only=true&event_type=ACC&date_from=2020-01-01"

# Any case whose findings mention thrust reversers on a 737
curl -X POST localhost:8000/api/v1/cases/query -H 'content-type: application/json' -d '{
  "rules": [{"column":"Finding.FindingText","operator":"contains","value":"thrust reverser"},
            {"column":"Aircraft.AircraftModel","operator":"contains","value":"737"}]}'

curl localhost:8000/api/v1/cases/DCA24MA063
curl -o report.pdf localhost:8000/api/v1/cases/DCA24MA063/report
```

## Generating client SDKs

`python scripts/export_openapi.py` writes `openapi.json`. Generate a typed client in any language:

```bash
npx @openapitools/openapi-generator-cli generate -i openapi.json -g python     -o sdk/python
npx @openapitools/openapi-generator-cli generate -i openapi.json -g typescript-fetch -o sdk/ts
```

## CLI

```bash
ntsb search --make Boeing --airline-only --from 2020-01-01 --limit 10
ntsb case DCA24MA063
ntsb report DCA24MA063 -o report.pdf
ntsb docket DCA24MA063 --download ./docket
ntsb export --finding "thrust reverser" -o reversers.json
```

## Python

```python
from ntsb_api import NTSBClient, CaseFilters

async with NTSBClient() as c:
    page = await c.search(CaseFilters(make="Airbus", airline_only=True).to_rules(), limit=50)
    case = await c.get_case(page["items"][0]["ntsb_number"])
    print(case["probable_cause"], case["findings"])
```

## MCP server (for agents)

`python -m ntsb_api.mcp_server` exposes `search_accidents`, `get_accident` and
`list_docket_documents` as tools for Claude Desktop, LangGraph, CrewAI or any MCP client.

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `NTSB_MOCK` | `0` | Serve synthetic data, never call NTSB |
| `NTSB_CACHE_TTL` | `900` | Seconds to cache upstream responses |
| `NTSB_MIN_INTERVAL` | `0.5` | Minimum seconds between upstream calls (be polite) |
| `NTSB_TIMEOUT` / `NTSB_MAX_RETRIES` | `60` / `3` | Upstream timeout and retries |
| `NTSB_AIRLINE_REG` | `Part 121: Air carrier` | CAROL value used by `airline_only` |
| `NTSB_CORS` | `*` | Allowed browser origins |
| `NTSB_CAROL_BASE`, `NTSB_REPORT_BASE`, `NTSB_DOCKET_BASE` | data.ntsb.gov URLs | Override endpoints |

## How it works and what to know

* **Source.** CAROL's public JSON query API is the same one the data.ntsb.gov search UI calls. It is
  unauthenticated but undocumented, so NTSB can change it. The client keeps all endpoint and
  payload knowledge in `query.py` / `config.py`, and the normalizer resolves each field from several
  candidate names and keeps the untouched record under `raw`, so a rename upstream degrades
  gracefully instead of breaking.
* **Two read paths.** `Query/Main` gives paged results plus a total count (search lists).
  `Query/FileExport` returns a ZIP of full JSON (narratives, findings, vehicles) and is used for case
  detail, stats and exports.
* **Dockets.** NTSB publishes no docket JSON API, so `docket.py` parses the docket page's document
  links. If NTSB renders a docket client-side, the endpoint returns the docket URL with a note.
* **Official API.** NTSB also runs a keyed developer portal (developer.ntsb.gov) and is beta-testing a
  new CAROL with its own API. To move over, add a backend in `client.py`; the REST surface stays the same.
* **Airline filter.** `airline_only` uses the CAROL value `Part 121: Air carrier`. If NTSB changes
  the label, set `NTSB_AIRLINE_REG`. Use `GET /api/v1/fields` to see current columns.
* **Etiquette.** Requests are paced, retried with backoff and cached. Keep bulk pulls reasonable.
* **Mock data** (`NTSB_MOCK=1`, the UI's demo mode) is synthetic. Every case number starts with `DEMO`.
