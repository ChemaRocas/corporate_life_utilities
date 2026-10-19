"""
Remove the background from images and save them as transparent PNGs.

Works on a single image or on every image in a folder. Everything runs on this
computer: the AI model is downloaded once (the first time you use it) and after
that the script works fully offline. Your images are never uploaded anywhere.

Each result:
  - is saved as "<original name>.png" in the output folder
  - is a 4-channel RGBA PNG (transparent background)
  - has exactly the same width x height as the original

Run it with:
  python3 remove_bg.py                              (asks for the paths)
  python3 remove_bg.py photo.jpg                    (single image)
  python3 remove_bg.py "My Photos" -o "Cut outs"    (whole folder)
  python3 remove_bg.py selfie.jpg --portrait        (portrait model, for people)
  python3 remove_bg.py --help                       (all options)
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
    from rembg import new_session, remove
    from rembg.sessions import sessions_class
except ImportError:
    print("The 'rembg' and/or 'Pillow' libraries are not installed on this computer.")
    print("Install them once with this command, then run the script again:\n")
    print(f'    "{sys.executable}" -m pip install "rembg[cpu]" pillow\n')
    sys.exit(1)


DEFAULT_MODEL = "birefnet-general"    # clean edges on any kind of image
PORTRAIT_MODEL = "birefnet-portrait"  # used with --portrait
DEFAULT_OUTPUT_NAME = "no_background"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

# Models that take a plain image and return one mask. Others in rembg need
# extra inputs (sam, *_custom) or return several masks (u2net_cloth_seg).
SUPPORTED_MODELS = [
    "birefnet-general",   # clean edges on any kind of image, ~900 MB (default)
    "birefnet-portrait",  # tuned for people, cleanest edges on portraits, ~900 MB (--portrait)
    "birefnet-general-lite",  # a bit faster, ~220 MB
    "u2net",              # much faster (~2 s vs ~14 s), but leaves a thin white edge
    "u2netp",             # lightweight version of u2net, ~4 MB
    "u2net_human_seg",    # people
    "silueta",            # same as u2net but ~40 MB
    "isnet-general-use",  # general use, often cleaner edges on objects
    "isnet-anime",        # anime / illustrations
    "bria-rmbg",
]

# Result of processing an image
DONE = "done"
EXISTS = "exists"
ERROR = "error"


def local_models():
    """Model name -> session class, only for models that run on this computer.

    Any rembg model that sends images to an online service or needs an API key
    is left out, so nothing can leave the machine by accident.
    """
    classes = {cls.name(): cls for cls in sessions_class}
    return {
        name: classes[name]
        for name in SUPPORTED_MODELS
        if name in classes
        and classes[name].is_local()
        and not classes[name].requires_credentials()
    }


def clean_path(raw):
    """Turn a pasted path into a usable Path.

    Handles surrounding quotes ('...' or "..."), macOS Terminal drag-and-drop
    escapes (My\\ Photos), stray whitespace and a leading ~.
    """
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        text = text[1:-1]
    elif os.name != "nt":
        # On macOS/Linux a backslash escapes the next character ("\ " -> " ").
        # On Windows backslashes are path separators, so leave them alone.
        text = re.sub(r"\\(.)", r"\1", text)
    return Path(text).expanduser()


def default_output(source):
    base = source if source.is_dir() else source.parent
    return base / DEFAULT_OUTPUT_NAME


def ask_input():
    while True:
        raw = input("Paste the path of an image or a folder of images: ")
        if not raw.strip():
            continue
        path = clean_path(raw)
        if path.exists():
            return path
        print(f"  That path doesn't exist:\n  {path}\n")


def ask_output(source):
    default = default_output(source)
    raw = input(f"Output folder (press Enter for {default}): ")
    return clean_path(raw) if raw.strip() else default


def find_images(source):
    if source.is_file():
        return [source]
    return sorted(
        path
        for path in source.iterdir()
        if path.is_file()
        and path.suffix.lower() in IMAGE_EXTENSIONS
        and not path.name.startswith(".")
    )


def output_paths(images, output_dir):
    """Image -> output PNG path. "photo.jpg" and "photo.png" in the same folder
    would both become "photo.png", so those get the extension in the name."""
    stems = {}
    for image in images:
        stems.setdefault(image.stem.lower(), []).append(image)
    targets = {}
    for image in images:
        if len(stems[image.stem.lower()]) > 1:
            name = f"{image.stem}_{image.suffix.lstrip('.').lower()}.png"
        else:
            name = f"{image.stem}.png"
        targets[image] = output_dir / name
    return targets


def load_model(model):
    """Create the rembg session, downloading the model first if needed."""
    cls = local_models()[model]
    if cls.resolve_existing(f"{model}.onnx") is None:
        print(f"Downloading the '{model}' model (only this once, then it works offline)...")
    else:
        print(f"Loading the '{model}' model...")
    return new_session(model)


def remove_background(image_path, target, session, overwrite=False):
    """Save a transparent RGBA PNG of image_path at target. Returns (result, detail)."""
    if target.exists() and not overwrite:
        return EXISTS, target.name
    try:
        with Image.open(image_path) as original:
            # Phone photos are often stored sideways with a "rotate me" tag.
            # PNG has no such tag, so apply the rotation to keep it upright.
            image = ImageOps.exif_transpose(original)
            icc_profile = original.info.get("icc_profile")
            dpi = original.info.get("dpi")
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA")

        result = remove(image, session=session).convert("RGBA")
        if result.size != image.size:
            return ERROR, f"size changed from {image.size} to {result.size}"

        save_options = {"optimize": True}
        if icc_profile:
            save_options["icc_profile"] = icc_profile  # keep the original colors
        if dpi:
            save_options["dpi"] = dpi
        target.parent.mkdir(parents=True, exist_ok=True)
        result.save(target, "PNG", **save_options)
    except Exception as exc:
        return ERROR, str(exc)
    return DONE, f"{result.width}x{result.height}"


def process(images, output_dir, session, overwrite=False):
    results = {DONE: [], EXISTS: [], ERROR: []}
    targets = output_paths(images, output_dir)
    for i, image_path in enumerate(images, 1):
        print(f"  [{i}/{len(images)}] {image_path.name} ... ", end="", flush=True)
        result, detail = remove_background(image_path, targets[image_path], session, overwrite)
        label = {
            DONE: f"saved {targets[image_path].name} ({detail})",
            EXISTS: "skipped, output already exists (use --overwrite to replace it)",
            ERROR: f"ERROR ({detail})",
        }[result]
        print(label)
        results[result].append((image_path.name, detail))
    return results


def print_summary(results, output_dir):
    print("\n----- Summary -----")
    print(f"  Backgrounds removed:  {len(results[DONE])}")
    print(f"  Skipped (existed):    {len(results[EXISTS])}")
    print(f"  Errors:               {len(results[ERROR])}")
    if results[ERROR]:
        print("\n  Images with errors:")
        for name, detail in results[ERROR]:
            print(f"    - {name}  ->  {detail}")
    if results[DONE]:
        print(f"\n  Saved in: {output_dir}")
    print()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Remove image backgrounds locally and save transparent PNGs. "
        "Run with no arguments to be asked for the paths.",
    )
    parser.add_argument("input", nargs="?", help="an image, or a folder of images")
    parser.add_argument(
        "-o", "--output",
        help=f"folder for the PNGs (default: a '{DEFAULT_OUTPUT_NAME}' folder next to the input)",
    )
    model = parser.add_mutually_exclusive_group()
    model.add_argument(
        "--portrait", dest="model", action="store_const", const=PORTRAIT_MODEL,
        help=f"use the model tuned for people ({PORTRAIT_MODEL})",
    )
    model.add_argument(
        "-m", "--model", choices=list(local_models()),
        help=f"AI model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="replace PNGs that already exist",
    )
    parser.add_argument(
        "--download-model", action="store_true",
        help="only download the model (for later offline use) and exit",
    )
    args = parser.parse_args()
    args.model = args.model or DEFAULT_MODEL
    return args


def main():
    args = parse_args()

    if args.download_model:
        load_model(args.model)
        print("Model ready. The script can now run offline.")
        return

    print("=== Background Remover ===\n")
    if args.input:
        source = clean_path(args.input)
        if not source.exists():
            sys.exit(f"That path doesn't exist: {source}")
        output_dir = clean_path(args.output) if args.output else default_output(source)
    else:
        source = ask_input()
        output_dir = clean_path(args.output) if args.output else ask_output(source)

    if source.is_file() and source.suffix.lower() not in IMAGE_EXTENSIONS:
        sys.exit(f"Not a supported image ({', '.join(sorted(IMAGE_EXTENSIONS))}): {source}")
    images = find_images(source)
    if not images:
        print(f"\nNo images found in {source}")
        return

    print(f"\nFound {len(images)} image(s). Output folder: {output_dir}\n")
    session = load_model(args.model)
    print("\nRemoving backgrounds:")
    results = process(images, output_dir, session, args.overwrite)
    print_summary(results, output_dir)
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(1)
