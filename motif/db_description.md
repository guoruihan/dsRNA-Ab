📄 PDB 本地数据存储格式规范（中文）
1. 数据概述

本数据集是 Protein Data Bank (PDB) 的本地镜像，包含了所有已公开的生物大分子三维结构数据。

文件格式：PDBx/mmCIF（.cif.gz）

内容包括：

蛋白质

RNA / DNA

蛋白–核酸复合物

配体 / 金属离子

👉 当前 PDB 标准格式为 mmCIF，自 2014 年起成为官方主格式

2. 根目录结构
/datapool/data2/home/ruihan/data/PDB_sync

目录结构如下：

PDB_sync/
├── 00/
├── 01/
├── 02/
├── ...
├── aa/
├── ab/
├── ac/
...
├── zz/
3. 分目录规则（核心）

PDB 使用一种 分片（sharding）存储方式：

每个子目录名称 = PDB ID 的第 2 和第 3 个字符

示例
PDB ID	所在目录
1abc	ab
2xyz	xy
8aaf	aa
4. 文件命名规则

每个结构对应一个文件：

<PDB_ID>.cif.gz

例如：

aa/
├── 1aaf.cif.gz
├── 2aag.cif.gz
5. 文件格式说明（mmCIF）

每个 .cif.gz 文件是一个 结构化文本文件，包含：

✔️ 原子级结构信息

原子坐标 (x, y, z)

原子类型

residue（残基）信息

✔️ 分子组成

蛋白（protein）

RNA / DNA（核酸）

配体 / 金属

✔️ 元数据

实验方法（X-ray / Cryo-EM / NMR）

分辨率

链（chain）信息

⚠️ 格式特点（重要）

mmCIF 是：

key-value + 表格结构的数据格式

例如：

_entity.id
_atom_site.Cartn_x

👉 相比旧 PDB 格式：

没有列宽限制

支持更大结构


6. 数据特点
✔️ 覆盖范围

全量 PDB（~20万+结构）

包含：

单蛋白结构

RNA 结构

蛋白–RNA复合物

✔️ 存储优势

gzip 压缩（节省空间）

分目录存储（避免单目录过大）

与官方 wwPDB 完全一致

7. 数据访问方式（代码层面）

给定一个 PDB ID：

pdb_id = "1abc"
folder = pdb_id[1:3]   # "ab"
path = f"{ROOT}/{folder}/{pdb_id}.cif.gz"
8. 示例
/datapool/data2/home/ruihan/data/PDB_sync/aa/1aaf.cif.gz

PDB ID：1aaf

所在目录：aa

文件：1aaf.cif.gz

9. 与你任务的关系（重点）

这个数据结构非常适合你现在要做的事情：

✔️ 可以直接支持：
① RNA 检测

residue name = A / U / G / C

② dsRNA 判断

通过几何关系（双链结构）

③ protein–RNA binding

距离 / 接触分析

10. 推荐处理流程（给你 pipeline 思路）
PDB_sync
   ↓
解析 mmCIF
   ↓
检测 RNA 链
   ↓
判断是否为双链 RNA
   ↓
检测蛋白是否接触 RNA
11. 设计优势总结

✅ 官方标准格式（mmCIF）

✅ 支持大规模并行处理

✅ 可直接构建 benchmark dataset

✅ 无需额外下载或转换