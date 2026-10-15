# cases — 真实排障案例库

每个案例记录一次完整的排障链路：症状 → 证据 → 根因 → 修复。按下面的格式提交。

## 提交格式

文件命名：`NNN-简短描述.md`（如 `001-pip-wrong-interpreter.md`）

````markdown
# 案例 NNN: <一句话标题>

- 来源: 实测 / 社区高频模式（脱敏）
- 平台: Windows 11 / macOS 14 / Ubuntu 24.04 / WSL2
- 现象: <报错原文第一行>
- 环境: Python 版本、安装方式、是否使用 venv

## 排查过程

1. <命令> → <输出要点>
2. ...

## 根因

<一句话 + 关键证据>

## 修复

<命令 + 验证命令>

## 防复发

<一句话>
````

## 案例列表

| 编号 | 标题 | 根因类型 |
|---|---|---|
| 001 | 裸 pip 命令与当前解释器错位 | 多环境错位 |
| 002 | torch 悄悄装成了 CPU 版 | GPU / CUDA |
| 003 | PyPI 直连超时（中国大陆） | 网络 / 镜像源 |
| 004 | PowerShell 拒绝执行 venv 激活脚本 | 虚拟环境 |
| 005 | 服务器 import cv2 报 libgomp 缺失 | 系统库 |
| 006 | numpy 大版本升级后 opencv/pandas 罢工 | 版本 / ABI |

---

## 案例 001: 裸 pip 命令与当前解释器错位

- 来源: 实测（env-icu 开发机，diagnose.py 自检时发现）
- 平台: Windows 11
- 现象: `pip install X` 显示安装成功，脚本仍报 `ModuleNotFoundError: No module named 'X'`
- 环境: 同一台机器上存在 8 个 Python 解释器（3.11 / 3.13 / 3.14 等多版本并存），未使用 venv

### 排查过程

1. `python -c "import sys; print(sys.executable)"` → 指向 3.14.3
2. `pip -V` → 指向 `Python311\Scripts\pip.EXE` ← 第一个关键证据：不是同一个环境
3. `python -m pip -V` → 3.14.3 自带 pip（与解释器一致）
4. `diagnose.py` 第 3 节列出 PATH 中全部 python/pip；第 9 节自动标记「裸 pip 命令错位」

### 根因

PATH 上 `pip` 命令先命中 Python 3.11 的 Scripts 目录，而 `python` 命令命中 3.14.3。
两条命令属于不同解释器——`pip install` 全部装进了运行时代码用不到的 3.11 里。

### 修复

统一改用 `python -m pip install X`（永远跟随当前解释器）：

```bash
python -m pip install X
python -c "import X; print(X.__version__)"    # 验证
```

### 防复发

只用 `python -m pip`，永远不用裸 `pip`；发现 import 异常先跑一遍 `diagnose.py`。

---

## 案例 002: torch 悄悄装成了 CPU 版

- 来源: 社区高频模式（脱敏）
- 平台: Windows
- 现象: `torch.cuda.is_available()` 返回 `False`；分配张量到 cuda 时报 `Torch not compiled with CUDA enabled`
- 环境: 有 NVIDIA 显卡 + 较新驱动，Python 3.11 venv

### 排查过程

1. `nvidia-smi` → 正常，驱动支持的最高 CUDA 版本 12.4
2. `python -c "import torch; print(torch.__version__, torch.version.cuda)"` → `2.x.x+cpu, None`
3. 证据齐全：驱动没问题，是 torch 本身不含 CUDA

### 根因

PyPI 默认源上的 Windows torch 是 CPU-only 版本。直接 `pip install torch` 拿不到 GPU 版。

### 修复

```bash
python -m pip uninstall -y torch torchvision torchaudio
# 命令从 pytorch.org 的 Get Started 页面复制（选好你的 CUDA 版本）
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
python -c "import torch; print(torch.cuda.is_available())"    # 验证 → True
```

### 防复发

装 torch 前先决定跑不跑 GPU；要 GPU 就去官网复制安装命令，**永远不要裸 pip install torch**。

---

## 案例 003: PyPI 直连超时（中国大陆）

- 来源: 实测（脱敏）
- 平台: Windows / 中国大陆家庭宽带
- 现象: `pip install X` 长时间无响应后 `Read timed out`（`socket.timeout`）
- 环境: 无代理，官方源直连

