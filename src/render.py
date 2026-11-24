"""生成自包含静态看板：docs/index.html。

数据直接内嵌进 HTML，不依赖同目录的 data/ 文件夹。
手机端、预览面板、微信内置浏览器打开单个 HTML 都能看到数据。
"""

from __future__ import annotations

import json
import os

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>开源星榜 · Forge Pulse</title>
<style>
:root{--bg:#0d1117;--panel:#161b22;--panel2:#1c2129;--line:#30363d;
--txt:#e6edf3;--sub:#8b949e;--up:#f04b4b;--down:#2ea043;--accent:#58a6ff;--warn:#e3b341}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);
 font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif}
.wrap{max-width:1280px;margin:0 auto;padding:24px 16px 48px}
header{display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:18px}
h1{margin:0;font-size:24px;letter-spacing:.5px}
h1 span{color:var(--accent)}
.sub{color:var(--sub);font-size:12px;margin-top:4px}
.stamp{color:var(--sub);font-size:12px;text-align:right}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:13px 15px}
.card .k{color:var(--sub);font-size:12px}
.card .v{font-size:22px;font-weight:650;margin-top:4px}
.card .v.hot{color:var(--up)}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:14px}
.group{display:flex;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:3px;gap:2px;overflow-x:auto}
button{background:transparent;color:var(--sub);border:0;border-radius:6px;padding:6px 12px;cursor:pointer;font-size:13px;white-space:nowrap}
button:hover{color:var(--txt)}
button.on{background:var(--panel2);color:var(--txt);box-shadow:0 1px 3px #0006}
input{background:var(--panel);border:1px solid var(--line);border-radius:8px;color:var(--txt);padding:8px 12px;font-size:13px;width:190px;outline:none}
input:focus{border-color:var(--accent)}
.spacer{flex:1}
.tbl-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--panel)}
table{width:100%;border-collapse:collapse;min-width:840px}
th{color:var(--sub);font-size:12px;font-weight:500;text-align:left;padding:11px 12px;background:var(--panel2);white-space:nowrap}
td{padding:10px 12px;border-top:1px solid var(--line);vertical-align:middle}
tr:hover td{background:#1b222b}
.rk{color:var(--sub);width:38px;font-variant-numeric:tabular-nums}
.rk.top{color:var(--accent);font-weight:700}
.repo a{color:var(--txt);text-decoration:none;font-weight:600}
.repo a:hover{color:var(--accent);text-decoration:underline}
.desc{color:var(--sub);font-size:12px;max-width:380px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-top:2px}
.tag{display:inline-block;font-size:11px;padding:2px 7px;border-radius:20px;border:1px solid var(--line);color:var(--sub)}
.tag.github{color:#d0d7de;border-color:#484f58}.tag.gitlab{color:#fc6d26;border-color:#7d3d20}.tag.gitee{color:#e34d4d;border-color:#7d3030}
.lang{color:var(--sub);font-size:12px;white-space:nowrap}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.up{color:var(--up);font-weight:650}.down{color:var(--down);font-weight:650}.mute{color:var(--sub)}
.spark{width:80px;height:26px}
.warn{color:var(--warn);font-size:11px;margin-left:4px}
.empty{text-align:center;color:var(--sub);padding:36px}
footer{margin-top:16px;color:var(--sub);font-size:12px;line-height:1.8}
.pgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px}
.pcard{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:15px}
.pcard h3{margin:0 0 10px;font-size:15px}
.pcard .big{font-size:22px;font-weight:650;color:var(--up)}
.pcard .mini{color:var(--sub);font-size:12px;margin-top:4px}
.barline{height:9px;border-radius:5px;background:var(--panel2);margin:9px 0 4px;overflow:hidden}
.barline i{display:block;height:100%;border-radius:5px}
.plist{margin:8px 0 0;padding:0;list-style:none;font-size:12px}
.plist li{display:flex;justify-content:space-between;padding:4px 0;border-top:1px solid var(--line)}
.plist a{color:var(--txt);text-decoration:none;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:72%}
.plist a:hover{color:var(--accent)}
.repo a{cursor:pointer}
.mask{position:fixed;inset:0;background:#000a;display:none;align-items:center;justify-content:center;z-index:50;padding:16px}
.modal{background:var(--panel);border:1px solid var(--line);border-radius:14px;width:min(560px,100%);max-height:86vh;overflow:auto;box-shadow:0 20px 60px #0008}
.mhead{display:flex;justify-content:space-between;align-items:flex-start;padding:18px 20px 12px;border-bottom:1px solid var(--line)}
.mhead h2{margin:0;font-size:18px;word-break:break-all}
.mhead .x{background:none;border:0;color:var(--sub);font-size:24px;cursor:pointer;line-height:1;padding:0 4px}
.mbody{padding:16px 20px 20px}
.mdesc{color:#c9d1d9;font-size:13px;line-height:1.85;margin:0 0 14px}
.mraw{margin:0 0 16px}
.mraw summary{color:var(--sub);font-size:12px;cursor:pointer;user-select:none}
.mraw summary:hover{color:var(--txt)}
.mraw p{color:var(--sub);font-size:12px;line-height:1.6;margin:8px 0 0;padding:10px;background:var(--panel2);border-radius:8px;word-break:break-word}
.mstats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:16px}
.mstat{background:var(--panel2);border-radius:8px;padding:10px;text-align:center}
.mstat .k{color:var(--sub);font-size:11px}
.mstat .v{font-size:17px;font-weight:650;margin-top:3px}
.mchart{background:var(--panel2);border-radius:8px;padding:10px 12px;margin-bottom:14px;overflow:hidden}
.mchart .t{color:var(--sub);font-size:11px;margin-bottom:6px}
.mchart svg{width:100%;height:60px}
.mmeta{color:var(--sub);font-size:12px;line-height:1.9}
.mmeta b{color:var(--txt);font-weight:500}
.golink{display:block;text-align:center;background:var(--accent);color:#fff;text-decoration:none;
 border-radius:8px;padding:10px;margin-top:16px;font-weight:600}
.golink:hover{filter:brightness(1.1)}
@media(max-width:820px){.cards,.pgrid{grid-template-columns:repeat(2,1fr)}input{width:100%}}
@media(max-width:520px){.mstats{grid-template-columns:repeat(2,1fr)}}
@media(max-width:520px){.cards,.pgrid{grid-template-columns:1fr}.stamp{text-align:left}}
</style>
</head>
<body>
<div class="wrap">
<header>
 <div><h1>开源<span>星榜</span> · Forge Pulse</h1>
 <div class="sub">GitHub / GitLab / Gitee 每日涨星聚合 · 快照相减算增量</div></div>
 <div class="stamp">数据日期 <b id="day">—</b><br><span id="gen"></span></div>
</header>
<div class="cards" id="cards"></div>
<div class="bar">
 <div class="group" id="boards"></div>
 <div class="group" id="platforms"></div>
 <input id="q" placeholder="搜索仓库名 / 描述…">
 <div class="spacer"></div><span class="sub" id="count"></span>
</div>

<div id="viewBoard">
 <div class="tbl-wrap"><table><thead><tr>
 <th class="rk">#</th><th>仓库</th><th>平台</th><th>语言</th><th class="num">总星</th>
 <th class="num">今日涨星</th><th class="num">7 日</th><th class="num">30 日</th><th>走势</th>
 </tr></thead><tbody id="rows"></tbody></table></div>
</div>

<div id="viewCompare" style="display:none">
 <div class="pgrid" id="pcards"></div>
 <div class="tbl-wrap"><table><thead><tr><th>平台</th><th>仓库</th><th class="num">总星</th><th class="num">今日涨星</th><th>说明</th></tr></thead><tbody id="crossRows"></tbody></table></div>
</div>

<div class="mask" id="mask" onclick="if(event.target===this)closeModal()">
 <div class="modal" id="modal">
  <div class="mhead"><h2 id="mTitle">—</h2><button class="x" onclick="closeModal()" title="关闭">×</button></div>
  <div class="mbody" id="mBody"></div>
 </div>
</div>

<footer>
<b>口径</b>：涨星 = 今日星数 − N 天前星数，来自本地每日快照，非第三方推算；无对应历史显示 <span class="mute">—</span>。
<span class="warn">⚠</span> 表示单日增量超过昨日存量 30% 且大于 100 星，可能是刷星或推广。
GitLab / Gitee 首次运行无历史，次日起出现增量。数据已内嵌本文件，手机或离线打开都能看。
</footer>
</div>
<script>window.FORGE_PULSE = __DATA__;</script>
<script>
const D = window.FORGE_PULSE || {boards:{},stats:{}};
let board='daily', platform='all', query='';
const fmt = n => n==null ? '<span class="mute">—</span>' :
 (n>0?'<span class="up">+'+n.toLocaleString()+'</span>':n<0?'<span class="down">'+n.toLocaleString()+'</span>':'<span class="mute">0</span>');
const esc = s => (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function sparkline(arr){
 if(!arr||arr.length<2) return '<span class="mute">—</span>';
 const mn=Math.min(...arr),mx=Math.max(...arr),sp=mx-mn||1;
 const pts=arr.map((v,i)=>(2+i*(76/(arr.length-1))).toFixed(1)+','+(23-(v-mn)/sp*20).toFixed(1)).join(' ');
 const c=arr[arr.length-1]>=arr[0]?'#f04b4b':'#2ea043';
 return '<svg class="spark" viewBox="0 0 80 26"><polyline fill="none" stroke="'+c+'" stroke-width="1.6" stroke-linejoin="round" points="'+pts+'"/></svg>';
}
function bigChart(arr){
 if(!arr||arr.length<2) return '<div class="mute">历史点数不足，次日起显示走势</div>';
 const mn=Math.min(...arr),mx=Math.max(...arr),sp=mx-mn||1;
 const pts=arr.map((v,i)=>(2+i*(496/(arr.length-1))).toFixed(1)+','+(56-(v-mn)/sp*50).toFixed(1)).join(' ');
 const c=arr[arr.length-1]>=arr[0]?'#f04b4b':'#2ea043';
 return '<svg viewBox="0 0 500 60" preserveAspectRatio="none"><polyline fill="none" stroke="'+c+'" stroke-width="2" stroke-linejoin="round" points="'+pts+'"/></svg>';
}
let DETAIL={};
const SRC_ZH={history:'历史快照基线',trending:'GitHub Trending 热榜',gh_trending:'GitHub Trending 热榜',seed:'固定追踪清单',explore:'GitLab 探索榜',gh_search:'GitHub 搜索',search_api:'GitHub 搜索',manual:'手动补采'};
function openModal(key){
 const r=DETAIL[key]; if(!r) return;
 document.getElementById('mTitle').innerHTML=esc(r.full_name)+' <span class="tag '+r.platform+'">'+r.platform+'</span>';
 const warn=r.suspicious?'<div style="color:#e3b341;font-size:12px;margin-top:8px">⚠ 单日增量异常，可能含刷星或推广活动</div>':'';
 const brief=r.zh_brief||'';
 const raw=r.description||'';
 const rawBlock=raw?'<details class="mraw"><summary>查看英文原文</summary><p>'+esc(raw)+'</p></details>':'';
 const body=
  '<div class="mdesc">'+esc(brief)+'</div>'+rawBlock+
  '<div class="mstats">'+
   '<div class="mstat"><div class="k">总星</div><div class="v">'+(r.stars||0).toLocaleString()+'</div></div>'+
   '<div class="mstat"><div class="k">今日</div><div class="v">'+fmtText(r.d1)+'</div></div>'+
   '<div class="mstat"><div class="k">7 日</div><div class="v">'+fmtText(r.d7)+'</div></div>'+
   '<div class="mstat"><div class="k">30 日</div><div class="v">'+fmtText(r.d30)+'</div></div>'+
  '</div>'+
  '<div class="mchart"><div class="t">最近 '+((r.spark||[]).length||0)+' 天星数走势</div>'+bigChart(r.spark)+'</div>'+
  '<div class="mmeta">'+
   '语言：<b>'+esc(r.language||'未标注')+'</b>　Fork：<b>'+(r.forks!=null?r.forks.toLocaleString():'—')+'</b><br>'+
   '创建：<b>'+esc(r.created||'—')+'</b>　追踪天数：<b>'+(r.days_tracked||'—')+' 天</b><br>'+
   '发现渠道：<b>'+esc(SRC_ZH[r.source]||r.source||'—')+'</b>'+warn+
  '</div>'+
  '<a class="golink" href="'+esc(r.url)+'" target="_blank" rel="noopener">打开原仓库 ↗</a>';
 document.getElementById('mBody').innerHTML=body;
 document.getElementById('mask').style.display='flex';
}
function fmtText(n){return n==null?'—':(n>0?'+'+n.toLocaleString():n.toLocaleString())}
function closeModal(){document.getElementById('mask').style.display='none'}
function repoLink(r){DETAIL[r.key]=r;return '<a href="javascript:void(0)" onclick="openModal(\''+r.key+'\')" title="点击查看项目说明">'+esc(r.full_name)+'</a>'}
function controls(){
 document.getElementById('boards').innerHTML=
  [['daily','今日涨星'],['weekly','7 日涨星'],['monthly','30 日涨星'],['total','总星榜'],['compare','平台对比']]
  .map(([k,t])=>'<button class="'+(k===board?'on':'')+'" data-b="'+k+'">'+t+'</button>').join('');
 document.getElementById('platforms').innerHTML=
  [['all','全部'],['github','GitHub'],['gitlab','GitLab'],['gitee','Gitee']]
  .map(([k,t])=>'<button class="'+(k===platform?'on':'')+'" data-p="'+k+'">'+t+'</button>').join('');
 document.querySelectorAll('[data-b]').forEach(b=>b.onclick=()=>{board=b.dataset.b;draw()});
 document.querySelectorAll('[data-p]').forEach(b=>b.onclick=()=>{platform=b.dataset.p;draw()});
}
function cards(){
 const s=D.stats||{};
 const it=[['追踪仓库',(s.tracked_repos||0).toLocaleString(),''],
  ['今日最高涨星','+'+(s.top_gain_today||0).toLocaleString(),'hot'],
  ['快照天数',(s.snapshot_days||0)+' 天',''],
  ['覆盖平台',(s.platforms||[]).join(' / ')||'—','']];
 document.getElementById('cards').innerHTML=it.map(([k,v,c])=>
  '<div class="card"><div class="k">'+k+'</div><div class="v '+c+'">'+esc(v)+'</div></div>').join('');
 document.getElementById('day').textContent=s.latest_date||'—';
 document.getElementById('gen').textContent='生成于 '+(D.generated_at||'').replace('T',' ');
}
function listRows(){
 let list=((D.boards||{})[board]||{})[platform]||[];
 if(query){const q=query.toLowerCase();list=list.filter(r=>(r.full_name||'').toLowerCase().includes(q)||(r.description||'').toLowerCase().includes(q));}
 document.getElementById('count').textContent='显示 '+list.length+' 个项目';
 document.getElementById('rows').innerHTML=list.length?list.map((r,i)=>{
  const w=r.suspicious?'<span class="warn" title="疑似刷星或推广">⚠</span>':'';
  return '<tr><td class="rk '+(i<3?'top':'')+'">'+(i+1)+'</td>'+
   '<td class="repo">'+repoLink(r)+w+
   (r.description?'<div class="desc" title="'+esc(r.description)+'">'+esc(r.description)+'</div>':'')+'</td>'+
   '<td><span class="tag '+r.platform+'">'+r.platform+'</span></td><td class="lang">'+esc(r.language||'—')+'</td>'+
   '<td class="num">'+(r.stars||0).toLocaleString()+'</td><td class="num">'+fmt(r.d1)+'</td>'+
   '<td class="num">'+fmt(r.d7)+'</td><td class="num">'+fmt(r.d30)+'</td><td>'+sparkline(r.spark)+'</td></tr>';
 }).join(''):'<tr><td colspan="9" class="empty">没有匹配的项目</td></tr>';
}
function compare(){
 const ps=['github','gitlab','gitee'], colors={github:'#8b949e',gitlab:'#fc6d26',gitee:'#e34d4d'};
 let maxGain=0; const data={};
 ps.forEach(p=>{
  const rows=((D.boards||{}).total||{})[p]||[];
  const gain=rows.filter(r=>r.d1!=null).reduce((a,b)=>a+b.d1,0);
  data[p]={rows,gain}; if(gain>maxGain)maxGain=gain;
 });
 document.getElementById('pcards').innerHTML=ps.map(p=>{
  const d=data[p], top=d.rows[0];
  return '<div class="pcard"><h3><span class="tag '+p+'">'+p+'</span></h3>'+
   '<div class="big">+'+(d.gain||0).toLocaleString()+'</div><div class="mini">今日涨星合计 · '+d.rows.length+' 个追踪仓库</div>'+
   '<div class="barline"><i style="width:'+(maxGain?Math.max(2,d.gain/maxGain*100):0)+'%;background:'+colors[p]+'"></i></div>'+
   (top?'<ul class="plist">'+d.rows.slice(0,5).map(r=>'<li>'+repoLink(r)+'<span class="up">'+(r.d1!=null?'+'+r.d1.toLocaleString():'—')+'</span></li>').join('')+'</ul>':'')+
   '</div>';
 }).join('');
 let all=[]; ps.forEach(p=>{data[p].rows.slice(0,3).forEach(r=>all.push(r))});
 all.sort((a,b)=>(b.d1||0)-(a.d1||0));
 document.getElementById('crossRows').innerHTML=all.slice(0,12).map(r=>
  '<tr><td><span class="tag '+r.platform+'">'+r.platform+'</span></td>'+
  '<td class="repo">'+repoLink(r)+'</td>'+
  '<td class="num">'+(r.stars||0).toLocaleString()+'</td><td class="num">'+fmt(r.d1)+'</td>'+
  '<td class="mute">'+(r.d1==null?'首日追踪，次日起显示增量':'来自本地快照')+'</td></tr>').join('');
}
function el(id){return document.getElementById(id)}
function draw(){
 controls();
 document.getElementById('viewBoard').style.display=(board==='compare')?'none':'';
 document.getElementById('viewCompare').style.display=board==='compare'?'':'none';
 if(board==='compare')compare();else listRows();
}
el('q').addEventListener('input',e=>{query=e.target.value.trim();draw()});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal()});
cards();draw();
</script>
</body>
</html>
"""


def write_page(path: str, payload: dict | None = None):
    """把数据内嵌进 HTML，生成完全自包含的看板文件。"""
    if payload is None:
        data_path = os.path.join(os.path.dirname(path), "..", "data", "leaderboard.json")
        with open(data_path, encoding="utf-8") as f:
            payload = json.load(f)
    data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # 防止描述里的 </script> 提前闭合脚本标签
    data_json = data_json.replace("<", "\\u003c")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(HTML.replace("__DATA__", data_json))
