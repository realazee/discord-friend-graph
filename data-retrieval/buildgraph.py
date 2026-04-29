import json
import networkx as nx
import math
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(SCRIPT_DIR, "mutuals_output.json")

with open(INPUT_FILE, "r") as f:
    raw = json.load(f)

G = nx.Graph()
all_ids = set(raw.keys())

for uid, info in raw.items():
    display = info.get("global_name") or info.get("username", uid)
    G.add_node(uid, username=info["username"], display=display, avatar=info.get("avatar", ""))

for uid, info in raw.items():
    for mid in info.get("mutual_friends", []):
        if mid in all_ids:
            G.add_edge(uid, mid)

print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")

communities = list(nx.community.louvain_communities(G, seed=42))
community_map = {}
for i, comm in enumerate(communities):
    for nid in comm:
        community_map[nid] = i

comm_sizes = {}
for nid, c in community_map.items():
    comm_sizes[c] = comm_sizes.get(c, 0) + 1
sorted_comms = sorted(comm_sizes.keys(), key=lambda c: -comm_sizes[c])
comm_remap = {old: new for new, old in enumerate(sorted_comms)}
for nid in community_map:
    community_map[nid] = comm_remap[community_map[nid]]

print("Computing layout...")
pos = nx.spring_layout(G, k=1.8/math.sqrt(G.number_of_nodes()), iterations=80, seed=42, scale=800)

nodes_data = []
for nid in G.nodes():
    x, y = pos[nid]
    data = G.nodes[nid]
    degree = G.degree(nid)
    nodes_data.append({
        "id": nid,
        "u": data["username"],
        "d": data["display"],
        "x": round(x, 2),
        "y": round(y, 2),
        "deg": degree,
        "c": community_map.get(nid, 0)
    })

edges_data = []
for u, v in G.edges():
    edges_data.append([u, v])

graph_json = json.dumps({"nodes": nodes_data, "edges": edges_data}, separators=(',', ':'))

print(f"Communities: {len(set(community_map.values()))}")
print(f"Largest community: {max(comm_sizes.values())} nodes")

# Generate HTML
html = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Friend Graph — Mutual Connections</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:#0a0a0f;color:#e0e0e0;overflow:hidden;height:100vh;width:100vw}
canvas{display:block;position:absolute;top:0;left:0}

