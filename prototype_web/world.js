/* 碎玉 Shattered Jade · 舆图 strategic map — faithful JS port of sim/overworld.py:
   fixed campaign hexes (pointy-top, same (col,row)→q convention as game.js), terrain
   move costs (官道/桥/聚落 1, 旷野/渡 2, 丘林 3, 大河层峦不可逾), MOVE_PER_DAY=8,
   视野 3（+1 于丘陵）。Bandits prowl their leash with roads
   weighted 3×, drawn from a seeded serializable PRNG (mulberry32, ?seed=N) so the
   web world is deterministic and survives page navigation;
   routed parties walk settlement routes by Dijkstra; hidden lairs render as natural
   ground until spotted; encounter scenario = anchored site → lair's own → terrain table.
   v0.4 adds the BB camera (drag-pan, edge-scroll, wheel zoom over a board bigger than
   the screen), 藩镇 territory captions, and the silver economy (sim/overworld.py M2):
   市集 buys provisions — NO free refill anywhere — 镖单 escorts/bounties (one contract
   at a time), and the city 铁匠铺 raising hero gear up the 品阶 ladder; the smith's
   work rides into every campaign battle via __SJ_GEAR / localStorage "sj_gear". */

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

/* ---------------- hex math (pointy-top axial, same as game.js) ---------------- */
const SQRT3 = Math.sqrt(3);
const HEX = 22; // big hexes: the board outgrows the screen — the camera pans over it
const DIRS = [[1,0],[1,-1],[0,-1],[-1,0],[-1,1],[0,1]];
const key = (q, r) => q + "," + r;
const pOf = (k) => k.split(",").map(Number);
const hexDist = (a, b) => {
  const dq = a[0] - b[0], dr = a[1] - b[1];
  return (Math.abs(dq) + Math.abs(dr) + Math.abs(dq + dr)) / 2;
};
const hexToPix = (q, r) => ({
  x: HEX * SQRT3 * (q + r / 2) + 50,
  y: HEX * 1.5 * r + 50,
});
const samePos = (a, b) => a[0] === b[0] && a[1] === b[1];
const sleep = (ms) => new Promise((res) => setTimeout(res, ms));

/* ---------------- overworld rules (mirrors sim/overworld.py) ---------------- */
const MOVE_PER_DAY = 8;     // 官道 ~8 hexes/day, open country ~4
const SIGHT = 3;            // hexes; +1 ending a step on hills
// provisions are units now; the cap rides on the roster (see capacity)
const CORE_ROSTER = ["wang", "liu", "shi", "yan"];
const PROVISION_BASE = 4, CARRY_PER_HEAD = 2, EAT_PER_HEAD = 1, WAGE_PER_HEAD = 2;
/* ---- BB recruitment (faithful port of sim/recruit.py; gameplay parity) ---- */
const R_SURNAMES = "赵钱孙李周吴郑王冯陈卫蒋沈韩杨朱秦许何吕张孔曹高石马苗凤花方俞任袁柳鲍史唐费岑薛雷贺倪汤殷罗毕郝安常乐于".split("");
const R_GIVEN = "勇刚虎彪豹龙彦荣贵福禄寿山林川河海江云风雷电铁钢锐锋利胜忠义信仁孝雄威猛壮健安平定兴旺金玉珠宝栋梁柱石根本".split("");
const R_FGIVEN = "娘秀英兰花玉珠香莲翠红梅杏桃春燕莺凤娥婵娟淑慧".split("");
const R_FNICK = new Set(["母大虫", "母夜叉", "一丈青"]);
const R_NICK = {
  tianong: ["拼命三郎","黑旋风","病大虫","笑面虎","急先锋","母大虫"],
  tuihuo: ["丧门神","催命判官","翻江蜃","白日鼠","鼓上蚤","短命二郎"],
  liehu: ["小李广","赛仁贵","落地太岁","花项虎","射雕手","穿云箭"],
  huanseng: ["花和尚","行者","金刚","降魔尊者","铁罗汉","醉头陀"],
  tangzishou: ["神行太保","镇三山","插翅虎","美髯公","金枪手","病关索"],
  youxia: ["豹子头","小旋风","玉麒麟","青面兽","九纹龙","扑天雕","浪里白条","一丈青","双枪将"],
};
const R_BG = {
  tianong: { name:"佃农", fee:[30,50], wage:2, hp:[40,48], skill:[44,50], dfn:[3,5], resolve:[32,40], init:[92,100], breath:[84,92], traits:["jianzhuang","lannuo","tiefei"], blurb:"田间出身，能扛能熬" },
  tuihuo: { name:"退伙强人", fee:[40,70], wage:3, hp:[44,52], skill:[48,54], dfn:[4,6], resolve:[36,44], init:[96,104], breath:[84,90], traits:["tanlan","jieao","jiujiu","hanyong"], blurb:"刀头舔血过来的，手熟心野" },
  liehu: { name:"猎户", fee:[70,100], wage:4, hp:[42,48], skill:[50,56], dfn:[5,7], resolve:[38,44], init:[104,112], breath:[88,94], traits:["duyan","tiefei","hanyong"], blurb:"山林讨生活，一手好箭法" },
  huanseng: { name:"还俗僧", fee:[90,130], wage:5, hp:[52,62], skill:[50,56], dfn:[5,7], resolve:[48,56], init:[88,96], breath:[90,96], traits:["shenli","jiujiu","hanyong"], blurb:"酒肉穿肠的莽和尚" },
  tangzishou: { name:"趟子手", fee:[100,150], wage:5, hp:[50,58], skill:[54,60], dfn:[6,9], resolve:[42,48], init:[96,104], breath:[87,92], traits:["hanyong","tiefei"], blurb:"押过多少趟镖的老手" },
  youxia: { name:"游侠", fee:[200,300], wage:8, hp:[48,58], skill:[60,68], dfn:[8,12], resolve:[44,52], init:[104,114], breath:[88,94], traits:["shenli","hanyong","bozu"], blurb:"来去无踪的剑客，价高却值" },
};
const R_TRAIT = { shenli:"天生神力", tiefei:"铁肺", hanyong:"悍勇", danqie:"胆怯", duyan:"独眼", bozu:"跛足", jiujiu:"嗜酒", tanlan:"贪婪", jieao:"桀骜", jianzhuang:"健壮", lannuo:"懒惰" };
const R_ATTRS = ["hp","skill","dfn","resolve","init","breath"];
const R_ANAME = { hp:"血", skill:"武艺", dfn:"招架", resolve:"胆识", init:"先手", breath:"气力" };
const R_REFRESH = 6, R_POOL = 4;
const R_WAGEADJ = { jiujiu:1, tanlan:2 };

function strSeed(s){let h=2166136261>>>0;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return h>>>0;}
function makeRng(str){let a=strSeed(str);const m=()=>{a=(a+0x6D2B79F5)>>>0;let t=a;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296;};
  return { next:m, int:(lo,hi)=>lo+Math.floor(m()*(hi-lo+1)), pick:(a)=>a[Math.floor(m()*a.length)],
    sample:(arr,k)=>{const c=arr.slice();const out=[];for(let i=0;i<k&&c.length;i++)out.push(c.splice(Math.floor(m()*c.length),1)[0]);return out;},
    chance:(p)=>m()<p, weighted:(keys,wts)=>{const s=wts.reduce((x,y)=>x+y,0);let r=m()*s;for(let i=0;i<keys.length;i++){r-=wts[i];if(r<0)return keys[i];}return keys[keys.length-1];} };}

