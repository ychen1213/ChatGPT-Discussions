"""Build an offline Chinese inventory; read existing artifacts without rebuilding geometry."""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
HTML_NAME = "文件用途索引.html"
JSON_NAME = "文件用途索引.json"
RUNTIME_NAMES = {".venv", "__pycache__", ".pytest_cache", ".playwright-cli"}

EXACT = {
    ".gitattributes": "指定 Git 对第三方库和自动生成 SVG 的空白检查规则；不影响几何计算或网页内容。",
    ".gitignore": "告诉 Git 哪些本机环境、缓存和大型结果不需要提交；它不控制查看器显示。",
    "启动3D查看器.bat": "Windows 双击入口：调用同目录 PowerShell 启动脚本，再打开本机 3D 网页。新人看模型从这里开始。",
    "启动3D查看器.ps1": "实际启动逻辑：检查 Python 环境、选择空闲端口、运行查看器服务。通常由 .bat 自动调用。",
    "先看这里.md": "项目入口和最短操作步骤；Markdown 文本，可用编辑器阅读。",
    "README.md": "新人和开发者共用的项目入口：说明阅读路径、已有成果及安装、生成、启动、测试命令。",
    "requirements.txt": "运行项目所需的 Python 库清单；供 pip 安装，通常不用手改。",
    "requirements-dev.txt": "在运行库之外补充测试/开发依赖的清单。",
    "run_validation.py": "实验总控程序：生成参考和观测、建立 P/T/V、执行 A 与 B、检查局部编辑并汇总结果。运行会生成大文件，不是打开现有模型的入口。",
    "serve_viewer.py": "本机 3D 服务：读取已保存模型，提供显示网格、截面和截图接口；网页默认在 127.0.0.1:8765。",
    "configs/default.json": "本轮默认实验配方：名义宽高、坐标、随机种子、合成起伏、场景范围和粗细步长。修改它不会自动改变已经保存的模型。",
    "inputs/source_provenance.json": "输入证据账本：计划书地址、参考项目/GDS 路径、尺寸核对和文件指纹；解释哪些数有来源、哪些是验证假设。这里没有复制原始 GDS。",
    "src/ah53/__init__.py": "Python 包入口，把读取器和 P/T/V 类开放给其他程序调用。",
    "src/ah53/common.py": "三种表示共用的坐标、轮廓采样、观测保存、网格连接、文件指纹及模型读取工具。",
    "src/ah53/reference_geometry.py": "定义合成参考形状：曲壁、左右圆肩、顶面和沿长度方向起伏；它是本次比较的已知标准答案。",
    "src/ah53/parametric.py": "P 的构建与读取：用分区三次样条保存光滑轮廓，支持求截面和局部修改控制系数。",
    "src/ah53/surface.py": "T 的构建与读取：保存顶点和三角连接关系、求真实三角形截面、检查闭合和执行顶点局部编辑。",
    "src/ah53/voxel.py": "V 的构建与读取：按小方格中心判定材料，保存标签体，查询标签及显示原始方格边界。",
    "src/ah53/evaluate.py": "评估程序：距离误差、体积、边缘曲线、资源和文件清单；负责比较模型与参考。",
    "scripts/audit_provenance.py": "重新核对外部示例输入和名义尺寸，更新 inputs/source_provenance.json 的文件指纹及证据。",
    "scripts/audit_saved_results.py": "读取已保存模型做后续核查：补充高度曲线、逐格比较不同转换结果、记录读取隔离证据；会更新报告记录。",
    "scripts/audit_core_and_samples.py": "核查保存的网格闭合/朝向等关键性质，并从正式模型裁出 samples 小样；不会重建正式模型。",
    "scripts/repair_volume_metrics.py": "用独立积分位置重新核算体积这一辅助指标，修正统计记录；不修改模型几何文件。",
    "scripts/build_report.py": "读取实验结果、绘制 01～08 图并生成原技术说明；重跑会更新对应报告与图。",
    "scripts/report_template.md": "原技术报告的 Markdown 模板，里面有生成脚本需要替换的占位内容。",
    "scripts/finalize_ui_evidence.py": "整理浏览器操作验收记录，把最终截图复制进正式结果目录并写 ui_validation.json。",
    "scripts/ui_acceptance.js": "浏览器自动验收步骤：旋转、缩放、切模型、切截面、保存截图和查看说明；给测试工具执行。",
    "scripts/ui_flow.js": "一组较早的浏览器连续操作流程，记录各步骤的状态和耗时。",
    "scripts/ui_routes.js": "检查 B1～B4 的模型选择对应关系，并检查页面资源是否来自本机。",
    "scripts/ui_document.js": "用浏览器检查新手说明的离线图片加载、目录锚点和窄窗口排版，并保存验证证据。",
    "scripts/build_file_index.py": "重新扫描项目并生成本文件用途索引；只读模型与结果，不生成新的 3D。",
    "tests/conftest.py": "测试初始化：配置 Python 导入路径和共用测试设置。",
    "tests/test_geometry.py": "几何相关自动检查，验证构建/读取/查询/局部操作的关键性质。",
    "tests/test_metrics.py": "误差计算相关自动检查，防止评价公式或采样规则出现回归。",
    "tests/test_run_configuration.py": "配置和续跑检查，防止把不同实验设置误当成同一轮结果。",
    "viewer/index.html": "3D 网页的页面骨架和控件；需要本机服务配合，建议用启动 .bat 打开。",
    "viewer/app.js": "3D 网页交互逻辑：加载模型、相机、切面、颜色、倍率和截图。",
    "viewer/style.css": "3D 网页的字体、颜色、布局及窄窗口样式。",
    "viewer/THIRD_PARTY.md": "本项目所用第三方网页库的来源和许可说明。",
    "viewer/vendor/three.module.js": "已随项目保存的 Three.js 三维绘图库，负责把三角形绘制到浏览器画面。",
    "viewer/vendor/OrbitControls.js": "Three.js 的相机控制工具，提供鼠标旋转、平移和缩放。",
    "viewer/vendor/THREE-LICENSE.txt": "Three.js 的使用许可；与库文件一起保留。",
    "samples/README.md": "三个实际模型小样的读取说明、坐标、来源与限制。",
    "samples/inspect_samples.py": "轻量读取小样并打印数组名称、维度、类型；不绘图，也不运行整轮实验。",
    "samples/sample_manifest.json": "小样身份卡：单位、裁取范围、来源模型和文件指纹。",
    "samples/central_stripe_triangles.npz": "从正式直接三角面裁出的中央一条纹：顶点、三角连接、原顶点编号及材料编号；完整闭合条纹，Z=-2000～2000 nm。",
    "samples/central_stripe_splines.npz": "从正式 P 裁出的中央一条纹样条系数及结点；六段轮廓，Z=-2000～2000 nm。",
    "samples/central_stripe_voxels.npz": "从正式 5 nm 标签体裁出的小区域；含标签、原点、步长和边界，Z=-200～800 nm，只是矩形局部裁片。",
    "samples/AH53_实际模型小样.zip": "上述小样及配套说明的便携压缩包；解压后仍是 NumPy 数据，不是 STL/OBJ/STEP。",
    "results/latest.txt": "记录最近结果批次的名字，当前为 20261024_v2；是文本指针，不是模型。",
    HTML_NAME: "本离线文件索引：可搜索名字、用途、路径，按文件夹展开每个实际文件。",
    JSON_NAME: "本索引的机器可读版本；包含逐文件路径、字节数、用途与运行环境分组统计。",
    "docs/文件与模型指南.md": "新手文件指南：模型地址、三种格式、目录含义、如何打开和哪些文件必须一起保留。",
    "docs/新手教程正文.md": "新手主教程的可编辑文字来源，解释实验目的、原理、各图和实际操作。",
    "docs/新手逐图讲解.md": "逐张解释报告图：它在回答什么问题、坐标和颜色怎么读、可以与不可以得出什么结论。",
    "docs/概念图说明.md": "新手概念图的文字说明，区分教学示意与正式测量结果。",
    "scripts/build_beginner_guide.py": "把新手教程正文及补充说明排版为 HTML/Markdown 交付文档；不改变正式几何模型。",
    "scripts/build_beginner_figures.py": "生成新手解释图（坐标、三种表示、实验流程、指标），其中实际形状读取已保存模型；不改正式结果。",
}
RESULTS = {
    "manifest.json": "整轮实验总账：使用的配置、机器环境、批次状态以及 A/B 的执行情况。",
    "preparation.json": "实验准备记录：参考对象、观测数据、准备耗时/内存和参考体积。",
    "lineage.json": "模型来历链：每份模型从谁生成、用了什么操作、输入和输出文件指纹；用于追溯转换。",
    "metrics.csv": "各模型对合成参考的指标总表，包括截面误差、体积、用时和存储等；Excel 可打开。",
    "conversions.csv": "B 转换路径的指标总表，区分相对上游的新增误差与相对参考的累计误差。",
    "edit_check.json": "局部编辑的详细证据：改了哪些系数/顶点、范围外是否变化、下游重建与测量结果。",
    "edit_check.md": "局部编辑检查的简短人类可读摘要。",
    "core_geometry_audit.json": "正式模型的关键几何核查记录，如网格是否闭合、朝向及读取后的性质。",
    "saved_model_isolation.json": "检查读取/查询是否真正使用保存的模型文件，避免后台偷用参考生成器。",
    "voxel_pairwise.json": "逐体素对照 B2/B3/B4 的最终标签，统计相同和不同的格子。",
    "volume_quadrature_audit.json": "体积辅助指标复算的定义、收敛检查和修正前后数值；不是边界精度。",
    "post_run_audit.json": "运行结束后的补充核查总记录。",
    "ui_validation.json": "真实浏览器操作验收记录与实测加载时间；说明查看器能否按步骤操作。",
    "viewer_backend_checks.json": "查看器服务端检查：路径、端口占用、缺失环境等恢复情况。",
    "delivery_check.json": "交付时的结果完整性检查摘要。",
    "beginner_guide_validation.json": "新版新手文档的质量检查结果：离线图片、内部链接/目录锚点与窄屏显示等，不是几何精度评估。",
}
FIGURES = {
    "01_nominal_layout.png": "名义版图图：帮助认识条纹排列、母周期与空白区。",
    "02_cross_sections.png": "截面图：从切开的轮廓比较曲壁、顶面及左右形状。",
    "03_shoulder_comparison.png": "圆肩局部放大图：比较 P/T/V 对小弯曲处的保留情况。",
    "04_edge_waviness.png": "局部边缘起伏图：观察沿条纹长度方向的边缘变化与统计。",
    "05_error_resources.png": "误差与数组负载比较图：左侧看数组负载 MB 与整体截面 P95 的取舍，右侧看各表面分区的 P95；本图没有画耗时或运行内存。",
    "06_full_mark.png": "完整场景示意图：看多母周期和九条纹在全域中的排布。",
    "07_conversion_errors.png": "转换误差图：比较 B 路径的新增误差和累计误差。",
    "08_full_edge_waviness.png": "全域长度上的中心位置与 CD（条纹宽度）波动图；本图没有高度曲线。",
    "viewer_full.png": "查看器全域画面的验收截图；是二维照片，不是 3D 数据文件。",
    "viewer_screenshot.png": "查看器圆肩局部画面的验收截图；用于说明界面和叠加效果。",
    "viewer_voxel.png": "查看器体素画面的验收截图；可见格子边界。",
}


