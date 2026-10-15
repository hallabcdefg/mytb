#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JS站源站存活+内容检测：提取 host/url/class_name，请求真实分类页"""
import json, re, os, requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
requests.packages.urllib3.disable_warnings()
UA="Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 Chrome/110 Mobile Safari/537.36"
def ns():
    s=requests.Session(); s.mount("http://",HTTPAdapter(max_retries=0)); s.mount("https://",HTTPAdapter(max_retries=0))
    s.headers.update({"User-Agent":UA}); return s
S=ns()

def rule_of(fp):
    txt=open(fp,encoding='utf-8',errors='ignore').read()
    g=lambda k: (re.search(k+r"\s*:\s*['\"]([^'\"]*)['\"]",txt) or [None,None])[1]
    return {
        'title':g('title'), 'host':g('host'), 'url':g('url'),
        'class_name':g('class_name'), 'class_url':g('class_url'),
        'homeUrl':g('homeUrl'),
    }

def test(name, fp):
    try: r=rule_of(fp)
    except Exception as e: return (name,None,f"读文件失败{type(e).__name__}")
    host=(r['host'] or '').strip()
    if not host or not host.startswith('http'):
        return (name,r,f"host无效:{host!r}")
    cls=(r['class_name'] or '').split('&')
    curl=(r['class_url'] or '').split('&')
    tests=[]
    # 构造几个真实分类请求
    for i in range(min(2,len(cls))):
        cid = curl[i] if i<len(curl) else cls[i]
        u=(r['url'] or '/')
        u=u.replace('fyclass',cid).replace('fypage','1').replace('fyfilter','')
        u=re.sub(r'\$[a-zA-Z_]+','',u)
        full = host.rstrip('/') + '/' + u.lstrip('/') if not u.startswith('http') else u
        tests.append((cls[i] if i<len(cls) else cid, full))
    out=[]
    for cname,url in tests:
        try:
            rr=S.get(url,timeout=12,verify=False,allow_redirects=True)
            ln=len(rr.text)
            # 简单判断：页面里有没有明显的视频链接/条目
            has_vid = len(re.findall(r'(voddetail|/vod/|/show/|href="[^"]*/\d+\.html|play|episode)', rr.text, re.I))
            out.append(f"{cname}:HTTP{rr.status_code}/len{ln}/vid{has_vid}")
        except Exception as e:
            out.append(f"{cname}:{type(e).__name__}")
    # 主域名存活
    try:
        rh=S.get(host,timeout=12,verify=False,allow_redirects=True)
        root=f"HTTP{rh.status_code}/len{len(rh.text)}"
    except Exception as e:
        root=f"{type(e).__name__}"
    return (name,r,f"root={root} | " + " | ".join(out))

def main():
    d=json.load(open('/workspace/tvbox-api-repo/mstore/allinone.json'))
    js=[(s['name'], str(s['ext'])) for s in d['sites'] if str(s.get('api','')).startswith('./libs/js/drpy')]
    print(f"=== JS站源站检测（{len(js)}）===",flush=True)
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs={ex.submit(test,n,('mstore/'+e[2:] if e.startswith('./') else e)):n for n,e in js}
        for f in as_completed(futs):
            n,r,info=f.result()
            print(f"  {n:20} {info}",flush=True)

if __name__=='__main__': main()
