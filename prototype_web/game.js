/* 血与银 · battle prototype — implements DESIGN.md §3 (M0/M1 staged ruleset):
   d100 under-chance (skill − defense + accuracy + height + surround, clamp 5–95,
   3-state morale multiplier), two-layer armor (head/body) with 25% head-hit crits,
   AP + Breath, initiative = base − breath spent, ZoC free strikes (hit cancels move),
   bleed, routs. Sim logic is plain functions over plain state (engine-agnostic core). */

"use strict";

/* any runtime error becomes visible on the page instead of a blank board */
window.addEventListener("error", (e) => {
  const el = document.getElementById("log");
  if (el) {
    const d = document.createElement("div");
    d.style.color = "#a02818"; d.style.fontWeight = "bold";
    d.textContent = "脚本错误 script error: " + e.message;
    el.appendChild(d);
  }
});

/* ---------------- hex math (pointy-top axial) ---------------- */
const SQRT3 = Math.sqrt(3);
const HEX = 33; // size
const DIRS = [[1,0],[1,-1],[0,-1],[-1,0],[-1,1],[0,1]];
const key = (q, r) => q + "," + r;
const hexDist = (a, b) => {
  const dq = a.q - b.q, dr = a.r - b.r;
  return (Math.abs(dq) + Math.abs(dr) + Math.abs(dq + dr)) / 2;
};
const hexToPix = (q, r) => ({
  x: HEX * SQRT3 * (q + r / 2) + 50,
  y: HEX * 1.5 * r + 50,
});

/* ---------------- map (built from scenarios/<id>.json — shared with the sim) ---------------- */
let COLS = 13, ROWS = 9;
const tiles = new Map(); // key -> {q,r,elev,terrain,moveCost}
let ROAD_PATH = [];      // hex keys, for the painted track
let scenario = null;     // the loaded scenario spec

function buildMap() {
  tiles.clear();
  const m = scenario.map;
  COLS = m.cols; ROWS = m.rows;
  const toKeys = (arr) => new Set((arr || []).map(k => key(k[0], k[1])));
  const road = toKeys(m.road);
  ROAD_PATH = (m.road || []).map(k => key(k[0], k[1]));
  const forest = toKeys(m.forest);
  const elev1 = toKeys(m.elev1);
  const elev2 = toKeys(m.elev2);
  const elev3 = toKeys(m.elev3);
  const wall = toKeys(m.wall);
  const cartK = m.cart ? key(m.cart[0], m.cart[1]) : null;
  for (let r = 0; r < ROWS; r++) {
    for (let col = 0; col < COLS; col++) {
      const q = col - (r >> 1);
      const k = key(q, r);
      let terrain = "grass", elev = 0, brCost = 2, impassable = false;
      if (forest.has(k)) terrain = "forest";
      if (elev1.has(k)) { terrain = "hill"; elev = 1; }
      if (elev2.has(k)) { terrain = "hill"; elev = 2; }
      if (elev3.has(k)) { terrain = "hill"; elev = 3; }
      if (road.has(k) && terrain === "grass") { terrain = "road"; brCost = 1; } // roads: half Breath
      if (k === cartK) { terrain = "cart"; impassable = true; }
      if (wall.has(k)) { terrain = "wall"; impassable = true; } // 寨墙：不可逾越
      tiles.set(k, { q, r, elev, terrain, brCost, impassable,
        moveCost: terrain === "forest" ? 3 : 2 });
    }
  }
}

/* ---------------- units ---------------- */
let UID = 0;
function mkUnit(t, q, r) {
  const u = Object.assign({
    id: ++UID, q, r, hp: t.hpMax,
    morale: "Steady", fledRounds: 0, bleed: 0, alive: true,
    ap: 0, attacksLeftHint: 0,
  }, JSON.parse(JSON.stringify(t)));
  const body = ARMOR[u.armor], helm = ARMOR[u.helmet];
  u.breathMax = u.breathBase - body.weight - helm.weight; // armor weight taxes Breath
  u.breath = u.breathMax;
  u.armorB = body.protect; u.armorH = helm.protect;
  u.armorName = body.label; u.helmName = helm.label;
  u.armorB0 = u.armorB; u.armorH0 = u.armorH; // starting values, for the bars
  return u;
}

const P = (id, n, glyph, t) => Object.assign({ id, name: n, glyph, side: "player" }, t);
const E = (id, n, glyph, t) => Object.assign({ id, name: n, glyph, side: "enemy" }, t);

