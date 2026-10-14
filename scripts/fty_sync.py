#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTY（饭太硬 / 梵泰英）spider jar 自动同步脚本
============================================
作用：定期从上游仓库拉取最新的 FTY jar（fan.txt），如果发现有新版本，就：
  1. 校验下载到的文件是完整合法的 dex zip（防止下载被截断）
  2. 解析 jar 内的爬虫类，确认仍是正常的 Guard 类 jar
  3. 覆盖上传到你的 kstore 空间（mstore/qist/jar/fan.txt）
  4. 校验线上文件 md5 与新 jar 一致
  5. 自动更新所有引用该 jar 的配置里的 md5 声明（否则 TVBox 校验不通过会加载失败）
  6. 自动剔除因 jar 更新而失效（类被移除）的站点，保证配置永远自洽
  7. 写日志，并可选自动 git 提交备份

用法：
  python3 fty_sync.py              # 正常同步（无更新则安全退出）
  python3 fty_sync.py --force      # 强制重新上传（即使 md5 没变）
  python3 fty_sync.py --dry-run    # 只检查不上传

凭据：优先读环境变量 KSTORE_DAV_USER / KSTORE_DAV_PASS / KSTORE_DAV_HOST
     （GitHub Actions 里从 Secrets 注入）；本地则回退读取 credentials.env。
"""

import os
import re
import io
import sys
import json
import time
import base64
import hashlib
import zipfile
import struct
import urllib.request
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE, '.sync_state.json')
LOG_FILE = os.path.join(BASE, 'logs', 'fty_sync.log')

# 上游 jar 地址：多镜像，按顺序尝试，任一成功即可（防止单点超时/被墙）
_GH = 'https://raw.githubusercontent.com/qist/tvbox/master/jar/fan.txt'
MIRRORS = [
    _GH,                                                        # GitHub 官方 raw
    'https://ghproxy.net/' + _GH,                               # ghproxy 镜像
    'https://gh-proxy.com/' + _GH,                              # gh-proxy 镜像
    'https://ghproxy.cc/' + _GH,                                # 备用镜像
    'https://fastly.jsdelivr.net/gh/qist/tvbox@master/jar/fan.txt',
    'https://cdn.jsdelivr.net/gh/qist/tvbox@master/jar/fan.txt',
]
if os.environ.get('FTY_UPSTREAM'):
    MIRRORS.insert(0, os.environ['FTY_UPSTREAM'])
JAR_REMOTE = 'mstore/qist/jar/fan.txt'                              # kstore 上的路径
JAR_PUBLIC = 'https://20328.kstore.space/mstore/qist/jar/fan.txt'   # 公开直链

# 引用了该 jar 的配置：（本地路径, kstore 远程路径）
CONFIGS = [
    (os.path.join(BASE, 'mstore', 'qist', 'fty.json'), 'mstore/qist/fty.json'),
    (os.path.join(BASE, 'mstore', 'evergreen.json'),   'mstore/evergreen.json'),
]

MD5_RE = re.compile(r'(;md5;)([0-9a-fA-F]{32})')


def log(msg):
    line = "[%s] %s" % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), msg)
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def load_creds():
    """读取 kstore WebDAV 凭据：优先环境变量，其次本地凭据文件。"""
    user = os.environ.get('KSTORE_DAV_USER')
    pwd = os.environ.get('KSTORE_DAV_PASS')
    host = os.environ.get('KSTORE_DAV_HOST')
    if user and pwd and host:
        return user, pwd, host
    envf = '/root/.codebuddy/credentials/credentials.env'
    if os.path.exists(envf):
        for ln in open(envf, encoding='utf-8'):
            ln = ln.strip()
            if not ln or ln.startswith('#') or '=' not in ln:
                continue
            k, v = ln.split('=', 1)
            v = v.strip().strip('"').strip("'")
            if k == 'KSTORE_DAV_USER':
                user = v
            elif k == 'KSTORE_DAV_PASS':
                pwd = v
            elif k == 'KSTORE_DAV_HOST':
                host = v
    if not (user and pwd and host):
        raise RuntimeError('缺少 kstore 凭据')
    return user, pwd, host


def md5hex(b):
    return hashlib.md5(b).hexdigest()


def try_one(url):
    """尝试从单个镜像下载并校验，成功返回 bytes，失败返回 (None, 原因)。"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=45) as r:
            data = r.read()
        if data[:2] != b'PK':
            return None, '非 zip 文件头'
        bio = io.BytesIO(data)
        if not zipfile.is_zipfile(bio):
            return None, 'zip 中央目录损坏（下载被截断）'
        with zipfile.ZipFile(bio) as z:
            if not any(n.endswith('.dex') for n in z.namelist()):
                return None, 'zip 内无 classes.dex'
        return data, None
    except Exception as e:
        return None, str(e)[:80]


