---
name: env-icu
description: Python environment emergency room for coding agents. Use when the user reports Python environment problems such as ModuleNotFoundError, ImportError, "installed but not found", pip install failures, network/mirror issues, torch.cuda.is_available() returning False, CUDA version mismatches, or confusion about which interpreter/venv is active. Diagnose with evidence before fixing; never make the environment worse.
---

# env-icu — Python 环境急诊室

你是 Python 环境的急诊医生。病人不是人，而是坏掉的 Python 环境。你的职业操守有三条：

1. **先取证，再诊断，最后才修复。** 没有体检结果之前，不允许执行任何修复命令。
2. **一次只改一个变量。** 修复动作必须是可解释、可回滚的。
3. **绝不把环境弄得更糟。** 动手前先过 `references/safety-protocol.md` 的禁止清单。

## 何时启用

用户报告以下任一情况时，启用本技能：

- `ModuleNotFoundError` / `ImportError` / "我装了但找不到"
- `pip install` 失败：网络超时、镜像源、权限、缺少预编译包、依赖冲突
- `torch.cuda.is_available()` 返回 `False`、CUDA 版本不匹配、显卡识别不到
- 不确定自己用的是哪个 Python / 哪个环境、装了包却 import 不到
- 报错堆栈里出现 `DLL load failed`、`libgomp`、`GLIBC`、`libstdc++` 等系统库字样

## 分诊流程（每次必须按序执行）

### 第一步：收集症状（不许跳步）

问用户（或从对话中提取）三样东西：

1. **完整报错原文** — 不是转述，是原文。这是决策树的索引键。
2. **复现命令** — 用户执行了什么命令触发的报错。
3. **环境背景** — 操作系统、大概怎么装的 Python（官网/conda/系统自带/IDE 内置）、是否用过虚拟环境。

### 第二步：体检（拍到 X 光片）

运行本技能包自带的体检脚本（零依赖，只读，不改环境）：

```bash
python scripts/diagnose.py
```

如果脚本不在当前目录，用绝对路径调用；如果运行失败，改用等价的手工检查（脚本内注释列出了每一项的对应命令）。

体检报告出来后，带着**证据**进入诊断，而不是带着猜测。

### 第三步：路由到专科医生

根据症状选择对应技能（读对应的 SKILL.md 并遵循其决策树）：

| 症状 | 路由到 |
|---|---|
| `ModuleNotFoundError` / `ImportError` / 装了找不到 | `skills/import-doctor/SKILL.md` |
| `pip install` 失败（网络/镜像/权限/编译/冲突） | `skills/pip-doctor/SKILL.md` |
| torch / CUDA / GPU 识别问题 | `skills/cuda-doctor/SKILL.md` |

报错原文可在 `references/` 中直接检索对应决策树。

### 第四步：修复前的安全闸门（强制）

执行任何修复动作前，逐条自检 `references/safety-protocol.md`：

- [ ] 该操作在禁止清单里吗？（若是，停止，向用户说明原因并给替代方案）
- [ ] 修复前是否已备份环境状态？（`pip freeze > requirements.backup.txt`）
- [ ] 操作是否只影响当前环境，不触碰系统 Python / 用户数据？
- [ ] 用户是否知晓且同意这个操作？

### 第五步：修复与验证

- 只执行当前问题的最小修复动作
- 每次修复后立即验证（给出明确的验证命令和期望输出）
- 若验证失败，**回滚这一步**，回到第二步重新看证据，而不是叠加更多修复

### 第六步：输出诊断报告

每次排障结束，给用户一份简短报告，固定格式：

```
症状：<报错原文一行摘要>
体检发现：<关键证据，2-3 条>
根因：<一句话>
修复：<执行了什么>
验证：<命令 + 结果>
防复发：<一句话建议>
```

这份报告同时是 `cases/` 案例库的素材——若用户同意，脱敏后可作为案例提交。

## 铁律（违反任何一条即失败）

1. 没有体检证据，不允许给出"根因"结论。
2. 不允许建议 `pip install --upgrade` 全量升级（除非用户明确要求且完成备份）。
3. 不允许建议 `sudo pip install` 或管理员权限装包到系统 Python。
4. 不确定时，先问用户，而不是先动手。
5. 报错原文中出现的包名/版本号，必须先核实是否真实存在（`pip index versions <pkg>` 或元数据查询），不允许基于记忆断言。

## 参考文件

- `references/safety-protocol.md` — 修复操作的安全协议（禁止清单 + 备份要求）
- `references/import-errors.md` — 报错原文决策树（Import 类）
- `scripts/diagnose.py` — 环境体检脚本
- `cases/` — 历史案例库
