# Kaggle notebooks (GPU stages)

Wan 2.2 (moving shots) and ACE-Step 1.5 (music) need a GPU, so they run on Kaggle, not on your laptop. The local pipeline exports a job, the notebook runs it, and the pipeline imports the results. File names carry the cache contract, so nothing is matched by hand.

| Step | Moving shots | Music |
|---|---|---|
| 1. Export a job bundle | `py -m pipeline shots --export outputs/kaggle/shots_job` | `py -m pipeline music --export outputs/kaggle/music_job` |
| 2. Upload the folder as a **Kaggle dataset** | `job.json` + `keyframes/*.jpg` (16:9 crops, 1280×704) | `job.json` |
| 3. Run the notebook (GPU, internet on) | `wan22_shots.ipynb` | `acestep_score.ipynb` |
| 4. Download `out.zip`, unzip, import | `py -m pipeline shots --import <folder>` | `py -m pipeline music --import <folder>` |
| 5. Re-render | `py -m pipeline assemble --mode final` | set `score.chosen` in `storyboard.json`, then re-render |

- **What import does:** copies only files whose names match the *current* storyboard (an old clip from a superseded keyframe is reported and ignored), and merges the notebook's `runs_fragment.jsonl` into `runs.jsonl` without duplicates. Each line includes `gpu_s` for COSTS.md.
- **Fallbacks:** any shot without a clip keeps its Ken Burns move, and without a chosen score the film uses the placeholder pad. The film can always be rendered.
- **Not verified from the development machine:**
  - Wan 2.2's CLI flags follow its README; the notebook prints `generate.py --help` first.
  - ACE-Step 1.5's exact entry point; the notebook prints the README's usage and isolates the call in one `generate()` function to adapt.

  Record any change in FAILURES.md.
