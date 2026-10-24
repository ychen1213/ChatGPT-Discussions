"""Build the three-page management brief and the detailed offline reading copy.

This reads existing results only. Run --html in the experiment environment
(markdown), and --pdf in a document environment with reportlab and pypdf.
No reconstruction, evaluation, or saved experiment record is modified.
"""
from __future__ import annotations

import argparse
import base64
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import quote

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parent
REVIEW = ROOT / "review-20261024"
LEADER = "2026-10-24_Mark三种几何表示_领导摘要"
DETAIL = "2026-10-24_Mark三种几何表示_详细比较与结论"
ORIGINAL = "2026-10-24_真实不规则Mark三维几何表示调研报告.md"
REPO_URL = "https://github.com/ychen1213/ChatGPT-Discussions/blob/main/3D-Geometry/"


def source_data():
    summary = json.loads((PROJECT / "results/20261024_voxel_reconstruction/summary.json").read_text(encoding="utf-8"))
    rows = {x["profile"]: x for x in summary["main"] if x["case"] == "local_5nm"}
    p = [rows[x] for x in ["P_sigma0", "P_sigma05", "P_sigma1"]]
    t = rows["T_MC"]
    assert len(rows) == 4 and summary["build_count"] == 20
    return summary, rows, p, t


def pages():
    _, rows, ps, t = source_data()
    lo = min(x["p95_nm"] for x in ps)
    hi = max(x["p95_nm"] for x in ps)
    return [
        dict(
            title="Mark 三维几何表示比较",
            subtitle="对象：合成 AH53 条纹。比较边界细节、数据量与编辑能力",
            figure="01_representation.png",
            alt="同一示意形状的三种保存方式：材料体素、三角边界、B样条参数边界",
            takeaway="建议：规则条纹优先深化 P，复杂缺陷保留 T，原始体素保留溯源。",
            support="P 是截面放样的 B 样条曲面；T 是三角网格；V 是材料体素。P 与 T 都记录边界。",
            qualification="本轮 P 尚非完整 CAD 内核。图为表示原理示意，不是精度对照或实测形貌。",
            source="依据：原调研与两轮 AH53 合成实验；全部方法和来源见详细比较。",
        ),
        dict(
            title="同一体素输入下，P 与 T 的误差接近",
            subtitle="第二轮：仅输入 5 nm 材料体素，自行寻找轮廓；局部窗口为 16 × 4 μm",
            figure="02_measured_tradeoff.png",
            alt="5纳米体素重建的全部三档P与直接T：截面P95误差和几何文件大小",
            takeaway=f"P：{lo:.3f}-{hi:.3f} nm / {ps[0]['payload_mb']:.2f} MB；T：{t['p95_nm']:.3f} nm / {t['payload_mb']:.2f} MB。",
            support="P 以较少数据保持接近的截面精度。此处 T 未做网格简化，大小差距不能泛化。",
            qualification="P95：95% 的已评估边界距离不超过此值。第一轮输入与评分口径不同，不混排。",
            source="来源：合成体素重建记录；14 个 XY 截面，Y ≥ 10 nm；非三维最大误差，MB 为十进制。",
        ),
        dict(
            title="复杂缺陷决定适用边界",
            subtitle="第二轮的四类独立小型挑战：检查孔洞、连接关系和单格细节",
            figure="03_topology_challenges.png",
            alt="直条、贯通孔、中段连接桥、单格毛刺的实际输入与当前P和T结果",
            takeaway="当前 P 会漏掉单格毛刺，并拒绝孔洞与合并；T 保留了这些挑战特征。",
            support="下一步：验证实测局部、多材料薄层，并比较受误差约束的 T 简化与 P 拟合。",
            qualification="已做 48 × 48 μm 合成规模验证；真实全 Mark、完整多材料内核及光学精度尚未验证。",
            source="来源：挑战输入及保存模型评分。T 的格中心标签一致，不代表连续表面零误差。",
        ),
    ]


