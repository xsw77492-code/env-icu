---
name: native-doctor
description: Fix native extension import failures — DLL load failed on Windows, missing .so libraries on Linux (libgomp, libGL, GLIBC/GLIBCXX version errors), undefined symbol, wrong architecture on macOS. Use when a package with C/C++ extensions installs fine but fails at import with system-level library errors.
---

# native-doctor — 原生扩展专科

收治"包装得上、代码也不缺，import 时却炸在 C/C++ 库上"的问题。

先按报错对号入座：

| 报错原文 | 平台 | 去哪 |
|---|---|---|
| `ImportError: DLL load failed while importing X` | Windows | W 组 |
| `OSError: [WinError 126] 找不到指定的模块` | Windows | W 组 |
| `ImportError: libgomp.so.1: cannot open shared object file` | Linux | L1 |
| `version GLIBCXX_3.4.29 not found` / `version GLIBC_2.28 not found` | Linux | L2 |
| `undefined symbol: _ZN...` | Linux | L3 |
| `mach-o, but wrong architecture` / `symbol not found` | macOS | M |

一个通用原则放在最前面：**报错里点名的那个库文件，就是缺口。** 读原文比搜关键词快。

## W 组：Windows DLL load failed

按概率排查：

### W1. VC++ 运行库缺失

新装的系统、新装的 Python 上高发，而且往往是多个 C 扩展包同时挂（pywin32、lxml、PyQt 一起报）。

修复：安装 Microsoft Visual C++ Redistributable（官网下载 vc_redist.x64.exe，2015-2022 是同一个安装包）。装完重启终端。

### W2. 位数不匹配

64 位 Python 装了 32 位轮子，或反过来。

```bash
# 看解释器位数
python -c "import sys; print('64' if sys.maxsize > 2**32 else '32')"
# 看已装包的文件名（wheel 标签会写 win_amd64 或 win32）
```

修复：卸载后重装对应位数的版本。

### W3. 依赖的 DLL 找不到

大型包（torch、onnxruntime）的典型故障。报错会点名具体文件，比如 `c10.dll`、`onnxruntime_providers_shared.dll`。

常见成因：conda 和 pip 混装过同一个包，两份文件互相覆盖；杀毒软件隔离了 DLL。

修复：干净重装（先 uninstall 再 install）。不要手动从别处拷 DLL 进 site-packages，那是把问题藏起来，下次升级就复发。

## L 组：Linux 缺 .so / 版本不够

### L1. 系统库缺失（无桌面服务器高发）

装完 opencv-python、matplotlib 后 import 报 `libgomp.so.1`、`libGL.so.1`、`libglib-2.0.so.0` 找不到。服务器和容器没有桌面环境，这些库默认没有。

修复（Debian / Ubuntu）：

```bash
sudo apt-get install libgomp1 libgl1 libglib2.0-0
```

装哪个以报错点名的为准。没有 root 权限的话有两条路：

- 换 headless 版：`opencv-python-headless` 就是为没有图形界面的服务器准备的
- 用 conda 安装：conda 包把依赖打进环境内部，不动系统

### L2. GLIBC / GLIBCXX 版本不够

老机器（CentOS 7、Ubuntu 18.04）装新轮子时出现：`version GLIBCXX_3.4.29 not found`。

原因：轮子是在新系统上编译的，要求更新的系统库。老系统的 GLIBC 又不能随便动——它是整套系统的地基，换了大概率整个系统报废。

修复顺序：

1. 换老一点的轮子：找 manylinux2014 标签的版本，而不是 manylinux_2_28
2. 换 conda 装：conda 自带较新的 libstdc++，只作用于环境内部
3. 升级机器或系统：最后手段

**红线：不要手动替换 `libc.so.6` / `libstdc++.so.6`。** 网上有些教程教你下载新库覆盖，那是在把一台还能用的机器变成一台启动不了的机器。

### L3. undefined symbol

`undefined symbol: _ZN...` 这类（名字是 C++ 编译混淆后的形式）。

原因：扩展编译时链接的库和运行时加载的不是同一个版本。常见于自己 compile 的扩展，或 conda / pip 混装。

修复：先整体重装该包；仍不行用 ldd 查链接指向：

```bash
ldd $(python -c "import X; print(X.__file__)")
```

输出里 `not found` 的行就是缺的库。

## M 组：macOS

- `mach-o, but wrong architecture`：arm64 和 x86_64 混了。Apple Silicon 上跑着 x86 的 conda / Python 时高发。检查：`python -c "import platform; print(platform.machine())"`，再对比包的 wheel 标签（arm64 vs x86_64）。修复：统一到原生 arm64，或装 Rosetta 下的全套 x86 环境，两边别混。
- `symbol not found`：处理逻辑同 L3，着重检查 conda 与 pip 混装史。

## 修复顺序（所有平台通用）

1. 读报错原文，确定缺什么、哪个版本不够
2. 能用包管理器解决就用包管理器（apt / conda），不要让用户手动下载 dll / so 往目录塞
3. 大型包（torch、onnx、opencv）优先整体干净重装，不做单文件修复
4. 修完立即验证：`python -c "import X; print(X.__version__)"`

## 输出要求

按 SKILL.md 第六步的固定格式输出。根因必须落到具体缺口：缺哪个库、哪个版本不够、哪个环节的位数/架构不匹配。
