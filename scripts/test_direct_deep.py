#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""复测：对疑似死站遍历前若干分类+翻页，确认是否真的无数据"""
import json, re, requests
from requests.adapters import HTTPAdapter

S = requests.Session()
S.mount("http://", HTTPAdapter(max_retries=0))
S.mount("https://", HTTPAdapter(max_retries=0))
S.headers.update({"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 okhttp/4.9.3"})
requests.packages.urllib3.disable_warnings()

def g(u, t=15):
    return S.get(u, timeout=t, verify=False, allow_redirects=True)

def listurl(api):
    api = api.strip()
    if 'ac=' not in api:
        return api + ('&' if '?' in api else '?') + 'ac=list'
    return re.sub(r'ac=\w+', 'ac=list', api)

def deep(name, api):
    lu = listurl(api)
    try:
        r = g(lu)
        if r.status_code != 200:
            return name, f"HTTP {r.status_code}"
        j = r.json()
        cats = j.get('class') or []
        if not cats:
            return name, "无分类"
        detail = []
        found = 0
        for c in cats[:6]:
            t1 = c.get('type_id')
            sep = '&' if '?' in lu else '?'
            for pg in (1, 2, 3):
                r2 = g(f"{lu}{sep}t={t1}&pg={pg}")
                try:
                    v = (r2.json().get('list') or [])
                except Exception:
                    v = []
                detail.append(f"t={t1}pg{pg}:{len(v)}")
                if v:
                    found += len(v)
                    break
            if found:
                break
        if found:
            return name, f"有数据 {found} ({' '.join(detail)})"
        return name, f"确认无数据 [{' '.join(detail[:12])}]"
    except Exception as e:
        return name, f"{type(e).__name__}: {str(e)[:70]}"

d = json.load(open('/workspace/tvbox-api-repo/mstore/allinone.json'))
names = ["🎪360┃秒播","☕🦊茶杯狐┃秒播","🎞️天堂┃采集","🐉┃索尼┃高清","🥗┃非凡┃资源",
         "影视•天涯","🚆极速┃影视","🦊火狐采集","🎏百度┃采集","索尼｜采集","⚡闪电┃影视",
         "️非凡采集","影视•非凡[直连]","非凡｜采集","影视•卧龙[直连]"]
for s in d['sites']:
    if s['name'] in names:
        n, r = deep(s['name'], str(s['api']))
        print(f"{n}  ->  {r}", flush=True)
