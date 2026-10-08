# DIY Diag

AI-assisted vehicle intake and draft diagnostic reports for DIY owners.

You describe the problem in your own words. DIY Diag turns that into a clear concern statement, flags safety issues, ranks the likely causes, and lays out checks you can do yourself. It also tells you how hard each fix is and when to stop and call a pro.

Built by James Baird, a 19-year master CDJR / Fiat / Alfa Romeo technician.

> Every report is a draft based on what you describe. It is not a confirmed diagnosis. Verify before you buy parts.

## Features
- Guided intake that asks about the vehicle, the concern, conditions, warning lights, codes, and recent work
- VIN check-digit validation, plus a free decode through NHTSA vPIC
- Model-level open recall lookup (NHTSA recalls API)
- Offline rule engine: ranked likely causes, DIY checks, a difficulty rating, and when to call a pro
- Safety flags and a "stop driving" call for flashing check engine lights, brakes, overheating, fuel smell, smoke, steering, and airbags
- Follow-up questions when the description is too vague to rank causes
- Optional LLM refinement through any OpenAI-compatible API. It keeps every safety flag and never invents TSB numbers or specs
- Markdown, printable HTML, and JSON reports
- No dependencies outside the Python standard library

## Quick start
```bash
python -m diydiag                                    # guided questions
python -m diydiag --intake examples/ram_shudder.json --html --out my_report
python -m diydiag --intake my.json --no-net          # offline
```

Optional LLM pass:
```bash
export DIYDIAG_API_KEY=...            # optional: DIYDIAG_API_BASE, DIYDIAG_MODEL
```

## Evaluation
```bash
python eval/run_eval.py   # 14 labeled owner intakes - Top-1: 1.00, Top-3: 1.00
python -m pytest -q       # 7 tests
```

The labeled set is small and hand-written. The next step is to add real-world owner descriptions where the final repair is known.

## Systems covered (v0.1)
- Torque converter shudder
- Misfire
- Driveline and tire vibration
- Brakes
- Battery and no-start
- Charging
- Cooling and overheating
- EVAP
- O2 sensors and catalytic converter
- Transmission slip
- Steering and suspension
- A/C

## License
MIT
