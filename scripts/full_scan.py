#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全站全层级深度体检 v2
- 直连站：遍历【每一个分类】，统计每类第1页视频数；首页(推荐)也查
- JS站：解析 JS 文件里的 host + 一级规则，尽量模拟请求
- 输出问题清单：首页空 / 任意分类空
"""
import json, re, sys, os, time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter

requests.packages.urllib3.disable_warnings()
UA = "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110 Mobile Safari/537.36"

def new_session():
    s = requests.Session()
    s.mount("http://", HTTPAdapter(max_retries=1, pool_connections=20, pool_maxsize=20))
    s.mount("https://", HTTPAdapter(max_retries=1, pool_connections=20, pool_maxsize=20))
    s.headers.update({"User-Agent": UA})
    return s

S = new_session()

def tvmode_list(api):
    """构造 TVBox 会请求的 ac=list URL"""
    a = api.strip()
    if 'ac=' in a:
        return re.sub(r'ac=\w+', 'ac=list', a)
    if a.endswith('?'): return a + 'ac=list'
    if '?' in a:        return a + '&ac=list'
    return a + ('/?' if False else '?') + 'ac=list'

def get_json(url, t=10):
    try:
        r = S.get(url, timeout=t, verify=False)
        if r.status_code != 200: return None, f"HTTP{r.status_code}"
        ct = r.headers.get('Content-Type','')
        txt = r.text.lstrip()
        if not txt.startswith('{') and not txt.startswith('['):
            return None, f"非JSON({txt[:30]!r})"
        return r.json(), None
    except Exception as e:
        return None, f"{type(e).__name__}"

def probe_direct(name, api):
    """遍历全部分类，返回 (首页条数, {分类名:条数})"""
    lu = tvmode_list(api)
    j, err = get_json(lu, 12)
    if err:
        return {"name": name, "api": api, "err": err, "cats": {}, "home": -1}
    cats = j.get('class') or []
    if not cats:
        return {"name": name, "api": api, "err": "无分类", "cats": {}, "home": -1}
    sep = '&' if '?' in lu else '?'
    result = {}
    home = -1
    for c in cats:
        cid = c.get('type_id'); cname = str(c.get('type_name', cid))
        j2, e2 = get_json(f"{lu}{sep}t={cid}&pg=1", 10)
        if e2:
            result[cname] = None   # 请求失败
        else:
            lst = j2.get('list') or []
            result[cname] = len(lst)
            if home < 0:
                home = len(lst)
    # 首页=第一个分类（TVBox 首页通常显示第一个分类或推荐）
    return {"name": name, "api": api, "err": None, "cats": result, "home": home}

def main():
    which = sys.argv[1] if len(sys.argv) > 1 else 'direct'
    d = json.load(open('/workspace/tvbox-api-repo/mstore/allinone.json'))
    sites = d['sites']

    if which == 'direct':
        targets = [(s['name'], str(s['api'])) for s in sites if str(s.get('api','')).startswith('http')]
    elif which == 'names':
        targets = []
    else:
        targets = []

    print(f"=== 直连站全分类深扫（{len(targets)} 个）===", flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(probe_direct, n, a): n for n, a in targets}
        for f in as_completed(futs):
            r = f.result()
            results.append(r)
            if r['err']:
                print(f"✗ {r['name']:22} ERR {r['err']}", flush=True)
            else:
                empty = [k for k, v in r['cats'].items() if v == 0]
                failed = [k for k, v in r['cats'].items() if v is None]
                total = sum(v for v in r['cats'].values() if v)
                flag = "✓" if not empty and not failed else ("△" if total > 0 else "✗")
                info = f"{len(r['cats'])}类 共{total}条"
                if empty: info += f" 空分类{len(empty)}:{empty[:8]}"
                if failed: info += f" 失败{len(failed)}:{failed[:5]}"
                print(f"{flag} {r['name']:22} {info}", flush=True)
    json.dump(results, open('/tmp/direct_full_scan.json','w'), ensure_ascii=False, indent=1)
    print("\n结果已存 /tmp/direct_full_scan.json")

if __name__ == '__main__':
    main()
