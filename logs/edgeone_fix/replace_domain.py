#!/usr/bin/env python3
"""EdgeOne 域名就位后，一键把配置里的 git.yylx.win 代理路径换成 EdgeOne 域名。
用法: python3 replace_domain.py https://你的项目.edgeone.app
"""
import json, sys, re, base64, os, urllib.request

def main():
    if len(sys.argv) < 2:
        print("用法: python3 replace_domain.py https://xxx.edgeone.app"); sys.exit(1)
    domain = sys.argv[1].rstrip('/')

    token = os.environ.get('GH_TOKEN','')
    if not token:
        print("错误: 需要 GH_TOKEN 环境变量(在 /workspace/.env 里)"); sys.exit(1)

    REPO = 'hallabcdefg/mytb'
    API = f'https://api.github.com/repos/{REPO}/contents/index.json'
    H = {'User-Agent':'fty-sync','Authorization':'token '+token}

    # 1. 拉线上当前内容
    req = urllib.request.Request(API, headers=H)
    cur = json.loads(urllib.request.urlopen(req, timeout=30).read())
    sha, content = cur['sha'], base64.b64decode(cur['content']).decode('utf-8')

    # 2. 替换: git.yylx.win/https://raw.githubusercontent.com/hallabcdefg/mytb/main/ -> domain/
    old_prefix = 'https://git.yylx.win/https://raw.githubusercontent.com/hallabcdefg/mytb/main/'
    n = content.count(old_prefix)
    new_content = content.replace(old_prefix, domain + '/')
    print(f'替换代理路径: {n} 处 -> {domain}/')

    if n == 0:
        print('没有找到代理路径,可能已替换过,中止'); sys.exit(0)

    # 3. 校验 JSON 合法
    cfg = json.loads(new_content)
    print(f'JSON 合法, 站点数: {len(cfg["sites"])}, spider: {cfg["spider"]}')

    # 4. 提交
    payload = {'message': f'chore(config): 资源路径切换到 EdgeOne 域名 {domain}',
               'content': base64.b64encode(new_content.encode()).decode(), 'sha': sha}
    req = urllib.request.Request(API, data=json.dumps(payload).encode(), method='PUT',
                                 headers={**H,'Content-Type':'application/json'})
    r = json.loads(urllib.request.urlopen(req, timeout=60).read())
    print('提交成功:', r['commit']['sha'][:12])
    print(f'\n电视端配置地址改为: {domain}/index.json')

if __name__ == '__main__':
    main()
