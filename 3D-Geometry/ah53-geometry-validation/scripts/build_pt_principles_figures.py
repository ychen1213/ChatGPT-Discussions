"""Reproducible P/T teaching figures; never modifies saved model data.

Figures 1--3 are explicit toy examples. Figure 4 reads the persisted synthetic
reference. All coordinates are identified in the figure, and SVGs embed glyphs.
"""
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.interpolate import CubicSpline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ah53 import load_model
OUT = ROOT / 'docs' / 'figures'
OUT.mkdir(parents=True, exist_ok=True)
INK, GREEN, BLUE, ORANGE, GRAY = '#20354c', '#008575', '#3477bf', '#cf672c', '#69798a'
COLORS = [BLUE, '#925cb5', GREEN, ORANGE, '#bd5c81', GRAY]
plt.rcParams.update({'font.sans-serif': ['Microsoft YaHei', 'SimHei', 'DejaVu Sans'],
                     'axes.unicode_minus': False, 'font.size': 13,
                     'axes.titlesize': 16, 'axes.labelsize': 13,
                     'text.color': INK, 'axes.labelcolor': INK,
                     'xtick.color': INK, 'ytick.color': INK,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'svg.fonttype': 'path', 'figure.dpi': 120, 'savefig.dpi': 170})


def save(fig, name):
    for ext in ['png', 'svg']:
        fig.savefig(OUT / f'{name}.{ext}', facecolor='white', bbox_inches='tight')
    plt.close(fig)


def plain(ax):
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)


def arrow(ax, p, q, color=INK, **kw):
    ax.annotate('', xy=q, xytext=p,
                arrowprops={'arrowstyle': '->', 'lw': 1.8, 'color': color, **kw})


def toy_contour(t, z=0, variable=False):
    """Six contour regions of a toy stripe, using cubic shoulders."""
    t = np.asarray(t)
    c = .18*np.sin(np.pi*z/2) if variable else 0.
    w = 1.6+.22*np.sin(np.pi*z/2) if variable else 1.6
    h = .32+.055*np.sin(np.pi*z/2) if variable else .32
    r = .09
    x, y = np.empty_like(t), np.empty_like(t)
    def bez(v, a, b, c, d):
        return (1-v)**3*a+3*(1-v)**2*v*b+3*(1-v)*v*v*c+v**3*d
    for k in range(6):
        m = (t >= k) & ((t < k+1) if k < 5 else (t <= 6))
        v = t[m]-k
        if k == 0: x[m], y[m] = c-w/2, v*(h-r)
        if k == 1:
            x[m] = bez(v,c-w/2,c-w/2,c-w/2+r*.45,c-w/2+r)
            y[m] = bez(v,h-r,h-r*.45,h,h)
        if k == 2: x[m], y[m] = c-w/2+r+(w-2*r)*v, h+0*v
        if k == 3:
            x[m] = bez(v,c+w/2-r,c+w/2-r*.45,c+w/2,c+w/2)
            y[m] = bez(v,h,h,h-r*.45,h-r)
        if k == 4: x[m], y[m] = c+w/2, (1-v)*(h-r)
        if k == 5: x[m], y[m] = c+w/2-w*v, 0*v
    return x, y


