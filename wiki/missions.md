# Missions · 镖单

One contract at a time. Taken at a settlement's **镖单** board; a lost battle voids the
bond. While one is in hand, a gold **caption** rides over the map and a dashed line marks
the target. *(`world.js cityJobs / takeJob / renderContract / applyBattleResult`)*

| Mission | Target | Pays on | Pay formula | Battle scenario |
|---|---|---|---|---|
| **押镖** escort | a city/town (3 nearest, 1 if hunted) | arrival | `40 + days × 48` | — (just travel) |
| **攻破** raze 山寨 | a known standing 寨 | razing it (stand on it → 攻寨) | `180 + days_to_寨 × 44` | the lair's own — `gongzhai` (攻寨) or `shouqiao` (水寨) |
| **剿匪** hunt band | a known roaming bandit/raider | beating it in the field | `120 + days_to_band × 36` | the encounter terrain — `jiebiao`/`duijue`/… |

- **`days`** = `ceil(move-cost / 8)` from where you stand when you take it.
- Bands & 寨 must be **spotted** to be offered — discover by sight or buy a 客栈 rumor (reveals the 寨 *and* its band, so both jobs appear).
- Razing a 寨 disbands its band, so it also voids any 剿匪 bond on that band.
- At **恶名 ≥ 6** the board is empty (nobody bonds cargo to the hunted).

## 劫道 (waylay) — the bureau turns bandit
Not a board job: click a **商队/巡骑** within reach to ambush it. *(`world.js offerWaylay`)*

| Prey | loot | 恶名 | scenario |
|---|---|---|---|
| 商队 caravan | 150两 | +3 | `jiebiao` |
| 巡骑 patrol | 60两 | +4 | `duijue` |

### Add / delete a mission type
1. Push entries in `cityJobs()` (give them a `kind`, `target`, `name`, `pay`).
2. Handle the payout in `applyBattleResult()` — under the matching `pend.kind`, or in the
   encounter branch keyed on `world.contract.kind` (that's how **剿匪** pays).
3. If it marks a map target, add a case to `renderContract()`.
Delete = remove those. The board rendering & 接单 button are generic — no change needed.
