"""Assemble the offline beginner guide without altering saved model data."""
from pathlib import Path
import re
import markdown

ROOT = Path(__file__).resolve().parents[1]
TITLE = 'AH53_三种几何表示验证_详细说明'

def main():
    body = (ROOT / 'docs/新手教程正文.md').read_text(encoding='utf-8')
    concepts = (ROOT / 'docs/概念图说明.md').read_text(encoding='utf-8')
    concepts = concepts.replace('](figures/', '](docs/figures/')
    sections = re.split(r'(?=^### 新手图)', concepts, flags=re.M)
    sections = [part for part in sections if part.startswith('### 新手图')]
    if len(sections) != 4: raise ValueError('Expected four concept figure sections')
    for i, section in enumerate(sections, 1):
        body = body.replace(f'<!-- CONCEPT_{i} -->', section.strip())
    body += '\n\n---\n\n' + (ROOT / 'docs/新手逐图讲解.md').read_text(encoding='utf-8')
    files = (ROOT / 'docs/文件与模型指南.md').read_text(encoding='utf-8')
    files = re.sub(r'^(#{1,5}) ', r'\1# ', files, flags=re.M)
    body += '\n\n---\n\n' + files
    # Component headings must not create multiple document titles.
    lines=body.splitlines()
    body='\n'.join(('## '+line[2:]) if i and line.startswith('# ') else line for i,line in enumerate(lines))+'\n'
    (ROOT / (TITLE + '.md')).write_text(body, encoding='utf-8')
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc', 'attr_list', 'md_in_html'], extension_configs={'toc': {'toc_depth': '2-3'}})
    article = md.convert(body)
    css = '''
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:30px}body{margin:0;background:#f4f6f8;color:#213146;font:17px/1.95 "Microsoft YaHei","Segoe UI",sans-serif}a{color:#006d73;text-underline-offset:3px}a:hover{color:#00494d}nav{position:fixed;inset:0 auto 0 0;width:285px;background:#e9eff3;padding:24px 18px;overflow-y:auto;font-size:13px;line-height:1.65;border-right:1px solid #d5dee5}nav strong{font-size:19px;display:block;margin-bottom:12px}nav ul{padding-left:18px}nav>div>ul{padding-left:18px}nav li{margin:7px 0}nav a{text-decoration:none}main{margin:0 0 0 285px;max-width:1180px;padding:45px 55px 90px;background:#fff;min-height:100vh}h1{font-size:34px;line-height:1.45;letter-spacing:-.5px;margin:0 0 25px;color:#123f50}h2{font-size:27px;line-height:1.5;margin:64px 0 22px;border-top:3px solid #d5e8e7;padding-top:25px;color:#154b52}h3{font-size:21px;line-height:1.6;margin:30px 0 12px;color:#245161}p{margin:14px 0}img{max-width:100%;height:auto;display:block;margin:22px auto;border:1px solid #e2e7eb;border-radius:6px}table{width:100%;display:block;overflow-x:auto;border-collapse:collapse;font-size:15px;line-height:1.75;margin:22px 0}td,th{padding:12px 14px;border:1px solid #d9e2e9;min-width:90px;vertical-align:top}th{background:#edf5f5;text-align:left}tr:nth-child(even){background:#f8fafb}blockquote{margin:24px 0;background:#edf7f4;border-left:5px solid #338779;padding:14px 22px}blockquote p{margin:8px 0}code{font-family:Consolas,monospace;font-size:.88em;background:#edf1f4;padding:2px 4px;border-radius:3px;overflow-wrap:anywhere}pre{padding:18px;background:#edf1f4;overflow:auto;line-height:1.6}pre code{padding:0;overflow-wrap:normal}li{margin:9px 0}hr{border:0;border-top:1px solid #d9e2e9;margin:60px 0}.stamp{font-size:13px;color:#536e78;margin-top:24px}.mobile-toc{display:none}summary{cursor:pointer}strong{color:#183e4b}
@media(max-width:1050px){nav{width:240px}main{margin-left:240px;padding:32px 28px}}@media(max-width:760px){body{font-size:16px}nav{display:none}main{margin:0;padding:25px 18px;max-width:100%}h1{font-size:27px}h2{font-size:23px;margin-top:42px}.mobile-toc{display:block;background:#e9eff3;padding:12px 18px;margin-bottom:26px;font-size:14px}.mobile-toc ul{padding-left:18px}blockquote{padding:12px 15px}table{font-size:14px}td,th{padding:9px 10px}}@media print{nav,.mobile-toc{display:none}main{margin:0;padding:0;max-width:none}body{background:#fff;font-size:11pt}h2{break-before:page}img,tr{break-inside:avoid}a{color:#213146;text-decoration:none}}
'''
    html = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AH53 从零开始：目的、原理、逐图讲解与模型文件</title><style>{css}</style></head><body><nav aria-label="教程目录"><strong>AH53 · 新手教程</strong>{md.toc}<p class="stamp">本页可离线阅读<br>模型运行：20261024_v2</p><a href="文件用途索引.html">查找文件用途 ↗</a></nav><main><details class="mobile-toc"><summary>展开教程目录</summary>{md.toc}</details>{article}</main></body></html>'''
    (ROOT / (TITLE + '.html')).write_text(html, encoding='utf-8')
    imgs=re.findall(r'<img[^>]+src="([^"]+)"', html)
    missing=[s for s in imgs if not (ROOT/s).exists()]
    if missing: raise FileNotFoundError(missing)
    print(f'Beginner guide: {len(body):,} characters, {len(imgs)} image references, all present.')

if __name__ == '__main__': main()
