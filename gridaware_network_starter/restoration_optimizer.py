"""Repair and step-restoration scheduling (exhaustive, small graph)."""
from __future__ import annotations

from typing import Any

from repair_labor import load_labor_config, repair_duration_hours
from restoration_actions import (
    apply_repair,
    apply_switch_action,
    repair_preconditions_met,
    switching_preconditions_met,
)
from restoration_graph import (
    is_group_connected,
    job_precedence,
    load_network,
    new_state,
    snapshot_from_state,
)


def _component_map(net: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {c["id"]: c for c in net["components"]}


def _topo_sort_jobs(jobs: list[str], precedence: dict[str, set[str]]) -> list[str]:
    """Order jobs so upstream dependencies are repaired first."""
    remaining = set(jobs)
    ordered: list[str] = []
    while remaining:
        ready = sorted(
            j for j in remaining if precedence.get(j, set()).issubset(set(ordered))
        )
        if not ready:
            ready = sorted(remaining)
        pick = ready[0]
        ordered.append(pick)
        remaining.remove(pick)
    return ordered


def _full_crews(total_workers: int, workers_per_crew: int) -> int:
    if workers_per_crew < 2 or workers_per_crew > 8:
        raise ValueError("workers_per_crew must be between 2 and 8")
    if total_workers < workers_per_crew:
        return 0
    return total_workers // workers_per_crew


def _switch_action_map(net: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {a["id"]: a for a in net.get("switching_actions", [])}


def _action_duration(
    net: dict[str, Any],
    action: dict[str, Any],
    *,
    workers_per_crew: int,
    labor_config: dict[str, Any],
    storm_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if action["type"] == "repair":
        comp = _component_map(net)[action["component_id"]]
        qty = 1.0
        if storm_ctx:
            qty = float(
                storm_ctx.get("repair_quantity_by_component", {}).get(
                    action["component_id"], 1.0
                )
            )
        return repair_duration_hours(
            comp["repair_type"],
            workers_per_crew=workers_per_crew,
            quantity=qty,
            config=labor_config,
        )
    sw_def = _switch_action_map(net)[action["action_id"]]
    hours = float(sw_def["duration_hours"])
    return {
        "central_repair_hours": hours,
        "eta_hours_low": round(hours * 0.9, 4),
        "eta_hours_high": round(hours * 1.1, 4),
        "action_id": action["action_id"],
    }


def _simulate_action_sequence(
    net: dict[str, Any],
    damaged: set[str],
    sequence: list[dict[str, Any]],
    *,
    total_workers: int,
    workers_per_crew: int,
    labor_config: dict[str, Any],
    storm_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    n_crews = min(3, _full_crews(total_workers, workers_per_crew))
    if not damaged and not sequence:
        state = new_state(net, set())
        snap = snapshot_from_state(net, state)
        return _empty_schedule(n_crews, snap)

    if n_crews == 0:
        raise ValueError("Not enough workers for one full crew")

    precedence = job_precedence(net)
    state = new_state(net, damaged)
    mobilization = float((storm_ctx or {}).get("crew_mobilization_hours", 0.0))
    access_by_comp = (storm_ctx or {}).get("access_ready_hours_by_component", {})
    crew_available = [mobilization] * n_crews
    timeline: list[dict[str, Any]] = []
    group_restore: dict[str, float | None] = {g["id"]: None for g in net["customer_groups"]}
    for g in net["customer_groups"]:
        if is_group_connected(net, g["id"], state):
            group_restore[g["id"]] = 0.0

    def record_restores(time: float) -> None:
        snap = snapshot_from_state(net, state)
        for gid, is_out in snap["groups"].items():
            if not is_out and group_restore[gid] is None:
                group_restore[gid] = time
                timeline.append(
                    {
                        "time_hours": round(time, 4),
                        "event": "group_restored",
                        "group_id": gid,
                        "snapshot": snap,
                    }
                )

    for action in sequence:
        if action["type"] == "repair":
            ok, reason = repair_preconditions_met(
                net, action["component_id"], state, precedence
            )
            if not ok:
                raise ValueError(f"Infeasible repair {action['component_id']}: {reason}")
        else:
            sw = _switch_action_map(net)[action["action_id"]]
            ok, reason = switching_preconditions_met(net, sw, state)
            if not ok:
                raise ValueError(f"Infeasible switch {action['action_id']}: {reason}")

        labor = _action_duration(
            net,
            action,
            workers_per_crew=workers_per_crew,
            labor_config=labor_config,
            storm_ctx=storm_ctx,
        )
        duration = labor["central_repair_hours"]
        crew_idx = min(range(n_crews), key=lambda i: crew_available[i])
        if action["type"] == "repair":
            earliest = float(access_by_comp.get(action["component_id"], mobilization))
        else:
            earliest = mobilization
        start = max(crew_available[crew_idx], earliest)
        finish = start + duration
        crew_available[crew_idx] = finish

        if action["type"] == "repair":
            state = apply_repair(state, action["component_id"])
            timeline.append(
                {
                    "time_hours": round(finish, 4),
                    "event": "repair_complete",
                    "component_id": action["component_id"],
                    "crew_index": crew_idx,
                    "start_hours": round(start, 4),
                    "finish_hours": round(finish, 4),
                    "labor": labor,
                }
            )
        else:
            sw = _switch_action_map(net)[action["action_id"]]
            state = apply_switch_action(state, sw)
            timeline.append(
                {
                    "time_hours": round(finish, 4),
                    "event": "switching_complete",
                    "action_id": action["action_id"],
                    "switch_id": sw["switch_id"],
                    "new_state": sw["target_state"],
                    "reason": sw.get("description"),
                    "crew_index": crew_idx,
                    "start_hours": round(start, 4),
                    "finish_hours": round(finish, 4),
                    "labor": labor,
                    "snapshot": snapshot_from_state(net, state),
                }
            )
        record_restores(finish)

    snap = snapshot_from_state(net, state)
    for gid in group_restore:
        if group_restore[gid] is None and not snap["groups"][gid]:
            group_restore[gid] = timeline[-1]["time_hours"] if timeline else 0.0

    total_customers = sum(g["simulated_customer_count"] for g in net["customer_groups"])
    weighted = 0.0
    customer_hours = 0.0
    for g in net["customer_groups"]:
        t = group_restore[g["id"]]
        if t is None:
            customer_hours += 1e6 * g["simulated_customer_count"]
            continue
        weighted += g["simulated_customer_count"] * t
        customer_hours += g["simulated_customer_count"] * t
    weighted /= total_customers if total_customers else 1

    makespan = max((t for t in group_restore.values() if t is not None), default=0.0)
    if any(t is None for t in group_restore.values()):
        makespan = None

    return {
        "strategy": sequence,
        "crew_count": n_crews,
        "timeline": timeline,
        "group_restoration_times": {
            k: (None if v is None else round(v, 4)) for k, v in group_restore.items()
        },
        "all_groups_restored_at": None if makespan is None else round(makespan, 4),
        "weighted_customer_restoration_time": round(weighted, 4),
        "customer_weighted_outage_person_hours": round(customer_hours, 4),
        "final_snapshot": snap,
    }


def _empty_schedule(n_crews: int, snap: dict[str, Any]) -> dict[str, Any]:
    groups = {g: 0.0 for g in snap["powered_group_ids"]}
    for gid in snap["simulated_outage_group_ids"]:
        groups[gid] = 0.0
    all_ids = groups.keys() | set(snap["groups"].keys())
    return {
        "strategy": [],
        "crew_count": n_crews,
        "timeline": [],
        "group_restoration_times": {g: 0.0 for g in all_ids},
        "all_groups_restored_at": 0.0,
        "weighted_customer_restoration_time": 0.0,
        "customer_weighted_outage_person_hours": 0.0,
        "final_snapshot": snap,
    }


def _objective_key(net: dict[str, Any], schedule: dict[str, Any]) -> tuple:
    gr = schedule["group_restoration_times"]
    h = gr.get("HOSPITAL")
    f = gr.get("FIRE")
    res_score = 0.0
    for g in net["customer_groups"]:
        if g["id"] in ("HOSPITAL", "FIRE"):
            continue
        t = gr.get(g["id"])
        if t is None:
            res_score += 1e9
        else:
            res_score += t * g["simulated_customer_count"]
    return (
        1e12 if h is None else h,
        1e6 if f is None else f,
        res_score,
        schedule.get("all_groups_restored_at") or 1e9,
    )


def _generate_sequences(
    net: dict[str, Any],
    damaged: set[str],
    *,
    allow_switching: bool,
) -> list[list[dict[str, Any]]]:
    """DFS build feasible action sequences (tractable for demo graph)."""
    precedence = job_precedence(net)
    switch_ids = list(_switch_action_map(net).keys()) if allow_switching else []
    repairs_needed = sorted(damaged)
    sequences: list[list[dict[str, Any]]] = []

    def dfs(
        state,
        repairs_done: set[str],
        switches_done: set[str],
        seq: list[dict[str, Any]],
    ) -> None:
        if repairs_done == damaged:
            sequences.append(list(seq))
            return
        if len(seq) > 14:
            return

        for comp in repairs_needed:
            if comp in repairs_done:
                continue
            ok, _ = repair_preconditions_met(net, comp, state, precedence)
            if not ok:
                continue
            nxt = apply_repair(state, comp)
            seq.append({"type": "repair", "component_id": comp})
            dfs(nxt, repairs_done | {comp}, switches_done, seq)
            seq.pop()

        if allow_switching:
            for sid in switch_ids:
                if sid in switches_done:
                    continue
                sw = _switch_action_map(net)[sid]
                ok, _ = switching_preconditions_met(net, sw, state)
                if not ok:
                    continue
                nxt = apply_switch_action(state, sw)
                seq.append({"type": "switch", "action_id": sid})
                dfs(nxt, repairs_done, switches_done | {sid}, seq)
                seq.pop()

    from restoration_graph import new_state

    dfs(new_state(net, damaged), set(), set(), [])
    if not sequences and not damaged:
        sequences.append([])
    return sequences


def _simulate_schedule(
    net: dict[str, Any],
    damaged: set[str],
    job_order: list[str],
    *,
    total_workers: int,
    workers_per_crew: int,
    labor_config: dict[str, Any],
    storm_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Legacy repair-only path (v1 compatibility shape)."""
    precedence = job_precedence(net)
    ordered = _topo_sort_jobs([j for j in job_order if j in damaged], precedence)
    seq = [{"type": "repair", "component_id": j} for j in ordered]
    result = _simulate_action_sequence(
        net,
        damaged,
        seq,
        total_workers=total_workers,
        workers_per_crew=workers_per_crew,
        labor_config=labor_config,
        storm_ctx=storm_ctx,
    )
    jobs = [t for t in result["timeline"] if t["event"] == "repair_complete"]
    return {
        "crew_count": result["crew_count"],
        "jobs": jobs,
        "restoration_events": result["timeline"],
        "group_restoration_times": result["group_restoration_times"],
        "all_groups_restored_at": result["all_groups_restored_at"],
        "weighted_customer_restoration_time": result["weighted_customer_restoration_time"],
        "final_snapshot": result["final_snapshot"],
        "repair_order": job_order,
    }


def _best_sequence(
    net: dict[str, Any],
    damaged: set[str],
    *,
    allow_switching: bool,
    total_workers: int,
    workers_per_crew: int,
    labor_config: dict[str, Any],
    storm_ctx: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    candidates = _generate_sequences(net, damaged, allow_switching=allow_switching)
    best = None
    best_sched = None
    for seq in candidates:
        try:
            sched = _simulate_action_sequence(
                net,
                damaged,
                seq,
                total_workers=total_workers,
                workers_per_crew=workers_per_crew,
                labor_config=labor_config,
                storm_ctx=storm_ctx,
            )
        except ValueError:
            continue
        key = _objective_key(net, sched)
        if best is None or key < best:
            best = key
            best_sched = sched
    return best_sched


def run_restoration_scenario(
    *,
    damaged_component_ids: list[str],
    total_workers: int,
    workers_per_crew: int,
    baseline_order: list[str] | None = None,
    enable_step_restoration: bool = True,
    damage_severity: str = "minor",
    access_conditions: str = "normal",
    extra_mobilization_hours: float = 0.0,
) -> dict[str, Any]:
    from restoration_storm import labor_preview_for_damaged, resolve_storm_context

    net = load_network()
    labor = load_labor_config()
    if _full_crews(total_workers, workers_per_crew) == 0:
        raise ValueError("Not enough workers for one full crew")
    valid_ids = {c["id"] for c in net["components"]}
    damaged = {c for c in damaged_component_ids if c in valid_ids}
    if len(damaged) != len(damaged_component_ids):
        raise ValueError(f"Invalid component ids: {sorted(set(damaged_component_ids) - valid_ids)}")

    from restoration_graph import new_state, snapshot_from_state

    initial = snapshot_from_state(net, new_state(net, damaged))
    storm_ctx = resolve_storm_context(
        net,
        damaged,
        damage_severity=damage_severity,  # type: ignore[arg-type]
        access_conditions=access_conditions,  # type: ignore[arg-type]
        extra_mobilization_hours=extra_mobilization_hours,
    )

    if not damaged:
        empty = _simulate_action_sequence(
            net,
            set(),
            [],
            total_workers=total_workers,
            workers_per_crew=workers_per_crew,
            labor_config=labor,
            storm_ctx=storm_ctx,
        )
        return {
            "network_version": net["network_version"],
            "damaged_component_ids": [],
            "initial_snapshot": initial,
            "repair_only": empty,
            "step_restoration": empty,
            "comparison": {"hospital_restore_delta_hours": 0.0},
            "labor_config_metadata": _labor_meta(labor),
            "limitations": _limitations(net),
        }

    repair_only_best = _best_sequence(
        net,
        damaged,
        allow_switching=False,
        total_workers=total_workers,
        workers_per_crew=workers_per_crew,
        labor_config=labor,
        storm_ctx=storm_ctx,
    )
    step_best = (
        _best_sequence(
            net,
            damaged,
            allow_switching=True,
            total_workers=total_workers,
            workers_per_crew=workers_per_crew,
            labor_config=labor,
            storm_ctx=storm_ctx,
        )
        if enable_step_restoration
        else None
    )

    base_order = _topo_sort_jobs(list(damaged), job_precedence(net))
    try:
        baseline = _simulate_schedule(
            net,
            damaged,
            base_order,
            total_workers=total_workers,
            workers_per_crew=workers_per_crew,
            labor_config=labor,
            storm_ctx=storm_ctx,
        )
    except ValueError:
        baseline = None

    h_repair = (repair_only_best or {}).get("group_restoration_times", {}).get("HOSPITAL")
    h_step = (step_best or {}).get("group_restoration_times", {}).get("HOSPITAL")
    delta = None
    if h_repair is not None and h_step is not None:
        delta = round(h_repair - h_step, 4)

    modeled_gid = net.get("modeled_customer_group_id", "RES1")
    schedule = step_best or repair_only_best
    home_hours = None
    network_hours = None
    if schedule:
        home_hours = schedule["group_restoration_times"].get(modeled_gid)
        network_hours = schedule.get("all_groups_restored_at")

    return {
        "network_version": net["network_version"],
        "damaged_component_ids": sorted(damaged),
        "initial_snapshot": initial,
        "storm_context": storm_ctx,
        "labor_preview": labor_preview_for_damaged(
            net, damaged, storm_ctx, workers_per_crew=workers_per_crew, labor_config=labor
        ),
        "modeled_customer_group_id": modeled_gid,
        "modeled_home_restore_hours": home_hours,
        "all_groups_restore_hours": network_hours,
        "baseline_repair_order": baseline,
        "repair_only_optimized": repair_only_best,
        "step_restoration_optimized": step_best,
        "comparison": {
            "hospital_restore_delta_hours": delta,
            "note": "Positive delta means step-restoration restores hospital sooner.",
            "repair_only_hospital_restore": h_repair,
            "step_restoration_hospital_restore": h_step,
        },
        "optimization_objective": (
            "Simulation policy (not AEP dispatch): safety/precedence, then hospital, "
            "fire, weighted residential, makespan."
        ),
        "labor_config_metadata": _labor_meta(labor),
        "limitations": _limitations(net),
        "optimized": repair_only_best,
        "baseline": baseline,
    }


def _labor_meta(labor: dict[str, Any]) -> dict[str, Any]:
    src = str(labor.get("source_workbook", ""))
    synthetic = (
        "fixture" in src.lower()
        or "minimal" in src.lower()
        or "synthetic" in str(labor.get("data_provenance", "")).lower()
    )
    return {
        "config_version": labor["config_version"],
        "source_workbook": labor.get("source_workbook"),
        "indirect_labor_multiplier": labor["indirect_labor_multiplier"],
        "data_provenance": labor.get("data_provenance"),
        "synthetic_labor_warning": synthetic,
        "replace_with_aep_workbook": labor.get("replace_with_aep_workbook"),
    }


def _limitations(net: dict[str, Any]) -> list[str]:
    return [
        "Illustrative network; switching actions include scenario-only tie assumptions.",
        "Not verified switching clearance or safety study.",
        "Priority policy is simulation-only, not AEP dispatch.",
    ] + ([net["disclaimer"]] if net.get("disclaimer") else [])


