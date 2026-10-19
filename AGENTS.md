# AGENTS.md

Notes for coding agents working in this repo. Humans: [README.md](README.md) is the
entry point, and each tool's own README explains how to use it.

## What this is

Small tools that run locally on Josemaria's computer, to stop handing files to websites
that keep your data and to get rid of repetitive tasks. Each tool lives in its own
folder and is a single script run with `python3`:

- `pdf_unlocker/`: removes passwords and copy/edit restrictions from every PDF in a folder.
- `background_remover/`: removes image backgrounds and saves transparent PNGs at the
  original resolution.

The people running them are not programmers. A tool that's correct but confusing to run
is not done.

## Setup

Python 3.12+. Install only the libraries of the tool you're working on:

```bash
python3 -m pip install ".[pdf]"          # pdf_unlocker
python3 -m pip install ".[background]"   # background_remover
python3 -m pip install ".[data]"         # pandas, numpy, matplotlib, seaborn
```

Each tool folder also has a `requirements.txt`, which its README uses, for someone who
only copies that one folder.

## Commands

```bash
python3 background_remover/remove_bg.py <image-or-folder> [-o OUTPUT]   # default model: birefnet-general
python3 background_remover/remove_bg.py <image> --portrait              # model tuned for people
python3 background_remover/remove_bg.py --download-model [--portrait]   # fetch a model once, then offline
python3 pdf_unlocker/unlock_pdfs.py                                     # interactive; asks folder + password
python3 -m py_compile */*.py                                            # syntax check every tool
```

## Rules that keep your files and data safe

These tools touch personal and work files (PDFs from courses, photos), so:

- **Everything runs locally.** No tool may upload a file or call an online API to do its
  work. Downloading a model or library once is fine; sending the user's files anywhere is
  not. `background_remover` filters out every rembg model that isn't local
  (`local_models()`); keep it that way when adding models.
- **Never lose an original.** `pdf_unlocker` deletes the locked PDF only after the
  unlocked copy has been written to a temp file, re-opened and checked (no encryption,
  same page count), and moved into place. `background_remover` never touches the input.
  A new tool that replaces files follows the same order: write, verify, then delete.
- **Never overwrite silently.** Existing outputs are skipped and reported (`--overwrite`
  is opt-in). Name collisions get a distinct name, not a replacement.
- **Don't run `pdf_unlocker` on a real folder to test it.** It deletes originals (to the
  Drive trash on Google Drive). Test on copies in a scratch folder.
- **Never commit the user's files.** No PDFs, images, or outputs (`no_background/`,
  `* - unlocked.pdf`) go into git.
- **Never type a password for the user.** `pdf_unlocker` asks for it with hidden input;
  the human types it.

## Paths

No hardcoded personal paths in code. Every tool takes its input path at runtime, either as
an argument or pasted at a prompt, and cleans it with `clean_path()`, which handles quotes,
macOS drag-and-drop escapes (`My\ Drive`) and `~`. Default outputs go next to the input
(`no_background/` beside the image or folder; `<name> - unlocked.pdf` beside the PDF).

Models downloaded by rembg live in `~/.rembg/models/` (or `~/.u2net` from older versions),
outside the repo.

## Layout

```
README.md              list of tools, one line each
AGENTS.md              this file
pyproject.toml         Python version + each tool's libraries as an extra
.claude/settings.json  git restrictions for agents (committed)
pdf_unlocker/
  unlock_pdfs.py       the tool
  README.md            how to set it up and run it, for non-programmers
  requirements.txt
background_remover/
  remove_bg.py
  README.md
  requirements.txt
```

Adding a tool means: a new folder with those three files, a line in the root README's
**Tools** list, and an extra in `pyproject.toml`.

## Conventions

**Each tool is self-contained.** No shared module between tools, even where code is
duplicated (`clean_path()` is in both). Someone should be able to copy one folder and
run it. Don't factor shared code out.

**Written for non-programmers.** That shows up as:

- Run with no arguments → the tool asks for what it needs (a pasted path, Enter for the
  default). Arguments are a shortcut, not a requirement.
- A missing library prints the exact install command, using `sys.executable`, and exits.
  No traceback.
- Progress per file (`[3/7] file.pdf ... done`), then a summary with counts and a list of
  anything that failed or was skipped, and why.
- Ctrl+C prints "Cancelled." instead of a traceback.
- Each README covers first-time setup on Mac and Windows, how to run it, and notes on edge
  cases, in plain language.

**Safe to run twice.** Re-running a tool on the same folder skips what's already done
instead of redoing or duplicating it.

**Module docstrings say what the tool does and how to run it**; comments explain *why*
(why the EXIF rotation is applied, why a model is excluded), not what the next line does.

**English** for code, comments, READMEs and console output.

## Tests

There is no automated test suite. Each tool was checked by hand, on sample files in a
scratch folder, never on real data:

- `background_remover` (2026-10-19): single image, a folder, the interactive prompts, a
  re-run (everything skipped), and a run with the network deliberately blocked to prove it's
  offline. Every output checked as a 4-channel RGBA PNG with the input's exact width x
  height. Inputs covered: an odd size, palette PNG, CMYK JPEG, a sideways-tagged phone
  photo, and two files differing only by extension. Models compared on one 896x1200
  picture: birefnet-general 14.1 s, birefnet-portrait 14.5 s, birefnet-general-lite 9.5 s,
  u2net 2.1 s (u2net leaves a thin white edge).
- `pdf_unlocker`: no recorded test. It has been used on real course folders.

When you change a tool: run `python3 -m py_compile` on it, then run it on copies of sample
files and check the output, the summary, and a re-run. If you add automated tests, use
`pytest` with `tmp_path`, generate the sample files inside the test, and don't add tests
that download models or call online services.

## Git

`git add`, `commit`, `push`, `rm`, `reset`, `checkout`, `restore` and `clean` are denied
by `.claude/settings.json`. That's deliberate: Josemaria commits. Stage nothing, and
don't hand out commit commands unless asked.