function rcGenerate(rng, bgKey, idx){
  const bg = R_BG[bgKey];
  const female = rng.chance(0.12);
  const given = rng.sample(female ? R_FGIVEN : R_GIVEN, rng.int(1,2)).join("");
  const name = rng.pick(R_SURNAMES) + given;
  const nicks = R_NICK[bgKey].filter((n)=>female || !R_FNICK.has(n));
  const nick = rng.pick(nicks);
  const stats = {}; for (const a of R_ATTRS) stats[a] = rng.int(bg[a][0], bg[a][1]);
  const pool = bg.traits.concat(Object.keys(R_TRAIT).filter(()=>rng.chance(0.15)));
  const nT = rng.weighted([0,1,2],[25,50,25]);
  const traits = rng.sample(pool, Math.min(nT, pool.length));
  const starred = rng.sample(R_ATTRS, 3); const talents = {};
  for (const a of starred) talents[a] = rng.weighted([1,2,3],[60,30,10]);
  let fee = rng.int(bg.fee[0], bg.fee[1]), wage = bg.wage;
  for (const t of traits) {
    if (t==="tiefei") stats.breath += 12; else if (t==="hanyong") stats.resolve += 8;
    else if (t==="danqie") stats.resolve -= 8; else if (t==="bozu") stats.init -= 8;
    else if (t==="lannuo") stats.init -= 4; else if (t==="jianzhuang") stats.hp += 6;
    else if (t==="jieao") { stats.resolve -= 4; stats.skill += 4; }
    wage += R_WAGEADJ[t] || 0;
  }
  return { rid:`${bgKey}_${idx}`, name, nick, female, bg:bgKey, bg_name:bg.name, blurb:bg.blurb,
           stats, traits, talents, fee, wage, reveal:0 };
}
function rcPool(settlement, day){
  const epoch = Math.floor(day / R_REFRESH);
  const rng = makeRng(`recruit:${spec.id}:${settlement.id}:${epoch}`);
  const w = settlement.kind === "city" ? { tianong:2, tuihuo:2, liehu:2, huanseng:1, tangzishou:2, youxia:1 }
    : settlement.kind === "town" ? { tianong:3, tuihuo:2, liehu:2, tangzishou:1 }
    : { tianong:4, tuihuo:1, liehu:2 };
  const keys = Object.keys(w), wts = keys.map((k)=>w[k]);
  const out = [];
  for (let i=0;i<R_POOL;i++) out.push(rcGenerate(rng, rng.weighted(keys,wts), i));
  return out;
}
function headcount() { return CORE_ROSTER.length + world.members.length; }
function capacity() { return PROVISION_BASE + CARRY_PER_HEAD * headcount(); }
function dailyFood() { return EAT_PER_HEAD * headcount(); }
function dailyWage() { return WAGE_PER_HEAD * CORE_ROSTER.length + world.members.reduce((s, m) => s + m.wage, 0); }

/* ---- the silver economy (M2, mirrors sim/overworld.py): markets, escorts, the smith ---- */
const GOLD_START = 100;
const PROVISION_PRICE = { city: 2, town: 2, village: 3 };  // 两 per day of 粮草
const ESCORT_RATE = 40;                                    // 两 per road-day
const BOUNTY_PAY = 260;                                    // 两 per razed lair
const QUALITY_LADDER = ["fan", "liang", "jing", "zhen", "shen"];
const QUALITY_LABEL = { fan: "凡品", liang: "良品", jing: "精品", zhen: "珍品", shen: "神品" };
const SMITH_PRICE = { liang: 100, jing: 250, zhen: 600, shen: 1500 };
const GEAR_SLOTS = ["wpn_q", "wpn2_q", "armor_q", "helmet_q"];
const SLOT_LABEL = { wpn_q: "兵", wpn2_q: "副", armor_q: "甲", helmet_q: "盔" };

/* player roster quality-slot defaults — replicated from game.js rosterTemplates()
   P(...) templates (sim load_world seeds gear from data.ROSTER the same way).
   wpn2 marks who carries a sidearm (so the smith offers the wpn2_q slot);
   smith marks the named heroes the 铁匠铺 serves — militia stay off the anvil. */
const HEROES = [
  { id: "wang", name: "王铁枪", wpn2: true, smith: true, wpnLabel: "长枪", wpn2Label: "腰刀", wpnDura: 64, wpn2Dura: 56 },
  { id: "liu",  name: "刘三刀", wpn_q: "jing", smith: true, wpnLabel: "腰刀", wpnDura: 56 },
  { id: "shi",  name: "石敢当", smith: true, wpnLabel: "大锤", wpnDura: 72 },
  { id: "yan",  name: "燕小乙", wpn_q: "liang", wpn2: true, smith: true, wpnLabel: "猎弓", wpn2Label: "匕首", wpnDura: 48, wpn2Dura: 40 },
  { id: "chen", name: "陈短矛", smith: true, wpnLabel: "短矛", wpnDura: 56 },
  { id: "he",   name: "何九鞭", smith: true, wpnLabel: "九节鞭", wpnDura: 56 },
  { id: "lu",   name: "鲁大弩", wpn2: true, smith: true, wpnLabel: "弩", wpn2Label: "短刀", wpnDura: 48, wpn2Dura: 48 },
  { id: "zhou", name: "周大刀", smith: true, wpnLabel: "大关刀", wpnDura: 64 },
  { id: "xya", name: "乡勇·甲" }, { id: "xyb", name: "乡勇·乙" },
  { id: "xyc", name: "乡勇·丙" }, { id: "xyd", name: "乡勇·丁" },
];
/* the heroes ride out with their template gear; the smith improves on it */
function seedGear() {
  const gear = {};
  for (const t of HEROES) {
    gear[t.id] = {};
    for (const k of GEAR_SLOTS) if (t[k]) gear[t.id][k] = t[k];
  }
  return gear;
}

const COST = { road: 1, bridge: 1, settlement: 1, plain: 2, ford: 2,
               hills: 3, forest: 3, marsh: 4, water: null, mountains: null };
const HOSTILE = new Set(["bandit", "raider", "hunter"]);
const WAYLAY_INFAMY = { caravan: 3, patrol: 4 };
const INFAMY_PRICED = 3, INFAMY_HUNTED = 6, ATONE_RATE = 40;
const FRIENDLY_KINDS = new Set(["city", "town", "village"]);

const KIND_GLYPH = { city: "◎", town: "○", village: "村", stronghold: "寨", occupied: "辽" };
const PARTY_GLYPH = { bandit: "匪", caravan: "商", patrol: "巡", raider: "骑", hunter: "捕" };
const PARTY_FILL = { bandit: "#8c2f1b", caravan: "#b8860b", patrol: "#3d7ea6", raider: "#641c10", hunter: "#3a2f28" };
const KIND_FILL = { city: "#2b2620", town: "#4a4337", village: "#5e553f",
                    stronghold: "#6e3328", occupied: "#8c2f1b" };
const TERRAIN_GLYPH = { hills: "山", forest: "林", ford: "渡", bridge: "桥", mountains: "峰", marsh: "沼" };
/* battle TERRAIN_FILL palette, extended with mountains and a river blue */
const TERRAIN_FILL = { plain: "#d8d2b0", forest: "#aab48c", hills: "#d9c79a", road: "#cdb488",
                       settlement: "#cdb488", bridge: "#c2a878", ford: "#bccbc4",
                       water: "#9cbecb", mountains: "#9b8d75", marsh: "#a9bda6" };
const TERRAIN_NAME = { plain: "旷野", road: "官道", hills: "丘陵", forest: "林间", water: "大河", marsh: "苇荡",
                       ford: "渡口", bridge: "桥头", mountains: "层峦", settlement: "市镇" };
const SCEN_NAME = { jiebiao: "劫镖 · 山道伏击", shouqiao: "守桥 · 断后之战",
                    duijue: "对决 · 黑风三煞", gongzhai: "攻寨 · 强袭山寨", juma: "血战 · 拒马河" };

/* ---------------- state ---------------- */
let spec = null;
const tiles = new Map();        // key -> { q, r, terrain }
const settlements = new Map();  // id -> spec entry (at: [q,r])
const sites = new Map();        // id -> spec entry (anchored set-pieces)
const world = { day: 1, provisions: PROVISIONS_MAX, party: null,
                parties: [], spotted: new Set(), destroyed: new Set(),
                gold: GOLD_START, gear: {}, contract: null };
let dij = null;                 // { costs, prev } from the column's hex
let busy = false;               // a journey is animating
let pendingScen = null;         // scenario behind the 开战 button
let pendingParty = null;        // the hostile (or the prey) behind it
let pendingKind = "encounter";  // encounter | waylay
let pendingBattle = null;       // {kind, target, scenario} — survives the page hop

/* seeded, serializable PRNG (mulberry32) — the worldgen stream's stand-in */
let rngState = 1;
function rnd() {
  rngState = (rngState + 0x6D2B79F5) >>> 0;
  let t = rngState;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}

/* ---------------- persistence: the world survives the battle page ---------------- */
const STORE = () => "sj_world_" + spec.id;

function saveState() {
  try {
    localStorage.setItem(STORE(), JSON.stringify({
      v: 2, day: world.day, provisions: world.provisions, party: world.party,
      infamy: world.infamy, members: world.members, gold2: true,
      gold: world.gold, gear: world.gear, contract: world.contract,
      rngState, spotted: [...world.spotted], destroyed: [...world.destroyed],
      parties: world.parties.map((p) => ({ pid: p.pid, pos: p.pos, leg: p.leg, alive: p.alive })),
      pending: pendingBattle,
    }));
  } catch (e) { /* file:// storage may be unavailable — play on, unsaved */ }
}

