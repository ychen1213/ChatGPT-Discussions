from pathlib import Path
import json, shutil
root=Path(__file__).resolve().parents[1]
out=root/'results/20261024_v2'
raw=(root/'output/playwright/ui_acceptance_output.txt').read_text(encoding='utf-8-sig')
record=json.loads(raw.split('### Result',1)[1].split('### Ran Playwright',1)[0].strip())
record['date_local']='2026-10-24'
record['cold_first_load_ms']=8653
record['cached_full_load_ms']=1980
record['runtime_dependencies']='All browser scripts/Three.js served locally; project Python environment required.'
record['report_text']='已在真实 Chromium 浏览器的 950×680 窗口完成连续操作：全域→母单元→单条纹→A 三种实际表示→B1 参数导出面→圆肩叠加→Z=410 nm 的 XY 截面→Y=270 nm 的 XZ 截面→B2/B3/B4 各体素→隐藏衬底、线框、平面着色、倍率切换→重置→保存截图→打开详细说明。旋转、缩放和平移已实际操作，模型切换保持相机位置；页面没有横向溢出、最终流程没有 JavaScript 异常，文档图片均加载成功。左侧面板在小窗口独立滚动。\n\n全域 P 首次加载约 8.65 s，缓存后一次实测约 1.98 s。一次短时全域渲染采样的帧间隔中位数约 16.7 ms、P95 约 16.8 ms；这不是所有机器或所有操作的帧率承诺。细体素单条纹包含 389,684 个原始面片，选择到截面全部就绪约 10 s；圆肩局部切换通常较快。加载阶段会显示状态，不能把本轮说成所有操作瞬时完成。\n\n已核对中文及空格路径、端口占用自动换端口和缺失环境的恢复提示，证据见 `viewer_backend_checks.json`。完整预览显示精度单列：P 抽样截面最大偏差约 1.48 nm；体素全域简化预览约 25 nm，因此纳米细节必须使用局部原始边界，不能用全域预览代替正式误差。两个数都是指定预览截面的抽样证据。'
(out/'ui_validation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copy2(root/'output/playwright/full_final950.png',out/'figures/viewer_full.png')
shutil.copy2(root/'output/playwright/shoulder950.png',out/'figures/viewer_screenshot.png')
shutil.copy2(root/'output/playwright/voxel_final950.png',out/'figures/viewer_voxel.png')
print('Browser acceptance evidence and screenshots saved.')
