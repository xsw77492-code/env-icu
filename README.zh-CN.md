# env-icu

**重装系统之前的最后一站。**

一个 Agent 技能包，把任何编码 Agent 变成 Python 环境排障医生——先取证、再修复，绝不把环境修得更坏。

**简体中文** | [English](README.md)

---

## 问题

Python 环境坏掉的时候，你的编码 Agent 通常会把事情弄得更糟：

- 对一切执行 `pip install --upgrade`，指望撞对一个
- 幻觉出根本不存在的版本号和包名
- `sudo pip install` 直接把系统 Python 搞坏
- 从 2019 年的 GitHub issue 里抄来一段建议，而那个库版本你根本没有

根因是：**Agent 在猜，而不是在诊断。** env-icu 给它的是一套纪律：

> 先取证，再下诊断，最后才修复。绝不让环境更糟。

## 安装（30 秒）

```bash
git clone https://github.com/你的用户名/env-icu.git

# Claude Code（个人技能目录）——其它 Agent 请替换为对应目录
cp -r env-icu ~/.claude/skills/env-icu
```

兼容任何支持 `SKILL.md` / Agent Skills 标准的 Agent：Claude Code、Codex、Cursor、OpenClaw、DeepSeek Harness 等。把仓库指向 Agent，或放入它的技能目录即可。

## 快速演示

```text
用户：我明明装了 requests，脚本却一直报：
     ModuleNotFoundError: No module named 'requests'

Agent：（加载 env-icu，先运行 scripts/diagnose.py）

     体检结论：
       - pip 属于  C:\Python314\python.exe
       - 而脚本运行在  .venv\Scripts\python.exe（3.11）
     这是两个不同的环境，包装到了你没在用的解释器里。

     修复：  python -m pip install requests
     验证：  python -c "import requests; print(requests.__version__)"
```

不靠猜。Agent 先测量了环境，然后修的是真正的问题。

## 里面有什么

| 技能 | 处理的症状 | 状态 |
|---|---|---|
| `import-doctor` | `ModuleNotFoundError`、`ImportError`、"装了但找不到" | 可用 |
| `cuda-doctor` | `torch.cuda.is_available()` 返回 `False`、CUDA 驱动/版本不匹配 | 可用 |
| `pip-doctor` | 安装失败：网络/镜像源、权限、缺少预编译包、依赖冲突 | 可用 |
| `venv-doctor` | 虚拟环境未激活、`pip` 装进了全局解释器 | 计划中 |
| `native-doctor` | `DLL load failed`、`libgomp`、`GLIBC` 缺失等系统库问题 | 计划中 |
| `conflict-doctor` | numpy / pydantic 等版本冲突、ABI 不兼容 | 计划中 |

另外：

- **`scripts/diagnose.py`** — 零依赖的环境 X 光机。一条命令给出全貌：解释器路径、`PATH` 里的每一个 Python、pip 归属、venv/conda 状态、GPU/驱动状态、镜像源配置，以及自动标红的风险项。
- **`references/`** — 按报错原文索引的决策树 + 安全协议。
- **`cases/`** — 真实排障案例（脱敏）。

## 设计原则

1. **先取证** — 没有体检报告不允许动手修复。`diagnose.py` 拍片，医生读片。
2. **安全协议** — 明确列出禁止操作（盲目升级、`sudo pip`、污染系统 Python）。目标不只是修好环境，而是**绝不让它更坏**。见 [`references/safety-protocol.md`](references/safety-protocol.md)。
3. **报错原文索引** — 决策树以完整的报错文本为键。这个仓库的设计目标就是：有人搜索报错时，它就该出现在答案里。
4. **中文优先的双语设计** — 中文和英文都是一等公民，因为中国的 Python 环境有它自己的经典故障模式：pip 镜像源配置、Windows + conda、CUDA/torch 版本地狱。

## 路线图

- **v0.1**（当前）：3 位医生、`diagnose.py`、安全协议、报错决策树、首批案例
- **v0.2**：`venv-doctor`、`native-doctor`、`conflict-doctor`；扩充案例库
- **之后**：社区提交的报错决策树、按平台整理的检查清单（Windows / WSL / Linux / macOS）

## 参与贡献

最有价值的贡献是**案例**：一个真实环境问题的完整诊断路径（脱敏后）。格式见 [`cases/`](cases/)。也欢迎修正决策树、为 `diagnose.py` 添加新的风险检测规则。

## 许可证

[MIT](LICENSE)
