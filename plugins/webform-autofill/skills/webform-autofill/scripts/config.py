#!/usr/bin/env python3
"""Persistent config + data locations for the webform-autofill skill.

The data dir survives plugin installs/updates (the plugin code itself is copied
into a cache that gets overwritten on update, so config must live elsewhere):

    $CLAUDE_PLUGIN_DATA            if set (Claude Code's per-plugin data dir), else
    ~/.config/webform-autofill     a stable user-level fallback

Files inside the data dir:
    config.json   -> {"resume_xlsx": "/path/to/resume.xlsx"}   (the remembered path)
    resume.json   -> the dumped resume cache

CLI:
    python3 config.py get        # print saved Excel path (empty if none)
    python3 config.py set <path> # remember the Excel path
    python3 config.py datadir    # print the data dir
    python3 config.py cachefile  # print the cache file path
"""
import json
import os
import sys


def data_dir():
    d = os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.expanduser(
        "~/.config/webform-autofill"
    )
    os.makedirs(d, exist_ok=True)
    return d


def config_file():
    return os.path.join(data_dir(), "config.json")


def cache_file():
    return os.path.join(data_dir(), "resume.json")


def _load():
    p = config_file()
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def get_xlsx():
    """Resolve the Excel path: RESUME_XLSX env override wins, then saved config."""
    env = os.environ.get("RESUME_XLSX")
    if env:
        return os.path.expanduser(env)
    val = _load().get("resume_xlsx")
    return os.path.expanduser(val) if val else None


def set_xlsx(path):
    path = os.path.expanduser(path.strip())
    cfg = _load()
    cfg["resume_xlsx"] = path
    with open(config_file(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return path


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "get"
    if cmd == "get":
        print(get_xlsx() or "")
    elif cmd == "set":
        if len(sys.argv) < 3:
            sys.exit("usage: config.py set <path>")
        saved = set_xlsx(sys.argv[2])
        print(f"saved: {saved}\n-> {config_file()}")
    elif cmd == "datadir":
        print(data_dir())
    elif cmd == "cachefile":
        print(cache_file())
    else:
        sys.exit(f"unknown command: {cmd}")
