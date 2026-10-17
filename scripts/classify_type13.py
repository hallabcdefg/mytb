#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主线 allinone.json 站点分类整理
==============================
1. type=1（API 直连）：名字标注"直连"，清掉误写的"采集"
2. type=3（采集）：名字统一追加"┃采集"
3. 排序：豆瓣集合页(豆)第一 → 直连组 → 采集组（组内保持原相对顺序）
"""
import json, shutil, sys
from datetime import datetime

CFG = 'mstore/allinone.json'
BAK = f'logs/config_backup/allinone.json.before_直连采集分类_{datetime.now():%Y%m%d_%H%M%S}.json'

def rename(name, t):
    if t == 1:
        n = name.replace('┃采集', '┃直连')
        if '采集' in n:
            n = n.replace('采集', '┃直连')
        if '直连' not in n:
            n = n + '┃直连'
        return n
    else:  # t == 3
        return name if '采集' in name else name + '┃采集'

d = json.load(open(CFG, encoding='utf-8'))
sites = d['sites']

douban = next((s for s in sites if s.get('key') == '豆'), None)
assert douban is not None, '未找到豆瓣集合页(key=豆)'
direct = [s for s in sites if s.get('type') == 1]
collect = [s for s in sites if s.get('type') == 3 and s is not douban]
assert 1 + len(direct) + len(collect) == len(sites), '存在 type 非 1/3 的站点'

for s in direct + collect + [douban]:
    s['name'] = rename(s['name'], s['type'])

d['sites'] = [douban] + direct + collect

shutil.copy(CFG, BAK)
open(CFG, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1))
print(f'备份 -> {BAK}')
print(f'完成: 豆瓣1 + 直连{len(direct)} + 采集{len(collect)} = {len(d["sites"])} 站')
