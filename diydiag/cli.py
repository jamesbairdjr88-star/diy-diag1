"""Command line: guided intake or JSON file -> Markdown/HTML report."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from .schema import Intake, Vehicle
from .vin import is_valid_vin, decode_vin
from .recalls import recalls_for
from .engine import analyze
from .llm import refine
from .report import to_markdown, to_html


def _ask(prompt, default=""):
    r = input(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
    return r or default


def guided_intake() -> Intake:
    print("DIY Diag - answer what you can, press Enter to skip.\n")
    vin = _ask("VIN (17 characters, on the dash or driver door jamb)")
    v = Vehicle(vin=vin.upper())
    if vin and is_valid_vin(vin):
        try:
            v = decode_vin(vin); print(f"  Decoded: {v.year} {v.make} {v.model} {v.engine}")
        except Exception:
            print("  (Could not reach the VIN decoder - enter details manually)")
    if not v.make:
        y = _ask("Year"); v.year = int(y) if y.isdigit() else None
        v.make = _ask("Make"); v.model = _ask("Model"); v.engine = _ask("Engine (e.g. 5.7L V8)")
    m = _ask("Mileage"); v.mileage = int(m.replace(",", "")) if m.replace(",", "").isdigit() else None
    concern = _ask("Describe the problem in your own words")
    return Intake(vehicle=v, concern=concern,
                  onset=_ask("When did it start? Sudden or gradual?"),
                  frequency=_ask("How often? (always / sometimes / once)"),
                  engine_temp=_ask("Engine cold, warm, or both?"),
                  speed_range=_ask("Speed or RPM when it happens (e.g. 40-50 mph)"),
                  driving_condition=[s.strip() for s in _ask("Idle, accelerating, cruising, braking, turning? (comma list)").split(",") if s.strip()],
                  weather=_ask("Weather when it happens (optional)"),
                  warning_lights=[s.strip() for s in _ask("Warning lights on? (e.g. check engine, flashing check engine, abs)").split(",") if s.strip()],
                  codes=[s.strip() for s in _ask("Codes, if you have them (e.g. P0301, P0420)").split(",") if s.strip()],
                  recent_work=_ask("Recent repairs or parts replaced"))


def main(argv=None):
    p = argparse.ArgumentParser(prog="diydiag", description="AI-assisted DIY vehicle intake and draft diagnostic report")
    p.add_argument("--intake", help="Path to intake JSON (skip the guided questions)")
    p.add_argument("--out", default="report", help="Output file path without extension")
    p.add_argument("--html", action="store_true", help="Also write a printable HTML report")
    p.add_argument("--no-net", action="store_true", help="Skip VIN decode and recall lookups")
    p.add_argument("--json", action="store_true", help="Also write the raw analysis JSON")
    a = p.parse_args(argv)

    intake = Intake.from_dict(json.loads(Path(a.intake).read_text())) if a.intake else guided_intake()
    v = intake.vehicle
    recalls = None
    if not a.no_net:
        if v.vin and is_valid_vin(v.vin) and not v.make:
            try: intake.vehicle = v = decode_vin(v.vin) if not v.mileage else _merge(decode_vin(v.vin), v)
            except Exception: pass
        if v.make and v.model and v.year:
            try: recalls = recalls_for(v.make, v.model, v.year)
            except Exception: recalls = None
    analysis = refine(intake, analyze(intake))
    md = to_markdown(intake, analysis, recalls)
    Path(a.out + ".md").write_text(md)
    print(f"Wrote {a.out}.md")
    if a.html:
        Path(a.out + ".html").write_text(to_html(md)); print(f"Wrote {a.out}.html")
    if a.json:
        Path(a.out + ".json").write_text(json.dumps(analysis, indent=2)); print(f"Wrote {a.out}.json")
    if analysis.get("stop_driving"):
        print("\nSAFETY: this concern may not be safe to keep driving. Read the 'Safety first' section.")
    return 0


def _merge(decoded: Vehicle, given: Vehicle) -> Vehicle:
    decoded.mileage = given.mileage
    return decoded


if __name__ == "__main__":
    sys.exit(main())
