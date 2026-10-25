"""One-off diagnosis of home ETA vs labor (run from gridaware_network_starter)."""
from __future__ import annotations

from repair_labor import load_labor_config, repair_duration_hours
from restoration_graph import load_network
from restoration_optimizer import run_restoration_scenario

labor = load_labor_config()
net = load_network()
print("=== AEP labor per repair type (4 workers, qty=1) ===")
for rt in sorted({c["repair_type"] for c in net["components"]}):
    d = repair_duration_hours(rt, workers_per_crew=4, config=labor)
    direct = d["removal_person_hours"] + d["installation_person_hours"]
    print(
        f"  {rt}: direct={direct:.3f} person-h central={d['central_repair_hours']}h "
        f"(ILM={d['indirect_labor_multiplier']})"
    )

scenarios = [
    ("1 comp B", ["B"]),
    ("1 comp C (home path)", ["C"]),
    ("4 comp A,B,C,D", ["A", "B", "C", "D"]),
    ("7 all", ["A", "B", "C", "D", "E", "F", "G"]),
]
for workers in (4, 12):
    print(f"\n=== total_workers={workers}, workers_per_crew=4 ===")
    for label, dmg in scenarios:
        r = run_restoration_scenario(
            damaged_component_ids=dmg,
            total_workers=workers,
            workers_per_crew=4,
            enable_step_restoration=True,
        )
        step = r["step_restoration_optimized"]
        if not step:
            print(f"{label}: NO SCHEDULE")
            continue
        res1 = step["group_restoration_times"].get("RES1")
        all_at = step["all_groups_restored_at"]
        print(f"{label}: crews={step['crew_count']} RES1={res1}h all_groups={all_at}h")
        for t in step["timeline"]:
            if t.get("event") == "repair_complete":
                lab = t.get("labor", {})
                print(
                    f"    repair {t['component_id']} crew{t['crew_index']} "
                    f"{t['start_hours']}-{t['finish_hours']}h qty={lab.get('quantity')}"
                )