CSS = r"""
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:#152e43;background:#eef2f5;font:17px/1.8 'Microsoft YaHei','Segoe UI',sans-serif}a{color:#166a8a;text-underline-offset:3px}header{max-width:1120px;margin:auto;padding:22px 34px;display:flex;gap:24px;flex-wrap:wrap;font-size:14px}main{max-width:1120px;margin:auto}.page{background:#fff;margin:0 0 24px;padding:38px 44px 28px;border-top:5px solid #19384b;box-shadow:0 4px 22px #10283a0a}h1,h2{font-size:32px;line-height:1.4;margin:0 0 10px;font-weight:700}p{margin:10px 0}.sub{color:#536675;font-size:17px}.figure{margin:20px 0 14px}.figure img{display:block;width:100%;height:auto}.figure a{display:block}.takeaway{font-size:21px;line-height:1.65;font-weight:700;margin:18px 0 12px}.support{font-size:17px}.qualification{font-size:14px;color:#586b79}.source{display:flex;justify-content:space-between;gap:20px;margin-top:24px;border-top:1px solid #dae3e9;padding-top:12px;font-size:12px;color:#647683}.source a{color:inherit}footer{padding:4px 34px 28px;color:#607483;font-size:13px}.doc{background:#fff;max-width:1060px;margin:auto;padding:40px 50px 75px}.doc h1{font-size:32px}.doc h2{font-size:26px;margin:48px 0 16px;border-top:2px solid #dce7ed;padding-top:20px}.doc h3{font-size:21px;margin:28px 0 10px}.doc img{max-width:100%;height:auto;display:block;margin:22px auto}.doc table{display:block;width:100%;border-collapse:collapse;overflow:auto;font-size:15px;line-height:1.75;margin:20px 0}.doc th,.doc td{border:1px solid #d7e1e8;padding:10px 13px;min-width:90px;vertical-align:top}.doc th{background:#edf4f7;text-align:left}.doc tr:nth-child(even){background:#f9fbfc}.doc blockquote{border-left:4px solid #c96a26;margin:22px 0;padding:4px 20px;background:#fff8f2}.doc code{font:0.89em/1.65 Consolas,monospace;background:#edf2f5;padding:2px 5px;overflow-wrap:anywhere}.doc pre{padding:15px;overflow:auto;background:#edf2f5}.doc pre code{padding:0;overflow-wrap:normal}.doc li{margin:7px 0}.toc{background:#f1f6f8;padding:12px 20px;font-size:15px}.toc ul{padding-left:22px}.toc a{text-decoration:none}summary{cursor:pointer}.doc a{overflow-wrap:anywhere}
@media(max-width:760px){header{padding:16px 20px;gap:12px}.page{padding:24px 18px 20px;margin-bottom:16px}h1,h2{font-size:25px}.sub{font-size:15px}.takeaway{font-size:18px}.support{font-size:16px}.qualification{font-size:13px}.source{display:block;font-size:11px}.doc{padding:25px 18px 45px}.doc h1{font-size:26px}.doc h2{font-size:23px}.doc table{font-size:14px}.doc td,.doc th{padding:8px 10px}body{font-size:16px}}
@media print{@page{size:A4 landscape;margin:12mm}body{background:#fff}header,footer,.toc{display:none}main{max-width:none}.page{break-after:page;margin:0;border:0;box-shadow:none;padding:0}.page:last-child{break-after:auto}.page h1,.page h2{font-size:24pt}.figure{margin:8px 0}.figure img{max-height:107mm;object-fit:contain}.takeaway{font-size:14pt}.support{font-size:11pt}.qualification,.source{font-size:9pt}.source{margin-top:10px}.doc{padding:0;max-width:none}.doc h2{break-before:auto}.doc img,tr{break-inside:avoid}}
"""


