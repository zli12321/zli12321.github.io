# Submitting to the LHTB leaderboard

The **Long-Horizon-Terminal-Bench (LHTB)** leaderboard follows the same submission
flow as [Terminal-Bench&nbsp;2](https://www.tbench.ai/leaderboard/terminal-bench/2.0):
run the full 46-task suite **once** under one shared harness,
then open a pull request against this repo with your job directories. Because this
is a **Hugging Face Dataset**, there is **no fork** — a PR pushes to a `refs/pr/N`
branch directly on the repo (see step 3). A bot validates the submission and a
maintainer reviews the trajectories against the hidden verifiers before it lands on
the board.

Repo: **`IntelligenceLab/LHTB-leaderboard`** (Hugging Face Dataset)

---

## 1. Run all 46 tasks once

Use the reference `terminus-2` harness and a 90-minute budget per task. `-k 1`
runs each task once.

**Evaluate a model (reference harness):**

```bash
harbor run -d long-horizon-terminal-bench \
  -a terminus-2 -m "your-provider/your-model" -k 1
```

**Bring your own agent:**

```bash
harbor run -d long-horizon-terminal-bench \
  --agent-import-path "path.to.agent:YourAgent" -k 1
```

This produces a job directory containing a `config.json` and a trial folder
with a `result.json` and the run artifacts (logs, terminal recordings, etc.).

---

## 2. Lay out your jobs (no fork needed)

> **Hugging Face has no forks.** Unlike GitHub, you do **not** fork the repo.
> Contributions are pushed to a special pull-request ref (`refs/pr/N`) directly on
> the dataset repo — the CLI in step 3 creates that PR branch for you.

Arrange your job folder(s) locally under this path:

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
      <trial-1>/result.json   # 1 trial/task, with artifacts
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

## 3. Open a pull request (no fork)

The simplest way is the Hugging Face CLI (or the `huggingface_hub` Python library) —
it uploads your folder to a fresh `refs/pr/N` branch **and** opens the PR in one step:

```bash
# one-time setup
pip install -U huggingface_hub
hf auth login                      # paste a token with write access

# upload your submission folder + open a PR (no fork, no manual branch)
hf upload IntelligenceLab/LHTB-leaderboard \
  submissions/long-horizon-terminal-bench/1.0/terminus-2__your-model \
  submissions/long-horizon-terminal-bench/1.0/terminus-2__your-model \
  --repo-type dataset --create-pr
```

`hf upload <repo-id> <local-path> <path-in-repo>` — the second path places the files
at the same location inside the dataset. The command prints the PR URL
(`.../refs%2Fpr%2FN`).

Python equivalent:

```python
from huggingface_hub import upload_folder

upload_folder(
    repo_id="IntelligenceLab/LHTB-leaderboard",
    repo_type="dataset",
    folder_path="submissions/long-horizon-terminal-bench/1.0/terminus-2__your-model",
    path_in_repo="submissions/long-horizon-terminal-bench/1.0/terminus-2__your-model",
    create_pr=True,
)
```

Prefer the browser? On the dataset page open **Community → New pull request**, then
add your files there — still no fork.

**To add more files to an existing PR** (say it is PR number `N`), push to the same
ref instead of opening a new one:

```bash
hf upload IntelligenceLab/LHTB-leaderboard <local-path> <path-in-repo> \
  --repo-type dataset --revision refs/pr/N
```

Once the PR is open:

- The validation bot auto-checks the submission and comments on any errors.
- Once it passes, a maintainer reviews the trajectories and merges.
- Your run is then imported to the board with a **verified** badge.

---

## Validation rules

A submission is valid only if **all** of the following hold:

- One trial per task (`-k 1`).
- `timeout_multiplier = 1.0` — no agent or verifier timeout overrides.
- No CPU / memory / storage overrides.
- Every trial has a valid `result.json` with run artifacts.
- Agents may **not** access the LHTB website or repository (reward hacking).
- Errored trials score **0**.

Scores are **mean reward** over the 46-task suite (errors = 0). A task counts as
*solved* at reward ≥ 0.95; the strict binary pass rate uses reward = 1.0.
