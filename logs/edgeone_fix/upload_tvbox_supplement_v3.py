#!/usr/bin/env python3
"""补传 kstore /mytb/ v3: TVBox 剩余文件 (JSON/PY/XYQHiker/wex.jar/txt/png) + 开直链"""
import os, sys, subprocess, urllib.parse, base64, json, time
from pathlib import Path
import concurrent.futures

DL = Path('/tmp/tvbox_dl')
env = {}
for line in open('/workspace/.env', encoding='utf-8'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        env[k] = v.strip('"').strip("'")
USER, PASS, GH = env['KSTORE_DAV_USER'], env['KSTORE_DAV_PASS'], env['GH_TOKEN']
API_TOK = env['KSTORE_API_TOKEN']
DAV = 'https://webdav.kstore.space'

EXTRA = [
    'TVBox/JSON/哔哩合集.json', 'TVBox/JSON/采集静态.json',
    'TVBox/PY/九龙影视.py', 'TVBox/PY/新视觉.py', 'TVBox/PY/猎手影视.py',
    'TVBox/XYQHiker/BT天堂.json', 'TVBox/XYQHiker/奇趣影视.json',
    'TVBox/XYQHiker/电影港.json', 'TVBox/XYQHiker/电影牛.json', 'TVBox/XYQHiker/短剧屋.json',
    'TVBox/wex.jar', 'TVBox/bilibili.txt', 'TVBox/quark.txt',
    'TVBox/token.txt', 'TVBox/uc.txt', 'TVBox/.版本.png',
]
print(f'待补传 {len(EXTRA)} 个文件', flush=True)

def gh_api(path):
    for attempt in range(3):
        r = subprocess.run(['curl', '-s', '--max-time', '60',
            f'https://api.github.com/repos/hallabcdefg/mytb/contents/{urllib.parse.quote(path)}',
            '-H', f'Authorization: token {GH}'], capture_output=True, text=True)
        try:
            d = json.loads(r.stdout)
            if isinstance(d, dict) and 'content' in d:
                return d
        except Exception:
            pass
        time.sleep(2)
    return None

def dl(p):
    dest = DL / p
    dest.parent.mkdir(parents=True, exist_ok=True)
    d = gh_api(p)
    if not d:
        return (p, 'FAIL')
    try:
        data = base64.b64decode(d['content'])
        dest.write_bytes(data)
        return (p, 'OK')
    except Exception as e:
        return (p, f'ERR:{e}')

ok = fail = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    for p, code in ex.map(dl, EXTRA):
        if code == 'OK':
            ok += 1
        else:
            fail += 1
            print(f'  [DL FAIL {code}] {p}', flush=True)
print(f'下载: 成功 {ok} / 失败 {fail}', flush=True)
if fail:
    sys.exit(1)

def upload(item):
    src, rel = item
    url = f'{DAV}/mytb/{urllib.parse.quote(rel)}'
    r = subprocess.run(['curl', '-s', '--max-time', '180', '-o', '/dev/null', '-w', '%{http_code}',
                        '-u', f'{USER}:{PASS}', '-g', '-T', src, url],
                       capture_output=True, text=True)
    return (rel, r.stdout.strip())

up_ok = up_fail = 0
for rel, code in map(upload, [(str(DL / p), p) for p in EXTRA]):
    if code in ('200', '201', '204'):
        up_ok += 1
    else:
        up_fail += 1
        print(f'  [UP FAIL {code}] {rel}', flush=True)
print(f'上传: 成功 {up_ok} / 失败 {up_fail}', flush=True)
sys.exit(1 if up_fail else 0)
