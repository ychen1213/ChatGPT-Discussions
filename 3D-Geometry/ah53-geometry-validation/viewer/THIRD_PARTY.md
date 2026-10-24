# 本地显示依赖

Three.js 0.160.1 与该版本的 OrbitControls 已完整放入 `vendor/`，使用 MIT 许可证，许可证见 `vendor/THREE-LICENSE.txt`。仅开发时下载，运行时不访问 CDN，也不需要 Node.js。

- 上游：https://github.com/mrdoob/three.js/tree/r160
- 安装说明：https://threejs.org/manual/pages/installation.html
- 页面通过项目 Python 的本地 HTTP 服务加载 ES modules。双击 `index.html` 不作为受支持入口。

模型查询依赖项目 Python 环境中的 NumPy / SciPy，版本记录于根目录 `requirements.txt`。
