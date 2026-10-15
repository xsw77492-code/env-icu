---
name: venv-doctor
description: Diagnose and fix virtual environment problems — venv activation not taking effect, packages installed into the global interpreter, missing pip inside a venv, broken activation scripts (Windows PowerShell policy), venvs broken after being moved or renamed, IDE/Jupyter not using the venv. Use when it is unclear which interpreter is actually running, or when installs and imports disagree about where things live.
---

# venv-doctor — 虚拟环境专科

处理"到底哪个环境在生效"的问题。先跑这条命令：

```bash
python -c "import sys; print(sys.executable); print(sys.prefix)"
```

`sys.executable` 是现在跑代码的解释器，`sys.prefix` 是它的环境根。这两个输出跟你以为的对不上，问题就出在这里。

## 分诊

| 症状 | 去哪 |
|---|---|
| 激活了 venv，包还是装到全局 | A |
| pip 命令指向别处（裸 pip 与 python -m pip 不一致） | B |
| venv 里没有 pip | C |
| Windows PowerShell 激活脚本报错 | D |
| venv 移动 / 重命名 / 换电脑后失效 | E |
| IDE / Jupyter 不认 venv | F |

## A. 激活了 venv，包却装到全局

先验证"激活成功"这件事本身，别信终端提示符：

```bash
python -c "import sys; print(sys.prefix != sys.base_prefix)"
```

- 输出 `False` → venv 实际没生效。逐项检查：
  1. 激活命令是不是在当前终端执行的？新开的窗口不会继承
  2. shell 类型对不对？PowerShell 用 `Activate.ps1`，cmd 用 `activate.bat`，Git Bash 用 `source Scripts/activate`（混用会静默失败）
  3. 有没有激活了 A 环境、却在用 B 环境的绝对路径命令？
- 输出 `True` → venv 生效了，问题在 pip 命令本身 → 走 B

修复原则：激活之后，装包一律用 `python -m pip install X`，让 pip 永远跟着当前 python 走。

## B. pip 指向别处

```bash
python -m pip -V
```

输出里的站点包路径必须属于当前环境。对照方法：`python -m pip -V` 的路径应包含 `python -c "import sys; print(sys.prefix)"` 的输出。

不属于 → 用 `python -m pip` 重装目标包；然后跑一次 `diagnose.py` 第 3 节，看 PATH 里是不是有别的 pip 排在前面（这在多 Python 机器上是常态）。

## C. venv 里没有 pip

特征：`python -m pip` 报 `No module named pip`。

常见成因：创建时加了 `--without-pip`、创建过程被打断、或 venv 是从别处复制来的残缺副本。

修复顺序：

```bash
python -m ensurepip --upgrade     # 官方救援，首选
```

不行就重建（见 E 的重建流程）。网上常见的"下载 get-pip.py 到环境里执行"能用，但多引入一个来路不明的文件，没必要。

## D. Windows PowerShell 激活报错

特征：

```text
无法加载文件 ...\Activate.ps1，因为在此系统上禁止运行脚本
```

这不是 venv 坏了，是 PowerShell 执行策略拦的。修复：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

改完新开一个终端。两点注意：不要改 `LocalMachine` 范围（只影响自己就够了）；如果这台机器被组策略锁定了策略，这条命令会无效——那种情况用 cmd 跑 `activate.bat`，别去和 IT 策略对抗。

## E. venv 移动 / 重命名 / 换电脑后失效

根因很直接：venv 的路径是写死的。`pyvenv.cfg`、激活脚本、pip 入口脚本里全是绝对路径。挪个位置就全断了。

处理方式：**重建，不修。** Python 官方就不支持 venv 迁移，各种 `--relocatable` 偏方在新版本上的坑比收益多。

```bash
python -m pip freeze > requirements.txt    # 从旧环境尽力导出
python -m venv .venv-new
.venv-new/Scripts/activate                 # POSIX: source .venv-new/bin/activate
python -m pip install -r requirements.txt
```

导出失败（比如 pip 已经坏了）时，先修出 pip 再导，或者根据项目的 `pyproject.toml` / `requirements.txt` 直接重装。

## F. IDE / Jupyter 不认 venv

- VS Code：`Ctrl+Shift+P` → "Python: Select Interpreter" → 选 venv 里的 `python.exe`
- PyCharm：Settings → Project → Python Interpreter → Add → Existing
- Jupyter：`python -m ipykernel install --user --name=<venv名>` 注册内核，再在 notebook 里切换
- 验证方式统一：在目标环境里跑 `import sys; print(sys.executable)`，必须指向 venv

## 修还是重建？

venv 天生是一次性的，这条判断线很清楚：

- venv 损坏（C、E 类）→ 直接重建。重建 30 秒，考古可能 30 分钟
- 有装了很久、没记录过的包 → 先 `pip freeze` 抢救清单
- conda 环境 → `conda env export > environment.yml` 之后再重建

## 输出要求

按 SKILL.md 第六步的固定格式输出。报告里必须写清三件事：哪个解释器在生效（`sys.executable` 的实际值）、包被装进了哪里、后续建议用什么命令（一律写成 `python -m pip ...` 形式）。
