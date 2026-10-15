# env-icu

**重装系统之前的最后一站。**

[English](README.md)

---

## 起因

说个真实的事。

我这台电脑里有 8 个 Python 解释器。不是故意的，是这些年装各种工具慢慢攒出来的。某天有个包死活 import 不进去，我让 AI 助手帮我修。

它很自信。先让我 `pip install --upgrade pip setuptools wheel`，再让我把包重装一遍。照做之后，问题从一个包装不上，变成了三个环境开始互相污染。

最后救场的是一条命令：`python -m pip -V`。输出告诉我，裸 `pip` 指向的是 Python 3.11，而我的代码跑在 3.14 上。折腾半天，全装进了我不会用的那个环境。

AI 从头到尾没看过这一层。

后来这种事我反复见到，AI 修 Python 环境的通病不是水平不够，是**它在猜，而且猜得很自信**：幻觉出不存在的版本号、无脑全量升级、把包装进你根本没在用的解释器。而环境问题最麻烦的地方是，它被修坏的代价往往延迟爆发——当场看着都正常，几天后开始连环报错。

所以有了 env-icu。它是一个 Agent 技能包，给 AI 助手立了三条规矩：

> **先体检，再诊断，最后才动手。**

它不魔法，也修不好所有问题。但它至少不会把你的环境修得更坏。

## 安装（30 秒）

```bash
git clone https://github.com/YOUR-NAME/env-icu.git

# Claude Code（个人技能目录）——其它 Agent 替换成对应目录
cp -r env-icu ~/.claude/skills/env-icu
```

兼容任何支持 `SKILL.md` / Agent Skills 标准的 Agent：Claude Code、Codex、Cursor、OpenClaw、DeepSeek Harness 等。

## 用起来是什么样

```text
你：  我明明装了 requests，脚本却一直报：
     ModuleNotFoundError: No module named 'requests'

Agent：（加载 env-icu，先跑体检脚本，不急着修）

     体检结论：
       - pip 属于  C:\Python314\python.exe
       - 而脚本运行在  .venv\Scripts\python.exe（3.11）
     两个不同的环境，包装到了你没在用的那个。

     修复：  python -m pip install requests
     验证：  python -c "import requests; print(requests.__version__)"
```

注意 Agent 的第一步：不是修，是看。

## 内容清单

| 技能 | 处理的问题 | 状态 |
|---|---|---|
| `import-doctor` | `ModuleNotFoundError`、"装了但找不到" | 可用 |
| `cuda-doctor` | torch 认不出显卡、CUDA 版本地狱 | 可用 |
| `pip-doctor` | 装不上：网络、镜像源、权限、编译、依赖冲突 | 可用 |
| `venv-doctor` | 虚拟环境失联、pip 装进全局、激活失败 | 可用 |
| `native-doctor` | `DLL load failed`、`libgomp`、`GLIBC` 缺失 | 计划中 |
| `conflict-doctor` | numpy/pydantic 版本冲突、ABI 不兼容 | 计划中 |

另外有三样东西：

- **`scripts/diagnose.py`** — 体检脚本。零依赖、只读，一条命令列出解释器、`PATH` 上的所有 Python、pip 归属、venv/conda 状态、GPU、镜像源，并自动标出可疑项。就是它第一个在我自己机器上抓到了"裸 pip 指向另一个环境"。
- **`references/`** — 按报错原文索引的决策树，外加一份安全协议。
- **`cases/`** — 排障案例，脱敏收录。

## 三条规矩

1. **先体检** — 没有体检报告，不允许下"根因"结论，更不允许动手。
2. **安全闸门** — 有份明确的禁止清单（盲目升级、`sudo pip`、动系统 Python……）。目标不只是修好，更是不修坏。见 [`references/safety-protocol.md`](references/safety-protocol.md)。
3. **报错即索引** — 决策树按报错原文组织。有人搜报错，它就该出现。

## 路线图

- 当前：四位医生（import / cuda / pip / venv）+ 体检脚本 + 安全协议
- 下一步：native-doctor、conflict-doctor；案例库扩充
- 更远：社区提交的报错决策树；按平台整理的清单（Windows / WSL / Linux / macOS）

## 参与

最有价值的贡献是一个案例：你踩过的坑、你的排查路径，脱敏之后就能帮到下一个人。格式见 [`cases/`](cases/)。

## 许可证

[MIT](LICENSE)
