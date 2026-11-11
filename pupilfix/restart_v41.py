# -*- coding: utf-8 -*-
"""v41 重启验证：杀渲染 → 剥播放列表(备份) → 起 wallpaper32 → 查日志 → 恢复播放列表"""
import subprocess, time, json, os, sys
from datetime import datetime, timezone, timedelta

CFG = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\config.json"
WEROOT = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine"
LOG = os.path.join(WEROOT, "log.txt")
BACKUP = r"C:\Users\25485\.zcode\workspace\default\temp\we_v41_backup"

# 记录重启前日志行数（只看新增）
log_lines_before = sum(1 for _ in open(LOG, encoding="utf-8", errors="replace"))

for exe in ("wallpaper64.exe", "wallpaper32.exe", "wallpaperui.exe"):
    subprocess.run(["taskkill", "/F", "/IM", exe], capture_output=True)
time.sleep(6.5)

cfg = json.load(open(CFG, encoding="utf-8"))
mon0 = cfg["25485"]["general"]["wallpaperconfig"]["selectedwallpapers"]["Monitor0"]
playlist = mon0.pop("playlist", None)
os.makedirs(BACKUP, exist_ok=True)
if playlist is not None:
    json.dump(playlist, open(os.path.join(BACKUP, "playlist_Monitor0.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("playlist backed up,", len(playlist.get("items", [])), "items")

def write_cfg(cfg):
    tmp = CFG + ".tmp"
    json.dump(cfg, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent="\t")
    os.replace(tmp, CFG)

write_cfg(cfg)
time.sleep(4)
# 复验（被回写就重写，≤3 次）
for i in range(3):
    back = json.load(open(CFG, encoding="utf-8"))
    if "playlist" not in back["25485"]["general"]["wallpaperconfig"]["selectedwallpapers"]["Monitor0"]:
        break
    write_cfg(cfg)
    time.sleep(4)
print("selected now:", json.load(open(CFG, encoding="utf-8"))["25485"]["general"]["wallpaperconfig"]["selectedwallpapers"]["Monitor0"].get("file"))

subprocess.Popen([os.path.join(WEROOT, "wallpaper32.exe")], cwd=WEROOT)
print("renderer started, waiting 12s ...")
time.sleep(12)

# 查新增日志（log 时基 UTC）
new_errs = []
with open(LOG, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()[log_lines_before:]
for ln in lines:
    if "error" in ln.lower() or "failed" in ln.lower():
        new_errs.append(ln.strip())
print("new log lines:", len(lines))
for e in new_errs[:15]:
    print("ERR:", e)
if not new_errs:
    print("no new errors")

# 恢复播放列表（渲染运行中不读，轮换在下次 UI 重启后生效）
if playlist is not None:
    cfg2 = json.load(open(CFG, encoding="utf-8"))
    cfg2["25485"]["general"]["wallpaperconfig"]["selectedwallpapers"]["Monitor0"]["playlist"] = playlist
    write_cfg(cfg2)
    time.sleep(3)
    back = json.load(open(CFG, encoding="utf-8"))
    ok = "playlist" in back["25485"]["general"]["wallpaperconfig"]["selectedwallpapers"]["Monitor0"]
    print("playlist restored:", ok)
