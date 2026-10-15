---
name: cuda-doctor
description: Diagnose and fix PyTorch/CUDA problems — torch.cuda.is_available() returning False, CPU-only torch installed by accident, driver/CUDA version mismatches, GPU not detected. Use when the GPU is not recognized by PyTorch, when installing torch for a machine with an NVIDIA GPU, or when a deep learning setup fails to use the GPU.
---

# cuda-doctor — GPU / CUDA 专科

处理一切 "torch 不认识我的显卡" 问题。核心方法论：**分层排查——驱动 → 驱动能力上限 → torch 编译版本 → 匹配关系。四层里哪层断，就是哪层的问题。**

## 分诊：先拍一张 X 光片

```bash
nvidia-smi
python -c "import torch; print('torch', torch.__version__); print('compiled cuda', torch.version.cuda); print('available', torch.cuda.is_available())"
```

读懂结果：

- `nvidia-smi` 右上角的 `CUDA Version: 12.4` = **驱动支持的最高版本**（能力上限），不是你装的 CUDA
- `torch.version.cuda` = **torch 编译时使用的 CUDA 版本**（如 `12.1`）
- `torch.version.cuda` 为 `None` 或版本号带 `+cpu` = **装的是 CPU-only 版本**
- 可用性条件：`nvidia-smi` 的正常值 ≥ `torch.version.cuda`，且 torch 不是 CPU 版

## 决策树

```
torch.cuda.is_available() == False
├── 1. import torch 本身失败？
│      → 转交 import-doctor
├── 2. torch.version.cuda 是 None / 版本号带 +cpu？
│      → 根因：装了 CPU-only 版（Windows 上 pip 默认源常见）
│      → 修复：重装 GPU 版（见下方"安装 GPU 版 torch"）
├── 3. nvidia-smi 命令不存在或报错？
│      ├── 机器根本没有 NVIDIA 显卡 → 无解，向用户解释清楚（别修了）
│      ├── 有显卡但没装驱动 → 去 NVIDIA 官网装对应型号驱动
│      └── WSL2 里没输出 → 检查 Windows 侧是否装了驱动（WSL 内不需要装驱动，
│          需要 Windows 主机装好 NVIDIA 驱动并经 WSL 透传）
├── 4. nvidia-smi 正常，对比两个版本号：
│      ├── 驱动上限 < torch.version.cuda → 根因：驱动太旧
│      │     修复 A（推荐）：更新 NVIDIA 驱动至支持该 CUDA 版本
│      │     修复 B：改装与旧驱动匹配的低 CUDA 版 torch
│      └── 驱动上限 ≥ torch.version.cuda → 继续查
├── 5. 是否有环境变量屏蔽？
│      CUDA_VISIBLE_DEVICES 被设为空字符串 / "-1" 
│      → 取消该变量后重试
└── 6. 全部正常但依然 False？
       ├── 笔记本双显卡：独显被电源管理禁用？检查 NVIDIA 控制面板
       ├── 容器/远程环境：宿主无 GPU 或未做设备映射
       └── 打印 torch.cuda.device_count() 与 torch.cuda.is_available() 
           对照，进入深度排查（运行 diagnose.py --deep）
```

## 安装 GPU 版 torch（关键操作）

**铁律：不要去背版本号。去 pytorch.org 的 Get Started 页面，选好你的组合（OS + pip + CUDA 版本），直接复制官方命令。**

原因：torch/CUDA/驱动三者版本矩阵每个月都在变，记忆中的组合大概率已过期——这正是很多教程害人的地方。

标准操作（以 CUDA 12.x 为例，实际以官网为准）：

```bash
# 1. 先卸掉旧版（含 CPU 版残留）
python -m pip uninstall -y torch torchvision torchaudio

# 2. 用官方 index 重装（命令从 pytorch.org 复制）
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

# 3. 验证
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

中国大陆网络提示：`download.pytorch.org` 直连可能超时。备选：清华镜像站有 torch 的 wheel 镜像（`https://mirrors.tuna.tsinghua.edu.cn/` 下的 pytorch-wheels 条目，具体路径以镜像站当前页面为准）；或者用离线的 `.whl` 文件本地安装。

## 三个最常见的误判

1. **"我装了 CUDA Toolkit，为什么不行？"**
   pip 安装的 torch 自带 CUDA runtime，**不需要**你在系统里单独装 CUDA Toolkit。系统 Toolkit 只在你要自己编译 CUDA 扩展时才需要。别为一个不需要的东西改环境。

2. **"conda 装了 cudatoolkit，为什么 nvidia-smi 还是旧的？"**
   conda 的 `cudatoolkit` 是环境内的 runtime 包，不改变系统驱动。驱动只能通过系统级安装更新。

3. **"以前能用，重装系统后不行了"**
   优先按决策树第 2 步查是否装成了 CPU 版——重装后从默认源 `pip install torch` 是最高频的翻车现场。

## 验证标准

修复后必须同时满足：

```bash
nvidia-smi                                  # 能正常输出显卡信息
python -c "import torch; assert torch.cuda.is_available(); print('GPU:', torch.cuda.get_device_name(0)); print('OK')"
```

两项都通过才算修复完成。若 `is_available()` 为 True 但分配张量报 out of memory / 无 kernel image，属于显存或更深层的运行时问题，超出本技能范围——如实告知用户，不要硬修。

## 输出要求

按 SKILL.md 第六步的固定格式输出诊断报告。"根因"必须指明断在哪一层（驱动层 / 驱动能力 / torch 编译版本 / 匹配关系 / 屏蔽变量），并附对应证据值（版本号对照）。
