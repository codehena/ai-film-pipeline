# Kaggle notebooks (GPU stages)

Wan 2.2 (moving shots) and ACE-Step 1.5 (music) need a GPU, so they run in Kaggle notebooks, not on your laptop.

Planned flow (built in Step 3):
1. `py -m pipeline shots` writes a job file listing only the shots whose inputs changed.
2. Upload the job file + keyframes to Kaggle, run the notebook.
3. The notebook writes clips and its own `runs.jsonl` lines (including GPU seconds).
4. Download them; `py -m pipeline shots` imports the clips and merges the log lines.
