"""Build beginner figures without changing any saved experiment data.

Figures 01/02 load persisted geometry; 03 is a workflow diagram; 04 is an
explicitly fictional teaching example. Each output is PNG and self-contained SVG.
"""
from pathlib import Path
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ah53 import load_model

MODELS = ROOT / "results" / "20261024_v2" / "models"
OUT = ROOT / "docs" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
INK = "#20354c"
GREEN = "#008575"
ORANGE = "#cf672c"
BLUE = "#3477bf"
GRAY = "#69798a"
BG = "#f4f7fb"
plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
    "axes.unicode_minus": False, "font.size": 13,
    "axes.titlesize": 16, "axes.labelsize": 13,
    "text.color": INK, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "svg.fonttype": "path", "figure.dpi": 120, "savefig.dpi": 180,
})


def save(fig, name):
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"{name}.{ext}", facecolor="white", bbox_inches="tight")
    plt.close(fig)


def arrow(ax, p, q, color=INK, **kwargs):
    ax.annotate("", xy=q, xytext=p,
                arrowprops={"arrowstyle": "->", "lw": 1.8, "color": color,
                            "shrinkA": 3, "shrinkB": 3, **kwargs})


def dimension(ax, x1, x2, y, label, color=INK):
    ax.annotate("", xy=(x1, y), xytext=(x2, y),
                arrowprops={"arrowstyle": "<->", "lw": 1.5, "color": color})
    ax.text((x1+x2)/2, y, label, ha="center", va="bottom",
            color=color, bbox={"facecolor": "white", "edgecolor": "none", "pad": 2})


def coordinates():
    ref = load_model(MODELS / "reference_local")
    fig, axes = plt.subplots(2, 1, figsize=(13, 10.5),
                             gridspec_kw={"height_ratios": [1.08, 1]})
    fig.subplots_adjust(hspace=.60, top=.88, bottom=.13, left=.10, right=.96)
    fig.suptitle("新手图 1｜先认清方向，再看大小", fontsize=23, y=.98)
    fig.text(.5, .935, "1 μm（微米）= 1000 nm（纳米）；以下使用本项目的坐标约定", ha="center")
    ax = axes[0]
    ax.add_patch(Rectangle((-8, -2), 16, 4, facecolor=BG, edgecolor="#cbd4dd"))
    ax.add_patch(Rectangle((-4, -2), 8, 4, facecolor="#e3f3ef", edgecolor="none"))
    for i, c in enumerate(ref.centers / 1000):
        ax.add_patch(Rectangle((c-.8, -2), 1.6, 4, facecolor=GREEN, alpha=.85))
        ax.text(c, -.95, f"第 {i+1} 条\nX 中心\n{c:g} μm", ha="center", color="white", fontsize=11)
    ax.axhline(.413, color=ORANGE, ls="--", lw=2)
    ax.text(8.15, .413, "沿这条线切开\nZ = 0.413 μm", va="center", color=ORANGE, fontsize=12)
    dimension(ax, -8, 8, 3.2, "一个母周期：16 μm")
    dimension(ax, -4, 4, 2.48, "条纹区：8 μm")
    ax.text(-6, 1.1, "空白\n4 μm", ha="center", color=GRAY)
    ax.text(6, 1.1, "空白\n4 μm", ha="center", color=GRAY)
    ax.set(xlim=(-8.5, 10.7), ylim=(-2.15, 3.8), xlabel="X：横着跨过三条条纹 / μm",
           ylabel="Z：沿条纹长度 / μm", title="① 俯视图（X–Z 平面）：从上往下看，只看占地位置", xticks=[-8,-4,-3.2,0,3.2,4,8])
    ax.tick_params(labelsize=11)
    ax.set_yticks([-2, 0, 2])
    ax.text(.5, -.30, "矩形是名义布局示意；左右各 4 μm 的空白与相邻母周期拼成 8 μm 空白区。", transform=ax.transAxes, ha="center", fontsize=12, color=GRAY)
    ax = axes[1]
    p = ref.contour(1, 413., step_nm=.5)
    ax.fill(p[:,0], p[:,1], color="#d9eee8")
    ax.plot(p[:,0], p[:,1], color=GREEN, lw=2.5)
    ax.fill_between([-1050,1050], -65, 0, color="#d4dae2")
    ax.text(0, -35, "基底（Y < 0）", ha="center", va="center", fontsize=12)
    ax.plot([-800,-800,800,800],[0,300,300,0], color=GRAY, ls="--", lw=1)
    dimension(ax, -800, 800, 365, "名义宽度 1600 nm = 1.6 μm")
    ax.annotate("", xy=(955,300), xytext=(955,0), arrowprops={"arrowstyle":"<->", "color":INK})
    ax.text(975, 150, "名义高度\n300 nm\n= 0.3 μm", va="center", fontsize=12)
    ax.annotate("圆肩：侧壁向顶面\n圆滑转弯的地方", xy=(-770,302), xytext=(-1020,440),
                fontsize=12, color=ORANGE, arrowprops={"arrowstyle":"->", "color":ORANGE})
    ax.text(0, 160, "中央条纹的截面\n实线来自已保存的合成参考", ha="center", fontsize=12)
    ax.set(xlim=(-1100,1260), ylim=(-70,520), xlabel="X / nm", ylabel="Y：离开基底的高度 / nm",
           title="② XY 截面：固定 Z，把条纹像面包一样切一片")
    ax.set_yticks([0,150,300])
    ax.grid(alpha=.12)
    fig.text(.5, .035, "读图提醒：为了看清圆肩，下图纵向显示被拉高；48 μm 宽的全域只有约 0.3 μm 高，真实比例看起来很薄。\n这里的形状是人为设计的合成测试样本，不是显微镜实测。", ha="center", fontsize=12, color=GRAY)
    save(fig, "01_方向与尺度")


