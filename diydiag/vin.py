"""VIN validation and decoding (NHTSA vPIC, free, no key)."""
from __future__ import annotations
import json, urllib.request, urllib.parse
from .schema import Vehicle

_TRANS = {**{str(i): i for i in range(10)},
          **dict(zip("ABCDEFGH", range(1, 9))), **dict(zip("JKLMN", range(1, 6))), "P": 7, "R": 9,
          **dict(zip("STUVWXYZ", range(2, 10)))}
_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]


def is_valid_vin(vin: str) -> bool:
    """Check length, allowed characters, and the North American check digit (position 9)."""
    vin = (vin or "").strip().upper()
    if len(vin) != 17 or any(c in "IOQ" for c in vin) or any(c not in _TRANS for c in vin):
        return False
    total = sum(_TRANS[c] * w for c, w in zip(vin, _WEIGHTS))
    check = total % 11
    return vin[8] == ("X" if check == 10 else str(check))


def decode_vin(vin: str, timeout: float = 10.0) -> Vehicle:
    """Decode a VIN with NHTSA vPIC. Raises on network failure; caller decides fallback."""
    url = ("https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/"
           f"{urllib.parse.quote(vin.strip())}?format=json")
    with urllib.request.urlopen(url, timeout=timeout) as r:
        row = json.load(r)["Results"][0]
    disp = row.get("DisplacementL") or ""
    cyl = row.get("EngineCylinders") or ""
    engine = " ".join(x for x in [f"{float(disp):.1f}L" if disp else "", f"{cyl}-cyl" if cyl else "",
                                  row.get("EngineModel") or ""] if x).strip()
    year = row.get("ModelYear")
    return Vehicle(vin=vin.strip().upper(), year=int(year) if year else None,
                   make=(row.get("Make") or "").title(), model=row.get("Model") or "",
                   engine=engine, transmission=row.get("TransmissionStyle") or "")
