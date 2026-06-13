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
let HEX = 22; // per-world hex radius (spec.hexSize); the board outgrows the screen — the camera pans over it
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
const PROVISION_BASE = 6, CARRY_PER_HEAD = 12, EAT_PER_HEAD = 1, WAGE_PER_HEAD = 2; // ~12 days of 粮草 per head (BB-style packs)
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

/* ---- leveling (port of sim/progress.py): baseline, cap, star-fed growth ---- */
const MAX_LEVEL = 11;
const LEVEL_XP = [0, 0, 200, 550, 1050, 1750, 2700, 3950, 5550, 7550, 10000, 15000];
const GROW = { hp:{per:[3,5],room:55}, breath:{per:[3,5],room:50}, skill:{per:[1,3],room:28},
               resolve:{per:[2,4],room:40}, init:{per:[2,4],room:40}, dfn:{per:[1,2],room:16} };
const BATTLE_XP = 280, HERO_LEVEL = 3;
/* the founding four are CHARACTERS too — own traits + star talents, like any hire */
const HERO_BASE = {
  wang: { stats:{hp:55,skill:62,dfn:10,resolve:48,init:96,breath:87}, talents:{skill:2}, traits:["hanyong","jianzhuang"] },
  liu:  { stats:{hp:60,skill:60,dfn:6,resolve:45,init:104,breath:87}, talents:{skill:1,init:1}, traits:["hanyong","jiujiu"] },
  shi:  { stats:{hp:65,skill:58,dfn:5,resolve:50,init:90,breath:93}, talents:{hp:2}, traits:["shenli","tiefei"] },
  yan:  { stats:{hp:45,skill:56,dfn:8,resolve:42,init:112,breath:94}, talents:{init:2}, traits:["tiefei","jieao"] },
};
function levelForXp(xp){let l=1;for(let L=2;L<=MAX_LEVEL;L++)if(xp>=LEVEL_XP[L])l=L;return l;}
function newProgress(base, talents, level, traits){
  level = level || 1;
  return { level, xp: LEVEL_XP[level], stats: Object.assign({}, base),
           base: Object.assign({}, base), talents: Object.assign({}, talents),
           traits: (traits || []).slice(), revealed: [] };
}
const capOf = (p, a) => p.base[a] + GROW[a].room;
const starsOf = (p, a) => p.talents[a] || 0;
function levelUp(p, rng){
  const ranked = R_ATTRS.slice().sort((x, y) => {
    const wx = (1 + starsOf(p,x)*4) * (capOf(p,x) > p.stats[x] ? 1 : 0) + (capOf(p,x)-p.stats[x])*0.01;
    const wy = (1 + starsOf(p,y)*4) * (capOf(p,y) > p.stats[y] ? 1 : 0) + (capOf(p,y)-p.stats[y])*0.01;
    return (wy - wx) || (rng.next() - 0.5);
  });
  for (const a of ranked.filter((a)=>capOf(p,a) > p.stats[a]).slice(0,3)) {
    let g = rng.int(GROW[a].per[0], GROW[a].per[1] + starsOf(p,a));
    g = Math.min(g, capOf(p,a) - p.stats[a]);
    if (g <= 0) continue;
    p.stats[a] += g;
    if (starsOf(p,a) && !p.revealed.includes(a)) p.revealed.push(a);
  }
  p.level += 1;
}
function awardXp(p, amount, rng){
  p.xp += amount;
  const target = levelForXp(p.xp);
  let n = 0;
  while (p.level < target) { levelUp(p, rng); n++; }
  return n;
}
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
  for (let i=0;i<R_POOL;i++) {
    const r = rcGenerate(rng, rng.weighted(keys,wts), i);
    r.rid = `${settlement.id}:${epoch}:${r.rid}`;   // unique per place+epoch — no rid collisions
    out.push(r);
  }
  return out;
}
/* the founders still standing — the fallen don't come back (BB permadeath) */
const livingCore = () => CORE_ROSTER.filter((id) => !world.fallen.has(id));
function headcount() { return livingCore().length + world.members.length; }
function capacity() { return PROVISION_BASE + CARRY_PER_HEAD * headcount() + PACK_CARRY * (world.packs || 0); }
function dailyFood() { return EAT_PER_HEAD * headcount(); }
function dailyWage() { return WAGE_PER_HEAD * livingCore().length + world.members.reduce((s, m) => s + m.wage, 0); }
function companyWiped() { return livingCore().length === 0 && world.members.length === 0; }

/* ---- the silver economy (M2, mirrors sim/overworld.py): markets, escorts, the smith ---- */
const GOLD_START = 100;
const PROVISION_PRICE = { city: 2, town: 2, village: 3 };  // 两 per day of 粮草
const ESCORT_RATE = 48, ESCORT_BASE = 40;                  // 镖银 = 底银 + 每日脚程
const BOUNTY_BASE = 180, BOUNTY_RATE = 44;                 // 破寨赏 scales with the trek to the 寨
const HUNT_BASE = 120, HUNT_RATE = 36;                     // 剿匪赏: hunt a roaming band on the road
const HUNTABLE = new Set(["bandit", "raider"]);            // bounty-able foes (not 官军 hunters)
const QUALITY_LADDER = ["fan", "liang", "jing", "zhen", "shen"];
const QUALITY_LABEL = { fan: "凡品", liang: "良品", jing: "精品", zhen: "珍品", shen: "神品" };
const SMITH_PRICE = { liang: 100, jing: 250, zhen: 600, shen: 1500 };
const GEAR_SLOTS = ["wpn_q", "wpn2_q", "armor_q", "helmet_q"];
const SLOT_LABEL = { wpn_q: "兵", wpn2_q: "副", armor_q: "甲", helmet_q: "盔" };

/* ---- BB-style settlement buildings (web map): 客栈 intel, 校场 drill, 马行 packs ---- */
const INTEL_PRICE = 25;                   // 客栈: a rumor that pins the nearest hidden 寨
const DRILL_TIERS = [                      // 校场: 银多则练得勤 — more silver buys more 经验
  { key: "light", name: "操演", xp: 90,  per: 8 },
  { key: "drill", name: "操练", xp: 200, per: 16 },
  { key: "hard",  name: "苦练", xp: 420, per: 30 },
];
const drillCost = (tier, n) => tier.per * n;   // n = the heads put through the yard
const PACK_CARRY = 12, PACK_MAX = 6;      // 马行: each 驮马 hauls +12 days of 粮草
const packBill = (n) => 80 + 60 * n;      // the n-th 驮马 (0-indexed) costs more
/* a settlement's building roster grows village → town → city (BB-style) */
const BUILDINGS = { village: ["market", "inn", "recruit", "jobs"],
                    town: ["market", "inn", "recruit", "jobs", "drill", "mend"],
                    city: ["market", "inn", "recruit", "jobs", "drill", "mend",
                           "smith", "stable", "yamen"] };