function restoreState() {
  let s = null;
  try { s = JSON.parse(localStorage.getItem(STORE()) || "null"); } catch (e) { s = null; }
  if (!s || s.v !== 2) return false;   // pre-economy saves are discarded
  world.day = s.day;
  world.provisions = s.provisions;
  world.infamy = s.infamy || 0;
  world.members = Array.isArray(s.members) ? s.members.filter(
    (m) => m && typeof m.wage === "number" && m.name) : [];
  world.party = s.party.slice();
  world.gold = s.gold;
  world.contract = s.contract || null;
  rngState = s.rngState >>> 0;
  world.spotted = new Set(s.spotted);
  world.destroyed = new Set(s.destroyed);
  const byId = new Map(world.parties.map((p) => [p.pid, p]));
  for (const sp of s.parties) {
    const p = byId.get(sp.pid);
    if (p) { p.pos = sp.pos.slice(); p.leg = sp.leg; p.alive = sp.alive; }
  }
  pendingBattle = s.pending || null;
  const seeded = seedGear();                 // every hero present, grades legal
  for (const uid of Object.keys(seeded)) {
    const sv = (s.gear || {})[uid] || {};
    for (const slot of GEAR_SLOTS) {
      if (QUALITY_LADDER.indexOf(sv[slot]) > 0) seeded[uid][slot] = sv[slot];
    }
    for (const k of ["armor_dmg", "helm_dmg"]) {
      if (Number.isInteger(sv[k]) && sv[k] > 0) seeded[uid][k] = sv[k];
    }
    for (const k of ["wpn_dura", "wpn2_dura"]) {
      if (Number.isInteger(sv[k]) && sv[k] >= 0) seeded[uid][k] = sv[k];
    }
  }
  world.gear = seeded;
  return true;
}

/* retreat: a beaten column falls back on the nearest friendly gates */
function retreatToFriendly() {
  const { costs } = dijkstra(world.party);
  let best = null, bc = 1 << 30;
  for (const s of settlements.values()) {
    if (!FRIENDLY_KINDS.has(s.kind) || world.destroyed.has(s.id)) continue;
    const k = key(s.at[0], s.at[1]);
    if (costs.has(k) && costs.get(k) < bc) { bc = costs.get(k); best = s; }
  }
  if (best) world.party = best.at.slice();   // no free grain at the gates anymore
  return best;
}

/* the loop closes: what happened on the battle page lands on the map.
   resOverride comes straight from the in-page battle frame (no storage). */
function applyBattleResult(resOverride) {
  const pend = pendingBattle;
  if (!pend) return;
  pendingBattle = null;
  let res = resOverride || null;
  if (!res) { try { res = JSON.parse(localStorage.getItem("sj_battle_result") || "null"); } catch (e) {} }
  if (!res || res.scenario !== pend.scenario) return;   // battle never fought
  try { localStorage.removeItem("sj_battle_result"); } catch (e) {}
  for (const wu of res.wear || []) {                    // the dents ride home
    const g = world.gear[wu.id];
    if (!g) continue;
    g.armor_dmg = (g.armor_dmg || 0) + (wu.armorLost || 0);
    g.helm_dmg = (g.helm_dmg || 0) + (wu.helmLost || 0);
    const h = HEROES.find((x) => x.id === wu.id);
    for (const wd of wu.wpns || []) {
      if (h && wd.base === h.wpnLabel) g.wpn_dura = wd.dura;
      else if (h && wd.base === h.wpn2Label) g.wpn2_dura = wd.dura;
    }
  }
  const win = res.winner === "player";
  if (pend.kind === "assault") {
    const lair = settlements.get(pend.target);
    if (win && lair) {
      applyRaze(lair);
      log(`第${world.day}日 · 血战破寨——${lair.name}已荡平，余匪作鸟兽散！`, "b");
    } else {
      const b = retreatToFriendly();
      log(`第${world.day}日 · 攻寨失利，残部退守${b ? b.name : "旷野"}`, "r");
      failContract();   // a lost battle voids the bond (sim fail_contract)
    }
  } else if (pend.kind === "waylay") {
    const p = world.parties.find((x) => x.pid === pend.target);
    if (win && p) {
      p.alive = false;
      const pay = WAYLAY_LOOT[p.kind] || 0;
      world.gold += pay;
      world.infamy += WAYLAY_INFAMY[p.kind] || 0;
      log(`第${world.day}日 · 劫了${p.name}，掠得${pay}两——恶名+${WAYLAY_INFAMY[p.kind] || 0}（现${world.infamy}）`, "r");
    } else if (!win) {
      failContract();
      const b = retreatToFriendly();
      log(`第${world.day}日 · 劫道失手，败走${b ? b.name : "荒野"}`, "r");
    }
  } else {
    const p = world.parties.find((x) => x.pid === pend.target);
    if (win) {
      if (p) p.alive = false;
      log(`第${world.day}日 · 镖队击溃${p ? p.name : "贼人"}，道路为之一清`, "b");
    } else {
      const b = retreatToFriendly();
      log(`第${world.day}日 · 战败溃走，退至${b ? b.name : "荒野"}`, "r");
      failContract();   // a lost battle voids the bond (sim fail_contract)
    }
  }
}
let boardEl, logEl, overlayEl, hoverEl;
let placeLayer, partyLayer, fxLayer;
let hoverPathEl = null;

const tileCost = (k) => COST[tiles.get(k).terrain];

/* ---------------- camera (BB/Bannerlord style: pan, edge-scroll, zoom) ----------------
   The viewBox is a window over the full board; scale = css px per board unit. */
let BOARD_W = 0, BOARD_H = 0;
const ZOOM_MIN = 0.5, ZOOM_MAX = 2.2;        // × base scale (base: 1 unit = 1 px)
const EDGE_PX = 28, EDGE_STEP = 12, EDGE_MS = 40;
const cam = { x: 0, y: 0, scale: 1 };
let wrapEl = null;
let dragLast = null, dragMoved = 0;          // >5px of drag suppresses the click
let edgeXY = null;                           // last cursor position over the pane

function viewSize() {
  const r = boardEl.getBoundingClientRect();
  return { w: (r.width || 960) / cam.scale, h: (r.height || 640) / cam.scale };
}
function clampCam() {
  const { w, h } = viewSize();
  cam.x = w >= BOARD_W ? (BOARD_W - w) / 2 : Math.max(0, Math.min(BOARD_W - w, cam.x));
  cam.y = h >= BOARD_H ? (BOARD_H - h) / 2 : Math.max(0, Math.min(BOARD_H - h, cam.y));
}
function applyCam() {
  if (!BOARD_W) return;
  clampCam();
  const { w, h } = viewSize();
  boardEl.setAttribute("viewBox",
    `${cam.x.toFixed(1)} ${cam.y.toFixed(1)} ${w.toFixed(1)} ${h.toFixed(1)}`);
}
function centerOn(pos) {
  const { x, y } = hexToPix(pos[0], pos[1]);
  const { w, h } = viewSize();
  cam.x = x - w / 2; cam.y = y - h / 2;
  applyCam();
}
function initCamera() {
  wrapEl = document.getElementById("boardwrap");
  boardEl.addEventListener("mousedown", (e) => {
    if (e.button !== 0) return;
    dragLast = [e.clientX, e.clientY]; dragMoved = 0;
    e.preventDefault();    // no text/image selection while panning
  });
  window.addEventListener("mousemove", (e) => {
    if (!dragLast) return;
    const dx = e.clientX - dragLast[0], dy = e.clientY - dragLast[1];
    dragLast = [e.clientX, e.clientY];
    dragMoved += Math.abs(dx) + Math.abs(dy);
    if (dragMoved > 5) boardEl.style.cursor = "grabbing";
    cam.x -= dx / cam.scale; cam.y -= dy / cam.scale;
    applyCam();
  });
  window.addEventListener("mouseup", () => {
    dragLast = null;
    boardEl.style.cursor = "";
  });
  // edge-scrolling, BB style: the cursor resting near a pane edge pans the map
  wrapEl.addEventListener("mousemove", (e) => { edgeXY = [e.clientX, e.clientY]; });
  wrapEl.addEventListener("mouseleave", () => { edgeXY = null; });
  setInterval(() => {
    if (!edgeXY || dragLast || busy || !BOARD_W) return;
    if (document.getElementById("battleframe")
        || overlayEl.style.display === "flex") return;   // a modal owns the screen
    const r = wrapEl.getBoundingClientRect();
    const step = EDGE_STEP / cam.scale;
    let dx = 0, dy = 0;
    if (edgeXY[0] - r.left < EDGE_PX) dx = -step;
    else if (r.right - edgeXY[0] < EDGE_PX) dx = step;
    if (edgeXY[1] - r.top < EDGE_PX) dy = -step;
    else if (r.bottom - edgeXY[1] < EDGE_PX) dy = step;
    if (dx || dy) { cam.x += dx; cam.y += dy; applyCam(); }
  }, EDGE_MS);
  // wheel zoom, anchored at the cursor
  wrapEl.addEventListener("wheel", (e) => {
    e.preventDefault();
    const r = boardEl.getBoundingClientRect();
    const mx = e.clientX - r.left, my = e.clientY - r.top;
    const bx = cam.x + mx / cam.scale, by = cam.y + my / cam.scale;
    const z = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, cam.scale * Math.exp(-e.deltaY * 0.0012)));
    if (z === cam.scale) return;
    cam.scale = z;
    cam.x = bx - mx / z; cam.y = by - my / z;
    applyCam();
  }, { passive: false });
  window.addEventListener("resize", applyCam);
}

