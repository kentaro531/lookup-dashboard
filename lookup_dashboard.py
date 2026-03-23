#!/usr/bin/env python3
"""
LOOK UP Todoist Dashboard v8
python3 lookup_dashboard.py
"""
import json, sys, webbrowser, urllib.request, urllib.error, ssl, base64, os
from datetime import datetime, date, timedelta
from pathlib import Path

CONFIG = Path.home() / ".lookup_dashboard_config.json"
OUTPUT = Path.home() / "Desktop" / "LOOK_UP_Dashboard.html"
API = "https://api.todoist.com/api/v1"

def get_snapshot_dir():
    """In CI mode, use repo-local dir. In local mode, use home dir. Mode-specific subdirs."""
    mode = get_mode()
    if os.environ.get("CI") == "true":
        base = Path("./snapshots")
    else:
        base = Path.home() / ".lookup_snapshots"
    if mode != "all":
        return base / mode
    return base
ANTHROPIC_API = "https://api.anthropic.com/v1/messages"
SLACK_API = "https://slack.com/api"
EXCLUDE_PROJECTS = ["00_LIFE"]
ACCG_PREFIX = "40_ACCG_"
ACCOUNTING_PROJECT_PREFIX = "40"
EXCLUDE_MEMBERS = ["Nao Matsumoto", "迫田昂輝", "Shihomi Okit", "米満"]

def get_mode():
    """Determine dashboard mode: 'all', 'accounting', 'non-accounting'."""
    # CLI args take priority
    if "--accounting" in sys.argv: return "accounting"
    if "--non-accounting" in sys.argv: return "non-accounting"
    # CI env var
    mode = os.environ.get("DASHBOARD_MODE", "all").lower()
    if mode in ("accounting", "non-accounting", "all"):
        return mode
    return "all"

def filter_by_mode(projects, sections, tasks, mode):
    """Filter projects/sections/tasks by mode."""
    if mode == "all":
        return projects, sections, tasks
    
    if mode == "accounting":
        target_pids = set(
            p.get("id") for p in projects
            if isinstance(p, dict) and p.get("name","").startswith(ACCOUNTING_PROJECT_PREFIX)
        )
        label = "会計（40_）"
    else:  # non-accounting
        target_pids = set(
            p.get("id") for p in projects
            if isinstance(p, dict) and not p.get("name","").startswith(ACCOUNTING_PROJECT_PREFIX)
        )
        label = "会計以外"

    projects = [p for p in projects if isinstance(p, dict) and p.get("id") in target_pids]
    sections = [s for s in sections if isinstance(s, dict) and s.get("project_id") in target_pids]
    tasks = [t for t in tasks if isinstance(t, dict) and t.get("project_id") in target_pids]
    print(f"    モード: {label} → {len(projects)}プロジェクト / {len(tasks)}タスク")
    return projects, sections, tasks

LOGO_B64 = "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"

def load_cfg():
    return json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
def save_cfg(c):
    CONFIG.write_text(json.dumps(c))
def api_get(url_path, token):
    url = url_path if url_path.startswith("http") else f"{API}/{url_path}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context()) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code in (401,403): print(f"  認証エラー ({e.code})"); save_cfg({}); sys.exit(1)
        return None
def extract(resp):
    if resp is None: return [], None
    if isinstance(resp, list): return resp, None
    if isinstance(resp, dict):
        items = []
        for k in ("results","items","data"):
            if k in resp and isinstance(resp[k], list): items = resp[k]; break
        return items, resp.get("next_cursor")
    return [], None
def fetch_all_pages(endpoint, token):
    all_items = []; url = endpoint; page = 1
    while True:
        resp = api_get(url, token); items, cursor = extract(resp)
        all_items.extend(items)
        if cursor:
            base = endpoint.split("?")[0]; url = f"{base}?cursor={cursor}"
            page += 1; sys.stdout.write(f"\r    ページ {page} ({len(all_items)}件)..."); sys.stdout.flush()
        else: break
    return all_items
def fetch(tok):
    print("  プロジェクト..."); projects = fetch_all_pages("projects", tok); print(f"    {len(projects)}件")
    print("  セクション..."); sections = fetch_all_pages("sections", tok); print(f"    {len(sections)}件")
    print("  タスク..."); tasks = fetch_all_pages("tasks", tok); print(f"    {len(tasks)}件")
    print("  メンバー...")
    collabs = {}
    for p in projects:
        if not isinstance(p, dict): continue
        pid = p.get("id")
        if not pid: continue
        try:
            items, _ = extract(api_get(f"projects/{pid}/collaborators", tok))
            for c in items:
                if isinstance(c, dict):
                    cid = str(c.get("id") or c.get("user_id") or "")
                    if cid: collabs[cid] = c
        except: pass
    print(f"    {len(collabs)}名")
    excl_ids = set()
    for p in projects:
        if isinstance(p, dict) and p.get("name") in EXCLUDE_PROJECTS:
            excl_ids.add(p.get("id")); print(f"    除外: {p.get('name')}")
    if excl_ids:
        projects = [p for p in projects if isinstance(p,dict) and p.get("id") not in excl_ids]
        sections = [s for s in sections if isinstance(s,dict) and s.get("project_id") not in excl_ids]
        tasks = [t for t in tasks if isinstance(t,dict) and t.get("project_id") not in excl_ids]
    print(f"    最終: {len(tasks)}タスク")
    return projects, sections, tasks, collabs

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>LOOK UP Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0A0F1C;--sf:#111827;--sfh:#1a2235;--card:#1E293B;--bd:#2D3A52;--tx:#E2E8F0;--txm:#94A3B8;--txd:#64748B;--ac:#3B82F6;--acl:#60A5FA;--gn:#22C55E;--yl:#FACC15;--or:#F97316;--rd:#EF4444;--pu:#A78BFA}
body{background:var(--bg);color:var(--tx);font-family:'JetBrains Mono',monospace;min-height:100vh}

