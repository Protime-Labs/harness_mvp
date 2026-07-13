"""Dashboard renderer — a self-contained HTML view of one or more assurance bundles.

No server, no network, no build step: the bundle JSON is embedded in the page and rendered
client-side, so you can double-click the file or serve it locally. A run selector switches
between embedded bundles (e.g. mock vs real), and a "Load bundle…" control reads any local
`result.json`/bundle with the browser FileReader — ideal for testing and experimentation.

Semantic state is encoded in form, not just number:
  APPROVE -> PASS (green) · WARN -> WARN (amber) · BLOCK -> FAIL (red) · MANUAL_REVIEW -> REVIEW.
"""
from __future__ import annotations

import http.server
import json
import os
import socketserver
import webbrowser
from typing import Any, Dict, List, Optional

_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{
  --ground:#f6f7fb; --surface:#ffffff; --surface-2:#eef1f7; --border:#e3e7f0;
  --ink:#1a1e29; --muted:#5b6376; --faint:#8b93a6;
  --accent:#4f6bed; --accent-soft:#e7ebfd;
  --pass:#12925a; --pass-bg:#e4f4ec; --warn:#a9740d; --warn-bg:#fbf0da;
  --fail:#d0293e; --fail-bg:#fbe5e8; --review:#5a5ad0; --review-bg:#eaeafb;
  --sev-critical:#d0293e; --sev-high:#e2673a; --sev-medium:#a9740d; --sev-low:#5b6b8c; --sev-info:#8b93a6;
  --shadow:0 1px 2px rgba(16,22,40,.05),0 8px 24px rgba(16,22,40,.06);
  --mono:ui-monospace,"Cascadia Code","Cascadia Mono",Consolas,"SFMono-Regular",monospace;
  --sans:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",sans-serif;
}
@media (prefers-color-scheme:dark){:root{
  --ground:#0d1017; --surface:#151a24; --surface-2:#1c2230; --border:#242c3b;
  --ink:#e8ecf5; --muted:#949db2; --faint:#6e7689;
  --accent:#7089f6; --accent-soft:#1e2740;
  --pass:#2fbe7e; --pass-bg:#123024; --warn:#e0a53a; --warn-bg:#332711; --fail:#f2566a; --fail-bg:#331319;
  --review:#8f8ff0; --review-bg:#1e1e3a;
  --sev-critical:#f2566a; --sev-high:#f2895a; --sev-medium:#e0a53a; --sev-low:#7f90b4; --sev-info:#6e7689;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);
}}
:root[data-theme="light"]{
  --ground:#f6f7fb; --surface:#ffffff; --surface-2:#eef1f7; --border:#e3e7f0;
  --ink:#1a1e29; --muted:#5b6376; --faint:#8b93a6; --accent:#4f6bed; --accent-soft:#e7ebfd;
  --pass:#12925a; --pass-bg:#e4f4ec; --warn:#a9740d; --warn-bg:#fbf0da; --fail:#d0293e; --fail-bg:#fbe5e8;
  --review:#5a5ad0; --review-bg:#eaeafb;
  --sev-critical:#d0293e; --sev-high:#e2673a; --sev-medium:#a9740d; --sev-low:#5b6b8c; --sev-info:#8b93a6;
}
:root[data-theme="dark"]{
  --ground:#0d1017; --surface:#151a24; --surface-2:#1c2230; --border:#242c3b;
  --ink:#e8ecf5; --muted:#949db2; --faint:#6e7689; --accent:#7089f6; --accent-soft:#1e2740;
  --pass:#2fbe7e; --pass-bg:#123024; --warn:#e0a53a; --warn-bg:#332711; --fail:#f2566a; --fail-bg:#331319;
  --review:#8f8ff0; --review-bg:#1e1e3a;
  --sev-critical:#f2566a; --sev-high:#f2895a; --sev-medium:#e0a53a; --sev-low:#7f90b4; --sev-info:#6e7689;
}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--ground);color:var(--ink);font-family:var(--sans);line-height:1.5;
  -webkit-font-smoothing:antialiased;font-size:15px}
.wrap{max-width:1120px;margin:0 auto;padding:0 20px 64px}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--faint)}
h1,h2,h3{text-wrap:balance;margin:0}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
a{color:var(--accent)}