/* ---------------- world build (load_world) ---------------- */
function buildWorld() {
  const marked = {};
  for (const kind of ["hills", "mountains", "marsh", "forest", "river", "ford", "bridge", "road"])
    marked[kind] = new Set((spec.map[kind] || []).map((k) => key(k[0], k[1])));
  tiles.clear(); settlements.clear(); sites.clear();
  for (let r = 0; r < spec.rows; r++) {
    for (let col = 0; col < spec.cols; col++) {
      const q = col - (r >> 1), k = key(q, r);
      let terrain = "plain";            // later marks override earlier ones
      if (marked.hills.has(k)) terrain = "hills";
      if (marked.mountains.has(k)) terrain = "mountains";
      if (marked.marsh.has(k)) terrain = "marsh";
      if (marked.forest.has(k)) terrain = "forest";
      if (marked.road.has(k)) terrain = "road"; // a road mark carves the pass
      if (marked.river.has(k)) terrain = "water";
      if (marked.ford.has(k)) terrain = "ford";
      if (marked.bridge.has(k)) terrain = "bridge";
      tiles.set(k, { q, r, terrain });
    }
  }
  for (const s of spec.settlements) {
    const k = key(s.at[0], s.at[1]);
    if (!(s.kind in KIND_GLYPH)) throw new Error(`聚落 ${s.id}：未知类别 ${s.kind}`);
    if (!tiles.has(k) || tiles.get(k).terrain === "water") throw new Error(`聚落 ${s.id} 落在图外或河中`);
    if (!s.hidden) tiles.get(k).terrain = "settlement";
    // a hidden lair's hex keeps its natural terrain — no render tell, no cost hole
    settlements.set(s.id, s);
  }
  world.party = settlements.get(spec.start).at.slice();
  world.gold = GOLD_START;
  world.gear = seedGear();   // the heroes ride out with their template gear
  world.contract = null;
  for (const p of spec.parties || []) {
    if (!(p.kind in PARTY_GLYPH)) throw new Error(`队伍 ${p.id}：未知类别 ${p.kind}`);
    for (const wp of p.route || []) if (!settlements.has(wp)) throw new Error(`队伍 ${p.id}：未知途经 ${wp}`);
    if (p.kind === "bandit" && (!p.home || (p.prowl || 0) < 0)) throw new Error(`匪伙 ${p.id} 须有巢穴`);
    const anchor = settlements.get(p.home || p.route[0]).at;
    const route = p.route || [];
    world.parties.push({
      pid: p.id, name: p.name, kind: p.kind, pos: anchor.slice(),
      speed: p.speed, route, home: p.home ? anchor.slice() : null,
      prowl: p.prowl || 0, leg: route.length ? 1 % route.length : 0, alive: true,
    });
  }
  for (const s of spec.sites || []) {
    const k = key(s.at[0], s.at[1]);
    if (!tiles.has(k) || COST[tiles.get(k).terrain] == null) throw new Error(`要隘 ${s.id} 落在图外或不可入`);
    sites.set(s.id, s);
  }
}

/* ---------------- pathfinding (one Dijkstra for reachability and paths) ---------------- */
function dijkstra(start, goal = null) {
  const startK = key(start[0], start[1]);
  const costs = new Map([[startK, 0]]);
  const prev = new Map();
  const heap = [[0, startK]];
  const lift = (i) => {
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (heap[p][0] <= heap[i][0]) break;
      const t = heap[p]; heap[p] = heap[i]; heap[i] = t; i = p;
    }
  };
  const pop = () => {
    const top = heap[0], last = heap.pop();
    if (heap.length) {
      heap[0] = last;
      let i = 0;
      for (;;) {
        let m = i; const l = 2 * i + 1, r = l + 1;
        if (l < heap.length && heap[l][0] < heap[m][0]) m = l;
        if (r < heap.length && heap[r][0] < heap[m][0]) m = r;
        if (m === i) break;
        const t = heap[m]; heap[m] = heap[i]; heap[i] = t; i = m;
      }
    }
    return top;
  };
  while (heap.length) {
    const [c, k] = pop();
    if (c > (costs.has(k) ? costs.get(k) : 1 << 30)) continue;
    if (k === goal) break; // goal cost is final — big-map speed
    const [q, r] = pOf(k);
    for (const [dq, dr] of DIRS) {
      const nk = key(q + dq, r + dr);
      const t = tiles.get(nk);
      if (!t || COST[t.terrain] == null) continue;
      const nc = c + COST[t.terrain];
      if (nc < (costs.has(nk) ? costs.get(nk) : 1 << 30)) {
        costs.set(nk, nc); prev.set(nk, k);
        heap.push([nc, nk]); lift(heap.length - 1);
      }
    }
  }
  return { costs, prev };
}

function pathTo(prev, destK) {
  const path = [destK];
  while (prev.has(path[0])) path.unshift(prev.get(path[0]));
  return path;
}

/* ---------------- the living world ---------------- */
function settlementAt(pos) {
  for (const s of settlements.values()) if (samePos(s.at, pos)) return s;
  return null;
}
function siteAt(pos) {
  for (const s of sites.values()) if (samePos(s.at, pos)) return s;
  return null;
}

function sightOf() {
  return SIGHT + (tiles.get(key(world.party[0], world.party[1])).terrain === "hills" ? 1 : 0);
}

/* first sighting of parties and hidden lairs — BB's exploration reveal */
function spot() {
  const reach = sightOf();
  for (const p of world.parties) {
    if (p.alive && !world.spotted.has(p.pid) && hexDist(p.pos, world.party) <= reach) {
      world.spotted.add(p.pid);
      log(`第${world.day}日 · 斥候望见${p.name}`, HOSTILE.has(p.kind) ? "r" : "b");
    }
  }
  for (const s of settlements.values()) {
    if (s.hidden && !world.spotted.has(s.id) && hexDist(s.at, world.party) <= reach) {
      world.spotted.add(s.id);
      log(`第${world.day}日 · 探得贼巢所在——${s.name}！`, "r");
    }
  }
}

/* advance a party up to its speed along the cheapest path */
function stepToward(party, dest) {
  if (samePos(party.pos, dest)) return;
  const destK = key(dest[0], dest[1]);
  const { costs, prev } = dijkstra(party.pos, destK);
  if (!costs.has(destK)) return;
  const path = pathTo(prev, destK);
  let budget = party.speed, i = 0;
  while (i + 1 < path.length && budget >= tileCost(path[i + 1])) {
    budget -= tileCost(path[i + 1]);
    i++;
  }
  party.pos = pOf(path[i]);
}

/* one day of the living world */
function tickParties() {
  for (const p of world.parties) {
    if (!p.alive) continue;
    if (p.kind === "bandit") {
      // prowl: a real day's march within the leash, drawn to the roads
      const { costs } = dijkstra(p.pos);
      const cands = [], roads = [];
      for (const [k, c] of costs) {
        if (c <= p.speed && hexDist(pOf(k), p.home) <= p.prowl) {
          cands.push(k);
          if (tiles.get(k).terrain === "road") roads.push(k);
        }
      }
      const pool = roads.concat(roads, cands);   // roads weighted 3× in total
      p.pos = pOf(pool[Math.floor(rnd() * pool.length)]);
    } else if (p.kind === "hunter") {
      stepToward(p, world.party);              // the writ names the bureau
    } else if (p.route.length) {
      const dest = settlements.get(p.route[p.leg]).at;
      stepToward(p, dest);
      if (samePos(p.pos, dest)) p.leg = (p.leg + 1) % p.route.length;
    }
  }
  // the world grinds on without the player: bandits maul caravans they catch
  for (const p of world.parties) {
    if (p.kind === "caravan" && p.alive) {
      for (const h of world.parties) {
        if (h.alive && HOSTILE.has(h.kind) && hexDist(h.pos, p.pos) <= 1) {
          log(`第${world.day}日 · 道上传闻：${h.name}扑向了${p.name}`, "sys");
        }
      }
    }
  }
}

function hostileInReach() {
  return world.parties.find((p) => p.alive && HOSTILE.has(p.kind)
    && hexDist(p.pos, world.party) <= 1) || null;
}