function rosterTemplates() {
  return [
    P("wang", "王铁枪", "枪", { hpMax: 55, skill: 62, def: 10, shield: 0, resolve: 48,
      initBase: 96, breathBase: 87, armor: "pijia", helmet: "pikui",
      wpn: { kind: "melee", label: "长枪", hands: 2, reach: 2, acc: 20, dmin: 22, dmax: 32, armorEff: 0.9, pierce: 0.3, ap: 6, br: 15, special: { type: "spearwall", label: "枪林", ap: 3, br: 18 } },
      wpn2: { kind: "melee", label: "腰刀", hands: 1, acc: 10, dmin: 18, dmax: 26, armorEff: 1.0, pierce: 0.3, ap: 4, br: 12, bleed: true, special: { type: "decap", label: "斩首", ap: 5, br: 15, dmgMult: 1.3 } } }),
    P("liu", "刘三刀", "刀", { hpMax: 60, skill: 60, def: 6, shield: 15, resolve: 45,
      initBase: 104, breathBase: 87, armor: "pijia", helmet: "pikui",
      wpn: { kind: "melee", label: "腰刀", hands: 1, acc: 10, dmin: 22, dmax: 32, armorEff: 1.0, pierce: 0.3, ap: 4, br: 12, bleed: true, special: { type: "decap", label: "斩首", ap: 5, br: 15, dmgMult: 1.3 } } }),
    P("shi", "石敢当", "锤", { hpMax: 65, skill: 58, def: 5, shield: 0, resolve: 50,
      initBase: 90, breathBase: 93, armor: "tiejia", helmet: "tiekui",
      wpn: { kind: "melee", label: "大锤", hands: 2, acc: 5, dmin: 28, dmax: 40, armorEff: 2.0, pierce: 0.2, ap: 6, br: 18, breathDrain: 20, special: { type: "demolish", label: "碎甲", ap: 6, br: 20, armorMult: 3.0 } } }),
    P("yan", "燕小乙", "弓", { hpMax: 45, skill: 56, def: 8, shield: 0, resolve: 42,
      initBase: 112, breathBase: 94, armor: "bujia", helmet: "bumao",
      wpn: { kind: "ranged", label: "猎弓", hands: 2, acc: 10, dmin: 16, dmax: 26, armorEff: 0.6, pierce: 0.35, ap: 4, br: 8, range: 7, falloff: 3, special: { type: "aimed", label: "瞄准", ap: 6, br: 12, accBonus: 10, falloff: 2 } },
      wpn2: { kind: "melee", label: "匕首", hands: 1, acc: -15, dmin: 14, dmax: 22, armorEff: 0.0, pierce: 1.0, ap: 4, br: 10, noHead: true } }),
    E("duyan", "独眼龙", "刀", { hpMax: 50, skill: 52, def: 4, shield: 0, resolve: 38,
      initBase: 100, breathBase: 89, armor: "bujia", helmet: "bumao",
      wpn: { kind: "melee", label: "砍刀", hands: 1, acc: 10, dmin: 17, dmax: 26, armorEff: 1.0, pierce: 0.3, ap: 4, br: 12, bleed: true, special: { type: "decap", label: "斩首", ap: 5, br: 15, dmgMult: 1.3 } } }),
    E("erma", "二麻子", "刀", { hpMax: 50, skill: 52, def: 4, shield: 0, resolve: 38,
      initBase: 98, breathBase: 89, armor: "bujia", helmet: "bumao",
      wpn: { kind: "melee", label: "砍刀", hands: 1, acc: 10, dmin: 17, dmax: 26, armorEff: 1.0, pierce: 0.3, ap: 4, br: 12, bleed: true, special: { type: "decap", label: "斩首", ap: 5, br: 15, dmgMult: 1.3 } } }),
    E("xiaohu", "笑面虎", "斧", { hpMax: 55, skill: 54, def: 4, shield: 0, resolve: 40,
      initBase: 94, breathBase: 86, armor: "bujia", helmet: "pikui",
      wpn: { kind: "melee", label: "大斧", hands: 2, acc: 5, dmin: 30, dmax: 44, armorEff: 1.3, pierce: 0.25, ap: 6, br: 16, chop: true, special: { type: "sweep", label: "横扫", ap: 6, br: 20, acc: -10 } } }),
    E("yemao", "夜猫子", "弓", { hpMax: 42, skill: 50, def: 6, shield: 0, resolve: 36,
      initBase: 108, breathBase: 91, armor: "bujia", helmet: "none_h",
      wpn: { kind: "ranged", label: "猎弓", hands: 2, acc: 10, dmin: 14, dmax: 24, armorEff: 0.6, pierce: 0.35, ap: 4, br: 8, range: 7, falloff: 3, special: { type: "aimed", label: "瞄准", ap: 6, br: 12, accBonus: 10, falloff: 2 } },
      wpn2: { kind: "melee", label: "短刀", hands: 1, acc: 0, dmin: 14, dmax: 22, armorEff: 0.8, pierce: 0.3, ap: 4, br: 10 } }),
    E("diao", "坐山雕", "首", { hpMax: 70, skill: 62, def: 12, shield: 15, resolve: 55,
      initBase: 92, breathBase: 91, armor: "tiejia", helmet: "tiekui", leader: true,
      wpn: { kind: "melee", label: "九环刀", hands: 1, acc: 10, dmin: 24, dmax: 34, armorEff: 1.0, pierce: 0.3, ap: 4, br: 12, bleed: true, special: { type: "decap", label: "斩首", ap: 5, br: 15, dmgMult: 1.3 } } }),
    // ---- the assault specialists (攻寨 roster) ----
    P("chen", "陈短矛", "矛", { hpMax: 58, skill: 58, def: 8, shield: 15, resolve: 46,
      initBase: 100, breathBase: 89, armor: "pijia", helmet: "pikui",
      wpn: { kind: "melee", label: "短矛", hands: 1, acc: 15, dmin: 16, dmax: 24, armorEff: 0.9, pierce: 0.25, ap: 4, br: 11, special: { type: "spearwall", label: "枪阵", ap: 3, br: 16 } } }),
    P("he", "何九鞭", "鞭", { hpMax: 52, skill: 57, def: 7, shield: 0, resolve: 44,
      initBase: 106, breathBase: 90, armor: "bujia", helmet: "pikui",
      wpn: { kind: "melee", label: "九节鞭", hands: 1, acc: 5, dmin: 18, dmax: 28, armorEff: 0.9, pierce: 0.3, ap: 4, br: 13, ignoreShield: true, headBonus: 10, special: { type: "headhunt", label: "兜头", ap: 5, br: 16 } } }),
    P("lu", "鲁大弩", "弩", { hpMax: 48, skill: 54, def: 6, shield: 0, resolve: 45,
      initBase: 95, breathBase: 89, armor: "pijia", helmet: "bumao",
      wpn: { kind: "ranged", label: "弩", hands: 2, acc: 15, dmin: 22, dmax: 32, armorEff: 0.8, pierce: 0.5, ap: 4, br: 10, range: 6, falloff: 2, special: { type: "aimed", label: "瞄准", ap: 6, br: 14, accBonus: 10, falloff: 1 } },
      wpn2: { kind: "melee", label: "短刀", hands: 1, acc: 0, dmin: 14, dmax: 22, armorEff: 0.8, pierce: 0.3, ap: 4, br: 10 } }),
    E("shemao", "蛇矛子", "矛", { hpMax: 52, skill: 55, def: 6, shield: 0, resolve: 40,
      initBase: 96, breathBase: 89, armor: "pijia", helmet: "bumao",
      wpn: { kind: "melee", label: "长枪", hands: 2, reach: 2, acc: 20, dmin: 22, dmax: 32, armorEff: 0.9, pierce: 0.3, ap: 6, br: 15, special: { type: "spearwall", label: "枪林", ap: 3, br: 18 } } }),
  ];
}
/* deployments come from the scenario file (scenarios/<id>.json) */

/* ---------------- state ---------------- */
let units = [], round = 0, queue = [], qIdx = -1;
let busy = false, gameOver = false;
let moveInfo = null; // {costs:Map, prev:Map}
let battleStats = {}; // per-unit damage/kills for the end-of-battle summary
let selectedSkill = "attack"; // BB-style skill bar: "attack" | "special"; ground click always moves
let logEl, boardEl, unitLayer, fxLayer, highlightLayer;
let hoverPathEl = null;

/* armor tiers: protection is an ablative pool, weight taxes max Breath */
const ARMOR = {
  none_b: { label: "无甲", slot: "body", protect: 0, weight: 0 },
  bujia:  { label: "布甲", slot: "body", protect: 25, weight: 3 },
  pijia:  { label: "皮甲", slot: "body", protect: 60, weight: 8 },
  tiejia: { label: "铁甲", slot: "body", protect: 110, weight: 16 },
  none_h: { label: "无盔", slot: "head", protect: 0, weight: 0 },
  bumao:  { label: "布帽", slot: "head", protect: 15, weight: 1 },
  pikui:  { label: "皮盔", slot: "head", protect: 40, weight: 3 },
  tiekui: { label: "铁盔", slot: "head", protect: 80, weight: 7 },
};

const VERB = { 长枪: "刺击", 腰刀: "劈砍", 砍刀: "劈砍", 九环刀: "劈砍", 大锤: "锤击", 大斧: "重劈", 猎弓: "放箭", 匕首: "突刺", 短刀: "刺击", 短矛: "刺击", 九节鞭: "抽击", 弩: "发弩" };

const alive = (side) => units.filter(u => u.alive && (!side || u.side === side));
const at = (q, r) => units.find(u => u.alive && u.q === q && u.r === r);
const active = () => (qIdx >= 0 && qIdx < queue.length) ? queue[qIdx] : null;

const moraleMult = (u) => u.morale === "Wavering" ? 0.9 : u.morale === "Fleeing" ? 0.7 : 1.0;
const exertsZoC = (u) => u.alive && u.wpn.kind === "melee" && u.morale !== "Fleeing";
// BB: a one-handed weapon with an empty off-hand is double-gripped for +25% damage
const doubleGrip = (u) => u.wpn.kind === "melee" && u.wpn.hands === 1 && !u.shield;

const rint = (a, b) => a + Math.floor(Math.random() * (b - a + 1));
const d100 = () => rint(1, 100);
const sleep = (ms) => new Promise(res => setTimeout(res, ms));

/* ---------------- combat math (the locked §3.3 staged formula) ---------------- */
function specialOpts(sp) {
  switch (sp.type) {
    case "decap": return { mult: sp.dmgMult, fearMod: -10, tag: sp.label };
    case "demolish": return { armorOnly: true, armorMult: sp.armorMult, tag: sp.label };
    case "aimed": return { accMod: sp.accBonus, falloff: sp.falloff, tag: sp.label };
    case "sweep": return { accMod: sp.acc, tag: sp.label };
    case "headhunt": return { forceHead: true, tag: sp.label };
  }
  return {};
}

function hitBreakdown(atk, def, opts = {}) {
  const parts = [];
  const effSkill = Math.round(atk.skill * moraleMult(atk));
  parts.push([`武艺 skill${moraleMult(atk) !== 1 ? " ×" + moraleMult(atk) : ""}`, effSkill]);
  parts.push([`兵器准头 ${atk.wpn.label}`, atk.wpn.acc]);
  if (opts.accMod) parts.push([`特技 ${opts.tag || ""}`, opts.accMod]);

  // flails ignore the shield's base defense; a raised shield's extra still counts (BB)
  const shieldBase = def.shield || 0;
  const shieldBonus = (atk.wpn.ignoreShield ? 0 : shieldBase) + (def.shieldwall ? shieldBase : 0);
  const defBase = Math.round((def.def + shieldBonus) * moraleMult(def));
  parts.push([`对方招架/盾${def.shieldwall ? "·举盾×2" : ""}${moraleMult(def) !== 1 ? " ×" + moraleMult(def) : ""}`, -defBase]);

  const ta = tiles.get(key(atk.q, atk.r)), td = tiles.get(key(def.q, def.r));
  const hdiff = ta.elev - td.elev;
  if (hdiff !== 0) parts.push([hdiff > 0 ? "居高临下 height" : "仰攻 uphill", hdiff * 10]);

  if (atk.wpn.kind === "melee" && hexDist(atk, def) === 2) {
    parts.push(["隔位远刺 long thrust", -15]); // BB: 2-hex attacks −15 unless mastered
  }

  let surround = 0;
  if (atk.wpn.kind === "melee") {
    const adjAtk = neighborsOf(def).map(k => at(tiles.get(k).q, tiles.get(k).r))
      .filter(u => u && u.side === atk.side && u.wpn.kind === "melee" && u.morale !== "Fleeing").length;
    surround = Math.max(0, adjAtk - 1) * 5;
    if (surround) parts.push(["围攻 surround ×" + (surround / 5), surround]);
  }

  if (atk.wpn.kind === "ranged") {
    const dist = hexDist(atk, def);
    const fall = -Math.max(0, dist - 1) * (opts.falloff ?? atk.wpn.falloff);
    if (fall) parts.push([`距离 ${dist} 格 falloff`, fall]);
  }

  let chance = parts.reduce((s, p) => s + p[1], 0);
  chance = Math.max(5, Math.min(95, Math.round(chance)));
  return { parts, chance };
}

