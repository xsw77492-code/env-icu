---
name: pip-doctor
description: Diagnose and fix pip install failures — network timeouts, mirror configuration, SSL/proxy errors, permission errors, missing prebuilt wheels requiring compilation, dependency resolution conflicts, and corrupted caches. Use when pip fails to install a package or when installs succeed but the environment becomes inconsistent.
---

# pip-doctor — 安装失败专科

处理一切 `pip install` 失败。核心方法论：**先读报错的第一段（错误类型），再读最后一段（真实原因）。中间 200 行回溯是给搜索引擎看的。**

## 分诊：按报错特征路由

| 报错特征 | 类型 | 去向 |
|---|---|---|
| `Read timed out` / `Connection refused` / `SSLError` / `ProxyError` | 网络 | N 组 |
| `PermissionError` / `Errno 13` / `Access is denied` | 权限 | P 组 |
| `error: Microsoft Visual C++ ... required` / `gcc: not found` / `Python.h: No such file` | 编译 | C 组 |
| `No matching distribution found for X` | 找不到包 | F 组 |
| `ResolutionImpossible` / `The conflict is caused by` | 依赖冲突 | D 组 |
| `No space left` / `哈希校验失败` / 缓存报错 | 缓存/磁盘 | X 组 |

## N 组：网络问题

### N1. 中国大陆直连 PyPI 超时（最高频）

先确认诊断：`pip install X` 卡住很久后 `Read timed out`。

修复（三种粒度，从临时到永久）：

```bash
# 临时：单次
python -m pip install X -i https://pypi.tuna.tsinghua.edu.cn/simple

# 项目级：写入项目 pip.conf / pip.ini

# 永久：全局配置
python -m pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

备选镜像（主源故障时）：阿里云 `https://mirrors.aliyun.com/pypi/simple/`、腾讯云 `https://mirrors.cloud.tencent.com/pypi/simple/`。

注意：不要因此把 `trusted-host` 一股脑关掉（见 N3）。

### N2. 代理冲突

特征：公司网络/代理软件残留。检查环境变量：

```bash
echo $HTTP_PROXY $HTTPS_PROXY     # POSIX
echo %HTTP_PROXY% %HTTPS_PROXY%   # Windows cmd
```

代理指向已失效的端口时，pip 会持续连不上。修复：清掉失效变量，或配置正确代理。

### N3. SSL 证书错误

特征：`SSLError: certificate verify failed`。多源于公司中间人代理或系统证书链不全。

修复顺序：换网络环境测试 → 更新 `certifi` → 更新系统证书。
**红线：不要把 `--trusted-host` / `--disable-pip-verify` 当作长期方案**——那是在关掉供应链校验，必须向用户明确说明风险后再考虑。

## P 组：权限问题

### P1. Linux / macOS 误用 sudo

特征：`sudo pip install` 报权限相关错，或装完后普通用户 import 失败。

**红线：禁止 sudo pip。** 修复路径：

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install X
```

### P2. Windows 装到系统目录

特征：Python 装在 `C:\Program Files\...`，普通权限写不进。

修复优先级：建 venv（推荐）→ 用户级安装 `python -m pip install --user X`（仅限纯 Python 包场景）。

## C 组：编译问题

特征：报错要求 C/C++ 编译器或 `Python.h`。

决策顺序（从省事到费事）：

1. **换预编译 wheel**：先升级 pip（新版对 wheel 选择更聪明）再重装：`python -m pip install --upgrade pip`
2. **换 conda 安装**：`conda install -c conda-forge X`（conda-forge 常有 Windows 预编译）
3. **找替代包**（生态里通常有纯 Python 实现）
4. **最后才装工具链**：Windows 装 VS Build Tools；Linux `apt install build-essential python3-dev`；macOS 装 Xcode Command Line Tools

原则：为一个包安装 6GB 的编译工具链之前，先问用户"能不能换个等价的包"。

## F 组：No matching distribution found

按概率排查：

1. **包名错误或别名** — `pip index versions <名字>` 验证；对照 import-doctor 的别名表
2. **Python 版本太新/太旧** — 报错通常会提示 `Requires-Python`；核实包的 supported versions
3. **平台不支持** — 例如只有 Linux wheel 的包在 Windows 上无解，走 conda 或找替代
4. **私有包** — 需要配置私有 index（`--extra-index-url`），问清楚来源

## D 组：依赖冲突 ResolutionImpossible

特征：`The conflict is caused by:` 后跟一长串链条。这是 pip 的**保护机制**，不是 bug——它在阻止你把环境装坏。

处理策略（按顺序）：

1. **读冲突链条**：pip 会指出哪个包要求哪个版本区间，找出"钉子包"（被多处同时约束的那个）
2. **收窄目标**：不要一口气装一个大型依赖树；先单独装核心包指定版本：`python -m pip install "A==1.2.*"`
3. **预演**：`python -m pip install --dry-run X` 先看会发生什么，再真装
4. **体检现状**：`python -m pip check` 列出已存在的依赖矛盾
5. **终极方案**：新建干净 venv，用锁定版本清单重装。**在冲突环境里修冲突，成功率低且污染加深——重建往往更快更干净。**

红线：不要用 `--force-reinstall` 粗暴覆盖（除非明确知道后果并已备份）；不要混合 conda 与 pip 互相覆盖同一批包。

## X 组：缓存与磁盘

```bash
python -m pip cache purge        # 清缓存（哈希失败/缓存损坏时）
```

磁盘满：先清理再装，不要忽略。

## 特殊场景：pip 自身坏了

`No module named pip` 或 pip 报内部错误：

```bash
python -m ensurepip --upgrade
# 或
python -m pip install --upgrade pip
```

## 输出要求

按 SKILL.md 第六步固定格式输出。诊断报告里必须包含：**完整安装命令（含镜像参数与版本约束）+ 验证命令 + 回滚方法**。