function burnRation() {
  world.provisions -= dailyFood();
  if (world.provisions <= 0) {
    world.provisions = 0;
    log(`第${world.day}日 · 粮草告罄，人马饥疲`, "r");
  }
  const wage = dailyWage();
  world.gold -= wage;
  if (world.gold < 0) { world.gold = 0; log(`第${world.day}日 · 饷银无着，军心浮动`, "r"); }
}

/* ---------------- the silver economy (mirrors sim/overworld.py exactly) ---------------- */

/* the friendly settlement underfoot, if any — where money talks */
function tradePost() {
  const s = settlementAt(world.party);
  if (s && FRIENDLY_KINDS.has(s.kind) && !world.destroyed.has(s.id)) return s;
  return null;
}

/* 市集: provisions for silver — fill up, limited by the purse (market_buy) */
function marketBuy() {
  const s = tradePost();
  if (!s) return 0;
  let price = PROVISION_PRICE[s.kind];
  if (world.infamy >= INFAMY_PRICED) price += (price + 1) >> 1;  // outlaws pay more
  const need = capacity() - world.provisions;
  const n = Math.max(0, Math.min(need, Math.floor(world.gold / price)));
  if (n) {
    world.provisions += n;
    world.gold -= n * price;
    log(`第${world.day}日 · 市集买粮${n}日，费银${n * price}两`, "sys");
  }
  return n;
}

/* 镖单: escorts to the 3 nearest cities/towns + a bounty on every discovered,
   standing lair. Deterministic: no dice, the map IS the job board (jobs) */
function cityJobs() {
  const s = tradePost();
  if (!s || world.infamy >= INFAMY_HUNTED) return [];  // nobody bonds to the hunted
  const { costs } = dijkstra(world.party);
  const out = [];
  const dests = [...settlements.values()]
    .filter((x) => x.id !== s.id && (x.kind === "city" || x.kind === "town")
      && !world.destroyed.has(x.id) && costs.has(key(x.at[0], x.at[1])))
    .sort((a, b) => costs.get(key(a.at[0], a.at[1])) - costs.get(key(b.at[0], b.at[1])))
    .slice(0, world.infamy >= INFAMY_PRICED ? 1 : 3);
  for (const d of dests) {
    const days = Math.max(1, Math.ceil(costs.get(key(d.at[0], d.at[1])) / MOVE_PER_DAY));
    out.push({ kind: "escort", to: d.id, name: `押镖至${d.name}`,
               pay: days * ESCORT_RATE + 20, days });
  }
  for (const lair of settlements.values()) {
    if (lair.kind === "stronghold" && world.spotted.has(lair.id)
        && !world.destroyed.has(lair.id)) {
      out.push({ kind: "bounty", target: lair.id, name: `剿灭${lair.name}`, pay: BOUNTY_PAY });
    }
  }
  return out;
}

/* one active contract at a time — the BB rule (take_job) */
function takeJob(job) {
  if (world.contract) return false;
  world.contract = Object.assign({}, job);
  log(`第${world.day}日 · 接下镖单——${job.name}（酬${job.pay}两）`, "b");
  return true;
}

/* a lost battle voids the bond — callers decide when (fail_contract) */
function failContract() {
  if (world.contract) {
    log(`第${world.day}日 · 镖单失约——${world.contract.name}，酬银泡了汤`, "r");
    world.contract = null;
  }
}

/* 铁匠铺 (cities only): one hero's gear, one grade up the 品阶 ladder (smith_upgrade) */
function smithUpgrade(uid, slot) {
  const s = tradePost();
  if (!s || s.kind !== "city" || !GEAR_SLOTS.includes(slot) || !(uid in world.gear))
    return null;
  const cur = world.gear[uid][slot] || "fan";
  const i = QUALITY_LADDER.indexOf(cur) + 1;
  if (i >= QUALITY_LADDER.length) return null;
  const nxt = QUALITY_LADDER[i];
  const price = SMITH_PRICE[nxt];
  if (world.gold < price) return null;
  world.gold -= price;
  world.gear[uid][slot] = nxt;
  const h = HEROES.find((t) => t.id === uid);
  log(`第${world.day}日 · 铁匠铺升造：${h ? h.name : uid}之${SLOT_LABEL[slot]}升至` +
      `${QUALITY_LABEL[nxt]}，费银${price}两`, "b");
  return nxt;
}

/* the world hex seeds the battle; an anchored site or a lair's own scenario
   overrides the terrain table — places mean something here */
function emitEncounter(p) {
  const enc = spec.encounters || {};
  const terrain = tiles.get(key(world.party[0], world.party[1])).terrain;
  const site = siteAt(world.party);
  const lair = settlementAt(world.party);
  const scen = (site && site.scenario) || (lair && lair.scenario)
    || enc[terrain] || enc.plain;
  const full = SCEN_NAME[scen] || scen;
  log(`第${world.day}日 · ${p.name}截住了镖队——${full.split(" · ")[0]}！`, "r");
  pendingScen = scen;
  pendingParty = p;
  document.getElementById("ovtitle").textContent = "截击";
  document.getElementById("ovtext").textContent =
    `${p.name}截住了镖队！【${full}】` + (site ? `（${site.name}）` : "");
  pendingKind = "encounter";
  overlayEl.style.display = "flex";
}

/* the bureau turns bandit: a caravan or patrol within reach can be prey */
function offerWaylay(p) {
  if (busy) return;
  const scen = WAYLAY_SCEN[p.kind];
  pendingScen = scen;
  pendingParty = p;
  pendingKind = "waylay";
  document.getElementById("ovtitle").textContent = "劫道";
  document.getElementById("ovtext").textContent =
    `伏于道旁，劫${p.name}？官府闻之必怒。【${SCEN_NAME[scen] || scen}】`;
  overlayEl.style.display = "flex";
}

/* shared end-of-day bookkeeping; returns the interceptor, if any */
function spawnHunter() {
  if (world.infamy < INFAMY_HUNTED) return;
  if (world.parties.some((p) => p.kind === "hunter" && p.alive)) return;
  const cities = [...settlements.values()].filter(
    (s) => s.kind === "city" && !world.destroyed.has(s.id));
  if (!cities.length) return;
  const src = cities.reduce((m, s) => hexDist(s.at, world.party) < hexDist(m.at, world.party) ? s : m);
  world.parties.push({ pid: "hunter_" + world.day, name: "缉捕官军", kind: "hunter",
                       pos: src.at.slice(), speed: 9, route: [], home: null,
                       prowl: 0, leg: 0, alive: true });
  world.spotted.add("hunter_" + world.day);
  log(`第${world.day}日 · 官府出了海捕文书——缉捕官军自${src.name}出动！`, "r");
}

function dusk() {
  burnRation();
  spawnHunter();
  tickParties();
  spot();
  const p = hostileInReach();
  if (p) emitEncounter(p);
  return p;
}

/* hold position for a day (wait out a patrol; food still burns — buy at the 市集) */
function doCamp() {
  if (busy) return;
  log(`第${world.day}日 · 就地扎营一日`, "sys");
  dusk();
  world.day += 1;
  refresh();
}

/* a fallen lair: mark the ruin, disband every band that called it home;
   a matching bounty pays out on the spot (sim raze()) */
function applyRaze(lair) {
  world.destroyed.add(lair.id);
  for (const p of world.parties)
    if (p.home && samePos(p.home, lair.at)) p.alive = false;
  if (world.contract && world.contract.kind === "bounty"
      && world.contract.target === lair.id) {
    world.gold += world.contract.pay;
    log(`第${world.day}日 · 剿匪功成——${world.contract.name}，赏银${world.contract.pay}两入账`, "b");
    world.contract = null;
  }
}

function doAssault() {
  const lair = settlementAt(world.party);
  if (busy || !lair || lair.kind !== "stronghold" || world.destroyed.has(lair.id)) return;
  const scen = lair.scenario || "gongzhai";
  launchBattle({ kind: "assault", target: lair.id, scenario: scen });
}

/* one-file edition: the battle engine rides inside and fights in an iframe —
   no server, no navigation, the verdict returns by direct callback */