/* top bar */
.topbar{position:sticky;top:0;z-index:10;background:color-mix(in srgb,var(--ground) 86%,transparent);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--border)}
.topbar .row{max-width:1120px;margin:0 auto;padding:12px 20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:10px;font-weight:650;letter-spacing:-.01em}
.brand .dot{width:10px;height:10px;border-radius:3px;background:var(--accent);box-shadow:0 0 0 4px var(--accent-soft)}
.spacer{flex:1}
.control{display:flex;align-items:center;gap:8px}
label.lbl{font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
select,.btn{font:inherit;color:var(--ink);background:var(--surface);border:1px solid var(--border);
  border-radius:8px;padding:7px 12px;cursor:pointer}
.btn:hover,select:hover{border-color:var(--accent)}
.btn:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

/* hero verdict */
.hero{margin-top:24px;display:grid;grid-template-columns:minmax(240px,320px) 1fr;gap:18px;align-items:stretch}
@media (max-width:720px){.hero{grid-template-columns:1fr}}
.verdict{position:relative;border-radius:16px;padding:22px 24px;overflow:hidden;
  border:1px solid var(--border);background:var(--surface);box-shadow:var(--shadow)}
.verdict .stripe{position:absolute;left:0;top:0;bottom:0;width:8px}
.verdict .code{font-family:var(--sans);font-size:52px;font-weight:760;letter-spacing:-.03em;line-height:1;margin:10px 0 6px}
.verdict .rule{font-family:var(--mono);font-size:12px;color:var(--muted)}
.verdict .why{margin-top:8px;color:var(--muted);font-size:13.5px}
.chips{display:flex;flex-wrap:wrap;gap:10px;align-content:flex-start}
.chip{display:flex;flex-direction:column;gap:4px;min-width:132px;flex:1;
  background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:12px 14px;box-shadow:var(--shadow)}
.chip .k{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--faint)}
.chip .v{font-weight:600;font-size:14px;display:flex;align-items:center;gap:7px}
.led{width:9px;height:9px;border-radius:50%;flex:none;box-shadow:0 0 0 3px color-mix(in srgb,currentColor 18%,transparent)}

/* status colors */
.pass{color:var(--pass)} .warn{color:var(--warn)} .fail{color:var(--fail)} .review{color:var(--review)}
.bg-pass{background:var(--pass)} .bg-warn{background:var(--warn)} .bg-fail{background:var(--fail)} .bg-review{background:var(--review)}

/* section */
section{margin-top:34px}
.sec-head{display:flex;align-items:baseline;gap:12px;margin-bottom:14px}
.sec-head h2{font-size:15px;font-weight:650;letter-spacing:-.01em}
.sec-head .count{font-family:var(--mono);font-size:12px;color:var(--faint)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media (max-width:860px){.grid2{grid-template-columns:1fr}}
.card{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:18px 20px;box-shadow:var(--shadow)}
.card h3{font-size:13px;font-family:var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:14px}

/* definition rows */
.dl{display:grid;grid-template-columns:auto 1fr;gap:8px 18px}
.dl dt{font-family:var(--mono);font-size:12px;color:var(--muted);white-space:nowrap}
.dl dd{margin:0;text-align:right;font-weight:550;font-size:13.5px}
.dl dd .mono{font-size:12.5px}
.tags{display:flex;flex-wrap:wrap;gap:6px;justify-content:flex-end}
.tag{font-family:var(--mono);font-size:11px;background:var(--surface-2);border:1px solid var(--border);
  border-radius:6px;padding:2px 7px;color:var(--muted)}

/* harness signal cards */
.signals{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px}
.sig{position:relative;background:var(--surface);border:1px solid var(--border);border-radius:12px;
  padding:14px 15px 14px 18px;box-shadow:var(--shadow);overflow:hidden}
.sig .edge{position:absolute;left:0;top:0;bottom:0;width:5px}
.sig .id{font-family:var(--mono);font-weight:600;font-size:13px}
.sig .nm{font-size:12.5px;color:var(--muted);margin:2px 0 12px;min-height:34px}
.sig .foot{display:flex;align-items:center;justify-content:space-between;gap:8px}
.badge{font-family:var(--mono);font-size:11px;font-weight:650;letter-spacing:.08em;text-transform:uppercase;
  padding:3px 9px;border-radius:999px}
.badge.pass{background:var(--pass-bg)} .badge.warn{background:var(--warn-bg)}
.badge.fail{background:var(--fail-bg)} .badge.review{background:var(--review-bg)}
.sig .n{font-family:var(--mono);font-size:12px;color:var(--muted)}
.sig .n b{color:var(--ink);font-size:15px}

/* tables */
.tablewrap{overflow-x:auto;border:1px solid var(--border);border-radius:12px;background:var(--surface);box-shadow:var(--shadow)}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:11px 14px;border-bottom:1px solid var(--border);white-space:nowrap}
th{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--faint);font-weight:600}
tr:last-child td{border-bottom:none}
td.sev{position:relative;padding-left:20px;font-family:var(--mono);font-weight:650}
td.sev .st{position:absolute;left:0;top:0;bottom:0;width:5px}
.sc{font-family:var(--mono)}
.owasp{color:var(--faint);font-family:var(--mono);font-size:11.5px}

