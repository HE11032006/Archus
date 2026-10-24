# Archus: Verifiable Architecture Decision System

> **Track:** The Agent That Can Explain Why  
> **Sponsor Technology:** Zetaris (Federated Data Layer), Meterless (Model Routing), NVIDIA Nemotron  
> **Run:** `python run.py`, then `POST /run` on port 8000  

---

## 1. Problem

Tech leads and software architects frequently face high-stakes legacy code decisions: should a software module be **maintained**, **refactored**, or **migrated**? Today, these decisions are often made based on subjective impressions or rushed estimates rather than verified quantitative metrics. When teams rely on generative AI, generic LLMs frequently hallucinate confidence and cite fictitious code statistics.

---

## 2. What Archus Does

**Archus** is a multi-agent system that helps tech leads make verifiable architectural decisions:
1. It queries real structural code metrics (cyclomatic complexity, test coverage estimates, coupling, God Class patterns, and git change hotspots) stored in **Zetaris**.
2. An independent **`EvidenceEvaluatorAgent`** verifies **every single factual claim** by issuing counter-queries to the database.
3. If critical baseline metrics are missing or unsubstantiated, the system **refuses to conclude** and triggers an explicit **Abstention** (`insufficient_evidence`).

---

## 3. Multi-Agent Architecture

Archus operates as an explicit state machine coordinating 5 specialized agents with an active feedback loop:

| Agent | Responsibility | Can Block / Retry? |
|---|---|---|
| `PlannerAgent` | Decomposes the tech lead's query into concrete criteria and plans SQL retrieval queries. | Yes |
| `RetrieverAgent` | Validates queries via `SQLGuard` and executes them against Zetaris (or local SQLite in Sample Mode). | Yes |
| `AnalystAgent` | Compares the 3 options (Maintain / Refactor / Migrate) and drafts quantitative claims. | Yes (Revises upon critique) |
| `EvidenceEvaluatorAgent` | **Veto & Verification Authority**: Re-queries Zetaris to prove claims, triggers feedback loops, or abstains. | **Yes (Has Veto Power)** |
| `ReporterAgent` | Synthesizes approved evidence and generates the final decision record and action plan. | No |

```
                     ┌──────────────────┐
                     │   POST /run      │
                     └─────────┬────────┘
                               ▼
                     ┌──────────────────┐
                     │   PlannerAgent   │
                     └─────────┬────────┘
                               ▼
                     ┌──────────────────┐      SQL Queries
                     │  RetrieverAgent  │ ─────────────────────► ┌──────────────────────┐
                     └─────────┬────────┘                        │  Zetaris / SQLite    │
                               ▼                                 │  (via SQLGuard)      │
                     ┌──────────────────┐                        └──────────┬───────────┘
               ┌────►│   AnalystAgent   │                                   │
               │     └─────────┬────────┘                                   │
               │               ▼                                            │
Feedback Loop  │     ┌────────────────────────┐                             │
(needs_revision)│     │ EvidenceEvaluatorAgent │◄── Independent Re-query ───┘
               └─────┤  (Independent Veto)    │
                     └─────────┬──────────────┘
                               │
               ┌───────────────┴───────────────┐
               ▼ (Approved)                    ▼ (Unsubstantiated)
     ┌──────────────────┐            ┌────────────────────────┐
     │  ReporterAgent   │            │      Abstention        │
     │ (Verified Output)│            │(insufficient_evidence) │
     └──────────────────┘            └────────────────────────┘
```

---

## 4. What Makes Archus a Genuine Agent System

