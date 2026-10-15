#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""env-icu diagnose — 环境体检 X 光机

只读脚本：只收集证据，不修改任何环境。
零依赖：仅使用 Python 标准库，Python 3.7+ 均可运行。

用法:
    python diagnose.py            # 输出 Markdown 体检报告
    python diagnose.py --json     # 输出 JSON（供 Agent 程序化读取）
    python diagnose.py --deep     # 额外做 torch/CUDA 联动检查（会启动子进程 import torch，较慢）

建议用「运行你代码的那个解释器」来执行本脚本，例如:
    .venv/Scripts/python.exe scripts/diagnose.py
"""

import argparse
import datetime
import json
import os
import platform
import re
import shutil
import subprocess
import sys

VERSION = "0.1.0"

KEY_PACKAGES = [
    "pip", "setuptools", "wheel", "virtualenv", "uv",
    "numpy", "pandas", "scipy", "matplotlib",
    "torch", "torchvision", "torchaudio",
    "pydantic", "requests", "opencv-python", "Pillow",
    "notebook", "jupyter-core", "ipykernel",
]

PROXY_VARS = ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
              "http_proxy", "https_proxy", "all_proxy", "no_proxy"]

# Python 可执行文件名匹配（跨平台）
_PY_NAME_RE = re.compile(r"^(python|pythonw|pip|py)[0-9.]*(\.exe)?$", re.IGNORECASE)


def _setup_stdout():
    """尽量让 Windows 控制台也能正确输出 UTF-8。"""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def run(cmd, timeout=20):
    """运行外部命令，返回 (ok, output)。永不抛异常。"""
    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        out = p.stdout.decode("utf-8", errors="replace").strip()
        return (p.returncode == 0, out)
    except FileNotFoundError:
        return (False, "")
    except subprocess.TimeoutExpired:
        return (False, "<timed out>")
    except Exception as e:  # noqa: BLE001
        return (False, "<error: %s>" % e)


def norm(p):
    """路径标准化（Windows 大小写不敏感）。"""
    if not p:
        return ""
    return os.path.normcase(os.path.normpath(p))


def is_windowsapps_stub(path):
    """Windows 微软商店的 python 占位符（0 字节 reparse point）。"""
    low = path.lower().replace("/", "\\")
    if "\\microsoft\\windowsapps\\" not in low and "\\windowsapps\\" not in low:
        return False
    try:
        return os.path.getsize(path) == 0
    except OSError:
        return False


def get_interpreter():
    bits = 64 if sys.maxsize > 2 ** 32 else 32
    info = {
        "executable": sys.executable,
        "version": platform.python_version(),
        "version_full": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "bits": bits,
        "compiler": platform.python_compiler(),
        "platform": platform.platform(),
        "os": platform.system(),
    }
    return info


def get_env_state():
    in_venv = sys.prefix != sys.base_prefix
    conda_meta = os.path.isdir(os.path.join(sys.prefix, "conda-meta"))
    state = {
        "in_virtualenv": in_venv,
        "in_conda": conda_meta,
        "sys_prefix": sys.prefix,
        "sys_base_prefix": sys.base_prefix,
        "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV", ""),
        "CONDA_PREFIX": os.environ.get("CONDA_PREFIX", ""),
        "CONDA_DEFAULT_ENV": os.environ.get("CONDA_DEFAULT_ENV", ""),
    }
    if in_venv:
        state["mode"] = "venv / virtualenv（已激活，当前解释器在虚拟环境中）"
    elif conda_meta:
        state["mode"] = "conda 环境（当前解释器在 conda 环境中）"
    else:
        state["mode"] = "全局解释器（未在任何虚拟环境中）"
    state["venv_consistent"] = True
    ve = state["VIRTUAL_ENV"]
    if ve and in_venv:
        state["venv_consistent"] = norm(ve) == norm(sys.prefix)
    return state


def get_path_pythons():
    """扫描 PATH，列出所有 python / pip 可执行文件。"""
    found = []
    seen = set()
    which_python = shutil.which("python")
    which_pip = shutil.which("pip")
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    for d in path_dirs:
        if not d or not os.path.isdir(d):
            continue
        try:
            entries = os.listdir(d)
        except OSError:
            continue
        for name in entries:
            if not _PY_NAME_RE.match(name):
                continue
            full = os.path.join(d, name)
            key = norm(full)
            if key in seen or not os.path.isfile(full):
                continue
            seen.add(key)
            tag = []
            if is_windowsapps_stub(full):
                tag.append("微软商店占位符(0字节)")
            if "conda" in full.lower():
                tag.append("conda")
            if "\\venv\\" in full.lower() or "\\.venv\\" in full.lower() \
                    or "/venv/" in full.lower() or "/.venv/" in full.lower():
                tag.append("疑似 venv")
            found.append({
                "path": full,
                "is_which_python": bool(which_python and norm(full) == norm(which_python)),
                "is_which_pip": bool(which_pip and norm(full) == norm(which_pip)),
                "tags": tag,
            })
    return {
        "resolved_python": which_python or "(not found)",
        "resolved_pip": which_pip or "(not found)",
        "entries": found,
    }


def get_pip_ownership():
    ok, out = run([sys.executable, "-m", "pip", "-V"], timeout=40)
    result = {
        "pip_version_output": out if ok else "<pip 不可用或以非零码退出>",
        "pip_site_packages": "",
        "consistent": None,
    }
    if ok and out:
        m = re.search(r"from\s+(.+?)\s+\(python", out)
        if m:
            pip_path = m.group(1)
            sp = ""
            for marker in ("site-packages", "dist-packages"):
                idx = pip_path.lower().find(marker)
                if idx != -1:
                    sp = pip_path[:idx + len(marker)]
                    break
            if sp:
                result["pip_site_packages"] = sp
                # 最可靠的判定：pip 的 site-packages 是否在当前解释器的 sys.path 中
                result["consistent"] = any(norm(p) == norm(sp) for p in sys.path)
    return result


def get_packages():
    from importlib import metadata
    installed = []
    for name in KEY_PACKAGES:
        try:
            v = metadata.version(name)
            installed.append((name, v))
        except Exception:
            continue
    return {"key_packages": installed}


def get_pip_config():
    ok, out = run([sys.executable, "-m", "pip", "config", "list"], timeout=30)
    lines = [l for l in out.splitlines() if l.strip()] if ok else []
    return {"pip_config": lines, "ok": ok}


def get_gpu():
    result = {"nvidia_smi": False, "gpus": [], "driver_supported_cuda": ""}
    ok, out = run(
        ["nvidia-smi", "--query-gpu=name,driver_version,memory.total",
         "--format=csv,noheader"],
        timeout=15,
    )
    if ok and out and "<" not in out:
        result["nvidia_smi"] = True
        result["gpus"] = [l.strip() for l in out.splitlines() if l.strip()]
    else:
        result["nvidia_smi_raw"] = out[:200] if out else ""
    # 驱动支持的最高 CUDA 版本（nvidia-smi 头部输出）
    ok2, out2 = run(["nvidia-smi"], timeout=15)
    if ok2 and out2:
        m = re.search(r"CUDA Version:\s*([0-9.]+)", out2)
        if m:
            result["driver_supported_cuda"] = m.group(1)
    return result


def get_torch_deep():
    """--deep: 子进程里 import torch，检查 CUDA 联动（不污染本进程）。"""
    code = (
        "import json\n"
        "try:\n"
        "    import torch\n"
        "    print(json.dumps({\n"
        "        'torch': torch.__version__,\n"
        "        'compiled_cuda': torch.version.cuda,\n"
        "        'cuda_available': bool(torch.cuda.is_available()),\n"
        "        'device_count': torch.cuda.device_count(),\n"
        "    }))\n"
        "except Exception as e:\n"
        "    print(json.dumps({'error': type(e).__name__ + ': ' + str(e)}))\n"
    )
    ok, out = run([sys.executable, "-c", code], timeout=120)
    if not ok or not out:
        return {"ok": False, "detail": out or "子进程执行失败"}
    try:
        line = out.strip().splitlines()[-1]
        return {"ok": True, "detail": json.loads(line)}
    except Exception:
        return {"ok": False, "detail": out}


def get_env_vars():
    interesting = ["PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV",
                   "CONDA_PREFIX", "CUDA_VISIBLE_DEVICES", "CUDA_HOME", "CUDA_PATH"]
    vals = {k: os.environ.get(k, "") for k in interesting if os.environ.get(k)}
    proxies = {k: os.environ.get(k, "") for k in PROXY_VARS if os.environ.get(k)}
    return {"python_vars": vals, "proxies": proxies}


def analyze(report):
    """核心价值：自动读取报告，产出风险提示。"""
    findings = []

    ident = report["interpreter"]
    envs = report["env_state"]
    pypaths = report["path_pythons"]
    pip_own = report["pip_ownership"]
    pkgs = dict(report["packages"]["key_packages"])
    gpu = report["gpu"]
    evars = report["env_vars"]

    # 1. python -m pip 与当前解释器归属
    if pip_own.get("consistent") is False:
        findings.append(
            ("高", "python -m pip 归属异常：pip 位于 `%s`，不在当前解释器的 sys.path 中。"
                 "这是『装了却 import 不到』的头号根因。"
                 "修复：确认用当前解释器执行 python -m pip install。"
                 % pip_own.get("pip_site_packages", "?")))
    elif pip_own.get("consistent") is None:
        findings.append(("中", "无法确认 pip 归属（pip -V 未正常输出），建议先修复 pip：python -m ensurepip --upgrade"))

    # 1b. 裸 pip 命令与当前解释器错位（PATH 顺序问题）
    rp = pypaths.get("resolved_pip", "")
    if rp and rp not in ("(not found)", "") and norm(sys.prefix) not in norm(rp):
        findings.append(
            ("中", "裸 `pip` 命令解析到 `%s`，不属于当前解释器环境。"
                   "直接敲 pip install 会把包装到别的环境——一律改用 python -m pip install。"
             % rp))

    # 2. PATH 中的多解释器
    entries = pypaths["entries"]
    real_pythons = [e for e in entries
                    if os.path.basename(e["path"]).lower().startswith("python")
                    and "微软商店占位符" not in "".join(e["tags"])]
    if len(entries) > 2:
        stub = [e for e in entries if "微软商店占位符(0字节)" in e["tags"]]
        msg = "PATH 中存在多个 python/pip 可执行文件，命令解析顺序可能导致装错环境。"
        if stub:
            msg += " 检测到微软商店占位符（%s），它可能拦截 python 命令。" % stub[0]["path"]
        findings.append(("中", msg + " 建议用解释器绝对路径或 python -m pip 明确指定。"))
    if len(real_pythons) > 1 and not envs["in_virtualenv"]:
        findings.append(
            ("中", "系统里有 %d 个真实的 python 解释器，且当前不在虚拟环境中。"
                   "强烈建议为每个项目创建独立 venv。" % len(real_pythons)))

    # 3. venv 变量一致性
    if envs["VIRTUAL_ENV"] and not envs["in_virtualenv"]:
        findings.append(
            ("高", "VIRTUAL_ENV 变量指向 %s，但当前解释器并不在该环境中"
                   "（venv 未生效或已损坏）。先修复激活流程再装任何包。"
                   % envs["VIRTUAL_ENV"]))
    elif envs.get("venv_consistent") is False:
        findings.append(("中", "VIRTUAL_ENV 与实际运行环境不一致（shell 状态残留），建议重开终端。"))

    # 4. conda 与 venv 混用
    if envs["in_virtualenv"] and envs["CONDA_PREFIX"]:
        findings.append(("中", "同时检测到 venv 与 conda 环境痕迹（CONDA_PREFIX=%s）。"
                               "激活 venv 前建议先 conda deactivate，避免包装错位置。" % envs["CONDA_PREFIX"]))

    # 5. PYTHONPATH 污染
    if evars["python_vars"].get("PYTHONPATH"):
        findings.append(("中", "PYTHONPATH 非空（%s），可能污染 import 查找路径。"
                               "排查导入问题时先临时清空它对照。"
                         % evars["python_vars"]["PYTHONPATH"]))

    # 6. torch CPU 版
    torch_ver = pkgs.get("torch", "")
    if torch_ver and ("+cpu" in torch_ver):
        if gpu["nvidia_smi"]:
            findings.append(("高", "检测到 NVIDIA 显卡，但 torch 是 CPU 版（%s）。"
                                   "若想用 GPU：pip uninstall torch 后用官方 CUDA index 重装（见 cuda-doctor）。" % torch_ver))
        else:
            findings.append(("低", "torch 是 CPU 版（%s），且未检测到 NVIDIA 显卡。" % torch_ver))

    # 7. GPU 相关
    if gpu["nvidia_smi"] and not torch_ver:
        findings.append(("低", "检测到 NVIDIA 显卡，但当前环境未安装 torch。"
                               "安装时请确认 GPU 版（见 cuda-doctor 的『安装 GPU 版 torch』）。"))
    if gpu["driver_supported_cuda"] and torch_ver and "+cpu" not in torch_ver:
        deep = report.get("torch_deep", {})
        detail = deep.get("detail", {}) if deep else {}
        compiled = detail.get("compiled_cuda") if isinstance(detail, dict) else None
        if compiled and compiled > gpu["driver_supported_cuda"]:
            findings.append(("高", "torch 编译 CUDA 版本(%s) 高于驱动支持版本(%s)，GPU 将不可用。"
                                   "更新驱动，或改装低 CUDA 版 torch。" % (compiled, gpu["driver_supported_cuda"])))

    # 8. 代理
    if evars["proxies"]:
        findings.append(("低", "检测到代理环境变量（%s）。若 pip 出现网络错误，优先检查这些代理是否失效。"
                         % ", ".join(sorted(evars["proxies"].keys()))))

    # 9. pip 镜像源
    cfg = report["pip_config"].get("pip_config", [])
    if not any("index-url" in l for l in cfg):
        findings.append(("低", "未配置 pip 镜像源。中国大陆网络下建议配置清华镜像（见 pip-doctor N1）。"))

    if not findings:
        findings.append(("无", "未发现明显风险项。"))
    return findings


def collect(deep=False):
    report = {
        "tool": "env-icu diagnose",
        "version": VERSION,
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "interpreter": get_interpreter(),
        "env_state": get_env_state(),
        "path_pythons": get_path_pythons(),
        "pip_ownership": get_pip_ownership(),
        "packages": get_packages(),
        "pip_config": get_pip_config(),
        "gpu": get_gpu(),
        "env_vars": get_env_vars(),
    }
    if deep:
        report["torch_deep"] = get_torch_deep()
    report["findings"] = analyze(report)
    return report


def render_markdown(r):
    L = []
    a = L.append
    a("# env-icu 环境体检报告")
    a("")
    a("生成时间: %s  |  脚本版本: %s" % (r["generated_at"], r["version"]))
    a("")

    i = r["interpreter"]
    a("## 1. 解释器")
    a("")
    a("- 路径: `%s`" % i["executable"])
    a("- 版本: %s (%s-bit, %s)" % (i["version"], i["bits"], i["implementation"]))
    a("- 编译器: %s" % i["compiler"])
    a("- 平台: %s" % i["platform"])
    a("")

    e = r["env_state"]
    a("## 2. 环境归属")
    a("")
    a("- 状态: **%s**" % e["mode"])
    a("- sys.prefix: `%s`" % e["sys_prefix"])
    a("- base_prefix: `%s`" % e["sys_base_prefix"])
    if e["VIRTUAL_ENV"]:
        a("- VIRTUAL_ENV: `%s`" % e["VIRTUAL_ENV"])
    if e["CONDA_PREFIX"]:
        a("- CONDA_PREFIX: `%s`（%s）" % (e["CONDA_PREFIX"], e["CONDA_DEFAULT_ENV"]))
    a("")

    p = r["path_pythons"]
    a("## 3. PATH 中的 Python 与 pip")
    a("")
    a("- `python` 命令解析到: `%s`" % p["resolved_python"])
    a("- `pip` 命令解析到: `%s`" % p["resolved_pip"])
    a("")
    if p["entries"]:
        a("| 路径 | 标记 |")
        a("|---|---|")
        for en in p["entries"]:
            marks = list(en["tags"])
            if en["is_which_python"]:
                marks.append("= python 命令")
            if en["is_which_pip"]:
                marks.append("= pip 命令")
            a("| `%s` | %s |" % (en["path"], "、".join(marks) or "—"))
        a("")
    else:
        a("（PATH 中未找到 python/pip 可执行文件）")
        a("")

    o = r["pip_ownership"]
    a("## 4. pip 归属")
    a("")
    a("- `python -m pip -V` 输出: `%s`" % o["pip_version_output"])
    if o.get("consistent") is True:
        a("- 结论: **一致** — pip 属于当前解释器所在环境")
    elif o.get("consistent") is False:
        a("- 结论: **不一致** — pip 属于 `%s`，而当前解释器 (`%s`) 的 sys.path 中不含该目录"
          % (o.get("pip_site_packages"), i["executable"]))
    else:
        a("- 结论: 无法判定（pip 未正常工作）")
    a("")

    a("## 5. 关键包（来自元数据，未 import）")
    a("")
    kp = r["packages"]["key_packages"]
    if kp:
        for name, ver in kp:
            a("- `%s == %s`" % (name, ver))
    else:
        a("（未检测到任何关键包）")
    a("")

    cfg = r["pip_config"]
    a("## 6. pip 配置")
    a("")
    if cfg.get("pip_config"):
        for l in cfg["pip_config"]:
            a("- `%s`" % l)
    else:
        a("（无自定义 pip 配置或读取失败）")
    a("")

    g = r["gpu"]
    a("## 7. GPU / CUDA")
    a("")
    if g["nvidia_smi"]:
        for line in g["gpus"]:
            a("- GPU: %s" % line)
        if g["driver_supported_cuda"]:
            a("- 驱动支持的最高 CUDA 版本: **%s**" % g["driver_supported_cuda"])
    else:
        a("- `nvidia-smi` 不可用（无 NVIDIA 显卡，或驱动未安装）")
    a("")

    deep = r.get("torch_deep")
    if deep is not None:
        a("## 7b. torch 深度检查（--deep）")
        a("")
        if deep.get("ok"):
            d = deep["detail"]
            a("- torch 版本: `%s`" % d.get("torch"))
            a("- 编译 CUDA 版本: `%s`" % d.get("compiled_cuda"))
            a("- cuda.is_available(): **%s**" % d.get("cuda_available"))
            a("- GPU 数量: %s" % d.get("device_count"))
        else:
            a("- 检查失败: %s" % deep.get("detail"))
        a("")

    ev = r["env_vars"]
    a("## 8. 相关环境变量")
    a("")
    if ev["python_vars"]:
        for k, v in ev["python_vars"].items():
            a("- `%s=%s`" % (k, v))
    else:
        a("（无相关变量设置）")
    if ev["proxies"]:
        a("")
        a("代理变量:")
        for k, v in ev["proxies"].items():
            a("- `%s=%s`" % (k, v))
    a("")

    a("## 9. 自动风险提示")
    a("")
    for idx, (level, msg) in enumerate(r["findings"], 1):
        a("%d. **[%s]** %s" % (idx, level, msg))
    a("")
    a("---")
    a("")
    a("-- env-icu diagnose · 只读检查，未改动任何环境")
    return "\n".join(L)


def main():
    parser = argparse.ArgumentParser(
        description="env-icu diagnose — 只读的 Python 环境体检工具")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--deep", action="store_true",
                        help="额外做 torch/CUDA 联动检查（较慢）")
    args = parser.parse_args()

    _setup_stdout()
    report = collect(deep=args.deep)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report))


if __name__ == "__main__":
    main()
