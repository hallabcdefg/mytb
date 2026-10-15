#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JS站二次验证：多UA/多协议/重试，排除沙箱抖动"""
import json,re,os,time,requests
from concurrent.futures import ThreadPoolExecutor, as_completed
requests.packages.urllib3.disable_warnings()

UAS=[
 "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 Chrome/110 Mobile Safari/537.36",
 "okhttp/4.9.3",
 "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
]

def probe(host):
    """对 host 试多种方式，返回 (是否可达, 详情)"""
    for attempt in range(3):
        for scheme_host in [host, host.replace('https://','http://'), host.replace('http://','https://')]:
            for ua in UAS[:2 if attempt==0 else 3]:
                try:
                    r=requests.get(scheme_host, timeout=20, verify=False, allow_redirects=True,
                                   headers={"User-Agent":ua})
                    if r.status_code<500 and len(r.text)>200:
                        return True, f"HTTP{r.status_code}/len{len(r.text)} via {ua[:20]}"
                except Exception:
                    continue
            time.sleep(0.3)
    return False, "全部失败"

def main():
    d=json.load(open('/workspace/tvbox-api-repo/mstore/allinone.json'))
    # 20个疑似死站的 host
    CAND={
 '⚽ Jrs┃球迷':'http://www.jrkan2022.com','🥔┃优酷(官)':'https://www.youku.com',
 '🧲世界磁力┃Js':'https://www.4khdr.cn','📽️聚短┃视频':'http://www.sharenice.net',
 '🌟┃三五┃影视':'https://www.555dyy.top','🌋┃B站┃影视':'https://bzhanys.com',
 '👨‍🌾┃农民┃影视':'https://www.nmddd.com','🤵┃电影┃先生':'http://dyxs29.com',
 '😎酷吧磁力┃Js':'https://www.kuba222.com','🔥┃骚火┃影视':'https://saohuo.vip',
 '☁️┃云播┃影视':'http://www.tvyb03.com','🍩┃奇优┃影视':'http://www.326tv.com',
 '❤┃爱看┃蓝光':'https://akanhd.com','🐠┃视觉┃影院':'https://www.6080dy4.com',
 '🧗‍┃童趣┃播视':'https://www.boosj.com','🏭️┃厂长┃Js':'https://czspp.com',
 '🐻‍贝尔磁力┃Js':'https://www.cilixiong.com','🎤酷奇┃MV':'https://www.kuqimv.com',
 '🍿┃奇米┃动漫':'https://www.qimi.tv','🥟┃饺子┃影院':'https://www.jiaozi.tv',
    }
    print("=== JS站host二次验证 ===",flush=True)
    alive=[]; dead=[]
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs={ex.submit(probe,h):n for n,h in CAND.items()}
        for f in as_completed(futs):
            n=futs[f]; ok,info=f.result()
            (alive if ok else dead).append((n,info))
            print(f"{'✓' if ok else '✗'} {n:20} {info}",flush=True)
    print(f"\n可达={len(alive)} 不可达={len(dead)}")
    print("确认死站:", [n for n,_ in dead])

if __name__=='__main__': main()