let frameVerdict = null;
function launchBattle(pend) {
  pendingBattle = pend;
  try { localStorage.removeItem("sj_battle_result"); } catch (e) {}  // no stale verdicts
  saveState();
  if (typeof EMBEDDED_BATTLE !== "undefined") {
    frameVerdict = null;
    overlayEl.style.display = "none";
    const wrap = document.createElement("div");
    wrap.id = "battleframe";
    wrap.style.cssText = "position:fixed;inset:0;z-index:50;background:#1d1a15;";
    const f = document.createElement("iframe");
    f.style.cssText = "width:100%;height:100%;border:0;";
    const inject = `<script>window.__SJ_SCEN=${JSON.stringify(pend.scenario)};window.__SJ_CAMPAIGN=1;` +
      `window.__SJ_GEAR=${JSON.stringify(world.gear)};<\/script>`;
    f.srcdoc = EMBEDDED_BATTLE.replace("<script>", inject + "<script>");
    wrap.appendChild(f);
    document.body.appendChild(wrap);
  } else {
    try { localStorage.setItem("sj_gear", JSON.stringify(world.gear)); } catch (e) {}
    location.href = "index.html?scenario=" + pend.scenario + "&campaign=1";
  }
}
window.__sjBattleVerdict = (res) => { frameVerdict = res; };
window.__sjCloseBattle = () => {
  const w = document.getElementById("battleframe");
  if (w) w.remove();
  applyBattleResult(frameVerdict);
  frameVerdict = null;
  refresh();
};

/* march day by day toward a hex; a hostile within reach — at departure or on
   any step — halts the column (sim/overworld.py travel(), animated per day) */
async function travelTo(destK) {
  busy = true;
  drawerOpen = false;
  clearHexHover();
  updateBar();
  const path = pathTo(dij.prev, destK);
  let i = 0;
  while (i + 1 < path.length) {
    let budget = MOVE_PER_DAY;
    let interceptor = hostileInReach();          // no slipping past at the gates
    while (!interceptor && i + 1 < path.length && budget >= tileCost(path[i + 1])) {
      budget -= tileCost(path[i + 1]);
      i++;
      world.party = pOf(path[i]);
      spot();                                    // scouts watch while marching
      renderParties();                           // the column walks the grids
      centerOn(world.party);
      await sleep(95);
      interceptor = hostileInReach();            // BB: contact stops the column
    }
    if (budget === MOVE_PER_DAY && !interceptor)
      throw new Error("terrain cost exceeds MOVE_PER_DAY — impassable map");
    if (interceptor) {
      burnRation();                              // the battle eats the day
      emitEncounter(interceptor);
    } else {
      interceptor = dusk();
    }
    const s = settlementAt(world.party);
    if (!interceptor && world.contract && world.contract.kind === "escort"
        && s && s.id === world.contract.to) {
      world.gold += world.contract.pay;          // 镖银两讫 (sim: travel arrival)
      log(`第${world.day}日 · 镖银两讫——${world.contract.name}，得${world.contract.pay}两`, "b");
      world.contract = null;
    }
    renderPlaces(); renderParties(); updateBar();
    centerOn(world.party);
    if (interceptor || i + 1 >= path.length) {
      if (!interceptor) {
        log(`第${world.day}日 · 行至${s ? s.name : locName(world.party)}`, "sys");
      }
      world.day += 1;
      break;
    }
    world.day += 1;
    updateBar();
    await sleep(280);
  }
  busy = false;
  refresh();
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

const NS = "http://www.w3.org/2000/svg";
function svgEl(tag, attrs) {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, v);
  return el;
}

function buildBoard() {
  boardEl.innerHTML = "";
  const w = HEX * SQRT3 * (spec.cols + 1) + 60, h = HEX * 1.5 * spec.rows + 70;
  BOARD_W = w; BOARD_H = h;                         // the camera pans this board
  boardEl.setAttribute("viewBox", `0 0 ${w} ${h}`); // placeholder until applyCam
  boardEl.setAttribute("preserveAspectRatio", "xMidYMid slice");
  const tileLayer = svgEl("g");
  for (const t of tiles.values()) {
    const { x, y } = hexToPix(t.q, t.r);
    const p = svgEl("polygon", { points: hexPoints(x, y), class: "hex",
                                 fill: TERRAIN_FILL[t.terrain] });
    const k = key(t.q, t.r);
    p.dataset.k = k;
    p.addEventListener("click", () => onHexClick(k));
    p.addEventListener("mouseenter", () => onHexHover(k));
    p.addEventListener("mouseleave", () => clearHexHover());
    tileLayer.appendChild(p);
    if (TERRAIN_GLYPH[t.terrain]) {
      const tx = svgEl("text", { x, y: y + 3.5, class: "tglyph",
                                 fill: t.terrain === "mountains" ? "#6e6250" : "#8d8268" });
      tx.textContent = TERRAIN_GLYPH[t.terrain];
      tileLayer.appendChild(tx);
    }
  }
  boardEl.appendChild(tileLayer);
  // 藩镇 territory captions — big, faint, part of the land itself
  const labelLayer = svgEl("g", { "pointer-events": "none" });
  for (const lb of spec.labels || []) {
    const { x, y } = hexToPix(lb.at[0], lb.at[1]);
    const t = svgEl("text", { x, y, "text-anchor": "middle",
      "font-size": 26, fill: "rgba(91,83,70,.35)", "font-weight": "bold" });
    t.textContent = lb.text;
    labelLayer.appendChild(t);
  }
  boardEl.appendChild(labelLayer);
  // anchored set-pieces: 关 / 陉 / 桥 / 渡 — fixed-map landmarks, always visible
  const siteLayer = svgEl("g", { "pointer-events": "none" });
  for (const s of sites.values()) {
    const { x, y } = hexToPix(s.at[0], s.at[1]);
    siteLayer.appendChild(svgEl("rect", { x: x - 6, y: y - 6, width: 12, height: 12,
      rx: 2, fill: "rgba(43,38,32,.88)", stroke: "#f5efe0", "stroke-width": .5 }));
    const g = svgEl("text", { x, y: y + 3.2, class: "glyph", "font-size": 9 });
    g.textContent = s.glyph || "址";
    siteLayer.appendChild(g);
    const lb = svgEl("text", { x, y: y + 15.5, class: "slabel" });
    lb.textContent = s.name;
    siteLayer.appendChild(lb);
  }
  boardEl.appendChild(siteLayer);
  placeLayer = svgEl("g", { "pointer-events": "none" });
  fxLayer = svgEl("g", { "pointer-events": "none" });
  partyLayer = svgEl("g", { "pointer-events": "none" });
  boardEl.appendChild(placeLayer);
  boardEl.appendChild(fxLayer);
  boardEl.appendChild(partyLayer);
}

/* settlements — hidden lairs invisible until spotted, razed lairs are ruins 墟 */
function renderPlaces() {
  placeLayer.innerHTML = "";
  for (const s of settlements.values()) {
    if (s.hidden && !world.spotted.has(s.id)) continue;
    const { x, y } = hexToPix(s.at[0], s.at[1]);
    const razed = world.destroyed.has(s.id);
    placeLayer.appendChild(svgEl("circle", { cx: x, cy: y, r: 8,
      fill: razed ? "#8a8170" : KIND_FILL[s.kind], stroke: "#1d1a15", "stroke-width": 1 }));
    const g = svgEl("text", { x, y: y + 3.5, class: "glyph",
      "font-size": s.kind === "city" || s.kind === "town" ? 11 : 9.5 });
    g.textContent = razed ? "墟" : KIND_GLYPH[s.kind];
    placeLayer.appendChild(g);
    const lb = svgEl("text", { x, y: y + 17.5, class: "plabel" });
    lb.textContent = s.name;
    placeLayer.appendChild(lb);
  }
}

/* spotted parties at live positions, then the bureau's column on top */
const WAYLAY_SCEN = { caravan: "jiebiao", patrol: "duijue" };
const WAYLAY_LOOT = { caravan: 150, patrol: 60 };

function renderParties() {
  partyLayer.innerHTML = "";
  for (const p of world.parties) {
    if (!p.alive || !world.spotted.has(p.pid)) continue;
    const { x, y } = hexToPix(p.pos[0], p.pos[1]);
    const preyable = !busy && p.kind in WAYLAY_SCEN
      && hexDist(p.pos, world.party) <= 1;
    const c = svgEl("circle", { cx: x, cy: y, r: 6.5,
      fill: PARTY_FILL[p.kind], stroke: preyable ? "#e8c14f" : "#1d1a15",
      "stroke-width": preyable ? 2 : 1 });
    if (preyable) {
      c.setAttribute("pointer-events", "auto");
      c.style.cursor = "pointer";
      c.addEventListener("click", () => offerWaylay(p));
    }
    partyLayer.appendChild(c);
    const g = svgEl("text", { x, y: y + 2.8, class: "glyph", "font-size": 8 });
    g.textContent = PARTY_GLYPH[p.kind];
    partyLayer.appendChild(g);
  }
  const { x, y } = hexToPix(world.party[0], world.party[1]);
  partyLayer.appendChild(svgEl("circle", { cx: x, cy: y, r: 8.5,
    fill: "#1b4965", stroke: "#b8860b", "stroke-width": 2 }));
  const g = svgEl("text", { x, y: y + 3.3, class: "glyph", "font-size": 9.5 });
  g.textContent = "镖";
  partyLayer.appendChild(g);
}