def model_name(identifier):
    scope = "全域" if identifier.startswith("full_") or identifier == "reference_full" else "局部"
    if "observations" in identifier:
        return scope + ("粗档" if "coarse" in identifier else "细档") + "共同观测点（P 与直接 T 的输入）"
    if identifier.startswith("reference_"):
        return scope + "合成参考定义（标准答案）"
    if "_V_from_Tdirect" in identifier:
        family = "B4：直接三角面 T → 体素 V"
    elif "_V_from_T" in identifier:
        family = "B3：P → T → V 的最终体素"
    elif "_V_from_P" in identifier:
        family = "B2：P → V 的体素"
    elif "_T_from_P" in identifier:
        family = "B1：P → T 的三角面（也是 B3 中间结果）"
    elif "_T_direct" in identifier:
        family = "A：从共同观测点直接连接的三角面 T"
    elif "_V_direct" in identifier:
        family = "A：由合成参考直接分类的体素 V"
    elif "_P_" in identifier:
        family = "A：由共同观测点建立的参数化 P"
    else:
        family = identifier
    level = "；粗档" if "coarse" in identifier else "；细档" if "fine" in identifier else "；10 nm 格子" if "10nm" in identifier else ""
    edit = "；局部编辑后的另存副本" if "edited" in identifier else ""
    return scope + " " + family + level + edit


