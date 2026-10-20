#!/usr/bin/env python3
"""补传 kstore /mytb/: TVBox/(JS+XBPQ+spider.jar) + kstore路径版index.json"""
import os, sys, subprocess, urllib.parse, time
from pathlib import Path

DL = Path('/tmp/tvbox_dl')
env = {}
for line in open('/workspace/.env', encoding='utf-8'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        env[k] = v.strip('"').strip("'")
USER, PASS, GH = env['KSTORE_DAV_USER'], env['KSTORE_DAV_PASS'], env['GH_TOKEN']
DAV = 'https://webdav.kstore.space'

# 1. 从 GitHub 拉 TVBox/ 文件清单
r = subprocess.run(['curl', '-s', '--max-time', '30',
    'https://api.github.com/repos/hallabcdefg/mytb/git/trees/main?recursive=1',
    '-H', f'Authorization: token {GH}'], capture_output=True, text=True)
import json
tree = json.loads(r.stdout)['tree']
tv_paths = [t['path'] for t in tree
            if (t['path'].startswith('TVBox/JS/') or t['path'].startswith('TVBox/XBPQ/')
                or t['path'] == 'TVBox/spider.jar') and t['type'] == 'blob']
print(f'GitHub TVBox/ 共 {len(tv_paths)} 个文件')

# 2. 下载
DL.mkdir(parents=True, exist_ok=True)
dl_ok = dl_fail = 0
for p in tv_paths:
    dest = DL / p
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = 'https://raw.githubusercontent.com/hallabcdefg/mytb/main/' + urllib.parse.quote(p)
    rr = subprocess.run(['curl', '-sL', '--max-time', '60', '-o', str(dest),
                         '-w', '%{http_code}', url], capture_output=True, text=True)
    if rr.stdout.strip() == '200' and dest.exists() and dest.stat().st_size > 0:
        dl_ok += 1
    else:
        dl_fail += 1
        print(f'  [DL FAIL {rr.stdout.strip()}] {p}')
print(f'下载: 成功 {dl_ok} / 失败 {dl_fail}')
if dl_fail:
    sys.exit(1)

# 3. 上传清单: TVBox 全部 + kstore路径版 index.json
items = [(str(DL / p), p) for p in tv_paths]
items.append(('/tmp/index.kstore.json', 'index.json'))
print(f'\n待上传 {len(items)} 个文件 (含 index.json)')

def upload(item):
    src, rel = item
    url = f'{DAV}/mytb/{urllib.parse.quote(rel)}'
    r = subprocess.run(['curl', '-s', '--max-time', '300', '-o', '/dev/null', '-w', '%{http_code}',
                        '-u', f'{USER}:{PASS}', '-g', '-T', src, url],
                       capture_output=True, text=True)
    return (rel, r.stdout.strip())

# 串行上传防竞态
ok = fail = 0
fails = []
for rel, code in map(upload, items):
    if code in ('200', '201', '204'):
        ok += 1
    else:
        fail += 1
        fails.append((rel, code))
        print(f'  [UP FAIL {code}] {rel}')
print(f'\n上传完成: 成功 {ok} / 失败 {fail}')
sys.exit(1 if fail else 0)
