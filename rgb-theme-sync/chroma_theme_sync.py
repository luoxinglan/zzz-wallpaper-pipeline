# -*- coding: utf-8 -*-
"""rgb-theme-sync：让全部 RGB 设备（雷蛇原生 + Chroma Link 第三方）显示当前壁纸的主题颜色。

链路：Wallpaper Engine(主题颜色 schemecolor, 本脚本只读其 config.json)
      -> Razer Chroma REST API -> 鼠标/底座/键盘 等 + Chroma Link(MSI 主板/七彩虹显卡)。

行为：
  - 每 2s 检查 WE config.json：当前壁纸切换或主题颜色修改 => 自动重推。
  - 每 5s 心跳保活 Chroma 会话；会话失效自动重建。
  - 单实例：占用本地端口 55329 作为锁。
"""
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request

WE_DIR = r'E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine'
CFG_PATH = os.path.join(WE_DIR, 'config.json')
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log.txt')
LOCK_PORT = 55329
POLL_SEC = 2
HEARTBEAT_SEC = 5
DEVICES = ('keyboard', 'mouse', 'mousepad', 'headset', 'keypad', 'chromalink')
DEFAULT_COLOR = (0.75, 0.2631, 0.35495)  # 找不到任何 schemecolor 时兜底
USER = '25485'

_log_f = None


def log(msg):
    global _log_f
    line = time.strftime('%m-%d %H:%M:%S ') + str(msg)
    try:
        if _log_f is None:
            _log_f = open(LOG_PATH, 'a', encoding='utf-8')
        if os.path.getsize(LOG_PATH) > 1_000_000:  # 超过1MB重新开始
            _log_f.close()
            _log_f = open(LOG_PATH, 'w', encoding='utf-8')
        _log_f.write(line + '\n')
        _log_f.flush()
    except OSError:
        pass


def http(method, url, payload=None, timeout=5):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(url, data=data, method=method,
                               headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        body = resp.read().decode('utf-8', 'ignore')
        return json.loads(body) if body else {}


def color_to_int(rgb):
    r, g, b = (max(0, min(255, int(round(c * 255)))) for c in rgb)
    return (b << 16) | (g << 8) | r  # Chroma: 0x00BBGGRR


def parse_color(s):
    parts = str(s).split()
    if len(parts) != 3:
        return None
    try:
        vals = [float(p) for p in parts]
    except ValueError:
        return None
    if any(v < 0 or v > 1 for v in vals):
        return None
    return tuple(vals)


def resolve_theme_color(cfg):
    """返回当前壁纸的有效主题颜色 (r,g,b 0-1)。"""
    try:
        sel = cfg[USER]['general']['wallpaperconfig']['selectedwallpapers']['Monitor0']
        file_path = sel.get('file', '')
        if not file_path:
            return None
        norm = file_path.replace('\\', '/')
        # 1) 用户在 WE 里给该壁纸设置过的覆盖值
        wprops = cfg[USER].get('wproperties', {})
        sc = wprops.get(norm, {}).get('Monitor0', {}).get('schemecolor')
        c = parse_color(sc) if sc else None
        if c:
            return c, 'override'
        # 2) 项目默认值
        proj_json = file_path.replace('/', os.sep).replace('scene.json', 'project.json')
        proj_json = proj_json.replace('index.html', 'project.json')
        if os.path.isfile(proj_json):
            with open(proj_json, encoding='utf-8') as f:
                pj = json.load(f)
            sc = pj.get('general', {}).get('properties', {}).get('schemecolor', {})
            c = parse_color(sc.get('value', ''))
            if c:
                return c, 'default'
        proj_dir = os.path.dirname(proj_json)
        log(f'warn: no schemecolor for {proj_dir}')
    except Exception as e:
        log(f'warn: resolve failed: {e!r}')
    return None


class ChromaSession:
    def __init__(self):
        self.uri = None
        self.last_push_color = None

    def init(self):
        payload = {
            'title': 'WE Theme Sync',
            'description': 'All RGB devices follow wallpaper theme color',
            'author': {'name': 'zcode', 'contact': 'local'},
            'device_supported': list(DEVICES),
            'category': 'application',
            'api_version': '1.0.0',
        }
        resp = http('POST', 'http://localhost:54235/razer/chromasdk', payload)
        self.uri = resp['uri']
        log(f'chroma session ok: {resp.get("sessionid")}')

    def push_static(self, color_int):
        for dev in DEVICES:
            http('POST', f'{self.uri}/{dev}',
                 {'effect': 'CHROMA_STATIC', 'param': {'color': color_int}})

    def heartbeat(self):
        http('PUT', f'{self.uri}/heartbeat')

    def close(self):
        try:
            http('DELETE', self.uri)
        except Exception:
            pass
        self.uri = None


def main():
    try:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(('127.0.0.1', LOCK_PORT))
        srv.listen(1)
    except OSError:
        log('another instance holds the lock, exit')
        return

    log('=== rgb-theme-sync start ===')
    sess = ChromaSession()
    cur_color = None        # 当前已推送的 Chroma 颜色 int
    cur_src = None
    last_cfg_mtime = None
    last_hb = 0.0

    while True:
        now = time.time()
        try:
            mtime = os.path.getmtime(CFG_PATH)
            if mtime != last_cfg_mtime:
                last_cfg_mtime = mtime
                with open(CFG_PATH, encoding='utf-8') as f:
                    cfg = json.load(f)
                res = resolve_theme_color(cfg)
                if res:
                    rgb, src = res
                    ci = color_to_int(rgb)
                    if ci != cur_color or src != cur_src:
                        log(f'color -> #{ci:06x} ({src})')
                        if sess.uri is None:
                            sess.init()
                            sess.last_push_color = None
                        sess.push_static(ci)
                        sess.last_push_color = ci
                        cur_color, cur_src = ci, src
            if sess.uri is not None and now - last_hb >= HEARTBEAT_SEC:
                sess.heartbeat()
                last_hb = now
        except urllib.error.HTTPError as e:
            log(f'http {e.code}, reinit session')
            sess.uri = None
            time.sleep(3)
        except Exception as e:
            log(f'error: {e!r}')
            sess.uri = None
            time.sleep(3)
        time.sleep(POLL_SEC)


if __name__ == '__main__':
    main()
