# Pre-existing and imported components

Archus was built for the Open Agent Hackathon 2026, track "The Agent That Can
Explain Why". This file declares everything in the build that was not written
from scratch during the build window: code that already existed, code imported
from elsewhere, specifications reimplemented, and libraries used as shipped.
Anything not listed here was written for this build.

## Summary

| Component | Origin | How Archus uses it | Committed in this repo? |
| --- | --- | --- | --- |
| ArchX `architect_insight` collector and metrics | Author's earlier project, ArchX | Measures a cloned repository (complexity, patterns, coupling, git hotspots, tests) before the agents run | No, used locally, listed in `.gitignore` |
| ArchX demo projects | Same ArchX project | Analysis targets during development (`django_app`, `springboot_app`, `flutter_app`) | No |
| Meterless World Model specification | Meterless (sponsor) | Reimplemented in Python as the agents' shared state, `app/world_model.py` | The reimplementation, yes; no Meterless code is copied |
| World Model conformance checks | Meterless specification | Ported to Python in `tests/test_world_model.py` | Yes |
| `smoke_test.py` | Hackathon Participant Setup Guide | Checks the Zetaris web, REST and JDBC setup | Yes |
| Python and JavaScript libraries | PyPI and npm, see below | Used as shipped, not modified | Locked by `requirements.txt` and `frontend_archus/package.json` |
| Zetaris, Meterless Runtime, NVIDIA Nemotron | Sponsor services | Called over their APIs; nothing vendored | No code, configuration only |

## 1. ArchX: the metrics collector (pre-existing code)

| Item | Value |
| --- | --- |
| Original repository | https://github.com/HE11032006/ArchX |
| Reused module | `ArchX/architect_insight/` |
| Status when imported | Working static analysis for Python repositories |
| Where Archus calls it | `app/repo_analyzer.py` (`from architect_insight.collector import collect`) |

What is reused, unchanged in purpose:

| Component | Path in ArchX | What it does |
| --- | --- | --- |
| Repository collector | `architect_insight/collector.py` | Walks a repository and collects per-file AST metrics |
| Metrics package | `architect_insight/metrics/` | Cyclomatic complexity, architecture patterns, dependencies, git change hotspots, test inventory |
| Demo repositories | `demo_projects/` | Ready-made targets used while developing |

What is not reused from ArchX: the dataset generation and training code
(`training/`, `dataset_generation/`), the original mock report front end, and
the cost calculators.

How it is used. Archus treats the collector as an ingestion source, not as a
library it rewrote. `analyze_and_ingest_repo` clones the target repository,
runs the collector, and writes the measurements into the metric tables
(`modules`, `tests`, `antipatterns`, `hotspots`, `dependencies`). From that
point the agents only see tables and SQL; they never import ArchX themselves.
If ArchX is absent, as in a fresh clone of this repository, the import in
`app/repo_analyzer.py` fails soft (`collect = None`) and runs fall back to the
metrics already stored, including sample mode. Personal identities (author
names and emails) produced by git hotspot analysis are filtered out before
storage.

Before and after:

|  | ArchX (before) | Archus (after) |
| --- | --- | --- |
| Output | A raw metrics JSON dump | A decision (maintain, refactor, migrate, or abstention) with verified evidence |
| Data layer | Local files | Metric tables queried through Zetaris or SQLite, behind SQLGuard |
| Reasoning | One model prompt | Five agents, with an evaluator that re-queries and can veto |
| Safety | None | SQLGuard, evaluator veto, abstention, full JSONL trace |
| Sample mode | None | Deterministic local mode with no credentials |

## 2. Meterless World Model (specification, reimplemented)

The shared state of the agents follows the Meterless World Model
specification: content-derived entity IDs, provenance required on every write,
field-level merge with optimistic revision checks, bitemporal edges, and an
append-only event log from which the state is rebuilt by replay. Archus
implements that specification in Python in `app/world_model.py`; no Meterless
source code is copied into this repository. The specification's conformance
checks are ported to Python and run as part of the test suite
(`tests/test_world_model.py`). Naming it as a reimplementation matters: if the
specification and this code disagree, the code is the one that is wrong.

## 3. Hackathon material

`smoke_test.py`, at the repository root, comes from the Participant Setup
Guide. It checks that Zetaris answers on its web interface, its REST API and
its JDBC endpoint. It was kept as shipped and used to validate the local
Zetaris installation; it is a setup check, not part of a run.

## 4. Libraries (used as shipped, not modified)

Backend, from `requirements.txt`:

| Library | Used for |
| --- | --- |
| FastAPI, Uvicorn | The HTTP API in `run.py` |
| Pydantic | Request, response and shared-state schemas (`app/schemas.py`) |
| requests | Zetaris REST calls, GitHub downloads |
| openai | OpenAI-compatible model calls (Meterless Runtime, Nemotron endpoint) |
| python-dotenv | Loading `.env` |
| sqlglot | Parsing SQL inside SQLGuard |
| pytest | Test dependency |

Front end, from `frontend_archus/package.json`: Next.js, React, Tailwind CSS,
Radix UI primitives (the `src/components/ui/` components follow the shadcn/ui
pattern of copy-in components built on Radix), lucide-react icons and
framer-motion. The component files in `src/components/ui/` were generated
from that pattern and then adapted to this interface; the libraries
underneath them are unmodified npm packages.

## 5. Sponsor services (called, not vendored)

- Zetaris: queried through its REST SQL runner. No Zetaris code is in this
  repository. `scripts/push_to_zetaris.py` is our own script for copying the
  local metric tables towards a Zetaris instance.
- Meterless Runtime: called as the primary model provider. Connection is
  configured with our `scripts/meterless.py`; tokens are stored outside git.
- NVIDIA Nemotron: called through Meterless, or directly through an
  OpenAI-compatible endpoint as the fallback provider.

## 6. What was written for this build

For the record, the parts that are new here: the five agents
(`app/agents/`), the orchestration state machine
(`app/orchestration/graph.py`), SQLGuard (`app/sqlguard.py`), the Zetaris
adapter (`app/adapters/zetaris.py`), the Meterless runtime adapter and
provider selection (`app/adapters/meterless_runtime.py`, `app/llm.py`), the
World Model implementation (`app/world_model.py`, `app/world_state.py`), the
scoring (`app/scoring.py`), repository ingestion around the ArchX collector
(`app/repo_analyzer.py`), the API (`run.py`), the sample data adapter, the
traces, the tests, and the whole `frontend_archus/` interface.
