---
name: conflict-doctor
description: Diagnose Python package version conflicts after the fact — ABI breakage after major upgrades (numpy 1.x to 2.x, pydantic v1 vs v2), pip check failures, packages that worked yesterday and broke after an upgrade. Use when imports fail with core-library errors, when two installed packages demand incompatible versions, or when an upgrade broke unrelated functionality.
---

# conflict-doctor — 版本冲突专科

和 pip-doctor 的 D 组分工明确：D 组处理安装**当时**的依赖冲突（ResolutionImpossible），这里处理装完之后爆发的冲突，尤其是大版本升级引发的地震。

## 分诊

| 特征 | 去哪 |
|---|---|
| 安装时就报依赖无法解析 | pip-doctor D 组 |
| `numpy.core.multiarray failed to import` 类错误 | A |
| pydantic 相关 ImportError / 行为突变 | B |
| `pip check` 一堆矛盾、程序时好时坏 | C |
| `undefined symbol` 等 ABI 报错 | native-doctor |

## A. numpy 大版本地震

最高频的场景：某次升级把 numpy 带上了 2.x，然后 opencv、pandas、matplotlib 集体罢工，报 `numpy.core.multiarray failed to import`。

原因不复杂：这些包编译时链接的是 numpy 1.x 的 C ABI，numpy 2.x 断掉了旧接口。

处理顺序：

1. 升级报错的包（首选，绝大多数包已适配）

```bash
python -m pip install --upgrade opencv-python
python -c "import numpy, cv2; print('OK')"
```

2. 一次改一个包，每个都验证。三个包同时升会把排查搞成一锅粥。
3. 某个包确实没有适配版本，回退 numpy 作为止损：

```bash
python -m pip install "numpy<2"
```

然后把这个约束写进 requirements.txt，别让它再被悄悄带上去。

## B. pydantic v1 / v2

v1 到 v2 不是升级，是换了个库。典型症状：

- `ImportError: cannot import name 'BaseSettings' from 'pydantic'`（v2 里搬到了 `pydantic-settings`）
- 老代码 `@validator` 报废弃警告（v2 用 `@field_validator`）
- FastAPI 版本和 pydantic 版本互相要求对不上

先确认版本：

```bash
python -c "import pydantic; print(pydantic.VERSION)"
```

两个方向的修法：

- 环境是 v1，要升 v2：升级 pydantic，同时装 `pydantic-settings`；FastAPI 也升到支持 v2 的版本（0.100+）。三者要一起动。
- 环境是 v2，有老库只认 v1：优先升级那个库；升级不了就用 v2 自带的兼容层：`from pydantic.v1 import ...`。兼容层是整个 v1 的 API，长期看还是应该换掉。

## C. pip check 报矛盾，但程序还能跑

先别急着全修。把矛盾分类：

1. 跑 `python -m pip check`，逐条看矛盾涉及哪个包
2. 分两类：涉及你实际用到的功能 → 修；只是版本范围告警、你没用到那边接口的 → 记录，先不动
3. 修的手法：先收窄报错包的版本约束，再动被牵连的包
4. 不要为了让 `pip check` 输出为空而全量升级。清空输出不是目标，环境能用才是。

## D. 防复发

冲突反复出现通常是习惯问题，四条：

1. **基石包锁版本**：numpy、pydantic、protobuf、sqlalchemy、torch 这类底层包，在 requirements.txt 里写明确版本（`==` 或 `~=`），不要用裸包名
2. **一个环境一种主管理器**：pip / conda 混装同一批包是冲突制造机
3. **成对升级**：升级核心包时，把依赖它的包一起看。opencv 和 numpy 是一对，fastapi 和 pydantic 是一对
4. **定期体检**：`pip check` + `diagnose.py`，每季度或每次大改环境前跑一次

## 输出要求

按 SKILL.md 第六步的固定格式输出。根因要写清冲突的两方是谁、各自的版本要求从哪来（哪个包要求的），以及为什么这次升级会触发它。
