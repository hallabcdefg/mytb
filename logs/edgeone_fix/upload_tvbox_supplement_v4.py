#!/usr/bin/env python3
"""补传 kstore /mytb/ v4: DX 剩余 4 文件 (cheerio.min.js/img/index.json) + 开直链"""
import os, sys, subprocess, urllib.parse, base64, json, time
from pathlib import Path

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
    'DX/drpy_libs/cheerio.min.js',
    'DX/img/logo500x200-1.png',
    'DX/img/logo500x200.png',
    'DX/index.json',
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
        dest.write_bytes(base64.b64decode(d['content']))
        return (p, 'OK')
    except Exception as e:
        return (p, f'ERR:{e}')

ok = fail = 0
for p, code in map(dl, EXTRA):
    if code == 'OK':
        ok += 1
    else:
        fail += 1
        print(f'  [DL FAIL {code}] {p}', flush=True)
print(f'下载: 成功 {ok} / 失败 {fail}', flush=True)
if fail:
    sys.exit(1)

def upload(src, rel):
    url = f'{DAV}/mytb/{urllib.parse.quote(rel)}'
    r = subprocess.run(['curl', '-s', '--max-time', '180', '-o', '/dev/null', '-w', '%{http_code}',
                        '-u', f'{USER}:{PASS}', '-g', '-T', src, url],
                       capture_output=True, text=True)
    return r.stdout.strip()

up_ok = up_fail = 0
for p in EXTRA:
    code = upload(str(DL / p), p)
    if code in ('200', '201', '204'):
        up_ok += 1
    else:
        up_fail += 1
        print(f'  [UP FAIL {code}] {p}', flush=True)
print(f'上传: 成功 {up_ok} / 失败 {up_fail}', flush=True)
sys.exit(1 if up_fail else 0)