def sweep():
    fig = plt.figure(figsize=(15, 9.4))
    fig.suptitle('原理图 1｜把一片截面变成一条三维条纹', fontsize=25, y=.985)
    fig.text(.5,.929,'教学假想形状；长度单位 μm。为看清截面，图中高度方向已放大。',ha='center',color=GRAY)
    for i, variable in enumerate([False, True]):
        ax = fig.add_axes([.025+i*.49, .285, .47, .59], projection='3d')
        t, z = np.linspace(0,6,121), np.linspace(0,4,65)
        T, Z = np.meshgrid(t,z)
        X, Y = np.array([toy_contour(t,zz,variable) for zz in z]).transpose(1,0,2)
        ax.plot_surface(X,Z,Y,color=GREEN if variable else BLUE,alpha=.26,
                        linewidth=0,rstride=2,cstride=2,shade=True)
        for k, zz in enumerate([0,1,2,3,4]):
            xx, yy = toy_contour(t,zz,variable)
            ax.plot(xx,np.full_like(xx,zz),yy,color=ORANGE if zz==1 else INK,lw=1.7)
        ax.set_xlabel('X：横向',labelpad=8);ax.set_ylabel('Z：条纹长度',labelpad=10)
        ax.set_zlabel('Y：高度',labelpad=8)
        ax.set(xlim=(-1.15,1.15),ylim=(0,4),zlim=(0,.45),zticks=[0,.2,.4],xticks=[-1,0,1])
        ax.view_init(elev=24,azim=-56)
        ax.set_box_aspect((2.4,4.2,1.9))
        ax.set_title(('① 直拉伸：每一片完全相同' if not variable else '② 变化截面扫掠：每片可以不同'),pad=17)
    fig.text(.255,.233,'固定一片轮廓 C0(t)，沿 Z 复制\nS(t,Z) = (x0(t), y0(t), Z)',ha='center',fontsize=17,color=BLUE)
    fig.text(.745,.233,'轮廓随 Z 改变：中心、宽度、高度都可变化\nS(t,Z) = (x(t,Z), y(t,Z), Z)',ha='center',fontsize=17,color=GREEN)
    fig.text(.5,.105,'黑线：选出的 5 片截面。半透明部分：它们之间的边界表面。\n橙线只是强调 Z = 1 μm 那一片；“扫掠”描述造形思路，还没有决定最终保存成 P 还是 T。',ha='center',fontsize=14,linespacing=1.8,
             bbox={'boxstyle':'round,pad=.8','fc':'#f0f5fa','ec':'none'})
    save(fig,'pt_01_sweep_and_spatial_variation')


def fields():
    fig, axes = plt.subplots(1,3,figsize=(16,9.4))
    fig.subplots_adjust(left=.055,right=.985,top=.78,bottom=.35,wspace=.30)
    fig.suptitle('原理图 2｜“左右位移场”到底改了什么？',fontsize=25,y=.985)
    fig.text(.5,.927,'固定一个高度 Y，只看这一层的两条边；下图横轴 Z 是长度位置，纵轴 X 是横向位置。',ha='center',fontsize=14)
    fig.text(.5,.87,'共同基准：左边 −800 nm，右边 +800 nm → 中心 c0 = 0，宽度 w0 = 1600 nm',ha='center',fontsize=15,color=INK)
    z=np.linspace(0,1000,501);f=np.sin(np.pi*z/1000)
    cases=[(0*f,0*f,'① 无变化','δL = 0，δR = 0\nc = 0 nm，w = 1600 nm'),
           (100*f,100*f,'② 两边一起右移','Z = 500 nm：δL = δR = +100 nm\nc = 100 nm，w = 1600 nm'),
           (-100*f,100*f,'③ 左右向外各移 100 nm','Z = 500 nm：δL = −100，δR = +100 nm\nc = 0 nm，w = 1800 nm')]
    for ax,(dl,dr,title,caption) in zip(axes,cases):
        l,r=-800+dl,800+dr
        ax.fill_between(z,l,r,color='#e3f2ed')
        for baseline in [-800,800]:ax.axhline(baseline,color=GRAY,lw=1,ls='--',alpha=.65)
        ax.plot(z,l,color=BLUE,lw=3,label='左边 xL')
        ax.plot(z,r,color=ORANGE,lw=3,label='右边 xR')
        ax.plot(z,(l+r)/2,color=GREEN,ls='-.',lw=2,label='中心 c')
        ax.axvline(500,color=INK,alpha=.3,lw=1)
        ax.scatter([500,500],[l[250],r[250]],color=[BLUE,ORANGE],s=38,zorder=4)
        ax.set(title=title,xlabel='Z：长度位置 / nm',xlim=(0,1000),ylim=(-1100,1100),yticks=[-800,0,800],xticks=[0,500,1000])
        ax.grid(alpha=.1)
        ax.text(.5,-.22,caption,transform=ax.transAxes,ha='center',va='top',fontsize=12.5,linespacing=1.7)
    axes[0].set_ylabel('X：横向位置 / nm')
    axes[0].legend(loc='upper right',fontsize=11,ncol=1)
    fig.text(.5,.163,'c = (xL + xR) / 2，w = xR − xL；等价地：xL = c − w/2，xR = c + w/2',ha='center',fontsize=17,color=INK)
    fig.text(.5,.099,'Δc = (δL + δR) / 2，Δw = δR − δL；这里的 δL、δR 就是原文的 uL(Y,Z)、uR(Y,Z)。',ha='center',fontsize=15)
    fig.text(.5,.037,'这是刻意放大到 100 nm 的教学例，并非本轮粗糙度数据。对不同 Y 也分别定义变化，就得到随高度和长度变化的场。',ha='center',fontsize=12,color=GRAY)
    save(fig,'pt_02_boundary_displacement_fields')


