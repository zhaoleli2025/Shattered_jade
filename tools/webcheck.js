// Headless load+boot smoke for the browser code — catches runtime ReferenceErrors
// that `node --check` (syntax only) and the Python suite never see.
// Run from the repo root:  node tools/webcheck.js   (exit 0 = both pages boot)
const fs = require("fs"), path = require("path");
const ROOT = path.join(__dirname, "..");
const mkEl = () => ({ addEventListener(){}, appendChild(){}, removeChild(){},
  setAttribute(){}, remove(){}, insertBefore(){}, querySelectorAll: () => [],
  querySelector: () => null, style:{}, dataset:{},
  classList:{add(){},remove(){},toggle(){},contains:()=>false},
  set innerHTML(v){}, get innerHTML(){return "";},
  set textContent(v){}, get textContent(){return "";},
  set value(v){}, get value(){return "";}, set srcdoc(v){},
  getBoundingClientRect: () => ({width:960,height:640,left:0,top:0}) });
function env(search) {
  const els = {};
  global.window = { addEventListener(){}, removeEventListener(){},
    location:{search,href:"",reload(){}}, parent:{}, __SJ_SCEN:null, __SJ_CAMPAIGN:null };
  global.document = { addEventListener(){}, body: mkEl(),
    getElementById:(id)=> els[id] || (els[id]=mkEl()),
    createElementNS:()=>mkEl(), createElement:()=>mkEl(), querySelectorAll:()=>[] };
  global.localStorage = { getItem:()=>null, setItem(){}, removeItem(){} };
  global.URLSearchParams = URLSearchParams;
}
function check(name, file, search, after) {
  env(search);
  let js = fs.readFileSync(path.join(ROOT, "prototype_web", file), "utf8")
    .replace(/\nboot\(\);\s*$/, "\n");
  if (after) js += "\n" + after;
  try { eval(js); console.log(`  ${name}: OK`); return true; }
  catch (e) { console.log(`  ${name}: BROKEN — ${e.message}`); return false; }
}
console.log("webcheck — booting the browser code headlessly:");
const hebei = JSON.stringify(JSON.parse(fs.readFileSync(path.join(ROOT,"world/hebei.json"),"utf8")));
const jiebiao = JSON.stringify(JSON.parse(fs.readFileSync(path.join(ROOT,"scenarios/jiebiao.json"),"utf8")));
let ok = true;
ok &= check("world.js (map)", "world.js", "?world=hebei",
  `spec=${hebei};buildWorld();headcount();capacity();dailyWage();recruitsHere();` +
  `if(!world.progress[CORE_ROSTER[0]])throw new Error("hero progress unseeded");` +
  `awardXp(world.progress.wang,600,makeRng("t"));`);
ok &= check("game.js (battle)", "game.js", "?scenario=jiebiao",
  `scenario=${jiebiao};buildMap();units=scenario.units.map(su=>mkUnit(rosterTemplates().find(t=>t.id===su.id),su.spawn[0],su.spawn[1],su));`);
process.exit(ok ? 0 : 1);
