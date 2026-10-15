# 报错原文决策树 (Import 类)

本文件按**报错原文**组织——复制报错的第一行，在索引里定位，按决策树走。

配套使用：`scripts/diagnose.py`（拍片）→ 本文（读片）→ `references/safety-protocol.md`（动手前闸门）。

## 索引

| 报错原文（节选） | 跳转 |
|---|---|
| `ModuleNotFoundError: No module named 'X'` | [A](#a-modulenotfounderror-no-module-named-x) |
| `ImportError: cannot import name 'x' from 'y'` | [B](#b-importerror-cannot-import-name-x-from-y) |
| `ImportError: DLL load failed while importing X` | [C](#c-importerror-dll-load-failed-while-importing-xwindows-专属) |
| `ImportError: numpy.core.multiarray failed to import` | [D](#d-importerror-numpycoremultiarray-failed-to-import) |
| `ModuleNotFoundError: No module named 'pip'` | [E](#e-modulenotfounderror-no-module-named-pip) |

---

## A. ModuleNotFoundError: No module named 'X'

最高频，占 import 问题约 80%。

### 决策树

**Q1. X 是"导入名 ≠ 包名"的别名吗？**

- 判断：`pip install X` 报 `No matching distribution found for X` → 几乎确定
- 完整别名对照表见 `skills/import-doctor/SKILL.md` 的 A1 一节
- 修复：`python -m pip install <正确包名>`

**Q2. "我确实装了"——三查错位（最高频根因）**

查一（概率最高）：**pip 和解释器是不是同一环境？**

```bash
python -c "import sys; print(sys.executable)"
python -m pip -V
```

两条输出里的环境路径不一致 → **根因：包装到了另一个环境**

```bash
# 修复：
python -m pip install X
```

查二：**机器上有几个 Python？**

```bash
python scripts/diagnose.py    # 第 3 节列出 PATH 中全部 python/pip
```

Windows 三坑：WindowsApps 占位符（0 字节，可能弹商店）、`py` launcher 指向不同版本（`py -0` 查看）、conda/官网版/IDE 内置版并存。

修复：用解释器绝对路径，或 `py -3.11` 明确指定。

查三：**IDE / Notebook 用的哪个解释器？**

Jupyter 里运行 `import sys; print(sys.executable)`，与终端对比。不一致 → 换 kernel / 换 IDE 解释器设置。

**Q3. 环境干净但仍失败？→ sys.path 遮断**

```bash
python -c "import X; print(X.__file__)"
```

- 指向项目本地目录 → **同名文件遮蔽**（项目里有 `random.py`、`json.py`、`email.py`、`typing.py` 等重名文件）。修复：重命名本地文件 + 清理 `__pycache__`。
- 检查 `PYTHONPATH` 是否指向奇怪目录 → 临时清空对照。

**Q4. 全部排查完依然失败 → 重建环境**（流程见 `safety-protocol.md` 第五节）。

---

## B. ImportError: cannot import name 'x' from 'y'

包存在，但 `y` 里没有 `x` 这个名字。两类根因：

### B1. 循环导入（circular import）

- 特征：报错堆栈里出现 `A → B → A` 的往复
- 修复（按优先级）：把 import 挪进函数内部（延迟导入）→ 抽公共依赖到第三个模块 → 仅类型标注场景用 `TYPE_CHECKING`

### B2. 版本不匹配（名字在别的版本里）

```bash
python -m pip show y     # 当前版本
```

核实该名字在哪个版本被移除/改名（查官方 changelog 或 `pip index versions y`，**不许凭记忆断言**）。

修复：升级代码用新 API，或把库锁回兼容版本（注意连带依赖）。

---

## C. ImportError: DLL load failed while importing X（Windows 专属）

### C1. 位数不匹配

32 位 Python 装了 64 位轮子（或反之）。

```bash
python -c "import sys; print('64-bit' if sys.maxsize > 2**32 else '32-bit')"
```

修复：装与解释器位数一致的包版本。

### C2. VC++ 运行库缺失

- 特征：`DLL load failed` 或 `0xc000007b`
- 高发于：`pywin32`、`lxml`、PyQt 等带 C 扩展的包
- 修复：安装 Microsoft Visual C++ Redistributable（注意年份与架构对应）

### C3. 依赖的系统 DLL 缺失

完整报错里通常点名具体 DLL（如 `c10.dll`、`libgomp`）。修复：重装该包；用依赖查看工具定位 DLL 来源。

---

## D. ImportError: numpy.core.multiarray failed to import

**根因模式**：某个包（常见 opencv-python、旧版 pandas/matplotlib）是针对旧版 numpy 编译的，而环境里的 numpy 已跨大版本升级（1.x → 2.x 典型）。

修复优先级：

1. **升级报错的包**到支持当前 numpy 的版本（首选）
2. 检查冲突链：`python -m pip show <相关包>`、`python -m pip check`
3. 回退 numpy 大版本（下策，注意连带依赖）

验证：

```bash
python -c "import numpy; import <肇事包>; print('OK')"
```

---

## E. ModuleNotFoundError: No module named 'pip'

pip 自身缺失或损坏：

```bash
python -m ensurepip --upgrade
```

若 `ensurepip` 也不可用：

- conda 环境：`conda install pip`
- 其它：重建 venv（`python -m venv .venv`）

---

## 附：修复后的三段验证（通用）

1. **能导入**：`python -c "import X; print(X.__version__)"`
2. **在对的环境**：`python -c "import X, sys; print(X.__file__); print(sys.executable)"`
3. **功能级**：重新运行用户最初失败的那条命令

三段全过才算修复完成。
