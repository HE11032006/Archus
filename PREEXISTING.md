# Pre-existing components

This project is a new build for the Open Agent Hackathon 2026. It reuses the components listed below, which existed **before the build window opened**. Everything not listed here was written during the build window.

## Reference

| Item | Value |
|---|---|
| Original repository | https://github.com/HE11032006/ArchX |
| Reused module | `ArchX/architect_insight/` |
| Scope | Code metric analysis (cyclomatic complexity, AST patterns, coupling, hotspots) |

## What is reused

| Component | Path in this repo | Status when imported |
|---|---|---|
| Repository collector | `ArchX/architect_insight/collector.py` | Static AST analysis for Python |
| Metrics (patterns, architecture, dependencies, git hotspots, tests) | `ArchX/architect_insight/metrics/` | Evaluates complexity and patterns |
| Demo repository | `ArchX/demo_projects/django_app` | Demo target repository |

## What is NOT reused

- Dataset generation & training code (`training/`, `dataset_generation/`)
- Original frontend mock reports
- Incomplete cost calculators

## How the pre-existing code is used

The pre-existing collector is **wrapped and queried as a data source, not rewritten**.
The new multi-agent architecture in `app/` consumes these metrics via **Zetaris** (live SQL) or local SQLite (`SAMPLE_MODE=true`).
Personal identities (authors, emails) from Git hotspots are explicitly filtered and anonymized to ensure data privacy.

## Before and After

| Feature | Before (ArchX) | After (Archus) |
|---|---|---|
| Output | Simple raw metric JSON dump | Sourced, verified decision (Maintain / Refactor / Migrate) |
| Data Layer | Unstructured local files | Fused metrics in Zetaris queried with SQLGuard |
| Reasoning | Single LLM prompt call | 5 collaborating agents with an independent critique loop |
| Safety & Integrity | None | Evaluator veto authority & abstention (`insufficient_evidence`) |
| Sample Mode | None | Deterministic SQLite local mode running without credentials |
