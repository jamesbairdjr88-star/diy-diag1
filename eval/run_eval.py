"""Measure top-1 / top-3 accuracy of the rule engine on labeled owner intakes."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from diydiag.schema import Intake
from diydiag.engine import analyze

cases = json.loads((Path(__file__).parent / "cases.json").read_text())
top1 = top3 = 0
for c in cases:
    ids = [x["id"] for x in analyze(Intake.from_dict(c["intake"]))["likely_causes"]]
    hit1 = bool(ids) and ids[0] == c["label"]; hit3 = c["label"] in ids
    top1 += hit1; top3 += hit3
    print(f"{'OK ' if hit1 else ('~3 ' if hit3 else 'MISS')} {c['label']:<16} -> {ids}")
n = len(cases)
print(f"\nCases: {n}  Top-1: {top1/n:.2f}  Top-3: {top3/n:.2f}")
