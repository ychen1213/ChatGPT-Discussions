# 可独立检查的小型实际模型样例

这里的数组均从本轮正式保存的模型读取和裁取，未重新调用参考生成器。

- `central_stripe_triangles.npz`：中央条纹的完整闭合三角表面，Z = −2000～2000 nm；`vertices_nm` 为 XYZ 顶点，`faces` 为零起始三角连接；底部相邻衬底，其他自由面相邻空气。模型保留实际存储的三角形和朝向。
- `central_stripe_splines.npz`：同一中央条纹的实际三次 B 样条系数，c0～c5 为六个截面分区，u0～u5 / z0～z5 为各自结点向量。系数轴为条纹、Z、u、XY。均为原始源数据的切片。
- `central_stripe_voxels.npz`：5 nm 标签体的局部矩形裁片，数组轴顺序 Z,Y,X。原点为第一个体素的左下近侧角，中心位置是 origin+(index+0.5)×spacing。0/1/2 分别为空气/条纹/衬底。
- `sample_manifest.json`：单位、来源文件哈希、坐标和尺寸。

用项目已安装的 Python 运行 `samples/inspect_samples.py` 可重新读取并打印实际数组信息。无需重新生成大模型。查看完整交互模型请双击项目根目录的 `启动3D查看器.bat`。
