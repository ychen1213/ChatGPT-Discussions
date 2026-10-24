"""Render Chinese Markdown/HTML and scientific figures from persisted results."""
from pathlib import Path
import argparse, csv, json, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import markdown

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ah53 import load_model

plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','SimHei','DejaVu Sans'], 'axes.unicode_minus':False,
                    'figure.dpi':130,'savefig.dpi':160,'axes.spines.top':False,'axes.spines.right':False})
COLORS=['#263a55','#008574','#dc7040','#8c5ba8','#4e82ca','#bf5b76']
LABELS={'local_P_fine':'P 参数化','local_T_direct_fine':'T_direct 直接三角面','local_V_direct_fine':'V_direct 5 nm',
        'local_T_from_P':'T_from_P 参数化导出','local_V_from_P':'V_from_P','local_V_from_T':'V_from_T','local_V_from_Tdirect':'V_from_Tdirect'}

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def fmt(v,n=4):return '未记录' if v is None else f'{float(v):.{n}g}'
def table(headers,rows):return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+['|'+'|'.join(map(str,row))+'|' for row in rows])
def save(fig,path):fig.savefig(path,bbox_inches='tight');plt.close(fig)

def figures(out,rows):
    dest=out/'figures';dest.mkdir(exist_ok=True)
    model=lambda id:load_model(out/'models'/id)
    ref=model('reference_local');pf=model('local_P_fine')
    fig,ax=plt.subplots(figsize=(10,3.4))
    for center in ref.centers/1000:ax.add_patch(Rectangle((center-.8,-2),1.6,4,color=COLORS[1],alpha=.85))
    for x in (-8,-4,4,8):ax.axvline(x,color='#728093',ls='--',lw=.8)
    ax.set(xlim=(-8.5,8.5),ylim=(-2.35,2.7),xlabel='X / µm',ylabel='Z / µm',title='AH53 名义布局：16 µm 母单元中的三条纹')
    for a,b,t in [(-8,8,'16 µm 母周期'),(-4,4,'8 µm 条纹区')]:
        y=2.5 if a==-8 else 2.15;ax.annotate('',(a,y),(b,y),arrowprops={'arrowstyle':'<->','color':COLORS[0]});ax.text((a+b)/2,y+.04,t,ha='center',fontsize=9)
    ax.set_aspect('equal');save(fig,dest/'01_nominal_layout.png')

    fig,axes=plt.subplots(2,1,figsize=(11,5.5))
    for z,c in zip((-1167.,137.,413.,677.),COLORS):
        p=ref.contour(1,z,step_nm=1)
        for ax in axes:ax.plot(p[:,0],p[:,1],color=c,label=f'Z={z:g} nm',lw=1.3)
    axes[0].plot([-800,-800,800,800,-800],[0,300,300,0,0],'--',color='#8993a0',label='理想矩形')
    for ax in axes:ax.set(xlabel='X / nm',ylabel='Y / nm');ax.set_aspect('equal',adjustable='box')
    axes[0].set_title('已保存参考：理想轮廓与不同 Z 的合成形貌');axes[0].legend(ncol=5,fontsize=8)
    axes[1].set(xlim=(-840,-670),ylim=(180,325),title='左圆肩放大：局部挑战在中央条纹 Z≈400 nm')
    fig.tight_layout();save(fig,dest/'02_cross_sections.png')

    fig,axes=plt.subplots(1,2,figsize=(11,4.2));ids=['reference_local','local_P_fine','local_T_direct_fine','local_T_from_P','local_V_direct_fine']
    for n,id in enumerate(ids):
        p=model(id).contour(1,413.,step_nm=.5)
        for ax in axes:ax.plot(p[:,0],p[:,1],color=COLORS[n],ls=['-','--','-.',':','-'][n],label='参考' if n==0 else LABELS[id],lw=1.4)
    axes[0].set(xlim=(-810,-700),ylim=(215,318),title='左圆肩');axes[1].set(xlim=(675,810),ylim=(205,318),title='右圆肩')
    for ax in axes:ax.set(xlabel='X / nm',ylabel='Y / nm');ax.set_aspect('equal');ax.grid(alpha=.15)
    axes[0].legend(fontsize=8);fig.suptitle('相同独立截面 Z=413 nm：各自已保存几何');fig.tight_layout();save(fig,dest/'03_shoulder_comparison.png')

    fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True)
    for n,id in enumerate(['local_P_fine','local_T_direct_fine','local_V_direct_fine','local_V_from_T']):
        with np.load(out/'profiles'/(id+'.npz')) as data:z=data['z_nm'];p=data['candidate'][1,1];r=data['reference'][1,1]
        if n==0:
            axes[0].plot(z/1000,(r[0]+r[1])/2-np.mean((r[0]+r[1])/2),color=COLORS[0],label='参考')
            axes[1].plot(z/1000,r[1]-r[0]-1600,color=COLORS[0])
            zz=z[::3];h=np.array([ref.contour(1,x,2)[:,1].max() for x in zz]);axes[2].plot(zz/1000,h,color=COLORS[0])
        axes[0].plot(z/1000,(p[0]+p[1])/2-np.mean((p[0]+p[1])/2),color=COLORS[n+1],label=LABELS[id],lw=1)
        axes[1].plot(z/1000,p[1]-p[0]-1600,color=COLORS[n+1],lw=1)
        m=model(id);h=np.array([m.contour(1,x,2)[:,1].max() for x in zz]);axes[2].plot(zz/1000,h,color=COLORS[n+1],lw=1)
    for ax,y in zip(axes,['中心去均值 / nm','CD −1600 / nm','最高高度 / nm']):ax.set_ylabel(y);ax.grid(alpha=.15)
    axes[0].legend(ncol=3,fontsize=8);axes[0].set_title('中央条纹沿 Z 的实际边缘与顶部；边缘取 Y=150 nm');axes[-1].set_xlabel('Z / µm');fig.tight_layout();save(fig,dest/'04_edge_waviness.png')

    fig,axes=plt.subplots(1,2,figsize=(11,4.3))
    for r in rows:
        c=COLORS[{'P':1,'T_direct':2,'V_direct':4}[r['method']]];marker='s' if r['scene']=='full' else ('o' if 'fine' in r['id'] else '^')
        axes[0].scatter(float(r['array_payload_bytes'])/1e6,float(r['section_p95_nm']),c=c,marker=marker,s=60)
        axes[0].annotate(r['id'].replace('local_','L_').replace('full_','F_'),(float(r['array_payload_bytes'])/1e6,float(r['section_p95_nm'])),fontsize=6,xytext=(3,4),textcoords='offset points')
    axes[0].set(xscale='log',yscale='log',xlabel='实际数组负载 / MB（十进制）',ylabel='双向截面距离 P95 / nm',title='A 九组：总体自由轮廓统计')
    axes[0].axhline(1,color='gray',ls='--',lw=.8);axes[0].grid(alpha=.15)
    local=[r for r in rows if r['scene']=='local'];x=np.arange(len(local));w=.16
    regs=['left_wall','left_shoulder','top','right_shoulder','right_wall']
    for j,reg in enumerate(regs):axes[1].bar(x+(j-2)*w,[float(r[reg+'_p95_nm']) for r in local],w,label=reg,color=COLORS[j])
    axes[1].axhline(1,color='gray',ls='--',lw=.8);axes[1].set_xticks(x,[r['id'].replace('local_','').replace('_','\n') for r in local],fontsize=7)
    axes[1].set(ylabel='分区 P95 / nm',title='局部五个区域：不以大片顶面掩盖圆肩');axes[1].legend(fontsize=7,ncol=2);fig.tight_layout();save(fig,dest/'05_error_resources.png')

    full=model('full_P_fine');fig=plt.figure(figsize=(11,6));ax=fig.add_subplot(111,projection='3d')
    for i,c in enumerate(full.centers):
        zs=np.linspace(-24000,24000,121);xs=np.linspace(c-750,c+750,32);X,Z=np.meshgrid(xs,zs);Y=np.empty_like(X)
        from ah53.evaluate import top_intersections
        for j,z in enumerate(zs):Y[j]=top_intersections(full.contour(i,z,step_nm=10),xs)
        ax.plot_surface(X/1000,Z/1000,Y/1000,cmap='viridis',vmin=.26,vmax=.33,linewidth=0,rstride=1,cstride=1,alpha=.95)
    ax.set(xlabel='X / µm',ylabel='Z / µm',zlabel='Y / µm',title='全域 P 保存数据的顶面抽样：48×48 µm，三个母单元、九条纹\n科学示意图 Y 视觉比例约放大 20 倍；查看器默认真实比例')
    ax.set_box_aspect((48,48,10));ax.set_zlim(0,.5);ax.view_init(elev=30,azim=-58);save(fig,dest/'06_full_mark.png')

    with (out/'conversions.csv').open(encoding='utf-8-sig') as stream:bc=[r for r in csv.DictReader(stream) if r['scene']=='local']
    fig,ax=plt.subplots(figsize=(9,4));x=np.arange(4)
    for shift,key,label,c in [(-.18,'section_p95_nm','相对共同参考：总误差',COLORS[0]),(.18,'incremental_section_p95_nm','相对自身上游：新增误差',COLORS[1])]:
        bars=ax.bar(x+shift,[float(r[key]) for r in bc],width=.36,label=label,color=c)
        ax.bar_label(bars,fmt='%.3f',fontsize=8,padding=3)
    ax.set_xticks(x,[r['path_id']+'\n'+r['method'] for r in bc]);ax.set(ylabel='双向截面距离 P95 / nm',title='转换误差分开测量；不可将统计量相加',ylim=(0,3));ax.legend(fontsize=9);fig.tight_layout();save(fig,dest/'07_conversion_errors.png')

    fig,axes=plt.subplots(2,1,figsize=(11,5.5),sharex=True)
    full_voxel_id=next(r['id'] for r in rows if r['scene']=='full' and r['method']=='V_direct')
    for n,id in enumerate(['full_P_fine','full_T_direct_fine',full_voxel_id]):
        with np.load(out/'profiles'/(id+'.npz')) as data:z=data['z_nm'];p=data['candidate'][4,1];r=data['reference'][4,1]
        if n==0:
            axes[0].plot(z/1000,(r[0]+r[1])/2-np.mean((r[0]+r[1])/2),c=COLORS[0],label='参考',lw=1)
            axes[1].plot(z/1000,r[1]-r[0]-1600,c=COLORS[0],lw=1)
        axes[0].plot(z/1000,(p[0]+p[1])/2-np.mean((p[0]+p[1])/2),c=COLORS[n+1],label=id,lw=.8,alpha=.8)
        axes[1].plot(z/1000,p[1]-p[0]-1600,c=COLORS[n+1],lw=.8,alpha=.8)
    axes[0].set(ylabel='中心去均值 / nm',title='完整48 µm长度：中央条纹，Y=150 nm');axes[0].legend(ncol=4,fontsize=8)
    axes[1].set(xlabel='Z / µm',ylabel='CD −1600 / nm');fig.tight_layout();save(fig,dest/'08_full_edge_waviness.png')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',default='20261024_v2');ap.add_argument('--skip-figures',action='store_true');args=ap.parse_args()
    out=ROOT/'results'/args.run
    with (out/'metrics.csv').open(encoding='utf-8-sig') as f:A=list(csv.DictReader(f))
    with (out/'conversions.csv').open(encoding='utf-8-sig') as f:B=list(csv.DictReader(f))
    by={r['id']:r for r in A+B};details={r['id']:read(out/'details'/(r['id']+'.json')) for r in A+B};manifest=read(out/'manifest.json');prep=read(out/'preparation.json');config=manifest.get('configuration') or read(ROOT/'configs/default.json')
    if not args.skip_figures:figures(out,A)
    fields={'RUN_ID':args.run}
    p,t,v=[by[s] for s in ['local_P_fine','local_T_direct_fine','local_V_direct_fine']]
    fields['SUMMARY']=f"已实际完成 A 的 9 组、B 的 4 条局部路径、1 条全域 P→T 路径和一次局部编辑。局部细档的双向截面距离 P95 分别为 P {fmt(p['section_p95_nm'])} nm、T_direct {fmt(t['section_p95_nm'])} nm、5 nm 体素 {fmt(v['section_p95_nm'])} nm。这里的指标是规定截面的距离，不能解释成完整三维曲面的全域误差上界。"
    syn=config['synthetic'];fields['SHAPE_DETAILS']=f"配置使用随机相位有限傅里叶叠加：最短波长 {min(syn['wavelengths_nm'])} nm，幅值按无限域理论 RMS 归一化，有限窗口重新测量。左／右圆肩特征尺度 {syn['shoulder_scale_nm']} nm、变化约 ±{syn['shoulder_relative_variation']*100:g}%；顶部横向拱高 {syn['top_transverse_rise_nm']} nm。中央母单元的中间条纹在 Z={syn['local_feature']['z_center_nm']} nm 有局部连续挑战：沿线半高宽 {syn['local_feature']['z_hwhm_nm']} nm、左侧位移幅度 {syn['local_feature']['left_displacement_nm']} nm、顶部增加 {syn['local_feature']['height_nm']} nm。圆肩由与两侧共享端点、对齐切线方向（G1 几何光顺）的解析 Bézier 段定义；参考生成器不调用候选样条。"
    measured=[]
    for id in ['local_P_fine','local_T_direct_fine','local_V_direct_fine','full_P_fine']:
        g=details[id]['metrics']['profiles']['actual_geometry'];measured.append([id,fmt(g['width_y150_mean_nm']),', '.join(fmt(x,3) for x in g['width_y150_fluctuation_rms_nm']),', '.join(fmt(x,3) for x in g['center_y150_fluctuation_rms_nm'])])
    fields['MEASURED_SHAPE']='最终模型重新测量，逐条纹去均值：\n\n'+table(['模型','平均 CD / nm','各条 CD RMS / nm','各条中心 RMS / nm'],measured)
    height_rows=[]
    for id in ['local_P_fine','local_T_direct_fine','local_V_direct_fine','full_P_fine']:
        g=details[id]['metrics']['profiles']['actual_geometry']
        height_rows.append([id,'～'.join(fmt(x,5) for x in g['height_range_nm']),', '.join(fmt(x,3) for x in g['height_maximum_per_section_rms_nm']),fmt(g['height_measurement_z_spacing_nm'])])
    fields['MEASURED_SHAPE']+='\n\n从实际各 Z 截面的最高点测得：\n\n'+table(['模型','最高点高度范围 / nm','各条高度起伏 RMS / nm','测量 ΔZ / nm'],height_rows)+'\n\n中央条纹含额外局部凸起，因此实际高度 RMS 可以超过随机场单独设定的 4 nm；这些是最终几何的统计值。'
    fields['METRIC_DEFINITION']='本次主边界指标明确采用**双向、按弧长加权的 XY 截面点到实际线段距离**。局部取 Z=−1783、−1167、−443、137、413、677、1549 nm，全域另取 8 个指定截面，覆盖中央局部起伏。这些位置不在 40/80 nm 构建节点上。分别报告左壁、左圆肩、顶面、右圆肩、右壁，底面和人工 Z 封口不参与主指标。参考和 P 评价轮廓以约 1 nm 几何步长离散，三角面按实际面片相交，体素按实际标签边界求交；距离计算投影到实际线段，不是稀疏顶点最近邻。两方向分别保存，统计采样步长约 2 nm。'
    conv=prep['reference_convergence'];fields['REFERENCE_CONVERGENCE']=f"在中央条纹 Z=413、677 nm 处，将参考轮廓步长由 1 nm 加密到 0.25 nm，实测截面距离的最大差异为 {fmt(conv['observed_discretization_estimate_nm'],5)} nm。这是本次高曲率处的数值收敛证据，不是全域解析上界；它也限定了极小误差的可解释精度。"
    fields['TABLE_A']=table(['组别','RMS / nm','P95 / nm','采样最大 / nm','负载 MB','文件 MB','构建 s','峰值 RSS MB'],[[r['id']]+[fmt(r[k]) for k in ['section_rms_nm','section_p95_nm','section_max_nm']]+[fmt(float(r['array_payload_bytes'])/1e6),fmt(float(r['file_bytes'])/1e6),fmt(r['construction_seconds']),fmt(float(r['peak_rss_bytes'])/1e6)] for r in A])
    fields['REGION_TABLE']=table(['组别','左壁 P95','左圆肩 P95','顶面 P95','右圆肩 P95','右壁 P95'],[[r['id']]+[fmt(r[k+'_p95_nm']) for k in ['left_wall','left_shoulder','top','right_shoulder','right_wall']] for r in A])+'\n\n各分区单位均为 nm；完整 RMS/P95/最大值及 CD、中心指标见 CSV 和 `details/*.json`。'
    fields['A_INTERPRETATION']='各表示粗→细的实际变化：\n\n'+table(['表示','粗档 P95 / nm','细档 P95 / nm','细/粗比'],[[m,fmt(by[f'local_{m}_coarse']['section_p95_nm']),fmt(by[f'local_{m}_fine']['section_p95_nm']),fmt(float(by[f'local_{m}_fine']['section_p95_nm'])/float(by[f'local_{m}_coarse']['section_p95_nm']))] for m in ['P','T_direct','V_direct']])+'\n\n该合成参考的肩部和顶面很平滑，部分区域本身是低阶解析曲线，会有利于分段样条；因此本轮不能排除合成先验偏置。直接三角面无需参数化也已成功生成与独立查询。'
    fields['TABLE_B']=table(['路径','输出','总 P95 / nm','相对上游 P95 / nm','转换 s','源链 MB','派生 MB','全部保存 MB'],[[r['path_id'],r['id'],fmt(r['section_p95_nm']),fmt(r['incremental_section_p95_nm']),fmt(r['construction_seconds'])]+[fmt(float(r[k])/1e6) for k in ['source_chain_bytes','derived_file_bytes','all_chain_saved_bytes']] for r in B if r['scene']=='local'])
    fields['B_INTERPRETATION']='T_from_P 的沿 Z 导出节点相对输入观测平移半步，端点仍保留，间距保持约 40 nm。这样实际测试拟合后的连续几何再采样，避免只在插值原节点导出而恰好得到与 T_direct 相同的顶点。此导出相位是已记录的路径设置，不表示所有网格化算法必然有同样误差。\n\n'+table(['最终体素','总截面 RMS / nm','总 P95 / nm','Y150 CD RMS / nm','Y150 中心 RMS / nm'],[[id]+[fmt(by[id][k]) for k in ['section_rms_nm','section_p95_nm','cd_y150_rms_nm','center_y150_rms_nm']] for id in ['local_V_from_P','local_V_from_T','local_V_from_Tdirect']])
    fields['B_INTERPRETATION']+='\n\n分区 P95，表格每格为“相对参考总误差 / 相对上游新增误差”，单位 nm：\n\n'+table(['路径','左圆肩','顶面','右圆肩'],[[r['path_id']]+[fmt(details[r['id']]['metrics']['section_distance']['regions'][region]['p95_nm'])+' / '+fmt(details[r['id']]['incremental']['section_distance']['regions'][region]['p95_nm']) for region in ['left_shoulder','top','right_shoulder']] for r in B if r['scene']=='local'])
    fields['PAIRWISE_VOXELS']='各路径近界面错分率：\n\n'+table(['路径','相对参考，±20 nm 带','相对上游，±20 nm 带'],[[r['path_id'],fmt(float(r['material_near_fraction'])*100)+'%',fmt(float(r['incremental_material_near_fraction'])*100)+'%'] for r in B if r['scene']=='local'])
    if (out/'voxel_pairwise.json').exists():
        pairs=read(out/'voxel_pairwise.json')['pairs']
        fields['PAIRWISE_VOXELS']+='\n\n以下逐格比较同一网格的已保存标签，未回调参考：\n\n'+table(['比较','不同标签数','全域比例','条纹并集内比例','条纹体积净变化 nm³'],[[q['left_model']+' → '+q['right_model'],q['changed_cells'],fmt(q['changed_global_fraction']*100)+'%',fmt(q['changed_fraction_of_stripe_union']*100)+'%',fmt(q['material_volume_delta_right_minus_left_nm3']['1'])] for q in pairs])+'\n\n全域比例小会受到空气和衬底的稀释，不能把它直接当作局部边缘精度。'
    full=by['full_T_from_P'];fields['FULL_CONVERSION']=f"全域实际执行 P→T_from_P 并保存重读：源 {fmt(float(full['source_chain_bytes'])/1e6)} MB，派生 {fmt(float(full['derived_file_bytes'])/1e6)} MB，总共 {fmt(float(full['all_chain_saved_bytes'])/1e6)} MB；转换 {fmt(full['construction_seconds'])} s，峰值 RSS {fmt(float(full['peak_rss_bytes'])/1e6)} MB。该路径单列，未当作第十组 A。"
    fields['EDGE_RESULTS']=table(['局部细档','Y150 CD RMS 误差 / nm','Y150 中心 RMS 误差 / nm','顶面高度 RMS 误差 / nm','缺失交点对'],[[r['id']]+[fmt(r[k]) for k in ['cd_y150_rms_nm','center_y150_rms_nm','top_height_rms_nm']]+[r['missing_pairs_y150']] for r in [p,t,v]])+'\n\n边缘相关系数、160–600 nm 与 600–4000 nm 波长带功率在每个模型的 `details` 文件中逐条纹、逐高度、逐左右边缘记录。频谱用有限窗口去均值曲线，不作去趋势；窗长和频率分辨率会限制解释。'
    edge_rows=[]
    for id in ['local_P_fine','local_T_direct_fine','local_V_direct_fine']:
        f=details[id]['metrics']['profiles']['edge_features']['line1_y150_left']
        edge_rows.append([id,fmt(f['rms_nm']),fmt(f['reference_rms_nm']),fmt(f['correlation'],6),fmt(f['bands']['short_160_600nm']['ratio']),fmt(f['bands']['long_600_4000nm']['ratio'])])
    fields['EDGE_RESULTS']+='\n\n以中央条纹 Y=150 nm 左边缘为例（带功率比 1 表示与参考相等）：\n\n'+table(['模型','边缘 RMS / nm','参考 RMS / nm','相关系数','160–600 nm 带功率比','600–4000 nm 带功率比'],edge_rows)
    fields['EDIT_RESULT']=(out/'edit_check.md').read_text(encoding='utf-8').split('\n',1)[1]
    fullv=next(r for r in A if r['scene']=='full' and r['method']=='V_direct');meta=details[fullv['id']]['model_metadata'];fields['RESOURCE_DETAILS']=f"实际全域 10 nm 标签负载 {fmt(float(fullv['array_payload_bytes'])/1e9)} GB，文件 {fmt(float(fullv['file_bytes'])/1e9)} GB，构建 {fmt(fullv['construction_seconds'])} s，峰值 RSS {fmt(float(fullv['peak_rss_bytes'])/1e9)} GB。Y 包围范围为 −100～400 nm，含衬底和顶部起伏空间。各组顺序在隔离子进程执行；预算为每组执行前可用内存的 60%，标签数组用磁盘映射。RSS 包含解释器、运行时临时数组和驻留映射页，与磁盘文件大小不是同一个量。所有字节换算为十进制 MB/GB。"
    fields['PREVIEW_DETAILS']='查看器的全域几何为明确标注的简化预览。局部查看加载细节，原始体素显示外露单元面。预览采样设置和源模型信息显示在详情中；主指标始终由原始模型计算。实际预览误差与浏览器验收记录见下节。'
    fields['VIEWER_INSTRUCTIONS']='1. 先用“整个 Mark”看九条纹，再选“单母周期”“单条纹”“局部圆肩”。\n2. 在“实验 A”里依次切换参数化、直接三角面和直接体素；选择“实验 B”后查看 B1～B4 的来源与目标。\n3. 用正交投影核对尺寸；俯视看 XZ 排布，XY 方向看截面。旋转拖动、滚轮缩放、右键平移。\n4. 拖动 Z 控件更新真实 XY 截面，改变 Y 更新 XZ 等高截面；打开叠加查看相同位置的轮廓。\n5. 局部开启线框，体素观察台阶；隐藏衬底可看到接触边界。高度放大只影响显示，页面持续显示倍率。\n6. 用重置相机恢复视角，保存截图，最后打开详细说明。'
    ui=out/'ui_validation.json';fields['UI_VALIDATION']='界面验收尚未记录；不要据文件存在宣称验收通过。'
    fields['VIEWER_SCREENSHOT']=''
    if ui.exists():
        u=read(ui);fields['UI_VALIDATION']=u.get('report_text',json.dumps(u,ensure_ascii=False,indent=2))
        if (out/'figures/viewer_screenshot.png').exists():fields['VIEWER_SCREENSHOT']='![查看器实际截图](results/'+args.run+'/figures/viewer_screenshot.png)'
    fields['RECOMMENDATION']=f"本轮局部细档 P 使用 {fmt(float(p['array_payload_bytes'])/1e6)} MB 数值负载，T_direct 使用 {fmt(float(t['array_payload_bytes'])/1e6)} MB，5 nm 体素使用 {fmt(float(v['array_payload_bytes'])/1e6)} MB。结合各自误差和编辑记录，建议对于本轮这类分段光滑、固定拓扑且需要语义编辑的模型，保留原始观测并以 P 作为可编辑源，按用途派生三角面和体素；如果来源本身就是经配准的实测轮廓或外部三角网格，也允许 T_direct 作为独立主数据，不强制反拟合参数。\n\n不要将一次合成结果硬编码成唯一格式。保留来源类型、实际连接和材料域，让两种源数据可并存；派生输出带参数与哈希，可失效后重建。原始体素适合直接材料查询和离散接口，但单元量化会改变边界，存储随分辨率增长快；是否保留全部缓存由实测资源和使用频率决定。"
    fields['CONFIG_EXAMPLE']='例如把 `synthetic.shoulder_scale_nm` 从 `[40,70]` 改为 `[45,70]`，表示改变合成参考的左圆肩尺度；这不是更改真实工艺测量。已有模型不会随配置文件自动变化，需要重新构建。'
    fields['RERUN_COMMAND']='完整重跑示例（使用新目录）：\n\n```powershell\n.\\.venv\\Scripts\\python.exe run_validation.py --config configs/default.json --output results/new_run\n.\\.venv\\Scripts\\python.exe scripts/audit_saved_results.py --output results/new_run\n.\\.venv\\Scripts\\python.exe scripts/build_report.py --run new_run\n```'
    template=(ROOT/'scripts/report_template.md').read_text(encoding='utf-8')
    for key,value in fields.items():template=template.replace('{{'+key+'}}',value)
    if '{{' in template:raise ValueError('Unfilled report placeholders')
    title='AH53_三种几何表示验证_技术验证报告';(ROOT/(title+'.md')).write_text(template,encoding='utf-8')
    body=markdown.markdown(template,extensions=['tables','fenced_code','toc'])
    css='body{font:16px/1.8 "Microsoft YaHei",sans-serif;color:#23344c;max-width:1100px;margin:36px auto;padding:0 24px}h1,h2{line-height:1.4}h2{margin-top:2em;border-bottom:1px solid #ddd;padding-bottom:.4em}table{display:block;overflow:auto;border-collapse:collapse;font-size:14px}th,td{padding:7px 10px;border:1px solid #d5dde5}th{background:#eef3f8}img{max-width:100%;height:auto}pre{background:#edf2f6;padding:16px;overflow:auto}a{color:#067c79}code{font-family:Consolas,monospace}strong{color:#263a55}'
    (ROOT/(title+'.html')).write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AH53 几何验证说明</title><style>'+css+'</style><body>'+body+'</body></html>',encoding='utf-8')
    print('Report and figures generated from '+str(out))

if __name__=='__main__':main()
