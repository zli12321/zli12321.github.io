# Submitting to the LHTB leaderboard

The **Long-Horizon-Terminal-Bench (LHTB)** leaderboard follows the same submission
flow as [Terminal-Bench&nbsp;2](https://www.tbench.ai/leaderboard/terminal-bench/2.0):
run the full 46-task suite with **five trials per task** under one shared harness,
then open a pull request against this repo with your job directories. A bot
validates the submission and a maintainer reviews the trajectories against the
hidden verifiers before it lands on the board.

Repo: **`IntelligenceLab/LHTB-leaderboard`** (Hugging Face Dataset)

---

## 1. Run all 46 tasks, five trials each

Use the reference `terminus-2` harness and a 90-minute budget per task. `-k 5`
runs each task five times.

**Evaluate a model (reference harness):**

```bash
harbor run -d long-horizon-terminal-bench \
  -a terminus-2 -m "your-provider/your-model" -k 5
```

**Bring your own agent:**

```bash
harbor run -d long-horizon-terminal-bench \
  --agent-import-path "path.to.agent:YourAgent" -k 5
```

This produces a job directory containing a `config.json` and one folder per trial,
each with a `result.json` and the run artifacts (logs, terminal recordings, etc.).

---

## 2. Fork this repo and add your jobs

Fork `IntelligenceLab/LHTB-leaderboard`, then drop your job folder(s) under:

```
submissions/long-horizon-terminal-bench/1.0/<agent>__<model>/
```

Alongside a `metadata.yaml`. Full layout:

```
submissions/long-horizon-terminal-bench/1.0/
  terminus-2__your-model/
    metadata.yaml
    <job-folder>/
      config.json
      <trial-1>/result.json
      <trial-2>/result.json
      ...              # >= 5 trials/task, with artifacts
```

**`metadata.yaml`:**

```yaml
agent: terminus-2
model: your-provider/your-model
organization: Your Org
repo: https://github.com/your/agent   # optional
docs: https://.../model-card          # optional
```

---

## 3. Open a pull request

Push your fork and open a PR against `IntelligenceLab/LHTB-leaderboard`.

- The validation bot auto-checks the submission and comments on any errors.
- Once it passes, a maintainer reviews the trajectories and merges.
- Your run is then imported to the board with a **verified** badge.

---

## Validation rules

A submission is valid only if **all** of the following hold:

- Five trials per task (`-k 5`).
- `timeout_multiplier = 1.0` — no agent or verifier timeout overrides.
- No CPU / memory / storage overrides.
- Every trial has a valid `result.json` with run artifacts.
- Agents may **not** access the LHTB website or repository (reward hacking).
- Errored trials score **0**.

Scores are **mean reward** over the 46-task suite (errors = 0). A task counts as
*solved* at reward ≥ 0.95; the strict binary pass rate uses reward = 1.0.