/* meter */
.meter{display:inline-flex;align-items:center;gap:8px}
.meter .track{width:74px;height:7px;border-radius:4px;background:var(--surface-2);overflow:hidden}
.meter .fill{height:100%;border-radius:4px}
.ok{color:var(--pass)} .no{color:var(--fail)}

.empty{color:var(--muted);font-style:italic;padding:18px;text-align:center}
.foot-note{margin-top:14px;color:var(--faint);font-size:12px;font-family:var(--mono)}
.drop{border:1px dashed var(--border);border-radius:8px;padding:6px 10px;color:var(--muted);font-size:12px}
.miss{margin:0;padding-left:18px;color:var(--muted);font-size:13px}
.miss li{margin:5px 0}

/* how-to legend (self-explaining dashboard) */
.howto{margin:16px 0 0;border:1px solid var(--border);border-radius:10px;background:var(--surface);overflow:hidden}
.howto>summary{cursor:pointer;padding:11px 16px;font-weight:600;font-size:13px;list-style:none;
  display:flex;align-items:center;gap:8px;color:var(--ink)}
.howto>summary::-webkit-details-marker{display:none}
.howto>summary::before{content:"?";display:inline-flex;align-items:center;justify-content:center;
  width:16px;height:16px;border-radius:50%;background:var(--surface-2);color:var(--muted);
  font-size:11px;font-weight:700}
.howto[open]>summary{border-bottom:1px solid var(--border)}
.howto .body{padding:14px 16px;font-size:13px;color:var(--muted);line-height:1.55}
.howto .body p{margin:0 0 12px}
.howto .body b{color:var(--ink)}
.howto .body dl{display:grid;grid-template-columns:minmax(120px,auto) 1fr;gap:7px 16px;margin:0}
.howto .body dt{font-weight:600;color:var(--ink);font-family:var(--mono);font-size:12px}
.howto .body dd{margin:0}
.howto .body .tip{margin:12px 0 0;font-size:12px;color:var(--faint)}

