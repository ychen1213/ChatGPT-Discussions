"""Build the offline P/T construction tutorial; do not modify geometry."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import json
import markdown

ROOT = Path(__file__).resolve().parents[1]
TITLE = 'AH53_P与T生成原理_从截面到三维'

def main():
    source=(ROOT/'docs/PT生成原理正文.md').read_text(encoding='utf-8')
    for i in range(1,5):
        files=sorted((ROOT/'docs/figures').glob(f'pt_{i:02d}*.png'))
        if len(files)!=1: raise ValueError(f'Expected one pt_{i:02d} figure, got {files}')
        src=files[0].relative_to(ROOT).as_posix()
        source=source.replace('{{FIG_'+str(i)+'}}',f'![原理图 {i}：从截面理解 P 与 T]({src})')
    if '{{FIG_' in source: raise ValueError('Unfilled figure marker')
    (ROOT/(TITLE+'.md')).write_text(source,encoding='utf-8')
    md=markdown.Markdown(extensions=['tables','fenced_code','toc','md_in_html'],extension_configs={'toc':{'toc_depth':'2-3'}})
    content=md.convert(source)
    css='''
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}body{margin:0;background:#f3f6f8;color:#24394b;font:18px/1.95 "Microsoft YaHei","Segoe UI",sans-serif}a{color:#006f76;text-underline-offset:3px}nav{position:fixed;inset:0 auto 0 0;width:280px;background:#eaf0f3;border-right:1px solid #d5e0e6;padding:24px 18px;overflow-y:auto;font-size:13px;line-height:1.65}nav strong{font-size:21px}nav ul{padding-left:18px}nav li{margin:8px 0}nav a{text-decoration:none}main{max-width:1280px;margin-left:280px;background:#fff;padding:40px 50px 80px;min-height:100vh}h1{font-size:34px;line-height:1.45;color:#164b59}h2{font-size:27px;line-height:1.55;color:#164b59;border-top:3px solid #d5e8e7;padding-top:25px;margin:60px 0 22px}h3{font-size:21px;line-height:1.6;color:#245362;margin:30px 0 12px}p{margin:16px 0}strong{color:#193e4b}li{margin:10px 0}.equation{font:21px/1.8 "Cambria Math",Georgia,serif;background:#edf7f4;border-left:4px solid #25877a;padding:16px 22px;margin:22px 0;overflow-x:auto;white-space:normal}blockquote{margin:24px 0;padding:14px 22px;background:#edf5f7;border-left:4px solid #4c8193}table{width:100%;display:block;overflow-x:auto;border-collapse:collapse;font-size:15px;line-height:1.75;margin:22px 0}td,th{padding:11px 13px;border:1px solid #d6e0e6;min-width:85px;vertical-align:top}th{background:#edf5f5;text-align:left}tr:nth-child(even){background:#f8fafb}img{max-width:100%;height:auto;display:block;margin:25px auto;border:1px solid #e3eaee;border-radius:5px}code{font: .86em/1.6 Consolas,monospace;background:#eef2f5;padding:2px 4px;border-radius:3px;overflow-wrap:anywhere}pre{background:#eef2f5;padding:18px;overflow:auto;line-height:1.6}pre code{padding:0;overflow-wrap:normal}.mobile-toc{display:none}.nav-links{margin:24px 0;line-height:2}.footer{font-size:14px;color:#617883;margin-top:40px}summary{cursor:pointer}
@media(max-width:1050px){nav{width:240px}main{margin-left:240px;padding:30px}}@media(max-width:760px){body{font-size:16px}nav{display:none}main{margin-left:0;padding:22px 18px;max-width:100%}h1{font-size:28px}h2{font-size:23px}h3{font-size:19px}.equation{font-size:18px;padding:12px 15px}.mobile-toc{display:block;background:#eaf0f3;padding:12px 18px;margin-bottom:24px;font-size:14px;line-height:1.7}.mobile-toc ul{padding-left:18px}table{font-size:14px}td,th{padding:9px}blockquote{padding:12px 15px}}@media print{nav,.mobile-toc{display:none}main{margin:0;padding:0;max-width:none}body{font-size:11pt;background:#fff}h2{break-before:page}img,tr{break-inside:avoid}a{color:inherit;text-decoration:none}}
'''
    html=f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>P 与 T 怎样生成：从截面到三维</title><style>{css}</style></head><body><nav aria-label="原理教程目录"><strong>P / T 生成原理</strong><div class="nav-links"><a href="docs/PT生成原理_动手演示.html">打开互动演示 ↗</a><br><a href="AH53_三种几何表示验证_详细说明.html">返回完整新手教程</a></div>{md.toc}</nav><main><details class="mobile-toc"><summary>展开原理教程目录</summary>{md.toc}</details>{content}<p class="footer">本页由 docs/PT生成原理正文.md 生成。新增图解不修改已保存的 AH53 模型。可离线阅读，图片需随项目目录保留。</p></main></body></html>'
    (ROOT/(TITLE+'.html')).write_text(html,encoding='utf-8')
    class Links(HTMLParser):
        def __init__(self): super().__init__();self.refs=[]
        def handle_starttag(self,tag,attrs):
            a=dict(attrs);url=a.get('src' if tag=='img' else 'href','')
            if tag in ('a','img') and url and not url.startswith(('#','https:','http:')): self.refs.append(url)
    p=Links();p.feed(html)
    missing=[v for v in p.refs if not (ROOT/unquote(urlsplit(v).path)).exists()]
    if missing: raise FileNotFoundError(missing)
    print(json.dumps({'characters':len(source),'image_count':html.count('<img '),'relative_links':len(p.refs),'missing':missing},ensure_ascii=True))

if __name__=='__main__': main()