def fetch(urls, tries=2):
    """依次尝试各镜像，严格校验是完整合法的 dex zip（避免截断文件被当成更新）。"""
    last = ''
    for idx, u in enumerate(urls, 1):
        for i in range(tries):
            data, err = try_one(u)
            if data is not None:
                log("  镜像 %d 下载成功: %s（%d bytes）" % (idx, u.split('/')[2], len(data)))
                return data
            last = err or '未知错误'
            log("  镜像 %d 第 %d 次失败(%s)" % (idx, i + 1, last))
            time.sleep(2)
    raise RuntimeError('全部镜像下载失败，最后错误: ' + last)


def dex_classes(data):
    """解析 dex 内的 com.github.catvod.spider.* 类名集合。"""
    cs = set()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
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


def _auth_header(user, pwd):
    return 'Basic ' + base64.b64encode(('%s:%s' % (user, pwd)).encode()).decode()


def dav_put(data, remote, user, pwd, host, tries=3):
    url = '%s/%s' % (host.rstrip('/'), remote.lstrip('/'))
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, method='PUT')
            req.add_header('Authorization', _auth_header(user, pwd))
            req.add_header('User-Agent', 'Mozilla/5.0')
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.status
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(3)


def dav_get(remote, user, pwd, host):
    url = '%s/%s' % (host.rstrip('/'), remote.lstrip('/'))
    req = urllib.request.Request(url, method='GET')
    req.add_header('Authorization', _auth_header(user, pwd))
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def update_config(path, new_md5, new_classes, write=True):
    """更新配置里 fan.txt 的 md5 声明，并剔除新 jar 中已不存在的类的站点。
    write=False 时只计算不落盘（用于 --dry-run 预演）。
    """
    cfg = json.load(open(path, encoding='utf-8'))
    spider = str(cfg.get('spider', ''))
    spider_is_fan = (JAR_PUBLIC in spider) or spider.endswith('fan.txt')

    if spider_is_fan:
        if ';md5;' in spider:
            cfg['spider'] = MD5_RE.sub(lambda m: m.group(1) + new_md5, spider)
        else:
            cfg['spider'] = '%s;md5;%s' % (JAR_PUBLIC, new_md5)

    removed, sites = [], []
    for s in cfg.get('sites', []):
        jar = str(s.get('jar', ''))
        api = str(s.get('api', ''))
        # 该站是否走 fan.txt（顶层 spider 或单站 jar 字段）
        uses_fan = (not jar and spider_is_fan) or (JAR_PUBLIC in jar)
        if uses_fan and ';md5;' in jar:
            s['jar'] = MD5_RE.sub(lambda m: m.group(1) + new_md5, jar)
        if uses_fan and api.startswith('csp_'):
            if 'Lcom/github/catvod/spider/%s;' % api[4:] not in new_classes:
                removed.append(str(s.get('key', '')))
                continue
        sites.append(s)

    cfg['sites'] = sites
    if write:
        json.dump(cfg, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return removed, len(sites)


def git_commit(msg):
    import subprocess
    try:
        subprocess.run(['git', '-C', BASE, 'add', '-A'], check=False, timeout=60)
        subprocess.run(['git', '-C', BASE, 'commit', '-q', '-m', msg], check=False, timeout=60)
        tok = os.environ.get('GITHUB_TOKEN')
        if tok:
            subprocess.run(['git', '-C', BASE, 'push',
                            'https://%s@github.com/hallabcdefg/mytb.git' % tok, 'main'],
                           check=False, timeout=180)
    except Exception as e:
        log("  (git 同步跳过: %s)" % str(e)[:60])


def main():
    args = sys.argv[1:]
    dry = '--dry-run' in args
    force = '--force' in args

    log("=== FTY jar 同步开始 ===")
    user, pwd, host = load_creds()
    data = fetch(MIRRORS)
    new_md5 = md5hex(data)
    log("上游 jar 下载成功: %d bytes, md5=%s" % (len(data), new_md5))

    last = None
    if os.path.exists(STATE_FILE):
        try:
            last = json.load(open(STATE_FILE)).get('last_md5')
        except Exception:
            pass
    if last is None:
        # 优先从配置里已声明的 md5 取基准（比重新下载整个 jar 可靠）
        try:
            sp = json.load(open(CONFIGS[0][0], encoding='utf-8')).get('spider', '')
            m = MD5_RE.search(str(sp))
            if m:
                last = m.group(2)
                log("初始化基准 md5（来自配置声明）: %s" % last)
        except Exception:
            pass
    if last is None:
        try:
            last = md5hex(dav_get(JAR_REMOTE, user, pwd, host))
            log("初始化基准 md5（当前线上）: %s" % last)
        except Exception as e:
            log("  读取线上 jar 失败: %s" % str(e)[:60])

    if last == new_md5 and not force:
        log("无更新（线上已是最新 %s），退出" % new_md5)
        json.dump({'last_md5': new_md5, 'last_check': datetime.now().isoformat()},
                  open(STATE_FILE, 'w'))
        return 0

    log("检测到新版本: %s -> %s" % (last, new_md5))
    classes = dex_classes(data)
    guard = sum(1 for c in classes if 'Guard' in c)
    log("新 jar 解析: spider 类 %d 个，其中 Guard 类 %d 个" % (len(classes), guard))
    if guard == 0:
        log("!! 新 jar 无 Guard 类，疑似异常，中止上传")
        return 1

    if dry:
        log("--dry-run: 跳过上传（本应更新为 %s）" % new_md5)
        for local, _ in CONFIGS:
            if os.path.exists(local):
                removed, total = update_config(local, new_md5, classes, write=False)
                log("  [预演] %s: %d 站，将剔除 %d %s"
                    % (os.path.basename(local), total, len(removed), removed if removed else ''))
        return 0

    st = dav_put(data, JAR_REMOTE, user, pwd, host)
    log("jar 上传完成 (HTTP %s)" % st)

    online = None
    for _ in range(5):
        try:
            req = urllib.request.Request(JAR_PUBLIC, headers={'User-Agent': 'Mozilla/5.0'})
            online = md5hex(urllib.request.urlopen(req, timeout=60).read())
            if online == new_md5:
                break
        except Exception:
            pass
        time.sleep(3)
    if online != new_md5:
        log("!! 线上校验失败（线上=%s, 期望=%s），中止配置更新" % (online, new_md5))
        return 1
    log("线上 jar 校验通过: md5=%s" % online)

    for local, remote in CONFIGS:
        if not os.path.exists(local):
            log("  配置不存在，跳过: %s" % local)
            continue
        removed, total = update_config(local, new_md5, classes)
        dav_put(open(local, 'rb').read(), remote, user, pwd, host)
        log("  已更新 %s: %d 站，剔除失效站 %d %s"
            % (os.path.basename(local), total, len(removed), removed if removed else ''))

    json.dump({'last_md5': new_md5, 'last_check': datetime.now().isoformat(),
               'last_size': len(data)}, open(STATE_FILE, 'w'))
    git_commit("chore(auto): FTY jar 自动同步 %s -> %s" % (str(last)[:8], new_md5[:8]))
    log("=== 同步完成 ===")
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        log("!! 同步失败: %s" % str(e)[:200])
        sys.exit(1)
