"""Open recall lookup by make/model/year (NHTSA recalls API, free, no key).

Note: this is a model-level lookup. The owner should confirm by VIN at nhtsa.gov/recalls
or with a dealer, because not every recall applies to every VIN.
"""
from __future__ import annotations
import json, urllib.request, urllib.parse
from typing import List, Dict


def recalls_for(make: str, model: str, year: int, timeout: float = 10.0) -> List[Dict]:
    q = urllib.parse.urlencode({"make": make, "model": model, "modelYear": year})
    with urllib.request.urlopen(f"https://api.nhtsa.gov/recalls/recallsByVehicle?{q}", timeout=timeout) as r:
        data = json.load(r)
    out = []
    for it in data.get("results", []):
        out.append({"campaign": it.get("NHTSACampaignNumber", ""),
                    "component": it.get("Component", ""),
                    "summary": (it.get("Summary") or "").strip(),
                    "remedy": (it.get("Remedy") or "").strip()})
    return out