.top-bar{position:fixed;top:0;left:0;right:0;height:52px;background:rgba(10,10,15,0.88);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-bottom:1px solid rgba(255,255,255,0.06);display:flex;align-items:center;padding:0 20px;z-index:100;gap:14px}
.top-bar h1{font-size:15px;font-weight:600;background:linear-gradient(135deg,#7c6cf0,#e06caa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;white-space:nowrap}
.search-box{position:relative;flex:0 1 280px}
.search-box input{width:100%;padding:7px 10px 7px 32px;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.08);border-radius:8px;color:#e0e0e0;font-family:inherit;font-size:12px;outline:none;transition:all .2s}
.search-box input:focus{background:rgba(255,255,255,0.1);border-color:rgba(124,108,240,.4);box-shadow:0 0 0 3px rgba(124,108,240,.1)}
.search-box input::placeholder{color:rgba(255,255,255,.3)}
.search-icon{position:absolute;left:10px;top:50%;transform:translateY(-50%);color:rgba(255,255,255,.3);font-size:12px;pointer-events:none}
.stats{margin-left:auto;display:flex;gap:16px;font-size:11px;color:rgba(255,255,255,.4)}
.stats .n{color:rgba(255,255,255,.7);font-weight:600}

.filter-bar{position:fixed;top:58px;right:16px;display:flex;gap:5px;z-index:100}
.filter-bar button{padding:5px 10px;border-radius:7px;background:rgba(18,18,28,.85);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.08);color:rgba(255,255,255,.5);font-family:inherit;font-size:10px;font-weight:500;cursor:pointer;transition:all .2s}
.filter-bar button:hover{background:rgba(30,30,45,.95);color:#fff}
.filter-bar button.active{background:rgba(124,108,240,.2);border-color:rgba(124,108,240,.4);color:#7c6cf0}

.tooltip{position:fixed;pointer-events:none;background:rgba(14,14,22,.95);backdrop-filter:blur(16px);border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:12px 14px;font-size:12px;z-index:200;opacity:0;transition:opacity .12s;min-width:160px;box-shadow:0 8px 28px rgba(0,0,0,.5)}
.tooltip.vis{opacity:1}
.tooltip .nm{font-weight:600;font-size:14px;color:#fff;margin-bottom:1px}
.tooltip .un{font-size:11px;color:rgba(255,255,255,.4);margin-bottom:6px}
.tooltip .mc{font-size:11px;color:rgba(255,255,255,.5)}.tooltip .mc b{color:#7c6cf0;font-weight:600}

.info-panel{position:fixed;bottom:16px;left:16px;background:rgba(14,14,22,.92);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:14px 18px;z-index:100;max-width:280px;box-shadow:0 8px 28px rgba(0,0,0,.4);transition:all .25s}
.info-panel.hide{opacity:0;transform:translateY(8px);pointer-events:none}
.info-panel .pn{font-weight:600;font-size:15px;color:#fff;margin-bottom:2px}
.info-panel .pu{font-size:11px;color:rgba(255,255,255,.4);margin-bottom:8px}
.info-panel .pm{font-size:11px;color:rgba(255,255,255,.5);margin-bottom:8px}
.info-panel .pm b{color:#7c6cf0;font-weight:600}
.info-panel .ml{max-height:180px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.1) transparent}
.info-panel .ml::-webkit-scrollbar{width:3px}.info-panel .ml::-webkit-scrollbar-thumb{background:rgba(255,255,255,.12);border-radius:3px}
.info-panel .mi{padding:3px 0;font-size:11px;color:rgba(255,255,255,.55);cursor:pointer;transition:color .12s}
.info-panel .mi:hover{color:#7c6cf0}
.info-panel .cb{position:absolute;top:8px;right:10px;background:none;border:none;color:rgba(255,255,255,.3);font-size:16px;cursor:pointer;line-height:1;padding:2px;transition:color .12s}
.info-panel .cb:hover{color:rgba(255,255,255,.7)}

.ctrls{position:fixed;bottom:16px;right:16px;display:flex;flex-direction:column;gap:5px;z-index:100}
.ctrls button{width:36px;height:36px;border-radius:9px;background:rgba(18,18,28,.9);backdrop-filter:blur(16px);border:1px solid rgba(255,255,255,.08);color:rgba(255,255,255,.6);font-size:15px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .2s;box-shadow:0 4px 10px rgba(0,0,0,.3)}
.ctrls button:hover{background:rgba(30,30,45,.95);color:#fff;border-color:rgba(124,108,240,.3)}
.ctrls button.on{background:rgba(124,108,240,.2);border-color:rgba(124,108,240,.4);color:#7c6cf0}

.legend{position:fixed;top:58px;left:16px;background:rgba(14,14,22,.85);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.06);border-radius:9px;padding:8px 12px;z-index:100;font-size:10px}
.legend-t{color:rgba(255,255,255,.4);font-weight:500;margin-bottom:4px;font-size:9px;text-transform:uppercase;letter-spacing:.5px}
.legend-i{display:flex;align-items:center;gap:5px;margin:2px 0;color:rgba(255,255,255,.5)}
.legend-d{width:7px;height:7px;border-radius:50%;flex-shrink:0}
</style>
</head>
<body>
<div class="top-bar">
 <h1>Friend Graph</h1>
 <div class="search-box"><span class="search-icon">🔍</span><input type="text" id="search" placeholder="Search for a friend…" autocomplete="off"></div>
 <div class="stats"><span><span class="n" id="sn">0</span> people</span><span><span class="n" id="se">0</span> connections</span></div>
</div>
<div class="filter-bar">
 <button class="active" data-f="all">All</button>
 <button data-f="connected">Connected Only</button>
 <button data-f="hubs">Hubs (10+)</button>
</div>
<div class="legend" id="legend"></div>
<canvas id="c"></canvas>
<div class="tooltip" id="tt"><div class="nm"></div><div class="un"></div><div class="mc"><b></b> mutual connections</div></div>
<div class="info-panel hide" id="ip">
 <button class="cb" id="cpb">×</button>
 <div class="pn"></div><div class="pu"></div>
 <div class="pm"><b></b> mutual connections in graph</div>
 <div class="ml"></div>
</div>
<div class="ctrls">
 <button id="zi" title="Zoom in">+</button>
 <button id="zo" title="Zoom out">−</button>
 <button id="zf" title="Fit to screen">⊡</button>
 <button id="tl" title="Toggle labels" class="on">A</button>
</div>

<script>
const GRAPH_DATA = """ + graph_json + r""";

(function(){
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
let W = window.innerWidth, H = window.innerHeight;
canvas.width = W; canvas.height = H;

const COLORS = [
 '#7c6cf0','#e06caa','#6ce0c4','#f0a86c','#6ca0f0',
 '#c46cf0','#f06c6c','#6cf0a8','#e0d06c','#6cd0f0',
 '#f06cc4','#a0f06c','#f0886c','#6c88f0','#d0a0f0',
 '#f0c06c','#6cf0d0','#b06cf0','#f06c90','#88e06c'
];

// Build lookup
const nodeMap = new Map();
const nodes = GRAPH_DATA.nodes;
const edges = GRAPH_DATA.edges;

nodes.forEach(n => {
 n.color = COLORS[n.c % COLORS.length];
 n.r = Math.max(3, Math.min(16, 2 + Math.sqrt(n.deg) * 2.2));
 n.neighbors = [];
 nodeMap.set(n.id, n);
});

// Build adjacency
edges.forEach(([u,v]) => {
 const a = nodeMap.get(u), b = nodeMap.get(v);
 if(a && b){ a.neighbors.push(v); b.neighbors.push(u); }
});

// Camera state
let camX = 0, camY = 0, camScale = 1;

// Fit to view initially
function fitView(){
 let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
 nodes.forEach(n=>{
  if(n.x<minX)minX=n.x; if(n.x>maxX)maxX=n.x;
  if(n.y<minY)minY=n.y; if(n.y>maxY)maxY=n.y;
 });
 const bw=maxX-minX||1, bh=maxY-minY||1;
 camScale = 0.85 * Math.min(W/bw, H/bh);
 camX = W/2 - (minX+bw/2)*camScale;
 camY = H/2 - (minY+bh/2)*camScale;
}
fitView();

// Transform helpers
function toScreen(x,y){return [x*camScale+camX, y*camScale+camY]}
function toWorld(sx,sy){return [(sx-camX)/camScale, (sy-camY)/camScale]}

// State
let hoverNode = null, selectedNode = null;
let showLabels = true;
let currentFilter = 'all';
let visibleSet = new Set(nodes.map(n=>n.id));
let searchMatches = null;

// Render
function draw(){
 ctx.clearRect(0,0,W,H);

 // BG
 const grad = ctx.createRadialGradient(W/2,H/2,0,W/2,H/2,W*0.6);
 grad.addColorStop(0,'#12121f');
 grad.addColorStop(1,'#0a0a0f');
 ctx.fillStyle = grad;
 ctx.fillRect(0,0,W,H);

 const highlightNode = hoverNode || selectedNode;
 const highlightSet = new Set();
 if(highlightNode){
  highlightSet.add(highlightNode.id);
  highlightNode.neighbors.forEach(nid => { if(visibleSet.has(nid)) highlightSet.add(nid); });
 }

 // Edges
 ctx.lineWidth = 0.5;
 edges.forEach(([uid,vid]) => {
  if(!visibleSet.has(uid)||!visibleSet.has(vid)) return;
  const u=nodeMap.get(uid), v=nodeMap.get(vid);
  const [x1,y1]=toScreen(u.x,u.y), [x2,y2]=toScreen(v.x,v.y);

  if(highlightNode){
   if(uid===highlightNode.id||vid===highlightNode.id){
    ctx.strokeStyle = highlightNode.color + 'aa';
    ctx.lineWidth = 1.8 * camScale / Math.max(camScale, 0.5);
   } else {
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = 0.4;
   }
  } else {
   ctx.strokeStyle = 'rgba(255,255,255,0.18)';
   ctx.lineWidth = 0.7;
  }
  ctx.beginPath();
  ctx.moveTo(x1,y1);
  ctx.lineTo(x2,y2);
  ctx.stroke();
 });

 // Nodes
 nodes.forEach(n => {
  if(!visibleSet.has(n.id)) return;
  const [sx,sy] = toScreen(n.x, n.y);
  const r = n.r * Math.min(camScale, 2.5) / Math.max(camScale, 0.3) * camScale * 0.5;
  const radius = Math.max(1.5, Math.min(r, 20));

  let alpha = 0.85;
  if(searchMatches && !searchMatches.has(n.id)) alpha = 0.06;
  else if(highlightNode && !highlightSet.has(n.id)) alpha = 0.06;

  ctx.globalAlpha = alpha;
  ctx.beginPath();
  ctx.arc(sx, sy, radius, 0, Math.PI*2);
  ctx.fillStyle = n.color;
  ctx.fill();

  // Glow on highlighted neighbors
  if(highlightNode && highlightSet.has(n.id) && n.id !== highlightNode.id){
   ctx.beginPath();
   ctx.arc(sx,sy,radius+2,0,Math.PI*2);
   ctx.fillStyle = n.color + '22';
   ctx.fill();
  }

  // Extra glow for the focused node itself
  if(highlightNode && n.id === highlightNode.id){
   ctx.beginPath();
   ctx.arc(sx,sy,radius+4,0,Math.PI*2);
   ctx.fillStyle = n.color + '33';
   ctx.fill();
  }

  ctx.globalAlpha = 1;
 });

 // Labels
 if(showLabels){
  nodes.forEach(n => {
   if(!visibleSet.has(n.id)) return;
   if(n.deg < 5 && camScale < 1.5) return; // only show labels for well-connected nodes when zoomed out
   if(n.deg < 2 && camScale < 3) return;
   const [sx,sy] = toScreen(n.x,n.y);
   const r = Math.max(1.5, n.r * Math.min(camScale, 2.5) / Math.max(camScale, 0.3) * camScale * 0.5);
   const fs = Math.max(8, Math.min(13, 7 + n.deg*0.25));

   let alpha = 0.6;
   if(searchMatches && !searchMatches.has(n.id)) alpha = 0.04;
   else if(highlightNode && !highlightSet.has(n.id)) alpha = 0.04;

   ctx.globalAlpha = alpha;
   ctx.font = `500 ${fs}px Inter, sans-serif`;
   ctx.textAlign = 'center';
   ctx.fillStyle = '#e0e0e0';
   ctx.fillText(n.d, sx, sy - r - 4);
   ctx.globalAlpha = 1;
  });
 }
}

draw();

// Interaction
let isDragging = false, dragStart = null, lastMouse = {x:0,y:0};

canvas.addEventListener('wheel', e => {
 e.preventDefault();
 const factor = e.deltaY > 0 ? 0.9 : 1.1;
 const mx = e.clientX, my = e.clientY;
 camX = mx - (mx - camX) * factor;
 camY = my - (my - camY) * factor;
 camScale *= factor;
 camScale = Math.max(0.02, Math.min(15, camScale));
 draw();
}, {passive:false});

canvas.addEventListener('mousedown', e => {
 isDragging = true;
 dragStart = {x: e.clientX, y: e.clientY, camX, camY};
 lastMouse = {x:e.clientX, y:e.clientY};
});

canvas.addEventListener('mousemove', e => {
 lastMouse = {x:e.clientX, y:e.clientY};
 if(isDragging){
  camX = dragStart.camX + (e.clientX - dragStart.x);
  camY = dragStart.camY + (e.clientY - dragStart.y);
  draw();
  return;
 }

 // Hit test
 const [wx,wy] = toWorld(e.clientX, e.clientY);
 let found = null;
 let minDist = Infinity;
 for(const n of nodes){
  if(!visibleSet.has(n.id)) continue;
  const dx = n.x-wx, dy = n.y-wy;
  const dist = Math.sqrt(dx*dx+dy*dy);
  const hitR = (n.r * 1.5) / camScale;
  if(dist < hitR && dist < minDist){
   minDist = dist; found = n;
  }
 }

 if(found !== hoverNode){
  hoverNode = found;
  canvas.style.cursor = found ? 'pointer' : 'grab';
  const tt = document.getElementById('tt');
  if(found){
   tt.querySelector('.nm').textContent = found.d;
   tt.querySelector('.un').textContent = '@'+found.u;
   tt.querySelector('b').textContent = found.deg;
   tt.classList.add('vis');
  } else {
   tt.classList.remove('vis');
  }
  draw();
 }
 if(hoverNode){
  const tt = document.getElementById('tt');
  tt.style.left = (e.clientX+14)+'px';
  tt.style.top = (e.clientY-8)+'px';
 }
});

canvas.addEventListener('mouseup', e => {
 const dx = dragStart ? e.clientX - dragStart.x : 0;
 const dy = dragStart ? e.clientY - dragStart.y : 0;
 const wasClick = Math.abs(dx) < 4 && Math.abs(dy) < 4;
 isDragging = false;
 dragStart = null;

 if(wasClick){
  if(hoverNode){
   selectedNode = hoverNode;
   showInfoPanel(hoverNode);
   draw();
  } else {
   selectedNode = null;
   document.getElementById('ip').classList.add('hide');
   draw();
  }
 }
});

canvas.addEventListener('mouseleave', () => {
 isDragging = false;
 hoverNode = null;
 document.getElementById('tt').classList.remove('vis');
 if(!selectedNode) draw();
});

// Info panel
function showInfoPanel(n){
 const ip = document.getElementById('ip');
 ip.classList.remove('hide');
 ip.querySelector('.pn').textContent = n.d;
 ip.querySelector('.pu').textContent = '@'+n.u;
 ip.querySelector('b').textContent = n.deg;
 const ml = ip.querySelector('.ml');
 ml.innerHTML = '';
 const neighbors = n.neighbors
  .map(id=>nodeMap.get(id))
  .filter(Boolean)
  .sort((a,b)=>b.deg-a.deg);
 neighbors.forEach(m=>{
  const div = document.createElement('div');
  div.className = 'mi';
  div.textContent = m.d+' (@'+m.u+')';
  div.onclick = e => {
   e.stopPropagation();
   selectedNode = m;
   hoverNode = null;
   showInfoPanel(m);
   // Pan to node
   const [sx,sy] = toScreen(m.x, m.y);
   camX += W/2 - sx;
   camY += H/2 - sy;
   draw();
  };
  ml.appendChild(div);
 });
}

document.getElementById('cpb').onclick = e => {
 e.stopPropagation();
 selectedNode = null;
 document.getElementById('ip').classList.add('hide');
 draw();
};

// Search
document.getElementById('search').addEventListener('input', e => {
 const q = e.target.value.toLowerCase().trim();
 if(!q){
  searchMatches = null;
  selectedNode = null;
  document.getElementById('ip').classList.add('hide');
  draw(); return;
 }
 const matches = nodes.filter(n => n.d.toLowerCase().includes(q) || n.u.toLowerCase().includes(q));
 searchMatches = new Set(matches.map(m=>m.id));
 if(matches.length === 1){
  selectedNode = matches[0];
  showInfoPanel(matches[0]);
  // also add neighbors to visible
  matches[0].neighbors.forEach(nid => searchMatches.add(nid));
  // Pan
  const [sx,sy] = toScreen(matches[0].x, matches[0].y);
  camX += W/2 - sx; camY += H/2 - sy;
 }
 draw();
});

// Controls
document.getElementById('zi').onclick = () => {
 camX = W/2 - (W/2-camX)*1.4;
 camY = H/2 - (H/2-camY)*1.4;
 camScale *= 1.4;
 draw();
};
document.getElementById('zo').onclick = () => {
 camX = W/2 - (W/2-camX)*0.7;
 camY = H/2 - (H/2-camY)*0.7;
 camScale *= 0.7;
 draw();
};
document.getElementById('zf').onclick = () => { fitView(); draw(); };
document.getElementById('tl').onclick = function(){
 showLabels = !showLabels;
 this.classList.toggle('on', showLabels);
 draw();
};

// Filters
document.querySelectorAll('.filter-bar button').forEach(btn => {
 btn.onclick = function(){
  document.querySelectorAll('.filter-bar button').forEach(b=>b.classList.remove('active'));
  this.classList.add('active');
  currentFilter = this.dataset.f;
  switch(currentFilter){
   case 'connected': visibleSet = new Set(nodes.filter(n=>n.deg>0).map(n=>n.id)); break;
   case 'hubs': visibleSet = new Set(nodes.filter(n=>n.deg>=10).map(n=>n.id)); break;
   default: visibleSet = new Set(nodes.map(n=>n.id));
  }
  document.getElementById('sn').textContent = visibleSet.size;
  document.getElementById('se').textContent = edges.filter(([u,v])=>visibleSet.has(u)&&visibleSet.has(v)).length;
  draw();
 };
});

// Stats
document.getElementById('sn').textContent = nodes.length;
document.getElementById('se').textContent = edges.length;

// Legend
const commCounts = {};
nodes.forEach(n => commCounts[n.c] = (commCounts[n.c]||0)+1);
const topComms = Object.entries(commCounts).sort((a,b)=>b[1]-a[1]).slice(0,8);
let lh = '<div class="legend-t">Clusters</div>';
topComms.forEach(([c,count],i) => {
 lh += '<div class="legend-i"><div class="legend-d" style="background:'+COLORS[c%COLORS.length]+'"></div>Group '+(i+1)+' ('+count+')</div>';
});
const shown = topComms.reduce((s,e)=>s+e[1],0);
if(nodes.length > shown) lh += '<div class="legend-i" style="color:rgba(255,255,255,.3)">+ '+(Object.keys(commCounts).length-topComms.length)+' more ('+(nodes.length-shown)+')</div>';
document.getElementById('legend').innerHTML = lh;

// Resize
window.addEventListener('resize', () => {
 W = window.innerWidth; H = window.innerHeight;
 canvas.width = W; canvas.height = H;
 draw();
});

})();
</script>
</body>
</html>"""

with open("graph.html", "w", encoding="utf-8") as f:
    f.write(html)

print("graph.html generated successfully!")
