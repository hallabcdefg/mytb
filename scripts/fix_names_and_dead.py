#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一分隔符 + 去重 + 清理死站"""
import json, re, sys

PATH = '/workspace/tvbox-api-repo/mstore/allinone.json'
SEPS = ['｜', '|', '·', '•', '・', '丨', '│', '┃', '∥', 'ᅵ']

def normalize_name(name: str) -> str:
    n = name
    n = re.sub(r'\[(直连|js|JS|js版|爬虫|采集)\]', '', n)
    for s in SEPS:
        n = n.replace(s, '┃')
    n = re.sub(r'┃+', '┃', n)
    n = re.sub(r'\s*┃\s*', '┃', n)
    return n.strip().strip('┃').strip()

def main():
    d = json.load(open(PATH, encoding='utf-8'))
    sites = d['sites']

    # ---- 1. 统一名字 ----
    renamed = 0
    for s in sites:
        old = s['name']; new = normalize_name(old)
        if new != old: s['name'] = new; renamed += 1

    # ---- 2. 去重：同一名字保留"内容更优"的那个 ----
    # 优先级：jar版(csp_) > js版(./libs) ；但看球类以能出数据的为准
    def score(s):
        api = str(s.get('api', ''))
        k = str(s.get('key', ''))
        if k.startswith('csp_') or api.startswith('csp_'): return 3
        if api.startswith('./libs'): return 2
        if api.startswith('http'): return 2
        return 1

    seen = {}
    removed_dup = []
    result = []
    # 手工指定保留策略（key 为要保留的）
    KEEP_KEY = {
        '🐯┃虎牙┃直播': '虎牙直播js',      # 本地 ext 更稳
        '📽️聚短┃视频': 'csp_聚短视频',      # 二者 ext 相同，保留前者
        '🎧有声┃小说': '有声小说',          # jar 版更省依赖
    }
    for s in sites:
        nm = s['name']
        if nm in seen:
            a, b = seen[nm], s
            want = KEEP_KEY.get(nm)
            if want:
                keep = a if a.get('key') == want else b
                drop = b if keep is a else a
            else:
                keep, drop = (a, b) if score(a) >= score(b) else (b, a)
            seen[nm] = keep
            removed_dup.append((drop['name'], drop.get('key')))
        else:
            seen[nm] = s
    # 重建
    result = list(seen.values())
    # 保持原顺序
    order = {id(s): i for i, s in enumerate(sites)}
    result.sort(key=lambda s: order[id(s)])

    # ---- 3. 删除确认死站 ----
    DEAD_KEYS = {'wolong', 'csp_310直播', '310直播'}
    DEAD_NAME_SUBSTR = ['影视┃卧龙', '310┃看球']
    before = len(result)
    result = [s for s in result
              if s.get('key') not in DEAD_KEYS
              and not any(sub in s['name'] for sub in DEAD_NAME_SUBSTR)]
    removed_dead = before - len(result)

    d['sites'] = result
    print(f"改名 {renamed} | 去重删 {len(removed_dup)} {removed_dup} | 删死站 {removed_dead}")
    print(f"站点数 {len(sites)} -> {len(result)}")
    for s in result:
        if '卧龙' in s['name'] or '310' in s['name']:
            print("!!! 残留:", s['name'], s.get('key'))
    if '--write' in sys.argv:
        json.dump(d, open(PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print("已写回")
    else:
        print("(预览)")

if __name__ == '__main__':
    main()
