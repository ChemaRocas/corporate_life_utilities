"""
Unlock PDFs in a folder (and all its subfolders).

Removes both kinds of protection:
  - an open password (the PDF asks for a password every time you open it)
  - restrictions (the PDF opens, but copying text, editing or commenting is blocked)

For every PDF that gets unlocked:
  - an unlocked copy is saved as "<original name> - unlocked.pdf" in the same folder
  - the protected original is deleted (on Google Drive it goes to the Drive trash)

PDFs with no protection, or whose password you don't have, are left untouched.
You're only asked for a password if at least one PDF actually needs one.

Run it with:  python3 unlock_pdfs.py
"""

import getpass
import os
import re
import sys
import tempfile
from pathlib import Path

try:
    import pikepdf
except ImportError:
    print("The 'pikepdf' library is not installed on this computer.")
    print("Install it once with this command, then run the script again:\n")
    print(f'    "{sys.executable}" -m pip install pikepdf\n')
    sys.exit(1)


SUFFIX = " - unlocked"

# What a PDF looks like before processing
FREE = "free"                # no password, no restrictions
RESTRICTED = "restricted"    # opens freely, but copy/edit/comment is blocked
LOCKED = "locked"            # needs a password to open

# Result of processing a PDF
UNLOCKED = "unlocked"
RESTRICTIONS_REMOVED = "restrictions_removed"
NOTHING_TO_DO = "nothing_to_do"
WRONG_PASSWORD = "wrong_password"
TARGET_EXISTS = "target_exists"
ORIGINAL_NOT_DELETED = "original_not_deleted"
ERROR = "error"

LABELS = {
    UNLOCKED: "password removed",
    RESTRICTIONS_REMOVED: "restrictions removed",
    WRONG_PASSWORD: "wrong password",
    TARGET_EXISTS: "skipped, unlocked copy already exists",
    ORIGINAL_NOT_DELETED: "unlocked, but original could NOT be deleted",
    ERROR: "ERROR",
}


def clean_path(raw):
    """Turn a pasted path into a usable Path.

    Handles surrounding quotes ('...' or "..."), macOS Terminal drag-and-drop
    escapes (My\\ Drive), stray whitespace and a leading ~.
    """
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        text = text[1:-1]
    elif os.name != "nt":
        # On macOS/Linux a backslash escapes the next character ("\ " -> " ").
        # On Windows backslashes are path separators, so leave them alone.
        text = re.sub(r"\\(.)", r"\1", text)
    return Path(text).expanduser()


def ask_folder():
    while True:
        raw = input("Paste the folder path: ")
        if not raw.strip():
            continue
        folder = clean_path(raw)
        if folder.is_dir():
            return folder
        print(f"  That folder doesn't exist or isn't a folder:\n  {folder}\n")


def ask_password(prompt="Password (typing is hidden): "):
    while True:
        password = getpass.getpass(prompt)
        if password:
            return password
        print("  The password can't be empty.")


def find_pdfs(folder):
    pdfs = []
    for path in folder.rglob("*"):
        if path.suffix.lower() != ".pdf" or not path.is_file():
            continue
        if path.name.startswith((".", "~$")):  # hidden/system/temp files
            continue
        if path.stem.endswith(SUFFIX):  # already produced by this script
            continue
        pdfs.append(path)
    return sorted(pdfs)


def classify(pdf_path):
    """Returns (FREE | RESTRICTED | LOCKED | ERROR, detail)."""
    try:
        with pikepdf.open(pdf_path) as pdf:
            # Encrypted but opened without a password = only restrictions.
            return (RESTRICTED if pdf.is_encrypted else FREE), ""
    except pikepdf.PasswordError:
        return LOCKED, ""
    except Exception as exc:
        return ERROR, str(exc)