### 排查过程

1. 浏览器访问 pypi.org 同样超时 → 排除 pip 本身问题
2. `python -m pip install X -i https://pypi.tuna.tsinghua.edu.cn/simple` → 立即安装成功

### 根因

PyPI 官方源在当前网络下不可达（不是 pip 的问题，是网络路径的问题）。

### 修复

```bash
# 永久配置镜像源
python -m pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

备选源（主源故障时）：阿里云 `https://mirrors.aliyun.com/pypi/simple/`、腾讯云 `https://mirrors.cloud.tencent.com/pypi/simple/`。

### 防复发

新机器初始化的第一件事：配置 pip 镜像源。

---

## 案例 004: PowerShell 拒绝执行 venv 激活脚本

- 来源: 社区高频模式（脱敏）
- 平台: Windows 10 / 11
- 现象: `.\venv\Scripts\Activate.ps1` 报「无法加载文件……因为在此系统上禁止运行脚本」
- 环境: 全新 Windows 机器，Python 官网安装，venv 创建过程本身无报错

### 排查过程

1. `Get-ExecutionPolicy` → `Restricted`（PowerShell 的默认策略）
2. 确认 venv 本身完好：同一 venv 用 cmd 的 `activate.bat` 可以正常激活
3. 问题定位：不是环境坏了，是激活脚本的执行权限被拦

### 根因

PowerShell 的执行策略禁止运行 `.ps1` 脚本，与 venv 本身无关。看起来像环境问题，其实是权限问题。

### 修复

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

新开终端后重新激活。如果策略被组策略锁定（`Get-ExecutionPolicy -List` 里 MachinePolicy 一栏非空），这条命令会无效——改用 cmd 跑 `activate.bat`，不要和 IT 策略较劲。

### 防复发

Windows 新机初始化清单加上这一条：`Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`。

---

## 案例 005: 服务器上 import cv2 报 libgomp 缺失

- 来源: 社区高频模式（脱敏）
- 平台: Ubuntu 22.04 服务器（无桌面环境）
- 现象: `pip install opencv-python` 显示安装成功，`import cv2` 报 `ImportError: libgomp.so.1: cannot open shared object file: No such file or directory`
- 环境: 最小化安装的服务器，Python 3.10 venv

### 排查过程

1. `ldconfig -p | grep libgomp` → 系统里确实没有这个库
2. `python -m pip show opencv-python` → 包本身安装完好
3. 排除掉"包装坏了"的可能，缺口在系统层

### 根因

opencv 的预编译轮子依赖系统的 libgomp（GNU OpenMP 运行时），精简安装的服务器没有预置。

### 修复

```bash
sudo apt-get install libgomp1
python -c "import cv2; print(cv2.__version__)"    # 验证
```

没有 root 权限时改用 `opencv-python-headless`（专为无图形界面的服务器准备），或用 conda 安装。

### 防复发

服务器初始化脚本里一次性装齐常见运行时库：libgomp1、libgl1、libglib2.0-0。

---

## 案例 006: numpy 大版本升级后 opencv/pandas 集体罢工

- 来源: 社区高频模式（脱敏）
- 平台: macOS
- 现象: 某次 `pip install` 后（numpy 被依赖解析带动升到 2.x），opencv 报 `numpy.core.multiarray failed to import`，pandas 报同类错误
- 环境: Python 3.11 venv，数据科学常用包齐全

### 排查过程

1. `python -c "import numpy; print(numpy.__version__)"` → 2.1.0（升级前是 1.26）
2. `python -m pip show opencv-python` → 4.5.x，编译年代对应 numpy 1.x
3. 链条清晰：numpy 主版本跳变，旧轮子链接的 C 接口被移除

### 根因

numpy 从 1.x 升到 2.x，旧版 opencv / pandas 的 C 扩展编译时链接的 ABI 不再存在。

### 修复

```bash
python -m pip install --upgrade opencv-python pandas
python -c "import numpy, cv2, pandas; print('OK')"    # 验证
```

如果某个包确实没有适配 numpy 2.x 的版本，止损：`python -m pip install "numpy<2"`，并把约束写进 requirements.txt。

### 防复发

numpy 这类基石包写死版本；升级主版本后，依赖它的包成对升级、逐一验证。
