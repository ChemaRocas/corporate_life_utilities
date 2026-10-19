# Background Remover

Removes the background from an image, or from every image in a folder, and saves each one as a
transparent PNG. Everything runs locally on your computer: your images are never uploaded anywhere.

For each image:
- a transparent copy is saved as `<original name>.png` in the output folder
- it keeps the exact width x height of the original (no resizing, no quality loss)
- the original is not touched

Works with `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tif` and `.tiff`.

## First-time setup (once per computer)

1. Install Python 3 if it's not there: https://www.python.org/downloads/
   (check with `python3 --version` on Mac, `py --version` on Windows)
2. Install the libraries:
   - Mac: `python3 -m pip install "rembg[cpu]" pillow`
   - Windows: `py -m pip install "rembg[cpu]" pillow`
3. Download the AI model (~900 MB, only once; after this the tool works with no internet):
   - Mac: `python3 remove_bg.py --download-model`
   - Windows: `py remove_bg.py --download-model`

   If you'll also use `--portrait` (see below), download that model too with
   `python3 remove_bg.py --download-model --portrait` (another ~900 MB).

   If you skip this step, the model is downloaded automatically the first time you run it.

## Running it

Open Terminal, go to this folder and run the script:

```bash
cd "<path to this Background Remover folder>"
python3 remove_bg.py
```

(On Windows use `py remove_bg.py`.) Tip: type `cd ` and drag the folder into the Terminal window.

Then:
1. Paste the path of an image or a folder (any format works: plain, quoted, or dragged in).
2. Press Enter to save the PNGs in a `no_background` folder next to it, or paste another output folder.

You can also skip the questions and pass the paths directly:

```bash
python3 remove_bg.py "photo.jpg"
python3 remove_bg.py "My Photos" -o "My Photos/cut outs"
python3 remove_bg.py "selfie.jpg" --portrait
```

## Which model?

By default it uses `birefnet-general`, which works on any kind of image (people, products, objects,
animals, logos) and leaves clean edges, with no white line around the outline. It takes about
14 seconds per image on a laptop.

For pictures of people, add `--portrait` to use `birefnet-portrait`. It's tuned for people and gave
slightly cleaner edges on our test portrait, in about the same time.

Results from one test picture (896x1200 drawing of a person):

| Model | Time | Edge |
|---|---|---|
| `birefnet-general` (default) | 14.1 s | clean |
| `birefnet-portrait` (`--portrait`) | 14.5 s | cleanest |
| `birefnet-general-lite` | 9.5 s | clean |
| `u2net` | 2.1 s | thin white line around the outline |

## Options

- `-o FOLDER`: where to save the PNGs (default: `no_background` next to the input)
- `--portrait`: use the model tuned for people (`birefnet-portrait`)
- `-m MODEL`: use any other model, for example `-m u2net` when you need speed more than clean edges.
  `python3 remove_bg.py --help` lists them all. Each new model is downloaded once the first time you use it.
- `--overwrite`: replace PNGs that already exist (by default they're skipped)
- `--download-model`: only download the model (add `--portrait` or `-m MODEL` for another one), for using the
  tool offline later

## Notes

- Safe to run again on the same folder: images whose PNG already exists are skipped.
- Only the images directly inside the folder are processed, not subfolders.
- Phone photos that are stored sideways are saved upright, the way you see them. In that case width and
  height are swapped compared to what the file stores internally, but no pixels are lost.
- If two images only differ in extension (`photo.jpg` and `photo.png`), they're saved as `photo_jpg.png`
  and `photo_png.png` so neither overwrites the other.
- iPhone `.heic` photos aren't supported: export them as JPG first.
- Models are stored in `~/.rembg` (or `~/.u2net` if you used rembg before).
