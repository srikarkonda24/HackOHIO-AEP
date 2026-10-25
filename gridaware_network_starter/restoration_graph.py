"""Graph connectivity with switch states for illustrative restoration."""
from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
NETWORK_PATH = REPO_ROOT / "config" / "restoration" / "illustrative_network_v2.json"


def load_network() -> dict[str, Any]:
    return json.loads(NETWORK_PATH.read_text(encoding="utf-8"))


def initial_switch_states(net: dict[str, Any]) -> dict[str, str]:
    return {s["id"]: s["initial_state"] for s in net.get("switches", [])}


@dataclass
class NetworkState:
    damaged: set[str] = field(default_factory=set)
    repaired: set[str] = field(default_factory=set)
    switch_states: dict[str, str] = field(default_factory=dict)

    def copy(self) -> NetworkState:
        return NetworkState(
            damaged=set(self.damaged),
            repaired=set(self.repaired),
            switch_states=dict(self.switch_states),
        )


def new_state(net: dict[str, Any], damaged: set[str]) -> NetworkState:
    return NetworkState(
        damaged=set(damaged),
        repaired=set(),
        switch_states=initial_switch_states(net),
    )


def _build_adjacency(net: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    adj: dict[str, list[dict[str, Any]]] = {}
    for edge in net["edges"]:
        adj.setdefault(edge["from"], []).append(edge)
    return adj


def _edge_available(net: dict[str, Any], edge: dict[str, Any], state: NetworkState) -> bool:
    comp = edge.get("requires_component")
    if comp and comp in state.damaged and comp not in state.repaired:
        return False
    sw = edge.get("requires_switch")
    if sw:
        need = edge.get("requires_switch_state", "closed")
        if state.switch_states.get(sw) != need:
            return False
    block_sw = edge.get("blocked_when_switch")
    if block_sw:
        if state.switch_states.get(block_sw) == edge.get("blocked_when_switch_state"):
            return False
    return True


def is_node_energized(net: dict[str, Any], node_id: str, state: NetworkState) -> bool:
    src = net["source_node_id"]
    if node_id == src:
        return True
    adj = _build_adjacency(net)
    queue = deque([src])
    seen = {src}
    while queue:
        node = queue.popleft()
        if node == node_id:
            return True
        for edge in adj.get(node, []):
            if not _edge_available(net, edge, state):
                continue
            nxt = edge["to"]
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return False


def is_group_connected(net: dict[str, Any], group_id: str, state: NetworkState) -> bool:
    for g in net["customer_groups"]:
        if g["id"] == group_id:
            return is_node_energized(net, g["node_id"], state)
    return False


def outage_groups(net: dict[str, Any], state: NetworkState) -> dict[str, bool]:
    return {
        g["id"]: not is_group_connected(net, g["id"], state)
        for g in net["customer_groups"]
    }


def restoration_snapshot(
    net: dict[str, Any],
    damaged: set[str],
    repaired: set[str],
    switch_states: dict[str, str] | None = None,
) -> dict[str, Any]:
    state = NetworkState(
        damaged=set(damaged),
        repaired=set(repaired),
        switch_states=switch_states or initial_switch_states(net),
    )
    return snapshot_from_state(net, state)


def snapshot_from_state(net: dict[str, Any], state: NetworkState) -> dict[str, Any]:
    statuses = outage_groups(net, state)
    return {
        "groups": statuses,
        "simulated_outage_group_ids": [gid for gid, out in statuses.items() if out],
        "powered_group_ids": [gid for gid, out in statuses.items() if not out],
        "switch_states": dict(state.switch_states),
    }


def job_precedence(net: dict[str, Any]) -> dict[str, set[str]]:
    """Documented repair precedence for illustrative radial v2."""
    prec: dict[str, set[str]] = {c["id"]: set() for c in net["components"]}
    trunk = {"C", "E", "F", "G"}
    for cid in prec:
        if cid != "A":
            prec[cid].add("A")
    for cid in trunk:
        if cid in prec:
            prec[cid].add("D")
    return prec


def is_group_connected_legacy(
    net: dict[str, Any],
    group_id: str,
    damaged: set[str],
    repaired: set[str],
) -> bool:
    state = NetworkState(
        damaged=set(damaged),
        repaired=set(repaired),
        switch_states=initial_switch_states(net),
    )
    return is_group_connected(net, group_id, state)
