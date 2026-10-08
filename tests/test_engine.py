import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diydiag.schema import Intake, Vehicle
from diydiag.engine import analyze
from diydiag.vin import is_valid_vin
from diydiag.report import to_markdown, to_html


def test_vin_check_digit():
    assert is_valid_vin("1HGCM82633A004352")
    assert not is_valid_vin("1HGCM82633A004353")
    assert not is_valid_vin("SHORT")


def test_ram_shudder_ranks_tcc_first():
    i = Intake.from_dict(json.loads((ROOT / "examples/ram_shudder.json").read_text()))
    a = analyze(i)
    assert a["likely_causes"][0]["id"] == "tcc_shudder"
    assert not a["stop_driving"]


def test_flashing_cel_is_safety_stop():
    i = Intake(vehicle=Vehicle(), concern="engine shaking", warning_lights=["flashing check engine"])
    a = analyze(i)
    assert a["stop_driving"] and a["safety_flags"]
    assert a["likely_causes"][0]["id"] == "misfire"


def test_code_alone_drives_ranking():
    a = analyze(Intake(vehicle=Vehicle(), concern="light came on", codes=["P0420"]))
    assert a["likely_causes"][0]["id"] == "o2_cat"


def test_vague_concern_asks_followups():
    a = analyze(Intake(vehicle=Vehicle(), concern="something feels off"))
    assert a["likely_causes"] == [] and len(a["needs_more_info"]) >= 3


def test_report_renders():
    i = Intake.from_dict(json.loads((ROOT / "examples/ram_shudder.json").read_text()))
    md = to_markdown(i, analyze(i), recalls=[])
    assert "DIY Diagnostic Report" in md and "not a confirmed diagnosis" in md
    assert "<h1>" in to_html(md)


def test_eval_meets_floor():
    out = subprocess.run([sys.executable, str(ROOT / "eval/run_eval.py")], capture_output=True, text=True).stdout
    top3 = float(out.strip().split("Top-3: ")[1])
    assert top3 >= 0.9
