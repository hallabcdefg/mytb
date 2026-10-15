#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""实测直连采集站是否真的能采到数据：ac=list 拿分类 → 拿第一个分类的视频列表"""
import json, re, sys, requests
from requests.adapters import HTTPAdapter

UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 okhttp/4.9.3"}
S = requests.Session()
S.mount("http://", HTTPAdapter(max_retries=0))
S.mount("https://", HTTPAdapter(max_retries=0))
S.headers.update(UA)

def get(url, t=12):
    return S.get(url, timeout=t, verify=False, allow_redirects=True)

def normalize(api):
    api = api.strip()
    # 去掉已有的 ac/参数尾缀做基准
    base = re.sub(r'(at/xml|from/\w+|/|\?)$'.replace('(at/xml|from/\\w+|/|\\?)','/?$'), '', api) if False else api
    return api

def test_site(name, api):
    api = api.strip()
    # 统一变成 list 接口
    if 'ac=' not in api:
        sep = '&' if '?' in api else '?'
        list_url = f"{api}{sep}ac=list"
    else:
        list_url = re.sub(r'ac=\w+', 'ac=list', api)
        if re.search(r'ac=\w+$', list_url) is None and '?' not in list_url:
            list_url = list_url + '?ac=list'
    try:
        r = get(list_url)
        if r.status_code != 200:
            return name, api, False, f"HTTP {r.status_code}"
        try:
            j = r.json()
        except Exception:
            # 有些站返回 xml
            if '<list' in r.text or '<video' in r.text:
                m = re.search(r'<video', r.text)
                return name, api, bool(m), f"XML响应({len(r.text)}B)"
            return name, api, False, f"非JSON({r.text[:60]!r})"
        cats = j.get('class') or []
        total = j.get('total')
        if not cats:
            return name, api, False, f"无分类 total={total}"
        # 拿第一个分类的视频列表
        t1 = cats[0].get('type_id')
        sep = '&' if '?' in list_url else '?'
        v_url = f"{list_url}{sep}t={t1}&pg=1"
        r2 = get(v_url)
        if r2.status_code != 200:
            return name, api, False, f"视频列表HTTP {r2.status_code}"
        try:
            j2 = r2.json()
        except Exception:
            return name, api, False, "视频列表非JSON"
        videos = j2.get('list') or []
        if not videos:
            return name, api, False, f"分类{t1}无视频"
        return name, api, True, f"OK {len(cats)}分类/{len(videos)}视频"
    except Exception as e:
        return name, api, False, f"{type(e).__name__}: {str(e)[:80]}"

def main():
    requests.packages.urllib3.disable_warnings()
    d = json.load(open('/workspace/tvbox-api-repo/mstore/allinone.json'))
    targets = [(s['name'], str(s['api'])) for s in d['sites'] if str(s.get('api','')).startswith('http')]
    results = []
    for name, api in targets:
        res = test_site(name, api)
        results.append(res)
        flag = "✓" if res[2] else "✗"
        print(f"{flag} {res[0]}  ->  {res[3]}", flush=True)
    dead = [r for r in results if not r[2]]
    print(f"\n=== 直连共 {len(results)}，死 {len(dead)} ===")
    for r in dead:
        print("DEAD:", r[0], "|", r[3])
    json.dump(results, open('/tmp/direct_test.json','w'), ensure_ascii=False)

if __name__ == '__main__':
    main()