function refresh() {
  saveState();
  dij = dijkstra(world.party);
  const curK = key(world.party[0], world.party[1]);
  for (const el of boardEl.querySelectorAll(".hex"))
    el.classList.toggle("reach", el.dataset.k !== curK && dij.costs.has(el.dataset.k));
  renderPlaces(); renderParties(); updateBar();
}

function destName(k) {
  const pos = pOf(k);
  const s = settlementAt(pos);
  if (s && (!s.hidden || world.spotted.has(s.id)))
    return world.destroyed.has(s.id) ? s.name + "（墟）" : s.name;
  // an undiscovered lair reads as its natural ground — no name tell
  const site = siteAt(pos);
  if (site) return site.name;
  return TERRAIN_NAME[tiles.get(k).terrain] || "旷野";
}
const locName = (pos) => destName(key(pos[0], pos[1]));

function updateBar() {
  document.getElementById("daylabel").textContent = `第 ${world.day} 日`;
  document.getElementById("provlabel").textContent =
    `粮草 ${world.provisions}/${capacity()} · ${headcount()}人(耗${dailyFood()}·饷${dailyWage()})`;
  document.getElementById("goldlabel").textContent = `银两 ${world.gold}`;
  document.getElementById("contractlabel").textContent =
    (world.contract ? `镖单·${world.contract.name}` : "") +
    (world.infamy ? `　恶名 ${world.infamy}${world.infamy >= INFAMY_HUNTED ? "·被缉捕" : ""}` : "");
  const s0 = settlementAt(world.party);
  document.getElementById("loclabel").textContent = locName(world.party) +
    (s0 && s0.fanzhen && (!s0.hidden || world.spotted.has(s0.id)) ? `（${s0.fanzhen}）` : "");
  const tb = document.getElementById("townbtn");
  const post = tradePost();
  tb.style.display = post && !busy && !drawerOpen ? "inline-block" : "none";
  tb.textContent = drawerOpen ? "出城 ▸" : "入城 ◂";
  if (!post) drawerOpen = false;
  renderCity();
  const s = settlementAt(world.party);
  const lair = s && s.kind === "stronghold" && !world.destroyed.has(s.id) && world.spotted.has(s.id);
  document.getElementById("assault").style.display = lair && !busy ? "" : "none";
  document.getElementById("campbtn").disabled = busy;
}

/* the town drawer: a folder tree on the right — 城 ▸ 市集 / 镖单 / 铁匠铺 ▸ 各人 */
let drawerOpen = false;

function renderCity() {
  const el = document.getElementById("citypanel");
  const s = tradePost();
  if (!s || busy || !drawerOpen) { el.style.display = "none"; el.innerHTML = ""; return; }
  const open = new Set([...el.querySelectorAll("details[open]")].map((d) => d.dataset.k));
  if (!el.innerHTML) { open.add("market"); open.add("jobs"); }   // first opening
  const o = (k, dflt) => (el.innerHTML ? open.has(k) : dflt) ? " open" : "";
  let price = PROVISION_PRICE[s.kind];
  if (world.infamy >= INFAMY_PRICED) price += (price + 1) >> 1;  // shown as charged
  const need = PROVISIONS_MAX - world.provisions;
  const canBuy = Math.max(0, Math.min(need, Math.floor(world.gold / price)));
  let html = `<button onclick="uiTown()" style="float:right">出城 ▸</button>` +
             `<b>${s.name}</b>${s.fanzhen ? `（${s.fanzhen}）` : ""}` +
             ` <span style="color:#c9bda0">银两 ${world.gold}</span>`;
  html += `<details data-k="market"${o("market", true)}><summary>市集</summary>` +
          `<div class="leaf">粮草 ${world.provisions}/${capacity()} · ${price}两/份<br>` +
          `<button onclick="uiBuy()" ${canBuy ? "" : "disabled"}>` +
          (canBuy ? `买粮${canBuy}日 · ${canBuy * price}两`
                  : need ? "银两不足" : "粮草已满") + `</button></div></details>`;
  html += `<details data-k="jobs"${o("jobs", true)}><summary>镖单</summary>`;
  const board = cityJobs();
  if (!board.length) html += `<div class="leaf">暂无镖单</div>`;
  board.forEach((jb, i) => {
    html += `<div class="job leaf"><span>${jb.name} · ${jb.pay}两</span>` +
            `<button onclick="uiTake(${i})" ${world.contract ? "disabled" : ""}>接单</button></div>`;
  });
  if (world.contract) html += `<div class="leaf" style="color:#c9bda0">在身：${world.contract.name}</div>`;
  html += `</details>`;
  // 招募: the named candidates this place is mustering (BB pool + reveal)
  {
    let rrows = "";
    for (const r of recruitsHere()) {
      const tr = r.reveal >= 1
        ? (r.traits.map((t)=>R_TRAIT[t]).join("、") || "无异")
        : `<button onclick="uiGossip('${r.rid}')" ${world.gold < Math.max(5, r.fee/10|0) ? "disabled":""}>茶馆${Math.max(5, r.fee/10|0)}</button>`;
      const tl = r.reveal >= 2
        ? `共${Object.values(r.talents).reduce((a,b)=>a+b,0)}★`
        : `<button onclick="uiExam('${r.rid}')" ${world.gold < Math.max(15, r.fee/4|0) ? "disabled":""}>考较${Math.max(15, r.fee/4|0)}</button>`;
      rrows += `<div class="job leaf" title="${r.blurb}"><span>${r.nick}·${r.name}` +
               `<span style="color:#c9bda0">（${r.bg_name} 武${r.stats.skill} 血${r.stats.hp}）</span></span>` +
               `<button onclick="uiHire('${r.rid}')" ${world.gold < r.fee ? "disabled":""}>招 ${r.fee}·饷${r.wage}</button></div>` +
               `<div class="leaf" style="font-size:11px;color:#b3a98c">特性：${tr}　天赋：${tl}</div>`;
    }
    world.members.forEach((m, i) => {
      rrows += `<div class="job leaf"><span>${m.nick ? m.nick+"·" : ""}${m.name}（${m.bg_name||""} 饷${m.wage}）</span>` +
               `<button onclick="uiFire(${i})">遣散</button></div>`;
    });
    html += `<details data-k="recruit"${o("recruit", false)}><summary>招募 · 在册${headcount()}人</summary>${rrows}</details>`;
  }
  if (s.kind === "city" || s.kind === "town") {
    let rows = "";
    for (const h of HEROES) {
      if (!h.smith) continue;
      const g = world.gear[h.id] || {};
      let pts = (g.armor_dmg || 0) + (g.helm_dmg || 0);
      if (g.wpn_dura != null) pts += (h.wpnDura || 0) - g.wpn_dura;
      if (g.wpn2_dura != null) pts += (h.wpn2Dura || 0) - g.wpn2_dura;
      if (pts <= 0) continue;
      const bill = Math.ceil(pts / 3);
      rows += `<div class="job"><span>${h.name} 甲械损${pts}点</span>` +
              `<button onclick="uiMend('${h.id}')" ${world.gold < bill ? "disabled" : ""}>修缮 ${bill}两</button></div>`;
    }
    if (rows) html += `<details data-k="mend" open><summary>修缮</summary>${rows}</details>`;
  }
  if (s.kind === "city" && world.infamy > 0) {
    const cost = world.infamy * ATONE_RATE;
    html += `<details data-k="yamen" open><summary>衙门</summary>` +
            `<div class="leaf">恶名 ${world.infamy} · 海捕${world.infamy >= INFAMY_HUNTED ? "已发" : "未发"}<br>` +
            `<button onclick="uiAtone()" ${world.gold < cost ? "disabled" : ""}>` +
            `纳赎罪银 ${cost}两</button></div></details>`;
  }
  if (s.kind === "city") {
    html += `<details data-k="smith"${o("smith", false)}><summary>铁匠铺</summary>`;
    for (const hero of HEROES) {
      if (!hero.smith) continue;             // militia stay off the anvil
      const g = world.gear[hero.id] || {};
      html += `<details data-k="smith-${hero.id}"${o("smith-" + hero.id, false)}>` +
              `<summary>${hero.name}</summary><div class="leaf">`;
      for (const slot of GEAR_SLOTS) {
        if (slot === "wpn2_q" && !hero.wpn2) continue;
        const cur = g[slot] || "fan";
        const i = QUALITY_LADDER.indexOf(cur) + 1;
        if (i >= QUALITY_LADDER.length) {
          html += `<button disabled>${SLOT_LABEL[slot]}·神品</button> `;
          continue;
        }
        const nxt = QUALITY_LADDER[i], cost = SMITH_PRICE[nxt];
        html += `<button onclick="uiSmith('${hero.id}','${slot}')" ` +
                `${world.gold < cost ? "disabled" : ""}>` +
                `${SLOT_LABEL[slot]} ${QUALITY_LABEL[cur]}→${QUALITY_LABEL[nxt]} ${cost}两</button> `;
      }
      html += `</div></details>`;
    }
    html += `</details>`;
  }
  el.innerHTML = html;
  el.style.display = "block";
}
window.uiBuy = () => { marketBuy(); refresh(); };
window.uiAtone = () => {
  const cost = world.infamy * ATONE_RATE;
  if (world.gold >= cost && world.infamy > 0) {
    world.gold -= cost;
    log(`第${world.day}日 · 衙门纳赎罪银${cost}两，恶名洗清`, "sys");
    world.infamy = 0;
  }
  refresh();
};
window.uiTake = (i) => { const jb = cityJobs()[i]; if (jb) takeJob(jb); refresh(); };
window.uiSmith = (uid, slot) => { smithUpgrade(uid, slot); refresh(); };
function recruitsHere() {
  const s = tradePost();
  if (!s) return [];
  const epoch = Math.floor(world.day / R_REFRESH);
  if (!world._pool || world._pool.key !== s.id + ":" + epoch) {
    const taken = new Set(world.members.map((m) => m.rid));
    world._pool = { key: s.id + ":" + epoch,
                    list: rcPool(s, world.day).filter((r) => !taken.has(r.rid)) };
  }
  return world._pool.list;
}
const recById = (rid) => recruitsHere().find((r) => r.rid === rid);
window.uiGossip = (rid) => {
  const r = recById(rid); if (!r || r.reveal >= 1) return;
  const cost = Math.max(5, r.fee / 10 | 0);
  if (world.gold < cost) return;
  world.gold -= cost; r.reveal = Math.max(r.reveal, 1);
  log(`第${world.day}日 · 茶馆打探${r.name}：${r.traits.map((t)=>R_TRAIT[t]).join("、")||"无异"}`, "sys");
  refresh();
};
window.uiExam = (rid) => {
  const r = recById(rid); if (!r || r.reveal >= 2) return;
  const cost = Math.max(15, r.fee / 4 | 0);
  if (world.gold < cost) return;
  world.gold -= cost; r.reveal = Math.max(r.reveal, 2);
  const total = Object.values(r.talents).reduce((a,b)=>a+b,0);
  log(`第${world.day}日 · 医馆考较${r.name}：共${total}星`, "sys");
  refresh();
};
window.uiHire = (rid) => {
  const r = recById(rid);
  if (!r || world.gold < r.fee) return;
  world.gold -= r.fee;
  world.members.push(Object.assign({}, r));
  world._pool.list = world._pool.list.filter((x) => x.rid !== rid);
  log(`第${world.day}日 · ${r.nick}·${r.name}（${r.bg_name}）入伙，雇金${r.fee}两`, "b");
  refresh();
};
window.uiFire = (i) => {
  if (i >= 0 && i < world.members.length) {
    const m = world.members.splice(i, 1)[0];
    world.provisions = Math.min(world.provisions, capacity());
    log(`第${world.day}日 · 遣散${m.name}`, "sys");
  }
  refresh();
};
window.uiMend = (uid) => {
  const h = HEROES.find((x) => x.id === uid);
  const g = world.gear[uid] || {};
  let pts = (g.armor_dmg || 0) + (g.helm_dmg || 0);
  if (g.wpn_dura != null) pts += (h.wpnDura || 0) - g.wpn_dura;
  if (g.wpn2_dura != null) pts += (h.wpn2Dura || 0) - g.wpn2_dura;
  const bill = Math.ceil(Math.max(0, pts) / 3);
  if (bill > 0 && world.gold >= bill) {
    world.gold -= bill;
    g.armor_dmg = 0; g.helm_dmg = 0;
    delete g.wpn_dura; delete g.wpn2_dura;
    log(`第${world.day}日 · 铁铺修缮${h.name}甲械，费银${bill}两`, "sys");
  }
  refresh();
};
window.uiTown = () => { drawerOpen = !drawerOpen; refresh(); };
window.uiZoom = (f) => {
  const v0 = viewSize();
  const cx = cam.x + v0.w / 2, cy = cam.y + v0.h / 2;
  cam.scale = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, cam.scale * f));
  const v = viewSize();
  cam.x = cx - v.w / 2; cam.y = cy - v.h / 2;
  applyCam();
};
window.uiCenter = () => { centerOn(world.party); };

