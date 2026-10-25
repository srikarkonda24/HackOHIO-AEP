"""Create minimal workbook matching AEP sheet layout for CI/tests only."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "Install_Labor_HackOHIO_minimal.xlsx"


def main() -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Labor time material related"
    ws.append(
        [
            "Construction Unit",
            "Description",
            "Removal Person Hours",
            "Installation Person Hours",
        ]
    )
    rows = [
        ("CU-POLE-TEST", "Wood Pole Class 45 replacement", 6.0, 10.0),
        ("CU-WIRE-TEST", "Primary conductor replacement segment", 4.0, 8.0),
        ("CU-XFMR-TEST", "Distribution transformer 25 kVA", 5.0, 9.0),
        ("CU-SW-TEST", "Switch gear replacement", 3.0, 7.0),
    ]
    for r in rows:
        ws.append(list(r))
    ilm = wb.create_sheet("Indirect Labor Multiplier")
    ilm["A1"] = "Indirect Labor Multiplier"
    ilm["B1"] = 4.5
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