def representations():
    p = load_model(MODELS / "local_P_fine")
    t = load_model(MODELS / "local_T_direct_fine")
    v = load_model(MODELS / "local_V_direct_fine")
    ref = load_model(MODELS / "reference_local")
    models = [p,t,v]
    colors = [GREEN, ORANGE, BLUE]
    fig = plt.figure(figsize=(15, 11.5))
    gs = fig.add_gridspec(2, 3, top=.85, bottom=.19, left=.06, right=.98, hspace=.50, wspace=.30)
    fig.suptitle("新手图 2｜同一个圆肩，用三种方法保存", fontsize=23, y=.98)
    fig.text(.5, .934, "全部从本轮实际保存的局部细档模型读取；三幅使用相同坐标范围。虚线是合成参考。", ha="center")
    names = ["P：保存光滑曲面的规则", "T：保存顶点和三角形连接", "V：保存每个小方块的材料"]
    section = ref.contour(1, 413., step_nm=.2)
    for i, (model, color) in enumerate(zip(models, colors)):
        ax = fig.add_subplot(gs[0,i])
        curve = model.contour(1,413.,step_nm=.2)
        ax.plot(section[:,0],section[:,1],"--", color=GRAY,lw=1.5,label="合成参考")
        if i == 0:
            control = p._z_splines[1](413.)[1]
            ax.plot(control[:,0],control[:,1], "o--", color="#84bdb2", ms=4, lw=1, label="实际截面控制点")
        if i == 2:
            h=v.spacing
            ix=np.arange(int((-795-v.origin[0])/h),int((-735-v.origin[0])/h))
            iy=np.arange(int((260-v.origin[1])/h),int((320-v.origin[1])/h))
            iz=int((413-v.origin[2])/h)
            for yy in iy:
                for xx in ix:
                    ax.add_patch(Rectangle((v.origin[0]+xx*h,v.origin[1]+yy*h),h,h,
                                          facecolor="#dbe9f8" if v.labels[iz,yy,xx]==1 else "white",
                                          edgecolor="#c3d1de", lw=.35))
        ax.plot(curve[:,0],curve[:,1],color=color,lw=2.5,label="保存模型的截面")
        ax.set(xlim=(-795,-735),ylim=(260,320),xlabel="X / nm",ylabel="Y / nm",title=names[i])
        ax.set_aspect("equal")
        ax.set_xticks([-790,-770,-750]); ax.set_yticks([260,280,300,320])
        ax.tick_params(labelsize=11)
        ax.text(.5,-.31,["圆点是实际 B 样条截面控制点\n控制点帮助定形，不必位于曲线上", "截面穿过三角面后是一条折线\n精细网格的折线可能看起来很光滑", "每格边长 5 nm\n边界沿格子边缘，呈台阶状"][i],
                transform=ax.transAxes,ha="center",fontsize=11.5,color=GRAY)
    roi=[-815,-705,240,330,400,480]
    for i, (model, color) in enumerate(zip(models, colors)):
        ax=fig.add_subplot(gs[1,i], projection="3d")
        if i==0:
            us=np.linspace(.82,2.07,130); zs=np.linspace(400,480,41)
            points=np.array([p.evaluate(1,us,z) for z in zs])
            surface=np.dstack((points,np.broadcast_to(zs[:,None],points.shape[:2])))
            polygons=[];shades=[]
            base=np.array(matplotlib.colors.to_rgb(GREEN));light=np.array([-.4,.7,.6]);light/=np.linalg.norm(light)
            for j in range(len(zs)-1):
                for k in range(len(us)-1):
                    quad=surface[[j,j,j+1,j+1],[k,k+1,k+1,k]]
                    polygon=clip_polygon(quad,roi)
                    if len(polygon)<3:
                        continue
                    normal=np.cross(quad[1]-quad[0],quad[3]-quad[0]);normal/=np.linalg.norm(normal)
                    polygons.append(polygon[:,[0,2,1]])
                    shades.append(base*(.55+.45*abs(normal@light)))
            ax.add_collection3d(Poly3DCollection(polygons,facecolors=shades,edgecolor="none",linewidths=0,antialiaseds=False))
        elif i==1:
            vertices,faces=t.mesh(line=1,roi=roi)
            polygons=[clip_polygon(triangle, roi) for triangle in vertices[faces]]
            xyz=[polygon[:,[0,2,1]] for polygon in polygons if len(polygon)>=3]
            ax.add_collection3d(Poly3DCollection(xyz,facecolor="#f4b38a",edgecolor="#a74c1d",linewidths=.75,alpha=.96))
        else:
            vertices,faces=v.mesh(line=1,roi=roi)
            quads=vertices.reshape(-1,4,3)[:,:,[0,2,1]]
            ax.add_collection3d(Poly3DCollection(quads,facecolor="#b9d5ef",edgecolor="#336da8",linewidths=.5,alpha=1))
        ax.set(xlim=(-815,-705),ylim=(400,480),zlim=(240,330),xlabel="X / nm",ylabel="Z / nm",zlabel="Y / nm")
        ax.set_box_aspect((110,80,90));ax.view_init(elev=25,azim=-65)
        ax.set_xticks([-800,-720]);ax.set_yticks([400,480]);ax.set_zticks([250,310])
        ax.tick_params(labelsize=9,pad=0)
        ax.set_title(["从公式计算出的光滑表面", "真实保存的三角面及边线", "真实标签外露的小方块表面"][i], fontsize=14,pad=10)
    fig.text(.5,.115,"上排：同一位置 Z = 413 nm 的切片。下排：中央条纹左圆肩，Z = 400–480 nm 的一小块 3D 表面。",ha="center",fontsize=12)
    fig.text(.5,.055,"P 的图像也要采样才能显示，但它的源文件保存样条系数；T 的源文件保存真实三角面连接；V 的源文件保存材料编号。\n画得光滑不等于存得光滑。此图用于解释表示方法，精度结论应看统一测量的误差表。",ha="center",fontsize=12,color=GRAY)
    save(fig,"02_三种表示实际圆肩")


