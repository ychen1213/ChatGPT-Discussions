# ASML iDBO：晶圆 → 光瞳 → 四象限 Wedge → 四圆相机图像

**[打开 HTML 源文件（GitHub）](2026-10-28_ASML_iDBO_晶圆光瞳四圆成像_完整理论交互教程.html)**

这是以 **ASML US11385552B2 Figures 3–7** 和 **WO2024002546A1 Figure 4** 为主要公开依据的中文版、独立离线交互教程。GitHub 不会在 blob 页面直接执行 HTML，点击文件上的 **Raw / Download raw file** 下载后，用 Chrome / Edge 打开即可。

## 内容

- 晶圆上四个 X+/X−/Y+/Y− Overlay Pad 的空间图案与同一圆形照明光斑；
- 0、±1 阶衍射的横向波矢及物镜圆形 NA 光瞳；
- ASML 专利的 a/b 两个照明象限、四个 Wedge 通道（502/504/506/508）；
- **为什么四分之一圆形光瞳不能理解成四分之一晶圆图像**：角空间傅里叶滤波和逆傅里叶重成像；
- **为什么最终是四个完整圆，每个圆里有四个矩形Pad亮度块**；
- 23组说明性公式、16幅内嵌SVG和互动Wedge分像程度滑块；
- Overlay 偏置±d、双层图案相对位置、+1/−1强度非对称及小位移反演；
- 2D Mark 的X/Y串扰与相对旋转90°的两次采集；
- RCWA/FDTD散射系数→角谱→光瞳→相机ROI的程序实现路线。

## 专利中四通道的准确对应

| 相机通道 | 来源 |
|---|---|
| 502 | 来自照明组 b 的 −X 级次，以及照明组 a 的 +Y 级次 |
| 504 | a₀ 零阶 |
| 506 | 来自 b 的 +X 级次，以及来自 a 的 −Y 级次 |
| 508 | b₀ 零阶 |

此通道映射仅对应专利示例，不保证所有 ASML iDBO / YieldStar 机型均采用该处方。

## 官方公开出处

- [US11385552B2：Figures 3–7](https://patents.google.com/patent/US11385552B2/en)
- [US11385552：Figure 3 光瞳与Wedge原图](https://patentimages.storage.googleapis.com/11/7b/75/b2534f4af01692/US11385552-20220712-D00003.png)
- [US11385552：Figure 4–5 四Pad与四圆原图](https://patentimages.storage.googleapis.com/88/f8/0e/b3d6332cee517a/US11385552-20220712-D00004.png)
- [WO2024002546A1：Figure 4 楔镜设计](https://patents.google.com/patent/WO2024002546A1/en)
- [ASML 官方YieldStar介绍](https://www.asml.com/en/technology/lithography-principles/measuring-accuracy)
- [ARCNL/VU/ASML：Intensity-only DBO (iDBO) 学术资料](https://cdn.fs.pathlms.com/oyswx0erShWFMcITDgeJ?cache=true&dl=true)

**声明**：HTML里的物镜焦距、图像比例、楔镜分像滑块、颜色、亮度和模拟K值均为教学示例；没有将未公开的仪器参数声称为真实数据。主体图像全部内嵌SVG，脱机可用；官方图纸通过需联网的链接打开。