def describe(relative):
    parts = Path(relative).parts
    name = parts[-1]
    if relative in EXACT:
        return EXACT[relative]
    if parts[0] == "results":
        if "models" in parts:
            ident = parts[parts.index("models") + 1]
            prefix = model_name(ident) + "。"
            meaning = {
                "metadata.json": "这份数据的身份卡：类型、单位、范围、材料、来源和构建设置；须与本目录数字数据一起保留。参考目录仅以此保存定义。",
                "splines.npz": "真实参数化模型数据：c0～c5 为六段轮廓的系数，u0～u5/z0～z5 为结点；用程序求值后得到光滑曲面。",
                "vertices.npy": "真实三角面顶点表：每一行是一个 XYZ 坐标（nm）；必须配合同目录 faces.npy 才知道怎样连成表面。",
                "faces.npy": "真实三角面连接表：每一行有三个从 0 开始的顶点编号；与 vertices.npy 共同构成三角表面。",
                "labels.npy": "真实体素标签体：按 Z、Y、X 排列的小方格材料编号，0=空气、1=条纹、2=衬底；位置与步长见 metadata.json。",
                "points.npy": "共同观测点坐标：条纹×Z 截面×轮廓位置×XY；是 P/T 建模输入，不是成品曲面。",
                "u.npy": "截面轮廓的位置参数表；u 标记沿轮廓的顺序/分区，不是以 nm 表示的 X 轴坐标。",
                "z.npy": "沿条纹长度的截面位置表，单位 nm；与观测/网格的截面层相对应。",
            }
            return prefix + meaning.get(name, "该模型的配套记录，需结合 metadata.json 阅读。")
        if "details" in parts:
            return model_name(Path(name).stem) + "的逐项评估记录：构建来源、文件指纹、误差分区、用时和资源；CSV 的细节在这里。"
        if "profiles" in parts:
            return model_name(Path(name).stem) + "的边缘/宽度/高度曲线数组，用于绘图与统计；不是完整 3D 源模型。"
        if "previews" in parts:
            if name.endswith(".json.gz"):
                return "查看器用的压缩显示网格缓存。文件名标明模型、显示范围和 Z 位置；可能裁切或简化，只为快速显示，不能替代 models 中的正式精度数据。"
            return "相应预览的显示说明：模型来源、采样/简化方式、显示面数和构建耗时；配合同名范围的压缩缓存。"
        if "screenshots" in parts:
            return "手动保存的查看器画面及当时状态。" + ("PNG 是二维截图。" if name.endswith(".png") else "JSON 保存选中的模型、截面、相机/显示等状态，便于追溯截图。")
        if "figures" in parts:
            return FIGURES.get(name, "报告附图；展示或解释计算结果，图片本身不是模型。")
        if name in RESULTS:
            return RESULTS[name]
    if parts[0] == "output":
        if name.endswith(".png"):
            return "浏览器验收过程截图：" + {"full_final950.png":"全域最终画面。", "initial950.png":"较小窗口的初始画面。", "shoulder950.png":"圆肩局部画面。", "voxel_final950.png":"体素最终画面。", "report_offline_top.png":"原报告顶部的离线显示。", "report_offline_results.png":"原报告结果部分的离线显示。"}.get(name, "用于检查页面显示，不是模型。")
        return "浏览器验收工具的文字输出，包含操作结果/耗时和诊断信息；供排查界面问题。"
    if "技术验证报告" in name:
        return "保留的原技术报告：完整方法、统计与证据。" + ("HTML 用浏览器看图和表。" if name.endswith(".html") else "Markdown 为文字版本。")
    if "详细说明" in name:
        return "新版新手主说明：从目的、概念、步骤到读图和文件，按初学者顺序展开。" + ("HTML 用浏览器看图和表。" if name.endswith(".html") else "Markdown 为文字版本。")
    if "新手" in name or "入门" in name or "零基础" in name or "图解" in name:
        return "面向新人的说明资料，解释目的、原理、图表和操作。浏览器阅读 HTML；文本编辑器阅读 Markdown。"
    if parts[0] == "docs" and "figures" in parts:
        purpose = {"01_方向与尺度":"新手导读图：解释 X/Y/Z 的物理方向、局部/全域尺度与单位。", "02_三种表示实际圆肩":"新手导读图：用实际圆肩比较光滑 P、三角面 T 和体素 V 的形状表示。", "03_A与B验证流程":"新手导读流程图：交代 A 的独立表示比较与 B 的模型转换关系。", "04_指标怎么读":"新手导读图：帮助理解误差统计的读法和适用范围。"}.get(Path(name).stem, "新手说明配图。")
        return purpose + ("SVG 为可缩放的矢量版本。" if name.endswith(".svg") else "PNG 为便于浏览的图片版本。")
    if parts[0] == "docs":
        return "补充说明文档：用于理解实验、图表或文件，不包含可独立显示的三维模型。"
    if parts[0] == "scripts":
        return "项目辅助脚本；先阅读脚本说明再运行，普通看模型无需运行。"
    return "项目配套文件；按下方扩展名说明选择阅读工具。用途未从固定清单确定，不能据文件名把它当作正式模型。"