def unlock(pdf_path, password=None):
    """Save an unprotected copy as '<name> - unlocked.pdf' and delete the original.

    Use password=None for PDFs that only have restrictions.
    Returns (result, detail).
    """
    target = pdf_path.with_name(pdf_path.stem + SUFFIX + pdf_path.suffix)
    if target.exists():
        return TARGET_EXISTS, target.name

    # 1. Open and save an unencrypted copy to a temp file in the same folder.
    fd, tmp_name = tempfile.mkstemp(
        prefix=".unlocking-", suffix=".pdf", dir=pdf_path.parent
    )
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        try:
            with pikepdf.open(pdf_path, password=password or "") as pdf:
                page_count = len(pdf.pages)
                # Only the protection is removed; content, highlights, drawings
                # and metadata are kept exactly as they are.
                pdf.save(tmp_path, encryption=False, fix_metadata_version=False)
        except pikepdf.PasswordError:
            return WRONG_PASSWORD, ""

        # 2. Check the temp file opens freely, has no restrictions and is complete.
        with pikepdf.open(tmp_path) as check:
            if check.is_encrypted or len(check.pages) != page_count:
                return ERROR, "the unlocked copy failed verification"

        # 3. Only now put the new file in place and delete the original.
        os.replace(tmp_path, target)
    except Exception as exc:
        return ERROR, str(exc)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    try:
        pdf_path.unlink()
    except Exception as exc:
        return ORIGINAL_NOT_DELETED, str(exc)
    return (UNLOCKED if password else RESTRICTIONS_REMOVED), ""


def process(pdfs, folder, results, password=None):
    for i, pdf_path in enumerate(pdfs, 1):
        rel = pdf_path.relative_to(folder)
        print(f"  [{i}/{len(pdfs)}] {rel} ... ", end="", flush=True)
        result, detail = unlock(pdf_path, password)
        print(LABELS[result] + (f" ({detail})" if detail else ""))
        results.setdefault(result, []).append((rel, detail))


def print_summary(results):
    count = lambda key: len(results.get(key, []))
    print("\n----- Summary -----")
    print(f"  Password removed:         {count(UNLOCKED)}")
    print(f"  Restrictions removed:     {count(RESTRICTIONS_REMOVED)}")
    print(f"  Already unprotected:      {count(NOTHING_TO_DO)}")
    print(f"  Wrong password:           {count(WRONG_PASSWORD)}")
    print(f"  Unlocked copy existed:    {count(TARGET_EXISTS)}")
    print(f"  Errors:                   {count(ERROR)}")
    if count(ORIGINAL_NOT_DELETED):
        print(f"  Unlocked, original kept:  {count(ORIGINAL_NOT_DELETED)}")

    sections = [
        (WRONG_PASSWORD, "Files where the password didn't work:"),
        (TARGET_EXISTS, "Skipped because an unlocked copy already exists (check them manually):"),
        (ORIGINAL_NOT_DELETED, "Unlocked, but the protected original is still there (delete it manually):"),
        (ERROR, "Files with errors:"),
    ]
    for key, title in sections:
        if results.get(key):
            print(f"\n  {title}")
            for rel, detail in results[key]:
                print(f"    - {rel}" + (f"  ->  {detail}" if detail else ""))
    print()


def main():
    print("=== PDF Unlocker ===\n")
    folder = ask_folder()
    pdfs = find_pdfs(folder)
    if not pdfs:
        print("\nNo PDFs to process in that folder.")
        return

    print(f"\nChecking {len(pdfs)} PDF(s) in {folder} ...")
    groups = {FREE: [], RESTRICTED: [], LOCKED: []}
    results = {}
    for pdf_path in pdfs:
        status, detail = classify(pdf_path)
        if status == ERROR:
            results.setdefault(ERROR, []).append((pdf_path.relative_to(folder), detail))
        else:
            groups[status].append(pdf_path)
    results[NOTHING_TO_DO] = [(p.relative_to(folder), "") for p in groups[FREE]]

    print(f"  Need a password:              {len(groups[LOCKED])}")
    print(f"  Copy/edit restrictions only:  {len(groups[RESTRICTED])}")
    print(f"  Already unprotected:          {len(groups[FREE])}")

    if groups[RESTRICTED]:
        print("\nRemoving restrictions (no password needed):")
        process(groups[RESTRICTED], folder, results)

    pending = groups[LOCKED]
    if pending:
        print()
        password = ask_password()
        while True:
            print("\nRemoving passwords:")
            results.pop(WRONG_PASSWORD, None)
            process(pending, folder, results, password)

            pending = [folder / rel for rel, _ in results.get(WRONG_PASSWORD, [])]
            if not pending:
                break
            again = input(f"\nTry another password on the {len(pending)} file(s) that failed? (y/n): ")
            if again.strip().lower() not in ("y", "yes", "s", "si", "sí"):
                break
            password = ask_password("New password (typing is hidden): ")

    print_summary(results)
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(1)
