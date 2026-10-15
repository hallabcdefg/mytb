#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox 配置站点分组归类脚本
==========================
排序规则（按成熟线路的惯例）：

  1. 聚合页      —— 首页合集入口（indexs 标记 / 名称含 聚合·首页·切源），置顶，不加标签
  2. 配置中心    —— 网盘登录配置入口（名称含"配置"），置顶，不加标签
  3. 本地视频    —— 本地存储（csp_Local），置顶，不加标签
  4. 直连        —— type 0/1 或 api 为 http 地址，直接取数据的站
  5. 爬虫        —— csp_ / drpy / js / py 等靠爬虫抓取的站（不再按 jar 归属细分）
  6. 4K          —— 高清/4K 类
  7. 直播        —— 直播/电视类（放最后）

注意：不再按 jar 包分组（"饭太硬""梵泰英"等同属一个作者，按 jar 文件名分会产生重复标签）。

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

JAR_FILES = {
    '饭太硬': '/tmp/jars/fty.jar', '梵泰英': '/tmp/jars/fantaiying.jar',
    '光速': '/tmp/jars/guangge.jar', '肥猫': '/tmp/jars/feimao.jar',
    '多多': '/tmp/jars/duoduo.jar', 'liu673cn': '/tmp/jars/liu.jar',
    'FTY': '/tmp/jars/fan.jar',
}
JAR_URL = {
    '饭太硬': 'https://20328.kstore.space/mstore/jars/饭太硬.jar',
    '梵泰英': 'https://20328.kstore.space/mstore/jars/fantaiying.jar',
    '光速': 'https://20328.kstore.space/mstore/jars/guangge.jar',
    '肥猫': 'https://20328.kstore.space/mstore/jars/feimao.jar',
    '多多': 'https://20328.kstore.space/mstore/jars/duoduo.jar',
    'liu673cn': 'https://20328.kstore.space/mstore/liu673cn/fty.jar',
    'FTY': 'https://20328.kstore.space/mstore/qist/jar/fan.txt',
}
JAR_PAT = [
    ('饭太硬', 'jars/饭太硬.jar'), ('FTY', 'qist/jar/fan.txt'),
    ('梵泰英', 'jars/fantaiying.jar'), ('光速', 'jars/guangge.jar'),
    ('肥猫', 'jars/feimao.jar'), ('多多', 'jars/duoduo.jar'),
    ('liu673cn', 'liu673cn/fty.jar'),
]

K4 = ['4k', '2160', 'uhd', 'hdr', '杜比', '蓝光', '高清', '8k', '原画', '超清']
LIVE = ['直播', '电视', '卫视', '央视', 'cctv', '体育', '赛事', '虎牙', '斗鱼',
        'huya', 'douyu', '频道', '轮播', 'live']

# 顺序：置顶三特殊页(聚合/配置/本地)之后，再按真实机制分组。
# 机制组整体置于"站点主体"的末端（不在最前面，保证站点名先可见），直播永远最后。
ORDER = ['直连', 'JS采集', '爬虫', '4K', '直播']
LABEL = {'直连': '【直连】', 'JS采集': '【JS采集】', '爬虫': '【爬虫】',
         '4K': '【4K】', '直播': '【直播】'}


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


def owner_jar(api):
    """找出包含该 csp 类的 jar（用于给缺失站绑定正确 jar）。"""
    if not api.startswith('csp_'):
        return None
    need = 'Lcom/github/catvod/spider/%s;' % api[4:]
    for name, cs in CLS.items():
        if need in cs:
            return name
    return None


def bare_name(s):
    """去掉已加的【xxx】标签，保证重复运行不叠加。"""
    return re.sub(r'^【[^】]*】', '', str(s.get('name', '')))


def is_agg(s):
    """聚合页：indexs 标记 或 名称含 聚合/首页/切源。"""
    if s.get('indexs') not in (None, 0, ''):
        return True
    return any(w in (str(s.get('key', '')) + bare_name(s)).lower()
               for w in ['聚合', '首页', '切源'])


def is_config(s):
    """配置中心：名称含"配置"（网盘登录入口）。"""
    b = (str(s.get('key', '')) + ' ' + bare_name(s) + ' ' + str(s.get('api', ''))).lower()
    return '配置' in b or 'mydrive' in b


def is_local(s):
    """本地视频：csp_Local 或名称含"本地"。"""
    b = (str(s.get('key', '')) + ' ' + bare_name(s) + ' ' + str(s.get('api', ''))).lower()
    return 'local' in b or '本地' in b


