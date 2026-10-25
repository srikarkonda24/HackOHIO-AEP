# GridAware proactive outage alerts (Stage 6)

## Purpose

Demonstrate a **simulated** customer notification lifecycle driven by **deterministic rules** on top of existing GridAware outputs:

- Stage 4 historical weather **relative risk** (`/customers/{id}/risk-assessment`)
- Stage 5 restoration **graph snapshots**, `group_restoration_times`, and playback timeline events

No LLM decides whether an alert fires. No SMS/email is sent. No AEP enrollment is implied.

## Demo session persistence

- Browser stores `gridaware_demo_alert_session_id` in `localStorage`.
- FastAPI keeps session state **in memory** keyed by that ID (resets when the API process restarts).
- Preferences, deduplication state, and the inbox survive navigation between `/prediction`, `/restoration`, and `/alerts`.

## Alert types and eligibility

| Type | Trigger |
|------|---------|
| **Storm preparation** | After **Calculate Risk**, server recomputes risk. HIGH → preview if notifications on. MEDIUM → only if user opted in. LOW → none. Duplicate assessment IDs are ignored. |
| **Modeled outage** | On **committed** restoration simulation (not damage preview), modeled home (`RES1`) transitions **powered → unpowered**. One alert per simulation run ID. |
| **ETA update** | After a **new** committed run, modeled home ETA **day category** changes vs previous committed category (uses `group_restoration_times[RES1]`, not network makespan). |
| **Power restored** | Playback time reaches backend `group_restored` time for `RES1` on the active simulation run (once per run). |

## API (`/alerts`)

| Method | Path | Role |
|--------|------|------|
| GET | `/alerts/session/{session_id}` | Preferences + inbox |
| PUT | `/alerts/session/{session_id}/preferences` | Enable/channel/medium-risk opt-in |
| POST | `/alerts/session/{session_id}/reset` | Clear demo |
| POST | `/alerts/session/{session_id}/mark-read` | Clear unread badge |
| POST | `/alerts/session/{session_id}/evaluate/risk-preparation` | Server-side risk + prep rules |
| POST | `/alerts/session/{session_id}/evaluate/restoration-committed` | Outage + ETA rules |
| POST | `/alerts/session/{session_id}/evaluate/restoration-playback` | Restored rule |
| POST | `/alerts/utils/sim-run-id` | Stable hash for deduplication |

## Demo script (four alerts)

1. **Prediction:** Load `000052580`, use **Severe Windstorm** or custom inputs → **Calculate Risk** (HIGH) → preparation alert.
2. **Restoration:** Damage equipment affecting **Your Home** (e.g. transformer **C**), **Simulate Restoration** → outage alert.
3. **Restoration:** Change workers or storm/access settings so home ETA **category** shifts → run again → ETA update.
4. **Restoration:** Play timeline until home restores → power restored alert.

Use **Reset demo alerts** on `/alerts` to repeat for judges.

## Limitations

- In-memory sessions only; not production notification infrastructure.
- Restoration demo uses illustrative network group `RES1`, not live premise GIS.
- Suppressed rule outcomes may be omitted from the inbox (only **previewed** alerts are shown as customer notifications).
