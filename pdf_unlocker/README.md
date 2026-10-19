# PDF Unlocker

Removes protection from every PDF in a folder (including all subfolders):
- **open passwords**: the PDF asks for a password every time you open it
- **restrictions**: the PDF opens, but copying text, editing or commenting is blocked

You're only asked for a password if at least one PDF actually needs one.

For each PDF that gets unlocked:
- an unlocked copy is saved next to it as `<original name> - unlocked.pdf`
- the locked original is deleted (on Google Drive it goes to the Drive trash, recoverable for 30 days)

PDFs with no protection, or with a password you don't have, are not touched. Your highlights,
drawings and comments are kept exactly as they are: only the protection is removed. At the end you get a
summary, and the option to try another password on the files that failed.

## First-time setup (once per computer)

1. Install Python 3 if it's not there: https://www.python.org/downloads/
   (check with `python3 --version` on Mac, `py --version` on Windows)
2. Install the PDF library:
   - Mac: `python3 -m pip install pikepdf`
   - Windows: `py -m pip install pikepdf`

## Running it

Open Terminal, go to this folder and run the script:

```bash
cd "<path to this PDF Unlocker folder>"
python3 unlock_pdfs.py
```

(On Windows use `py unlock_pdfs.py`.) Tip: type `cd ` and drag the folder into the Terminal window.

Then:
1. Paste the path of the folder with the PDFs (any format works: plain, quoted, or dragged in).
2. If any PDF needs a password, type it (it won't show while typing) and press Enter.

## Notes

- Safe to run again on the same folder: files ending in ` - unlocked` are skipped.
- If `X - unlocked.pdf` already exists, `X.pdf` is skipped and listed so nothing is overwritten.
- Scanned PDFs (pages that are just photos) still won't let you copy text: there is no text in them.
- If Google Drive files are "online-only", they get downloaded as they're processed, so it may be slower.