def group_of(s):
    """按 api 字段判定真实机制（唯一权威判据），绝不再凭名字瞎贴标签。

      优先级（从强到弱）：
        1) api 为 http(s)://            → 直连 （源站自带标准 API，不用 jar）
        2) api 为 ./libs/js/*.js / drpy / js_ / dr_ → JS采集（本地脚本解析，不用 jar）
        3) api 以 csp_ 开头 或 带 jar 字段 → 爬虫 （依赖 jar 现场抓）
        4) api 为 py_* / tv 直播类      → 直播
        5) 以上都不符时，才用名称关键字兜底判 4K / 直播
    """
    n = bare_name(s)
    api = str(s.get('api', ''))
    key = str(s.get('key', ''))
    bare = (key + ' ' + n + ' ' + api).lower()

    # —— 机制判据（最权威）——
    if api.startswith('http'):
        return '直连'
    if api.startswith('./libs') or api.endswith('.js') or 'drpy' in api \
            or re.match(r'^(js_|dr_)', api):
        return 'JS采集'
    if api.startswith('csp_') or (s.get('jar') and not api.startswith('http')):
        return '爬虫'
    if api.startswith('py_') or api.startswith('tv_') or 'live' in api.lower():
        return '直播'

    # —— 名称关键字兜底（仅对上面判不出的少数站点生效）——
    if any(w in bare for w in K4):
        return '4K'
    if any(w in bare for w in LIVE):
        return '直播'
    return '爬虫'


def process(path):
    cfg = json.load(open(path, encoding='utf-8'))
    sites = cfg['sites']

    agg = [s for s in sites if is_agg(s) and not is_config(s) and not is_local(s)]
    conf = [s for s in sites if is_config(s)]
    local = [s for s in sites if is_local(s) and not is_config(s)]
    special = set(id(s) for s in agg + conf + local)
    rest = [s for s in sites if id(s) not in special]

    buckets = {g: [] for g in ORDER}
    for s in rest:
        buckets.setdefault(group_of(s), []).append(s)

    new = []
    for s in agg + conf + local:          # 置顶区：聚合页 → 配置中心 → 本地
        s['name'] = bare_name(s)
        new.append(s)
    for g in ORDER:                        # 按机制排序，但不在名字前加标签
        for s in sorted(buckets.get(g, []), key=lambda x: str(x.get('key', ''))):
            s['name'] = bare_name(s)
            new.append(s)

    cfg['sites'] = new
    json.dump(cfg, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    bad = []
    for s in new:
        api = str(s.get('api', ''))
        if not api.startswith('csp_'):
            continue
        j = None
        for tag, pat in JAR_PAT:
            if pat in str(s.get('jar', '')):
                j = tag
                break
        if j is None:
            j = owner_jar(api) or 'FTY'
        if 'Lcom/github/catvod/spider/%s;' % api[4:] not in CLS.get(j, set()):
            bad.append((s.get('key'), api, j))
    return len(new), [bare_name(s) for s in agg], [bare_name(s) for s in conf], \
        [bare_name(s) for s in local], Counter(group_of(s) for s in rest), bad


def ensure_special(target, src):
    """确保配置中心、本地视频这类必备入口在目标配置中存在（缺失则从主配置补）。"""
    tcfg = json.load(open(target, encoding='utf-8'))
    scfg = json.load(open(src, encoding='utf-8'))
    have = set(str(s.get('key', '')) for s in tcfg['sites'])
    added = []
    for s in scfg['sites']:
        if not (is_config(s) or is_local(s)):
            continue
        if str(s.get('key', '')) in have:
            continue
        s = dict(s)
        j = owner_jar(str(s.get('api', ''))) if str(s.get('api', '')).startswith('csp_') else None
        if j:
            s['jar'] = JAR_URL[j]
        tcfg['sites'].append(s)
        added.append((s.get('key'), s.get('name'), j))
    if added:
        json.dump(tcfg, open(target, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return added


if __name__ == '__main__':
    allf = os.path.join(BASE, 'mstore', 'allinone.json')
    # 注：本次仅重排/修正线路一(allinone)，线路二/三按既定要求保持不动。
    targets = sys.argv[1:] or [allf]
    for f in targets:
        tot, agg, conf, local, stat, bad = process(f)
        print('\n===== %s: %d 站 =====' % (os.path.basename(f), tot))
        print('  置顶-聚合页  : %s' % agg)
        print('  置顶-配置中心: %s' % conf)
        print('  置顶-本地视频: %s' % local)
        for g in ORDER:
            if stat.get(g):
                print('    %-8s: %d' % (LABEL[g], stat[g]))
        print('  类命中缺失(诊断):', bad if bad else '无 ✓')
