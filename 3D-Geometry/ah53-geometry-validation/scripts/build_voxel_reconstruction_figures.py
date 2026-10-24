"""Actual-data figures for blind labelled-voxel P/T reconstruction.

No reconstruction decisions use analytic-reference files.  The accuracy chart
reads the independent evaluator's published scalar metrics only.  All spatial
views read sanitized labels/grid and the actual saved reconstructed models.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
import numpy as np
from scipy import ndimage
from skimage.measure import find_contours


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "figures"
INK, GREEN, BLUE, ORANGE, GRAY, PURPLE = "#20354c", "#008575", "#3477bf", "#cf672c", "#69798a", "#8052a3"
LABEL_CMAP = ListedColormap(["#f5f8fc", "#badbd2", "#bac6d6"])
PROFILE_COLORS = {"P_sigma0": GREEN, "P_sigma05": PURPLE, "P_sigma1": BLUE, "T_MC": ORANGE, "voxel_baseline": GRAY}
PROFILE_NAMES = {"P_sigma0": "P：σ=0", "P_sigma05": "P：σ=0.5h", "P_sigma1": "P：σ=1h", "T_MC": "T：MC", "voxel_baseline": "原体素 V"}
plt.rcParams.update({"font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
    "axes.unicode_minus": False, "font.size": 12.5, "axes.titlesize": 15,
    "text.color": INK, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "svg.fonttype": "path", "figure.dpi": 120, "savefig.dpi": 175})
spec = importlib.util.spec_from_file_location("blind_voxel_reconstruction", ROOT / "src" / "ah53" / "voxel_reconstruction.py")
VR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(VR)


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in ("png", "svg"):
        path = OUT / f"{name}.{ext}"
        fig.savefig(path, facecolor="white", bbox_inches="tight")
        paths.append(str(path.relative_to(ROOT)))
    plt.close(fig)
    return paths


def load_input(run, case):
    path = run / "inputs" / case
    labels = np.load(path / "labels.npy", mmap_mode="r")
    grid = json.loads((path / "grid.json").read_text(encoding="utf-8"))
    return labels, grid, np.asarray(grid["origin_xyz_nm"], float), float(grid["spacing_nm"])


def model(run, case, profile):
    kind = "T" if profile == "T_MC" else "P"
    return VR.load_reconstruction(run / "models" / f"{case}__{profile}", kind)


def read_model_meta(run, case, profile):
    kind = "T" if profile == "T_MC" else "P"
    return json.loads((run / "models" / f"{case}__{profile}" / kind / "metadata.json").read_text(encoding="utf-8"))


def draw_slice(ax, labels, origin, h, iz, bounds=None, alpha=1.):
    ny, nx = labels.shape[1:]
    ax.imshow(labels[iz], origin="lower", extent=[origin[0], origin[0] + nx*h, origin[1], origin[1] + ny*h],
              cmap=LABEL_CMAP, vmin=0, vmax=2, interpolation="nearest", alpha=alpha)
    if bounds is not None:
        ax.set_xlim(bounds[:2]); ax.set_ylim(bounds[2:])
    ax.set_aspect("equal")
    ax.set_xlabel("X / nm"); ax.set_ylabel("Y / nm")


def draw_grid(ax, bounds, h, origin):
    x0, x1, y0, y1 = bounds
    for x in np.arange(np.floor((x0-origin[0])/h), np.ceil((x1-origin[0])/h)+1)*h+origin[0]:
        ax.axvline(x, color=GRAY, lw=.45, alpha=.28)
    for y in np.arange(np.floor((y0-origin[1])/h), np.ceil((y1-origin[1])/h)+1)*h+origin[1]:
        ax.axhline(y, color=GRAY, lw=.45, alpha=.28)


def draw_rings(ax, rings, color, label=None, lw=2., ls="-"):
    for i, ring in enumerate(rings):
        ax.plot(ring[:, 0], ring[:, 1], color=color, lw=lw, ls=ls, label=label if i == 0 else None)


def workflow():
    fig, ax = plt.subplots(figsize=(16, 9.4))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    fig.suptitle("新实验 1｜这次从方格里找边界，再分别建立 P 和 T", fontsize=24, y=.975)
    fig.text(.5, .916, "重建程序只读材料标签与网格坐标；不知道条纹个数、中心、侧壁公式或轮廓分区。", ha="center", fontsize=14)
    def box(x, y, w, h, title, body, color=BLUE):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=.013",edgecolor=color,facecolor=color+"12",linewidth=1.8))
        ax.text(x+w/2,y+h*.74,title,ha="center",va="center",fontsize=16,color=color,fontweight="bold")
        ax.text(x+w/2,y+h*.34,body,ha="center",va="center",fontsize=12.5,linespacing=1.6)
    def arrow(p,q,color=INK):
        ax.add_patch(FancyArrowPatch(p,q,arrowstyle="-|>",mutation_scale=17,linewidth=1.7,color=color))
    box(.02,.45,.195,.29,"① 精简输入","labels.npy：0 / 1 / 2\ngrid.json：每格大小、坐标\n0空气 / 1条纹 / 2衬底")
    box(.285,.65,.285,.19,"② P：先整理轮廓","每片找连通区域和边界\n排序、按相邻片重叠关系配对",GREEN)
    box(.65,.65,.30,.19,"③ P：拟合连续曲面","按弧长重采样 → 可选平滑\n周期样条＋沿 Z 的样条",GREEN)
    box(.285,.33,.285,.19,"② T：直接提取三维表面","先变成“是否为条纹”的 0/1 场\nMarching Cubes 在 0.5 处插值",ORANGE)
    box(.65,.33,.30,.19,"③ T：保存网格","顶点坐标＋三角面连接\n不做额外平滑或简化",ORANGE)
    arrow((.23,.65),(.27,.74),GREEN);arrow((.23,.5),(.27,.43),ORANGE)
    arrow((.585,.745),(.635,.745),GREEN);arrow((.585,.425),(.635,.425),ORANGE)
    ax.text(.43,.588,"孔洞、合并或分叉 → 本轮 P 明确拒绝",ha="center",color="#b04a46",fontsize=12.5)
    box(.285,.02,.665,.18,"④ 独立评分：精度、体素一致性、拓扑、体积和文件大小","隐藏原始形状只进入评分程序；绝不回流给重建程序或用来选择平滑强度。",GRAY)
    arrow((.8,.315),(.8,.215),GRAY)
    arrow((.966,.745),(.984,.745),GRAY);arrow((.984,.745),(.984,.11),GRAY);arrow((.984,.11),(.965,.11),GRAY)
    ax.text(.11,.20,"每格 5 nm 与 10 nm\nP 预先固定三档 σ\n0、0.5h、1h",ha="center",va="center",fontsize=13,linespacing=1.7)
    fig.text(.5,.025,"注意：输入已分好材料类别；本轮不研究从原始显微图像识别材料。σ 是人工指定的平滑参数，不是测得的噪声。",ha="center",fontsize=12,color=GRAY)
    return save(fig,"vr_01_blind_reconstruction_workflow")


def actual_slice(run):
    case = "local_5nm"
    labels, grid, origin, h = load_input(run, case)
    iz = labels.shape[0] // 2
    z = origin[2] + (iz+.5)*h
    cc, count = ndimage.label(labels[iz] == 1)
    centres = ndimage.center_of_mass(labels[iz] == 1, cc, range(1,count+1))
    component = int(np.argsort([p[1] for p in centres])[count//2] + 1)
    ys, xs = np.nonzero(cc == component)
    full = [origin[0]+(xs.min()-8)*h, origin[0]+(xs.max()+9)*h,
            origin[1]+(ys.min()-6)*h, origin[1]+(ys.max()+7)*h]
    top_y = origin[1]+(ys.max()+1)*h
    high = (cc == component) & (np.arange(labels.shape[1])[:,None] >= ys.max()-20)
    x_left = origin[0] + np.nonzero(high)[1].min()*h
    roi = [x_left-25, x_left+135, top_y-130, top_y+30]
    raw = []
    for q in find_contours(np.pad((cc==component).astype(np.uint8),1),.5,fully_connected="high"):
        raw.append(origin[:2]+(q[:,::-1]-.5)*h)
    fig=plt.figure(figsize=(16,11.4))
    fig.suptitle("新实验 2｜从真实的 5 nm 标签格子，到自动提取的边界",fontsize=23,y=.976)
    fig.text(.5,.927,f"使用现有体素文件的 Z = {z:g} nm 切片；只按标签找到区域。图中没有绘入隐藏原始轮廓。",ha="center",fontsize=13.5)
    overview=fig.add_axes([.07,.665,.61,.185]);draw_slice(overview,labels,origin,h,iz,full)
    overview.set_title("① 自动找到一个材料区域，框出左上角放大",pad=13)
    overview.add_patch(Rectangle((roi[0],roi[2]),roi[1]-roi[0],roi[3]-roi[2],fill=False,edgecolor="#ba4555",lw=2))
    textax=fig.add_axes([.735,.65,.245,.22]);textax.set_axis_off()
    textax.text(0,.91,"一个格子 = 5 × 5 nm",fontsize=16,fontweight="bold")
    for j,(name,color) in enumerate([("0：空气",LABEL_CMAP(0)),("1：条纹材料",LABEL_CMAP(1)),("2：衬底材料",LABEL_CMAP(2))]):
        textax.add_patch(Rectangle((0,.62-j*.22),.1,.12,color=color,ec=GRAY,lw=.5))
        textax.text(.15,.68-j*.22,name,va="center",fontsize=14)
    left=fig.add_axes([.07,.18,.39,.39]);draw_slice(left,labels,origin,h,iz,roi);draw_grid(left,roi,h,origin)
    draw_rings(left,raw,INK,"从这一片 0/1 场提取的等值线",1.8)
    left.set_title("② 材料变化给出边界线索",pad=14)
    left.legend(loc="lower left",fontsize=10.5)
    right=fig.add_axes([.55,.18,.39,.39]);draw_slice(right,labels,origin,h,iz,roi,alpha=.55);draw_grid(right,roi,h,origin)
    for profile,ls in [("T_MC","-"),("P_sigma0","--"),("P_sigma05","-.")]:
        obj=model(run,case,profile)
        draw_rings(right,obj.section(z,step_nm=.5),PROFILE_COLORS[profile],PROFILE_NAMES[profile],2.,ls)
    right.set_title("③ 从保存后的 P / T 读取相同截面",pad=14)
    right.legend(loc="lower left",fontsize=10.5)
    fig.text(.5,.09,"左图黑线由相邻格子中心的 0/1 值插值得到，不是已知的真实表面；右图各模型使用同一份标签输入。",ha="center",fontsize=12.5)
    fig.text(.5,.045,"图中 σ=0.5h 的 P 同时平滑轮廓方向和 Z 方向。此处只展示预先规定的设置，不按隐藏答案挑选最漂亮的一条线。",ha="center",fontsize=12,color=GRAY)
    return save(fig,"vr_02_actual_voxels_to_contours")


def _read_metric(run,case,profile):
    return json.loads((run/"metrics"/f"{case}__{profile}.json").read_text(encoding="utf-8"))


def _metric_body(data):
    if "reconstructed_to_reference" in data or "input_voxel_to_reference" in data:
        return data
    for key in ("evaluation","metrics","result"):
        if key in data and isinstance(data[key],dict):
            candidate=_metric_body(data[key])
            if "reconstructed_to_reference" in candidate or "input_voxel_to_reference" in candidate:return candidate
    raise ValueError("Unrecognized independent metric schema")


def tradeoffs(run):
    profiles=["voxel_baseline","T_MC","P_sigma0","P_sigma05","P_sigma1"]
    fig,axes=plt.subplots(2,3,figsize=(17,10.5))
    fig.subplots_adjust(left=.07,right=.985,top=.82,bottom=.18,hspace=.67,wspace=.32)
    fig.suptitle("新实验 3｜从同一份体素重建后，精度与代价怎样变化？",fontsize=23,y=.977)
    fig.text(.5,.923,"误差只在预先固定的 XY 切面、共同高度带统计：双向弧长加权 P95；不是完整三维表面的最大误差。",ha="center",fontsize=13)
    fig.text(.5,.875,"高度带排除衬底接触角附近（底部以上 2h）；全部底边的结果另列报告，避免拿两种口径混比。",ha="center",fontsize=12,color=GRAY)
    for row,(case,h) in enumerate([("local_5nm",5),("local_10nm",10)]):
        records=[]
        baseline=None
        for profile in profiles:
            if profile=="voxel_baseline":
                baseline=_metric_body(_read_metric(run,case,profile))
                labels,_,_,_=load_input(run,case)
                metric=baseline.get("input_voxel_to_reference",baseline.get("voxel_to_reference"))
                if metric is None:raise ValueError("Voxel baseline reference metric missing")
                p95=metric["all"]["p95_nm"]
                size=labels.nbytes/1e6;iou=1.
            else:
                data=_metric_body(_read_metric(run,case,profile))
                p95=data["reconstructed_to_reference"]["all"]["p95_nm"]
                size=read_model_meta(run,case,profile)["payload_bytes"]/1e6
                iou=data["material_consistency"]["iou"]
            records.append((p95,size,100*(1-iou)))
        x=np.arange(len(profiles));colors=[PROFILE_COLORS[p] for p in profiles]
        for col,(title,ylabel) in enumerate([("与隐藏原始形状的距离","切面 P95 / nm（越低越好）"),("保存模型的文件大小","模型数据 / MB（对数轴）"),("重建后与输入标签不一致","100 × (1 − IoU) / %（越低越好）")]):
            ax=axes[row,col];values=np.asarray(records)[:,col]
            bars=ax.bar(x,values,color=colors,width=.65)
            ax.set_xticks(x,[PROFILE_NAMES[p].replace("：","\n") for p in profiles],fontsize=10.5)
            ax.set_ylabel(ylabel,fontsize=11.5);ax.set_title(f"h = {h} nm｜{title}",fontsize=13.5,pad=12)
            if col==1:ax.set_yscale("log");ax.set_ylim(max(min(values)*.45,.001),max(values)*3)
            else:ax.set_ylim(0,max(values)*1.27+.001)
            ax.grid(axis="y",alpha=.13);ax.set_axisbelow(True)
            for bar,value in zip(bars,values):
                ax.annotate(f"{value:.3g}",xy=(bar.get_x()+bar.get_width()/2,value),xytext=(0,5),textcoords="offset points",ha="center",fontsize=10.5)
    fig.text(.5,.095,"P 的三档平滑强度在评分前固定；σ=0 表示不做高斯平滑，也仍会进行重采样与样条插值。",ha="center",fontsize=12.5)
    fig.text(.5,.048,"IoU 衡量哪些原体素中心仍被判为材料，原体素与自身的 IoU 固定为 1。它与接近隐藏连续表面的程度是两个不同问题。",ha="center",fontsize=12,color=GRAY)
    return save(fig,"vr_03_accuracy_storage_consistency")


def challenges(run):
    cases=[("through_hole","孔洞：内部也有一圈边界"),("merging_bridge","合并：两块区域在这一段相连"),("single_voxel_spur","小毛刺：只多出一个材料格")]
    fig,axes=plt.subplots(1,3,figsize=(17,9.1))
    fig.subplots_adjust(left=.055,right=.985,top=.78,bottom=.31,wspace=.27)
    fig.suptitle("新实验 4｜边界不再是一条普通条纹时，P / T 会怎样？",fontsize=23,y=.977)
    fig.text(.5,.913,"这三份小体素是单独构造的能力挑战，不是从主样品测出的缺陷；格子大小均为 10 nm。",ha="center",fontsize=13.5)
    for ax,(case,title) in zip(axes,cases):
        labels,grid,origin,h=load_input(run,case)
        iz=labels.shape[0]//2 if case=="through_hole" else int(np.argmax(np.sum(labels==1,axis=(1,2))))
        z=origin[2]+(iz+.5)*h
        if case=="single_voxel_spur":
            changed=np.argwhere(labels[iz]!=labels[0])
            cy,cx=changed.mean(axis=0)
            x,y=origin[:2]+(np.array([cx,cy])+.5)*h
            bounds=[x-55,x+65,y-65,y+55]
        else:
            ys,xs=np.nonzero(labels[iz]==1)
            bounds=[origin[0]+(xs.min()-3)*h,origin[0]+(xs.max()+4)*h,origin[1]+(ys.min()-3)*h,origin[1]+(ys.max()+4)*h]
        draw_slice(ax,labels,origin,h,iz,bounds)
        if case=="single_voxel_spur":draw_grid(ax,bounds,h,origin)
        draw_rings(ax,model(run,case,"T_MC").section(z),ORANGE,"T：保存网格的截面",2.)
        chosen=None
        for profile in ("P_sigma05","P_sigma0","P_sigma1"):
            path=run/"models"/f"{case}__{profile}"/"P"/"metadata.json"
            if path.exists():chosen=profile;break
        if chosen is None:raise FileNotFoundError(f"No challenge P result for {case}")
        meta=read_model_meta(run,case,chosen)
        if meta["status"]=="ok":
            for p,ls in [("P_sigma0","--"),("P_sigma05","-."),("P_sigma1",":")]:
                if (run/"models"/f"{case}__{p}"/"P"/"coefficients.npz").exists():
                    draw_rings(ax,model(run,case,p).section(z,step_nm=.4),PROFILE_COLORS[p],PROFILE_NAMES[p],2.,ls)
            caption="重采样与插值就可能改变小毛刺；\n平滑还会进一步改变它，不能直接称为去噪。"
        else:
            caption="P 明确报告不支持此拓扑，未生成曲面。\nT 直接保留图中的孔洞或连接关系。"
        ax.set_title(f"{title}\nZ = {z:g} nm",fontsize=14,pad=13)
        ax.legend(loc="lower left",fontsize=9.5)
        centre=(ax.get_position().x0+ax.get_position().x1)/2
        fig.text(centre,.218,caption,ha="center",va="top",fontsize=11.5,linespacing=1.7)
    fig.text(.5,.10,"拒绝表示是本轮 P 实现的能力边界：固定数量、贯穿 Z、无孔洞的闭合轮廓。它不是对所有参数化曲面方法的否定。",ha="center",fontsize=12.5)
    fig.text(.5,.045,"图中没有隐藏原始曲线；T 的“保留”是针对已给定体素里的连接关系，不代表自动恢复扫描分辨率以下的真实缺陷。",ha="center",fontsize=12,color=GRAY)
    return save(fig,"vr_04_topology_and_small_features")


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--run",default="20261024_voxel_reconstruction")
    parser.add_argument("--only",nargs="*",choices=["workflow","slice","tradeoffs","challenges"])
    args=parser.parse_args();run=ROOT/"results"/args.run
    selected=args.only or ["workflow","slice","tradeoffs","challenges"]
    paths=[]
    for item in selected:
        paths.extend(workflow() if item=="workflow" else {"slice":actual_slice,"tradeoffs":tradeoffs,"challenges":challenges}[item](run))
    print(json.dumps({"generated":paths},ensure_ascii=False,indent=2))


if __name__=="__main__":main()
