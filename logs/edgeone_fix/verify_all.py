#!/usr/bin/env python3
"""全量验证 kstore /mytb/ 配置链路: index.json 引用 vs 实际可达性"""
import json, re, subprocess, urllib.parse, sys

BASE = 'https://20328.kstore.space/mytb'
env = {}
for line in open('/workspace/.env', encoding='utf-8'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        env[k] = v.strip('"').strip("'")

def http(url, max_time=25):
    r = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
                        '--max-time', str(max_time), '-g', url],
                       capture_output=True, text=True)
    return r.stdout.strip()

def get(url, max_time=30):
    r = subprocess.run(['curl', '-s', '--max-time', str(max_time), '-g', url],
                       capture_output=True, text=True)
    return r.stdout

# 1. index.json 本身
code = http(f'{BASE}/index.json')
print(f'[{"OK" if code=="200" else "FAIL"}] index.json -> HTTP {code}')
if code != '200':
    sys.exit(1)
raw = get(f'{BASE}/index.json')
d = json.loads(raw)
sites = d.get('sites', [])
print(f'  站数: {len(sites)} | 大小: {len(raw)}B')

# 2. 提取所有 kstore 本地引用
refs = set()
for s in sites:
    for key in ('api', 'ext', 'jar', 'spider'):
        v = s.get(key, '')
        if isinstance(v, str):
            for m in re.findall(re.escape(BASE) + r'/([^\s"\']+)', v):
                refs.add(m)
    # 弹幕/XBPQ 引用
    ext = s.get('ext', '')
    if isinstance(ext, str):
        for m in re.findall(r'https://20328\.kstore\.space/mytb/([^\s"\']+)', ext):
            refs.add(m)
print(f'kstore 本地引用: {len(refs)} 个')

# 3. spider
spider = d.get('spider', '')
print(f'  spider 字段: {spider[:80]}')
if 'kstore' in str(spider):
    c = http(str(spider).split(';')[0])
    print(f'[{"OK" if c=="200" else "FAIL"}] spider.jar -> HTTP {c}')

# 4. 逐个验证引用 (ref 已是 URL 编码形式, 禁止二次编码)
import urllib.parse as _up
ok = fail = 0
fails = []
for ref in sorted(refs):
    ref_clean = _up.unquote(ref)          # 先解码成中文名
    url = f'{BASE}/{_up.quote(ref_clean, safe="/")}'  # 再一次性正确编码
    c = http(url)
    if c == '200':
        ok += 1
    else:
        fail += 1
        fails.append((ref, c))
print(f'\n引用验证: 成功 {ok} / 失败 {fail}')
for r_, c in fails:
    print(f'  [FAIL {c}] {r_}')
sys.exit(1 if fail else 0)