def construction():
    fig=plt.figure(figsize=(16,12.2))
    fig.suptitle('原理图 3｜同一组有序点，P 与 T 用不同规则补上点之间的表面',fontsize=24,y=.986)
    fig.text(.5,.936,'教学例：只画边界上的一小块。每个黑点都有 (X,Y,Z) 坐标，还知道它在第几片、轮廓的第几个位置。',ha='center',fontsize=13.5)
    ts=np.linspace(0,1,4);zs=np.linspace(0,1,4)
    T,Z=np.meshgrid(ts,zs,indexing='ij')
    # Both models below use exactly these 16 ordered observations.
    values=.34*np.sin(np.pi*T)*np.cos(np.pi*Z*.8)+.14*T+.1*Z
    tf,zf=np.linspace(0,1,45),np.linspace(0,1,45)
    vf=CubicSpline(zs,CubicSpline(ts,values,axis=0)(tf),axis=1)(zf)
    U,V=np.meshgrid(tf,zf,indexing='ij')
    for i,kind in enumerate(['P','T']):
        ax=fig.add_axes([.02+i*.49,.48,.47,.40],projection='3d')
        if kind=='P':
            ax.plot_surface(U,V,vf,color=GREEN,alpha=.65,linewidth=0,shade=True)
            for k,z in enumerate(zs):ax.plot(tf,tf*0+z,CubicSpline(ts,values[:,k])(tf),color=GREEN,lw=1)
        else:
            verts=[]
            for a in range(3):
                for b in range(3):
                    A=[ts[a],zs[b],values[a,b]];B=[ts[a+1],zs[b],values[a+1,b]]
                    C=[ts[a+1],zs[b+1],values[a+1,b+1]];D=[ts[a],zs[b+1],values[a,b+1]]
                    verts.extend([[A,D,C],[A,C,B]])
            ax.add_collection3d(Poly3DCollection(verts,facecolor='#9cc8e9',edgecolor=BLUE,linewidth=1,alpha=.85))
        ax.scatter(T.ravel(),Z.ravel(),values.ravel(),color=INK,s=26,depthshade=False)
        ax.set(xlim=(0,1),ylim=(0,1),zlim=(-.1,.5),xticks=[],yticks=[],zticks=[])
        ax.set_xlabel('沿轮廓的次序',labelpad=-5);ax.set_ylabel('沿长度 Z',labelpad=-5);ax.set_zlabel('一小块弯曲边界',labelpad=-5)
        ax.view_init(elev=27,azim=-55);ax.set_box_aspect((1,1,.6))
        ax.set_title('P：分片三次插值，得到连续曲面' if kind=='P' else 'T：相邻点直接连成平三角形',pad=2,color=GREEN if kind=='P' else BLUE)
    ax=fig.add_axes([.055,.12,.405,.32]);plain(ax)
    ax.text(0,1,'P 的生成顺序',fontsize=18,color=GREEN,va='top')
    steps=['① 在每一片内：沿轮廓顺序插值 X、Y。','② 沿 Z 插值这些曲线的系数，连接各片。','③ 保存样条节点与样条系数。','④ 输入任意 (t,Z)，计算对应的 (X,Y,Z)。']
    for k,s in enumerate(steps):ax.text(0,.79-k*.15,s,fontsize=14,va='top')
    ax.text(0,.04,'黑点是观测坐标；样条系数是计算出来的数字。\n系数不等于黑点，也不一定是可直接拖动的空间点。',fontsize=12,color=GRAY,va='bottom',linespacing=1.6)
    ax=fig.add_axes([.55,.125,.39,.32]);plain(ax)
    ax.text(0,1,'T 的最小连面单元：4 点 → 2 个三角形',fontsize=17,color=BLUE,va='top')
    A=np.array([.10,.21]);B=np.array([.70,.15]);C=np.array([.87,.67]);D=np.array([.28,.74])
    ax.add_patch(Polygon([A,D,C],fc='#e3eff9',ec=BLUE,lw=2))
    ax.add_patch(Polygon([A,C,B],fc='#a9cdea',ec=BLUE,lw=2))
    ax.plot([A[0],C[0]],[A[1],C[1]],color=ORANGE,lw=3)
    for p,lab,off in [(A,'A：第 j 片，第 i 点',(-.08,-.12)),(B,'B：第 j 片，第 i+1 点',(-.05,-.12)),(D,'D：第 j+1 片，第 i 点',(-.17,.04)),(C,'C：第 j+1 片，第 i+1 点',(-.10,.04))]:
        ax.scatter(*p,color=INK,s=34,zorder=5)
        ax.text(*(p+off),lab,fontsize=10.5,ha='left')
    ax.text(.39,.53,'A–D–C',fontsize=14,color=BLUE);ax.text(.55,.31,'A–C–B',fontsize=14,color=BLUE)
    fig.text(.5,.049,'两者都从同一组黑点开始；T_direct 不需要先建立 P。只有“P → T”导出路线，才先在 P 上取点再连三角形。',ha='center',fontsize=14,
             bbox={'boxstyle':'round,pad=.6','fc':'#f0f5fa','ec':'none'})
    save(fig,'pt_03_same_points_to_P_and_T')