function neighborsOf(u) {
  const out = [];
  for (const [dq, dr] of DIRS) {
    const k = key(u.q + dq, u.r + dr);
    if (tiles.has(k)) out.push(k);
  }
  return out;
}

function applyHit(atk, def, isFree, opts = {}) {
  const bd = hitBreakdown(atk, def, opts);
  const roll = d100();
  const cls = atk.side === "player" ? "b" : "r";
  const tag = opts.tag ? `【${opts.tag}】` : isFree ? "【截击】" : "";
  if (roll > bd.chance) {
    log(`${tag}${atk.name} 攻 ${def.name}：${bd.chance}% — d100=${roll} → <b>挥空 MISS</b>`, cls);
    float(def, "MISS", "#7a7263");
    return false;
  }
  // head roll — the crit system (daggers' Puncture can't headshot)
  const headRoll = d100();
  const head = !!opts.forceHead || (!atk.wpn.noHead && headRoll <= 25 + (atk.wpn.headBonus || 0));
  let dmg = rint(atk.wpn.dmin, atk.wpn.dmax);
  if (doubleGrip(atk)) dmg = Math.round(dmg * 1.25); // empty off-hand
  if (opts.mult) dmg = Math.round(dmg * opts.mult);
  if (isFree && opts.halfDmg) dmg = Math.round(dmg * 0.5);
  const part = head ? "armorH" : "armorB";
  const armorBefore = def[part];
  let armorDmg, hpDmg, mult = 1;
  if (opts.armorOnly) { // 碎甲: pure armor destruction
    armorDmg = Math.min(armorBefore, Math.round(dmg * opts.armorMult));
    hpDmg = 0;
  } else {
    armorDmg = Math.min(armorBefore, Math.round(dmg * atk.wpn.armorEff));
    hpDmg = Math.max(0, Math.round(dmg * atk.wpn.pierce - 0.1 * armorBefore));
    if (armorDmg >= armorBefore) { // armor destroyed → overflow
      hpDmg += Math.max(0, Math.round(dmg * (1 - atk.wpn.pierce)) - armorBefore);
    }
    if (head) { mult = 1.5; if (atk.wpn.chop) mult = 2.25; }
    hpDmg = Math.round(hpDmg * mult);
  }
  def[part] = Math.max(0, armorBefore - armorDmg);
  def.hp = Math.max(0, def.hp - hpDmg);
  def.breath = Math.max(0, def.breath - (atk.wpn.breathDrain || 5));
  if (atk.wpn.bleed && hpDmg >= 6 && def.alive) def.bleed = 2;

  log(`${tag}${atk.name} 攻 ${def.name}：${bd.chance}% — d100=${roll} → 命中` +
      `${head ? `；部位 d100=${headRoll}≤25 → <b>爆头 ×${mult}</b>` : `（部位 d100=${headRoll}→身）`}` +
      `；伤 ${dmg} → 甲−${armorDmg}，血−${hpDmg}${def.bleed && atk.wpn.bleed && hpDmg >= 6 ? "，流血" : ""}`, cls);
  float(def, hpDmg > 0 ? "−" + hpDmg : "⛨−" + armorDmg, hpDmg > 0 ? "#a02818" : "#6f6450");
  if (battleStats[atk.id]) battleStats[atk.id].dmg += armorDmg + hpDmg;

  if (def.hp <= 0) { kill(def, atk, opts.fearMod || 0); }
  else if (hpDmg >= 15) { moraleCheck(def, -10, "重创"); }
  return true;
}

function kill(u, killer, fearMod = 0) {
  u.alive = false;
  if (killer && battleStats[killer.id]) battleStats[killer.id].kills++;
  log(`☠ <b>${u.name}</b> 倒下了${killer ? "（" + killer.name + " 所杀）" : ""}${fearMod ? " —— 杀法骇人，众皆胆寒" : ""}。`, "sys");
  // negative checks ripple through the victim's side, scaled by distance
  for (const ally of alive(u.side)) {
    if (ally === u) continue;
    const d = hexDist(ally, u);
    if (d <= 5) moraleCheck(ally, (u.leader ? -15 : 0) + fearMod, "同伴阵亡");
  }
  renderUnits();
  checkEnd();
}

function moraleCheck(u, mod, reason) {
  if (!u.alive || u.morale === "Fleeing") return;
  const adj = neighborsOf(u).map(k => at(tiles.get(k).q, tiles.get(k).r))
    .filter(x => x && x.side === u.side).length;
  const target = u.resolve + adj * 3 + mod;
  const roll = d100();
  if (roll <= target) {
    log(`${u.name} 胆识考验（${reason}）：d100=${roll} ≤ ${target} → 稳住`, "sys");
  } else {
    u.morale = u.morale === "Steady" ? "Wavering" : "Fleeing";
    log(`${u.name} 胆识考验（${reason}）：d100=${roll} > ${target} → <b>${u.morale === "Wavering" ? "动摇" : "溃逃！"}</b>`, "sys");
    if (u.morale === "Fleeing") u.fledRounds = 0;
  }
}

/* ---------------- movement ---------------- */
function dijkstra(u, apBudget, brBudget) {
  const start = key(u.q, u.r);
  const costs = new Map([[start, 0]]); // AP along best path
  const brc = new Map([[start, 0]]);   // Breath along that path (roads cost 1, rest 2)
  const prev = new Map();
  const frontier = [[0, start]];
  while (frontier.length) {
    frontier.sort((a, b) => a[0] - b[0]);
    const [c, k] = frontier.shift();
    if (c > (costs.get(k) ?? Infinity)) continue;
    const t = tiles.get(k);
    for (const [dq, dr] of DIRS) {
      const nk = key(t.q + dq, t.r + dr);
      const nt = tiles.get(nk);
      if (!nt || nt.impassable || at(nt.q, nt.r)) continue;
      const climb = Math.max(0, nt.elev - t.elev);
      const nc = c + nt.moveCost + climb;
      const nb = (brc.get(k) ?? 0) + nt.brCost;
      if (nc <= apBudget && nb <= brBudget && nc < (costs.get(nk) ?? Infinity)) {
        costs.set(nk, nc); brc.set(nk, nb); prev.set(nk, k);
        frontier.push([nc, nk]);
      }
    }
  }
  return { costs, brc, prev };
}

const breathOfPath = (path) =>
  path.slice(1).reduce((s, k) => s + tiles.get(k).brCost, 0);

function pathTo(prev, destK) {
  const path = [destK];
  while (prev.has(path[0])) path.unshift(prev.get(path[0]));
  return path; // includes start
}

