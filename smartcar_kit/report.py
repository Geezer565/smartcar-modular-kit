"""Portable, self-contained reports built from the simulator's actual records."""

import html
import json
from pathlib import Path


def trajectory_svg(result: dict) -> str:
    world, records, path = result['world'], result['records'], result['path']
    width, height = world['width'] * world['resolution'], world['height'] * world['resolution']
    scale = min(800 / width, 460 / height)
    ox, oy = 56, 128
    def point(x, y):
        return f'{ox + x * scale:.2f},{oy + (height - y) * scale:.2f}'
    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="920" height="660" viewBox="0 0 920 660" role="img" aria-label="Simulated robot planned path and driven trajectory">
<rect width="920" height="660" rx="24" fill="#0b1220"/>
<text x="48" y="48" fill="#e9f1ff" font-size="24" font-family="sans-serif" font-weight="700">SMARTCAR KIT / TRAJECTORY</text>
<text x="48" y="80" fill="#93a8c4" font-size="14" font-family="sans-serif">A* planning + Pure pursuit + command protection | Synthetic scene</text>
<rect x="{ox}" y="{oy}" width="{width * scale}" height="{height * scale}" fill="#111f33" stroke="#31435c"/>
''']
    r = world['resolution']
    for field, color in [('inflated', '#1b3146'), ('blocked', '#64748b')]:
        for x, y in world[field]:
            px, py = point(x * r, (y + 1) * r).split(',')
            parts.append(f'<rect x="{px}" y="{py}" width="{r * scale:.2f}" height="{r * scale:.2f}" fill="{color}"/>')
    points = ' '.join(point(x, y) for x, y in path)
    driven = ' '.join(point(row['x'], row['y']) for row in records)
    parts += [f'<polyline points="{points}" fill="none" stroke="#f5b85a" stroke-width="2.5" stroke-dasharray="6 6"/>',
              f'<polyline points="{driven}" fill="none" stroke="#36d6bc" stroke-width="3.5"/>']
    for label, (x, y), color in [('START', path[0], '#36d6bc'), ('GOAL', path[-1], '#f5b85a')]:
        px, py = map(float, point(x, y).split(','))
        parts += [f'<circle cx="{px}" cy="{py}" r="6" fill="{color}"/>',
                  f'<text x="{px + 10}" y="{py - 10}" fill="{color}" font-family="sans-serif" font-size="12">{label}</text>']
    summary = result['summary']
    stats = (f"{result['scenario'].upper()} | success={summary['success']} | "
             f"collision={summary['collision']} | goal error={summary['goal_error']:.3f} m")
    parts += [f'<text x="48" y="616" fill="#c6d4e6" font-family="monospace" font-size="13">{html.escape(stats)}</text>',
              '<text x="48" y="640" fill="#93a8c4" font-family="sans-serif" font-size="12">Amber: planned path   Teal: simulated motion   Shaded: planning clearance   No real-vehicle claim</text></svg>']
    return '\n'.join(parts)


def write_report(result: dict, destination: Path):
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'run.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    (destination / 'trajectory.svg').write_text(trajectory_svg(result), encoding='utf-8')
    payload = json.dumps(result, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')
    page = '''<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SmartCar Kit · 行驶回放</title>