def parameterization():
    ref=load_model(ROOT/'results'/'20261024_v2'/'models'/'reference_local')
    t=np.linspace(0,6,2401);p=ref.evaluate(1,t,413.)
    cut=150.;left=ref._wall(1,cut,413.,0);right=ref._wall(1,cut,413.,1)
    fig,axes=plt.subplots(1,2,figsize=(16,10))
    fig.subplots_adjust(left=.06,right=.98,top=.79,bottom=.37,wspace=.25)
    fig.suptitle('原理图 4｜同一条轮廓，可以用两套“找点方法”描述',fontsize=25,y=.985)
    fig.text(.5,.928,'这一图读取本轮已保存的合成参考：中央条纹，Z = 413 nm。高度方向放大显示，便于辨认圆肩。',ha='center',fontsize=13.5,color=GRAY)
    ax=axes[0]
    ax.fill(p[:,0],p[:,1],color='#edf4f8');ax.plot(p[:,0],p[:,1],color=INK,lw=2.4)
    ax.axhline(cut,color=ORANGE,ls='--',lw=1.6)
    ax.scatter([left,right],[cut,cut],color=[BLUE,ORANGE],s=60,zorder=4)
    ax.annotate('左交点 xL(150,413)',xy=(left,cut),xytext=(-1070,230),fontsize=12,color=BLUE,arrowprops={'arrowstyle':'->','color':BLUE})
    ax.annotate('右交点 xR(150,413)',xy=(right,cut),xytext=(220,80),fontsize=12,color=ORANGE,arrowprops={'arrowstyle':'->','color':ORANGE})
    ax.text(0,cut+14,'固定 Y = 150 nm，向左右找边界',ha='center',fontsize=11)
    ax.set_title('① 用高度 Y 找点：一层一层读左右边界',pad=16)
    ax.text(.5,-.25,'输入 (Y,Z) → 得到左边 X、右边 X\n材料区间：xL(Y,Z) ≤ X ≤ xR(Y,Z)',transform=ax.transAxes,ha='center',fontsize=15,linespacing=1.7)
    ax=axes[1];ax.fill(p[:,0],p[:,1],color='#edf4f8')
    labels=['左壁','左肩','顶面','右肩','右壁','底面']
    for k in range(6):
        tt=np.linspace(k,k+1,101);pp=ref.evaluate(1,tt,413.)
        ax.plot(pp[:,0],pp[:,1],lw=3.3,color=COLORS[k])
        a=ref.evaluate(1,k+.40,413.);b=ref.evaluate(1,k+.60,413.)
        ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','color':COLORS[k],'lw':2.5})
    points=ref.evaluate(1,np.arange(7,dtype=float),413.)
    for k in range(6):
        q=points[k];ax.scatter(*q,color=COLORS[k],s=27,zorder=5)
    labels_with_pos=[('t = 0 / 6',(-1070,-32)),('t = 1',(-1070,215)),('t = 2',(-690,355)),('t = 3',(370,355)),('t = 4',(850,210)),('t = 5',(850,-32))]
    for lab,pos in labels_with_pos:ax.text(*pos,lab,fontsize=11,color=INK)
    ax.set_title('② 用轮廓进度 t 找点：沿边界走一圈',pad=16)
    ax.text(.5,-.25,'输入 (t,Z) → 得到 X = x(t,Z)、Y = y(t,Z)\n三维边界点 S(t,Z) = (x(t,Z), y(t,Z), Z)',transform=ax.transAxes,ha='center',fontsize=15,linespacing=1.7)
    for ax in axes:
        ax.set(xlim=(-1150,1150),ylim=(-55,405),xlabel='X / nm',ylabel='Y / nm',xticks=[-800,0,800],yticks=[0,150,300]);ax.grid(alpha=.1)
    bar=fig.add_axes([.12,.167,.76,.065]);bar.set_xlim(0,6);bar.set_ylim(0,1);bar.set_axis_off()
    for k,label in enumerate(labels):
        bar.add_patch(Rectangle((k,.05),1,.55,facecolor=COLORS[k],alpha=.95))
        bar.text(k+.5,.33,label,ha='center',va='center',color='white',fontsize=14)
        bar.text(k,.78,str(k),ha='center',fontsize=12)
    bar.text(6,.78,'6 = 回到起点',ha='center',fontsize=12)
    fig.text(.5,.108,'t 是沿轮廓走到哪里，不是时间，也不是 nm；代码中这个轮廓参数名叫 u。',ha='center',fontsize=14)
    fig.text(.5,.037,'注意：轮廓参数 u 与位移场 uL、uR 不是同一个量。改用 C(t,Z) 不会自动增加几何细节；\n它只是让侧壁、圆肩、顶面、底面能用统一方式连接和插值。左右边界函数本身也能表示圆肩。',ha='center',fontsize=13,linespacing=1.6,
             bbox={'boxstyle':'round,pad=.55','fc':'#f0f5fa','ec':'none'})
    save(fig,'pt_04_height_vs_contour_parameter')


if __name__ == '__main__':
    sweep();fields();construction();parameterization()
    print('Wrote 4 P/T principle diagrams as PNG + SVG to', OUT)
