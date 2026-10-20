# vendor/ — 本目录故意留空

本轮的第三方依赖不是重新下载安装的，而是从既有研究目录**逐字节复制**的冻结副本，
放在保持原始相对布局的位置，这样 `portable_frozen.py` 与 PPCPP 候选的 manifest 校验
不需要改动就能工作：

```
sources/reference_tree/研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/.deps/
    numpy      2.5.4
    pyscipopt  6.2.1
    glns       0.1.0   （作者维护的 C++ 版 GLNS python 扩展，OARP_CORE2 的 GTSP 后端）
```

哈希见 `manifests/source_copy_sha256.json`，版本核对见 `manifests/method_matrix.csv`。

## 没有放进来的东西

- **LKH**：许可为"仅学术/非商业使用，作者保留全部权利"，
  且执行稿 §8 明确本轮不下载编译巨量依赖。规格见 `specs/LKH_spec.md`，
  下一轮按该文件 §7 的顺序获取并记录 URL/字节数/SHA256/构建命令。
- 任何 pip 安装物、任何全局环境改动。

本交付自身的代码只依赖 Python 标准库。