/* Header */
.hdr{position:sticky;top:0;z-index:100;background:rgba(10,15,28,.92);backdrop-filter:blur(12px);border-bottom:1px solid var(--bd);padding:10px 24px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.logo-s{font-size:10px;color:var(--ac);margin-left:4px}
.gen{font-size:9px;color:var(--txd);margin-left:auto}

/* Nav */
.nav{padding:10px 24px;display:flex;gap:6px;flex-wrap:wrap;align-items:center;border-bottom:1px solid var(--bd);background:var(--sf)}
.nav-group{display:flex;background:var(--bg);border-radius:6px;border:1px solid var(--bd);overflow:hidden}
.nav-btn{padding:6px 14px;font-size:10px;border:none;cursor:pointer;font-family:inherit;background:transparent;color:var(--txm);transition:.15s;white-space:nowrap}
.nav-btn.on{background:var(--ac);color:#fff;font-weight:600}
.nav-btn:hover:not(.on){background:var(--sfh)}
.nav-sep{width:1px;background:var(--bd);margin:0 8px;height:20px}
.nav-label{font-size:9px;color:var(--txd);text-transform:uppercase;letter-spacing:1px;margin-right:4px}

/* Member chips */
.member-bar{padding:8px 24px;display:flex;gap:6px;flex-wrap:wrap;border-bottom:1px solid var(--bd);background:rgba(17,24,39,.6)}
.member-chip{padding:5px 12px;font-size:10px;border-radius:16px;cursor:pointer;border:1px solid var(--bd);background:var(--card);color:var(--txm);font-family:inherit;transition:.15s;display:flex;align-items:center;gap:4px}
.member-chip.on{background:var(--ac);border-color:var(--ac);color:#fff;font-weight:600}
.member-chip:hover:not(.on){background:var(--sfh)}
.member-chip .chip-count{font-size:8px;opacity:.7}

/* Date blocks container */
.blocks{display:flex;gap:10px;padding:16px 24px;flex-wrap:wrap}

/* Date block card */
.block-card{flex:1;min-width:150px;max-width:250px;background:var(--card);border:1px solid var(--bd);border-radius:10px;cursor:pointer;transition:all .2s;position:relative;overflow:hidden}
.block-card:hover{border-color:var(--acl);transform:translateY(-2px)}
.block-card.active{border-color:var(--ac);box-shadow:0 0 20px rgba(59,130,246,.15)}
.block-top{padding:14px 16px}
.block-label{font-size:10px;font-weight:600;margin-bottom:8px}
.block-nums{display:flex;justify-content:space-between;align-items:baseline}
.block-count{font-size:26px;font-weight:800}
.block-time{font-size:12px;font-weight:600}
.block-bar{height:3px;background:var(--bd)}
.block-bar-fill{height:100%;border-radius:2px;transition:width .3s}

.block-ov .block-label{color:var(--rd)}.block-ov .block-count{color:var(--rd)}.block-ov .block-time{color:var(--rd)}.block-ov .block-bar-fill{background:var(--rd)}
.block-td .block-label{color:var(--or)}.block-td .block-count{color:var(--or)}.block-td .block-time{color:var(--or)}.block-td .block-bar-fill{background:var(--or)}
.block-tm .block-label{color:var(--yl)}.block-tm .block-count{color:var(--yl)}.block-tm .block-time{color:var(--yl)}.block-tm .block-bar-fill{background:var(--yl)}
.block-da .block-label{color:var(--acl)}.block-da .block-count{color:var(--acl)}.block-da .block-time{color:var(--acl)}.block-da .block-bar-fill{background:var(--acl)}
.block-ft .block-label{color:var(--txm)}.block-ft .block-count{color:var(--tx)}.block-ft .block-time{color:var(--gn)}.block-ft .block-bar-fill{background:var(--gn)}

/* Detail panel */
.detail{margin:0 24px 16px;border:1px solid var(--bd);border-radius:10px;background:var(--sf);overflow:hidden;display:none}
.detail.show{display:block}
.detail-hdr{padding:10px 14px;font-size:11px;font-weight:700;border-bottom:1px solid var(--bd);display:flex;justify-content:space-between;align-items:center}
.detail-close{cursor:pointer;color:var(--txd);font-size:14px;padding:0 6px}

/* Shared task/section styles */
.main{padding:12px 24px 40px}
.sec{margin-bottom:6px}
.sh{display:flex;align-items:center;gap:8px;padding:8px 12px;background:var(--card);cursor:pointer;user-select:none;border:1px solid var(--bd)}.sh.op{border-radius:8px 8px 0 0;border-bottom:none}.sh.cl{border-radius:8px}
.arr{font-size:10px;color:var(--txm);display:inline-block;transition:transform .2s}.arr.op{transform:rotate(90deg)}
.dot{width:8px;height:8px;border-radius:50%}
.st{flex:1;font-size:12px;font-weight:600;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.scn{font-size:10px;color:var(--txm);background:var(--sf);padding:2px 8px;border-radius:10px}
.sb{border:1px solid var(--bd);border-top:none;border-radius:0 0 8px 8px;overflow:hidden;background:var(--sf)}
.ssh{padding:6px 12px;font-size:11px;font-weight:600;color:var(--acl);background:rgba(30,64,175,.13);border-top:1px solid var(--bd);display:flex;justify-content:space-between;align-items:center}
.ssn{padding:5px 12px;font-size:9px;color:var(--txd);text-transform:uppercase;letter-spacing:1px;background:rgba(10,15,28,.4)}
.tr{display:flex;align-items:center;padding:6px 12px;border-bottom:1px solid var(--bd);gap:6px;font-size:12px;transition:background .15s}.tr:hover{background:var(--sfh)}.tr:last-child{border-bottom:none}
.tp{font-size:9px;font-weight:700;padding:2px 5px;border-radius:3px;min-width:22px;text-align:center}
.tc{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tpj{font-size:9px;color:var(--txd);background:var(--card);padding:2px 6px;border-radius:10px}
.tas{font-size:9px;color:var(--pu);background:rgba(167,139,250,.12);padding:2px 6px;border-radius:10px}
.tlb{font-size:9px;color:var(--gn);background:rgba(34,197,94,.1);padding:2px 6px;border-radius:10px}
.tsc{font-size:9px;color:var(--acl);background:rgba(59,130,246,.1);padding:2px 6px;border-radius:10px;white-space:nowrap;max-width:140px;overflow:hidden;text-overflow:ellipsis}
.td{font-size:10px;font-weight:600}.td.ov{color:var(--rd);background:rgba(239,68,68,.1);padding:2px 5px;border-radius:3px}.td.to{color:var(--or)}.td.sn{color:var(--yl)}.td.nm{color:var(--txd)}
.bg{font-size:9px;padding:2px 6px;border-radius:10px;white-space:nowrap}.bg-r{color:var(--rd);background:rgba(239,68,68,.12)}.bg-o{color:var(--or);background:rgba(249,115,22,.12)}.bg-y{color:var(--yl);background:rgba(250,204,21,.12)}.bg-g{color:var(--gn);background:rgba(34,197,94,.12)}
.client-badges{display:flex;gap:4px;flex-wrap:wrap}
.empty{text-align:center;padding:30px;color:var(--txm);font-size:12px}
.chg-bar{margin:8px 24px;padding:10px 16px;background:rgba(249,115,22,.08);border:1px solid rgba(249,115,22,.2);border-radius:10px;cursor:pointer;display:flex;align-items:center;gap:10px;transition:all .15s}
.chg-bar:hover{background:rgba(249,115,22,.12)}
.chg-bar-icon{font-size:16px}
.chg-bar-text{flex:1;font-size:11px;color:var(--or);font-weight:600}
.chg-bar-count{font-size:20px;font-weight:800;color:var(--or)}
.chg-bar-detail{font-size:9px;color:var(--txm)}
.chg-panel{margin:0 24px 12px;border:1px solid var(--bd);border-radius:10px;background:var(--sf);overflow:hidden}
.chg-hdr{padding:10px 14px;font-size:11px;font-weight:700;border-bottom:1px solid var(--bd);display:flex;justify-content:space-between;align-items:center;color:var(--or)}
.chg-row{display:flex;align-items:center;padding:7px 12px;border-bottom:1px solid var(--bd);gap:8px;font-size:11px;transition:background .15s}
.chg-row:hover{background:var(--sfh)}.chg-row:last-child{border-bottom:none}
.chg-type{font-size:9px;font-weight:700;padding:2px 6px;border-radius:3px;min-width:36px;text-align:center}
.chg-postponed{color:var(--rd);background:rgba(239,68,68,.12)}
.chg-earlier{color:var(--gn);background:rgba(34,197,94,.12)}
.chg-removed{color:var(--txd);background:rgba(100,116,139,.12)}
.chg-added{color:var(--acl);background:rgba(59,130,246,.12)}
.chg-content{flex:1;color:var(--tx);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chg-arrow{color:var(--txd);font-size:10px}
.chg-date-old{color:var(--txd);text-decoration:line-through;font-size:10px}
.chg-date-new{color:var(--or);font-weight:600;font-size:10px}
.weekly-view{padding:12px 24px}
.weekly-period{font-size:11px;color:var(--txm);margin-bottom:12px;font-weight:600}
.weekly-tbl{width:100%;border-collapse:collapse;font-size:12px}
.weekly-tbl thead{background:var(--sf)}
.weekly-tbl th{padding:8px 10px;text-align:center;color:var(--txm);font-weight:600;border-bottom:1px solid var(--bd)}
.weekly-tbl th.wt-name{text-align:left;min-width:100px}
.weekly-tbl th.wt-grp{font-size:13px;color:var(--tx);padding:6px 10px}
.weekly-tbl th.wt-sub{font-size:10px;color:var(--txd)}
.weekly-tbl td{padding:7px 10px;border-bottom:1px solid var(--bd)}
.weekly-tbl td.wt-name{color:var(--tx);font-weight:600;white-space:nowrap}
.weekly-tbl td.wt-val{text-align:center;color:var(--txm)}
.weekly-tbl td.wt-total,.weekly-tbl th.wt-total{font-weight:700;color:var(--tx)}
.weekly-tbl tr:hover{background:var(--sfh)}
.weekly-tbl tr.wt-foot{background:var(--sf);border-top:2px solid var(--bd)}
.weekly-tbl tr.wt-foot td{font-weight:700;color:var(--ac)}
.wt-click{cursor:pointer;position:relative}
.wt-click:hover{background:rgba(59,130,246,.15);border-radius:4px}
.wt-cnt{font-size:10px;color:var(--txd)}
.wt-detail-row td{padding:0!important;background:var(--bg)}
.wt-detail{padding:8px 16px;max-height:300px;overflow-y:auto}
.wt-detail-item{display:flex;gap:8px;padding:4px 8px;border-bottom:1px solid var(--bd);font-size:11px;align-items:center}
.wt-detail-item:last-child{border-bottom:none}
.wt-detail-date{color:var(--txd);min-width:40px;font-size:10px}
.wt-detail-content{flex:1;color:var(--tx);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.wt-detail-proj{color:var(--txd);font-size:10px;max-width:120px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.wt-detail-min{color:var(--ac);font-weight:600;font-size:10px;min-width:40px;text-align:right}
.sec-cards{display:flex;gap:8px;padding:12px 24px;flex-wrap:wrap}
.sec-card{background:var(--sf);border:1px solid var(--bd);border-radius:8px;padding:10px 14px;cursor:pointer;min-width:140px;max-width:200px;transition:all .15s}
.sec-card:hover{background:var(--sfh);border-color:var(--ac)}
.sec-card.active{border-color:var(--ac);background:rgba(59,130,246,.08)}
.sec-card-name{font-size:12px;font-weight:700;color:var(--tx);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sec-card-proj{font-size:9px;color:var(--txd);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sec-card-stats{display:flex;gap:8px;margin-top:6px;align-items:center}
.sec-card-count{font-size:11px;color:var(--txm)}
.sec-card-time{font-size:11px;color:var(--ac);font-weight:600}
.sec-card-badges{display:flex;gap:3px;margin-top:4px;flex-wrap:wrap}
.sec-detail{margin:0 24px 16px;border:1px solid var(--bd);border-radius:10px;background:var(--sf);overflow:hidden}
.sec-detail-hdr{padding:10px 14px;display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--bd);background:rgba(59,130,246,.05)}
.sec-detail-hdr>span:first-child{font-size:13px;font-weight:700;color:var(--tx);flex:1}
.sec-detail-info{font-size:11px;color:var(--txm)}
.sec-detail .blocks{padding:10px 14px}
.sec-detail .block-card{min-width:80px}
.member-cards{display:flex;gap:8px;padding:12px 14px;flex-wrap:wrap}
.m-card{min-width:120px;flex:1;max-width:200px;background:var(--bg);border:1px solid var(--bd);border-radius:8px;padding:10px 14px;cursor:pointer;transition:all .2s}
.m-card:hover{border-color:var(--acl);transform:translateY(-1px)}
.m-card.active{border-color:var(--ac);background:rgba(59,130,246,.08)}
.m-card-name{font-size:11px;font-weight:700;color:var(--tx);margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.m-card-row{display:flex;justify-content:space-between;align-items:baseline}
.m-card-count{font-size:18px;font-weight:800;color:var(--tx)}
.m-card-time{font-size:11px;font-weight:600;color:var(--gn)}
.m-card-unit{font-size:8px;color:var(--txd)}
</style></head><body><div id="app"></div>
<script>
var DATA = __DATA_PLACEHOLDER__;
var ACCG_PREFIX = "__ACCG_PREFIX__";
var PCOL={4:"#EF4444",3:"#F97316",2:"#FACC15",1:"#64748B"};
var PLAB={4:"P1",3:"P2",2:"P3",1:"P4"};
var PPAL=["#3B82F6","#22C55E","#F97316","#A78BFA","#EC4899","#14B8A6","#FACC15","#EF4444","#06B6D4","#8B5CF6"];
var S={mode:"member",sub:"all",member:"__all__",openBlock:null,openMember:null,showChanges:true,weekDetail:null,openSection:null,secBlock:null};
// For filtered modes, default to project view (data is already filtered)
if(DATA.dashboard_mode==="accounting"||DATA.dashboard_mode==="non-accounting"){S.mode="project";S.sub="all";}

var secMap={};for(var i=0;i<DATA.sections.length;i++)secMap[DATA.sections[i].id]=DATA.sections[i];
var projMap={};for(var i=0;i<DATA.projects.length;i++)projMap[DATA.projects[i].id]=DATA.projects[i];

function isOv(d){if(!d)return false;var t=new Date();t.setHours(0,0,0,0);return new Date(d)<t;}
function isTd(d){return d===DATA.today;}
function isTm(d){return d===DATA.tomorrow;}
function isDat(d){return d===DATA.dayafter;}
function isSn(d){if(!d)return false;var f=(new Date(d)-new Date())/864e5;return f>=0&&f<=3;}
function fmtD(d){if(!d)return"";var t=new Date(d+"T00:00:00");var w=["日","月","火","水","木","金","土"];return(t.getMonth()+1)+"/"+t.getDate()+"("+w[t.getDay()]+")";}
function esc(s){if(!s)return"";var d=document.createElement("div");d.textContent=s;return d.innerHTML;}
function gA(t){return String(t.assignee_id||t.responsible_uid||"");}
function isExcludedMember(aid){
  if(!aid||!DATA.exclude_members||!DATA.exclude_members.length)return false;
  var c=DATA.collaborators[aid];if(!c)return false;
  var nm=(c.name||c.full_name||c.email||"").toLowerCase();
  for(var i=0;i<DATA.exclude_members.length;i++){if(nm.indexOf(DATA.exclude_members[i].toLowerCase())>=0)return true;}
  return false;
}
function isAccg(t){var p=projMap[t.project_id];return p&&p.name&&p.name.indexOf(ACCG_PREFIX)===0;}
function isAcct40(t){var p=projMap[t.project_id];return p&&p.name&&p.name.substring(0,2)==="40";}
function getWeekBounds(){
  var today=new Date(DATA.today);
  var dow=today.getDay();var diff=dow===0?6:dow-1;
  var mon=new Date(today);mon.setDate(today.getDate()-diff);
  var sun=new Date(mon);sun.setDate(mon.getDate()+6);
  var nMon=new Date(mon);nMon.setDate(mon.getDate()+7);
  var nSun=new Date(nMon);nSun.setDate(nMon.getDate()+6);
  function fmt(d){return d.toISOString().split("T")[0];}
  return{thisWeek:{start:fmt(mon),end:fmt(sun)},nextWeek:{start:fmt(nMon),end:fmt(nSun)}};
}
function inRange(d,s,e){return d&&d>=s&&d<=e;}

function parseMinutes(labels){
  if(!labels||!labels.length)return 0;var total=0;
  for(var i=0;i<labels.length;i++){
    var lb=labels[i].toLowerCase().replace(/^@/,"");var m;
    if(lb==="lessthan5minutes"){total+=5;continue;}
    m=lb.match(/^(\d+)\s*minutes?$/);if(m){total+=parseInt(m[1]);continue;}
    m=lb.match(/^(\d+)\s*hours?$/);if(m){total+=parseInt(m[1])*60;continue;}
  }
  return total;
}
function fmtMin(m){if(m>=60){var h=Math.floor(m/60);var r=m%60;return r?h+"h"+r+"m":h+"h";}return m+"m";}

function sortTasks(arr){return arr.sort(function(a,b){var ao=isOv(a.due?a.due.date:null)?0:1;var bo=isOv(b.due?b.due.date:null)?0:1;if(ao!==bo)return ao-bo;if((b.priority||1)!==(a.priority||1))return(b.priority||1)-(a.priority||1);var ad=a.due?a.due.date:"";var bd=b.due?b.due.date:"";if(ad&&bd)return ad<bd?-1:ad>bd?1:0;return ad?-1:1;});}

function toggle(id){var b=document.getElementById("b-"+id);var a=document.getElementById("a-"+id);if(!b)return;var h=a.parentElement;if(b.style.display==="none"){b.style.display="";a.className="arr op";h.className="sh op";}else{b.style.display="none";a.className="arr";h.className="sh cl";}}

function tRow(t,sP,sA){
  var pc=PCOL[t.priority]||PCOL[1];var dd=t.due?t.due.date:null;
  var dc="nm",dp="";
  if(isOv(dd)){dc="ov";dp="! ";}else if(isTd(dd)){dc="to";}else if(isSn(dd)){dc="sn";}
  var pn=projMap[t.project_id]?projMap[t.project_id].name:"";
  var sn=t.section_id&&secMap[t.section_id]?secMap[t.section_id].name:"";
  var aid=gA(t);var as=aid?DATA.collaborators[aid]:null;
  var aname=as?(as.name||as.full_name||as.email||""):"";
  var mins=parseMinutes(t.labels);
  return '<div class="tr"><span class="tp" style="color:'+pc+';background:'+pc+'18">'+(PLAB[t.priority]||"P4")+'</span><span class="tc">'+esc(t.content)+'</span>'+(mins?'<span class="tlb">'+fmtMin(mins)+'</span>':"")+(sn?'<span class="tsc">'+esc(sn)+'</span>':"")+(sA&&aname?'<span class="tas">'+esc(aname)+'</span>':"")+(sP?'<span class="tpj">'+esc(pn)+'</span>':"")+(dd?'<span class="td '+dc+'">'+dp+fmtD(dd)+'</span>':"")+'</div>';
}

function bucketTasks(tasks){
  var b={overdue:[],today:[],tomorrow:[],dayafter:[],rest:[]};
  for(var i=0;i<tasks.length;i++){
    var t=tasks[i];var dd=t.due?t.due.date:null;
    if(!dd){b.rest.push(t);continue;}
    if(isOv(dd))b.overdue.push(t);
    else if(isTd(dd))b.today.push(t);
    else if(isTm(dd))b.tomorrow.push(t);
    else if(isDat(dd))b.dayafter.push(t);
    else b.rest.push(t);
  }
  return b;
}

function bucketInfo(arr){
  var mins=0;for(var i=0;i<arr.length;i++)mins+=parseMinutes(arr[i].labels);
  return {count:arr.length,mins:mins};
}

function clickBlock(key){
  if(S.openBlock===key){S.openBlock=null;S.openMember=null;}
  else{S.openBlock=key;S.openMember=null;}
  render();
}
function clickMemberCard(memberId){
  if(S.openMember===memberId)S.openMember=null;
  else S.openMember=memberId;
  render();
}

function groupByMember(tasks){
  var map={};
  for(var i=0;i<tasks.length;i++){
    var t=tasks[i];var a=gA(t)||"__ua__";
    if(isExcludedMember(a))continue;
    if(!map[a])map[a]={tasks:[],mins:0};
    map[a].tasks.push(t);
    map[a].mins+=parseMinutes(t.labels);
  }
  var arr=[];
  for(var k in map){
    var c=DATA.collaborators[k];
    var nm=k==="__ua__"?"未割当":(c?(c.name||c.full_name||c.email||"不明"):"不明");
    arr.push({id:k,name:nm,tasks:map[k].tasks,mins:map[k].mins,count:map[k].tasks.length});
  }
  arr.sort(function(a,b){return b.mins-a.mins||b.count-a.count;});
  return arr;
}

function groupByProject(tasks){
  var map={};
  for(var i=0;i<tasks.length;i++){
    var t=tasks[i];var pid=t.project_id||"__np__";
    if(!map[pid])map[pid]={tasks:[],mins:0};
    map[pid].tasks.push(t);
    map[pid].mins+=parseMinutes(t.labels);
  }
  var arr=[];
  for(var k in map){
    var p=projMap[k];
    var nm=k==="__np__"?"プロジェクトなし":(p?(p.name||"不明"):"不明");
    arr.push({id:k,name:nm,tasks:map[k].tasks,mins:map[k].mins,count:map[k].tasks.length});
  }
  arr.sort(function(a,b){return b.count-a.count||b.mins-a.mins;});
  return arr;
}

function renderBlocks(tasks,prefix,drilldown){
  var bk=bucketTasks(tasks);
  var maxCount=Math.max(bk.overdue.length,bk.today.length,bk.tomorrow.length,bk.dayafter.length,bk.rest.length,1);
  var defs=[
    {key:"overdue",label:"期限超過",cls:"block-ov",tasks:bk.overdue},
    {key:"today",label:"今日 "+fmtD(DATA.today),cls:"block-td",tasks:bk.today},
    {key:"tomorrow",label:"明日 "+fmtD(DATA.tomorrow),cls:"block-tm",tasks:bk.tomorrow},
    {key:"dayafter",label:"明後日 "+fmtD(DATA.dayafter),cls:"block-da",tasks:bk.dayafter},
    {key:"rest",label:"それ以降",cls:"block-ft",tasks:bk.rest}
  ];

  // Date block cards
  var h='<div class="blocks">';
  for(var i=0;i<defs.length;i++){
    var d=defs[i];var info=bucketInfo(d.tasks);
    var fullKey=prefix+"_"+d.key;
    var isActive=S.openBlock===fullKey;
    var barW=maxCount>0?Math.round(info.count/maxCount*100):0;
    h+='<div class="block-card '+d.cls+(isActive?" active":"")+'" onclick="clickBlock(\''+fullKey+'\')">';
    h+='<div class="block-top"><div class="block-label">'+d.label+'</div>';
    h+='<div class="block-nums"><span class="block-count">'+info.count+'</span>';
    h+=(info.mins?'<span class="block-time">'+fmtMin(info.mins)+'</span>':'<span class="block-time" style="opacity:.3">0m</span>')+'</div></div>';
    h+='<div class="block-bar"><div class="block-bar-fill" style="width:'+barW+'%"></div></div>';
    h+='</div>';
  }
  h+='</div>';

  // Detail panel for active block
  for(var i=0;i<defs.length;i++){
    var d=defs[i];var fullKey=prefix+"_"+d.key;
    if(S.openBlock!==fullKey||!d.tasks.length)continue;
    var info=bucketInfo(d.tasks);

    if(drilldown==="member"||drilldown===true){
      // DRILL-DOWN: member cards
      var members=groupByMember(d.tasks);
      h+='<div class="detail show"><div class="detail-hdr"><span>'+d.label+' &#8212; '+info.count+'件'+(info.mins?' / '+fmtMin(info.mins):'')+'</span><span class="detail-close" onclick="S.openBlock=null;S.openMember=null;render()">&#10005;</span></div>';
      h+='<div class="member-cards">';
      for(var mi=0;mi<members.length;mi++){
        var m=members[mi];
        var isOn=S.openMember===m.id;
        h+='<div class="m-card'+(isOn?" active":"")+'" onclick="event.stopPropagation();clickMemberCard(\''+m.id+'\')">';
        h+='<div class="m-card-name">'+esc(m.name)+'</div>';
        h+='<div class="m-card-row"><span class="m-card-count">'+m.count+'<span class="m-card-unit"> 件</span></span>';
        h+=(m.mins?'<span class="m-card-time">'+fmtMin(m.mins)+'</span>':'')+'</div>';
        h+='</div>';
      }
      h+='</div>';

      if(S.openMember){
        var selMember=null;
        for(var mi=0;mi<members.length;mi++){if(members[mi].id===S.openMember){selMember=members[mi];break;}}
        if(selMember){
          h+='<div style="padding:6px 14px;font-size:10px;font-weight:600;color:var(--acl);background:rgba(30,64,175,.1);border-top:1px solid var(--bd);display:flex;justify-content:space-between;align-items:center"><span>'+esc(selMember.name)+' &#8212; '+selMember.count+'件'+(selMember.mins?' / '+fmtMin(selMember.mins):'')+'</span><span style="color:var(--txd);font-size:9px;cursor:pointer" onclick="event.stopPropagation();S.openMember=null;render()">&#10005; 閉じる</span></div>';
          sortTasks(selMember.tasks);
          for(var j=0;j<selMember.tasks.length;j++)h+=tRow(selMember.tasks[j],true,false);
        }
      }
      h+='</div>';

    } else if(drilldown==="project"){
      // DRILL-DOWN: project cards
      var projects=groupByProject(d.tasks);
      h+='<div class="detail show"><div class="detail-hdr"><span>'+d.label+' &#8212; '+info.count+'件'+(info.mins?' / '+fmtMin(info.mins):'')+'</span><span class="detail-close" onclick="S.openBlock=null;S.openMember=null;render()">&#10005;</span></div>';
      h+='<div class="member-cards">';
      for(var pi=0;pi<projects.length;pi++){
        var p=projects[pi];
        var isOn=S.openMember==="proj_"+p.id;
        h+='<div class="m-card'+(isOn?" active":"")+'" onclick="event.stopPropagation();clickMemberCard(\'proj_'+p.id+'\')" style="min-width:140px">';
        h+='<div class="m-card-name" style="font-size:10px">'+esc(p.name)+'</div>';
        h+='<div class="m-card-row"><span class="m-card-count">'+p.count+'<span class="m-card-unit"> 件</span></span>';
        h+=(p.mins?'<span class="m-card-time">'+fmtMin(p.mins)+'</span>':'')+'</div>';
        h+='</div>';
      }
      h+='</div>';

      if(S.openMember&&S.openMember.indexOf("proj_")===0){
        var selProjId=S.openMember.replace("proj_","");
        var selProj=null;
        for(var pi=0;pi<projects.length;pi++){if(projects[pi].id===selProjId){selProj=projects[pi];break;}}
        if(selProj){
          h+='<div style="padding:6px 14px;font-size:10px;font-weight:600;color:var(--acl);background:rgba(30,64,175,.1);border-top:1px solid var(--bd);display:flex;justify-content:space-between;align-items:center"><span>'+esc(selProj.name)+' &#8212; '+selProj.count+'件'+(selProj.mins?' / '+fmtMin(selProj.mins):'')+'</span><span style="color:var(--txd);font-size:9px;cursor:pointer" onclick="event.stopPropagation();S.openMember=null;render()">&#10005; 閉じる</span></div>';
          sortTasks(selProj.tasks);
          for(var j=0;j<selProj.tasks.length;j++)h+=tRow(selProj.tasks[j],false,true);
        }
      }
      h+='</div>';

    } else {
      // DIRECT MODE: show tasks directly
      h+='<div class="detail show"><div class="detail-hdr"><span>'+d.label+' &#8212; '+info.count+'件'+(info.mins?' / '+fmtMin(info.mins):'')+'</span><span class="detail-close" onclick="S.openBlock=null;S.openMember=null;render()">&#10005;</span></div>';
      sortTasks(d.tasks);
      for(var j=0;j<d.tasks.length;j++)h+=tRow(d.tasks[j],true,true);
      h+='</div>';
    }
  }
  return h;
}

function renderSectionView(tasks,filterMode){
  // Gather all sections with their tasks
  var secData={};
  for(var i=0;i<tasks.length;i++){
    var t=tasks[i];
    var sid=t.section_id||"__nosec__";
    if(!secData[sid])secData[sid]={tasks:[],mins:0};
    secData[sid].tasks.push(t);
    secData[sid].mins+=parseMinutes(t.labels);
  }
  // Build section list
  var secList=[];
  for(var k in secData){
    var secInfo=secMap[k];
    var nm=k==="__nosec__"?"セクションなし":(secInfo?secInfo.name:"不明");
    var proj=secInfo?projMap[secInfo.project_id]:null;
    var projName=proj?proj.name:"";
    // Count date buckets
    var bk=bucketTasks(secData[k].tasks);
    secList.push({
      id:k,name:nm,projName:projName,
      tasks:secData[k].tasks,mins:secData[k].mins,count:secData[k].tasks.length,
      ovCount:bk.overdue.length,tdCount:bk.today.length,tmCount:bk.tomorrow.length
    });
  }
  secList.sort(function(a,b){return b.ovCount-a.ovCount||b.count-a.count;});

  var h='';
  // Section cards
  h+='<div class="sec-cards">';
  for(var i=0;i<secList.length;i++){
    var s=secList[i];
    var isOn=S.openSection===s.id;
    h+='<div class="sec-card'+(isOn?" active":"")+'" onclick="S.openSection=S.openSection===\''+s.id+'\'?null:\''+s.id+'\';S.secBlock=null;render()">';
    h+='<div class="sec-card-name">'+esc(s.name)+'</div>';
    if(s.projName&&filterMode!=="accg")h+='<div class="sec-card-proj">'+esc(s.projName)+'</div>';
    h+='<div class="sec-card-stats">';
    h+='<span class="sec-card-count">'+s.count+'件</span>';
    if(s.mins)h+='<span class="sec-card-time">'+fmtMin(s.mins)+'</span>';
    h+='</div>';
    var hasBadge=s.ovCount>0||s.tdCount>0;
    if(hasBadge){h+='<div class="sec-card-badges">';
    if(s.ovCount)h+='<span class="bg bg-r">超過'+s.ovCount+'</span>';
    if(s.tdCount)h+='<span class="bg bg-o">今日'+s.tdCount+'</span>';
    h+='</div>';}
    h+='</div>';
  }
  h+='</div>';

  // Expanded section: date blocks
  if(S.openSection){
    var selSec=null;
    for(var i=0;i<secList.length;i++){if(secList[i].id===S.openSection){selSec=secList[i];break;}}
    if(selSec){
      h+='<div class="sec-detail">';
      h+='<div class="sec-detail-hdr"><span>'+esc(selSec.name)+(selSec.projName&&filterMode!=="accg"?' ― '+esc(selSec.projName):'')+'</span>';
      h+='<span class="sec-detail-info">'+selSec.count+'件'+(selSec.mins?' / '+fmtMin(selSec.mins):'')+'</span>';
      h+='<span class="detail-close" onclick="S.openSection=null;S.secBlock=null;render()">&#10005;</span></div>';

      // Date blocks within this section
      var bk=bucketTasks(selSec.tasks);
      var defs=[
        {key:"overdue",label:"期限超過",cls:"block-ov",tasks:bk.overdue},
        {key:"today",label:"今日",cls:"block-td",tasks:bk.today},
        {key:"tomorrow",label:"明日",cls:"block-tm",tasks:bk.tomorrow},
        {key:"dayafter",label:"明後日",cls:"block-da",tasks:bk.dayafter},
        {key:"rest",label:"それ以降",cls:"block-ft",tasks:bk.rest}
      ];
      var maxCount=Math.max(bk.overdue.length,bk.today.length,bk.tomorrow.length,bk.dayafter.length,bk.rest.length,1);
      h+='<div class="blocks">';
      for(var i=0;i<defs.length;i++){
        var d=defs[i];var info=bucketInfo(d.tasks);
        var isActive=S.secBlock===d.key;
        var barW=maxCount>0?Math.round(info.count/maxCount*100):0;
        h+='<div class="block-card '+d.cls+(isActive?" active":"")+'" onclick="event.stopPropagation();S.secBlock=S.secBlock===\''+d.key+'\'?null:\''+d.key+'\';render()">';
        h+='<div class="block-top"><div class="block-label">'+d.label+'</div>';
        h+='<div class="block-nums"><span class="block-count">'+info.count+'</span>';
        h+=(info.mins?'<span class="block-time">'+fmtMin(info.mins)+'</span>':'<span class="block-time" style="opacity:.3">0m</span>')+'</div></div>';
        h+='<div class="block-bar"><div class="block-bar-fill" style="width:'+barW+'%"></div></div>';
        h+='</div>';
      }
      h+='</div>';

      // Task list for selected date block
      for(var i=0;i<defs.length;i++){
        var d=defs[i];
        if(S.secBlock!==d.key||!d.tasks.length)continue;
        var info=bucketInfo(d.tasks);
        h+='<div class="detail show"><div class="detail-hdr"><span>'+esc(selSec.name)+' &#8212; '+d.label+' '+info.count+'件'+(info.mins?' / '+fmtMin(info.mins):'')+'</span>';
        h+='<span class="detail-close" onclick="S.secBlock=null;render()">&#10005;</span></div>';
        sortTasks(d.tasks);
        for(var j=0;j<d.tasks.length;j++)h+=tRow(d.tasks[j],false,true);
        h+='</div>';
      }
      h+='</div>';
    }
  }
  return h;
}

function getMembers(tasks){
  var map={};
  for(var i=0;i<tasks.length;i++){
    var a=gA(tasks[i]);if(!a)continue;
    if(isExcludedMember(a))continue;
    if(!map[a])map[a]=0;map[a]++;
  }
  var result=[];
  for(var k in map){
    var c=DATA.collaborators[k];
    var nm=c?(c.name||c.full_name||c.email||"不明"):"不明";
    result.push({id:k,name:nm,count:map[k]});
  }
  result.sort(function(a,b){return b.count-a.count;});
  return result;
}

function renderWeeklyView(){
  var allTasks=DATA.all_tasks||DATA.tasks;
  var allProj={};if(DATA.all_projects)for(var i=0;i<DATA.all_projects.length;i++)allProj[DATA.all_projects[i].id]=DATA.all_projects[i];
  else allProj=projMap;
  function is40(t){var p=allProj[t.project_id];return p&&p.name&&p.name.substring(0,2)==="40";}
  var wb=getWeekBounds();
  var excl=DATA.exclude_members||[];
  function isExcl(nm){for(var i=0;i<excl.length;i++){if(nm.toLowerCase().indexOf(excl[i].toLowerCase())>=0)return true;}return false;}
  var members={};
  for(var i=0;i<allTasks.length;i++){
    var t=allTasks[i];var aid=gA(t);if(!aid)continue;
    var c=DATA.collaborators[aid];if(!c)continue;
    var nm=c.name||c.full_name||"";if(isExcl(nm))continue;
    var dd=t.due?t.due.date:null;if(!dd)continue;
    var mins=parseMinutes(t.labels);var a40=is40(t);
    if(!members[aid])members[aid]={id:aid,name:nm,tw40m:0,tw40c:0,tw40t:[],twOm:0,twOc:0,twOt:[],nw40m:0,nw40c:0,nw40t:[],nwOm:0,nwOc:0,nwOt:[]};
    var m=members[aid];
    var pn=allProj[t.project_id]?allProj[t.project_id].name:"";
    var info={content:t.content,project:pn,mins:mins,due:dd};
    if(inRange(dd,wb.thisWeek.start,wb.thisWeek.end)){
      if(a40){m.tw40m+=mins;m.tw40c++;m.tw40t.push(info);}
      else{m.twOm+=mins;m.twOc++;m.twOt.push(info);}
    }
    if(inRange(dd,wb.nextWeek.start,wb.nextWeek.end)){
      if(a40){m.nw40m+=mins;m.nw40c++;m.nw40t.push(info);}
      else{m.nwOm+=mins;m.nwOc++;m.nwOt.push(info);}
    }
  }
  var arr=[];for(var k in members)arr.push(members[k]);
  arr.sort(function(a,b){return(b.tw40c+b.twOc+b.nw40c+b.nwOc)-(a.tw40c+a.twOc+a.nw40c+a.nwOc);});
  var tot={tw40m:0,tw40c:0,twOm:0,twOc:0,nw40m:0,nw40c:0,nwOm:0,nwOc:0};
  for(var i=0;i<arr.length;i++){var m=arr[i];tot.tw40m+=m.tw40m;tot.tw40c+=m.tw40c;tot.twOm+=m.twOm;tot.twOc+=m.twOc;tot.nw40m+=m.nw40m;tot.nw40c+=m.nw40c;tot.nwOm+=m.nwOm;tot.nwOc+=m.nwOc;}
  function fmtD(d){var p=d.split("-");return parseInt(p[1])+"/"+parseInt(p[2]);}
  function cell(mins,cnt,key){
    if(cnt===0)return'<td class="wt-val">-</td>';
    var txt=mins?fmtMin(mins):'';
    txt+=(txt?' ':'')+'<span class="wt-cnt">('+cnt+'件)</span>';
    var safeKey=key.replace(/'/g,"\\'");
    return'<td class="wt-val wt-click" onclick="event.preventDefault();event.stopPropagation();S.weekDetail=S.weekDetail===\''+safeKey+'\'?null:\''+safeKey+'\';render()">'+txt+'</td>';
  }
  function detailRows(tasks,colSpan){
    if(!tasks.length)return'';
    var h='<tr class="wt-detail-row"><td colspan="'+colSpan+'"><div class="wt-detail">';
    tasks.sort(function(a,b){return a.due<b.due?-1:a.due>b.due?1:0;});
    for(var i=0;i<tasks.length;i++){
      var t=tasks[i];
      h+='<div class="wt-detail-item"><span class="wt-detail-date">'+fmtD(t.due)+'</span>';
      h+='<span class="wt-detail-content">'+esc(t.content)+'</span>';
      h+='<span class="wt-detail-proj">'+esc(t.project)+'</span>';
      if(t.mins)h+='<span class="wt-detail-min">'+fmtMin(t.mins)+'</span>';
      h+='</div>';
    }
    h+='</div></td></tr>';
    return h;
  }
  var h='<div class="weekly-view">';
  h+='<div class="weekly-period">今週: '+fmtD(wb.thisWeek.start)+' ～ '+fmtD(wb.thisWeek.end)+'　　来週: '+fmtD(wb.nextWeek.start)+' ～ '+fmtD(wb.nextWeek.end)+'</div>';
  h+='<table class="weekly-tbl"><thead>';
  h+='<tr><th class="wt-name" rowspan="2">メンバー</th>';
  h+='<th class="wt-grp" colspan="3" style="border-bottom:2px solid var(--ac)">今週</th>';
  h+='<th class="wt-grp" colspan="3" style="border-bottom:2px solid var(--pu)">来週</th></tr>';
  h+='<tr><th class="wt-sub">会計</th><th class="wt-sub">会計以外</th><th class="wt-sub wt-total">合計</th>';
  h+='<th class="wt-sub">会計</th><th class="wt-sub">会計以外</th><th class="wt-sub wt-total">合計</th></tr>';
  h+='</thead><tbody>';
  for(var i=0;i<arr.length;i++){
    var m=arr[i];
    var twT=m.tw40c+m.twOc;var nwT=m.nw40c+m.nwOc;
    if(twT===0&&nwT===0)continue;
    var twTm=m.tw40m+m.twOm;var nwTm=m.nw40m+m.nwOm;
    h+='<tr><td class="wt-name">'+esc(m.name)+'</td>';
    h+=cell(m.tw40m,m.tw40c,'tw40_'+m.id);
    h+=cell(m.twOm,m.twOc,'twO_'+m.id);
    h+='<td class="wt-val wt-total">'+(twT?((twTm?fmtMin(twTm)+' ':'')+'('+twT+'件)'):'-')+'</td>';
    h+=cell(m.nw40m,m.nw40c,'nw40_'+m.id);
    h+=cell(m.nwOm,m.nwOc,'nwO_'+m.id);
    h+='<td class="wt-val wt-total">'+(nwT?((nwTm?fmtMin(nwTm)+' ':'')+'('+nwT+'件)'):'-')+'</td>';
    h+='</tr>';
    if(S.weekDetail==='tw40_'+m.id)h+=detailRows(m.tw40t,7);
    if(S.weekDetail==='twO_'+m.id)h+=detailRows(m.twOt,7);
    if(S.weekDetail==='nw40_'+m.id)h+=detailRows(m.nw40t,7);
    if(S.weekDetail==='nwO_'+m.id)h+=detailRows(m.nwOt,7);
  }
  h+='<tr class="wt-foot"><td class="wt-name">合計</td>';
  h+='<td class="wt-val">'+(tot.tw40c?(tot.tw40m?fmtMin(tot.tw40m)+' ':'')+'('+tot.tw40c+'件)':'-')+'</td>';
  h+='<td class="wt-val">'+(tot.twOc?(tot.twOm?fmtMin(tot.twOm)+' ':'')+'('+tot.twOc+'件)':'-')+'</td>';
  var twAll=tot.tw40m+tot.twOm;var twAllC=tot.tw40c+tot.twOc;
  h+='<td class="wt-val wt-total">'+(twAllC?(twAll?fmtMin(twAll)+' ':'')+'('+twAllC+'件)':'-')+'</td>';
  h+='<td class="wt-val">'+(tot.nw40c?(tot.nw40m?fmtMin(tot.nw40m)+' ':'')+'('+tot.nw40c+'件)':'-')+'</td>';
  h+='<td class="wt-val">'+(tot.nwOc?(tot.nwOm?fmtMin(tot.nwOm)+' ':'')+'('+tot.nwOc+'件)':'-')+'</td>';
  var nwAll=tot.nw40m+tot.nwOm;var nwAllC=tot.nw40c+tot.nwOc;
  h+='<td class="wt-val wt-total">'+(nwAllC?(nwAll?fmtMin(nwAll)+' ':'')+'('+nwAllC+'件)':'-')+'</td>';
  h+='</tr></tbody></table></div>';
  return h;
}
function render(){
  var ts=DATA.tasks;
  var logoHtml=DATA.logo?'<img src="data:image/png;base64,'+DATA.logo+'" style="height:26px" alt="LOOK UP">':'<span style="font-size:16px;font-weight:800">LOOK UP</span>';

  // Header
  var modeLabel=DATA.dashboard_mode==="accounting"?" [会計]":DATA.dashboard_mode==="non-accounting"?" [会計以外]":"";
  var h='<div class="hdr">'+logoHtml+'<span class="logo-s">Dashboard v10.1'+modeLabel+'</span><span class="gen">'+DATA.generated+' | '+ts.length+' tasks</span></div>';

  // Navigation
  h+='<div class="nav">';
  h+='<span class="nav-label">VIEW</span>';
  h+='<div class="nav-group">';
  h+='<button class="nav-btn '+(S.mode==="project"?"on":"")+'" onclick="S.mode=\'project\';S.sub=\'all\';S.openBlock=null;S.openMember=null;S.openSection=null;S.secBlock=null;render()">セクション別</button>';
  h+='<button class="nav-btn '+(S.mode==="member"?"on":"")+'" onclick="S.mode=\'member\';S.sub=\'all\';S.member=\'__all__\';S.openBlock=null;S.openMember=null;render()">メンバー</button>';
  h+='<button class="nav-btn '+(S.mode==="weekly"?"on":"")+'" onclick="S.mode=\'weekly\';render()">週間予定</button>';
  h+='</div>';

  if(S.mode==="project"){
    var dm=DATA.dashboard_mode||"all";
    if(dm==="all"){
      h+='<div class="nav-sep"></div>';
      h+='<div class="nav-group">';
      h+='<button class="nav-btn '+(S.sub==="all"?"on":"")+'" onclick="S.sub=\'all\';render()">全社</button>';
      h+='<button class="nav-btn '+(S.sub==="accg"?"on":"")+'" onclick="S.sub=\'accg\';render()">会計</button>';
      h+='<button class="nav-btn '+(S.sub==="other"?"on":"")+'" onclick="S.sub=\'other\';render()">その他</button>';
      h+='</div>';
    }
  }
  if(S.mode==="member"){
    h+='<div class="nav-sep"></div>';
    h+='<div class="nav-group">';
    h+='<button class="nav-btn '+(S.sub==="all"?"on":"")+'" onclick="S.sub=\'all\';S.member=\'__all__\';S.openBlock=null;S.openMember=null;render()">全体</button>';
    h+='<button class="nav-btn '+(S.sub==="each"?"on":"")+'" onclick="S.sub=\'each\';S.openBlock=null;S.openMember=null;render()">各メンバー</button>';
    h+='</div>';
  }
  h+='</div>';

  // Member chips
  if(S.mode==="member"&&S.sub==="each"){
    var members=getMembers(ts);
    h+='<div class="member-bar">';
    for(var i=0;i<members.length;i++){
      var m=members[i];
      var isOn=S.member===m.id;
      h+='<button class="member-chip'+(isOn?" on":"")+'" onclick="S.member=\''+m.id+'\';S.openBlock=null;S.openMember=null;render()">'+esc(m.name)+' <span class="chip-count">'+m.count+'</span></button>';
    }
    // Unassigned
    var uaCount=ts.filter(function(t){return !gA(t);}).length;
    if(uaCount){
      var isOn=S.member==="__ua__";
      h+='<button class="member-chip'+(isOn?" on":"")+'" onclick="S.member=\'__ua__\';S.openBlock=null;S.openMember=null;render()">未割当 <span class="chip-count">'+uaCount+'</span></button>';
    }
    h+='</div>';
  }

  // Content
  h+='<div style="min-height:60vh">';

  // Changes alert bar
  if(DATA.changes&&DATA.changes.length){
    var postponed=0,earlier=0,removed=0,added=0;
    for(var ci=0;ci<DATA.changes.length;ci++){
      var ct=DATA.changes[ci].change_type;
      if(ct==="postponed")postponed++;
      else if(ct==="moved_earlier")earlier++;
      else if(ct==="removed")removed++;
      else if(ct==="added")added++;
    }
    h+='<div class="chg-bar" onclick="S.showChanges=!S.showChanges;render()">';
    h+='<span class="chg-bar-icon">&#9888;</span>';
    h+='<span class="chg-bar-text">期限変更を検出</span>';
    h+='<span class="chg-bar-count">'+DATA.changes.length+'</span>';
    h+='<span class="chg-bar-detail">';
    if(postponed)h+='後ろ:'+postponed+' ';
    if(earlier)h+='前:'+earlier+' ';
    if(removed)h+='削除:'+removed+' ';
    if(added)h+='追加:'+added;
    h+='</span>';
    h+='</div>';

    if(S.showChanges){
      h+='<div class="chg-panel"><div class="chg-hdr"><span>期限変更タスク (前回比)</span><span style="color:var(--txd);font-size:9px;cursor:pointer" onclick="event.stopPropagation();S.showChanges=false;render()">&#10005; 閉じる</span></div>';
      var sorted=DATA.changes.slice().sort(function(a,b){
        var ord={postponed:0,removed:1,added:2,moved_earlier:3};
        return(ord[a.change_type]||9)-(ord[b.change_type]||9);
      });
      for(var ci=0;ci<sorted.length;ci++){
        var ch=sorted[ci];
        var typeLbl,typeCls;
        if(ch.change_type==="postponed"){typeLbl="後ろ";typeCls="chg-postponed";}
        else if(ch.change_type==="moved_earlier"){typeLbl="前へ";typeCls="chg-earlier";}
        else if(ch.change_type==="removed"){typeLbl="削除";typeCls="chg-removed";}
        else{typeLbl="追加";typeCls="chg-added";}
        var secName=ch.section_id&&secMap[ch.section_id]?secMap[ch.section_id].name:"";
        var projName=projMap[ch.project_id]?projMap[ch.project_id].name:"";
        var assignee=ch.assignee_id&&DATA.collaborators[ch.assignee_id]?(DATA.collaborators[ch.assignee_id].name||DATA.collaborators[ch.assignee_id].full_name||""):"";
        h+='<div class="chg-row">';
        h+='<span class="chg-type '+typeCls+'">'+typeLbl+'</span>';
        h+='<span class="chg-content">'+esc(ch.content)+'</span>';
        if(secName)h+='<span class="tsc">'+esc(secName)+'</span>';
        if(assignee)h+='<span class="tas">'+esc(assignee)+'</span>';
        if(projName)h+='<span class="tpj">'+esc(projName)+'</span>';
        h+='<span class="chg-date-old">'+(ch.old_due?fmtD(ch.old_due):"なし")+'</span>';
        h+='<span class="chg-arrow">→</span>';
        h+='<span class="chg-date-new">'+(ch.new_due?fmtD(ch.new_due):"なし")+'</span>';
        h+='</div>';
      }
      h+='</div>';
    }
  }

  if(S.mode==="project"){
    h+='<div class="main">';
    h+=renderSectionView(ts,S.sub);
    h+='</div>';
  }

  if(S.mode==="member"&&S.sub==="all"){
    h+=renderBlocks(ts,"all","member");
  }

  if(S.mode==="member"&&S.sub==="each"){
    var memberTasks;
    if(S.member==="__all__"){
      h+='<div class="empty">上のメンバーを選択してください</div>';
    }else if(S.member==="__ua__"){
      memberTasks=ts.filter(function(t){return !gA(t);});
      h+=renderBlocks(memberTasks,"ua","project");
    }else{
      memberTasks=ts.filter(function(t){return gA(t)===S.member;});
      h+=renderBlocks(memberTasks,"m"+S.member,"project");
    }
  }

  if(S.mode==="weekly"){
    h+='<div class="main">';
    h+=renderWeeklyView();
    h+='</div>';
  }

  h+='</div>';
  document.getElementById("app").innerHTML=h;
}
render();
</script></body></html>'''

def save_snapshot(tasks):
    """Save current task state for future comparison."""
    get_snapshot_dir().mkdir(parents=True, exist_ok=True)
    snapshot = {}
    for t in tasks:
        if not isinstance(t, dict): continue
        tid = t.get("id")
        if not tid: continue
        snapshot[str(tid)] = {
            "content": t.get("content",""),
            "due": t.get("due",{}).get("date") if isinstance(t.get("due"), dict) else None,
            "is_recurring": t.get("due",{}).get("is_recurring", False) if isinstance(t.get("due"), dict) else False,
            "project_id": t.get("project_id"),
            "section_id": t.get("section_id"),
            "assignee_id": str(t.get("assignee_id") or t.get("responsible_uid") or ""),
            "priority": t.get("priority",1),
        }
    today_str = date.today().isoformat()
    filepath = get_snapshot_dir() / f"snapshot_{today_str}.json"
    filepath.write_text(json.dumps(snapshot, ensure_ascii=False))
    # Keep only last 14 days of snapshots
    for f in sorted(get_snapshot_dir().glob("snapshot_*.json"))[:-14]:
        f.unlink()
    return filepath

def load_previous_snapshot():
    """Load the most recent snapshot before today."""
    if not get_snapshot_dir().exists(): return None, None
    today_str = date.today().isoformat()
    files = sorted(get_snapshot_dir().glob("snapshot_*.json"))
    for f in reversed(files):
        snap_date = f.stem.replace("snapshot_","")
        if snap_date < today_str:
            return json.loads(f.read_text()), snap_date
    return None, None

def compare_snapshots(old_snap, new_tasks):
    """Compare old snapshot with current tasks. Detect due date changes.
    Skips recurring tasks (date changes from completion, not postponement)."""
    if not old_snap: return []
    changes = []
    for t in new_tasks:
        if not isinstance(t, dict): continue
        tid = str(t.get("id",""))
        if tid not in old_snap: continue
        # Skip recurring tasks — their dates change automatically on completion
        is_recurring_now = t.get("due",{}).get("is_recurring", False) if isinstance(t.get("due"), dict) else False
        is_recurring_old = old_snap[tid].get("is_recurring", False)
        if is_recurring_now or is_recurring_old:
            continue
        old = old_snap[tid]
        new_due = t.get("due",{}).get("date") if isinstance(t.get("due"), dict) else None
        old_due = old.get("due")
        if old_due != new_due:
            change_type = "none"
            if old_due and new_due:
                if new_due > old_due: change_type = "postponed"
                elif new_due < old_due: change_type = "moved_earlier"
                else: change_type = "changed"
            elif old_due and not new_due: change_type = "removed"
            elif not old_due and new_due: change_type = "added"
            changes.append({
                "task_id": tid,
                "content": t.get("content",""),
                "project_id": t.get("project_id"),
                "section_id": t.get("section_id"),
                "assignee_id": str(t.get("assignee_id") or t.get("responsible_uid") or ""),
                "old_due": old_due,
                "new_due": new_due,
                "change_type": change_type,
                "priority": t.get("priority",1),
            })
    return changes

def deploy_github(html_content, filename="index.html"):
    """Deploy HTML to GitHub Pages."""
    cfg = get_config()
    gh_token = cfg.get("github_token", "")
    gh_user = cfg.get("github_user", "")
    gh_repo = cfg.get("github_repo", "lookup-dashboard")
    if not gh_token or not gh_user:
        return None

    import base64 as b64mod
    url = f"https://api.github.com/repos/{gh_user}/{gh_repo}/contents/{filename}"

    # First, get current file SHA (needed for update)
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {gh_token}",
        "Accept": "application/vnd.github+json"
    })
    sha = None
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context()) as r:
            data = json.loads(r.read())
            sha = data.get("sha")
    except urllib.error.HTTPError:
        pass  # File doesn't exist yet, that's OK

    # Upload/update file
    payload = {
        "message": f"Dashboard update {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "content": b64mod.b64encode(html_content.encode("utf-8")).decode("ascii"),
    }
    if sha:
        payload["sha"] = sha

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="PUT", headers={
        "Authorization": f"Bearer {gh_token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json"
    })
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context()) as r:
            return f"https://{gh_user}.github.io/{gh_repo}/{filename}"
    except urllib.error.HTTPError as e:
        print(f"    GitHub APIエラー: {e.code} {e.read().decode()[:200]}")
        return None

def slack_post(bot_token, channel, text, thread_ts=None):
    """Post message via Slack Bot Token API. Returns message ts."""
    payload = {"channel": channel, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(f"{SLACK_API}/chat.postMessage", data=data, headers={
        "Authorization": f"Bearer {bot_token}",
        "Content-Type": "application/json; charset=utf-8"
    })
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context()) as r:
            resp = json.loads(r.read())
            if resp.get("ok"):
                return resp.get("ts")
            else:
                print(f"    Slack APIエラー: {resp.get('error','unknown')}")
                return None
    except Exception as e:
        print(f"    Slack通信エラー: {e}")
        return None

def call_claude(api_key, prompt, max_tokens=500):
    """Call Anthropic API to generate coaching comment."""
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(ANTHROPIC_API, data=data, headers={
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    })
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context()) as r:
            resp = json.loads(r.read())
            for block in resp.get("content", []):
                if block.get("type") == "text":
                    return block["text"]
    except Exception as e:
        print(f"    Claude APIエラー: {e}")
    return None

def build_member_data(tasks, changes, collabs, projects, sections):
    """Build per-member task summary for coaching."""
    import re as re_mod
    td = date.today().isoformat()
    tm = (date.today() + timedelta(days=1)).isoformat()
    proj_map = {p["id"]:p for p in projects if isinstance(p,dict)}
    sec_map = {s["id"]:s for s in sections if isinstance(s,dict)}

    def is_excluded(aid):
        if not aid: return False
        c = collabs.get(aid, collabs.get(str(aid)))
        if not c: return False
        nm = (c.get("name") or c.get("full_name") or "").lower()
        return any(ex.lower() in nm for ex in EXCLUDE_MEMBERS)

    def parse_min(labels):
        if not labels: return 0
        total = 0
        for lb in labels:
            lb = lb.lower().lstrip("@")
            if lb == "lessthan5minutes": total += 5; continue
            m = re_mod.match(r"^(\d+)\s*minutes?$", lb)
            if m: total += int(m.group(1)); continue
            m = re_mod.match(r"^(\d+)\s*hours?$", lb)
            if m: total += int(m.group(1))*60; continue
        return total

    def fmt_min(m):
        if m >= 60:
            h = m // 60; r = m % 60
            return f"{h}h{r}m" if r else f"{h}h"
        return f"{m}m"

    def days_overdue(d):
        try:
            y,mo,dy = d.split("-")
            diff = (date.today() - date(int(y),int(mo),int(dy))).days
            return max(0, diff)
        except: return 0

    postponed_ids = set()
    if changes:
        for c in changes:
            if c.get("change_type") == "postponed":
                postponed_ids.add(c.get("task_id"))

    member_data = {}
    for t in tasks:
        if not isinstance(t, dict): continue
        aid = str(t.get("assignee_id") or t.get("responsible_uid") or "")
        if not aid or is_excluded(aid): continue
        if aid not in member_data:
            c = collabs.get(aid, collabs.get(str(aid), {}))
            nm = c.get("name") or c.get("full_name") or "不明"
            member_data[aid] = {"name":nm, "overdue":[],"today":[],"tomorrow":[],"total_min":0}
        md = member_data[aid]
        dd = t.get("due",{}).get("date","") if isinstance(t.get("due"),dict) else ""
        mins = parse_min(t.get("labels"))
        md["total_min"] += mins
        sec_name = sec_map.get(t.get("section_id"),{}).get("name","")
        proj_name = proj_map.get(t.get("project_id"),{}).get("name","")
        tid = str(t.get("id",""))
        task_info = {
            "content": t.get("content",""),
            "section": sec_name,
            "project": proj_name,
            "mins": mins,
            "mins_str": fmt_min(mins) if mins else "",
            "priority": t.get("priority",1),
            "due": dd,
            "days_ov": days_overdue(dd) if dd and dd < td else 0,
            "postponed": tid in postponed_ids,
        }
        if dd and dd < td: md["overdue"].append(task_info)
        elif dd == td: md["today"].append(task_info)
        elif dd == tm: md["tomorrow"].append(task_info)

    # Sort by overdue count desc
    members = sorted(member_data.values(),
        key=lambda x: (len(x["overdue"]), x["total_min"]), reverse=True)

    # Calculate scores
    for m in members:
        ov_count = len(m["overdue"])
        postponed_count = sum(1 for t in m["overdue"] if t["postponed"])
        score = 100 - (ov_count * 10) - (postponed_count * 3)
        m["score"] = max(0, min(100, int(score)))

    return members

def build_summary_message(tasks, changes, sec_map, members=None, dashboard_url=None):
    """Build parent summary message with score ranking."""
    td = date.today().isoformat()
    tm = (date.today() + timedelta(days=1)).isoformat()

    def fmtD_short(d):
        if not d: return ""
        try:
            y,m,day = d.split("-")
            t = date(int(y),int(m),int(day))
            w = ["月","火","水","木","金","土","日"]
            return f"{int(m)}/{int(day)}({w[t.weekday()]})"
        except: return d

    def fmt_min(m):
        if m >= 60:
            h = m // 60; r = m % 60
            return f"{h}h{r}m" if r else f"{h}h"
        return f"{m}m"

    total = len(tasks)
    overdue = sum(1 for t in tasks if isinstance(t,dict) and t.get("due") and isinstance(t["due"],dict) and (t["due"].get("date","") or "") < td and t["due"].get("date",""))
    today_count = sum(1 for t in tasks if isinstance(t,dict) and t.get("due") and isinstance(t["due"],dict) and t["due"].get("date","") == td)
    tomorrow_count = sum(1 for t in tasks if isinstance(t,dict) and t.get("due") and isinstance(t["due"],dict) and t["due"].get("date","") == tm)

    now = datetime.now().strftime("%m/%d %H:%M")
    td_name = fmtD_short(td)
    lines = [
        f":bar_chart:  *LOOK UP タスクダッシュボード*　{td_name} {now}",
        "",
        f":red_circle: 期限超過 *{overdue}件*　　:large_blue_circle: 今日 *{today_count}件*　　:white_circle: 明日 *{tomorrow_count}件*　　全 *{total}件*",
    ]

    if changes:
        postponed = sum(1 for c in changes if c["change_type"]=="postponed")
        if postponed:
            lines.append("")
            lines.append(f":warning:  *後ろ倒し {postponed}件*")
            for c in [c for c in changes if c["change_type"]=="postponed"][:5]:
                sec_name = sec_map.get(c.get("section_id"),{}).get("name","")
                sec_str = f"  {sec_name}" if sec_name else ""
                lines.append(f"　　{c.get('content','')}{sec_str}　{fmtD_short(c['old_due'])} → {fmtD_short(c['new_due'])}")

    if members:
        sorted_by_score = sorted(members, key=lambda x: x.get("score",0), reverse=True)
        lines.append("")
        lines.append("*:trophy: スコア*")
        rank_lines = []
        for i, m in enumerate(sorted_by_score):
            nm = m["name"]
            if len(nm) > 12: nm = nm[:12]
            score = m.get("score", 0)
            ov_count = len(m["overdue"])
            td_count = len(m["today"])
            # Calculate overdue time and today time separately
            ov_min = sum(t.get("mins",0) for t in m["overdue"])
            td_min = sum(t.get("mins",0) for t in m["today"])
            # Line 1: rank, name, score
            rank_lines.append(f"{i+1} {nm:<12s} {score:>3d}点")
            # Line 2: overdue info + today info
            parts = []
            if ov_count:
                ov_time = f" {fmt_min(ov_min)}" if ov_min else ""
                parts.append(f"超過{ov_count}{ov_time}")
            if td_count:
                td_time = f" {fmt_min(td_min)}" if td_min else ""
                parts.append(f"今日{td_count}{td_time}")
            if parts:
                rank_lines.append("  " + "  ".join(parts))
            else:
                rank_lines.append("  -")
            # Separator at 50 point boundary
            if i < len(sorted_by_score) - 1:
                next_score = sorted_by_score[i+1].get("score", 0)
                if score >= 50 and next_score < 50:
                    rank_lines.append("─" * 22)
        lines.append("```" + "\n".join(rank_lines) + "```")

    if dashboard_url:
        lines.append(f":computer:  <{dashboard_url}|ダッシュボードを開く>")

    lines.append("")
    lines.append("_Yukikoが各メンバーへのコメントをスレッドにまとめています :thread:_")

    return "\n".join(lines)

def generate_coaching(api_key, member):
    """Use Claude to generate a coaching comment for one member."""
    name = member["name"]
    ov = member["overdue"]
    td = member["today"]
    tm = member["tomorrow"]
    total_min = member["total_min"]

    # Build task list for prompt (top items only for focused comment)
    task_lines = []
    for t in sorted(ov, key=lambda x: x["days_ov"], reverse=True)[:5]:
        postponed_mark = " ※後ろ倒し" if t["postponed"] else ""
        task_lines.append(f"  超過{t['days_ov']}日: {t['content']} {t['section']} {t['mins_str']}{postponed_mark}")
    for t in sorted(td, key=lambda x: x["priority"], reverse=True)[:3]:
        task_lines.append(f"  今日: {t['content']} {t['section']} {t['mins_str']}")
    for t in sorted(tm, key=lambda x: x["priority"], reverse=True)[:2]:
        task_lines.append(f"  明日: {t['content']} {t['section']} {t['mins_str']}")

    if not task_lines:
        return None

    tasks_text = "\n".join(task_lines)

    score = member.get("score", 0)

    prompt = f"""あなたはYukikoという名前の会計事務所のAIマネージャーです。メンバーへの簡潔なタスク管理コメントを日本語で書いてください。

{name}さん（スコア: {score}/100）
超過: {len(ov)}件 / 今日: {len(td)}件 / 明日: {len(tm)}件

{tasks_text}

ルール:
- 2行以内で簡潔に（80文字以内が理想）
- 「〜から着手がおすすめです」のような提案型
- 後ろ倒しタスクは特に指摘
- 具体的なタスク名を1-2個挙げる
- スコアが低い人には改善方法を提案（不要タスクの完了処理など）
- スコアが高い人には短く認める
- 余計な挨拶や応援は不要。事実と提案だけ
- 絵文字は使わない
- 末尾に「― Yukiko」と署名する"""

    return call_claude(api_key, prompt, max_tokens=150)

def send_slack_with_coaching(tasks, changes, collabs, projects, sections, dashboard_url=None):
    """Post summary to Slack channel, then per-member coaching in thread."""
    cfg = get_config()
    bot_token = cfg.get("slack_bot_token", "")
    channel_id = cfg.get("slack_channel_id", "")
    anthropic_key = cfg.get("anthropic_key", "")
    if not bot_token or not channel_id:
        return False

    sec_map = {s["id"]:s for s in sections if isinstance(s,dict)}

    # 1. Build member data first (needed for score ranking in summary)
    members = build_member_data(tasks, changes, collabs, projects, sections)

    # 2. Post parent summary with score ranking
    summary = build_summary_message(tasks, changes, sec_map, members=members, dashboard_url=dashboard_url)
    parent_ts = slack_post(bot_token, channel_id, summary)
    if not parent_ts:
        print("    親メッセージ投稿失敗")
        return False
    print(f"    親メッセージ投稿完了 (ts={parent_ts})")

    # 3. Post thread replies per member (sorted by score, low first = most urgent)
    sorted_members = sorted(members, key=lambda x: x.get("score",0))

    def fmt_min(m):
        if m >= 60:
            h = m // 60; r = m % 60
            return f"{h}h{r}m" if r else f"{h}h"
        return f"{m}m"

    for member in sorted_members:
        if not member["overdue"] and not member["today"]:
            continue

        name = member["name"]
        score = member.get("score", 0)
        ov_count = len(member["overdue"])
        td_count = len(member["today"])
        tm_count = len(member["tomorrow"])

        # Score icon
        if score >= 80: score_icon = ":chart_with_upwards_trend:"
        elif score >= 50: score_icon = ""
        elif score >= 30: score_icon = ":chart_with_downwards_trend:"
        else: score_icon = ":rotating_light:"

        # Status parts
        status_parts = []
        if ov_count: status_parts.append(f"超過{ov_count}")
        if td_count: status_parts.append(f"今日{td_count}")
        if tm_count: status_parts.append(f"明日{tm_count}")
        time_str = f"　計 *{fmt_min(member['total_min'])}*" if member['total_min'] else ""

        # Build thread message
        lines = [
            "━━━━━━━━━━━━━━━━━━━━",
            f"*{name}さん　　スコア {score}/100* {score_icon}",
            "━━━━━━━━━━━━━━━━━━━━",
        ]

        # Status line
        status_line = ""
        if ov_count: status_line += f":red_circle: *超過{ov_count}件*　"
        if td_count: status_line += f":large_blue_circle: 今日{td_count}　"
        if tm_count: status_line += f":white_circle: 明日{tm_count}　"
        status_line += time_str
        lines.append(status_line.strip())
        lines.append("")

        # Task list
        for t in sorted(member["overdue"], key=lambda x: x["days_ov"], reverse=True)[:3]:
            postponed_mark = " :warning:" if t["postponed"] else ""
            if t["days_ov"] >= 30:
                icon = ":rotating_light:"
            else:
                icon = ":red_circle:"
            mins_str = f"　{t['mins_str']}" if t['mins_str'] else ""
            lines.append(f"　{icon} {t['content']}　{t['section']}{mins_str}　超過{t['days_ov']}日{postponed_mark}")
        for t in sorted(member["today"], key=lambda x: x["priority"], reverse=True)[:2]:
            mins_str = f"　{t['mins_str']}" if t['mins_str'] else ""
            lines.append(f"　:large_blue_circle: {t['content']}　{t['section']}{mins_str}")

        thread_text = "\n".join(lines)

        # Generate Claude coaching comment
        if anthropic_key:
            print(f"    {name}さんのコメント生成中...")
            coaching = generate_coaching(anthropic_key, member)
            if coaching:
                thread_text += f"\n\n_{coaching}_"

        slack_post(bot_token, channel_id, thread_text, thread_ts=parent_ts)
        print(f"    {name}さん → スレッド投稿完了 (スコア:{score})")

    return True

def gen(projects, sections, tasks, collabs, logo_b64, changes=None, mode="all", all_tasks=None, all_projects=None):
    now = datetime.now().strftime("%Y/%m/%d %H:%M")
    today = date.today()
    for t in (all_tasks or tasks):
        if isinstance(t, dict) and "assignee_id" not in t and "responsible_uid" in t:
            t["assignee_id"] = t["responsible_uid"]
    data = {"projects":projects,"sections":sections,"tasks":tasks,
            "collaborators":collabs,"generated":now,
            "today":today.isoformat(),
            "tomorrow":(today+timedelta(days=1)).isoformat(),
            "dayafter":(today+timedelta(days=2)).isoformat(),
            "logo":logo_b64,
            "exclude_members":EXCLUDE_MEMBERS,
            "dashboard_mode": mode,
            "all_tasks": all_tasks or tasks,
            "all_projects": all_projects or projects,
            "changes":changes or []}
    # Escape </ in JSON to prevent HTML parser from closing <script> tag prematurely
    json_str = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", json_str)
    return html.replace("__ACCG_PREFIX__", ACCG_PREFIX)

def slack_bot_post(bot_token, channel, text, thread_ts=None):
    """Post message via Slack Bot Token. Returns message ts."""
    payload = {"channel": channel, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request("https://slack.com/api/chat.postMessage", data=data, headers={
        "Authorization": f"Bearer {bot_token}",
        "Content-Type": "application/json; charset=utf-8"
    })
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context()) as r:
            resp = json.loads(r.read())
            if resp.get("ok"):
                return resp.get("ts")
            else:
                print(f"    Slack APIエラー: {resp.get('error')}")
                return None
    except Exception as e:
        print(f"    Slack通信エラー: {e}")
        return None

def generate_coaching_comment(anthropic_key, member_name, member_data, sec_map):
    """Call Claude API to generate a coaching comment for a member."""
    td = date.today().isoformat()

    def fmt_min(m):
        if m >= 60:
            h = m // 60; r = m % 60
            return f"{h}h{r}m" if r else f"{h}h"
        return f"{m}m"

    # Build context about this member's tasks
    task_lines = []
    for category, label in [("overdue","期限超過"), ("today","今日期限"), ("tomorrow","明日期限")]:
        tasks = member_data.get(category, [])
        if not tasks: continue
        task_lines.append(f"\n【{label}】")
        for t in tasks:
            sec_name = t.get("section","")
            sec_str = f" [{sec_name}]" if sec_name else ""
            time_str = f" ({fmt_min(t['mins'])})" if t.get("mins") else ""
            ov_str = f" 超過{t['days_ov']}日" if t.get("days_ov") else ""
            post_str = " ※後ろ倒し検出" if t.get("postponed") else ""
            task_lines.append(f"  - {t['content']}{sec_str}{time_str}{ov_str}{post_str}")

    if not task_lines:
        return None

    task_context = "\n".join(task_lines)
    total_min = member_data.get("total_min", 0)
    time_str = fmt_min(total_min) if total_min else "不明"

    prompt = f"""あなたは会計事務所のタスク管理AIアシスタントです。
以下のメンバーのタスク状況を見て、業務的で簡潔なコメントを日本語で書いてください。

ルール:
- 2〜3行で簡潔に（最大100文字程度）
- 優先すべきタスクの順序を提案
- 超過タスクがあれば、そこから着手することを促す
- 後ろ倒しが検出されたタスクには注意を促す
- 時間見積もりがある場合、効率的な順序を提案（短いものから片付ける等）
- 敬語を使い、温かみのあるトーンで（指示ではなく提案）
- 「〜しましょう」「〜がおすすめです」のような柔らかい表現
- メンバー名は不要（投稿先で分かるため）

メンバー: {member_name}
合計見積もり時間: {time_str}
{task_context}
"""

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=payload, headers={
        "x-api-key": anthropic_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    })
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context()) as r:
            resp = json.loads(r.read())
            for block in resp.get("content", []):
                if block.get("type") == "text":
                    return block["text"].strip()
    except Exception as e:
        print(f"    Claude APIエラー ({member_name}): {e}")
    return None

def send_slack_with_threads(tasks, changes, collabs, projects, sections, dashboard_url=None):
    """Post summary to channel, then per-member coaching as thread replies."""
    import re as re_mod
    cfg = get_config()
    bot_token = cfg.get("slack_bot_token", "")
    channel_id = cfg.get("slack_channel_id", "")
    anthropic_key = cfg.get("anthropic_key", "")
    webhook_url = cfg.get("slack_webhook", "")

    if not bot_token or not channel_id:
        # Fall back to webhook-only (no threads)
        if webhook_url:
            payload = json.dumps({"text": "ダッシュボード更新（Bot Token未設定のためサマリーのみ）"}).encode("utf-8")
            req = urllib.request.Request(webhook_url, data=payload, headers={"Content-Type":"application/json"})
            try:
                urllib.request.urlopen(req, context=ssl.create_default_context())
                return True
            except: pass
        return False

    td = date.today().isoformat()
    tm = (date.today() + timedelta(days=1)).isoformat()
    proj_map = {p["id"]:p for p in projects if isinstance(p,dict)}
    sec_map_local = {s["id"]:s for s in sections if isinstance(s,dict)}

    def is_excluded(aid):
        if not aid: return False
        c = collabs.get(aid, collabs.get(str(aid)))
        if not c: return False
        nm = (c.get("name") or c.get("full_name") or "").lower()
        return any(ex.lower() in nm for ex in EXCLUDE_MEMBERS)

    def parse_min(labels):
        if not labels: return 0
        total = 0
        for lb in labels:
            lb = lb.lower().lstrip("@")
            if lb == "lessthan5minutes": total += 5; continue
            m = re_mod.match(r"^(\d+)\s*minutes?$", lb)
            if m: total += int(m.group(1)); continue
            m = re_mod.match(r"^(\d+)\s*hours?$", lb)
            if m: total += int(m.group(1))*60; continue
        return total

    def fmt_min(m):
        if m >= 60:
            h = m // 60; r = m % 60
            return f"{h}h{r}m" if r else f"{h}h"
        return f"{m}m"

    def days_overdue(d):
        if not d: return 0
        try:
            y,mo,day = d.split("-")
            diff = (date.today() - date(int(y),int(mo),int(day))).days
            return max(0, diff)
        except: return 0

    # --- Build parent message (same as before) ---
    total = len(tasks)
    overdue = sum(1 for t in tasks if isinstance(t,dict) and t.get("due") and isinstance(t["due"],dict) and (t["due"].get("date","") or "") < td and t["due"].get("date",""))
    today_count = sum(1 for t in tasks if isinstance(t,dict) and t.get("due") and isinstance(t["due"],dict) and t["due"].get("date","") == td)
    tomorrow_count = sum(1 for t in tasks if isinstance(t,dict) and t.get("due") and isinstance(t["due"],dict) and t["due"].get("date","") == tm)

    now = datetime.now().strftime("%Y/%m/%d %H:%M")
    lines = [
        f":bar_chart: *LOOK UP タスクダッシュボード* ({now}更新)",
        "━━━━━━━━━━━━━━━━━━━━",
        f"全タスク: *{total}件*",
        f":red_circle: 期限超過: *{overdue}件*" if overdue else ":large_green_circle: 期限超過: 0件",
        f":orange_circle: 今日期限: *{today_count}件*",
        f":yellow_circle: 明日期限: *{tomorrow_count}件*",
    ]

    if changes:
        postponed_c = sum(1 for c in changes if c["change_type"]=="postponed")
        earlier_c = sum(1 for c in changes if c["change_type"]=="moved_earlier")
        removed_c = sum(1 for c in changes if c["change_type"]=="removed")
        added_c = sum(1 for c in changes if c["change_type"]=="added")
        lines.append("")
        lines.append(f":warning: *期限変更: {len(changes)}件* (後ろ:{postponed_c} / 前:{earlier_c} / 削除:{removed_c} / 追加:{added_c})")
        for c in [c for c in changes if c["change_type"]=="postponed"][:5]:
            sec_name = sec_map_local.get(c.get("section_id"),{}).get("name","")
            sec_str = f" [{sec_name}]" if sec_name else ""
            lines.append(f"  :arrow_right: {c.get('content','')}{sec_str} `{c['old_due']}` → `{c['new_due']}`")

    # Member summary lines (inline)
    member_ov_map = {}
    for t in tasks:
        if not isinstance(t, dict): continue
        dd = t.get("due",{}).get("date","") if isinstance(t.get("due"),dict) else ""
        if not dd or dd >= td: continue
        aid = str(t.get("assignee_id") or t.get("responsible_uid") or "")
        if not aid or is_excluded(aid): continue
        if aid not in member_ov_map: member_ov_map[aid] = {"count":0,"mins":0}
        member_ov_map[aid]["count"] += 1
        member_ov_map[aid]["mins"] += parse_min(t.get("labels"))
    if member_ov_map:
        lines.append("")
        lines.append("*メンバー別 期限超過:*")
        for aid, info in sorted(member_ov_map.items(), key=lambda x: x[1]["mins"], reverse=True)[:8]:
            c = collabs.get(aid, collabs.get(str(aid), {}))
            nm = c.get("name") or c.get("full_name") or "不明"
            time_str = f" ({fmt_min(info['mins'])})" if info["mins"] else ""
            lines.append(f"  {nm}: {info['count']}件{time_str}")

    if dashboard_url:
        lines.append("")
        lines.append(f":computer: <{dashboard_url}|ダッシュボードを開く>")

    parent_text = "\n".join(lines)

    # --- Post parent message ---
    print("    親メッセージ投稿中...")
    parent_ts = slack_bot_post(bot_token, channel_id, parent_text)
    if not parent_ts:
        print("    親メッセージ投稿失敗。")
        # Try webhook as fallback
        if webhook_url:
            payload = json.dumps({"text": parent_text}).encode("utf-8")
            req = urllib.request.Request(webhook_url, data=payload, headers={"Content-Type":"application/json"})
            try:
                urllib.request.urlopen(req, context=ssl.create_default_context())
                print("    Webhookで投稿しました（スレッドなし）")
                return True
            except: pass
        return False

    # --- Generate and post thread replies (Claude coaching) ---
    if not anthropic_key:
        print("    Anthropic APIキーなし。スレッド投稿スキップ。")
        return True

    # Build per-member data
    postponed_ids = set()
    if changes:
        for c in changes:
            if c.get("change_type") == "postponed":
                postponed_ids.add(c.get("task_id"))

    member_buckets = {}
    for t in tasks:
        if not isinstance(t, dict): continue
        aid = str(t.get("assignee_id") or t.get("responsible_uid") or "")
        if not aid or is_excluded(aid): continue
        if aid not in member_buckets:
            member_buckets[aid] = {"overdue":[],"today":[],"tomorrow":[],"total_min":0}
        mb = member_buckets[aid]
        dd = t.get("due",{}).get("date","") if isinstance(t.get("due"),dict) else ""
        mins = parse_min(t.get("labels"))
        mb["total_min"] += mins
        sec_name = sec_map_local.get(t.get("section_id"),{}).get("name","")
        tid = str(t.get("id",""))
        info = {"content":t.get("content",""),"section":sec_name,"mins":mins,
                "priority":t.get("priority",1),"due":dd,
                "days_ov":days_overdue(dd) if dd and dd < td else 0,
                "postponed":tid in postponed_ids}
        if dd and dd < td: mb["overdue"].append(info)
        elif dd == td: mb["today"].append(info)
        elif dd == tm: mb["tomorrow"].append(info)

    # Sort by urgency
    sorted_members = sorted(member_buckets.items(),
        key=lambda x: (len(x[1]["overdue"]), x[1]["total_min"]), reverse=True)

    # Only members with overdue or today tasks
    active_members = [(aid, mb) for aid, mb in sorted_members
                      if mb["overdue"] or mb["today"]]

    print(f"    コーチングコメント生成中... ({len(active_members)}名)")
    for aid, mb in active_members:
        c = collabs.get(aid, collabs.get(str(aid), {}))
        name = c.get("name") or c.get("full_name") or "不明"

        comment = generate_coaching_comment(anthropic_key, name, mb, sec_map_local)
        if not comment:
            continue

        # Build thread reply
        ov_count = len(mb["overdue"])
        td_count = len(mb["today"])
        status_parts = []
        if ov_count: status_parts.append(f"超過{ov_count}")
        if td_count: status_parts.append(f"今日{td_count}")
        time_str = f" | {fmt_min(mb['total_min'])}" if mb["total_min"] else ""
        status = " / ".join(status_parts) + time_str

        thread_text = f":robot_face: *{name}*  {status}\n{comment}"
        slack_bot_post(bot_token, channel_id, thread_text, thread_ts=parent_ts)
        print(f"      {name}: 投稿完了")

    return True

def is_ci():
    """Check if running in CI (GitHub Actions)."""
    return os.environ.get("CI") == "true"

def get_config():
    """Get config from env vars (CI) or config file (local)."""
    if is_ci():
        return {
            "token": os.environ.get("TODOIST_TOKEN", ""),
            "slack_bot_token": os.environ.get("SLACK_BOT_TOKEN", ""),
            "slack_channel_id": os.environ.get("SLACK_CHANNEL_ID", ""),
            "slack_webhook": os.environ.get("SLACK_WEBHOOK", ""),
            "anthropic_key": os.environ.get("ANTHROPIC_KEY", ""),
            "github_token": os.environ.get("GH_PAT", ""),
            "github_user": os.environ.get("GH_USER", ""),
            "github_repo": os.environ.get("GH_REPO", "lookup-dashboard"),
        }
    else:
        cfg = load_cfg()
        # Local mode: override channel based on mode
        mode = get_mode()
        if mode == "accounting" and cfg.get("slack_channel_accounting"):
            cfg["slack_channel_id"] = cfg["slack_channel_accounting"]
        elif mode == "non-accounting" and cfg.get("slack_channel_non_accounting"):
            cfg["slack_channel_id"] = cfg["slack_channel_non_accounting"]
        return cfg

def main():
    mode = get_mode()
    mode_labels = {"all": "全体", "accounting": "会計", "non-accounting": "会計以外"}
    mode_label = mode_labels.get(mode, mode)

    print("\n" + "="*50)
    print("  LOOK UP Todoist Dashboard v10")
    print(f"  Mode: {'CI' if is_ci() else 'Local'} / {mode_label}")
    print("="*50)

    cfg = get_config()

    # --- LOCAL MODE: Interactive setup ---
    if not is_ci():
        tok = cfg.get("token","")
        if not tok:
            print("\nTodoist APIトークンを入力:")
            tok = input("  > ").strip()
            if not tok: print("中止"); sys.exit(1)
            cfg["token"] = tok; save_cfg(cfg)

        if "slack_bot_token" not in cfg:
            print("\n  Slack Bot Token (xoxb-...) を入力 (スキップはEnter):")
            bt = input("  > ").strip()
            if bt:
                cfg["slack_bot_token"] = bt
                print("  チャンネルIDを入力:")
                ch = input("  > ").strip()
                cfg["slack_channel_id"] = ch
            else:
                cfg["slack_bot_token"] = ""; cfg["slack_channel_id"] = ""
            save_cfg(cfg)

        if "anthropic_key" not in cfg:
            print("\n  Anthropic APIキー (スキップはEnter):")
            ak = input("  > ").strip()
            cfg["anthropic_key"] = ak or ""
            save_cfg(cfg)

        if "github_token" not in cfg:
            print("\n  GitHub Token (スキップはEnter):")
            gt = input("  > ").strip()
            if gt:
                print("  GitHubユーザー名:"); gu = input("  > ").strip()
                print("  リポジトリ名 (default: lookup-dashboard):"); gr = input("  > ").strip() or "lookup-dashboard"
                cfg["github_token"] = gt; cfg["github_user"] = gu; cfg["github_repo"] = gr
            else:
                cfg["github_token"] = ""; cfg["github_user"] = ""; cfg["github_repo"] = ""
            save_cfg(cfg)

    # --- Common: show status ---
    tok = cfg.get("token","")
    if not tok: print("  ERROR: Todoist token missing"); sys.exit(1)
    print(f"\n  Todoist: {tok[:4]}****{tok[-4:]}")
    if cfg.get("slack_bot_token"): print(f"  Slack: ON")
    if cfg.get("anthropic_key"): print("  Claude: ON")
    if cfg.get("github_token"): print(f"  GitHub: ON")
    print()

    # --- Fetch data ---
    projects, sections, tasks, collabs = fetch(tok)

    # Save unfiltered data for weekly view (needs both accounting and non-accounting)
    all_tasks = list(tasks)
    all_projects = list(projects)

    # --- Mode filtering ---
    projects, sections, tasks = filter_by_mode(projects, sections, tasks, mode)

    td = date.today().isoformat()
    ov = sum(1 for t in tasks if isinstance(t,dict) and t.get("due") and isinstance(t["due"],dict) and t["due"].get("date","") < td)
    print(f"\n  合計: {len(tasks)}タスク / {ov}件超過 （{mode_label}）")

    # --- Snapshot comparison (mode-specific) ---
    print("  スナップショット比較中...")
    old_snap, snap_date = load_previous_snapshot()
    changes = []
    if old_snap:
        changes = compare_snapshots(old_snap, tasks)
        # Filter out changes from excluded members
        def is_excluded_change(c):
            aid = c.get("assignee_id", "")
            if not aid: return False
            col = collabs.get(aid, collabs.get(str(aid), {}))
            nm = (col.get("name") or col.get("full_name") or "").lower()
            return any(ex.lower() in nm for ex in EXCLUDE_MEMBERS)
        changes = [c for c in changes if not is_excluded_change(c)]
        postponed = sum(1 for c in changes if c["change_type"]=="postponed")
        earlier = sum(1 for c in changes if c["change_type"]=="moved_earlier")
        removed = sum(1 for c in changes if c["change_type"]=="removed")
        added = sum(1 for c in changes if c["change_type"]=="added")
        print(f"    前回: {snap_date} ({len(old_snap)}タスク)")
        print(f"    期限変更: {len(changes)}件 (後ろ:{postponed} 前:{earlier} 削除:{removed} 追加:{added})")
    else:
        print("    前回のスナップショットなし（初回実行）。")
    save_snapshot(tasks)

    # --- Generate HTML ---
    print("  HTML生成中...")
    html = gen(projects, sections, tasks, collabs, LOGO_B64, changes, mode=mode, all_tasks=all_tasks, all_projects=all_projects)

    # Save HTML locally
    if mode == "all":
        output_path = OUTPUT
        ci_filename = "index.html"
    elif mode == "accounting":
        output_path = Path.home() / "Desktop" / "LOOK_UP_Dashboard_Accounting.html"
        ci_filename = "accounting.html"
    else:
        output_path = Path.home() / "Desktop" / "LOOK_UP_Dashboard_Other.html"
        ci_filename = "other.html"
    if is_ci():
        output_path = Path(ci_filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(output_path), "w", encoding="utf-8") as f: f.write(html)
    print(f"  保存: {output_path}")

    # --- GitHub Pages deploy ---
    dashboard_url = None
    if cfg.get("github_token") and not is_ci():
        # Local mode: deploy via API with mode-specific filename
        print("  GitHub Pagesにデプロイ中...")
        dashboard_url = deploy_github(html, ci_filename)
        if dashboard_url:
            print(f"    公開: {dashboard_url}")
        else:
            print("    デプロイ失敗")
    elif is_ci() and cfg.get("github_user"):
        # CI mode: file is committed by workflow, just build URL
        dashboard_url = f"https://{cfg['github_user']}.github.io/{cfg['github_repo']}/{ci_filename}"
        print(f"  GitHub Pages: {dashboard_url} (ワークフローがコミット)")

    # --- Slack notification ---
    if cfg.get("slack_bot_token") and cfg.get("slack_channel_id"):
        print("  Slack投稿中（サマリー + スレッドコーチング）...")
        if send_slack_with_coaching(tasks, changes, collabs, projects, sections, dashboard_url):
            print("    完了")
        else:
            print("    失敗")

    # --- Open browser (local only) ---
    if not is_ci():
        webbrowser.open(f"file://{output_path}")
        print(f"\n  次回: python3 ~/Desktop/lookup_dashboard.py")
        print(f"  設定リセット: rm {CONFIG}")
    else:
        print("\n  CI実行完了。")

    print()

if __name__ == "__main__":
    main()
