"""
Generates real output examples from input examples using the OrchestrationGraph.
Ensures outputs are 100% authentic runtime executions, never manually written.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.orchestration.graph import OrchestrationGraph
INPUTS_DIR = ROOT / "input_examples"
OUTPUTS_DIR = ROOT / "output_examples"

def main():
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    graph = OrchestrationGraph(force_sample_mode=True)

    mappings = [
        ("example_1_refactor.json", "output_1_refactor.json"),
        ("example_2_migrate.json", "output_2_migrate.json"),
        ("example_3_abstention.json", "output_3_abstention.json"),
    ]

    for in_name, out_name in mappings:
        in_file = INPUTS_DIR / in_name
        out_file = OUTPUTS_DIR / out_name

        with open(in_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        inp = data["input"]
        options = data.get("options", {})

        print(f"Executing {in_name} -> {out_name}...")
        resp = graph.execute_run(
            query=inp["query"],
            repo=inp["repo"],
            module_path=inp.get("module_path"),
            sample_mode=options.get("sample_mode", True)
        )

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(resp.model_dump(), f, indent=2, ensure_ascii=False)
        print(f"Saved: {out_file} (Status: {resp.status})")

if __name__ == "__main__":
    main()
