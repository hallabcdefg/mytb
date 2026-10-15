#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为直连站生成 categories 白名单（只含有数据的分类），彻底解决"点进空分类"问题。
策略：实测扫描全部分类 → 保留非空分类 → 写入站点 categories 字段。
若某站原本已有 categories，则取其与实测的交集（保留原有顺序）。
"""
import json, re, sys, requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
requests.packages.urllib3.disable_warnings()
UA="Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/110 Mobile Safari/537.36"
def ns():
    s=requests.Session(); s.mount("http://",HTTPAdapter(max_retries=1)); s.mount("https://",HTTPAdapter(max_retries=1))
    s.headers.update({"User-Agent":UA}); return s
S=ns()

def gj(u,t=12):
    try:
        r=S.get(u,timeout=t,verify=False)
        if r.status_code!=200: return None
        t2=r.text.lstrip()
        return r.json() if t2.startswith('{') else None
    except Exception: return None

def scan_nonempty(api):
    a=api.strip()
    lu=re.sub(r'ac=\w+','ac=list',a) if 'ac=' in a else (a+'ac=list' if a.endswith('?') else (a+'&ac=list' if '?' in a else a+'?ac=list'))
    j=gj(lu)
    if not j: return None
    cats=j.get('class') or []
    sep='&' if '?' in lu else '?'
    good=[]
    for c in cats:
        cid=c.get('type_id'); cname=str(c.get('type_name',cid))
        n=0
        for pg in (1,2):
            j2=gj(f"{lu}{sep}t={cid}&pg={pg}",10)
            if j2 and (j2.get('list') or []): n=len(j2['list']); break
        if n>0: good.append(cname)
    return good

def main():
    path='/workspace/tvbox-api-repo/mstore/allinone.json'
    d=json.load(open(path))
    directs=[s for s in d['sites'] if str(s.get('api','')).startswith('http')]
    print(f"扫描 {len(directs)} 个直连站...",flush=True)
    res={}
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs={ex.submit(scan_nonempty,str(s['api'])):s['name'] for s in directs}
        for f in as_completed(futs):
            n=futs[f]; r=f.result()
            res[n]=r
            if r is None:
                print(f"  ✗ {n:20} 扫描失败",flush=True)
            else:
                print(f"  ✓ {n:20} 非空分类 {len(r)} 个",flush=True)
    json.dump(res,open('/tmp/nonempty_cats.json','w'),ensure_ascii=False,indent=1)
    print("\n已存 /tmp/nonempty_cats.json")

if __name__=='__main__': main()
