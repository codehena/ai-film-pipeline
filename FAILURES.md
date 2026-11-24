# Failures

What broke, what I tried, what fixed it (or how I worked around it). Write these down as they happen.

## Template

### F-01: short title
- **Date:**
- **Stage / model:**
- **What happened:** (paste the error message)
- **What I tried:**
- **What fixed it / workaround:**
- **Lesson:**

---

### F-01: Git and FFmpeg not installed on the development machine
- **Date:** 2026-11-25
- **Stage / model:** setup
- **What happened:** `git` and `ffmpeg` were not found in PowerShell; `python` opened the Microsoft Store prompt instead of running Python.
- **What I tried:** checked with `Get-Command`; found Python 3.13 available through the `py` launcher.
- **What fixed it / workaround:** use `py` instead of `python`; install Git and FFmpeg with `winget`.
- **Lesson:** check the toolchain before writing pipeline code; document `py` vs `python3` in the README.

---

### F-02: Git commit failed due to missing author identity
- **Date:** 2026-11-25
- **Stage / model:** setup / git
- **What happened:** `git commit` failed with `Author identity unknown` and `fatal: unable to auto-detect email address` in PowerShell.
- **What I tried:** ran `git commit -m "chore: add verified pipeline skeleton and offline tests"` after staging files.
- **What fixed it / workaround:** set global Git `user.name` and `user.email` with `git config --global`, then re-ran `git commit` and verified a clean working tree with `git status`.
- **Lesson:** configure Git author identity right after initializing a repository before making the first commit.

---

### F-03: Rotated Cloudflare Workers AI token after early screenshot exposure
- **Date:** 2026-11-25
- **Stage / model:** setup / cloudflare-workers-ai
- **What happened:** an early Cloudflare Workers AI token value was exposed during setup prior to running live pipeline checks.
- **What I tried:** checked `.gitignore` / `.env` handling so secrets stay local and out of version control.
- **What fixed it / workaround:** revoked the exposed token, generated a scoped replacement token, saved it in `.env`, and verified environment presence without printing secret values.
- **Lesson:** rotate any exposed credential immediately rather than reusing it, and verify `.env` stays ignored before live API calls.