def embedded_image(path):
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def executive_html():
    sections = []
    for i, p in enumerate(pages(), 1):
        tag = "h1" if i == 1 else "h2"
        fig = REVIEW / "figures" / p["figure"]
        sections.append(f'''<section class="page" id="page-{i}">
<{tag}>{escape(p['title'])}</{tag}><p class="sub">{escape(p['subtitle'])}</p>
<figure class="figure"><a href="{quote('review-20261024/figures/'+p['figure'])}" target="_blank" aria-label="放大查看第{i}张图"><img src="{embedded_image(fig)}" alt="{escape(p['alt'])}"></a></figure>
<p class="takeaway">{escape(p['takeaway'])}</p><p class="support">{escape(p['support'])}</p>
<p class="qualification">{escape(p['qualification'])}</p>
<div class="source"><span>{escape(p['source'])}</span><span>2026-10-24 · {i}/3</span></div></section>''')
    header = f'<header><a href="{quote(LEADER)}.pdf">下载三页 PDF</a><a href="{quote(DETAIL)}.html">详细比较与结论</a><a href="{quote(ORIGINAL)}">修订后的调研报告</a></header>'
    body = header + '<main>' + '\n'.join(sections) + '</main><footer>三张图已嵌入本页，可离线阅读；点击图可打开仓库中的原图。结论适用于已验证的合成结构与具体实现。</footer>'
    (ROOT / (LEADER + '.html')).write_text(f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Mark 三维几何表示比较 · 领导摘要</title><style>{CSS}</style></head><body>{body}</body></html>', encoding='utf-8')


def executive_markdown():
    text = '# Mark 三维几何表示比较 领导摘要\n\n'
    text += f'[下载三页 PDF]({LEADER}.pdf) · [离线图文版]({LEADER}.html) · [详细比较与结论]({DETAIL}.md)\n\n'
    for p in pages():
        text += f"## {p['title']}\n\n{p['subtitle']}。\n\n![{p['alt']}](review-20261024/figures/{p['figure']})\n\n**{p['takeaway']}**\n\n{p['support']}\n\n{p['qualification']}\n\n"
    text += '来源：[第一轮已知轮廓与规模实验](ah53-geometry-validation/AH53_三种几何表示验证_技术验证报告.md)、[第二轮体素重建与挑战实验](ah53-geometry-validation/AH53_从体素重建P与T_检查与测试.md)。\n'
    (ROOT / (LEADER + '.md')).write_text(text, encoding='utf-8')


def detail_html():
    import markdown
    source = (ROOT / (DETAIL + '.md')).read_text(encoding='utf-8')
    # The detailed document uses plain-text formula blocks, so no external math runtime is needed.
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc', 'sane_lists'], extension_configs={'toc': {'toc_depth': '2-3'}})
    article = md.convert(source)
    # Embed only the three report figures; links to evidence remain relative and inspectable.
    def replace_image(m):
        value = m.group(1)
        path = ROOT / value
        if path.is_file() and path.suffix.lower() == '.png':
            return 'src="' + embedded_image(path) + '"'
        return m.group(0)
    article = re.sub(r'src="([^"]+)"', replace_image, article)
    header = f'<header><a href="{quote(LEADER)}.html">三页领导摘要</a><a href="{quote(LEADER)}.pdf">下载摘要 PDF</a><a href="{quote(ORIGINAL)}">修订后的原调研报告</a></header>'
    html = f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mark 三种几何表示 · 详细比较与结论</title><style>{CSS}</style></head><body>{header}<article class="doc"><details class="toc"><summary>展开目录</summary>{md.toc}</details>{article}</article></body></html>'
    (ROOT / (DETAIL + '.html')).write_text(html, encoding='utf-8')


def executive_pdf():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Paragraph
    from reportlab.pdfgen import canvas
    from pypdf import PdfReader

    pdfmetrics.registerFont(TTFont('YaHei', 'C:/Windows/Fonts/msyh.ttc', subfontIndex=0))
    pdfmetrics.registerFont(TTFont('YaHeiBold', 'C:/Windows/Fonts/msyhbd.ttc', subfontIndex=0))
    pdf = ROOT / (LEADER + '.pdf')
    width, height = landscape(A4)
    margin = 43
    content_width = width - 2 * margin
    c = canvas.Canvas(str(pdf), pagesize=(width, height), pageCompression=1, invariant=1)
    c.setTitle('Mark 三维几何表示比较 - 领导摘要')
    c.setAuthor('AH53 几何验证项目')
    c.setSubject('三页总结：V/T/P 原理、同体素重建结果、缺陷与方案建议')
    dark = '#152e43'
    muted = '#586b79'

    def paragraph(text, x, top, size, leading=None, bold=False, color=dark, box_width=content_width):
        style = ParagraphStyle('p', fontName='YaHeiBold' if bold else 'YaHei', fontSize=size,
                               leading=leading or size*1.5, textColor=colors.HexColor(color), wordWrap='CJK')
        obj = Paragraph(escape(text), style)
        _, used = obj.wrap(box_width, height)
        obj.drawOn(c, x, top-used)
        return used

    bounds = []
    for i, p in enumerate(pages(), 1):
        c.setFillColor(colors.HexColor(dark))
        c.rect(margin, height-31, 48, 4, fill=1, stroke=0)
        c.setFillColor(colors.HexColor(muted))
        c.setFont('YaHei', 10)
        c.drawRightString(width-margin, height-30, f'AH53  /  2026-10-24  /  {i:02d}')
        title_h = paragraph(p['title'], margin, height-47, 27, 37, True)
        sub_h = paragraph(p['subtitle'], margin, height-91, 12.2, 19, color=muted)
        image_y, image_h = 153, content_width * 7/16
        c.drawImage(ImageReader(str(REVIEW / 'figures' / p['figure'])), margin, image_y,
                    width=content_width, height=image_h, mask='auto', preserveAspectRatio=True, anchor='c')
        a = paragraph(p['takeaway'], margin, 150, 17.2, 25, True)
        b = paragraph(p['support'], margin, 115, 12.4, 19)
        d = paragraph(p['qualification'], margin, 85, 10.6, 16, color=muted)
        c.setStrokeColor(colors.HexColor('#d7e2e9'))
        c.setLineWidth(.6)
        c.line(margin, 44, width-margin, 44)
        paragraph(p['source'], margin, 36, 8.6, 12, color=muted, box_width=content_width-100)
        c.setFont('YaHei', 9)
        c.setFillColor(colors.HexColor('#166a8a'))
        c.drawRightString(width-margin, 24, f'完整比较与来源  |  {i}/3')
        c.linkURL(REPO_URL + quote(DETAIL+'.md'), (width-margin-110, 19, width-margin, 38), relative=0)
        bounds.append(dict(page=i, title_height=title_h, subtitle_height=sub_h,
                           takeaway_height=a, support_height=b, qualification_height=d))
        assert title_h <= 38 and sub_h <= 20 and a <= 26 and b <= 20 and d <= 33, bounds[-1]
        c.showPage()
    c.save()
    reader = PdfReader(pdf)
    assert len(reader.pages) == 3
    extracted = [p.extract_text() for p in reader.pages]
    for i, (p, text) in enumerate(zip(pages(), extracted), 1):
        assert p['title'].replace(' ', '') in text.replace(' ', '').replace('\n',''), (i, text)
        assert '\ufffd' not in text
    REVIEW.mkdir(parents=True, exist_ok=True)
    (REVIEW/'pdf_layout_checks.json').write_text(json.dumps({'pages':3, 'bounds':bounds,
        'text_extraction_ok':True, 'figures_per_page':1, 'font':'Microsoft YaHei embedded subset',
        'visual_review':'pending'}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'PDF: {pdf.name}, 3 pages, {pdf.stat().st_size:,} bytes')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--html', action='store_true')
    parser.add_argument('--pdf', action='store_true')
    args = parser.parse_args()
    if not (args.html or args.pdf):
        parser.error('choose --html and/or --pdf')
    if args.html:
        executive_html()
        executive_markdown()
        detail_html()
        print('Built executive HTML/Markdown and detailed HTML; figures embedded for offline reading.')
    if args.pdf:
        executive_pdf()


if __name__ == '__main__':
    main()
