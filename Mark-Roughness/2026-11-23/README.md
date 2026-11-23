# 随机 Mark 边缘参数化与电磁仿真

**日期：2026-11-23** · Alignment / Overlay Mark · RCWA / FDTD · LER / LWR

本目录归档了随机粗糙边缘参数化、PSD、相邻边缘/高度相关性、三维电磁仿真、以及以 AL / WQ / APD 为约束的细节截断方案。

## 文件

- [调研报告文本（22 页 PDF 的全文提取）](mark_roughness_research_text_2026-11-23.md)：包含报告正文、实施路线、参考文献。因由 PDF 提取，原版图表布局和排版不会完整保留。
- [31 处可编辑 LaTeX 公式](roughness_equations_LaTeX.tex)：完整 XeLaTeX 公式集合，使用 `ctexart`、`amsmath` 与 `unicode-math`。这是**公式合集**，不是完整报告的 LaTeX 源文件。

## 核心技术结论

1. 单值边缘可通过 Fourier / B-spline 基函数叠加表示；随机场应由 PSD、幅度分布、左右边缘互相关、邻线相关以及高度相关性约束。
2. 优先将边缘分解为中心线偏移和线宽变化，避免 CD、位置和侧壁角参数重复计入。
3. 沿条纹的随机变化一般使原一维衍射问题转为三维散射问题；用 3D RCWA 超胞或 3D FDTD 严格验证，并保留二维角谱复振幅。
4. 小于波长、被 NA 截断或小于网格的几何细节不应直接忽略，应采用固定 seed 的带宽截断收敛，并以完整扫描曲线和定位 KPI 的配对误差验收。

## 公式编译

在安装了 TeX Live 的环境中：

```bash
xelatex roughness_equations_LaTeX.tex
```

**归档说明：**原始的两份 22 页图文 PDF（LaTeX 版与中文兼容版）仍保留在对应的 ChatGPT 会话文件中。当前 GitHub 连接器只支持从文本内容创建文件，未能直接读取并提交 PDF 二进制文件。故本目录目前上传的是**文本与 LaTeX 源码**，不是 PDF 原件。

## 打包下载

- [LaTeX 与 Markdown 源码压缩包](mark_roughness_LaTeX_source_bundle_2026-11-23.zip)：已通过 GitHub 二进制 blob 上传，包含原生可编辑公式、报告全文文字转存及本 README。
- **原始 22 页图文 PDF 不在上述 ZIP 中。** 目前 GitHub 连接器不能直接读取本地 PDF 二进制字节；含两份 PDF 原件的完整 ZIP 已在 ChatGPT 当前会话生成，需通过会话附件下载。