const BUILDING_NAME = { market: "市集", inn: "客栈", recruit: "招募", jobs: "镖单",
                        drill: "校场", mend: "修缮", smith: "铁匠铺", stable: "马行",
                        yamen: "衙门" };

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
const world = { day: 1, provisions: 12, party: null, infamy: 0,
                members: [], progress: {},
                parties: [], spotted: new Set(), destroyed: new Set(),
                gold: GOLD_START, gear: {}, contract: null,
                packs: 0, drillDay: 0, fallen: new Set() };
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
      infamy: world.infamy, members: world.members, progress: world.progress, gold2: true,
      gold: world.gold, gear: world.gear, contract: world.contract,
      packs: world.packs, drillDay: world.drillDay, fallen: [...world.fallen],
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
  if (s.progress && typeof s.progress === "object") world.progress = s.progress;
  for (const hid of CORE_ROSTER)                  // backfill traits onto pre-trait saves
    if (world.progress[hid] && !(world.progress[hid].traits || []).length)
      world.progress[hid].traits = (HERO_BASE[hid].traits || []).slice();
  for (const m of world.members)                  // and onto restored hires
    if (world.progress[m.rid] && !(world.progress[m.rid].traits || []).length)
      world.progress[m.rid].traits = (m.traits || []).slice();
  world.party = s.party.slice();
  world.gold = s.gold;
  world.contract = s.contract || null;
  world.packs = s.packs || 0;
  world.drillDay = s.drillDay || 0;
  world.fallen = new Set(s.fallen || []);
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
  for (const m of world.members)             // hires are equippable — keep their gear too
    if (!seeded[m.rid]) seeded[m.rid] = {};
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
  for (const wu of res.wear || []) {                    // the dents ride home (survivors only)
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
  // hardcore (BB): the slain are struck from the roster — for good
  for (const id of res.fallen || []) {
    const isCore = CORE_ROSTER.includes(id);
    const mi = world.members.findIndex((m) => m.rid === id);
    if (!isCore && mi < 0) continue;                    // unknown id — ignore
    log(`第${world.day}日 · 阵亡——${nameOf(id)}永远地倒下了。`, "r");
    if (isCore) world.fallen.add(id);
    if (mi >= 0) world.members.splice(mi, 1);
    delete world.progress[id];
    delete world.gear[id];
  }
  const win = res.winner === "player";
  if (win) {                                            // combat-fed leveling
    const rng = makeRng(`xp:${spec.id}:${world.day}:${world.gold}`);
    for (const cid of Object.keys(world.progress)) {
      const before = world.progress[cid].level;
      awardXp(world.progress[cid], BATTLE_XP, rng);
      if (world.progress[cid].level > before)
        log(`第${world.day}日 · ${cid} 升至 ${world.progress[cid].level} 级！`, "b");
    }
  }
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
      if (world.contract && world.contract.kind === "huntband"
          && world.contract.target === pend.target) {     // 剿匪镖单功成
        world.gold += world.contract.pay;
        log(`第${world.day}日 · 剿匪功成——${world.contract.name}，赏银${world.contract.pay}两入账`, "b");
        world.contract = null;
      }
    } else {
      const b = retreatToFriendly();
      log(`第${world.day}日 · 战败溃走，退至${b ? b.name : "荒野"}`, "r");
      failContract();   // a lost battle voids the bond (sim fail_contract)
    }
  }
  if (companyWiped()) {                                  // 全军覆没 — nobody left to march
    world.contract = null;
    log(`第${world.day}日 · 全军覆没——镖局烟消云散。按「重开」另起炉灶。`, "r");
  }
}
let boardEl, logEl, overlayEl, hoverEl;
let placeLayer, partyLayer, fxLayer, contractLayer;
let hoverPathEl = null;

const tileCost = (k) => COST[tiles.get(k).terrain];

/* ---------------- camera (BB/Bannerlord style: pan, edge-scroll, zoom) ----------------
   The viewBox is a window over the full board; scale = css px per board unit. */
