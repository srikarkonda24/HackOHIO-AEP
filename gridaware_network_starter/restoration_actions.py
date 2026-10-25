"""Switching and repair action semantics."""
from __future__ import annotations

from typing import Any

from restoration_graph import NetworkState, is_group_connected, is_node_energized


def _component_ok(state: NetworkState, comp_id: str) -> bool:
    return comp_id not in state.damaged or comp_id in state.repaired


def switching_preconditions_met(
    net: dict[str, Any], action: dict[str, Any], state: NetworkState
) -> tuple[bool, str]:
    pre = action.get("preconditions", {})
    sw = state.switch_states
    for sid, need in pre.get("switch_states", {}).items():
        if sw.get(sid) != need:
            return False, f"Switch {sid} must be {need}"
    for comp in pre.get("components_intact", []):
        if not _component_ok(state, comp):
            return False, f"Component {comp} must be intact or repaired"
    for comp in pre.get("components_repaired", []):
        if comp not in state.repaired:
            return False, f"Component {comp} must be repaired first"
    if pre.get("source_reachable"):
        if not is_node_energized(net, net["source_node_id"], state):
            return False, "Source path not energized"
        if not _component_ok(state, "A"):
            return False, "Main supply component A required"
    damaged = state.damaged
    if "damaged_may_include" in pre:
        for comp in pre["damaged_may_include"]:
            if comp not in damaged:
                continue
        if "D" in pre.get("components_intact", []):
            if "D" in damaged and "D" not in state.repaired:
                return False, "Trunk D must be intact for tie close"
    return True, "ok"


def apply_switch_action(state: NetworkState, action: dict[str, Any]) -> NetworkState:
    nxt = state.copy()
    nxt.switch_states[action["switch_id"]] = action["target_state"]
    return nxt


def apply_repair(state: NetworkState, component_id: str) -> NetworkState:
    nxt = state.copy()
    nxt.repaired.add(component_id)
    return nxt


def repair_preconditions_met(
    net: dict[str, Any],
    component_id: str,
    state: NetworkState,
    precedence: dict[str, set[str]],
) -> tuple[bool, str]:
    for dep in precedence.get(component_id, set()):
        if dep in state.damaged and dep not in state.repaired:
            return False, f"Upstream repair {dep} required first"
    return True, "ok"