def clip_polygon(points, roi):
    """Clip a saved triangle to the drawing box without altering its surface."""
    polygon = np.asarray(points)
    for axis in range(3):
        for bound, keep_greater in ((roi[2*axis], True), (roi[2*axis+1], False)):
            if not len(polygon):
                return polygon
            clipped=[]
            previous=polygon[-1]
            previous_inside=(previous[axis]>=bound if keep_greater else previous[axis]<=bound)
            for current in polygon:
                inside=(current[axis]>=bound if keep_greater else current[axis]<=bound)
                if inside != previous_inside:
                    alpha=(bound-previous[axis])/(current[axis]-previous[axis])
                    clipped.append(previous+alpha*(current-previous))
                if inside:
                    clipped.append(current)
                previous=current;previous_inside=inside
            polygon=np.asarray(clipped)
    return polygon


def box(ax,x,y,w,h,label,color=INK,face=BG,size=13):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.012,rounding_size=0.018",edgecolor=color,facecolor=face,lw=1.5))
    ax.text(x+w/2,y+h/2,label,ha="center",va="center",fontsize=size,color=color)


def workflows():
    fig, axes=plt.subplots(2,1,figsize=(14,11.5),gridspec_kw={"height_ratios":[1,1.12]})
    fig.subplots_adjust(top=.88,bottom=.12,hspace=.32,left=.04,right=.96)
    fig.suptitle("新手图 3｜A 测“怎么保存”，B 测“换格式会损失多少”",fontsize=23,y=.98)
    fig.text(.5,.935,"这是实验流程示意图，不是形貌图，也不是实测数据。箭头表示数据从哪里来。",ha="center")
    ax=axes[0]; ax.set(xlim=(0,1),ylim=(0,1));ax.axis("off")
    ax.text(.01,.97,"A：独立建模比较",fontsize=19,weight="bold",va="top")
    box(ax,.025,.39,.21,.23,"合成连续参考\n预先定义的答案",INK)
    box(ax,.32,.58,.24,.24,"共同离散观测点\nP 和 T 用同一批点",INK)
    box(ax,.69,.70,.26,.17,"P：拟合样条",GREEN,"#e4f4ef")
    box(ax,.69,.46,.26,.17,"T_direct：直接连三角面",ORANGE,"#fff0e5",12)
    box(ax,.69,.13,.26,.17,"V_direct：独立体素",BLUE,"#e8f1fc")
    arrow(ax,(.235,.56),(.32,.70))
    arrow(ax,(.56,.75),(.69,.78),GREEN)
    arrow(ax,(.56,.63),(.69,.55),ORANGE)
    arrow(ax,(.235,.46),(.69,.215),BLUE)
    ax.text(.43,.15,"直接检查每格中心属于哪种材料\nV 没有先经过 P 或 T",color=BLUE,ha="center",fontsize=12)
    ax.text(.025,.03,"A 共 9 组：局部粗档 3 种 + 局部细档 3 种 + 全域 3 种。",fontsize=12,color=GRAY)
    ax=axes[1];ax.set(xlim=(0,1),ylim=(0,1));ax.axis("off")
    ax.text(.01,.98,"B：从已经保存的模型继续转换（局部四条路径）",fontsize=19,weight="bold",va="top")
    ys=[.76,.55,.34,.13]
    for y,label in zip(ys,["B1","B2","B3","B4"]):ax.text(.025,y+.055,label,fontsize=15,weight="bold",va="center")
    box(ax,.11,ys[0],.17,.12,"P",GREEN,"#e4f4ef");box(ax,.49,ys[0],.28,.12,"T_from_P",ORANGE,"#fff0e5")
    arrow(ax,(.28,ys[0]+.06),(.49,ys[0]+.06));ax.text(.385,ys[0]+.095,"三角化",ha="center",fontsize=11)
    box(ax,.11,ys[1],.17,.12,"P",GREEN,"#e4f4ef");box(ax,.49,ys[1],.28,.12,"V_from_P",BLUE,"#e8f1fc")
    arrow(ax,(.28,ys[1]+.06),(.49,ys[1]+.06));ax.text(.385,ys[1]+.095,"体素化",ha="center",fontsize=11)
    box(ax,.11,ys[2],.17,.12,"P",GREEN,"#e4f4ef");box(ax,.39,ys[2],.22,.12,"T_from_P",ORANGE,"#fff0e5")
    box(ax,.73,ys[2],.24,.12,"V_from_T",BLUE,"#e8f1fc");arrow(ax,(.28,ys[2]+.06),(.39,ys[2]+.06));arrow(ax,(.61,ys[2]+.06),(.73,ys[2]+.06))
    box(ax,.11,ys[3],.22,.12,"T_direct",ORANGE,"#fff0e5");box(ax,.49,ys[3],.28,.12,"V_from_Tdirect",BLUE,"#e8f1fc")
    arrow(ax,(.33,ys[3]+.06),(.49,ys[3]+.06));ax.text(.41,ys[3]+.095,"体素化",ha="center",fontsize=11)
    fig.text(.5,.075,"共同检查方式：生成 → 写入磁盘 → 重新读取 → 从已保存的数据取截面、查材料、测误差。",ha="center",fontsize=13,weight="bold")
    fig.text(.5,.025,"注意：P/T 用离散观测，独立 V 用连续参考，因此 A 的输入信息并不完全相同。\nB 同时量“相对参考的总误差”和“相对直接上游的新增差异”；两个 P95 不能直接相加。",ha="center",fontsize=12,color=GRAY)
    save(fig,"03_A与B验证流程")


