#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""搜索质量检测：实测每个站搜索'美人鱼'，算匹配率"""
import requests,json,urllib.parse,re
from concurrent.futures import ThreadPoolExecutor, as_completed
requests.packages.urllib3.disable_warnings()
UA="Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/110 Mobile Safari/537.36"
S=requests.Session(); S.headers.update({"User-Agent":UA})
KW='美人鱼'; KWE=urllib.parse.quote(KW)

def names_from(txt):
    return re.findall(r'"(?:vod_name|name|title|albumName|tvName|videoName|display_name)"\s*:\s*"([^"]{1,40})"',txt)

def check_direct(name,api):
    base=api.rstrip('?/').rstrip('/'); sep='&' if '?' in base else '?'
    try:
        r=S.get(f"{base}{sep}ac=detail&wd={KWE}",timeout=15,verify=False)
        j=r.json(); lst=j.get('list') or []
        if not lst: return name,'空',0,0,[]
        ns=[str(v.get('vod_name','')) for v in lst]
        hit=sum(1 for n in ns if KW in n)
        return name,'直连',len(lst),hit,ns[:5]
    except Exception as e:
        return name,'ERR:'+type(e).__name__,0,0,[]

def check_js(name,searchurl,host):
    if not searchurl or not searchurl.startswith(('http','/')): return name,'无searchUrl',0,0,[]
    u=searchurl.replace('**',KWE).replace('fypage','1')
    if u.startswith('/'): u=host.rstrip('/')+u
    u=re.sub(r'fyfilter','',u)
    try:
        hdr={"Referer":host,"Origin":host}
        r=S.get(u,timeout=15,verify=False,headers=hdr)
        names=names_from(r.text)
        if not names: return name,f'HTTP{r.status_code}无片名',0,0,[]
        # 只统计非标签名的
        skip={'全部','影视','精选','综艺','动漫','电影','电视剧','纪录片','少儿','音乐','搞笑','生活','游戏','教育','VIP'}
        real=[n for n in names if n not in skip and len(n)>2]
        hit=sum(1 for n in real if KW in n)
        return name,f'JS(HTTP{r.status_code})',len(real),hit,real[:5]
    except Exception as e:
        return name,'ERR:'+type(e).__name__,0,0,[]

def main():
    d=json.load(open('/workspace/tvbox-api-repo/mstore/allinone.json'))
    print(f"=== 搜索质量检测（关键词: {KW}）===\n")
    # 直连站
    print("--- 直连站 ---")
    for s in d['sites']:
        a=str(s.get('api',''))
        if not a.startswith('http'): continue
        if s.get('searchable')==0:
            print(f"  [已禁搜] {s['name']}"); continue
        n,typ,tot,hit,samp=check_direct(s['name'],a)
        rate=hit/tot if tot else 0
        flag='✓' if (tot==0 or rate>=0.8) else ('△' if rate>0 else '✗垃圾')
        print(f"  {flag} {n:18} {typ:6} 共{tot:3} 命中{hit:3} 匹配率{rate:.0%}")
    # JS 站
    print("\n--- JS站（官源）---")
    import os
    for s in d['sites']:
        if not str(s.get('api','')).startswith('./libs/js/drpy'): continue
        ext=str(s.get('ext','')); p='mstore/'+ext[2:] if ext.startswith('./') else ext
        if not os.path.exists(p): continue
        t=open(p,encoding='utf-8',errors='ignore').read()
        host=(re.search(r"host\s*:\s*['\"]([^'\"]+)['\"]",t) or [None,''])[1]
        if not any(k in host for k in ['iqiyi','mgtv','qq.com','youku','360kan','sogou','bilibili']): continue
        su=(re.search(r"searchUrl\s*:\s*['\"]([^'\"]*)['\"]",t) or [None,''])[1]
        if s.get('searchable')==0:
            print(f"  [已禁搜] {s['name']}"); continue
        n,typ,tot,hit,samp=check_js(s['name'],su,host)
        rate=hit/tot if tot else 0
        flag='✓' if (tot==0 or rate>=0.8) else ('△' if rate>0 else '✗垃圾')
        print(f"  {flag} {n:18} {typ:18} 共{tot:3} 命中{hit:3} 匹配率{rate:.0%} 样本{samp if tot else ''}")

if __name__=='__main__': main()
