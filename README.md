# env-icu

**The last stop before you reinstall your OS.**

An agent skill pack that turns any coding agent into a Python environment troubleshooter — one that gathers evidence first, and never makes a broken environment worse.

[简体中文](README.zh-CN.md)

---

## The problem

When a Python environment breaks, your coding agent usually makes it worse:

- `pip install --upgrade` on everything, hoping something sticks
- Hallucinated version numbers and packages that do not exist
- `sudo pip install` that corrupts the system Python
- Advice copy-pasted from a 2019 GitHub issue for a library you do not even have

The root cause: **agents guess instead of diagnosing.** env-icu gives them a discipline instead:

> Evidence first. Diagnose, then fix. Never break it worse.

## Install (30 seconds)

```bash
git clone https://github.com/YOUR-NAME/env-icu.git

# Claude Code (personal skills directory) — adapt the path for your agent
cp -r env-icu ~/.claude/skills/env-icu
```

Works with any agent that supports the `SKILL.md` / Agent Skills standard: Claude Code, Codex, Cursor, OpenClaw, DeepSeek Harness, and others. Point the agent at this repository, or drop it into your agent's skills directory.

## Quick demo

```text
User:   I installed requests, but my script says:
        ModuleNotFoundError: No module named 'requests'

Agent:  (loads env-icu, runs scripts/diagnose.py first)

        Evidence:
          - pip belongs to  C:\Python314\python.exe
          - your script runs under  .venv\Scripts\python.exe (3.11)
        Two different environments. The package went to the interpreter
        you are not using.

        Fix:    python -m pip install requests
        Verify: python -c "import requests; print(requests.__version__)"
```

No guessing. The agent measured first, then fixed the actual problem.

## What's inside

| Skill | Symptoms it handles | Status |
|---|---|---|
| `import-doctor` | `ModuleNotFoundError`, `ImportError`, "I installed it but it's not found" | available |
| `cuda-doctor` | `torch.cuda.is_available()` returns `False`, CUDA driver/version mismatch | available |
| `pip-doctor` | install failures: network/mirrors, permissions, missing wheels, dependency conflicts | available |
| `venv-doctor` | venv not activating, `pip` installing into the global interpreter | roadmap |
| `native-doctor` | `DLL load failed`, `libgomp`, `GLIBC` not found, missing system libraries | roadmap |
| `conflict-doctor` | numpy / pydantic version conflicts, ABI incompatibilities | roadmap |

Plus:

- **`scripts/diagnose.py`** — a zero-dependency environment X-ray. One command, full picture: interpreter paths, every Python on your `PATH`, pip ownership, venv/conda state, GPU/driver status, mirror config, and automatic red flags.
- **`references/`** — decision trees keyed by the exact error text, plus a safety protocol.
- **`cases/`** — real-world debugging cases, anonymized.

## Design principles

1. **Evidence first** — no fix is allowed before the environment is measured. `diagnose.py` produces the X-ray; the doctors read it.
2. **Safety protocol** — a hard list of forbidden operations (blind upgrades, `sudo pip`, system Python pollution). The goal is not only to fix the environment, but to *never make it worse*. See [`references/safety-protocol.md`](references/safety-protocol.md).
3. **Error-text indexed** — decision trees are keyed by the exact error text you paste in. The repository is designed to be the answer when someone searches their error message.
4. **Bilingual by design** — Chinese and English are both first-class, because China's Python setup has its own classic failure modes: pip mirror configuration, Windows + conda, CUDA/torch "version hell".

## Roadmap

- **v0.1** (current): 3 doctors, `diagnose.py`, safety protocol, error trees, first cases
- **v0.2**: `venv-doctor`, `native-doctor`, `conflict-doctor`; expanded case library
- **later**: community-submitted error trees, per-platform checklists (Windows / WSL / Linux / macOS)

## Contributing

The most valuable contribution is a **case**: a real environment problem with its diagnosis path, anonymized. See [`cases/`](cases/) for the format. Error-tree corrections and new red-flag rules for `diagnose.py` are also welcome.

## License

[MIT](LICENSE)
