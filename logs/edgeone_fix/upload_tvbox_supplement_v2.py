#!/usr/bin/env python3
"""补传 kstore /mytb/ v2: Contents API 下载 + 串行 WebDAV 上传 + 开直链"""
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

def gh_api(path):
    for attempt in range(3):
        r = subprocess.run(['curl', '-s', '--max-time', '60',
            f'https://api.github.com/repos/hallabcdefg/mytb/contents/{urllib.parse.quote(path)}',
            '-H', f'Authorization: token {GH}',
            '-H', 'Accept: application/vnd.github+json'],
            capture_output=True, text=True)
        try:
            d = json.loads(r.stdout)
            if isinstance(d, dict) and 'content' in d:
                return d
        except Exception:
            pass
        time.sleep(2)
    return None

# 1. 列 TVBox/ 文件清单
r = subprocess.run(['curl', '-s', '--max-time', '30',
    'https://api.github.com/repos/hallabcdefg/mytb/git/trees/main?recursive=1',
    '-H', f'Authorization: token {GH}'], capture_output=True, text=True)
tree = json.loads(r.stdout)['tree']
tv_paths = [t['path'] for t in tree
            if (t['path'].startswith('TVBox/JS/') or t['path'].startswith('TVBox/XBPQ/')
                or t['path'] == 'TVBox/spider.jar') and t['type'] == 'blob']
print(f'GitHub TVBox/ 共 {len(tv_paths)} 个文件', flush=True)

# 2. Contents API 并行下载 (base64)
def dl(p):
    dest = DL / p
    if dest.exists() and dest.stat().st_size > 0:
        return (p, 'CACHED')
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
    for p, code in ex.map(dl, tv_paths):
        if code in ('OK', 'CACHED'):
            ok += 1
        else:
            fail += 1
            print(f'  [DL FAIL {code}] {p}', flush=True)
print(f'下载: 成功 {ok} / 失败 {fail}', flush=True)
if fail:
    sys.exit(1)

# 3. 上传: TVBox 全部 + kstore路径版 index.json (串行防竞态)
items = [(str(DL / p), p) for p in tv_paths]
items.append(('/tmp/index.kstore.json', 'index.json'))
print(f'\n待上传 {len(items)} 个文件 (含 index.json)', flush=True)

def upload(item):
    src, rel = item
    url = f'{DAV}/mytb/{urllib.parse.quote(rel)}'
    r = subprocess.run(['curl', '-s', '--max-time', '180', '-o', '/dev/null', '-w', '%{http_code}',
                        '-u', f'{USER}:{PASS}', '-g', '-T', src, url],
                       capture_output=True, text=True)
    return (rel, r.stdout.strip())

up_ok = up_fail = 0
fails = []
for i, (rel, code) in enumerate(map(upload, items), 1):
    if code in ('200', '201', '204'):
        up_ok += 1
    else:
        up_fail += 1
        fails.append((rel, code))
    if i % 10 == 0 or i == len(items):
        print(f'  上传进度: {i}/{len(items)}', flush=True)
print(f'\n上传完成: 成功 {up_ok} / 失败 {up_fail}', flush=True)
for r_, c in fails:
    print(f'  [UP FAIL {c}] {r_}', flush=True)
sys.exit(1 if up_fail else 0)
