#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox 配置站点分组归类脚本
==========================
把配置里的站点按「内容大类 + jar 归属」分组排序，并给站名加可读标签。

重要保护（踩过的坑）：
  带 indexs 标记 / 名称含"聚合""首页""切源"的站点是 **TVBox 首页聚合页入口**，
  不是普通站点 —— 必须置顶且保持原名不加标签，否则首页合集会丢失。

用法：
  python3 scripts/group_sites.py                     # 处理默认两份配置
  python3 scripts/group_sites.py mstore/xxx.json     # 指定文件
"""

import os
import re
import sys
import json
import zipfile
import struct
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# jar 标识 -> 本地 jar 文件（用于校验类名命中，可选）
JAR_FILES = {
    '饭太硬': '/tmp/jars/fty.jar', '梵泰英': '/tmp/jars/fantaiying.jar',
    '光速': '/tmp/jars/guangge.jar', '肥猫': '/tmp/jars/feimao.jar',
    '多多': '/tmp/jars/duoduo.jar', 'liu673cn': '/tmp/jars/liu.jar',
    'fan.txt(FTY)': '/tmp/jars/fan.jar',
}
JAR_PAT = [
    ('饭太硬', 'jars/饭太硬.jar'), ('fan.txt(FTY)', 'qist/jar/fan.txt'),
    ('梵泰英', 'jars/fantaiying.jar'), ('光速', 'jars/guangge.jar'),
    ('肥猫', 'jars/feimao.jar'), ('多多', 'jars/duoduo.jar'),
    ('liu673cn', 'liu673cn/fty.jar'),
]

K4 = ['4k', '2160', 'uhd', 'hdr', '杜比', '蓝光', '高清', '8k', '原画', '超清']
LIVE = ['直播', '电视', '卫视', '央视', 'cctv', '体育', '赛事', '虎牙', '斗鱼',
        'huya', 'douyu', '频道', '轮播', 'live']
NETDISK = ['网盘', '云盘', '夸克', '阿里', '天翼', '电信', 'alist', '迅雷', '115',
           'quark', 'mogg', 'pansou', '盘搜', '我的云盘', '盘社']

ORDER = ['网盘', '4K', '直播', '直连', '饭太硬', '梵泰英', '光速', '肥猫', '多多',
         'liu673cn', 'fan.txt(FTY)', 'JS', 'PY', '其他']
LABEL = {
    '网盘': '【网盘】', '4K': '【4K】', '直播': '【直播】', '直连': '【直连】',
    '饭太硬': '【饭太硬】', '梵泰英': '【梵泰英】', '光速': '【光速】', '肥猫': '【肥猫】',
    '多多': '【多多】', 'liu673cn': '【Liu673】', 'fan.txt(FTY)': '【FTY】',
    'JS': '【JS】', 'PY': '【PY】', '其他': '【其他】',
}


def classes_of(path):
    cs = set()
    try:
        z = zipfile.ZipFile(path)
    except Exception:
        return cs
    for n in z.namelist():
        if not n.endswith('.dex'):
            continue
        d = z.read(n)
        if len(d) < 0x44:
            continue
        sz = struct.unpack('<I', d[0x38:0x3C])[0]
        off = struct.unpack('<I', d[0x3C:0x40])[0]
        for i in range(sz):
            o = struct.unpack('<I', d[off + i * 4:off + i * 4 + 4])[0]
            s = o
            sh = 0
            ln = 0
            while True:
                b = d[s]
                ln |= (b & 0x7F) << sh
                s += 1
                if not (b & 0x80):
                    break
                sh += 7
            try:
                c = d[s:s + ln].decode('utf-8', 'ignore')
            except Exception:
                continue
            if c.startswith('Lcom/github/catvod/spider/') and c.endswith(';'):
                cs.add(c)
    return cs


CLS = {k: classes_of(v) for k, v in JAR_FILES.items()}


def jarof(s, cfg):
    u = str(s.get('jar', '')) or str(cfg.get('spider', ''))
    for tag, pat in JAR_PAT:
        if pat in u:
            return tag
    return 'liu673cn'


def bare_name(s):
    """去掉已加的【xxx】标签，保证重复运行不会叠加。"""
    return re.sub(r'^【[^】]*】', '', str(s.get('name', '')))


def is_home(s):
    """首页/聚合页入口：带 indexs 标记，或名称含 聚合/首页/切源。"""
    if s.get('indexs') not in (None, 0, ''):
        return True
    b = (str(s.get('key', '')) + ' ' + bare_name(s)).lower()
    return any(w in b for w in ['聚合', '首页', '切源'])


def group_of(s, cfg):
    k = str(s.get('key', ''))
    n = bare_name(s)
    api = str(s.get('api', ''))
    t = s.get('type')
    blob = json.dumps(s, ensure_ascii=False).lower()
    bare = (k + ' ' + n + ' ' + api).lower()
    if any(w in bare for w in K4):
        return '4K'
    if any(w in bare for w in LIVE):
        return '直播'
    # 排除冒名"百度"的 apibdzy 第三方采集站
    if any(w in bare for w in NETDISK) and 'apibdzy' not in blob:
        return '网盘'
    if t in (0, 1) or api.startswith('http'):
        return '直连'
    if api.startswith('csp_'):
        return jarof(s, cfg)
    if 'drpy' in api.lower() or '.js' in api:
        return 'JS'
    if api.startswith('py_'):
        return 'PY'
    return '其他'


def process(path):
    cfg = json.load(open(path, encoding='utf-8'))
    homes = [s for s in cfg['sites'] if is_home(s)]
    rest = [s for s in cfg['sites'] if not is_home(s)]
    # 首页站内部：带 indexs 标记的排最前（真正的首页聚合页）
    homes.sort(key=lambda s: 0 if s.get('indexs') not in (None, 0, '') else 1)

    buckets = {g: [] for g in ORDER}
    for s in rest:
        buckets.setdefault(group_of(s, cfg), []).append(s)

    new = []
    for s in homes:                       # 首页入口置顶，保持原名不加标签
        s['name'] = bare_name(s)
        new.append(s)
    for g in ORDER:
        for s in sorted(buckets.get(g, []), key=lambda x: str(x.get('key', ''))):
            s['name'] = LABEL[g] + bare_name(s)
            new.append(s)

    cfg['sites'] = new
    json.dump(cfg, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    bad = [(s.get('key'), s.get('api'), jarof(s, cfg)) for s in new
           if str(s.get('api', '')).startswith('csp_')
           and 'Lcom/github/catvod/spider/%s;' % str(s.get('api'))[4:] not in CLS.get(jarof(s, cfg), set())]
    return len(new), homes, Counter(group_of(s, cfg) for s in rest), bad


if __name__ == '__main__':
    targets = sys.argv[1:] or [os.path.join(BASE, 'mstore', 'allinone.json'),
                               os.path.join(BASE, 'mstore', 'evergreen.json')]
    for f in targets:
        tot, homes, stat, bad = process(f)
        print('\n===== %s: %d 站 =====' % (os.path.basename(f), tot))
        print('  【首页/聚合】置顶 %d 个: %s' % (len(homes), [bare_name(h) for h in homes]))
        for g in ORDER:
            if stat.get(g):
                print('    %-10s: %d' % (LABEL[g], stat[g]))
        print('  类命中缺失:', bad if bad else '无 ✓')
