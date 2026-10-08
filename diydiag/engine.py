"""Offline rule-based diagnostic engine.

Turns an owner's intake into ranked likely causes, safety flags, a DIY check plan,
and a clear "stop and see a pro" call. Works with no API key. An optional LLM pass
(see llm.py) can refine the wording, but this engine is the deterministic baseline
that the evaluation harness measures.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
from .schema import Intake

DIFFICULTY = {1: "Easy - basic hand tools", 2: "Moderate - some mechanical experience",
              3: "Advanced - special tools or lifting the vehicle", 4: "Pro recommended"}


@dataclass
class Hypothesis:
    id: str
    name: str
    system: str
    keywords: List[str]
    boosts: Dict[str, float] = field(default_factory=dict)   # condition token -> extra score
    codes: List[str] = field(default_factory=list)            # code prefixes that support it
    diy_checks: List[str] = field(default_factory=list)
    difficulty: int = 2
    pro_when: str = ""
    why: str = ""


KB: List[Hypothesis] = [
    Hypothesis("tcc_shudder", "Torque converter clutch shudder", "Transmission",
               ["shudder", "rumble strip", "rumble", "vibrat", "shake"],
               {"warm": 1.5, "cruis": 1.5, "light throttle": 1.0, "40": 0.5, "45": 0.5, "50": 0.5},
               ["P0740", "P0741", "P1740"],
               ["Check transmission fluid level and condition if your vehicle has a dipstick (red/pink and not burnt-smelling is good).",
                "Note the exact speed it happens. If a light tap of the brake (without slowing) or a slight throttle change makes it stop instantly, that points to the converter clutch.",
                "Scan for codes, including pending codes."],
               3, "Fluid service or software updates often need a shop scan tool. Internal converter problems are a shop job.",
               "Shudder that only shows up warm at a steady, light-throttle cruise is the classic converter-clutch pattern."),
    Hypothesis("misfire", "Engine misfire (plugs, coils, or injector)", "Engine",
               ["misfire", "rough idle", "stumble", "hesitat", "shake", "jerk", "sputter", "flashing"],
               {"accelerat": 1.0, "idle": 1.0, "rain": 0.5, "flashing check engine": 3.0, "check engine": 1.0},
               ["P030", "P0300"],
               ["Scan for codes. P0301-P0308 tell you which cylinder.",
                "If one cylinder is misfiring and your engine has coil-on-plug, swap that coil with a neighbor. If the misfire follows the coil, replace the coil.",
                "Pull and inspect the spark plug in that cylinder. Look for oil, cracks, or a worn electrode."],
               2, "If the check engine light is flashing, stop driving: unburned fuel can overheat and ruin the catalytic converter.",
               "Shaking with stumbling or a check engine light most often comes from ignition parts."),
    Hypothesis("driveline", "Driveline, tire, or wheel balance vibration", "Tires/Driveline",
               ["vibrat", "shake", "wobble", "steering wheel shake", "highway"],
               {"highway": 1.0, "60": 0.5, "65": 0.5, "70": 0.5, "both": 0.5},
               [],
               ["Look for uneven tire wear, bulges, or missing wheel weights.",
                "Check whether the vibration depends on speed (same at any throttle) or on load. Speed-only usually means tires, balance, or the driveshaft.",
                "With the vehicle safely on jack stands, check u-joints for play by twisting the driveshaft by hand."],
               2, "Tire balancing needs a shop machine. Any play in the u-joints or a wobbling tire should be fixed before highway driving.",
               "Vibration that follows road speed rather than engine load usually comes from the tires, wheels, or driveshaft."),
    Hypothesis("brakes_worn", "Worn brake pads or rotors", "Brakes",
               ["squeal", "grind", "brake noise", "pulsat", "brake pedal", "brakes", "stopping"],
               {"braking": 2.0},
               [],
               ["Look through the wheel spokes at the pad thickness. Less than about 3 mm (1/8 inch) means it's time.",
                "Grinding means the pads may be metal-on-metal. Check the rotors for deep grooves.",
                "A pulsing pedal usually means warped or unevenly worn rotors."],
               2, "Grinding or a soft or sinking pedal: stop driving and have it inspected. Brakes are safety-critical.",
               "Noise or pulsation that happens with braking points to pads and rotors."),
    Hypothesis("no_start_battery", "Weak battery or bad battery connection", "Starting/Charging",
               ["won't start", "wont start", "no start", "click", "slow crank", "dead", "battery"],
               {"cold": 1.0, "battery": 1.5},
               [],
               ["Measure battery voltage with the engine off. About 12.6 V is full, and below 12.2 V is weak.",
                "Clean and tighten the battery terminals.",
                "Have the battery load-tested. Most parts stores do this for free."],
               1, "If the battery tests good and it still clicks, the starter or the wiring needs a closer look.",
               "Clicking or slow cranking, especially in the cold, most often comes from the battery."),
    Hypothesis("charging", "Alternator or charging system problem", "Starting/Charging",
               ["battery light", "dim", "dies while driving", "battery keeps dying", "whine"],
               {"battery": 1.5},
               [],
               ["With the engine running, battery voltage should be about 13.8-14.7 V.",
                "Check the serpentine belt for cracks, glazing, or looseness."],
               2, "Alternator replacement is moderate on some vehicles and pro-level on others.",
               "A battery warning light or dimming lights while driving point to the charging system."),
    Hypothesis("overheat", "Cooling system problem (low coolant, thermostat, fan, or water pump)", "Cooling",
               ["overheat", "temp gauge", "hot", "coolant", "steam", "sweet smell"],
               {"idle": 1.0, "temp": 2.0},
               [],
               ["Only when the engine is fully cold: check the coolant level in the reservoir.",
                "Look for leaks (green, orange, or pink fluid, or a sweet smell) at the hoses, radiator, and water pump.",
                "With the engine warm and A/C on, the cooling fan should be running."],
               3, "Never open a hot radiator cap. If the temperature gauge is in the red, pull over and shut the engine off. Repeated overheating can damage the engine.",
               "A high temperature reading or a sweet coolant smell points to the cooling system."),
    Hypothesis("evap", "EVAP leak (loose gas cap is the most common)", "Emissions",
               ["gas cap", "fuel smell", "evap"],
               {"check engine": 1.0},
               ["P0440", "P0442", "P0455", "P0456", "P0457"],
               ["Remove the gas cap, check its seal, and tighten it until it clicks.",
                "Clear the code and drive for a few days. It may take several drive cycles to stay off."],
               1, "A strong raw-fuel smell inside the cabin is a fire risk. Get it checked promptly.",
               "Small EVAP leak codes very often come from the gas cap."),
    Hypothesis("o2_cat", "O2 sensor or catalytic converter problem", "Emissions",
               ["rotten egg", "sulfur", "catalyst", "o2 sensor", "poor mpg", "fuel economy"],
               {"check engine": 1.0},
               ["P0420", "P0430", "P013", "P014", "P015"],
               ["Scan for codes and note any misfire codes. Fix misfires first, because they damage the catalytic converter.",
                "Check for exhaust leaks ahead of the O2 sensors (ticking noise on a cold start)."],
               3, "Replacing a catalytic converter is expensive. Confirm the diagnosis before buying parts.",
               "A catalyst-efficiency code or a rotten-egg smell points here."),
    Hypothesis("trans_slip", "Transmission slipping or harsh shifting", "Transmission",
               ["slip", "flare", "harsh shift", "delayed engagement", "won't shift", "rpm jumps"],
               {"accelerat": 1.0, "warm": 0.5},
               ["P07", "P08"],
               ["Check the fluid level and smell (follow your owner's manual - many need the engine running and warm).",
                "Scan for transmission codes."],
               4, "Transmission repair is pro-level. Low fluid or a leak is the only common DIY fix.",
               "RPM rising without the vehicle speeding up points to slipping."),
    Hypothesis("steering_susp", "Steering or suspension wear (tie rod, ball joint, sway bar link, strut)", "Steering/Suspension",
               ["clunk", "knock over bumps", "pulls", "wander", "loose steering", "creak", "bumps"],
               {"turning": 1.0, "bumps": 1.0},
               [],
               ["With the vehicle safely on jack stands, grab the tire at the 12 and 6 o'clock positions and rock it (checks ball joints), then at 3 and 9 (checks tie rods).",
                "Inspect the sway bar end links and look for leaking struts or shocks."],
               3, "Loose steering or ball joints are a safety issue, and an alignment is needed after most of these repairs.",
               "Clunking over bumps or loose steering usually means worn suspension or steering joints."),
    Hypothesis("ac", "A/C not cooling (low refrigerant, compressor, or blend door)", "HVAC",
               ["a/c", "ac not", "air conditioning", "blowing warm", "not cold"],
               {"heat": 1.0},
               [],
               ["With the A/C on, check whether the compressor clutch is engaging (the center of the pulley spins).",
                "Check that the cabin air filter is not clogged and that the condenser fins are not blocked."],
               3, "Refrigerant work legally needs EPA-certified handling. DIY recharge cans can overcharge the system.",
               "Warm air from the A/C usually means low refrigerant or a compressor or clutch problem."),
]

SAFETY_RULES = [
    (["flashing check engine", "flashing"], "Flashing check engine light: stop driving soon. Severe misfire can damage the catalytic converter or start a fire."),
    (["grind", "brake pedal", "soft pedal", "sinking pedal", "brakes"], "Brake concern: brakes are safety-critical. Inspect them before more driving."),
    (["fuel smell", "gas smell", "raw fuel"], "Fuel smell: possible fire risk. Inspect promptly and don't park in an enclosed garage."),
    (["overheat", "temp gauge", "steam"], "Overheating: pull over and shut the engine off. Never open a hot radiator cap."),
    (["airbag"], "Airbag light: the airbags may not deploy in a crash. This is a pro diagnosis - don't probe airbag wiring."),
    (["loose steering", "steering"], "Steering concern: any looseness or binding is a safety issue."),
    (["smoke", "burning"], "Smoke or burning smell: find the source before driving further."),
]


def _score(h: Hypothesis, text: str, codes: List[str]) -> float:
    s = sum(1.0 for k in h.keywords if k in text)
    if s == 0 and not any(c.upper().startswith(p) for c in codes for p in h.codes):
        return 0.0
    s += sum(w for k, w in h.boosts.items() if k in text)
    s += sum(3.0 for c in codes for p in h.codes if c.upper().startswith(p))
    return s


def analyze(intake: Intake, top_n: int = 3) -> dict:
    text = intake.text_blob()
    codes = [c.strip().upper() for c in intake.codes if c.strip()]
    scored = [(h, _score(h, text, codes)) for h in KB]
    scored = [x for x in scored if x[1] > 0]
    scored.sort(key=lambda x: -x[1])
    total = sum(s for _, s in scored[:top_n]) or 1.0
    causes = [{"id": h.id, "name": h.name, "system": h.system,
               "confidence": round(s / total, 2), "why": h.why,
               "diy_checks": h.diy_checks, "difficulty": h.difficulty,
               "difficulty_label": DIFFICULTY[h.difficulty], "pro_when": h.pro_when}
              for h, s in scored[:top_n]]
    flags = [msg for keys, msg in SAFETY_RULES if any(k in text for k in keys)]
    stop_driving = any(k in text for k in ["flashing", "grind", "overheat", "steam", "fuel smell", "smoke", "soft pedal"])
    return {"structured_concern": structure_concern(intake), "safety_flags": flags,
            "stop_driving": stop_driving, "likely_causes": causes,
            "needs_more_info": follow_up_questions(intake), "engine": "rules-v0.1"}


def structure_concern(i: Intake) -> str:
    bits = [f"Owner reports: {i.concern.strip().rstrip('.')}"]
    cond = []
    if i.speed_range: cond.append(f"at {i.speed_range}")
    if i.driving_condition: cond.append("while " + ", ".join(i.driving_condition))
    if i.engine_temp: cond.append(f"engine {i.engine_temp}")
    if i.weather: cond.append(f"in {i.weather} weather")
    if cond: bits.append("Occurs " + "; ".join(cond))
    if i.frequency: bits.append(f"Frequency: {i.frequency}")
    if i.onset: bits.append(f"Started: {i.onset}")
    if i.warning_lights: bits.append("Warning lights: " + ", ".join(i.warning_lights))
    if i.codes: bits.append("Codes: " + ", ".join(c.upper() for c in i.codes))
    return ". ".join(bits) + "."


def follow_up_questions(i: Intake) -> List[str]:
    q = []
    if not i.codes and ("check engine" in " ".join(i.warning_lights).lower() or not i.warning_lights):
        q.append("Can you read the codes? Many parts stores scan for free, or a basic OBD2 reader costs about $20-30.")
    if not i.engine_temp: q.append("Does it happen with the engine cold, warmed up, or both?")
    if not i.speed_range and not i.driving_condition: q.append("When does it happen - idling, accelerating, cruising, braking, or turning?")
    if not i.frequency: q.append("Does it happen every time, sometimes, or did it only happen once?")
    return q
