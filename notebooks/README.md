# Kaggle notebooks (GPU stages)

Wan 2.2 (moving shots) and ACE-Step 1.5 (music) need a GPU, so they run on Kaggle, not on your laptop. The local pipeline exports a job, the notebook runs it, and the pipeline imports the results. File names carry the cache contract, so nothing is matched by hand.

| Step | Moving shots | Music |
|---|---|---|
| 1. Export a job bundle | `py -m pipeline shots --export outputs/kaggle/shots_job` | `py -m pipeline music --export outputs/kaggle/music_job` |
| 2. Upload the folder as a **Kaggle dataset** | `job.json` + `keyframes/*.jpg` (16:9 crops, 1280×704) | `job.json` |
| 3. Run the notebook (GPU, internet on) | `wan22_shots.ipynb` | `acestep_score.ipynb` |
| 4. Download the zip, unzip into `outputs/kaggle_results/`, import | `py -m pipeline shots --import outputs/kaggle_results/shots` | `py -m pipeline music --import outputs/kaggle_results/music` |
| 5. Re-render | `py -m pipeline assemble --mode final` | set `score.chosen` in `storyboard.json`, then re-render |

- **What import does:** copies only files whose names match the *current* storyboard (an old clip from a superseded keyframe is reported and ignored), and merges the notebook's `runs_fragment.jsonl` into `runs.jsonl` without duplicates. Each line includes `gpu_s` for COSTS.md.
- **Fallbacks:** any shot without a clip keeps its Ken Burns move, and without a chosen score the film uses the placeholder pad. The film can always be rendered.
- **Status, run on Kaggle 2× T4 on 2026-11-25:**
  - `acestep_score.ipynb` **works**: 3 × 75 s candidates, about 60 s each.
  - `wan22_shots.ipynb` loads, then runs out of GPU memory at step 0 on a T4 (F-26, EXP-12). It needs a ≥ 24 GB GPU.
- **Environment rules learned the hard way (F-25):**
  - one Python 3.11 venv per model
  - `uv pip install --python <venv>/bin/python` on every install
  - pin the torch trio together (Wan via a constraints file)
  - `MPLBACKEND=Agg`
  - no flash-attn on a T4
  - every setup cell ends in an import-level smoke test