/* plugin inventory */
.legend{display:flex;flex-wrap:wrap;gap:14px;margin:-4px 0 14px;font-family:var(--mono);font-size:11px;color:var(--muted)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend .led{width:8px;height:8px}
.plugcols{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px}
.plug h3{display:flex;align-items:center;justify-content:space-between}
.plug .rows{display:flex;flex-direction:column;gap:2px}
.plug .r{display:grid;grid-template-columns:1fr auto;gap:10px 12px;align-items:center;
  padding:9px 2px;border-bottom:1px solid var(--border)}
.plug .r:last-child{border-bottom:none}
.plug .nm{font-size:13px;font-weight:550}
.plug .meta{font-family:var(--mono);font-size:11px;color:var(--faint);margin-top:2px}
.pill{font-family:var(--mono);font-size:10px;font-weight:650;letter-spacing:.07em;text-transform:uppercase;
  padding:3px 8px;border-radius:999px;white-space:nowrap;display:inline-flex;align-items:center;gap:6px}
.st-available{color:var(--pass)} .st-available.pill{background:var(--pass-bg)}
.st-installable{color:var(--warn)} .st-installable.pill{background:var(--warn-bg)}
.st-stub{color:var(--review)} .st-stub.pill{background:var(--review-bg)}
.st-enterprise{color:var(--faint)} .st-enterprise.pill{background:var(--surface-2)}
</style>
</head>
<body>
<div class="topbar"><div class="row">
  <div class="brand"><span class="dot"></span><span>AI Assurance Harness</span></div>
  <div class="control"><label class="lbl" for="runsel">Run</label><select id="runsel"></select></div>
  <div class="spacer"></div>
  <label class="btn" title="Load a local result/bundle JSON">Load bundle…
    <input id="file" type="file" accept="application/json,.json" hidden></label>
</div></div>

<div class="wrap">
<details class="howto">
  <summary>How to read this dashboard</summary>
  <div class="body">
    <p>This page is a <b>read-only report</b> for one assurance run. A <b>bundle</b>
      (<code>result_bundle.json</code>) is the complete saved record of that run — the gate decision,
      findings, evidence, scorecard and config. The <b>target</b> is either a <b>mock</b> (a built-in
      simulated model — no API key, no cost, deterministic; profile <code>vulnerable</code> ⇒ findings + BLOCK,
      <code>hardened</code> ⇒ 0 findings + APPROVE) or a <b>real</b> endpoint. Use the <b>Run</b> selector
      (top bar) to switch between bundles embedded in this page (e.g. mock vs real), or <b>Load bundle…</b>
      to open a saved <code>result_bundle.json</code> from disk — neither re-runs anything.</p>
    <dl>
      <dt>Hero</dt><dd>The verdict — the gate badge (APPROVE / WARN / BLOCK / MANUAL_REVIEW) plus chips. <b>Mode-A replay: reproduced</b> means the decision was rebuilt from evidence alone.</dd>
      <dt>Inputs</dt><dd>What produced the decision — the asset &amp; use case (drives risk) and the run configuration (provider, target &amp; judge model, quorum, fail-on severity, seed).</dd>
      <dt>Enterprise readiness</dt><dd>Whether this is a <b>real</b> or a <b>mock/simulated</b> run, and which enterprise dependencies are still stubbed for the pilot.</dd>
      <dt>Harness signals</dt><dd>What was tested — one card per harness with its finding count and a decision LED, plus the H5.1 governance self-check.</dd>
      <dt>Scorecard</dt><dd>Coverage vs known-vulnerability criteria (OWASP-LLM / NIST / ATLAS): PASS / WARN / FAIL, or <b>n/a</b> = not tested in this pack.</dd>
      <dt>Findings</dt><dd>Why it failed — each confirmed finding's severity, category, harness, and <b>basis</b> (detector = deterministic evidence; judge = model verdict).</dd>
    </dl>
    <p class="tip">Read top-down: the badge is the verdict, Enterprise-readiness tells you real vs mock,
      Harness-signals + Scorecard show what was tested, Findings show why it failed.</p>
  </div>
</details>
</div>

<div class="wrap" id="app"></div>

<script>
const DATA = /*__DATA__*/{};
const NAMES = /*__NAMES__*/{};
const CAPS = /*__CAPS__*/[];
const VERDICT = {approve:{code:"PASS",cls:"pass"},warn:{code:"WARN",cls:"warn"},
  block:{code:"FAIL",cls:"fail"},manual_review:{code:"REVIEW",cls:"review"}};
const SEVFILL = {critical:"var(--sev-critical)",high:"var(--sev-high)",medium:"var(--sev-medium)",
  low:"var(--sev-low)",info:"var(--sev-info)"};

const el=(t,c,txt)=>{const e=document.createElement(t);if(c)e.className=c;if(txt!=null)e.textContent=txt;return e;};
const esc=s=>String(s==null?"":s);

function verdict(dec){return VERDICT[dec]||{code:esc(dec).toUpperCase(),cls:"review"};}

function ledClass(dec){return verdict(dec).cls;}

function decBadge(dec){const v=verdict(dec);const b=el("span","badge "+v.cls,v.code);return b;}

function render(bundle){
  const app=document.getElementById("app");app.innerHTML="";
  const g=bundle.gate||{};const v=verdict(g.decision);
  const rc=bundle.run_config||{};const uc=bundle.use_case||{};const ctx=bundle.context||{};
  const hr=bundle.harness_results||{};const cal=bundle.calibration||{};
  const findings=bundle.findings||[];const gov=(bundle.governance||{}).metrics||{};
  const replay=(bundle.replay||{}).ok;
  const ready=bundle.enterprise_readiness||{};const miss=ready.missing||[];const live=ready.enabled||{};

  // pick a representative determinism / basis from first harness
  const first=Object.values(hr)[0]||{};const det=(first.determinism||{});
  const basis=first.evidence_basis||"—";

  // ---- HERO ----
  const hero=el("div","hero");
  const vc=el("div","verdict");
  const stripe=el("div","stripe "+("bg-"+v.cls));vc.appendChild(stripe);
  vc.appendChild(el("div","eyebrow","Gate decision"));
  const code=el("div","code "+v.cls,v.code);vc.appendChild(code);
  vc.appendChild(el("div","rule mono",esc(g.matched_rule||"")));
  vc.appendChild(el("div","why",esc(g.rationale||"")));
  hero.appendChild(vc);

  const chips=el("div","chips");
  const mkchip=(k,val,cls)=>{const c=el("div","chip");c.appendChild(el("div","k",k));
    const dd=el("div","v"+(cls?" "+cls:""));if(cls){const l=el("span","led");l.style.background="currentColor";dd.appendChild(l);}
    dd.appendChild(document.createTextNode(esc(val)));c.appendChild(dd);return c;};
  chips.appendChild(mkchip("Asset",esc(bundle.asset&&bundle.asset.name||"—")));
  chips.appendChild(mkchip("Risk tier",(ctx.tier||"—")+" ("+(ctx.score!=null?ctx.score:"—")+")"));
  chips.appendChild(mkchip("Evidence basis",basis.split("(")[0].trim()));
  chips.appendChild(mkchip("Mode-A replay",replay?"reproduced":"FAILED",replay?"pass":"fail"));
  chips.appendChild(mkchip("Determinism",det.determinism_class||"—"));
  chips.appendChild(mkchip("Findings",findings.length));
  // cost / latency (summed across harnesses)
  let tok=0,lat=0,cost=0;
  for(const r of Object.values(hr)){const m=r.metrics||{};tok+=m.tokens||0;lat+=m.latency_s||0;cost+=m.cost_usd||0;}
  chips.appendChild(mkchip("Tokens",tok.toLocaleString()));
  chips.appendChild(mkchip("Latency",lat.toFixed(2)+"s"));
  chips.appendChild(mkchip("Enterprise deps",miss.length?miss.length+" missing":"ready",miss.length?"warn":"pass"));
  hero.appendChild(chips);
  app.appendChild(hero);

  // ---- INPUTS ----
  const inSec=el("section");
  inSec.appendChild(secHead("Inputs","what produced this decision"));
  const g2=el("div","grid2");
  // use case card
  const c1=el("div","card");c1.appendChild(el("h3","Asset & use case"));
  const dl1=el("dl","dl");
  addRow(dl1,"name",uc.name||bundle.asset&&bundle.asset.name||"—");
  addTags(dl1,"data classes",uc.data_classes||[]);
  addRow(dl1,"exposure",uc.exposure||"—");
  addRow(dl1,"write tools",uc.write_tools==null?"—":(uc.write_tools?"present":"absent"));
  addTags(dl1,"users",uc.users||[]);
  addRow(dl1,"criticality",uc.criticality||"—");
  addRow(dl1,"required pack",(ctx.pack_tier||"—"));
  c1.appendChild(dl1);g2.appendChild(c1);
  // run config card
  const c2=el("div","card");c2.appendChild(el("h3","Run configuration"));
  const dl2=el("dl","dl");
  addRow(dl2,"provider",rc.provider_mode||"—");
  addRow(dl2,"target model",rc.target_model||"—",true);
  addRow(dl2,"judge model",rc.judge_model||"—",true);
  addRow(dl2,"quorum",(rc.quorum_n!=null?rc.quorum_n:"—")+" · "+(rc.quorum_rule||""));
  addRow(dl2,"fail-on severity",rc.fail_on_severity||"—");
  addRow(dl2,"seed",rc.seed!=null?rc.seed:"—",true);
  const b=rc.budget||{};addRow(dl2,"budget",(b.max_turns!=null?("turns "+b.max_turns+" · tok "+b.max_tokens):"—"),true);
  c2.appendChild(dl2);g2.appendChild(c2);
  inSec.appendChild(g2);app.appendChild(inSec);

  // ---- ENTERPRISE READINESS ----
  const rSec=el("section");
  rSec.appendChild(secHead("Enterprise readiness",miss.length?miss.length+" dependency gaps":"all configured"));
  const rg=el("div","grid2");
  const rc1=el("div","card");rc1.appendChild(el("h3","Live components"));
  const rdl=el("dl","dl");
  addRow(rdl,"provider",live.provider_mode||rc.provider_mode||"—");
  addRow(rdl,"target",live.real_target?"real endpoint/model":"mock/simulated");
  addRow(rdl,"judge",live.real_judge?"real independent judge":"offline/simulated");
  addRow(rdl,"scenarios",live.scenario_source||"built-in/config suite",true);
  addRow(rdl,"evidence",live.evidence_store||"—");
  addRow(rdl,"driver",live.driver||"—");
  addTags(rdl,"detectors",live.detectors||[]);
  addRow(rdl,"golden controls",live.golden_controls_ready?"production":"placeholder/missing");
  rc1.appendChild(rdl);rg.appendChild(rc1);
  const rc2=el("div","card");rc2.appendChild(el("h3","Missing enterprise dependencies"));
  if(!miss.length) rc2.appendChild(el("div","empty","No missing enterprise dependencies reported."));
  else{const ul=el("ul","miss");miss.forEach(x=>ul.appendChild(el("li",null,x)));rc2.appendChild(ul);}
  rg.appendChild(rc2);rSec.appendChild(rg);app.appendChild(rSec);

  // ---- HARNESS SIGNALS ----
  const hSec=el("section");
  hSec.appendChild(secHead("Harness signals",Object.keys(hr).length+" harnesses + governance"));
  const sig=el("div","signals");
  for(const [hid,r] of Object.entries(hr)){
    const cls=ledClass(r.decision);
    const card=el("div","sig");
    const edge=el("div","edge "+("bg-"+cls));card.appendChild(edge);
    card.appendChild(el("div","id",hid));
    card.appendChild(el("div","nm",esc(NAMES[hid]||"")));
    const foot=el("div","foot");
    const n=el("div","n");const nb=el("b",null,String((r.metrics||{}).findings!=null?r.metrics.findings:"—"));
    n.appendChild(nb);n.appendChild(document.createTextNode(" finding"+((r.metrics||{}).findings===1?"":"s")));
    foot.appendChild(n);foot.appendChild(decBadge(r.decision));
    card.appendChild(foot);
    sig.appendChild(card);
  }
  // governance mini card
  {const complete=gov.complete,checked=gov.checked;
   const okgov=checked!=null&&complete===checked;
   const card=el("div","sig");card.appendChild(el("div","edge "+("bg-"+(checked?(okgov?"pass":"warn"):"pass"))));
   card.appendChild(el("div","id","H5.1"));card.appendChild(el("div","nm","Finding Lifecycle / Evidence / Verdict"));
   const foot=el("div","foot");const n=el("div","n");
   const nb=el("b",null,(complete!=null?complete:"0")+"/"+(checked!=null?checked:"0"));
   n.appendChild(nb);n.appendChild(document.createTextNode(" complete"));
   foot.appendChild(n);const badge=el("span","badge "+(okgov?"pass":"warn"),okgov?"OK":"CHECK");foot.appendChild(badge);
   card.appendChild(foot);sig.appendChild(card);}
  hSec.appendChild(sig);app.appendChild(hSec);

  // ---- SCORECARD (vulnerability × criteria) ----
  const scard=bundle.scorecard;
  if(scard){
    const scSec=el("section");
    scSec.appendChild(secHead("Scorecard — vulnerability × criteria",
      "profile: "+esc(scard.profile||"")));
    const s=scard.summary||{};
    scSec.appendChild(el("div","foot-note",
      s.pass+" pass · "+s.warn+" warn · "+s.fail+" fail · "+s.not_tested+" not-tested   ·   declared trust "+
      (scard.declared_trust||"n/a")+
      (scard.trusted_but_failing?"   ·   ⚠ declared-high yet a blocking finding":"")));
    const w=el("div","tablewrap");const t=el("table");
    const thead=el("thead");const htr=el("tr");
    ["criterion","vulnerability","harnesses","status"].forEach(h=>htr.appendChild(el("th",null,h)));
    thead.appendChild(htr);t.appendChild(thead);const tb=el("tbody");
    const badgeCls={pass:"pass",warn:"warn",fail:"block",not_tested:"info"};
    const badgeTxt={pass:"PASS",warn:"WARN",fail:"FAIL",not_tested:"n/a"};
    (scard.rows||[]).forEach(r=>{
      const tr=el("tr");
      tr.appendChild(el("td","mono",esc(r.criterion)));
      tr.appendChild(el("td",null,esc(r.title)));
      tr.appendChild(el("td","mono",(r.harnesses||[]).join(", ")));
      const td=el("td");td.appendChild(el("span","badge "+(badgeCls[r.status]||"info"),badgeTxt[r.status]||r.status));
      tr.appendChild(td);tb.appendChild(tr);
    });
    t.appendChild(tb);w.appendChild(t);scSec.appendChild(w);app.appendChild(scSec);
  }

  // ---- FINDINGS ----
  const fSec=el("section");
  fSec.appendChild(secHead("Findings feedback",findings.length+" total"));
  if(!findings.length){const w=el("div","tablewrap");w.appendChild(el("div","empty","No confirmed findings — the target refused or no attack succeeded."));fSec.appendChild(w);}
  else{
    const w=el("div","tablewrap");const t=el("table");
    const thead=el("thead");const htr=el("tr");
    ["severity","category","harness","basis","OWASP-LLM"].forEach(h=>htr.appendChild(el("th",null,h)));
    thead.appendChild(htr);t.appendChild(thead);
    const tb=el("tbody");
    findings.slice().sort((a,b)=>rank(b.severity)-rank(a.severity)).forEach(f=>{
      const tr=el("tr");
      const sc=el("td","sev "+sevClass(f.severity));const st=el("div","st");st.style.background=SEVFILL[f.severity]||"var(--sev-info)";
      sc.appendChild(st);sc.appendChild(document.createTextNode(esc(f.severity)));tr.appendChild(sc);
      tr.appendChild(el("td","sc",esc(f.category)));
      tr.appendChild(el("td","mono",esc(f.harness)));
      tr.appendChild(el("td",null,esc(f.basis)));
      const ow=((f.standards||{}).owasp_llm||[]).join(" ");
      tr.appendChild(el("td","owasp",ow||"—"));
      tb.appendChild(tr);
    });
    t.appendChild(tb);w.appendChild(t);fSec.appendChild(w);
  }
  app.appendChild(fSec);

  // ---- CALIBRATION ----
  const cSec=el("section");
  cSec.appendChild(secHead("Judge calibration","precision / recall / accuracy vs ground truth"));
  const w=el("div","tablewrap");const t=el("table");
  const thead=el("thead");const htr=el("tr");
  ["harness","precision","recall","accuracy","gate-eligible"].forEach(h=>htr.appendChild(el("th",null,h)));
  thead.appendChild(htr);t.appendChild(thead);const tb=el("tbody");
  for(const [hid,c] of Object.entries(cal)){
    const tr=el("tr");tr.appendChild(el("td","mono",hid));
    tr.appendChild(meterCell(c.precision));tr.appendChild(meterCell(c.recall));tr.appendChild(meterCell(c.accuracy));
    const e=el("td","mono "+(c.gate_eligible?"ok":"no"),c.gate_eligible?"eligible":"not eligible");tr.appendChild(e);
    tb.appendChild(tr);
  }
  t.appendChild(tb);w.appendChild(t);cSec.appendChild(w);
  const jc=bundle.judge_calibration;
  if(jc){cSec.appendChild(el("div","foot-note",
    "judge calibration (verdict-level, target-independent): P="+jc.precision+" R="+jc.recall+" A="+jc.accuracy+
    " · eligible="+jc.gate_eligible+" · n="+jc.n+" · "+jc.basis));}
  const plan=bundle.plan||[];
  if(plan.length){cSec.appendChild(el("div","foot-note","selection: "+plan.map(p=>p.harness+" ("+(p.reason||"selected")+")").join(" · ")));}
  const skipped=bundle.skipped||[];
  if(skipped.length){cSec.appendChild(el("div","foot-note","skipped: "+skipped.map(s=>s.harness+" ("+s.reason+")").join(" · ")));}
  app.appendChild(cSec);

  // ---- PLUGINS & DEPENDENCIES (environment-level, same across runs) ----
  if(CAPS && CAPS.length) app.appendChild(renderCaps());
}

const CAPLABEL={available:"available",installable:"installable",stub:"stub",enterprise:"enterprise"};
function renderCaps(){
  const sec=el("section");
  const lab=CAPS.filter(c=>c.lab).length;
  sec.appendChild(secHead("Plugins & dependencies",lab+" / "+CAPS.length+" runnable in the lab"));
  const legend=el("div","legend");
  [["available","runs now"],["installable","pip install"],["stub","seam, buildable"],["enterprise","not wired in lab"]]
    .forEach(([k,txt])=>{const s=el("span");const d=el("span","led st-"+k);d.style.background="currentColor";
      s.appendChild(d);s.appendChild(document.createTextNode(k+" — "+txt));s.className="st-"+k;legend.appendChild(s);});
  sec.appendChild(legend);
  // group
  const groups={};CAPS.forEach(c=>{(groups[c.group]=groups[c.group]||[]).push(c);});
  const cols=el("div","plugcols");
  for(const [gname,items] of Object.entries(groups)){
    const card=el("div","card plug");
    const h=el("h3");h.appendChild(el("span",null,gname));
    const n=items.filter(i=>i.lab).length;h.appendChild(el("span","count","("+n+"/"+items.length+")"));
    card.appendChild(h);
    const rows=el("div","rows");
    items.forEach(c=>{
      const r=el("div","r");
      const left=el("div");left.appendChild(el("div","nm",esc(c.name)));
      let meta=esc(c.seam);
      if(c.extra&&c.status==="installable")meta+="  ·  .["+c.extra+"]";
      if(c.wired===false&&c.status==="installable")meta+="  ·  adapter: stub";
      if(c.pkg_installed===true&&c.status==="installable")meta+="  ·  pkg installed";
      if(c.key_present===false&&c.status==="available")meta+="  ·  no key in env";
      if(c.cite)meta+="  ·  "+esc(c.cite);
      left.appendChild(el("div","meta",meta));
      r.appendChild(left);
      const p=el("span","pill st-"+c.status);const dot=el("span","led");dot.style.background="currentColor";
      p.appendChild(dot);p.appendChild(document.createTextNode(CAPLABEL[c.status]||c.status));
      r.appendChild(p);
      rows.appendChild(r);
    });
    card.appendChild(rows);cols.appendChild(card);
  }
  sec.appendChild(cols);
  return sec;
}

function secHead(title,count){const h=el("div","sec-head");h.appendChild(el("h2",null,title));
  if(count!=null)h.appendChild(el("span","count",count));return h;}
function addRow(dl,k,val,mono){dl.appendChild(el("dt",null,k));const dd=el("dd",mono?"mono":null,esc(val));dl.appendChild(dd);}
function addTags(dl,k,arr){dl.appendChild(el("dt",null,k));const dd=el("dd");const tg=el("div","tags");
  (arr.length?arr:["—"]).forEach(x=>tg.appendChild(el("span","tag",esc(x))));dd.appendChild(tg);dl.appendChild(dd);}
function rank(s){return {info:0,low:1,medium:2,high:3,critical:4}[s]||0;}
function sevClass(s){return s;}
function meterCell(x){const td=el("td");const m=el("div","meter");const tr=el("div","track");const fl=el("div","fill");
  const pct=Math.round((x==null?0:x)*100);fl.style.width=pct+"%";
  fl.style.background=pct>=85?"var(--pass)":(pct>=60?"var(--warn)":"var(--fail)");
  tr.appendChild(fl);m.appendChild(tr);m.appendChild(el("span","mono",(x==null?"—":x.toFixed(2))));td.appendChild(m);return td;}

// ---- run selector + file loader ----
function populate(){
  const sel=document.getElementById("runsel");sel.innerHTML="";
  DATA.forEach((b,i)=>{const o=el("option",null,b.__label||("run "+(i+1)));o.value=i;sel.appendChild(o);});
  sel.onchange=()=>render(DATA[+sel.value]);
  render(DATA[0]);
}
document.getElementById("file").addEventListener("change",ev=>{
  const f=ev.target.files[0];if(!f)return;const r=new FileReader();
  r.onload=()=>{try{const b=JSON.parse(r.result);b.__label=f.name;DATA.unshift(b);populate();
    document.getElementById("runsel").value=0;render(DATA[0]);}
    catch(e){alert("Could not parse JSON: "+e.message);}};
  r.readAsText(f);
});
populate();
</script>
</body>
</html>
"""


def _label_for(bundle: dict, fallback: str) -> str:
    rc = bundle.get("run_config", {})
    prov = rc.get("provider_mode", "?")
    dec = (bundle.get("gate", {}) or {}).get("decision", "?")
    return f"{fallback} · {prov} · {dec}".strip(" ·")


def render_dashboard(bundles: List[dict], names: Dict[str, str],
                     title: str = "AI Assurance Harness — Dashboard",
                     labels: Optional[List[str]] = None,
                     capabilities: Optional[List[dict]] = None) -> str:
    """Render one or more bundles + the plugin/dependency inventory into one HTML document."""
    data = []
    for i, b in enumerate(bundles):
        b = dict(b)
        lbl = (labels[i] if labels and i < len(labels) else None)
        b["__label"] = lbl or _label_for(b, f"run {i + 1}")
        # drop private/live keys that don't serialize cleanly
        for k in list(b.keys()):
            if k.startswith("_") and k != "__label":
                b.pop(k, None)
        data.append(b)
    html = _TEMPLATE.replace("/*__DATA__*/{}", json.dumps(data, default=str))
    html = html.replace("/*__NAMES__*/{}", json.dumps(names, default=str))
    html = html.replace("/*__CAPS__*/[]", json.dumps(capabilities or [], default=str))
    html = html.replace("__TITLE__", title)
    return html


def write_dashboard(bundles: List[dict], names: Dict[str, str], out_path: str,
                    title: str = "AI Assurance Harness — Dashboard",
                    labels: Optional[List[str]] = None,
                    capabilities: Optional[List[dict]] = None) -> str:
    html = render_dashboard(bundles, names, title=title, labels=labels, capabilities=capabilities)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return os.path.abspath(out_path)


def open_in_browser(path: str) -> None:
    webbrowser.open("file://" + os.path.abspath(path))


def serve(directory: str, filename: str, port: int = 8000, open_browser: bool = True) -> None:
    """Serve `directory` on localhost:`port` and (optionally) open the dashboard. Ctrl-C to stop."""
    directory = os.path.abspath(directory)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=directory, **k)

        def log_message(self, *a):  # quiet
            pass

    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        url = f"http://127.0.0.1:{port}/{filename}"
        print(f"Serving dashboard at {url}  (Ctrl-C to stop)")
        if open_browser:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped.")