async function execMove(u, path, totalCost) {
  // step-by-step; leaving a hex adjacent to a melee enemy triggers free strikes
  u.ap -= totalCost;
  u.breath = Math.max(0, u.breath - breathOfPath(path)); // roads drain half
  const struck = new Set(), wallStruck = new Set();
  for (let i = 0; i + 1 < path.length; i++) {
    const here = tiles.get(path[i]);
    const zocers = neighborsOf({ q: here.q, r: here.r })
      .map(k => at(tiles.get(k).q, tiles.get(k).r))
      .filter(e => e && e.side !== u.side && exertsZoC(e) && !struck.has(e.id));
    let blocked = false;
    for (const e of zocers) {
      struck.add(e.id);
      if (applyHit(e, u, true)) blocked = true;
      if (!u.alive) return;
    }
    if (blocked) {
      log(`${u.name} 被截击打断，止步原地（行动力已耗）。`, "sys");
      renderUnits(); return;
    }
    // spearwall: approaching into a waiting spear's reach draws a half-damage thrust;
    // a hit stops the approach cold (BB: spearwall halts movement on hit)
    const next = tiles.get(path[i + 1]);
    const walls = neighborsOf({ q: next.q, r: next.r })
      .map(k => at(tiles.get(k).q, tiles.get(k).r))
      .filter(e => e && e.side !== u.side && e.spearwall && e.alive && e.morale !== "Fleeing" && !wallStruck.has(e.id));
    let halted = false;
    for (const e of walls) {
      wallStruck.add(e.id);
      if (applyHit(e, u, true, { halfDmg: true, tag: "枪林" })) halted = true;
      if (!u.alive) return;
    }
    if (halted) {
      log(`${u.name} 撞上枪林，被逼停在枪下。`, "sys");
      renderUnits(); return;
    }
    u.q = next.q; u.r = next.r;
    renderUnits();
    await sleep(110);
  }
}

/* ---------------- turn engine ---------------- */
function startRound() {
  round++;
  document.getElementById("roundlabel").textContent = `第 ${round} 回合`;
  queue = alive().slice().sort((a, b) =>
    (b.initBase - (b.breathMax - b.breath)) - (a.initBase - (a.breathMax - a.breath)));
  qIdx = -1;
  log(`—— 第 ${round} 回合 ——`, "sys");
  nextTurn();
}

async function nextTurn() {
  if (gameOver) return;
  qIdx++;
  renderQueue();
  if (qIdx >= queue.length) { startRound(); return; }
  const u = queue[qIdx];
  if (!u.alive) { nextTurn(); return; }

  // turn upkeep
  u.shieldwall = false; // raised shield lasts until the bearer's next turn
  u.spearwall = false;  // so does the spear hedge
  selectedSkill = "attack";
  u.breath = Math.min(u.breathMax, u.breath + 15);
  u.ap = 9;
  if (u.bleed > 0) {
    u.bleed--; u.hp = Math.max(0, u.hp - 5);
    log(`${u.name} 流血 −5`, "sys"); float(u, "−5", "#a02818");
    if (u.hp <= 0) { kill(u, null); nextTurn(); return; }
  }
  if (u.morale === "Fleeing") {
    u.fledRounds++;
    const adjEnemy = neighborsOf(u).some(k => { const o = at(tiles.get(k).q, tiles.get(k).r); return o && o.side !== u.side; });
    if (!adjEnemy && d100() <= u.resolve + 10 * u.fledRounds) {
      u.morale = "Wavering";
      log(`${u.name} 缓过神来，止住了逃势（动摇）。`, "sys");
    } else {
      busy = true; await fleeMove(u); busy = false;
      if (u.alive) { nextTurn(); return; }
      nextTurn(); return;
    }
  }
  renderUnits(); renderCard();
  if (u.side === "enemy") {
    busy = true; await aiTurn(u); busy = false;
    nextTurn();
  } else {
    moveInfo = dijkstra(u, u.ap, u.breath);
    renderUnits(); renderCard();
    // player acts via clicks; End Turn advances
  }
}

async function fleeMove(u) {
  const edgeCol = u.side === "enemy" ? COLS - 1 : 0;
  const info = dijkstra(u, u.ap, u.breath);
  let best = null, bestScore = Infinity;
  for (const [k] of info.costs) {
    const t = tiles.get(k);
    const col = t.q + (t.r >> 1);
    const score = Math.abs(edgeCol - col);
    if (score < bestScore) { bestScore = score; best = k; }
  }
  if (best && best !== key(u.q, u.r)) {
    await execMove(u, pathTo(info.prev, best), info.costs.get(best));
  }
  const col = u.q + (u.r >> 1);
  if (u.alive && (col === edgeCol)) {
    u.alive = false;
    u.escaped = true;
    log(`${u.name} 逃离了战场。`, "sys");
    renderUnits(); checkEnd();
  }
}

function meleeTargets(u) {
  if (u.wpn.kind !== "melee") return [];
  const reach = u.wpn.reach || 1;
  return alive(u.side === "player" ? "enemy" : "player")
    .filter(e => hexDist(u, e) <= reach);
}
function rangedTargets(u) {
  if (u.wpn.kind !== "ranged") return [];
  return alive(u.side === "player" ? "enemy" : "player")
    .filter(e => {
      const d = hexDist(u, e);
      return d >= 2 && d <= u.wpn.range + tiles.get(key(u.q, u.r)).elev; // no point-blank shots
    });
}
const targetsOf = (u) => u.wpn.kind === "melee" ? meleeTargets(u) : rangedTargets(u);
const canAttack = (u) => u.ap >= u.wpn.ap && u.breath >= u.wpn.br;

const SWITCH_AP = 4, SHIELDWALL_AP = 4, SHIELDWALL_BR = 10;

function switchWeapon(u) {
  if (!u.wpn2 || u.ap < SWITCH_AP) return false;
  [u.wpn, u.wpn2] = [u.wpn2, u.wpn];
  u.ap -= SWITCH_AP;
  u.spearwall = false; // can't hold the hedge with the spear stowed
  log(`${u.name} 换械：拔出 <b>${u.wpn.label}</b>（−${SWITCH_AP} 行动力）`, u.side === "player" ? "b" : "r");
  float(u, "换械", "#5b5346");
  return true;
}

function raiseShield(u) {
  if (!u.shield || u.shieldwall || u.ap < SHIELDWALL_AP || u.breath < SHIELDWALL_BR) return false;
  u.ap -= SHIELDWALL_AP;
  u.breath -= SHIELDWALL_BR;
  u.shieldwall = true;
  log(`${u.name} <b>举盾</b>（盾防 ×2，至其下回合）`, u.side === "player" ? "b" : "r");
  float(u, "举盾", "#24506e");
  return true;
}

function uiSwitchWeapon() {
  const u = active();
  if (busy || gameOver || !u || u.side !== "player" || u.morale === "Fleeing") return;
  selectedSkill = "attack";
  if (switchWeapon(u)) { renderUnits(); renderCard(); }
}

function uiSelectSkill(kind) {
  const u = active();
  if (busy || gameOver || !u || u.side !== "player" || u.morale === "Fleeing") return;
  if (kind === "special" && (!u.wpn.special || u.wpn.special.type === "spearwall" || !canSpecial(u))) return;
  selectedSkill = kind;
  renderUnits(); renderCard();
}

function uiSpearwall() {
  const u = active();
  if (busy || gameOver || !u || u.side !== "player" || u.morale === "Fleeing") return;
  const sp = u.wpn.special;
  if (!sp || sp.type !== "spearwall" || u.spearwall || u.ap < sp.ap || u.breath < sp.br) return;
  u.ap -= sp.ap; u.breath -= sp.br;
  u.spearwall = true;
  log(`${u.name} 立定<b>枪林</b>——逼近者吃枪（半伤，刺中即停），至其下回合。`, "b");
  float(u, "枪林", "#24506e");
  renderUnits(); renderCard();
}

function uiRaiseShield() {
  const u = active();
  if (busy || gameOver || !u || u.side !== "player" || u.morale === "Fleeing") return;
  if (raiseShield(u)) { renderUnits(); renderCard(); }
}

const canSpecial = (u) => {
  const sp = u.wpn.special;
  return sp && sp.type !== "spearwall" && u.ap >= sp.ap && u.breath >= sp.br;
};

async function doAttack(u, t, useSpecial) {
  const sp = u.wpn.special;
  const cost = useSpecial ? sp : u.wpn;
  u.ap -= cost.ap;
  u.breath -= cost.br;
  const opts = useSpecial ? specialOpts(sp) : {};
  if (useSpecial && sp.type === "sweep") {
    // round swing: everyone adjacent, friend and foe
    const victims = neighborsOf(u).map(k => at(tiles.get(k).q, tiles.get(k).r)).filter(Boolean);
    log(`${u.name} 抡圆了大斧——<b>横扫</b>！`, u.side === "player" ? "b" : "r");
    for (const v of victims) { if (v.alive) applyHit(u, v, false, opts); }
  } else {
    applyHit(u, t, false, opts);
  }
  selectedSkill = "attack"; // BB-style: revert to the default skill after a special
  renderUnits(); renderCard();
  await sleep(300);
}

