"""Extract AEP repair labor from Install_Labor_HackOHIO.xlsx into JSON config."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "config" / "restoration" / "repair_labor_v1.json"
XLSX_CANDIDATES = [
    ROOT / "Install_Labor_HackOHIO.xlsx",
    ROOT / "data" / "raw" / "Install_Labor_HackOHIO.xlsx",
    ROOT / "data" / "reference" / "Install_Labor_HackOHIO.xlsx",
]

INDIRECT_MULTIPLIER = 4.5


def find_workbook() -> Path | None:
    for p in XLSX_CANDIDATES:
        if p.is_file():
            return p
    return None


def _parse_material_blocks(df) -> dict[str, tuple[float, float, str]]:
    """Parse 'Labor time material related' sheet blocks into label -> (install, removal, detail)."""
    blocks: dict[str, tuple[float, float, str]] = {}
    i = 0
    n = len(df)
    while i < n:
        title = df.iloc[i, 0]
        if not isinstance(title, str) or "Average Hours" not in title:
            i += 1
            continue
        label = title.strip()
        i += 1
        if i >= n:
            break
        header = df.iloc[i]
        hdr0 = str(header.iloc[0]) if header.iloc[0] == header.iloc[0] else ""
        if hdr0 == "Avg Install Hours":
            i += 1
            if i < n:
                inst = float(df.iloc[i, 0])
                rem = float(df.iloc[i, 1])
                blocks[label] = (inst, rem, "aggregate average")
            i += 1
            continue
        if hdr0 == "Size Group":
            i += 1
            while i < n and isinstance(df.iloc[i, 0], str):
                size = df.iloc[i, 0]
                inst = float(df.iloc[i, 2])
                rem = float(df.iloc[i, 3])
                blocks[f"{label} / {size}"] = (
                    inst,
                    rem,
                    f"{df.iloc[i, 1]}",
                )
                i += 1
            continue
        if hdr0 == "Size (kVA)":
            i += 1
            while i < n:
                val = df.iloc[i, 0]
                if val != val or not isinstance(val, (int, float)):
                    break
                kva = int(val)
                inst = float(df.iloc[i, 2])
                rem = float(df.iloc[i, 3])
                blocks[f"{label} / {kva} kVA"] = (inst, rem, f"CU count {df.iloc[i, 1]}")
                i += 1
            continue
        if hdr0 == "CU Count":
            i += 1
            if i < n:
                inst = float(df.iloc[i, 1])
                rem = float(df.iloc[i, 2])
                blocks[label] = (inst, rem, f"CU count {df.iloc[i, 0]}")
            i += 1
            continue
        i += 1
    return blocks


def extract_labor(xlsx: Path) -> dict:
    import pandas as pd

    material = pd.read_excel(xlsx, sheet_name="Labor time material related", header=None)
    blocks = _parse_material_blocks(material)

    ilm_df = pd.read_excel(xlsx, sheet_name="Indirect Labor Multiplier", header=None)
    ilm = INDIRECT_MULTIPLIER
    for val in ilm_df.to_numpy().flatten():
        if isinstance(val, (int, float)) and val == val:
            ilm = float(val)
            break

    def entry(
        key: str,
        block_key: str,
        *,
        construction_unit_id: str,
        mapping_note: str,
        approximate: bool = False,
    ) -> dict:
        if block_key not in blocks:
            return {
                "configured": False,
                "mapping_note": mapping_note,
                "approximate_mapping": approximate,
                "sought_block": block_key,
            }
        inst, rem, detail = blocks[block_key]
        return {
            "configured": True,
            "construction_unit_id": construction_unit_id,
            "description": block_key,
            "detail": detail,
            "removal_person_hours": rem,
            "installation_person_hours": inst,
            "quantity_default": 1,
            "mapping_note": mapping_note,
            "approximate_mapping": approximate,
            "supporting_units": [],
            "source_sheet": "Labor time material related",
        }

    repairs = {
        "pole_replacement": entry(
            "pole_replacement",
            "Pole CU Average Hours by Size / Medium",
            construction_unit_id="AEP-POL-MEDIUM-40-55ft",
            mapping_note="Damaged Pole proxy: Pole CU average hours, Medium (40–55 ft) from workbook.",
        ),
        "wire_replacement": entry(
            "wire_replacement",
            "Service CU Average Hours",
            construction_unit_id="AEP-SERVICE-CU-AVG",
            mapping_note=(
                "Damaged Wire proxy: Service CU aggregate average hours "
                "(workbook has no primary-conductor line replacement aggregate)."
            ),
            approximate=True,
        ),
        "transformer_replacement": entry(
            "transformer_replacement",
            "Transformer CU Average Hours by Size / 25 kVA",
            construction_unit_id="AEP-XFMR-25KVA-AVG",
            mapping_note="Damaged Equipment proxy: distribution transformer 25 kVA row (CU count 47).",
        ),
        "switch_replacement": entry(
            "switch_replacement",
            "Switch CU Average Hours",
            construction_unit_id="AEP-SWITCH-AVG",
            mapping_note="Damaged Switch proxy: Switch CU aggregate average hours.",
        ),
    }

    return {
        "config_version": "repair_labor_v1",
        "source_workbook": str(xlsx.relative_to(ROOT)) if xlsx.is_relative_to(ROOT) else str(xlsx),
        "indirect_labor_multiplier": ilm,
        "duration_formula": (
            "repair_hours = (removal_person_hours + installation_person_hours) "
            "* quantity * indirect_labor_multiplier / workers_per_crew"
        ),
        "unit_interpretation": (
            "Workbook Avg Install/Removal Hours are direct person-hours before ILM (×4.5 once)."
        ),
        "repairs": repairs,
        "extracted_blocks_available": sorted(blocks.keys()),
    }


def main() -> int:
    xlsx = find_workbook()
    if not xlsx:
        print("Install_Labor_HackOHIO.xlsx not found.", file=sys.stderr)
        return 1
    payload = extract_labor(xlsx)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")
    for k, v in payload["repairs"].items():
        if v.get("configured"):
            print(
                k,
                "OK",
                v["removal_person_hours"],
                "+",
                v["installation_person_hours"],
                "h direct",
                "(approx)" if v.get("approximate_mapping") else "",
            )
        else:
            print(k, "MISSING", v.get("sought_block"))
    return 0 if all(v.get("configured") for v in payload["repairs"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
