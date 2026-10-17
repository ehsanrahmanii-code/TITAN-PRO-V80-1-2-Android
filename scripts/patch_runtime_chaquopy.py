#!/usr/bin/env python3
"""Patch titan/runtime.py so Chaquopy AssetFinder can load layers."""
from pathlib import Path

p = Path("app/src/main/python/titan/runtime.py")
raw = p.read_text(encoding="utf-8")

raw = raw.replace(
    'LAYER_DIR = Path(__file__).resolve().parent / "layers"',
    'LAYER_DIR = Path(__file__).parent / "layers"  # Chaquopy: no resolve()',
)
raw = raw.replace(
    '"__file__": str(Path(entry_file).resolve()),',
    '"__file__": str(entry_file),',
)

old = (
    "        path = LAYER_DIR / f\"{name}.py\"\n"
    "        if not path.is_file():\n"
    "            raise FileNotFoundError(f\"TITAN layer missing: {path}\")\n"
    "        try:\n"
    "            src = path.read_text(encoding=\"utf-8\")\n"
    "            code = compile(src, str(path), \"exec\", flags=_FLAGS, dont_inherit=True)\n"
    "        except (OSError, SyntaxError) as exc:\n"
    "            raise RuntimeError(f\"Failed to load TITAN layer {name}: {exc}\") from exc"
)

new = (
    "        path = LAYER_DIR / f\"{name}.py\"\n"
    "        path_s = str(path)\n"
    "        try:\n"
    "            # Chaquopy AssetFinder: open() works; pathlib often fails\n"
    "            with open(path_s, \"r\", encoding=\"utf-8\") as _fp:\n"
    "                src = _fp.read()\n"
    "            code = compile(src, path_s, \"exec\", flags=_FLAGS, dont_inherit=True)\n"
    "        except FileNotFoundError as exc:\n"
    "            raise FileNotFoundError(f\"TITAN layer missing: {path_s}\") from exc\n"
    "        except (OSError, SyntaxError) as exc:\n"
    "            raise RuntimeError(f\"Failed to load TITAN layer {name}: {exc}\") from exc"
)

if old in raw:
    raw = raw.replace(old, new)
    print("runtime load-block patched")
elif "path_s = str(path)" in raw:
    print("runtime already patched")
else:
    raw2 = raw.replace(
        'src = path.read_text(encoding="utf-8")',
        'src = open(str(path), encoding="utf-8").read()',
    )
    if raw2 != raw:
        raw = raw2
        print("runtime read_text fallback patch")
    else:
        print("WARNING: could not patch runtime.py")

p.write_text(raw, encoding="utf-8")
core = Path("app/src/main/python/titan/layers/core/bootstrap_storage.py")
print("bootstrap_storage exists", core.is_file(), core.stat().st_size if core.is_file() else 0)