/* ---------------- enemy AI (v0: greedy + 3 hand rules) ---------------- */
const inBounds = (u, t) => u.garrison == null || hexDist(t, u.home) <= u.garrison;

async function aiTurn(u) {
  await sleep(250);
  for (let safety = 0; safety < 8 && u.alive && !gameOver; safety++) {
    if (u.morale === "Fleeing") return; // routed mid-turn (ZoC strike) → stop acting
    const tgts = canAttack(u) || canSpecial(u) ? targetsOf(u) : [];
    if (tgts.length) {
      tgts.sort((a, b) => hitBreakdown(u, b).chance - hitBreakdown(u, a).chance || a.hp - b.hp);
      const sp = u.wpn.special;
      // family rules for specials
      if (sp && canSpecial(u)) {
        if (sp.type === "decap") {
          const weak = tgts.find(x => x.hp / x.hpMax < 0.4);
          if (weak) { await doAttack(u, weak, true); continue; }
        } else if (sp.type === "sweep") {
          const adj = neighborsOf(u).map(k => at(tiles.get(k).q, tiles.get(k).r)).filter(Boolean);
          const foesAdj = adj.filter(v => v.side !== u.side).length;
          const friendsAdj = adj.filter(v => v.side === u.side).length;
          if (foesAdj >= 2 && friendsAdj === 0) { await doAttack(u, null, true); continue; }
        } else if (sp.type === "aimed") {
          if (hitBreakdown(u, tgts[0]).chance < 55) { await doAttack(u, tgts[0], true); continue; }
        }
      }
      if (canAttack(u)) { await doAttack(u, tgts[0], false); continue; }
      return;
    }
    if (u.wpn.kind === "ranged") {
      const foes = alive(u.side === "player" ? "enemy" : "player");
      if (!foes.length) return;
      const nearest = foes.reduce((m, f) => hexDist(u, f) < hexDist(u, m) ? f : m);
      const dist = hexDist(u, nearest);
      // rule: pinned archer draws the sidearm and fights
      if (dist === 1 && u.wpn2 && u.ap >= SWITCH_AP + u.wpn2.ap) {
        switchWeapon(u);
        renderUnits();
        await sleep(250);
        continue;
      }
      if (dist < 3 && u.ap >= 2) { // rule: archers keep distance
        const info = dijkstra(u, u.ap, u.breath);
        let best = null, bestScore = -Infinity;
        for (const [k] of info.costs) {
          const t = tiles.get(k);
          if (!inBounds(u, t)) continue;
          const dmin = Math.min(...foes.map(f => hexDist(t, f)));
          const score = Math.min(dmin, 6) + t.elev * 0.5;
          if (score > bestScore) { bestScore = score; best = k; }
        }
        if (best && best !== key(u.q, u.r)) {
          await execMove(u, pathTo(info.prev, best), info.costs.get(best));
          continue;
        }
      }
      // rule: out of bow range entirely → close in (no archer stand-offs)
      const rngMax = u.wpn.range + tiles.get(key(u.q, u.r)).elev;
      if (dist > rngMax && u.ap >= 2 && u.breath >= 1) {
        const info = dijkstra(u, u.ap, u.breath);
        let best = null, bestScore = Infinity;
        for (const [k, c] of info.costs) {
          const t = tiles.get(k);
          if (!inBounds(u, t)) continue;
          const dmin = Math.min(...foes.map(f => hexDist(t, f)));
          const score = dmin * 10 - t.elev * 3 + c * 0.1;
          if (score < bestScore) { bestScore = score; best = k; }
        }
        if (best && best !== key(u.q, u.r)) {
          await execMove(u, pathTo(info.prev, best), info.costs.get(best));
          continue;
        }
      }
      if (rangedTargets(u).length && canAttack(u)) continue; // loop will attack
      return;
    }
    // melee: out of attacks but enemy at hand → raise the shield (rule 4)
    const foes = alive(u.side === "player" ? "enemy" : "player");
    if (!foes.length) return;
    const adjFoe = foes.some(f => hexDist(u, f) === 1);
    if (adjFoe && !canAttack(u) && raiseShield(u)) { renderUnits(); return; }
    // spear-bearer with enemies closing (2–3 hexes) → set the spearwall
    const spw = u.wpn.special;
    if (spw && spw.type === "spearwall" && !u.spearwall && u.ap >= spw.ap && u.breath >= spw.br) {
      const nd = Math.min(...foes.map(f => hexDist(u, f)));
      if (nd >= 2 && nd <= 3) {
        u.ap -= spw.ap; u.breath -= spw.br; u.spearwall = true;
        log(`${u.name} 立定<b>${spw.label}</b>——逼近者吃枪（半伤，刺中即停）。`, u.side === "player" ? "b" : "r");
        float(u, spw.label, "#24506e");
        renderUnits();
        return;
      }
    }
    // melee: advance toward nearest foe, prefer high ground (rule 3)
    if (u.ap < 2 || u.breath < 1) return;
    const info = dijkstra(u, u.ap, u.breath);
    let best = null, bestScore = Infinity;
    for (const [k, c] of info.costs) {
      const t = tiles.get(k);
      if (!inBounds(u, t)) continue;
      const dmin = Math.min(...foes.map(f => hexDist(t, f)));
      const score = dmin * 10 - t.elev * 3 + c * 0.1;
      if (score < bestScore) { bestScore = score; best = k; }
    }
    if (!best || best === key(u.q, u.r)) return;
    await execMove(u, pathTo(info.prev, best), info.costs.get(best));
    if (!targetsOf(u).length || !canAttack(u)) return;
  }
}

/* ---------------- end conditions ---------------- */
function checkEnd() {
  if (gameOver) return;
  const p = alive("player").length, e = alive("enemy").length;
  if (e === 0 || p === 0) {
    gameOver = true;
    const ov = document.getElementById("overlay");
    document.getElementById("ovtitle").textContent = e === 0 ? "胜" : "败";
    document.getElementById("ovtext").textContent = e === 0
      ? `山贼或死或逃。${4 - p > 0 ? `镖局折了 ${4 - p} 人——他们不会回来了。` : "全员生还，今夜有酒。"}`
      : "镖旗倒在山道上。镖局还在，再招人手,再来。";
    document.getElementById("ovstats").innerHTML = summaryHTML();
    ov.style.display = "flex";
  }
}

function summaryHTML() {
  const fate = (u) => u.alive ? "存活" : u.escaped ? "溃走" : "阵亡";
  const cls = (u) => u.alive ? "ok" : u.escaped ? "" : "bad";
  const row = (u) =>
    `<tr><td>${u.name}</td><td>${u.wpn.label}</td><td>${battleStats[u.id].dmg}</td>` +
    `<td>${battleStats[u.id].kills}</td><td class="${cls(u)}">${fate(u)}</td></tr>`;
  const side = (s, label) =>
    `<tr class="hd"><td colspan="5">${label}</td></tr>` +
    units.filter(u => u.side === s).map(row).join("");
  return `<table><tr class="hd"><td>名号</td><td>兵器</td><td>伤害</td><td>击杀</td><td>下场</td></tr>` +
    side("player", "镖局") + side("enemy", "山贼") +
    `</table><div class="rds">历时 ${round} 回合 · 骰子尽数公开于战斗记录</div>`;
}

/* ---------------- rendering ---------------- */
function hexPoints(cx, cy) {
  const pts = [];
  for (let i = 0; i < 6; i++) {
    const a = Math.PI / 180 * (60 * i - 30);
    pts.push((cx + HEX * Math.cos(a)).toFixed(1) + "," + (cy + HEX * Math.sin(a)).toFixed(1));
  }
  return pts.join(" ");
}

const TERRAIN_FILL = { grass: "#d8d2b0", forest: "#aab48c", hill: "#d9c79a", road: "#cdb488", cart: "#c2a878", wall: "#857258" };

