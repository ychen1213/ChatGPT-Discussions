# 三种几何表示总结的图与证据

本目录支持上一级的三页领导摘要与详细比较。图 1 是原理示意；图 2 和图 3 读取已保存的实验记录及小型挑战输入生成。没有重跑或改写原实验。

| 文件 | 用途 |
| --- | --- |
| `figures/01_representation.png` / `.svg` | 同一形状的 V、T、P 保存方式示意 |
| `figures/02_measured_tradeoff.png` / `.svg` | 同一 5 nm 体素输入下，全部三档 P 与直接 T 的截面误差和几何文件大小 |
| `figures/03_topology_challenges.png` / `.svg` | 四类小型挑战的输入形状与结果 |
| `comparison_evidence.json` | 图表数值、单位及其原始记录位置 |
| `pdf_layout_checks.json` | PDF 页数、文字布局检查 |
| `delivery_checks.json` | 最终图文、链接与浏览器检查记录 |

图和 HTML 使用验证项目环境生成：

```powershell
cd 3D-Geometry/ah53-geometry-validation
.\.venv\Scripts\python.exe scripts/build_executive_comparison_figures.py
.\.venv\Scripts\python.exe scripts/build_comparison_documents.py --html
```

PDF 用独立文档环境生成，避免改动实验环境。需要 `reportlab`、`pypdf` 以及 Windows 微软雅黑字体；在相同工作目录执行：

```powershell
python scripts/build_comparison_documents.py --pdf
```

PDF 输出到上一级，与领导摘要 HTML、Markdown 同名。建议使用 `pdftoppm` 将三页渲染成图片检查后再分发。完整评分模型和大体素仍保留在本机原结果目录，图表不能替代它们。
