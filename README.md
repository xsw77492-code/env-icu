# env-icu

**The last stop before you reinstall your OS.**

[简体中文](README.zh-CN.md)

---

## Why this exists

True story.

This machine has 8 Python interpreters on it. Not by design — they accumulated over years of installing one tool after another. One day a package refused to import, so I asked my AI assistant to sort it out.

It was very confident. First `pip install --upgrade pip setuptools wheel`, then reinstall the package. After that, "one package won't import" had grown into "three environments contaminating each other."

What finally found it was a single command: `python -m pip -V`. The bare `pip` command pointed at Python 3.11. My code ran on 3.14. Everything had been "fixed" into an interpreter I never use.

The agent never looked at that layer.

The pattern keeps repeating: agents are great at guessing, terrible at measuring. Hallucinated versions, blanket upgrades, packages installed into the wrong interpreter. And environment damage is patient — everything looks fine on the spot, then things start breaking days later.

So here's env-icu: a skill pack that gives agents three rules.

> **Measure first. Diagnose second. Touch the environment last.**

Not magic. It won't fix everything. But it won't make things worse.

## Install (30 seconds)

```bash
git clone https://github.com/YOUR-NAME/env-icu.git

# Claude Code (personal skills dir) — adapt for your agent
cp -r env-icu ~/.claude/skills/env-icu
```

Works with any agent that reads `SKILL.md` / Agent Skills: Claude Code, Codex, Cursor, OpenClaw, DeepSeek Harness, and others.

## What using it looks like

```text
User:   I installed requests, but my script keeps saying:
        ModuleNotFoundError: No module named 'requests'

Agent:  (loads env-icu, runs the diagnostic script first — no fixing yet)

        Findings:
          - pip belongs to  C:\Python314\python.exe
          - your script runs under  .venv\Scripts\python.exe (3.11)
        Two different environments. The package went to the one you don't use.

        Fix:    python -m pip install requests
        Verify: python -c "import requests; print(requests.__version__)"
```

Notice the first move: measure, not fix.

## What's inside

| Skill | Handles | Status |
|---|---|---|
| `import-doctor` | `ModuleNotFoundError`, "installed but not found" | available |
| `cuda-doctor` | torch can't see the GPU, CUDA version hell | available |
| `pip-doctor` | install failures: network, mirrors, permissions, builds, conflicts | available |
| `venv-doctor` | broken activation, pip into global, moved venvs | available |
| `native-doctor` | `DLL load failed`, `libgomp`, `GLIBC` | planned |
| `conflict-doctor` | numpy / pydantic conflicts, ABI mismatches | planned |

Plus three things:

- **`scripts/diagnose.py`** — a zero-dependency, read-only checkup. One command lists every Python on your `PATH`, pip ownership, venv/conda state, GPU status, mirror config, and flags what looks off. This is the script that first caught the "bare pip points to another environment" problem on my own machine.
- **`references/`** — decision trees indexed by raw error text, plus the safety protocol.
- **`cases/`** — anonymized debugging cases.

## Three rules

1. **Measure first.** No root-cause claim, and no fixing, before the environment is measured.
2. **Safety gate.** An explicit forbidden-operations list (blind upgrades, `sudo pip`, colliding with the system Python). The goal isn't just to fix it — it's to not make it worse. See [`references/safety-protocol.md`](references/safety-protocol.md).
3. **Errors are the index.** Decision trees are keyed by raw error text, so someone pasting their error lands in the right place.

## Roadmap

- Now: four doctors (import / cuda / pip / venv), the diagnostic script, the safety protocol
- Next: native-doctor, conflict-doctor; more cases
- Later: community-submitted error trees; per-platform checklists (Windows / WSL / Linux / macOS)

## Contributing

The most valuable contribution is a case: a problem you actually hit, and how you found it. Anonymized is fine. Format guide in [`cases/`](cases/).

## License

[MIT](LICENSE)