function buildBoard() {
  boardEl.innerHTML = "";
  const w = HEX * SQRT3 * (COLS + 1) + 60, h = HEX * 1.5 * ROWS + 110;
  boardEl.setAttribute("viewBox", `0 0 ${w} ${h}`); // scales to fill the pane
  boardEl.setAttribute("preserveAspectRatio", "xMidYMid meet");
  const tileLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
  for (const t of tiles.values()) {
    const { x, y } = hexToPix(t.q, t.r);
    const p = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
    p.setAttribute("points", hexPoints(x, y));
    p.setAttribute("class", "hex");
    p.dataset.k = key(t.q, t.r);
    let fill = TERRAIN_FILL[t.terrain];
    if (t.terrain === "hill" && t.elev === 2) fill = "#c9b27e";
    if (t.terrain === "hill" && t.elev === 3) fill = "#b69a62";
    p.setAttribute("fill", fill);
    p.addEventListener("click", () => onHexClick(key(t.q, t.r)));
    p.addEventListener("mouseenter", () => onHexHover(key(t.q, t.r)));
    p.addEventListener("mouseleave", () => clearHexHover());
    tileLayer.appendChild(p);
    if (t.terrain === "forest" || t.elev > 0 || t.terrain === "cart" || t.terrain === "wall") {
      const tx = document.createElementNS("http://www.w3.org/2000/svg", "text");
      tx.setAttribute("x", x); tx.setAttribute("y", y + 5);
      tx.setAttribute("text-anchor", "middle");
      tx.setAttribute("fill", t.terrain === "cart" ? "#4a3826" : "#8d8268");
      tx.setAttribute("font-size", t.terrain === "cart" ? "19" : "13");
      if (t.terrain === "cart") tx.setAttribute("font-weight", "bold");
      tx.setAttribute("pointer-events", "none");
      tx.textContent = t.terrain === "cart" ? "镖" : t.terrain === "wall" ? "栅" : t.terrain === "forest" ? "竹" : (t.elev === 3 ? "峰" : t.elev === 2 ? "岭" : "丘");
      tileLayer.appendChild(tx);
    }
  }
  // paint the road as a worn track through the hex centers
  if (ROAD_PATH.length >= 2) {
  const roadLine = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  roadLine.setAttribute("points", ROAD_PATH.map(k => {
    const t = tiles.get(k); const p = hexToPix(t.q, t.r);
    return p.x.toFixed(1) + "," + p.y.toFixed(1);
  }).join(" "));
  roadLine.setAttribute("fill", "none");
  roadLine.setAttribute("stroke", "#a8895a");
  roadLine.setAttribute("stroke-width", "9");
  roadLine.setAttribute("stroke-linejoin", "round");
  roadLine.setAttribute("stroke-linecap", "round");
  roadLine.setAttribute("opacity", "0.45");
  roadLine.setAttribute("pointer-events", "none");
  tileLayer.appendChild(roadLine);
  }
  boardEl.appendChild(tileLayer);
  highlightLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
  highlightLayer.setAttribute("pointer-events", "none");
  unitLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
  fxLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
  fxLayer.setAttribute("pointer-events", "none");
  boardEl.appendChild(highlightLayer);
  boardEl.appendChild(unitLayer);
  boardEl.appendChild(fxLayer);
}

/* hexes this unit could strike right now (red overlay) */
function attackRangeHexes(u) {
  const melee = u.wpn.kind === "melee";
  const R = melee ? (u.wpn.reach || 1) : u.wpn.range + tiles.get(key(u.q, u.r)).elev;
  const dMin = melee ? 1 : 2; // bows can't fire point-blank
  const out = [];
  for (const t of tiles.values()) {
    const d = hexDist(t, u);
    if (d >= dMin && d <= R) out.push(key(t.q, t.r));
  }
  return out;
}

function svgPoly(points, fill, stroke, sw) {
  const p = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
  p.setAttribute("points", points);
  p.setAttribute("fill", fill);
  if (stroke) { p.setAttribute("stroke", stroke); p.setAttribute("stroke-width", sw || 1); }
  return p;
}

function renderHighlights(act, playerTurn) {
  highlightLayer.innerHTML = "";
  for (const hexEl of boardEl.querySelectorAll(".hex")) hexEl.classList.remove("reach");
  if (!playerTurn) return;

  // attack range — red wash (under the green so move options stay readable)
  if (canAttack(act)) {
    for (const k of attackRangeHexes(act)) {
      const t = tiles.get(k);
      const { x, y } = hexToPix(t.q, t.r);
      highlightLayer.appendChild(svgPoly(hexPoints(x, y), "rgba(160,46,24,0.15)", "rgba(160,46,24,0.4)", 1));
    }
  }
  // movement range — green fill + AP cost label
  if (moveInfo) {
    for (const [k, c] of moveInfo.costs) {
      if (c === 0) continue;
      const t = tiles.get(k);
      const { x, y } = hexToPix(t.q, t.r);
      highlightLayer.appendChild(svgPoly(hexPoints(x, y), "rgba(96,140,58,0.38)", "rgba(54,92,36,0.55)", 1));
      const tx = document.createElementNS("http://www.w3.org/2000/svg", "text");
      tx.setAttribute("x", x); tx.setAttribute("y", y - 13);
      tx.setAttribute("text-anchor", "middle");
      tx.setAttribute("font-size", "10.5"); tx.setAttribute("fill", "#2c481e");
      tx.setAttribute("font-family", "sans-serif");
      tx.textContent = c;
      highlightLayer.appendChild(tx);
      const el = boardEl.querySelector(`.hex[data-k="${k}"]`);
      if (el) el.classList.add("reach");
    }
  }
}

/* path preview on hover, with ZoC warning */
function onHexHover(k) {
  const u = active();
  if (busy || gameOver || !u || u.side !== "player" || u.morale === "Fleeing") return;
  if (!moveInfo || !moveInfo.costs.has(k) || moveInfo.costs.get(k) === 0) return;
  clearHexHover();
  const c = moveInfo.costs.get(k);
  const path = pathTo(moveInfo.prev, k);
  const pts = path.map(pk => {
    const t = tiles.get(pk); const p = hexToPix(t.q, t.r);
    return p.x.toFixed(1) + "," + p.y.toFixed(1);
  }).join(" ");
  hoverPathEl = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  hoverPathEl.setAttribute("points", pts);
  hoverPathEl.setAttribute("fill", "none");
  hoverPathEl.setAttribute("stroke", "#2f5d24");
  hoverPathEl.setAttribute("stroke-width", "3.5");
  hoverPathEl.setAttribute("stroke-dasharray", "7 5");
  hoverPathEl.setAttribute("stroke-linecap", "round");
  hoverPathEl.setAttribute("opacity", "0.85");
  fxLayer.appendChild(hoverPathEl);

  let zoc = false;
  for (let i = 0; i + 1 < path.length; i++) {
    const t = tiles.get(path[i]);
    if (neighborsOf({ q: t.q, r: t.r }).some(nk => {
      const e = at(tiles.get(nk).q, tiles.get(nk).r);
      return e && e.side !== u.side && exertsZoC(e);
    })) { zoc = true; break; }
  }
  const br = breathOfPath(path);
  const onRoad = path.slice(1).every(pk => tiles.get(pk).brCost === 1);
  document.getElementById("hoverinfo").innerHTML =
    `<b>${u.name}</b> 移动预览<br>耗 ${c} 行动力（剩 ${u.ap - c}）· 气力 −${br}` +
    (onRoad ? `<span style="color:#6b5520">（走官道，省力）</span>` : "") +
    (zoc ? `<br><b style="color:#a02818">⚠ 途经敌人控制区——脱身要挨截击，被打中即止步</b>` : "");
}

function clearHexHover() {
  if (hoverPathEl) { hoverPathEl.remove(); hoverPathEl = null; }
}