def metrics():
    fig,axes=plt.subplots(1,2,figsize=(14,7.5),gridspec_kw={"width_ratios":[1.12,1]})
    fig.subplots_adjust(top=.78,bottom=.22,wspace=.30,left=.07,right=.97)
    fig.suptitle("新手图 4｜宽度、中心和 P95 分别回答什么问题",fontsize=22,y=.98)
    fig.text(.5,.91,"本图数字是教学例子，不是本次实验结果。",ha="center",fontsize=14,color=ORANGE)
    ax=axes[0]
    examples=[(-800,800,3,"名义截面",INK),(-805,805,2,"两侧各向外 5 nm",GREEN),(-790,810,1,"整体向右平移 10 nm",BLUE)]
    for l,r,y,label,color in examples:
        ax.plot([l,r],[y,y],lw=15,color=color,solid_capstyle="butt",alpha=.78)
        ax.plot([(l+r)/2]*2,[y-.16,y+.16],color="white",lw=3)
        ax.text(0,y+.25,label,ha="center",fontsize=13,color=color)
        ax.text(0,y-.22,f"宽度 = {r-l} nm；中心 = {(l+r)/2:g} nm",ha="center",va="top",fontsize=12)
        ax.text(l-25,y,f"L\n{l}",ha="right",va="center",fontsize=11)
        ax.text(r+25,y,f"R\n{r}",ha="left",va="center",fontsize=11)
    ax.axvline(0,color=GRAY,lw=1,ls="--",zorder=0)
    ax.set(xlim=(-1100,1100),ylim=(.55,3.6),title="① 固定 Y、Z 后，找左右边界 L 和 R")
    ax.axis("off")
    ax.text(.5,-.13,"CD（这里指条纹宽度）= R − L\n中心位置 = (L + R) ÷ 2",transform=ax.transAxes,ha="center",fontsize=14)
    ax=axes[1]
    distances=np.r_[np.linspace(.1,1.9,94),2.,2.,3.,4.,6.,8.]
    p95=float(np.percentile(distances,95))
    ax.plot(np.arange(1,101),distances,color=BLUE,lw=2)
    ax.scatter([95],[distances[94]],color=ORANGE,s=65,zorder=5)
    ax.axhline(p95,color=ORANGE,ls="--")
    ax.axvline(95,color=GRAY,ls=":")
    ax.text(5,2.35,f"P95 = {p95:g} nm",color=ORANGE,fontsize=14)
    ax.annotate("最大值 = 8 nm\n仍有少数偏差较大",xy=(100,8),xytext=(25,6.2),arrowprops={"arrowstyle":"->","color":INK},fontsize=12)
    ax.set(xlim=(0,104),ylim=(0,9),xlabel="把 100 个距离从小到大排序后的序号",ylabel="到另一条轮廓的距离 / nm",
           title="② P95 看“大部分误差有多大”")
    ax.set_xticks([1,25,50,75,95]);ax.grid(alpha=.13)
    fig.text(.5,.04,"真实实验会沿轮廓采很多点，测点到另一条轮廓的最近距离；两个方向都测，再统计 RMS、P95 和最大值。\nP95 约为 2 nm 不代表每个地方都小于 2 nm，也不代表“95% 的模型正确”。",ha="center",fontsize=12,color=GRAY)
    save(fig,"04_指标怎么读")


if __name__ == "__main__":
    coordinates()
    representations()
    workflows()
    metrics()
    print(json.dumps({"output":str(OUT),"figures":[p.name for p in sorted(OUT.glob('*'))]},ensure_ascii=False,indent=2))