<style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#0b1220;color:#edf3fc}
body{max-width:1120px;margin:0 auto;padding:36px 22px}small,.muted{color:#96aac5}
h1{font-size:clamp(28px,5vw,44px);margin:8px 0}header{margin-bottom:24px}
.layout{display:grid;grid-template-columns:3fr 1fr;gap:18px}.panel{background:#111f33;border:1px solid #293c54;border-radius:18px;padding:18px}
canvas{width:100%;height:auto;display:block}button{cursor:pointer;background:#36d6bc;color:#09241f;border:0;border-radius:9px;padding:10px 18px;font-weight:700}
input{width:100%;accent-color:#36d6bc}select{padding:8px;border-radius:8px;background:#1d3048;color:inherit}
.controls{display:flex;gap:12px;align-items:center;margin-top:14px}dl{margin:0}dt{font-size:12px;color:#96aac5;margin-top:18px}dd{margin:4px 0;font-family:monospace;font-size:18px}
.legend{font-size:13px;margin:12px 0;color:#b5c6da}footer{margin-top:22px;font-size:13px;color:#96aac5}
@media(max-width:760px){.layout{grid-template-columns:1fr}dl{display:grid;grid-template-columns:1fr 1fr}}
</style>
<header><small>SMARTCAR KIT / SOFTWARE DEMO</small><h1>从一条路径，到一次完整行驶。</h1><p class="muted">拖动时间轴，查看每一刻的位置、指令和任务状态。所有记录来自本地模拟。</p></header>
<main class="layout"><section class="panel"><canvas id="view" width="900" height="600" aria-label="模拟路径与车辆位置"></canvas>
<p class="legend">🟨 规划路径　🟩 实际模拟轨迹　灰色：障碍物　深色：预留距离</p>
<input id="timeline" type="range" min="0" step="1" aria-label="回放进度">
<div class="controls"><button id="play">播放</button><button id="restart">重头开始</button><select id="rate" aria-label="回放速度"><option value="1">1×</option><option value="2" selected>2×</option><option value="5">5×</option></select></div>
</section><aside class="panel"><small>LIVE RECORD</small><dl id="stats"></dl></aside></main>
<footer>平面运动模拟 · 无真实传感器、车辆或网络连接 · 空格键播放/暂停</footer>
<script>
const data=__DATA__,rows=data.records,w=data.world,cv=document.getElementById('view'),ctx=cv.getContext('2d');
const slider=document.getElementById('timeline'),play=document.getElementById('play'),rate=document.getElementById('rate'),stats=document.getElementById('stats');
let cursor=0,playing=false,last=null;
slider.max=rows.length-1;
const s=Math.min(800/(w.width*w.resolution),490/(w.height*w.resolution));
function p(x,y){return [45+x*s,45+(w.height*w.resolution-y)*s]}
function line(points,color,dashed=false){ctx.strokeStyle=color;ctx.lineWidth=3;ctx.setLineDash(dashed?[7,6]:[]);ctx.beginPath();points.forEach((v,i)=>{const a=p(v[0],v[1]);i?ctx.lineTo(...a):ctx.moveTo(...a)});ctx.stroke();ctx.setLineDash([])}
function draw(){const i=Math.min(rows.length-1,Math.floor(cursor)),row=rows[i];slider.value=i;ctx.clearRect(0,0,cv.width,cv.height);ctx.fillStyle='#14253b';ctx.fillRect(45,45,w.width*w.resolution*s,w.height*w.resolution*s);
for(const [cells,color] of [[w.inflated,'#1b3449'],[w.blocked,'#64748b']]){ctx.fillStyle=color;for(const [x,y] of cells){const a=p(x*w.resolution,(y+1)*w.resolution);ctx.fillRect(...a,w.resolution*s,w.resolution*s)}}
line(data.path,'#f5b85a',true);line(rows.slice(0,i+1).map(r=>[r.x,r.y]),'#36d6bc');
const a=p(row.x,row.y);ctx.save();ctx.translate(...a);ctx.rotate(-row.yaw);ctx.fillStyle='#36d6bc';ctx.beginPath();ctx.moveTo(13,0);ctx.lineTo(-10,-8);ctx.lineTo(-10,8);ctx.closePath();ctx.fill();ctx.restore();
const g=p(...data.path[data.path.length-1]);ctx.strokeStyle='#f5b85a';ctx.lineWidth=3;ctx.beginPath();ctx.arc(...g,8,0,Math.PI*2);ctx.stroke();
const values=[['场景',data.scenario],['模拟时间',row.t.toFixed(2)+' s'],['任务状态',row.state],['保护状态',row.reason],['速度',row.speed.toFixed(3)+' m/s'],['转向速度',row.yaw_rate.toFixed(3)+' rad/s'],['指令来源',row.source],['运行结果',data.summary.success?'通过预期检查':'未完成']];stats.replaceChildren();for(const [label,value] of values){const wrap=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=value;wrap.append(dt,dd);stats.append(wrap)}}
play.onclick=()=>{playing=!playing;if(cursor>=rows.length-1)cursor=0;play.textContent=playing?'暂停':'播放';last=null};
document.getElementById('restart').onclick=()=>{cursor=0;last=null;draw()};slider.oninput=()=>{cursor=+slider.value;draw()};
document.addEventListener('keydown',e=>{if(e.code==='Space'&&e.target.tagName!=='SELECT'){e.preventDefault();play.click()}});
function frame(t){if(playing&&last!==null){cursor+=(t-last)/1000*Number(rate.value)/data.config.dt;if(cursor>=rows.length-1){cursor=rows.length-1;playing=false;play.textContent='播放'}}last=t;draw();requestAnimationFrame(frame)}draw();requestAnimationFrame(frame);
</script></html>'''
    (destination / 'replay.html').write_text(page.replace('__DATA__', payload), encoding='utf-8')