def usage(relative):
    p = Path(relative)
    suffix = p.suffix.lower()
    if suffix in {".npy", ".npz"}:
        return "用项目查看器/NumPy 读取；不要当文本编辑。分享正式模型时复制整个模型子目录。"
    if p.name.endswith(".json.gz"):
        return "由查看器自动使用；不必手动打开。压缩显示缓存可重新生成。"
    if suffix == ".html":
        return "浏览器打开；viewer/index.html 请通过启动脚本打开。"
    if suffix == ".csv":
        return "Excel/表格软件或文本编辑器打开；建议保留原记录，分析时另存副本。"
    if suffix == ".png":
        return "系统照片查看器打开；这是二维图。"
    if suffix == ".svg":
        return "浏览器或矢量图编辑器打开；缩放不易模糊，这是二维说明图。"
    if suffix == ".json":
        return "文本编辑器查看结构化记录；结果/模型元数据不宜随意改。configs 中的配方可另存后调整。"
    if suffix in {".md", ".txt"}:
        return "文本编辑器阅读；Markdown 预览更适合看表格。"
    if suffix == ".zip":
        return "资源管理器解压；里面的数据仍需相应读取工具。"
    if suffix == ".bat":
        return "Windows 双击运行启动器。"
    if suffix in {".py", ".js", ".css", ".ps1"}:
        return "源程序/样式文件；编辑器可看代码，新人先使用现成入口。修改后才会影响对应程序行为。"
    return "先看用途；无须为了浏览结果而修改。"