function renderUnits() {
  unitLayer.innerHTML = "";
  const act = active();
  const playerTurn = act && act.side === "player" && !busy && !gameOver && act.morale !== "Fleeing";
  const canStrike = playerTurn && ((selectedSkill === "special" && canSpecial(act)) || canAttack(act));
  const tgtIds = canStrike ? new Set(targetsOf(act).map(t => t.id)) : new Set();

  renderHighlights(act, playerTurn);

  for (const u of alive()) {
    const { x, y } = hexToPix(u.q, u.r);
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("class", "unit" + (u === act ? " active" : "") + (tgtIds.has(u.id) ? " attackable" : ""));
    g.setAttribute("transform", `translate(${x},${y})`);
    g.dataset.id = u.id;

    const ring = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    ring.setAttribute("class", "ring"); ring.setAttribute("r", 24); ring.setAttribute("fill", "none");
    g.appendChild(ring);
    const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    c.setAttribute("class", "body"); c.setAttribute("r", 19);
    c.setAttribute("fill", u.side === "player" ? "#1b4965" : "#8c2f1b");
    if (u.leader) c.setAttribute("stroke", "#b8860b");
    g.appendChild(c);
    const tx = document.createElementNS("http://www.w3.org/2000/svg", "text");
    tx.setAttribute("class", "glyph"); tx.setAttribute("y", 7);
    tx.textContent = u.glyph;
    g.appendChild(tx);

    // hp bar
    const bw = 38;
    const bg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    bg.setAttribute("x", -bw / 2); bg.setAttribute("y", 23); bg.setAttribute("width", bw); bg.setAttribute("height", 5);
    bg.setAttribute("fill", "#4a443a");
    g.appendChild(bg);
    const fg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    const frac = u.hp / u.hpMax;
    fg.setAttribute("x", -bw / 2); fg.setAttribute("y", 23); fg.setAttribute("width", bw * frac); fg.setAttribute("height", 5);
    fg.setAttribute("fill", frac > 0.5 ? "#5c7a3f" : frac > 0.25 ? "#b8860b" : "#a02818");
    g.appendChild(fg);
    // body armor bar (steel blue) — fraction of the unit's STARTING armor
    if (u.armorB0 > 0) {
      const abg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      abg.setAttribute("x", -bw / 2); abg.setAttribute("y", 29); abg.setAttribute("width", bw); abg.setAttribute("height", 3);
      abg.setAttribute("fill", "#564f42");
      g.appendChild(abg);
      const ab = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      ab.setAttribute("x", -bw / 2); ab.setAttribute("y", 29); ab.setAttribute("width", bw * (u.armorB / u.armorB0)); ab.setAttribute("height", 3);
      ab.setAttribute("fill", "#7d99a8");
      g.appendChild(ab);
    }
    // helmet bar (bronze)
    if (u.armorH0 > 0) {
      const hbg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      hbg.setAttribute("x", -bw / 2); hbg.setAttribute("y", 33); hbg.setAttribute("width", bw); hbg.setAttribute("height", 3);
      hbg.setAttribute("fill", "#564f42");
      g.appendChild(hbg);
      const hb = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      hb.setAttribute("x", -bw / 2); hb.setAttribute("y", 33); hb.setAttribute("width", bw * (u.armorH / u.armorH0)); hb.setAttribute("height", 3);
      hb.setAttribute("fill", "#b8923f");
      g.appendChild(hb);
    }
    if (u.morale !== "Steady") {
      const m = document.createElementNS("http://www.w3.org/2000/svg", "text");
      m.setAttribute("x", 18); m.setAttribute("y", -14);
      m.setAttribute("font-size", "13"); m.setAttribute("fill", "#a02818");
      m.setAttribute("font-weight", "bold");
      m.textContent = u.morale === "Wavering" ? "怯" : "逃";
      g.appendChild(m);
    }
    if (u.shieldwall || u.spearwall) {
      const s = document.createElementNS("http://www.w3.org/2000/svg", "text");
      s.setAttribute("x", -26); s.setAttribute("y", -14);
      s.setAttribute("font-size", "13"); s.setAttribute("fill", "#24506e");
      s.setAttribute("font-weight", "bold");
      s.textContent = u.shieldwall ? "盾" : "枪";
      g.appendChild(s);
    }

    g.addEventListener("click", () => onUnitClick(u.id));
    g.addEventListener("contextmenu", (e) => { e.preventDefault(); renderInspect(u); });
    g.addEventListener("mouseenter", () => onUnitHover(u.id));
    g.addEventListener("mouseleave", () => renderHover(null));
    unitLayer.appendChild(g);
  }
}

function float(u, txt, color) {
  const { x, y } = hexToPix(u.q, u.r);
  const t = document.createElementNS("http://www.w3.org/2000/svg", "text");
  t.setAttribute("class", "float"); t.setAttribute("x", x); t.setAttribute("y", y - 22);
  t.setAttribute("fill", color);
  t.textContent = txt;
  fxLayer.appendChild(t);
  setTimeout(() => t.remove(), 1100);
}

function renderQueue() {
  const el = document.getElementById("turnorder");
  el.innerHTML = "";
  queue.forEach((u, i) => {
    const s = document.createElement("span");
    s.className = "chip" + (i === qIdx ? " cur" : "") + (i < qIdx || !u.alive ? " done" : "");
    s.style.background = u.side === "player" ? "#1b4965" : "#8c2f1b";
    s.textContent = u.name;
    el.appendChild(s);
  });
}

function renderCard() {
  const u = active();
  const el = document.getElementById("unitcard");
  if (!u || !u.alive) { el.style.display = "none"; renderSkillbar(); return; }
  el.style.display = "block";
  el.innerHTML =
    `<b>${u.name}</b>（${u.side === "player" ? "镖局" : "山贼"} · ${u.wpn.label}）<br>` +
    `血 ${u.hp}/${u.hpMax} ｜ 甲 身${u.armorB} 头${u.armorH}<br>` +
    `行动力 ${u.ap}/9 ｜ 气力 ${u.breath}/${u.breathMax} ｜ 士气 ${u.morale === "Steady" ? "稳" : u.morale === "Wavering" ? "动摇" : "溃逃"}` +
    (u.shieldwall ? " ｜ <b style='color:#24506e'>举盾中</b>" : "") +
    (u.spearwall ? " ｜ <b style='color:#24506e'>枪林立定</b>" : "") +
    (u.side === "player"
      ? `<br><i>还可攻击 ${Math.min(Math.floor(u.ap / u.wpn.ap), Math.floor(u.breath / u.wpn.br))} 次</i>`
      : "");
  renderSkillbar();
}

function renderSkillbar() {
  const el = document.getElementById("skillbar");
  const u = active();
  if (!u || !u.alive || u.side !== "player" || gameOver || u.morale === "Fleeing") {
    el.style.display = "none"; el.innerHTML = ""; return;
  }
  el.style.display = "flex";
  const w = u.wpn, sp = w.special;
  let html =
    `<button class="skill ${selectedSkill === "attack" ? "sel" : ""}" onclick="uiSelectSkill('attack')" ${canAttack(u) ? "" : "disabled"}>${VERB[w.label] || "攻击"}<span>${w.ap}行动·${w.br}气</span></button>`;
  if (sp) {
    if (sp.type === "spearwall") {
      html += `<button class="skill" onclick="uiSpearwall()" ${(u.spearwall || u.ap < sp.ap || u.breath < sp.br) ? "disabled" : ""}>${sp.label}<span>${sp.ap}行动·${sp.br}气·立阵</span></button>`;
    } else {
      html += `<button class="skill ${selectedSkill === "special" ? "sel" : ""}" onclick="uiSelectSkill('special')" ${canSpecial(u) ? "" : "disabled"}>${sp.label}<span>${sp.ap}行动·${sp.br}气</span></button>`;
    }
  }
  if (u.shield) {
    html += `<button class="skill" onclick="uiRaiseShield()" ${(u.shieldwall || u.ap < SHIELDWALL_AP || u.breath < SHIELDWALL_BR) ? "disabled" : ""}>举盾<span>4行动·10气·防×2</span></button>`;
  }
  if (u.wpn2) {
    html += `<button class="skill" onclick="uiSwitchWeapon()" ${u.ap < SWITCH_AP ? "disabled" : ""}>换械<span>→${u.wpn2.label}·4行动</span></button>`;
  }
  html += `<button class="skill endbtn" onclick="endPlayerTurn()">结束<span>⏎</span></button>`;
  el.innerHTML = html;
}

