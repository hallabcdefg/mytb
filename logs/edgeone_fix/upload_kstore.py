#!/usr/bin/env python3
"""把 FongMi 203站配置部署到 kstore WebDAV: mytb/ 目录"""
import os, sys, subprocess, urllib.parse, concurrent.futures

sys.path.insert(0, '/workspace')
from pathlib import Path

REPO = Path('/workspace/tvbox-api-repo')
KSTORE_BASE = 'https://20328.kstore.space/mytb'
DAV_HOST = 'https://webdav.kstore.space'

# 从 .env 读凭证
env = {}
for line in open('/workspace/.env', encoding='utf-8'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        env[k] = v.strip('"').strip("'")
USER, PASS = env.get('KSTORE_DAV_USER', ''), env.get('KSTORE_DAV_PASS', '')
assert USER and PASS, '缺少 kstore 凭证'

# 文件清单: (本地路径, 远程相对路径); index.json 用 kstore 路径版
files = [('/tmp/index.mstore.json', 'index.json'), ('TVBox/spider.jar', 'TVBox/spider.jar')]
files += [(f'DX/drpy_libs/{f}', f'DX/drpy_libs/{f}') for f in sorted(os.listdir(REPO/'DX/drpy_libs'))]
files += [(f'DX/drpy_js/{f}', f'DX/drpy_js/{f}') for f in sorted(os.listdir(REPO/'DX/drpy_js'))]

print(f'待上传 {len(files)} 个文件')

def upload(item):
    local_rel, remote_rel = item
    src = Path(local_rel) if local_rel.startswith('/') else REPO / local_rel
    if not src.exists():
        return (remote_rel, 'MISSING')
    url = f'{DAV_HOST}/mstore/mytb/{urllib.parse.quote(remote_rel)}'
    r = subprocess.run(
        ['curl', '-s', '--max-time', '120', '-o', '/dev/null', '-w', '%{http_code}',
         '-u', f'{USER}:{PASS}', '-g', '-T', str(src), url],
        capture_output=True, text=True)
    return (remote_rel, r.stdout.strip())

ok = fail = 0
fails = []
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
    for remote, code in ex.map(upload, files):
        if code in ('200', '201', '204'):
            ok += 1
        else:
            fail += 1
            fails.append((remote, code))
        if ok % 10 == 0 and fail == 0:
            print(f'  进度: {ok}/{len(files)}')

print(f'\n上传完成: 成功 {ok} / 失败 {fail}')
for r, c in fails:
    print(f'  [FAIL {c}] {r}')
sys.exit(1 if fail else 0)
