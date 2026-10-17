# -*- coding: utf-8 -*-
"""Bootstrap TITAN PRO V80.1.2 inside Chaquopy Android."""
from __future__ import annotations

import os
import sys
import threading
import time
import traceback
import urllib.request
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

_started = False
_lock = threading.Lock()
_last_error = ""
_error_log = None
_fallback_started = False


def _record_error(label: str) -> str:
    global _last_error
    details = traceback.format_exc()
    _last_error = f"{label}:\n{details}"
    try:
        if _error_log is not None:
            _error_log.parent.mkdir(parents=True, exist_ok=True)
            with _error_log.open("a", encoding="utf-8") as fp:
                fp.write("\n" + "=" * 70 + "\n" + _last_error + "\n")
    except Exception:
        pass
    print(_last_error, flush=True)
    return _last_error


def _materialize_titan_tree(files_dir: str, asset_python_root: Path) -> str:
    """Copy titan/ from AssetFinder onto real FS so layer loader can open files."""
    dest_root = Path(files_dir) / "titan_materialized"
    marker = dest_root / "titan" / "runtime.py"
    if marker.is_file() and marker.stat().st_size > 100:
        root = str(dest_root)
        if root not in sys.path:
            sys.path.insert(0, root)
        return root

    def _listdir(p: Path):
        try:
            return os.listdir(str(p))
        except Exception:
            return None

    def copy_tree(src: Path, dst: Path) -> int:
        names = _listdir(src)
        if names is None:
            return 0
        dst.mkdir(parents=True, exist_ok=True)
        n = 0
        for name in names:
            if name.startswith("__pycache__") or name.endswith(".pyc"):
                continue
            s = src / name
            d = dst / name
            child = _listdir(s)
            if child is not None:
                n += copy_tree(s, d)
            else:
                try:
                    with open(str(s), "rb") as f:
                        data = f.read()
                    d.parent.mkdir(parents=True, exist_ok=True)
                    with open(str(d), "wb") as f:
                        f.write(data)
                    n += 1
                except Exception:
                    pass
        return n

    src_titan = asset_python_root / "titan"
    copied = copy_tree(src_titan, dest_root / "titan")
    print(f"materialized titan files: {copied}", flush=True)
    root = str(dest_root)
    if root not in sys.path:
        sys.path.insert(0, root)
    return root


class _FallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        err = _last_error or "موتور کامل لود نشد"
        body = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TITAN V80</title>
<style>body{{font-family:system-ui;background:#0b1220;color:#e2e8f0;margin:0;padding:24px}}
h1{{color:#38bdf8}}pre{{white-space:pre-wrap;color:#f87171;background:#0f172a;padding:12px;border-radius:8px}}</style>
</head><body><h1>TITAN PRO V80.1.2</h1>
<p>موتور کامل بالا نیامد — حالت پشتیبان.</p>
<pre>{err}</pre></body></html>"""
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _start_fallback():
    global _fallback_started
    if _fallback_started:
        return
    _fallback_started = True
    try:
        server = HTTPServer(("127.0.0.1", 8080), _FallbackHandler)
        threading.Thread(target=server.serve_forever, name="titan-fallback", daemon=True).start()
    except Exception:
        _record_error("Fallback server failed")


def start_titan(files_dir: str) -> str:
    global _started, _error_log, _last_error
    with _lock:
        if _started:
            return "already-started"
        try:
            home_root = Path(files_dir).resolve()
            home = home_root / "MMM"
            home.mkdir(parents=True, exist_ok=True)
            for sub in ("data", "cache", "memory", "secrets"):
                (home / sub).mkdir(exist_ok=True)
            (home / "cache" / "tmp").mkdir(parents=True, exist_ok=True)
            _error_log = home / "data" / "android_bootstrap_errors.log"

            os.environ["TITAN_HOME"] = str(home_root)
            os.environ["TITAN_HOST"] = "127.0.0.1"
            os.environ["TITAN_PORT"] = "8080"
            os.environ["TITAN_OPEN_BROWSER"] = "0"
            os.environ["TITAN_ANALYSIS_ONLY"] = "1"
            os.environ["TITAN_LIVE_TRADING"] = "0"
            os.environ["TMPDIR"] = str(home / "cache" / "tmp")
            os.environ["TEMP"] = str(home / "cache" / "tmp")
            os.environ["TMP"] = str(home / "cache" / "tmp")
            os.environ["PYTHONUNBUFFERED"] = "1"

            asset_root = Path(__file__).parent
            if str(asset_root) not in sys.path:
                sys.path.insert(0, str(asset_root))

            mat = _materialize_titan_tree(str(home_root), asset_root)
            os.environ["TITAN_SRC_ROOT"] = mat

            def _run():
                try:
                    if mat and Path(mat, "titan", "runtime.py").is_file():
                        if mat not in sys.path:
                            sys.path.insert(0, mat)
                        entry = str(Path(mat) / "titan" / "runtime.py")
                        import importlib.util
                        spec = importlib.util.spec_from_file_location("titan_runtime_mat", entry)
                        mod = importlib.util.module_from_spec(spec)
                        assert spec.loader is not None
                        spec.loader.exec_module(mod)
                        load = mod.load
                    else:
                        from titan.runtime import load
                        entry = str(asset_root / "titan" / "runtime.py")

                    ns = load(entry, as_main=True)
                    app = ns.get("app") if isinstance(ns, dict) else None
                    if app is not None:
                        host = os.environ.get("TITAN_HOST", "127.0.0.1")
                        port = int(os.environ.get("TITAN_PORT", "8080"))
                        try:
                            from waitress import serve
                            serve(app, host=host, port=port, threads=4)
                        except Exception:
                            app.run(host=host, port=port, threaded=True, use_reloader=False)
                    else:
                        starter = None
                        if isinstance(ns, dict):
                            starter = ns.get("start_server") or ns.get("run_titan") or ns.get("main")
                        if callable(starter):
                            starter()
                        else:
                            raise RuntimeError("Engine loaded but no Flask app found")
                except Exception:
                    _record_error("TITAN runtime.load error")
                    _start_fallback()

            threading.Thread(target=_run, name="titan-v80-flask", daemon=True).start()
            _started = True
            return "started"
        except Exception:
            _record_error("TITAN bootstrap error")
            _start_fallback()
            _started = True
            return "fallback-error"


def wait_ready(url: str = "http://127.0.0.1:8080/", timeout: float = 180.0) -> bool:
    deadline = time.time() + float(timeout)
    urls = [
        "http://127.0.0.1:8080/",
        "http://127.0.0.1:8080/api/v80/health",
        "http://127.0.0.1:8080/health",
        "http://localhost:8080/",
    ]
    while time.time() < deadline:
        for u in urls:
            try:
                with urllib.request.urlopen(u, timeout=2.0) as resp:
                    if 200 <= getattr(resp, "status", 200) < 500:
                        return True
            except Exception:
                pass
        time.sleep(1.0)
    _start_fallback()
    return False


def last_error() -> str:
    return _last_error or ""