def category(relative):
    parts = Path(relative).parts
    if parts[0] == "results":
        for folder, title in (("models", "正式模型及共同观测"), ("details", "逐模型评估明细"), ("profiles", "测量曲线数组"), ("figures", "报告图与截图"), ("previews", "查看器显示缓存")):
            if folder in parts:
                return title
        return "结果总表与核查记录"
    return {"samples": "可分享的小型模型样例", "src": "几何实现源码", "scripts": "辅助生成与核查脚本", "tests": "自动检查代码", "viewer": "查看器网页与离线依赖", "configs": "实验配方", "inputs": "输入来源证据", "output": "浏览器检查过程记录", "docs": "补充说明文档"}.get(parts[0], "根目录与入口文档")


def make_html(data):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AH53 文件用途索引</title><style>
    :root{font-family:'Microsoft YaHei',system-ui,sans-serif;color:#16304a;background:#f3f6fa}body{max-width:1180px;margin:auto;padding:30px 20px 70px;line-height:1.75}h1{font-size:32px}a{color:#0866b5}code{overflow-wrap:anywhere;background:#edf2f7;padding:2px 4px;border-radius:4px}header,.intro,details{background:white;border:1px solid #dce4ed;border-radius:12px;padding:18px 22px;margin:14px 0}input,select,button{font:inherit;border:1px solid #a9bbcd;border-radius:7px;padding:10px;background:#fff}input{flex:1;min-width:190px}.controls{display:flex;gap:10px;flex-wrap:wrap;position:sticky;top:0;padding:12px 0;background:#f3f6fa;z-index:1}.file{padding:17px 0;border-top:1px solid #e5ebf1}.path{font-family:Consolas,monospace;font-size:13px;color:#52687d;overflow-wrap:anywhere}.meta{color:#52687d;font-size:13px}.purpose{margin:8px 0}.usage{font-size:14px;color:#546778}summary{cursor:pointer;font-weight:bold}.tag{font-size:12px;padding:2px 8px;background:#e6f0fa;border-radius:20px}#empty{padding:30px}.runtime{background:#f7f8fa}.address{white-space:pre-wrap;overflow-wrap:anywhere}a{overflow-wrap:anywhere}@media(max-width:600px){body{padding:15px 10px}header,.intro,details{padding:14px}h1{font-size:25px}}@media print{.controls{display:none}body{max-width:none;background:white}details{break-inside:auto}.file{break-inside:avoid}}
    </style></head><body><header><p class="tag">逐文件说明 · 可离线搜索</p><h1>AH53 文件用途索引</h1><p>先找三维模型：<code>results/20261024_v2/models/</code>。这里逐个列出项目自己的文件；Python 安装库和自动缓存按组解释，避免数千个库文件淹没实际结果。</p><p><a href="docs/文件与模型指南.md">文件与模型文字指南</a> · <a href="AH53_三种几何表示验证_详细说明.html">实验说明</a> · <a href="文件用途索引.json">机器可读清单</a></p><p id="snapshot" class="meta"></p></header><section class="intro"><b>这些三维模型目前使用项目自己的 NumPy 数据格式。</b><p>P 的 <code>splines.npz</code>、T 的 <code>vertices.npy + faces.npy</code>、V 的 <code>labels.npy</code> 都是真实保存的数据；请连同同目录配套文件保留。本轮没有把它们导出成 STL、OBJ 或 STEP。看形状请双击 <a href="启动3D查看器.bat">启动3D查看器.bat</a>（若浏览器不允许运行，请在资源管理器双击）；本索引点到二进制数据时，浏览器可能下载它，并不会自动显示三维。</p><p>正式模型 ≠ <code>previews</code> 显示缓存 ≠ <code>figures</code> 图片 ≠ <code>profiles</code> 测量曲线。</p></section><div class="controls"><input id="search" aria-label="搜索文件、用途或模型名" placeholder="搜索，例如 labels / B3 / 圆肩 / local_P_fine"><select id="category" aria-label="文件类别"><option value="">全部类别</option></select><button id="expand">全部展开</button><button id="collapse">全部收起</button></div><p id="count" class="meta"></p><main id="files"></main><section id="runtime"></section><script id="inventory" type="application/json">""" + payload + """</script><script>
    const data=JSON.parse(document.getElementById('inventory').textContent),el=document.getElementById('files');
    const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    function bytes(n){return n>=1e9?(n/1e9).toFixed(3)+' GB':n>=1e6?(n/1e6).toFixed(3)+' MB':n>=1e3?(n/1e3).toFixed(2)+' kB':n+' B'}
    const cats=[...new Set(data.files.map(f=>f.category))];cats.forEach(c=>{const o=document.createElement('option');o.value=c;o.textContent=c;document.getElementById('category').append(o)});
    document.getElementById('snapshot').textContent='清单日期：'+data.date_local+'（香港时间）｜根目录：'+data.root+'｜文件大小按十进制 B/kB/MB/GB 显示。索引是生成时快照。';
    function render(){const query=document.getElementById('search').value.trim().toLowerCase(),cat=document.getElementById('category').value;const list=data.files.filter(f=>(!cat||f.category===cat)&&(!query||(f.relative_path+' '+f.purpose+' '+f.category).toLowerCase().includes(query)));document.getElementById('count').textContent='当前 '+list.length+' / '+data.files.length+' 个项目文件；另有 '+data.runtime_groups.length+' 组运行环境/缓存。';let content='';for(const c of cats){const items=list.filter(f=>f.category===c);if(!items.length)continue;content+='<details '+(query?'open':'')+'><summary>'+esc(c)+' · '+items.length+' 个文件</summary>'+items.map(f=>'<article class="file"><b><a href="'+esc(f.href)+'">'+esc(f.relative_path)+'</a></b><div class="meta">'+bytes(f.size_bytes)+' · '+f.size_bytes.toLocaleString()+' 字节</div><div class="path">'+esc(f.absolute_path)+'</div><p class="purpose">'+esc(f.purpose)+'</p><div class="usage">怎么用：'+esc(f.how_to_use)+'</div></article>').join('')+'</details>';}el.innerHTML=content||'<p id="empty">没有匹配文件。试试更短的名字或选择全部类别。</p>';}
    document.getElementById('search').addEventListener('input',render);document.getElementById('category').addEventListener('change',render);document.getElementById('expand').onclick=()=>document.querySelectorAll('#files details').forEach(e=>e.open=true);document.getElementById('collapse').onclick=()=>document.querySelectorAll('#files details').forEach(e=>e.open=false);render();
    document.getElementById('runtime').innerHTML='<details class="runtime"><summary>运行环境与自动缓存：为什么没有逐个解释第三方库源码？</summary><p>这些文件是安装或运行软件自动产生的。它们服务于程序运行，不是本轮几何实验的自定义成果。按目录说明用途，比逐行列出数千个库文件更有助于找到模型。</p>'+data.runtime_groups.map(g=>'<article class="file"><b>'+esc(g.path)+'</b><div class="meta">'+g.file_count+' 个文件 · '+bytes(g.total_bytes)+'</div><p>'+esc(g.purpose)+'</p><div class="path">'+esc(g.absolute_path)+'</div></article>').join('')+'</details>';
    </script></body></html>"""


def main():
    files = []
    runtime = defaultdict(lambda: {"file_count": 0, "total_bytes": 0})
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        parts = path.relative_to(ROOT).parts
        group = next((p for p in parts if p in RUNTIME_NAMES), None)
        if group:
            key = "/".join(parts[:parts.index(group)+1])
            runtime[key]["file_count"] += 1
            runtime[key]["total_bytes"] += path.stat().st_size
            continue
        if any(p == ".git" for p in parts):
            continue
        files.append({"relative_path": rel, "absolute_path": str(path), "href": quote(rel, safe="/"), "size_bytes": path.stat().st_size, "category": category(rel), "purpose": describe(rel), "how_to_use": usage(rel)})
    existing = {f["relative_path"] for f in files}
    for name in (HTML_NAME, JSON_NAME):
        if name not in existing:
            files.append({"relative_path": name, "absolute_path": str(ROOT/name), "href": quote(name), "size_bytes": 0, "category": category(name), "purpose": describe(name), "how_to_use": usage(name)})
    files.sort(key=lambda f: f["relative_path"])
    explanations = {".venv":"项目专用 Python 运行环境及第三方库。查看器依赖它；看结果不需要阅读这些库源码。删除后须重新安装环境。", "__pycache__":"Python 自动生成的编译缓存，来自同目录 .py；不是模型，运行时可以重新产生。", ".pytest_cache":"自动测试工具的上次运行状态/缓存；不是测试结果正文或模型。", ".playwright-cli":"浏览器自动化的页面快照、控制台日志和临时截图；正式验收记录另存于 output/playwright 和 results 的 JSON。"}
    groups = [{"path": key, "absolute_path": str(ROOT/key), **value, "purpose": explanations[Path(key).name]} for key, value in sorted(runtime.items())]
    # The user-facing date follows the client's Hong Kong date for this delivery.
    data = {"date_local": "2026-10-24", "root": str(ROOT), "scope": "项目文件逐项列出；第三方运行环境及自动缓存按组统计", "files": files, "runtime_groups": groups}
    # Resolve the two generated files' own sizes without stale size entries.
    for _ in range(12):
        json_text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        html_text = make_html(data)
        sizes = {JSON_NAME: len(json_text.encode("utf-8")), HTML_NAME: len(html_text.encode("utf-8"))}
        changed = False
        for f in files:
            if f["relative_path"] in sizes and f["size_bytes"] != sizes[f["relative_path"]]:
                f["size_bytes"] = sizes[f["relative_path"]]
                changed = True
        if not changed:
            break
    else:
        raise RuntimeError("Inventory self-size did not converge")
    (ROOT/JSON_NAME).write_bytes(json_text.encode("utf-8"))
    (ROOT/HTML_NAME).write_bytes(html_text.encode("utf-8"))
    total = sum(f["size_bytes"] for f in files)
    print(json.dumps({"indexed_project_files": len(files), "project_bytes": total, "runtime_groups": len(groups), "outputs": [HTML_NAME, JSON_NAME]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