- **Independent Counter-Verification:** The Evaluator does not passively read the Analyst's output; it independently executes SQL queries against Zetaris to confirm that numbers cited (e.g., complexity 14.0, test coverage 68.5%) actually exist in the data.
- **Active Critique Loop (`needs_revision`):** When numbers diverge or criteria are untested, the Evaluator sends the dossier back to the Analyst for correction.
- **Principled Abstention (`insufficient_evidence`):** When repository data is absent or insufficient, Archus abstains instead of guessing.
- **Full Traceability:** Every event, query, evaluation check, and duration is logged in JSONL format to `stdout` and [logs/](file:///h:/hackgen/archus/logs).

---

## 4b. Meterless Engine: World Model (shared agent state)

Archus implements the [Meterless World Model](https://github.com/Meterless/Meterless/tree/main/engines/world-model) as the state its agents share. The Analyst writes each claim to the World Model; the Evaluator reads the claim back from there, re-queries the data, and records its verdict on the same entity without erasing the Analyst's fields.

| Spec property | Where in Archus |
|---|---|
| Stable, content-derived IDs (`type:system:id`, `ent_<sha256>`) | `app/world_model.py`, `app/world_state.py` |
| Provenance on every write (agent + timestamp + run) | `WorldModel.upsert_entity` / `relate` reject writes without a source |
| Append-only event log, views rebuilt by replay | SQLite `data/world_model.db` (`WORLD_MODEL_DB`), `WorldModel._replay` |
| Field-level merge + optimistic revision check | Evaluator writes with `expected_rev`; a stale write raises `ConflictError` |
| Bitemporal edges | A new `verified_by` edge closes the previous one, so verification history stays queryable |
| Ordered audit | `WorldModel.audit()` |

Graph per run: `run -executed-> query`, `run -asserts-> claim`, `claim -cites-> query` (retrieval), `claim -verified_by-> query` (independent re-query), `claim -about-> module`. Each evidence item in `POST /run` carries `claim_id`, `cited_query_ids` and `verified_by_query_id`.

Read endpoints: `GET /world/runs/{run_id}` (lineage of every claim), `GET /world/entities/{id}`, `GET /world/stats`.

Tests: `python -m unittest discover -s tests -v` runs the official conformance checks ported to Python (stable IDs, merge bands, provenance, idempotent ingest, bitemporal edges, audit order), concurrent-writer and stale-writer tests, restart-by-replay, and the full pipeline in Sample Mode. `scripts/judge_check.py` runs them as step 9.

---

## 5. Technology Stack & Sponsors

| Layer | Component | Description |
|---|---|---|
| **Data Layer** | **Zetaris** | Federated SQL engine querying metric tables via REST API (`POST /sql-editor/sqls/run`). |
| **Power Layer** | **Meterless** | Model routing runtime managing OpenAI-compatible completions (e.g. NVIDIA Nemotron). |
| **API** | **FastAPI + Uvicorn** | Programmatic entrypoint on `POST /run` (listening on `0.0.0.0:$PORT`). |
| **Safety** | **SQLGuard (sqlglot)** | Strict AST validator: read-only `SELECT`, table whitelisting, mandatory `LIMIT`. |
| **Sample Mode** | **SQLite Local** | Fully functional fallback using cached realistic metrics with zero live credentials. |

---

## 6. Quick Start & Setup

### Option A: Standard Python Environment
```bash
# 1. Clone repository and navigate
cd archus

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Fill in your ZETARIS_* and MODEL_* variables in .env if running live

# 4. Start the server
python run.py --serve --port 8000
```

### Option B: Docker
```bash
docker build -t archus-submission .
docker run --rm -p 8000:8000 --env-file .env archus-submission
```

---

## 7. Sample Mode (Zero-Credential Judge Testing)

Judges can execute and evaluate Archus **without any external API keys or active Zetaris instances**:

```bash
# Force Sample Mode via CLI
python run.py --sample --query "Should we refactor the accounts module?" --repo django_app --module accounts

# Or run the automated 9-step verification suite
python scripts/judge_check.py
```

In `SAMPLE_MODE=true`, the real multi-agent orchestration, SQLGuard, and critique loops run against pre-seeded realistic metrics in SQLite. No pre-recorded responses are used.

---

## 8. Usage & Example Endpoints

### Run Request (`POST /run`)
```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "query": "Should we refactor or maintain the accounts module?",
      "repo": "django_app",
      "module_path": "accounts"
    },
    "options": {
      "sample_mode": true
    }
  }'
```

### Real Output (Abridged)
```json
{
  "run_id": "9f67edca",
  "status": "success",
  "output": {
    "decision": "refactor",
    "confidence": 0.8,
    "options_compared": [
      {
        "option": "maintain",
        "score": 52.0,
        "rationale": "Current max complexity is 14.0 with 7 bug fixes recorded."
      },
      {
        "option": "refactor",
        "score": 67.4,
        "rationale": "Test coverage is 68.5% with coupling score of 3.8."
      },
      {
        "option": "migrate",
        "score": 17.7,
        "rationale": "God classes detected: 0, coupling score: 3.8."
      }
    ],
    "evidence": [
      {
        "claim": "Maximum cyclomatic complexity is 14.0",
        "metric": "complexity_max",
        "source_table": "modules",
        "verified": true
      },
      {
        "claim": "Test coverage estimate is 68.5%",
        "metric": "coverage_estimate",
        "source_table": "tests",
        "verified": true
      }
    ],
    "action_plan": [
      "Decompose long methods into pure helper functions covered by existing tests.",
      "Decouple cross-module references using dependency inversion."
    ]
  }
}
```

---

## 8b. Model Provider: Meterless Runtime

Meterless Runtime is Archus's **primary model provider**. Providers (`app/llm.py`):

| Provider id | Name | Configured by |
|---|---|---|
| `meterless` (default) | Meterless Runtime (local Nightshift, contract v4) | `scripts/meterless.py`, saved in `data/provider_settings.json` (gitignored); routing mode `METERLESS_MODEL` (default `meterless/auto`) |
| `openai_compatible` | Any OpenAI-compatible endpoint (e.g. NVIDIA) | `MODEL_BASE_URL`, `MODEL_API_KEY`, `NEMOTRON_MODEL` |
| `none` | No model call: the deterministic rules text | nothing |

Choose per run with `"options": {"provider": "meterless"}` on `POST /run` or `python run.py --provider meterless`; the default is `LLM_PROVIDER`, else `meterless`. If the selected provider is unavailable or fails, the other one is tried, then the rules. Only the ReporterAgent's summary wording uses a model: decisions and evidence are always computed and verified from data, so they never change with the provider. Each response carries `output.model_provider` (provider, routing mode requested, model served, fallback, attempts), also logged as the `llm_call` trace event.

```bash
python scripts/meterless.py detect            # Auto Detect: 127.0.0.1, localhost, [::1] x 8088, 8090, 8787, 11434
python scripts/meterless.py connect           # paste a base URL (any form) or a connect link /connect#k=<key>, typed hidden
python scripts/meterless.py token             # paste the token from the runtime Console (hidden input)
python scripts/meterless.py status            # online / unauthorized / offline
python scripts/meterless.py chat "Say hello"  # plain text request on meterless/auto
```

- Pasted URLs are normalised to `<host>/v1` (`/v1`, `/v1/models`, `/v1/chat/completions`, `/healthz`, no scheme: all accepted; never `/v1/v1`).
- Every call sends `Authorization: Bearer <token>` and `meterless-app: archus`; chat also sends `meterless-scope: user`. The token is stored under `meterless_runtime_token`, or read from `<METERLESS_STATE_DIR>/proxy-token`. The placeholder `rt-local` is rejected. Tokens and connect-link keys are never printed or logged.
- Status comes from `GET /v1/models`: 401/403 = `unauthorized` (paste the token), 200 with `meterless/*` ids = `online`, anything else = `offline`. Unknown `meterless/*` routing modes are kept.
- Requests use a 180 s timeout (a cold model load can take minutes).
- Read-only API: `GET /providers`, `GET /providers/meterless/status`. Connecting is CLI-only, so a client on the network can't repoint Archus and capture the token.
- Tests: `python -m unittest tests.test_meterless_runtime -v`, against `tests/meterless_stub.py`, a local stand-in that enforces the contract.

---

## 9. Failure & Fallback Handling

| Scenario | Behavior |
|---|---|
| **Zetaris Unreachable** | Logs warning and cleanly falls back to cached local metrics database. |
| **Model Rate-Limited / Offline** | Falls back to deterministic rule scoring engine without crashing. |
| **Dangerous SQL Attempted** | Blocked by `SQLGuard` with structured error; query is rejected. |
| **Missing Module Data** | System triggers `insufficient_evidence` abstention with explicit missing data list. |

---

## 10. Pre-existing Code Declaration

See [PREEXISTING.md](PREEXISTING.md) for full details on reused components imported from ArchX.
The AST collector is wrapped as an ingested data source; all orchestration, agents, guards, adapters, and APIs were created during the hackathon window.
