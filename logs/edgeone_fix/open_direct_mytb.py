#!/usr/bin/env python3
"""给 kstore /mytb/ 下所有未开直链的文件开启直链"""
import subprocess, json, sys, time

env = {}
for line in open('/workspace/.env', encoding='utf-8'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        env[k] = v.strip('"').strip("'")
TOK = env['KSTORE_API_TOKEN']

def api(path, data):
    for attempt in range(3):
        args = ['curl', '-s', '--max-time', '30', '-X', 'POST',
                f'https://api.kstore.cc/api/v2{path}',
                '-H', f'Authorization: {TOK}']
        for k, v in data.items():
            args += ['-d', f'{k}={v}']
        r = subprocess.run(args, capture_output=True, text=True)
        try:
            return json.loads(r.stdout)
        except Exception:
            time.sleep(1)
    return None

def find_list(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ('list', 'files', 'records') and isinstance(v, list):
                return v
            r = find_list(v)
            if r:
                return r
    return None

all_files = []  # (id, path, direct)

def walk(path):
    d = api('/file/list', {'path': path, 'currentPage': 1, 'pageSize': 1000})
    items = find_list(d) or []
    for it in items:
        if it.get('isDir') or it.get('dir') or it.get('type') == 'dir' or (it.get('isFolder')):
            walk(f"{path}{it['name']}/")
        else:
            all_files.append((it.get('id') or it.get('fileId'), f"{path}{it['name']}",
                              it.get('direct', 0)))

walk('mytb/')
print(f'mytb/ 共 {len(all_files)} 个文件', flush=True)
closed = [f for f in all_files if f[2] in (0, '0', None)]
print(f'其中未开直链: {len(closed)} 个', flush=True)

ok = fail = 0
for fid, path, _ in closed:
    r = api('/file/direct', {'fileId': fid, 'direct': 1})
    code = (r or {}).get('code')
    if code in (0, 200, '0', '200'):
        ok += 1
    else:
        fail += 1
        print(f'  [FAIL] {path} -> {r}', flush=True)
print(f'\n开直链: 成功 {ok} / 失败 {fail}', flush=True)
sys.exit(1 if fail else 0)