function renderHover(u) {
  const el = document.getElementById("hoverinfo");
  const act = active();
  if (!u || !act || u.side === act.side) {
    el.textContent = "将鼠标移到红圈敌人上，查看完整命中计算。";
    return;
  }
  const inRange = targetsOf(act).some(t => t.id === u.id);
  const pointBlank = act.wpn.kind === "ranged" && hexDist(act, u) < 2;
  const opts = (selectedSkill === "special" && act.wpn.special && canSpecial(act)) ? specialOpts(act.wpn.special) : {};
  const bd = hitBreakdown(act, u, opts);
  let html = `<b>${act.name} → ${u.name}</b>${opts.tag ? `【${opts.tag}】` : ""}` +
    (pointBlank ? `（<b style="color:#a02818">贴身，弓箭无法施射——换械！</b>）` : inRange ? "" : "（不在射程，预演）") + "<br>";
  for (const [label, v] of bd.parts) {
    html += `${v >= 0 ? "+" : "−"}${Math.abs(v)}  ${label}<br>`;
  }
  html += `<span class="pct">= ${bd.chance}%</span>（夹在 5–95 之间）<br>`;
  html += `目标：血 ${u.hp} ｜ 甲 身${u.armorB} 头${u.armorH} ｜ 25% 爆头 ×1.5`;
  el.innerHTML = html;
}

/* ---------------- input ---------------- */
async function onHexClick(k) {
  const u = active();
  if (busy || gameOver || !u || u.side !== "player" || u.morale === "Fleeing") return;
  if (!moveInfo || !moveInfo.costs.has(k) || moveInfo.costs.get(k) === 0) return;
  clearHexHover();
  busy = true;
  await execMove(u, pathTo(moveInfo.prev, k), moveInfo.costs.get(k));
  moveInfo = (u.alive && u.morale !== "Fleeing") ? dijkstra(u, u.ap, u.breath) : null;
  busy = false;
  renderUnits(); renderCard();
  if (!u.alive) nextTurn();
}

async function onUnitClick(id) {
  const t = units.find(x => x.id === id);
  if (!t || !t.alive) return;
  // left click = action only; inspection lives on right click
  const u = active();
  if (busy || gameOver || !u || u.side !== "player" || u.morale === "Fleeing") return;
  const useSp = selectedSkill === "special" && canSpecial(u);
  if (t.side !== "player" && (useSp || canAttack(u)) && targetsOf(u).some(x => x.id === t.id)) {
    busy = true;
    await doAttack(u, t, useSp);
    moveInfo = (u.alive && u.morale !== "Fleeing") ? dijkstra(u, u.ap, u.breath) : null;
    busy = false;
    renderUnits(); renderCard();
  }
}

function onUnitHover(id) {
  const t = units.find(x => x.id === id);
  if (t && t.alive) renderHover(t);
}

function renderInspect(u) {
  const el = document.getElementById("hoverinfo");
  const w = u.wpn;
  const traits = [];
  if (w.kind === "melee") {
    traits.push(w.hands === 2
      ? `双手兵器${(w.reach || 1) === 2 ? "·长杆：可攻 2 格（隔位 −15 准头）" : ""}`
      : "单手兵器");
  }
  if (u.shield) traits.push(`盾牌（招架/闪避 +${u.shield}${u.shieldwall ? "，举盾中 ×2" : "，可举盾"}）`);
  if (doubleGrip(u)) traits.push("空出副手：双手紧握，伤害 +25%");
  if (w.noHead) traits.push("透甲刺（穿甲 100%，不能爆头）");
  if (w.ignoreShield) traits.push("软兵：无视盾牌招架（举盾加成仍有效）");
  if (w.headBonus) traits.push(`专打头（爆头几率 +${w.headBonus}%）`);
  if (w.special) {
    const SPDESC = {
      spearwall: "立定枪阵：逼近者吃半伤截刺，刺中即停（至下回合）",
      decap: "伤害 ×1.3；杀敌骇人，周围敌人额外胆识考验（−10）",
      demolish: "纯破甲：甲伤 ×3，不伤血",
      aimed: "准头 +10，距离衰减减半",
      sweep: "命中所有相邻者——敌我不分，准头 −10",
      headhunt: "兜头一击：必中头部（×1.5）",
    };
    traits.push(`特技【${w.special.label}】${w.special.ap}行动力/${w.special.br}气力 — ${SPDESC[w.special.type]}`);
  }
  if (u.spearwall) traits.push("枪林立定中");
  if (u.wpn2) traits.push(`副械：${u.wpn2.label}（换械 4 行动力）`);
  if (w.bleed) traits.push("利刃见血（伤≥6 流血 5×2 回合）");
  if (w.chop) traits.push("劈颅（爆头伤害 ×2.25）");
  if (w.breathDrain) traits.push(`沉重（命中多泄敌气力 ${w.breathDrain}）`);
  if (w.kind === "ranged") traits.push(`双手弓弩 · 射程 ${w.range}（每格远 −${w.falloff}%）`);
  if (u.leader) traits.push("匪首");
  const initNow = u.initBase - (u.breathMax - u.breath);
  el.innerHTML =
    `<span class="nm"><b>${u.name}</b></span>（${u.side === "player" ? "镖局" : "山贼"}）` +
    `${u.morale !== "Steady" ? ` · <b style="color:#a02818">${u.morale === "Wavering" ? "动摇" : "溃逃"}</b>` : ""}` +
    `${u.bleed > 0 ? ` · <b style="color:#a02818">流血</b>` : ""}<br>` +
    `血 ${u.hp}/${u.hpMax} ｜ ${u.armorName} ${u.armorB}/${u.armorB0} · ${u.helmName} ${u.armorH}/${u.armorH0} ｜ 招架 ${u.def}${u.shield ? "+" + u.shield : ""}<br>` +
    `甲胄重 ${ARMOR[u.armor].weight + ARMOR[u.helmet].weight}（气力上限 ${u.breathBase}−重＝${u.breathMax}）<br>` +
    `兵器 ${w.label}：伤 ${w.dmin}–${w.dmax} ｜ 破甲 ${Math.round(w.armorEff * 100)}% ｜ 穿甲 ${Math.round(w.pierce * 100)}%` +
    ` ｜ 每击 ${w.ap} 行动力 / ${w.br} 气力<br>` +
    `武艺 ${u.skill} ｜ 胆识 ${u.resolve} ｜ 气力 ${u.breath}/${u.breathMax} ｜ 当前先手 ${initNow}` +
    (traits.length ? `<br>特性：${traits.join("；")}` : "");
}

/* ---------------- log ---------------- */
function log(html, cls) {
  const d = document.createElement("div");
  if (cls) d.className = cls;
  d.innerHTML = html;
  logEl.appendChild(d);
  logEl.scrollTop = logEl.scrollHeight;
}

/* ---------------- boot ---------------- */
async function boot() {
  logEl = document.getElementById("log");
  boardEl = document.getElementById("board");
  const scenId = new URLSearchParams(location.search).get("scenario") || "jiebiao";
  try {
    const res = await fetch(`scenarios/${scenId}.json`, { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    scenario = await res.json();
  } catch (err) {
    document.getElementById("subtitle").textContent = "无法载入战役 " + scenId;
    if (logEl) {
      const d = document.createElement("div");
      d.style.color = "#a02818"; d.style.fontWeight = "bold";
      d.textContent = `战役载入失败（${err.message}）——请强制刷新 Cmd+Shift+R；若仍失败，告诉我这行字。`;
      logEl.appendChild(d);
    }
    return;
  }
  const pick = document.getElementById("scenpick");
  if (pick) pick.value = scenId;
  document.getElementById("subtitle").textContent = scenario.name;
  buildMap();
  const tplById = {};
  for (const t of rosterTemplates()) tplById[t.id] = t;
  battleStats = {};
  units = scenario.units.map(su => {
    const un = mkUnit(tplById[su.id], su.spawn[0], su.spawn[1]);
    un.garrison = su.garrison ?? null; // AI holds within this radius of home
    un.home = { q: su.spawn[0], r: su.spawn[1] };
    battleStats[un.id] = { dmg: 0, kills: 0 };
    return un;
  });
  buildBoard();
  for (const line of scenario.intro || []) log(line, "sys");
  startRound();
}

function endPlayerTurn() {
  const u = active();
  if (!busy && !gameOver && u && u.side === "player") {
    clearHexHover(); moveInfo = null; nextTurn();
  }
}
document.getElementById("endturn").addEventListener("click", endPlayerTurn);
document.addEventListener("keydown", (e) => {
  if (e.key === "Enter") { e.preventDefault(); endPlayerTurn(); }
});
document.getElementById("restart").addEventListener("click", () => location.reload());
document.getElementById("scenpick").addEventListener("change", (e) => {
  location.search = "?scenario=" + e.target.value;
});

boot();
