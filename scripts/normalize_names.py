#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一站点名分隔符为 ┃，并清理冗余 [xxx] 方括号标签"""
import json, re, sys

PATH = '/workspace/tvbox-api-repo/mstore/allinone.json'

# 需要归一为 ┃ 的分隔符
SEPS = ['｜', '|', '·', '•', '・', '丨', '│', '┃', '∥', 'ᅵ']

def normalize_name(name: str) -> str:
    n = name
    # 1) 去掉 [直连] [js] [js版] 等方括号标签
    n = re.sub(r'\[(直连|js|JS|js版|爬虫|采集)\]', '', n)
    # 2) 把所有分隔符替换为 ┃
    for s in SEPS:
        n = n.replace(s, '┃')
    # 3) 合并连续 ┃
    n = re.sub(r'┃+', '┃', n)
    # 4) 去掉首尾 ┃ 和空白
    n = n.strip().strip('┃').strip()
    # 5) 去掉 ┃ 两侧多余空格
    n = re.sub(r'\s*┃\s*', '┃', n)
    return n

def main():
    d = json.load(open(PATH, encoding='utf-8'))
    sites = d['sites']
    changed = []
    seen = {}
    for s in sites:
        old = s['name']
        new = normalize_name(old)
        if new != old:
            changed.append((old, new))
            s['name'] = new
        # 重名检测
        seen.setdefault(new, []).append(s.get('key'))
    print(f"共 {len(sites)} 站，改名 {len(changed)} 个：")
    for o, n in changed:
        print(f"  {o}  ->  {n}")
    dups = {k: v for k, v in seen.items() if len(v) > 1}
    if dups:
        print("\n!! 重名：")
        for k, v in dups.items():
            print(f"  {k}  keys={v}")
    if '--write' in sys.argv:
        json.dump(d, open(PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print("\n已写回", PATH)
    else:
        print("\n(预览模式，加 --write 才写回)")

if __name__ == '__main__':
    main()
