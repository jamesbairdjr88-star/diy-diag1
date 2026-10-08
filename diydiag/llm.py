"""Optional LLM refinement (OpenAI-compatible API).

If DIYDIAG_API_KEY is set, the rule-engine result plus the intake are sent to the model,
which may re-rank causes and improve wording. The model's output must match the same
JSON shape; if it fails or the key is missing, the rule-engine result is returned unchanged.
Safety flags from the rule engine are always kept.
"""
from __future__ import annotations
import json, os, urllib.request
from .schema import Intake

SYSTEM = ("You are an ASE-level automotive diagnostic assistant writing for DIY vehicle owners. "
          "You receive an owner intake and a rule-engine draft. Improve the ranking and wording. "
          "Never invent TSB numbers, part numbers, torque specs or fluid capacities; tell the owner where to verify. "
          "Keep every safety flag. Return ONLY JSON with the same keys as the draft.")


def refine(intake: Intake, draft: dict, timeout: float = 30.0) -> dict:
    key = os.environ.get("DIYDIAG_API_KEY")
    if not key:
        return draft
    base = os.environ.get("DIYDIAG_API_BASE", "https://api.openai.com/v1")
    model = os.environ.get("DIYDIAG_MODEL", "gpt-4o-mini")
    body = {"model": model, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": json.dumps({"intake": intake.to_dict(), "draft": draft})}]}
    req = urllib.request.Request(f"{base}/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = json.loads(json.load(r)["choices"][0]["message"]["content"])
        if not isinstance(out.get("likely_causes"), list):
            return draft
        out["safety_flags"] = list(dict.fromkeys(draft["safety_flags"] + out.get("safety_flags", [])))
        out["stop_driving"] = draft["stop_driving"] or bool(out.get("stop_driving"))
        out["engine"] = f"rules-v0.1 + {model}"
        for k in draft:
            out.setdefault(k, draft[k])
        return out
    except Exception:
        return draft
