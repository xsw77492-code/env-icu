---
name: import-doctor
description: Diagnose and fix Python import failures — ModuleNotFoundError, ImportError, "I installed it but Python can't find it". Use when code fails at import time, when a package seems missing despite being installed, or when imports resolve to the wrong file/environment.
---

# import-doctor — 导入问题专科

处理一切 `ModuleNotFoundError` / `ImportError`。核心方法论：**报错分两类——"没装对地方"和"装对了但解释器不对"。九成的"装了却找不到"属于后者。**

## 分诊：先确认三件事

1. 报错原文是哪一种？
   - `ModuleNotFoundError: No module named 'X'` → 走 A 组
   - `ImportError: cannot import name 'X' from 'Y'` → 走 B 组
   - `ImportError: attempted relative import...` → 走 C 组
   - `ImportError: DLL load failed while importing X` → 转交 `native` 类问题（系统库缺失，先用 `diagnose.py` 看 PATH 与位数）
   - `ImportError: numpy.core.multiarray failed to import` 等 "X.core failed" → 版本冲突，检查 numpy 依赖链
2. 运行代码的解释器是谁？**必问**：`python -c "import sys; print(sys.executable)"`
3. 装包用的 pip 是谁？**必问**：`python -m pip -V`（注意：是 `python -m pip`，不是裸 `pip`）

第 2、3 条的路径如果不一致，根因基本就锁定了：**包装进了另一个环境**。

## A 组：No module named 'X'

按顺序执行，遇到命中即停：

### A1. X 是"导入名 ≠ 包名"的别名吗？

`pip install` 报 `No matching distribution found for X` 时，几乎可以确定是别名问题。常见对照：

| import 名 | pip 安装名 |
|---|---|
| `cv2` | `opencv-python` |
| `PIL` | `Pillow` |
| `sklearn` | `scikit-learn` |
| `yaml` | `PyYAML` |
| `bs4` | `beautifulsoup4` |
| `dateutil` | `python-dateutil` |
| `dotenv` | `python-dotenv` |
| `serial` | `pyserial` |
| `Crypto` | `pycryptodome` |
| `win32gui` 等 `win32*` | `pywin32` |
| `fitz` | `PyMuPDF` |

不确定时，用元数据反查：

```bash
python -m pip index versions <候选包名>     # 验证包真实存在
```

### A2. "明明装了"——三查错位

**查一：pip 与解释器是否属于同一环境**

```bash
python -m pip -V        # 输出形如: pip 23.x from ...\site-packages\pip (python 3.11)
python -c "import sys; print(sys.executable)"
```

对比两个路径所属的解释器。不一致 → **根因：包装到了另一个环境**。

修复（用运行代码的那个解释器来装）：

```bash
python -m pip install <包名>
```

**查二：系统里是否只有一个 Python？**

运行 `diagnose.py`，看 "Python on PATH" 一节。Windows 常见三坑：

- `python` 命令解析到 `WindowsApps\python.exe`（微软商店 0 字节占位符，可能直接打开商店）
- `py` launcher 指向的版本与当前运行的版本不同（`py -0` 列出全部）
- 官网版、conda 版、IDE 内置版并存

修复：明确指定解释器绝对路径，或用 `py -3.11` / 激活正确环境后再装。

**查三：IDE / Notebook 用的是哪个解释器？**

- VS Code / PyCharm：右下角/设置里的解释器选择器
- Jupyter：在 notebook 里跑 `import sys; print(sys.executable)`，与终端对比；不一致 → 换 kernel

修复：把 IDE 解释器切到"已经装了包的那个"，或往 IDE 用的解释器里补装。

### A3. sys.path 污染与遮蔽

检查包是否被"错误的同名文件"顶掉了：

```bash
python -c "import X; print(X.__file__)"
```

- 指向你的项目目录 → **同名文件遮蔽**（脚本目录里有 `random.py`、`json.py`、`email.py`、`typing.py` 等与标准库/库重名的文件）。修复：重命名本地文件，删掉残留 `__pycache__`。
- 检查 `PYTHONPATH`：非空且指向不相关目录时，先临时 `unset PYTHONPATH` 重试，确认后再清理来源。

### A4. 环境彻底乱了

如果 A2 三查都正常仍找不到，且环境装过很多互相覆盖的包：**不要修，直接重建**。

```bash
python -m venv .venv-new
.venv-new/Scripts/activate     # Windows；POSIX: source .venv-new/bin/activate
python -m pip install -r requirements.txt
```

在烂环境里考古的时间成本，几乎总是高于重建。

## B 组：cannot import name 'X' from 'Y'

包存在，但 `Y` 里没有 `X` 这个名字。两个主因：

### B1. 循环导入（circular import）

特征：报错堆栈里能看到 `A → B → A` 的往复；或两个模块互相 `from ... import ...`。

修复（按优先级）：
1. 把 `import` 从模块顶层挪进函数内部（延迟导入）
2. 抽公共依赖到第三个模块
3. 只在 `TYPE_CHECKING` 分支里导入（仅类型标注场景）

### B2. 版本不匹配（名字在别的版本里）

特征：报错提到知名库的核心类，如 `from pydantic import BaseSettings`。

```bash
python -m pip show <Y>          # 看当前版本
```

对照官方 changelog 确认该名字在哪个版本被移除/改名（**必须核实，不许凭记忆断言**）。

修复：要么按新版 API 改代码，要么把库锁回兼容版本（注意连带依赖，用 `pip install "Y==<版本>"` 并在安全协议下操作）。

## C 组：attempted relative import with no known parent package

根因：用 `python script.py` 直接运行了一个使用相对导入（`from . import ...`）的模块。

修复（二选一）：

```bash
python -m package.module        # 推荐：以模块方式运行
```

或把相对导入改为绝对导入（视项目结构而定）。

## 输出要求

按 SKILL.md 第六步的固定格式输出诊断报告。其中"根因"必须是带回溯证据的一句话，例如：

> 根因：pip（属 C:\Python314）与运行解释器（.venv 的 3.11）错位，requests 装进了未被使用的环境。

不允许输出"可能是环境问题，建议重装"这类无证据结论。