/* days a path takes at MOVE_PER_DAY budget per day (interception-free estimate) */
function daysAlong(path) {
  let days = 0, i = 0;
  while (i + 1 < path.length) {
    let budget = MOVE_PER_DAY;
    while (i + 1 < path.length && budget >= tileCost(path[i + 1])) {
      budget -= tileCost(path[i + 1]);
      i++;
    }
    days++;
  }
  return days;
}

/* path preview on hover, with day estimate — the battle page's move preview */
function onHexHover(k) {
  if (busy || !dij) return;
  clearHexHover();
  const curK = key(world.party[0], world.party[1]);
  if (k === curK || !dij.costs.has(k)) return;
  const path = pathTo(dij.prev, k);
  hoverPathEl = svgEl("polyline", {
    points: path.map((pk) => {
      const t = tiles.get(pk); const p = hexToPix(t.q, t.r);
      return p.x.toFixed(1) + "," + p.y.toFixed(1);
    }).join(" "),
    fill: "none", stroke: "#2f5d24", "stroke-width": 2.5,
    "stroke-dasharray": "6 4", "stroke-linecap": "round", opacity: .85,
  });
  fxLayer.appendChild(hoverPathEl);
  const days = daysAlong(path);
  hoverEl.innerHTML = `<b>去往 ${destName(k)}</b><br>` +
    `路费 ${dij.costs.get(k)} 移动力 · 约 ${days} 日（日行 ${MOVE_PER_DAY}）` +
    (days > world.provisions
      ? `<br><b style="color:#a02818">⚠ 粮草不济——须沿途友镇补给</b>` : "");
}

function clearHexHover() {
  if (hoverPathEl) { hoverPathEl.remove(); hoverPathEl = null; }
}

function onHexClick(k) {
  if (busy || !dij) return;
  const curK = key(world.party[0], world.party[1]);
  if (k === curK || !dij.costs.has(k)) return;
  travelTo(k);
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
  overlayEl = document.getElementById("overlay");
  hoverEl = document.getElementById("hoverinfo");
  const worldId = new URLSearchParams(location.search).get("world") || "hebei";
  const pick = document.getElementById("worldpick");
  if (pick) {
    pick.value = worldId;
    pick.addEventListener("change", (e) => { location.search = "?world=" + e.target.value; });
  }
  try {
    const res = await fetch(`world/${worldId}.json`, { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    spec = await res.json();
  } catch (err) {
    document.getElementById("subtitle").textContent = "无法载入舆图 " + worldId;
    if (logEl) {
      const d = document.createElement("div");
      d.style.color = "#a02818"; d.style.fontWeight = "bold";
      d.textContent = `舆图载入失败（${err.message}）——请强制刷新 Cmd+Shift+R；若仍失败，告诉我这行字。`;
      logEl.appendChild(d);
    }
    return;
  }
  document.getElementById("subtitle").textContent = `${spec.name} — ${spec.era}`;
  buildWorld();
  rngState = ((parseInt(new URLSearchParams(location.search).get("seed"), 10) || 1) >>> 0);
  const resumed = restoreState();   // the world survives the battle page
  buildBoard();
  initCamera();
  centerOn(world.party);
  if (resumed) {
    applyBattleResult();
    log(`第${world.day}日 · 行程继续（重开请按「重开」）`, "sys");
  } else {
    log(`镖局总号驻${settlements.get(spec.start).name}。点击舆图任意可达之处即出发；遇匪遇骑，开战或脱离悉听尊便。`, "sys");
  }
  if (!resumed) world.provisions = capacity();   // ride out with full packs
  spot();   // what the bureau can see from the gate on day one
  refresh();
}

document.getElementById("campbtn").addEventListener("click", doCamp);
document.getElementById("townbtn").addEventListener("click", window.uiTown);
document.getElementById("assault").addEventListener("click", doAssault);
document.getElementById("restartw").addEventListener("click", () => {
  try {
    localStorage.removeItem(STORE());
    localStorage.removeItem("sj_battle_result");
    localStorage.removeItem("sj_gear");
  } catch (e) {}
  location.reload();
});
document.getElementById("ovfight").addEventListener("click", () => {
  if (!pendingScen) return;
  launchBattle({ kind: pendingKind,
                 target: pendingParty ? pendingParty.pid : null,
                 scenario: pendingScen });
});
document.getElementById("ovflee").addEventListener("click", () => {
  overlayEl.style.display = "none";
  refresh();
});

boot();