let BOARD_W = 0, BOARD_H = 0;
const ZOOM_MIN = 0.3, ZOOM_MAX = 2.2;        // × base scale (base: 1 unit = 1 px) — 0.3 fits the big enlarged board whole
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
    const over = document.elementFromPoint(edgeXY[0], edgeXY[1]);  // not while reading a panel
    if (over && over.closest && over.closest("#citypanel,#musterpanel,#inspector")) return;
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
  world.packs = 0;           // 驮马 bought at the 马行 (raise 粮草 capacity)
  world.drillDay = 0;        // last day the company drilled at a 校场
  world.fallen = new Set();  // founders killed in battle never return (hardcore)
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
  for (const hid of CORE_ROSTER) {
    const h = HERO_BASE[hid];
    world.progress[hid] = newProgress(h.stats, h.talents, HERO_LEVEL, h.traits);
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
               pay: ESCORT_BASE + days * ESCORT_RATE, days });
  }
  for (const lair of settlements.values()) {
    if (lair.kind === "stronghold" && world.spotted.has(lair.id)
        && !world.destroyed.has(lair.id)) {
      const lk = key(lair.at[0], lair.at[1]);
      const days = costs.has(lk) ? Math.max(1, Math.ceil(costs.get(lk) / MOVE_PER_DAY)) : 1;
      out.push({ kind: "bounty", target: lair.id, name: `攻破${lair.name}`,
                 pay: BOUNTY_BASE + days * BOUNTY_RATE });
    }
  }
  // 剿匪: a bounty on every known roaming band — defeat it in the field (not its 寨)
  for (const p of world.parties) {
    if (p.alive && HUNTABLE.has(p.kind) && world.spotted.has(p.pid)) {
      const anchor = p.home || p.pos;
      const ak = key(anchor[0], anchor[1]);
      const days = costs.has(ak) ? Math.max(1, Math.ceil(costs.get(ak) / MOVE_PER_DAY)) : 2;
      out.push({ kind: "huntband", target: p.pid, name: `剿灭${p.name}`,
                 pay: HUNT_BASE + days * HUNT_RATE });
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
  if (!s || s.kind !== "city" || !GEAR_SLOTS.includes(slot)
      || !companyGearIds().includes(uid) || !world.gear[uid])
    return null;                               // only the fighting company, not phantoms
  const cur = world.gear[uid][slot] || "fan";
  const i = QUALITY_LADDER.indexOf(cur) + 1;
  if (i >= QUALITY_LADDER.length) return null;
  const nxt = QUALITY_LADDER[i];
  const price = SMITH_PRICE[nxt];
  if (world.gold < price) return null;
  world.gold -= price;
  world.gear[uid][slot] = nxt;
  log(`第${world.day}日 · 铁匠铺升造：${nameOf(uid)}之${SLOT_LABEL[slot]}升至` +
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
  if (companyWiped()) { log(`镖局已散——请按「重开」。`, "r"); return; }
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
    log(`第${world.day}日 · 破寨功成——${world.contract.name}，赏银${world.contract.pay}两入账`, "b");
    world.contract = null;
  }
  // razing the den disbands its band — a 剿匪 bond on that band can't be filled
  if (world.contract && world.contract.kind === "huntband") {
    const tb = world.parties.find((p) => p.pid === world.contract.target);
    if (tb && !tb.alive) failContract();
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
    const lv = battleLevels();
    const inject = `<script>window.__SJ_SCEN=${JSON.stringify(pend.scenario)};window.__SJ_CAMPAIGN=1;` +
      `window.__SJ_GEAR=${JSON.stringify(world.gear)};window.__SJ_LEVELS=${JSON.stringify(lv)};` +
      `window.__SJ_ROSTER=${JSON.stringify(battleRoster())};window.__SJ_ENEMY_SEED=${battleSeed(pend.scenario)};<\/script>`;
    f.srcdoc = EMBEDDED_BATTLE.replace("<script>", inject + "<script>");
    wrap.appendChild(f);
    document.body.appendChild(wrap);
  } else {
    try {
      localStorage.setItem("sj_gear", JSON.stringify(world.gear));
      localStorage.setItem("sj_levels", JSON.stringify(battleLevels()));
      localStorage.setItem("sj_roster", JSON.stringify(battleRoster()));
      localStorage.setItem("sj_seed", String(battleSeed(pend.scenario)));
    } catch (e) {}
    location.href = "index.html?scenario=" + pend.scenario + "&campaign=1";
  }
}
function battleLevels() {
  const out = {};
  for (const cid of Object.keys(world.progress)) out[cid] = world.progress[cid].stats;
  return out;
}
/* the company that rides to war: the 3–4 core founders, then every hire — the
   battle deploys THIS roster (not a scenario's fixed line), BB-style */
function battleRoster() {
  const out = livingCore().map((id) => ({ id }));   // the fallen never ride again
  for (const m of world.members)
    out.push({ id: m.rid, bg: m.bg, name: (m.nick ? m.nick + "·" : "") + m.name });
  return out;
}
/* a per-encounter seed so a given fight's randomized warband is stable on reload */
function battleSeed(scen) {
  return ((world.day * 2654435761) ^ (world.party[0] * 40503) ^
          (world.party[1] * 65537) ^ strSeed(scen || "")) >>> 0;
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
  if (companyWiped()) { log(`镖局已散——请按「重开」。`, "r"); return; }
  busy = true;
  drawerOpen = false;
  clearHexHover();
  hideInspector();
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
  // event delegation: one set of listeners for the whole grid — the enlarged
  // board has thousands of hexes, far too many for per-tile handlers
  tileLayer.addEventListener("click", (e) => {
    const k = e.target.dataset && e.target.dataset.k;
    if (k) onHexClick(k);
  });
  tileLayer.addEventListener("mouseover", (e) => {
    const k = e.target.dataset && e.target.dataset.k;
    if (k) onHexHover(k);
  });
  tileLayer.addEventListener("mouseout", (e) => {
    const k = e.target.dataset && e.target.dataset.k;
    if (k) clearHexHover();
  });
  for (const t of tiles.values()) {
    const { x, y } = hexToPix(t.q, t.r);
    const p = svgEl("polygon", { points: hexPoints(x, y), class: "hex",
                                 fill: TERRAIN_FILL[t.terrain] });
    const k = key(t.q, t.r);
    p.dataset.k = k;
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
  contractLayer = svgEl("g", { "pointer-events": "none" });
  partyLayer = svgEl("g", { "pointer-events": "none" });
  boardEl.appendChild(placeLayer);
  boardEl.appendChild(fxLayer);
  boardEl.appendChild(contractLayer);
  boardEl.appendChild(partyLayer);
}

/* settlements — hidden lairs invisible until spotted, razed lairs are ruins 墟 */
function renderPlaces() {
  placeLayer.innerHTML = "";
  const ms = HEX / 22;                              // markers scale with the hex
  for (const s of settlements.values()) {
    if (s.hidden && !world.spotted.has(s.id)) continue;
    const { x, y } = hexToPix(s.at[0], s.at[1]);
    const razed = world.destroyed.has(s.id);
    const c = svgEl("circle", { cx: x, cy: y, r: 8 * ms,
      fill: razed ? "#8a8170" : KIND_FILL[s.kind], stroke: "#1d1a15", "stroke-width": 1 });
    c.setAttribute("pointer-events", "auto");      // click a place to read it
    c.style.cursor = "pointer";
    c.addEventListener("click", (e) => { if (dragMoved <= 5) inspectSettlement(s.id, e); });
    placeLayer.appendChild(c);
    const g = svgEl("text", { x, y: y + 3.5 * ms, class: "glyph",
      "font-size": s.kind === "city" || s.kind === "town" ? 11 : 9.5 });
    g.textContent = razed ? "墟" : KIND_GLYPH[s.kind];
    placeLayer.appendChild(g);
    const lb = svgEl("text", { x, y: y + 17.5 * ms, class: "plabel" });
    lb.textContent = s.name;
    placeLayer.appendChild(lb);
  }
}

/* spotted parties at live positions, then the bureau's column on top */
const WAYLAY_SCEN = { caravan: "jiebiao", patrol: "duijue" };
const WAYLAY_LOOT = { caravan: 150, patrol: 60 };

function renderParties() {
  partyLayer.innerHTML = "";
  const ms = HEX / 22;                              // markers scale with the hex
  for (const p of world.parties) {
    if (!p.alive || !world.spotted.has(p.pid)) continue;
    const { x, y } = hexToPix(p.pos[0], p.pos[1]);
    const preyable = !busy && p.kind in WAYLAY_SCEN
      && hexDist(p.pos, world.party) <= 1;
    const c = svgEl("circle", { cx: x, cy: y, r: 6.5 * ms,
      fill: PARTY_FILL[p.kind], stroke: preyable ? "#e8c14f" : "#1d1a15",
      "stroke-width": preyable ? 2 : 1 });
    c.setAttribute("pointer-events", "auto");        // click any party to read it
    c.style.cursor = "pointer";
    c.addEventListener("click", (e) => { if (dragMoved <= 5) inspectParty(p.pid, e); });
    partyLayer.appendChild(c);
    const g = svgEl("text", { x, y: y + 2.8 * ms, class: "glyph", "font-size": 8 });
    g.textContent = PARTY_GLYPH[p.kind];
    partyLayer.appendChild(g);
  }
  const { x, y } = hexToPix(world.party[0], world.party[1]);
  const pc = svgEl("circle", { cx: x, cy: y, r: 8.5 * ms,
    fill: "#1b4965", stroke: "#b8860b", "stroke-width": 2 });
  pc.setAttribute("pointer-events", "auto");         // click the 镖 dot to read the column
  pc.style.cursor = "pointer";
  pc.addEventListener("click", (e) => { if (dragMoved <= 5) inspectPlayer(e); });
  partyLayer.appendChild(pc);
  const g = svgEl("text", { x, y: y + 3.3 * ms, class: "glyph", "font-size": 9.5 });
  g.textContent = "镖";
  partyLayer.appendChild(g);
  renderContract();                          // the active 镖单, captioned on the map
}

/* the accepted 镖单 drawn onto the map: a caption banner + a marked target & a
   dashed line from the column to it (escort 城镇 / 破寨 山寨 / 剿匪 the band) */
function renderContract() {
  if (contractLayer) contractLayer.innerHTML = "";
  const cap = document.getElementById("contractcap");
  if (!world.contract) { if (cap) cap.style.display = "none"; return; }
  const c = world.contract;
  let pos = null, where = "";
  if (c.kind === "escort") {
    const s = settlements.get(c.to); if (s) { pos = s.at; where = "→ " + s.name; }
  } else if (c.kind === "bounty") {
    const s = settlements.get(c.target);
    if (s && (!s.hidden || world.spotted.has(s.id))) { pos = s.at; where = "→ " + s.name; }
  } else if (c.kind === "huntband") {
    const p = world.parties.find((x) => x.pid === c.target && x.alive);
    if (p && world.spotted.has(p.pid)) { pos = p.pos; where = "→ " + p.name; }
  }
  if (cap) {                                 // always-visible caption (survives panning)
    let hint = where;
    if (pos && dij) {
      const k = key(pos[0], pos[1]);
      if (dij.costs.has(k)) hint += ` · 约${daysAlong(pathTo(dij.prev, k))}日`;
    }
    cap.innerHTML = `<b>镖单</b> ${c.name} <span style="opacity:.85">${hint}` +
      `（酬${c.pay != null ? c.pay : "—"}两）</span>`;
    cap.style.display = "block";
  }
  if (!pos || !contractLayer) return;        // target not yet locatable on the map
  const t = hexToPix(pos[0], pos[1]), me = hexToPix(world.party[0], world.party[1]);
  contractLayer.appendChild(svgEl("line", { x1: me.x, y1: me.y, x2: t.x, y2: t.y,
    stroke: "rgba(184,134,11,.55)", "stroke-width": 2, "stroke-dasharray": "8 6",
    "stroke-linecap": "round" }));
  const ms = HEX / 22, r = 13 * ms;
  contractLayer.appendChild(svgEl("circle", { cx: t.x, cy: t.y, r, fill: "none",
    stroke: "#b8860b", "stroke-width": 2.5, opacity: 0.9 }));
  const flag = svgEl("text", { x: t.x, y: t.y - r - 3, class: "glyph",
    "font-size": 13 * ms, fill: "#b8860b" });
  flag.textContent = "✦"; contractLayer.appendChild(flag);
  const lb = svgEl("text", { x: t.x, y: t.y + r + 12 * ms, class: "plabel",
    "font-size": 11 * ms, fill: "#7a5c12" });
  lb.textContent = "镖单·" + c.name; contractLayer.appendChild(lb);
}

/* ---------------- the unit inspector (click a 城/寨/商旅/巡骑/镖队 to read it) ---------------- */
let inspectEl = null;
const KIND_READ = { city: "州城", town: "军镇", village: "村镇",
                    stronghold: "山寨", occupied: "辽占" };
const PARTY_READ = { bandit: "绿林匪伙", caravan: "行商车队", patrol: "官军巡骑",
                     raider: "契丹游骑", hunter: "缉捕官军" };

function hideInspector() {
  if (!inspectEl) inspectEl = document.getElementById("inspector");
  if (inspectEl) { inspectEl.style.display = "none"; inspectEl.innerHTML = ""; }
}
window.hideInspector = hideInspector;

/* float the card near the click, clamped inside the board pane */
function showInspectorAt(html, ev) {
  if (!inspectEl) inspectEl = document.getElementById("inspector");
  if (!inspectEl) return;
  inspectEl.innerHTML = html;
  inspectEl.style.display = "block";
  const wrap = document.getElementById("boardwrap");
  const wr = wrap.getBoundingClientRect();
  const ir = inspectEl.getBoundingClientRect();
  let x = (ev ? ev.clientX - wr.left : 24) + 14;
  let y = (ev ? ev.clientY - wr.top : 24) + 10;
  x = Math.max(6, Math.min(Math.max(6, wr.width - ir.width - 6), x));
  y = Math.max(6, Math.min(Math.max(6, wr.height - ir.height - 6), y));
  inspectEl.style.left = x.toFixed(0) + "px";
  inspectEl.style.top = y.toFixed(0) + "px";
}

function inspHead(name, tag) {
  return `<div class="ihead"><span class="iname">${name}</span>` +
    (tag ? `<span class="itag">${tag}</span>` : "") +
    `<span class="iclose" onclick="hideInspector()" title="关闭">×</span></div>`;
}

function inspectSettlement(id, ev) {
  const s = settlements.get(id);
  if (!s) return;
  const razed = world.destroyed.has(id);
  const here = samePos(s.at, world.party);
  const k = key(s.at[0], s.at[1]);
  const reachable = dij && dij.costs.has(k) && !here;
  let rows = `<div class="irow">${razed ? "已荡平的废墟（墟）" : (KIND_READ[s.kind] || s.kind)}` +
    (s.fanzhen ? ` · <b>${s.fanzhen}</b>` : "") + `</div>`;
  if (s.kind === "stronghold" && !razed)
    rows += `<div class="irow">绿林贼巢——破之，余匪作鸟兽散</div>`;
  if (s.kind === "occupied" && !razed)
    rows += `<div class="irow">辽人占据，市集不纳外客</div>`;
  if (here) rows += `<div class="irow">镖队正驻此地</div>`;
  else if (reachable) {
    const cost = dij.costs.get(k), days = daysAlong(pathTo(dij.prev, k));
    rows += `<div class="irow">路程 <b>${cost}</b> 移动力 · 约 <b>${days}</b> 日` +
      (days > world.provisions ? `<br><b style="color:#e0a07a">⚠ 粮草不济</b>` : "") + `</div>`;
  } else rows += `<div class="irow">大河层峦相隔，暂不可达</div>`;
  if (FRIENDLY_KINDS.has(s.kind) && !razed) {
    let price = PROVISION_PRICE[s.kind];
    if (world.infamy >= INFAMY_PRICED) price += (price + 1) >> 1;
    rows += `<div class="irow">市集粮价 <b>${price}</b> 两/份` +
      (s.kind === "city" ? " · 城内有铁匠铺" : "") + `</div>`;
  }
  let acts = "";
  if (reachable && !busy) acts += `<button onclick="uiGoTo('${k}')">前往此地</button>`;
  if (here && tradePost() && !busy) acts += `<button onclick="hideInspector();uiTown()">入城</button>`;
  if (here && s.kind === "stronghold" && !razed && world.spotted.has(id) && !busy)
    acts += `<button class="prey" onclick="hideInspector();doAssault()">攻寨</button>`;
  if (acts) rows += `<div class="iacts">${acts}</div>`;
  showInspectorAt(inspHead(razed ? s.name + "·墟" : s.name, KIND_GLYPH[s.kind]) + rows, ev);
}

function inspectParty(pid, ev) {
  const p = world.parties.find((x) => x.pid === pid);
  if (!p || !p.alive) return;
  const hostile = HOSTILE.has(p.kind);
  const dist = hexDist(p.pos, world.party);
  const preyable = !busy && p.kind in WAYLAY_SCEN && dist <= 1;
  let rows = `<div class="irow">${PARTY_READ[p.kind] || p.kind} · ` +
    (hostile ? '<b style="color:#e0a07a">敌</b>' : '<b style="color:#9ec9a0">非敌</b>') + `</div>`;
  rows += `<div class="irow">脚力 <b>${p.speed}</b> 格/日 · 距镖队 <b>${dist}</b> 格</div>`;
  if (p.kind === "bandit") {
    const home = p.home ? settlementAt(p.home) : null;
    rows += `<div class="irow">巢穴 ${home ? home.name : "山中"}，游弋 ${p.prowl} 格</div>`;
  } else if (p.route && p.route.length) {
    const names = [...new Set(p.route.map((rid) => {
      const s = settlements.get(rid); return s ? s.name : rid; }))];
    rows += `<div class="irow">巡行 ${names.join("→")}</div>`;
  }
  if (hostile && dist <= 1)
    rows += `<div class="irow" style="color:#e0a07a">已贴身——扎营或出发即开战</div>`;
  else if (preyable)
    rows += `<div class="irow">可伏击劫道（官府闻之必怒，恶名+）</div>`;
  if (preyable)
    rows += `<div class="iacts"><button class="prey" onclick="uiWaylay('${pid}')">劫道</button></div>`;
  showInspectorAt(inspHead(p.name, PARTY_GLYPH[p.kind]) + rows, ev);
}

function inspectPlayer(ev) {
  const here = settlementAt(world.party);
  let rows = `<div class="irow">第 <b>${world.day}</b> 日 · 现驻 <b>${locName(world.party)}</b>` +
    (here && here.fanzhen && (!here.hidden || world.spotted.has(here.id)) ? `（${here.fanzhen}）` : "") + `</div>`;
  rows += `<div class="irow">粮草 <b>${world.provisions}/${capacity()}</b> · 银两 <b>${world.gold}</b>` +
    (world.infamy ? ` · 恶名 <b style="color:#e0a07a">${world.infamy}</b>` : "") + `</div>`;
  rows += `<div class="irow">在册 <b>${headcount()}</b> 人 · 日耗粮 ${dailyFood()} · 日饷 ${dailyWage()} 两</div>`;
  const lv = [];
  for (const hid of livingCore()) {
    const pr = world.progress[hid];
    if (pr) lv.push(`${(HEROES.find((h) => h.id === hid) || {}).name || hid} Lv${pr.level}`);
  }
  if (lv.length) rows += `<div class="irow" style="font-size:11.5px;color:#c9bda0">${lv.join(" · ")}</div>`;
  if (world.members.length)
    rows += `<div class="irow" style="font-size:11.5px;color:#c9bda0">部曲 ${world.members.length} 人随征</div>`;
  if (world.contract) rows += `<div class="irow">镖单：<b>${world.contract.name}</b></div>`;
  rows += `<div class="iacts"><button onclick="hideInspector();uiMuster()">校阅花名册</button></div>`;
  showInspectorAt(inspHead("镖队", "镖") + rows, ev);
}

window.uiGoTo = (k) => { hideInspector(); travelTo(k); };
window.uiWaylay = (pid) => {
  const p = world.parties.find((x) => x.pid === pid);
  hideInspector();
  if (p) offerWaylay(p);
};

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
  tb.style.display = post && !busy && !drawerOpen && !musterOpen ? "inline-block" : "none";
  tb.textContent = drawerOpen ? "出城 ▸" : "入城 ◂";
  if (!post) drawerOpen = false;
  renderCity();
  renderMuster();
  const mb = document.getElementById("musterbtn");
  if (mb) mb.disabled = busy;
  const s = settlementAt(world.party);
  const lair = s && s.kind === "stronghold" && !world.destroyed.has(s.id) && world.spotted.has(s.id);
  document.getElementById("assault").style.display = lair && !busy ? "" : "none";
  document.getElementById("campbtn").disabled = busy;
}

/* the town drawer: a folder tree on the right — 城 ▸ 市集 / 镖单 / 铁匠铺 ▸ 各人 */
let drawerOpen = false;

/* ---- the company armoury: the smith & 修缮 tend the people who actually fight ----
   (founders + hires), not the phantom assault-roster heroes who never deploy */
const BG_SIDEARM = new Set(["liehu"]);       // only the 猎户 hire carries a 副 (匕首)
function companyGearIds() { return livingCore().concat(world.members.map((m) => m.rid)); }
function hasSidearm(id) {
  const h = HEROES.find((x) => x.id === id);
  if (h) return !!h.wpn2;
  const m = world.members.find((x) => x.rid === id);
  return m ? BG_SIDEARM.has(m.bg) : false;
}
function gearSlotsForId(id) {
  return GEAR_SLOTS.filter((slot) => slot !== "wpn2_q" || hasSidearm(id));
}
/* dent points on a member's gear (hires take no weapon-dura wear — no base dura) */
function gearWearPts(id) {
  const g = world.gear[id] || {}, h = HEROES.find((x) => x.id === id);
  let pts = (g.armor_dmg || 0) + (g.helm_dmg || 0);
  if (h && g.wpn_dura != null) pts += (h.wpnDura || 0) - g.wpn_dura;
  if (h && g.wpn2_dura != null) pts += (h.wpn2Dura || 0) - g.wpn2_dura;
  return Math.max(0, pts);
}

/* the named hidden 寨 nearest the column, still unspotted — what the 客栈 sells */
function nearestHiddenLair() {
  let best = null, bd = Infinity;
  for (const s of settlements.values()) {
    if (s.kind === "stronghold" && s.hidden && !world.spotted.has(s.id)
        && !world.destroyed.has(s.id)) {
      const d = hexDist(s.at, world.party);
      if (d < bd) { bd = d; best = s; }
    }
  }
  return best;
}
/* every soul here who can still grow — founders AND hires alike (校场 trains all) */
function drillTrainees() {
  return livingCore().concat(world.members.map((m) => m.rid))
    .filter((id) => world.progress[id] && world.progress[id].level < MAX_LEVEL);
}
const nameOf = (id) => (HEROES.find((h) => h.id === id) || {}).name ||
  (world.members.find((m) => m.rid === id) || {}).name || id;

/* the settlement drawer: BB-style — a building roster that grows village→town→city,
   each 坊 a folded function. 校阅 has moved OUT (a roving review, see renderMuster) */
function renderCity() {
  const el = document.getElementById("citypanel");
  const s = tradePost();
  if (!s || busy || !drawerOpen) { el.style.display = "none"; el.innerHTML = ""; return; }
  const open = new Set([...el.querySelectorAll("details[open]")].map((d) => d.dataset.k));
  if (!el.innerHTML) { open.add("market"); open.add("jobs"); }   // first opening
  const o = (k, dflt) => (el.innerHTML ? open.has(k) : dflt) ? " open" : "";
  const blds = BUILDINGS[s.kind] || BUILDINGS.village;
  const has = (k) => blds.includes(k);
  let html = `<button onclick="uiTown()" style="float:right">出城 ▸</button>` +
             `<b>${s.name}</b>${s.fanzhen ? `（${s.fanzhen}）` : ""}` +
             ` <span style="color:#c9bda0">银两 ${world.gold}</span>` +
             `<div style="color:#9a907a;font-size:11px;margin:1px 0 4px">` +
             `${KIND_READ[s.kind] || s.kind} · ${blds.length}坊</div>`;

  if (has("market")) {                       // 市集 — provisions for silver
    let price = PROVISION_PRICE[s.kind];
    if (world.infamy >= INFAMY_PRICED) price += (price + 1) >> 1;
    const need = capacity() - world.provisions;
    const canBuy = Math.max(0, Math.min(need, Math.floor(world.gold / price)));
    html += `<details data-k="market"${o("market", true)}><summary>市集</summary>` +
            `<div class="leaf">粮草 ${world.provisions}/${capacity()} · ${price}两/份<br>` +
            `<button onclick="uiBuy()" ${canBuy ? "" : "disabled"}>` +
            (canBuy ? `买粮${canBuy}日 · ${canBuy * price}两`
                    : need ? "银两不足" : "粮草已满") + `</button></div></details>`;
  }

  if (has("inn")) {                          // 客栈 — a rumor pins the nearest hidden 寨
    const lair = nearestHiddenLair();
    html += `<details data-k="inn"${o("inn", false)}><summary>客栈</summary><div class="leaf">` +
            (lair
              ? `酒客行旅，似知贼巢去向。<br>` +
                `<button onclick="uiIntel()" ${world.gold < INTEL_PRICE ? "disabled" : ""}>` +
                `打探消息 ${INTEL_PRICE}两</button>`
              : `境内贼巢已探明，再无风声可买。`) + `</div></details>`;
  }

  if (has("jobs")) {                         // 镖单 — escorts & bounties
    html += `<details data-k="jobs"${o("jobs", true)}><summary>镖单</summary>`;
    const board = cityJobs();
    if (!board.length) html += `<div class="leaf">暂无镖单</div>`;
    board.forEach((jb, i) => {
      html += `<div class="job leaf"><span>${jb.name} · ${jb.pay}两</span>` +
              `<button onclick="uiTake(${i})" ${world.contract ? "disabled" : ""}>接单</button></div>`;
    });
    if (world.contract) html += `<div class="leaf" style="color:#c9bda0">在身：${world.contract.name}</div>`;
    html += `</details>`;
  }

  if (has("recruit")) {                      // 招募 — the candidates this place musters
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
    if (!rrows) rrows = `<div class="leaf">此地暂无可募之人。</div>`;   // hired ones leave the board
    html += `<details data-k="recruit"${o("recruit", false)}><summary>招募 · 可募${recruitsHere().length}人</summary>${rrows}</details>`;
  }

  if (has("drill")) {                        // 校场 — paid sparring lifts the WHOLE company
    const crew = drillTrainees(), drilled = world.drillDay === world.day;
    let body;
    if (!crew.length) body = `全队已至顶级，无需操练。`;
    else if (drilled) body = `今日已操练，明日再来。`;
    else body = `演武操练全队 ${crew.length} 人（银多则练得勤）：<br>` +
      DRILL_TIERS.map((t) => { const c = drillCost(t, crew.length);
        return `<button onclick="uiDrill('${t.key}')" ${world.gold < c ? "disabled" : ""}>` +
               `${t.name}·各+${t.xp}·${c}两</button>`; }).join(" ");
    html += `<details data-k="drill"${o("drill", false)}><summary>校场</summary><div class="leaf">${body}</div></details>`;
  }

  if (has("mend")) {                         // 修缮 — mend the company's dented gear
    let rows = "";
    for (const id of companyGearIds()) {
      const pts = gearWearPts(id);
      if (pts <= 0) continue;
      const bill = Math.ceil(pts / 3);
      rows += `<div class="job"><span>${nameOf(id)} 甲械损${pts}点</span>` +
              `<button onclick="uiMend('${id}')" ${world.gold < bill ? "disabled" : ""}>修缮 ${bill}两</button></div>`;
    }
    html += `<details data-k="mend" open><summary>修缮</summary>` +
            (rows || `<div class="leaf">甲械俱全，无需修缮。</div>`) + `</details>`;
  }

  if (has("smith")) {                        // 铁匠铺 — raise the company's gear up the 品阶 ladder
    html += `<details data-k="smith"${o("smith", false)}><summary>铁匠铺</summary>`;
    for (const id of companyGearIds()) {
      const g = world.gear[id] || {};
      html += `<details data-k="smith-${id}"${o("smith-" + id, false)}>` +
              `<summary>${nameOf(id)}</summary><div class="leaf">`;
      for (const slot of gearSlotsForId(id)) {
        const cur = g[slot] || "fan";
        const i = QUALITY_LADDER.indexOf(cur) + 1;
        if (i >= QUALITY_LADDER.length) {
          html += `<button disabled>${SLOT_LABEL[slot]}·神品</button> `;
          continue;
        }
        const nxt = QUALITY_LADDER[i], cost = SMITH_PRICE[nxt];
        html += `<button onclick="uiSmith('${id}','${slot}')" ` +
                `${world.gold < cost ? "disabled" : ""}>` +
                `${SLOT_LABEL[slot]} ${QUALITY_LABEL[cur]}→${QUALITY_LABEL[nxt]} ${cost}两</button> `;
      }
      html += `</div></details>`;
    }
    html += `</details>`;
  }

  if (has("stable")) {                       // 马行 — 驮马 raise the 粮草 carry (city)
    const n = world.packs || 0, bill = packBill(n);
    html += `<details data-k="stable"${o("stable", false)}><summary>马行</summary><div class="leaf">` +
            `驮马 ${n}/${PACK_MAX} · 每匹增粮草上限 ${PACK_CARRY}<br>` +
            (n >= PACK_MAX ? `驮队已满，足支远途。`
              : `<button onclick="uiPack()" ${world.gold < bill ? "disabled" : ""}>购置驮马 ${bill}两</button>`) +
            `</div></details>`;
  }

  if (has("yamen") && world.infamy > 0) {    // 衙门 — wash off 恶名 for silver (city)
    const cost = world.infamy * ATONE_RATE;
    html += `<details data-k="yamen" open><summary>衙门</summary>` +
            `<div class="leaf">恶名 ${world.infamy} · 海捕${world.infamy >= INFAMY_HUNTED ? "已发" : "未发"}<br>` +
            `<button onclick="uiAtone()" ${world.gold < cost ? "disabled" : ""}>` +
            `纳赎罪银 ${cost}两</button></div></details>`;
  }
  el.innerHTML = html;
  el.style.display = "block";
}

/* 校阅 · the roving review — ONE roster of characters (founders and hires alike,
   every one with traits + star talents). Click any name for the full sheet. */
let musterOpen = false;

/* the whole company as uniform character entries — no 镖师/部曲 divide */
function rosterList() {
  const out = [];
  for (const id of livingCore()) {
    const h = HEROES.find((x) => x.id === id) || {};
    out.push({ id, name: h.name || id, role: h.wpnLabel || "镖师", member: null });
  }
  for (const m of world.members)
    out.push({ id: m.rid, name: (m.nick ? m.nick + "·" : "") + m.name,
               role: m.bg_name || "部曲", member: m });
  return out;
}
/* traits live on the progress (founders + hires both); fall back to the hire record */
function traitsOf(id, member) {
  const p = world.progress[id];
  const t = (p && p.traits && p.traits.length) ? p.traits : (member ? member.traits : null);
  return (t && t.length) ? t : [];
}

let gearMove = null;                          // {id, slot} picked up for a 调拨 transfer

/* the gear chips on a muster row — click one, then another's same part, to 调拨 */
function gearChips(id) {
  const g = world.gear[id] || {};
  return gearSlotsForId(id).map((slot) => {
    const q = g[slot] || "fan";
    const sel = gearMove && gearMove.id === id && gearMove.slot === slot;
    return `<span class="gchip${sel ? " gsel" : ""}" onclick="uiGearChip('${id}','${slot}',event)" ` +
           `title="${SLOT_LABEL[slot]}·${QUALITY_LABEL[q]}（点选调拨）">` +
           `${SLOT_LABEL[slot]}${QUALITY_LABEL[q][0]}</span>`;
  }).join("");
}

function renderMuster() {
  const el = document.getElementById("musterpanel");
  if (!el) return;
  if (!musterOpen || busy) { el.style.display = "none"; el.innerHTML = ""; return; }
  let html = `<button onclick="uiMuster()" style="float:right">收起 ▸</button>` +
             `<b>校阅 · 风尘镖谱</b>` +
             `<div style="color:#9a907a;font-size:11px;margin:1px 0 5px">` +
             `在册 ${headcount()}人 · 日饷 ${dailyWage()}两 · 点名看详情，点装备格可调拨</div>`;
  if (gearMove)
    html += `<div style="color:#e8c14f;font-size:11px;margin:0 0 4px">调拨中：` +
            `${nameOf(gearMove.id)}的「${SLOT_LABEL[gearMove.slot]}」——点另一人同部位即调拨，再点此格取消</div>`;
  for (const c of rosterList()) {
    const p = world.progress[c.id];
    if (!p) continue;
    const stat = R_ATTRS.map((a) => `${R_ANAME[a]}${p.stats[a]}/${capOf(p, a)}` +
      (starsOf(p, a) ? "★".repeat(starsOf(p, a)) : "")).join(" ");
    const tn = p.level >= MAX_LEVEL ? "满级" : (LEVEL_XP[p.level + 1] - p.xp) + "经验";
    const tr = traitsOf(c.id, c.member).map((t) => R_TRAIT[t]).join("、") || "无异";
    html += `<div class="mrow mclick" onclick="uiCharDetail('${c.id}',event)" title="点选看详情">` +
            `<b>${c.name}</b> <span class="msub">${c.role} · Lv${p.level} · ${tn}</span>` +
            `<div class="mstat">${stat}</div>` +
            `<div class="mtrait">特性：${tr}</div>` +
            `<div class="mgear">装备 ${gearChips(c.id)}</div></div>`;
  }
  el.innerHTML = html;
  el.style.display = "block";
}

/* 调拨: pick up a member's gear slot, then click another's same part to swap them.
   It is the company's own kit — rearrange it freely, anywhere (no forge needed). */
window.uiGearChip = (id, slot, ev) => {
  if (ev) ev.stopPropagation();
  if (!world.gear[id]) world.gear[id] = {};
  if (!gearMove || gearMove.slot !== slot) { gearMove = { id, slot }; refresh(); return; }
  if (gearMove.id === id) { gearMove = null; refresh(); return; }     // clicked self — cancel
  const a = gearMove.id, b = id;
  if (!world.gear[a]) world.gear[a] = {};
  const qa = world.gear[a][slot], qb = world.gear[b][slot];
  if (qb) world.gear[a][slot] = qb; else delete world.gear[a][slot];
  if (qa) world.gear[b][slot] = qa; else delete world.gear[b][slot];
  log(`第${world.day}日 · 调拨${SLOT_LABEL[slot]}：${nameOf(a)}（${QUALITY_LABEL[qa || "fan"]}）` +
      `⇄ ${nameOf(b)}（${QUALITY_LABEL[qb || "fan"]}）`, "sys");
  gearMove = null;
  refresh();
};

/* the full sheet for one character — floats over the board like a unit inspector */
window.uiCharDetail = (id, ev) => {
  const p = world.progress[id];
  if (!p) return;
  const c = rosterList().find((x) => x.id === id);
  if (!c) return;
  const m = c.member;
  const tn = p.level >= MAX_LEVEL ? "满级" : (LEVEL_XP[p.level + 1] - p.xp) + "经验";
  let rows = `<div class="irow">${m ? (m.bg_name || "部曲") : "镖局元老"} · ${c.role}</div>`;
  rows += `<div class="irow">Lv <b>${p.level}</b> · ${tn}` + (m ? ` · 饷 ${m.wage}两` : "") + `</div>`;
  for (const a of R_ATTRS) {
    const s = starsOf(p, a);
    rows += `<div class="irow">${R_ANAME[a]} <b>${p.stats[a]}</b> / ${capOf(p, a)}` +
            (s ? ` <span style="color:#e8c14f">${"★".repeat(s)}</span>（成长快）` : "") + `</div>`;
  }
  const tr = traitsOf(id, m);
  rows += `<div class="irow">特性：<b>${tr.map((t) => R_TRAIT[t]).join("、") || "无异"}</b></div>`;
  const gl = gearSlotsForId(id).map((slot) =>
    `${SLOT_LABEL[slot]}·${QUALITY_LABEL[(world.gear[id] || {})[slot] || "fan"]}`).join("　");
  rows += `<div class="irow">装备：${gl}</div>`;
  if (m && m.blurb) rows += `<div class="irow" style="color:#c9bda0">${m.blurb}</div>`;
  if (m) rows += `<div class="iacts"><button class="prey" onclick="hideInspector();uiFireById('${id}')">遣散</button></div>`;
  showInspectorAt(inspHead(c.name, "谱") + rows, ev);
};
window.uiFireById = (rid) => {
  const i = world.members.findIndex((m) => m.rid === rid);
  if (i >= 0) window.uiFire(i);
};
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
  world.progress[r.rid] = newProgress(r.stats, r.talents, 1, r.traits);
  if (!world.gear[r.rid]) world.gear[r.rid] = {};   // the hire is equippable too
  world._pool.list = world._pool.list.filter((x) => x.rid !== rid);
  log(`第${world.day}日 · ${r.nick}·${r.name}（${r.bg_name}）入伙，雇金${r.fee}两`, "b");
  refresh();
};
window.uiFire = (i) => {
  if (i >= 0 && i < world.members.length) {
    const m = world.members.splice(i, 1)[0];
    delete world.progress[m.rid];
    delete world.gear[m.rid];                  // his kit leaves with him
    world.provisions = Math.min(world.provisions, capacity());
    log(`第${world.day}日 · 遣散${m.name}`, "sys");
  }
  refresh();
};
window.uiMend = (uid) => {
  const g = world.gear[uid];
  if (!g) return;
  const bill = Math.ceil(gearWearPts(uid) / 3);
  if (bill > 0 && world.gold >= bill) {
    world.gold -= bill;
    g.armor_dmg = 0; g.helm_dmg = 0;
    delete g.wpn_dura; delete g.wpn2_dura;
    log(`第${world.day}日 · 铁铺修缮${nameOf(uid)}甲械，费银${bill}两`, "sys");
  }
  refresh();
};
/* 客栈: a rumor pins the nearest hidden 寨 AND its band — posts both 破寨 & 剿匪 镖单 */
window.uiIntel = () => {
  const lair = nearestHiddenLair();
  if (!tradePost() || busy || !lair || world.gold < INTEL_PRICE) return;
  world.gold -= INTEL_PRICE;
  world.spotted.add(lair.id);
  for (const p of world.parties)              // the band that dens there, too
    if (p.alive && p.home && samePos(p.home, lair.at)) world.spotted.add(p.pid);
  log(`第${world.day}日 · 客栈打探——${lair.name}及其匪众的去向有了着落！`, "r");
  refresh();
};
/* 校场: pay to drill the WHOLE company up — pick an intensity, once a day */
window.uiDrill = (tkey) => {
  if (!tradePost() || busy || world.drillDay === world.day) return;
  const tier = DRILL_TIERS.find((t) => t.key === tkey);
  const crew = drillTrainees();
  if (!tier || !crew.length) return;
  const cost = drillCost(tier, crew.length);
  if (world.gold < cost) return;
  world.gold -= cost;
  world.drillDay = world.day;
  const rng = makeRng(`drill:${spec.id}:${world.day}:${tkey}:${world.gold}`);
  for (const id of crew) {
    const before = world.progress[id].level;
    awardXp(world.progress[id], tier.xp, rng);
    if (world.progress[id].level > before)
      log(`第${world.day}日 · 校场操练——${nameOf(id)}升至 ${world.progress[id].level} 级！`, "b");
  }
  log(`第${world.day}日 · 校场${tier.name}全队${crew.length}人，费银${cost}两`, "sys");
  refresh();
};
/* 马行: buy a 驮马 — each one raises the 粮草 carry, the reach of a longer march */
window.uiPack = () => {
  const s = tradePost();
  const n = world.packs || 0, bill = packBill(n);
  if (!s || s.kind !== "city" || busy || n >= PACK_MAX || world.gold < bill) return;
  world.gold -= bill;
  world.packs = n + 1;
  log(`第${world.day}日 · 马行购置驮马一匹，费银${bill}两——粮草上限增至 ${capacity()}`, "b");
  refresh();
};
window.uiMuster = () => { musterOpen = !musterOpen; if (musterOpen) drawerOpen = false; refresh(); };
window.uiTown = () => { drawerOpen = !drawerOpen; if (drawerOpen) musterOpen = false; refresh(); };
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
  HEX = spec.hexSize || 22;     // bigger hexes on roomy maps — easier to read & click
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
document.getElementById("musterbtn").addEventListener("click", window.uiMuster);
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
