"""Assemble an offline Chinese explanation from the computed CSV/JSON files."""
from pathlib import Path
import base64
import csv
import html
import json

ROOT=Path(__file__).resolve().parent


def load(relative):
    return json.loads((ROOT/relative).read_text(encoding='utf-8'))


def picture(relative,caption):
    encoded=base64.b64encode((ROOT/relative).read_bytes()).decode('ascii')
    return f'<figure><img src="data:image/png;base64,{encoded}"><figcaption>{caption}</figcaption></figure>'


def table(head,rows):
    return '<div class="scroll"><table><thead><tr>'+''.join(f'<th>{html.escape(str(c))}</th>' for c in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{html.escape(str(c))}</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def main():
    geometry=load('geometry/summary.json')
    optical=load('optical/summary_n512.json')
    grids={key:512 for key in optical}
    if (ROOT/'optical/summary_n1024.json').exists():
        fine=load('optical/summary_n1024.json')
        optical.update(fine)
        grids.update({key:1024 for key in fine})
    modes=load('review/summary.json')
    cases=geometry['cases']
    grows=[]
    labels={'ideal':'理想 CB','xstrip_1':'贯通 X 区，c=1','crossblank_0p5':'十字留白，g=0.5',
            'crossblank_1':'十字留白，g=1','squareblank_1':'中心方孔，g=1','squareblank_2':'中心方孔，g=2',
            'registry_p4':'上下相对位移 p/4','registry_p2':'上下相对位移 p/2'}
    for c in cases:
        if c['id'] in labels:
            m=c['actual_plus_peaks']
            grows.append([labels[c['id']],f"{m['R01']:.4f}",f"{100*m['side_cv']:.2f}%" if m['side_cv'] is not None else '—',
                          ', '.join(f'{x:.4f}' for x in c['actual_plus_peak_positions_um'][:3])])
    orows=[]
    for p,label in [('disk_r020','圆盘半径 0.20'),('disk_r010','圆盘半径 0.10'),('disk_r005','圆盘半径 0.05'),('disk_r010_y006','半径 0.10，y 偏心 0.06')]:
        orows.append([label]+[f"{optical[g][p]['port_sum']['successive_drop_ratios'][0]:.4f}" for g in ('ideal','cross_gap1')])
    gap_data=[]
    for c in cases:
        if c['id'] in ('crossblank_0p5','crossblank_1'):
            p=c['actual_plus_peaks']
            gap_data.append([labels[c['id']],', '.join(f'{x:.8f}' for x in p['heights']),', '.join(f'{x:.8f}' for x in p['drops'])])
    records={}
    for g in ('ideal','cross_gap1','square_gap2','phase_upper_pi'):
        records[g]={}
        for p in optical[g]:
            file=ROOT/'optical'/f'scan_n{grids[g]}_{g}_{p}.csv'
            rows=list(csv.DictReader(file.open(encoding='utf-8-sig')))
            records[g][p]={key:[float(r[key]) for r in rows] for key in ('s_um','port_sum','port_diff','raw_sum','same_arm_xy_a','same_arm_xy_b')}
    scale=records['ideal']['disk_r020']['port_sum'][0]
    mode_rows=[]
    for r in modes['selected']:
        if r['case']=='main only' or (r['case']=='main + Gaussian receiver' and r['delta']==.45) or r['case']=='main + full collection':
            mode_rows.append([r['case'],', '.join(f"{r[f'P{n}']:.6f}" for n in range(5)),f"{r['R01']:.5f}",f"{r['side_cv']*100:.2f}%"])
    convergence_note='1024 网格复核完成后，另见 optical/convergence.json 与 README.txt。主表为同一套 512 网格的比较。'
    if (ROOT/'optical/convergence.json').exists():
        convergence_note='主表的理想与十字留白均使用 1024 网格；512→1024 的相长端口整条曲线最大变化分别约为中心标度的 0.126%/0.275%。下降量之比更敏感，十字留白宽圆盘比值从 0.6595 变为 0.6333，宜按约 0.63 理解。其他结构只跑 512 网格；完整误差见 optical/convergence.json。'

    body='''<h1>CB 中心结构与收集光路：具体构造和数据</h1>
<p class="lead">本次找到了一个明确的中心几何机制：中央贯通空带在两旋转图像中的重合，会给单干涉端口一个局限在中心附近的附加项。g=0.5–1 μm 时首步下降约为后续的 1.88–2.20 倍。有限光瞳会压低该效应；理想互补端口的原始和会消掉它。</p>
<p>以下是可复现的条件性构造，没有读取公司 D4C 数据，也没有调用真实 RCWA。p=2 μm 为已知；L=40 μm、照明强度 1/e² 半径 w=12 μm、r±1=0.2、r0=0 均为显式示例假设。保留原始标量功率，各条曲线没有逐扫描点归一化。Dₙ=Pₙ−Pₙ₊₁，以真实局部极大值计算。</p>
<h2>1. 中心结构究竟怎么改</h2>
<p>以方框内 |y|≥|x| 为 X 区，其余为 Y 区。蓝色/橙色表示宏观 X/Y 区，深色条纹只是 p=2 μm、50% 占空比的图形说明，不会再乘入已经包含周期结构的 RCWA 场。</p>'''
    body+=picture('geometry/center_geometry.png','图 1：不同中心构造。应比较上中贯通 X 区、上右十字留白、下左小方孔，以及下中/下右相位错位。它们不是同一种中心变化。')
    body+='''<p><b>贯通 X 区：</b>把 |x|&lt;c/2 内原本属于 Y 的位置改为 X，X/Y 保持互斥；它只补上中心很小的一块区域。<b>十字留白：</b>把 |x|&lt;g/2 或 |y|&lt;g/2 的周期衍射项去掉，沿整条十字延伸。<b>方孔：</b>只在 |x|&lt;g/2 且 |y|&lt;g/2 去掉周期项。这里“空白”只表示示例中的 ±1 响应为零，不代表真实表面零反射；真实模型需要保留 flat 区零级和边缘衍射。</p>
<p><b>上下条纹错位：</b>对各衍射级 cₘ→cₘ exp(−imGδ)，G=2π/p。本例上半 δ=0，下半 δ=p/4 或 p/2，其他区域不动。它通常改变峰的位置和端口明暗，而不是只增强中心。</p>'''
    body+=table(['结构（μm）','真实峰 D₀/D₁','D₁,D₂,D₃ 的 CV','前三个峰位置（μm）'],grows)
    body+='''<p>完整收集的几何对照采用 X-only 复场 Eₛ=A Mₓ r[eⁱᴳ⁽ᵘ⁺ˢ⁻δ⁾+e⁻ⁱᴳ⁽ᵘ⁺ˢ⁻δ⁾]，第二臂为空间旋转 Eₛ(−u,−v)，I±=½∫|Eₛ±Eₛ,rot|²。完整收集是几何诊断基准，不表示某个实际 NA 可以收到全部空间频率。X 积分在每个 step 边界处分段，y 积分解析；96 与 192 点积分的最大差为 1.2×10⁻¹⁴。</p>'''
    body+=table(['留白结构','P₀…P₄，原始合成标量功率','D₀…D₃'],gap_data)
    body+='''<p>十字留白降低了中心的绝对高度：理想中心约 0.07993463，g=1 后约 0.06952023。其第一侧峰从约 0.07245007 降到 0.05956921，损失更大。因此“中心相对侧峰突出”不等于中心绝对功率增加。</p>
<h2>2. 为什么十字留白能只改变中心附近</h2>
<p>对 X 三角区，十字留白等价于删掉中央竖条 H=1{|x|&lt;g/2}。扫描后两臂看到 H_A=H(u+s)、H_B=H(s−u)。窗口乘积严格分解为：</p>
<div class="eq">M_A M_B = M_A⁰ M_B⁰ [1 − H_A − H_B + H_A H_B]</div>
<p>最后的 +H_AH_B 是两空带的交集。它仅在 |2s|&lt;g 时存在；s=0 时两空带重合，移动后分离。它作为单端口干涉项出现，不需要给中心 mask 赋值大于 1。</p>'''
    body+=picture('geometry/hole_overlap_decomposition.png','图 2：上排蓝线为实际构造的 plus 端口，橙线只在代数上删除 H_AH_B 项；两线只在中心附近不同。下排展示该项支持范围：g=0.5/1 时分别在 |s|=0.25/0.5 μm 结束。删除项是诊断分解，不是另一块可制造 mark。')
    body+='''<p>g=0.5 和 g=1 的中心交集贡献分别为 0.00428337 和 0.00520720。只删掉该项，保留两臂自身功率及其余交叉项，等间距采样的比值从 1.8816/2.2016 回到 1.0332/1.0516。这把变化定位到一个具体代数项。真正局部峰的数据见上表与 CSV。</p>
<p class="notice">通道限制：该项在 minus 端口取相反号。因此它对 IΣ=Iplus+Iminus 的贡献严格为零。若 D4C 当前比较的确实是原始匹配互补和，此结果不能直接作为最终归因；需要先定位和信号中的载波来源。</p>
<h2>3. 同一个中心结构经过不同光瞳会怎样</h2>
<p>把同一二维复场送入 Fourier 平面：Fₛ=FFT(Eₛ)。固定物镜 NA=0.45、λ=0.633 μm；在 +X 一级 (fₓ,fᵧ)=(0.5,0) cycles/μm 周围设置不同半径的收集圆盘，所有圆盘与物镜光瞳相交。两臂 a=D Fₛ(k)、b=D Fₛ(−k)，不对第二臂做共轭。偏心光瞳的中心改为 (0.5,0.06)。</p>
<div class="eq">I± = ½(‖a‖²+‖b‖²) ± Re⟨a,b⟩； IΣ = ‖a‖²+‖b‖²</div>
<p>这是完整 X+Y 场、固定复系数、相同输入功率下的光路对照。有限光瞳使实空间检测算子成为非局部算子；几何交集不再等于最终检测重叠，窄中心项可以被抹平。</p>'''
    body+=table(['收集圆盘（cycles/μm）','理想 CB，plus D₀/D₁','十字留白 g=1，plus D₀/D₁'],orows)
    body+=f'<p>{convergence_note}</p>'
    body+='''<p>完整收集约 2.20 的结果，到半径 0.20 的实际局部光瞳后约为 0.63，表明“有中心空带”与“检测到中央两倍差”之间还隔着收集光路。下面可以切换结构、光瞳和通道；全部曲线使用同一个理想宽光瞳中心标度，保留幅值变化。</p>
<div class="controls"><label>结构<select id="geom"><option value="ideal">理想 CB</option><option value="cross_gap1" selected>十字留白 g=1</option><option value="square_gap2">中心方孔 g=2</option><option value="phase_upper_pi">上半 X 相位 π</option></select></label>
<label>光瞳<select id="pupil"><option value="disk_r020">半径 0.20</option><option value="disk_r010">半径 0.10</option><option value="disk_r005">半径 0.05</option><option value="disk_r010_y006">半径 0.10，偏心 y=0.06</option><option value="disk_r020_edge_y004">半径 0.20，截取 fy≥0.04</option></select></label>
<label>通道<select id="channel"><option value="port_sum">相长端口 Iplus</option><option value="port_diff">相消端口 Iminus</option><option value="raw_sum">原始和 Iplus+Iminus</option></select></label></div>
<svg id="chart" viewBox="0 0 1000 370" role="img" aria-label="切换结构和光瞳后的扫描曲线"></svg><p id="chartnote"></p><div id="peaktable"></div>
<p>原始和的跨臂项恒等消失。有限光瞳仍允许同一臂的 X/Y 或级次交叉项存在：实际程序已分别保存 same_arm_xy_a/b 与 cross_arm_real。在这些示例中，未验证出原始和中一串符合所述规律的 1 μm 峰；512 网格很小的离散起伏在 1024 复核中消失，不能当作复现。</p>
<p><b>同臂耦合的直接数据：</b>上半 X 相位变 π 时，对称圆盘内的 X/Y 交叉项因对称性抵消；偏心或截取光瞳后会保留。1024 网格、s=5 μm，偏心圆盘的原始和为 0.0241095764，X/Y 分开求功率再相加为 0.0243754752，交叉项 −0.0002658988（−1.09%）；截取 fy≥0.04 后分别为 0.00278808573、0.00309750128，交叉项 −0.00030941554（−9.99%）。对称半径 0.20 圆盘中的交叉项约 10⁻¹⁹。这是同一结构与实际收集算子耦合的明确例子，但没有复现中心两倍。</p>
<div class="eq">PXY = ∫Ω |FX+FY|² = PX+PY+2 Re∫Ω FX FY*；有限 Ω 可使原本全平面正交的场不再正交。</div>
<h2>4. 真实重叠区域怎么设，为什么不能直接把两套场加倍</h2>
<p>真正 X/Y 交叉刻蚀的中心应定义新的互斥 C 区：E=A[MₓFₓ+MᵧFᵧ+M_CF_C+MflatFflat]，各区域不重叠。F_C 的复系数来自局部交叉单元 RCWA、其他局部计算或标定；一份一维周期 R 不会自动给出它。</p>
<p>附带计算使用 1/2 μm 中心方形 C 区，假设四个中心衍射系数为 r/√2、r/√2、eⁱχr/√2、eⁱχr/√2，χ=0,π/2,π。这样系数平方和保持与原 X/Y 区相同，而不是把中心场机械翻倍。这是显式假设，不是交叉刻蚀预测。对所测宽、窄、偏心光瞳没有得到中心两倍；峰下降比约 0.35–0.52。</p>
<p>该模型把中心与外围的检测功率精确拆为 P=Pbulk+PC+2Re⟨D Fbulk,D FC⟩。因此可以直接检查中心自身功率，还是其与外围的相干交叉项造成变化。分解误差约 7.9×10⁻¹⁸；512→1024 关键采样点的 plus 差低于 0.031%。完整数据在 overlap 子目录。</p>
<h2>5. 一个确实能给局域中心响应的收集模式例子</h2>
<p>以下只是验证“中心小结构与检测模式耦合”能否做到的条件性正例。假设中心有交叉偏振有效项 δr=δ exp[−(x²+y²)/d²]，d=0.3 μm；另一个正交偏振被半径 a=0.5 μm 的归一化高斯模式 ψ 收集。需要实际系统接受该偏振和该空间模式，且不能被中央遮挡拒绝。它不是 D4C 已知配置。</p>
<div class="eq">Jmode(s)=δ²[2/(waα)]² exp[−2s²/(b²+d²)]； α=w⁻²+a⁻²+d⁻²，b²=(w⁻²+a⁻²)⁻¹</div>
<p>同一个局部结构，全空间模收集时 Jall(s)=δ²d²/(w²+d²)·exp[−2s²/(w²+d²)]。w=12 时，窄模式的 J(1)/J(0)=0.002767，而全收集为 0.986216。前者只影响中心附近，后者造成宽响应。</p>'''
    body+=table(['条件','真实局部峰 P₀…P₄ / 主通道中心标度','D₀/D₁','后续下降 CV'],mode_rows)
    body+=picture('review/mode_selection.png','图 3：橙色为窄模式检测中心项，右图首个下降约 0.192、后续约 0.093/0.090/0.086。绿色为同一中心结构的全模式收集，它把整段曲线抬高，并没有中心独有两倍。')
    body+='''<p>这个正例还要求弱主通道：ηmain=0.001、δ=0.45。保持 δ 不变，把 ηmain 提到 0.01/0.08，比值降至 1.1174/1.0248。因此它不能被泛化为“任意小中心结构都能解释”。所构造 thin-Jones 模型用充分条件 4ηmain+δ²≤1 限制点值幅度。对原始互补和 2ηmain q+J，载波仍相消，没有侧峰；不能把这个单端口正例移用到和信号。</p>
<h2>6. 接到现有 RCWA 程序的顺序</h2>
<ol><li>由实际入射向量计算 r=R a，保留复相位及正确模态功率；X/Y 使用各自偏振定义。</li><li>以互斥的二维宏观窗口限定 X、Y、flat、center；上下位置原点写入 exp(−imGδ)。不重复乘 50% duty 的微观二值条纹。</li><li>构造 Eₛ(u,v)=A(u,v)ΣⱼMⱼ(u+s,v)Σₘrⱼₘ exp[imGⱼ·(u+s,v)]，加入真实 flat/center 系数。</li><li>按实际光路顺序传播到 pupil、field stop、detector mode。场阑在像面时应乘像面场后再传播，不能直接当作 Fourier 圆盘。</li><li>输出两个臂功率、复交叠 C、两个互补端口、原始和、同臂级次/区域交叉项；真实局部峰提取后比较 D₀…D₃。</li><li>中心十字的额外 gap 必须是超出原周期单元的真实区域。如果只是 50% duty 中原本的空槽，它已包含在 RCWA 中，不能再加一个宏观空带重复扣除。</li></ol>
<p>专利只支持整体 CB 结构背景，不证明本文构造的尺寸和光路：<a href="https://patents.google.com/patent/WO2022258371A1/en">WO2022258371A1</a>。场阑边缘引起阶次串扰的可能性也见 <a href="https://patents.google.com/patent/US7564534B2/en">US7564534B2</a>；具体是否发生仍由同链分解验证。</p>
<p>文件对应：geometry/ 保存几何、真实峰与孔重叠分解；optical/ 保存固定光瞳的全部原始曲线及网格复核；overlap/ 保存三区域中心系数的条件性试验；review/ 保存空间模式例子和效率扫描。所有脚本均可用 uv run --with numpy --with scipy --with matplotlib 脚本路径 重跑。</p>'''
    js='''const curves=CURVES, metrics=METRICS, scale=SCALE, grids=GRIDS;
const $=id=>document.getElementById(id);const names={port_sum:'相长端口',port_diff:'相消端口',raw_sum:'原始互补和'};
function render(){const g=$('geom').value,p=$('pupil').value,c=$('channel').value;
const a=curves[g][p],b=curves.ideal[p],m=metrics[g][p][c];
const sets=[a[c].map(v=>v/scale),b[c].map(v=>v/scale)];const lo=Math.min(0,...sets.flat()),hi=Math.max(...sets.flat())*1.08||1;
const X=x=>65+x/5*900,Y=y=>315-(y-lo)/(hi-lo)*270;
let s='';for(let i=0;i<=5;i++){let x=X(i);s+=`<line x1="${x}" x2="${x}" y1="45" y2="315" stroke="#ddd"/><text x="${x}" y="340" text-anchor="middle">${i}</text>`;}
for(let i=0;i<=5;i++){let v=lo+(hi-lo)*i/5,y=Y(v);s+=`<line x1="65" x2="965" y1="${y}" y2="${y}" stroke="#ddd"/><text x="55" y="${y+5}" text-anchor="end">${v.toFixed(2)}</text>`;}
sets.forEach((y,k)=>{let d=y.map((v,i)=>(i?'L':'M')+X(a.s_um[i]).toFixed(2)+','+Y(v).toFixed(2)).join(' ');s+=`<path d="${d}" fill="none" stroke="${k?'#777':'#087f8c'}" stroke-width="${k?1.3:2}" ${k?'stroke-dasharray="5 4"':''}/>`;});
s+='<text x="500" y="365" text-anchor="middle">扫描 s (μm)；蓝绿=所选结构，灰虚线=同光瞳理想结构</text>';$('chart').innerHTML=s;
let ratio=m.successive_drop_ratios[0];$('chartnote').textContent=(c==='raw_sum'?'这是原始和；小起伏未经物理峰认定，不能从任意局部极值推断 p/2 峰列。':`${names[c]}：中心是否为峰=${m.has_central_maximum?'是':'否'}，前两个下降之比=${Number.isFinite(ratio)?ratio.toFixed(5):'无有效比值'}。`)+` 网格 N=${grids[g]}。`;
let t='<table><tr><th>局部峰</th><th>位置 μm</th><th>原始标量功率</th><th>到下一峰绝对下降</th></tr>';
m.peak_heights.slice(0,5).forEach((v,i)=>t+=`<tr><td>${i}</td><td>${m.peak_positions_um[i].toFixed(5)}</td><td>${v.toFixed(8)}</td><td>${m.absolute_drops[i]===undefined?'—':m.absolute_drops[i].toFixed(8)}</td></tr>`);$('peaktable').innerHTML=t+'</table>';}
['geom','pupil','channel'].forEach(id=>$(id).addEventListener('change',render));render();'''
    js=js.replace('CURVES',json.dumps(records,separators=(',',':'))).replace('METRICS',json.dumps(optical,separators=(',',':'))).replace('SCALE',repr(scale)).replace('GRIDS',json.dumps(grids))
    css='''body{max-width:1160px;margin:32px auto;padding:0 22px 60px;font-family:"Microsoft YaHei",system-ui,sans-serif;color:#19323b;line-height:1.85;background:#fbfcfd}h1{line-height:1.4;font-size:30px}h2{font-size:23px;margin-top:38px;border-bottom:2px solid #bedbdc;padding-bottom:7px}.lead{font-size:19px;background:#e6f4f2;padding:18px;border-radius:8px}.notice{background:#fff2d7;padding:15px;border-left:4px solid #bf8c29}.eq{font-family:Cambria,serif;font-size:20px;text-align:center;padding:14px;background:white;border:1px solid #ddd}figure{margin:25px 0}img{max-width:100%;height:auto}figcaption{font-size:14px;color:#4b6169}table{border-collapse:collapse;width:100%;font-size:14px;margin:12px 0}th,td{padding:9px;border:1px solid #cbd5db;vertical-align:top}th{background:#eaf0f3}tr:nth-child(even){background:white}.scroll{overflow:auto}.controls{display:flex;flex-wrap:wrap;gap:18px;padding:16px;background:#e6f4f2}select{display:block;padding:8px;min-width:180px}svg{width:100%;background:white}a{color:#087f8c}li{margin:8px 0}@media print{body{max-width:none;margin:0}figure,table{break-inside:avoid}.controls,svg,#chartnote,#peaktable{display:none}}'''
    doc=f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CB中心结构与光路耦合：构造及数据</title><style>{css}</style></head><body>{body}<script>{js}</script></body></html>'
    path=ROOT/'CB中心结构与光路耦合_构造和数据.html'
    path.write_text(doc,encoding='utf-8')
    (ROOT/'report_interactive.js').write_text(js,encoding='utf-8')
    print(f'Created {path.name}: {len(doc)} characters; {len(records)} geometry groups, {sum(len(x) for x in records.values())} optical cases.')


if __name__=='__main__':main()
