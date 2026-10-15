#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""深挖：空分类是真的空吗？翻页试试；并给出站点实质质量评分"""
import json, re, requests, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
requests.packages.urllib3.disable_warnings()
UA="Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/110 Mobile Safari/537.36"
def ns():
    s=requests.Session(); s.mount("http://",HTTPAdapter(max_retries=0)); s.mount("https://",HTTPAdapter(max_retries=0))
    s.headers.update({"User-Agent":UA}); return s
S=ns()

def gj(u,t=10):
    try:
        r=S.get(u,timeout=t,verify=False)
        if r.status_code!=200: return None
        txt=r.text.lstrip()
        if not txt.startswith('{'): return None
        return r.json()
    except Exception: return None

def probe(name,api):
    a=api.strip()
    lu = re.sub(r'ac=\w+','ac=list',a) if 'ac=' in a else (a+'ac=list' if a.endswith('?') else (a+'&ac=list' if '?' in a else a+'?ac=list'))
    j=gj(lu,12)
    if not j: return {"name":name,"api":api,"err":"list失败","empty_cats":[],"filled":0,"total":0,"empty":0}
    cats=j.get('class') or []
    sep='&' if '?' in lu else '?'
    empty=[]; filled=0; total=0
    for c in cats:
        cid=c.get('type_id'); cname=str(c.get('type_name',cid))
        v=0
        for pg in (1,2):
            j2=gj(f"{lu}{sep}t={cid}&pg={pg}",10)
            if j2 and (j2.get('list') or []): v=len(j2['list']); break
        if v==0: empty.append(cname)
        else: filled+=1; total+=v
    return {"name":name,"api":api,"err":None,"empty_cats":empty,"filled":filled,"total":total,"empty":len(empty),"ncats":len(cats)}

def main():
    d=json.load(open('/workspace/tvbox-api-repo/mstore/allinone.json'))
    targets=[(s['name'],str(s['api'])) for s in d['sites'] if str(s.get('api','')).startswith('http')]
    res=[]
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs={ex.submit(probe,n,a):n for n,a in targets}
        for f in as_completed(futs):
            r=f.result(); res.append(r)
            if r['err']: print(f"✗ {r['name']:20} {r['err']}",flush=True); continue
            ratio = r['filled']/r['ncats'] if r['ncats'] else 0
            print(f"{r['name']:20} 填充{r['filled']}/{r['ncats']}({ratio:.0%}) 空{r['empty']} 空类={r['empty_cats'][:6]}",flush=True)
    json.dump(res,open('/tmp/deep_scan.json','w'),ensure_ascii=False,indent=1)

if __name__=='__main__': main()
