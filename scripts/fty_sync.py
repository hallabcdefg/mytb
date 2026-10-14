#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox spider jar 自动同步脚本（多包版）
=====================================
源站地址封在 jar 里，作者一发新 jar 就换掉失效源站 —— 所以 jar 必须跟着更新。
本脚本定期从上游拉取最新的 spider jar，若有更新就自动上传到 kstore 并改写配置 md5。

同步目标：
  1. FTY 的 fan.txt        —— Guard 类站（线路二/三在用）
  2. spider.jar (2026)     —— 非 Guard 爬虫站（线路一 66 个站在用）

流程（每个 jar 独立）：
  下载(多镜像) → 校验完整 dex zip → 比对 md5 → 无更新则跳过
  → 有更新则上传 kstore → 校验线上 md5 → 改写引用配置的 md5 → 剔除失效站 → 写日志

用法：
  python3 fty_sync.py              # 正常同步（无更新则安全退出）
  python3 fty_sync.py --force      # 强制重新上传
  python3 fty_sync.py --dry-run    # 只检查不上传

凭据：优先环境变量 KSTORE_DAV_USER / KSTORE_DAV_PASS / KSTORE_DAV_HOST
     （GitHub Actions 从 Secrets 注入）；本地回退读取 credentials.env。
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

# ---------- 上游与同步目标 ----------
_GH = 'https://raw.githubusercontent.com/qist/tvbox/master/jar/'
_MIRRORS = ['https://ghproxy.net/', 'https://gh-proxy.com/', 'https://ghproxy.cc/']

TARGETS = [
    {
        'name': 'FTY fan.txt',
        'upstreams': [_GH + 'fan.txt'] + [m + _GH + 'fan.txt' for m in _MIRRORS],
        'remote': 'mstore/qist/jar/fan.txt',
        'public': 'https://20328.kstore.space/mstore/qist/jar/fan.txt',
        # 引用了该 jar 的配置（本地路径, kstore 远程路径）—— 需要同步 md5
        'configs': [
            (os.path.join(BASE, 'mstore', 'qist', 'fty.json'), 'mstore/qist/fty.json'),
            (os.path.join(BASE, 'mstore', 'evergreen.json'), 'mstore/evergreen.json'),
        ],
        'min_guard': 1,      # 至少要有 Guard 类，否则视为异常
    },
    {
        'name': 'spider.jar(2026)',
        'upstreams': [_GH + 'spider.jar'] + [m + _GH + 'spider.jar' for m in _MIRRORS],
        'remote': 'mstore/jars/spider_2026.jar',
        'public': 'https://20328.kstore.space/mstore/jars/spider_2026.jar',
        'configs': [],       # 单站 jar 引用，无需改写 md5
        'min_classes': 500,  # 至少这么多爬虫类，否则视为异常
    },
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
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as r:
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
    last = ''
    for idx, u in enumerate(urls, 1):
        for i in range(tries):
            data, err = try_one(u)
            if data is not None:
                log("  镜像 %d 下载成功（%d bytes）" % (idx, len(data)))
                return data
            last = err or '未知错误'
            log("  镜像 %d 第 %d 次失败(%s)" % (idx, i + 1, last))
            time.sleep(2)
    raise RuntimeError('全部镜像下载失败，最后错误: ' + last)


def dex_classes(data):
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


def _auth(user, pwd):
    return 'Basic ' + base64.b64encode(('%s:%s' % (user, pwd)).encode()).decode()


def dav_put(data, remote, user, pwd, host, tries=3):
    url = '%s/%s' % (host.rstrip('/'), remote.lstrip('/'))
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, method='PUT')
            req.add_header('Authorization', _auth(user, pwd))
            req.add_header('User-Agent', 'Mozilla/5.0')
            with urllib.request.urlopen(req, timeout=240) as r:
                return r.status
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(3)


def dav_get(remote, user, pwd, host):
    url = '%s/%s' % (host.rstrip('/'), remote.lstrip('/'))
    req = urllib.request.Request(url, method='GET')
    req.add_header('Authorization', _auth(user, pwd))
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def update_config(path, jar_public, new_md5, new_classes):
    """更新配置里该 jar 的 md5 声明，并剔除新 jar 中已不存在的类的站点。"""
    cfg = json.load(open(path, encoding='utf-8'))
    spider = str(cfg.get('spider', ''))
    spider_is = jar_public in spider or spider.endswith('fan.txt')

    if spider_is:
        if ';md5;' in spider:
            cfg['spider'] = MD5_RE.sub(lambda m: m.group(1) + new_md5, spider)
        else:
            cfg['spider'] = '%s;md5;%s' % (jar_public, new_md5)

    removed, sites = [], []
    for s in cfg.get('sites', []):
        jar = str(s.get('jar', ''))
        api = str(s.get('api', ''))
        uses = (not jar and spider_is) or (jar_public in jar)
        if uses and ';md5;' in jar:
            s['jar'] = MD5_RE.sub(lambda m: m.group(1) + new_md5, jar)
        if uses and api.startswith('csp_'):
            if 'Lcom/github/catvod/spider/%s;' % api[4:] not in new_classes:
                removed.append(str(s.get('key', '')))
                continue
        sites.append(s)

    cfg['sites'] = sites
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
                           check=False, timeout=240)
    except Exception as e:
        log("  (git 同步跳过: %s)" % str(e)[:60])


def sync_target(t, state, user, pwd, host, dry, force):
    name = t['name']
    log("---- 检查 [%s] ----" % name)
    data = fetch(t['upstreams'])
    new_md5 = md5hex(data)
    classes = dex_classes(data)
    guard = sum(1 for c in classes if 'Guard' in c)
    log("  上游: %d bytes, md5=%s, 类 %d (Guard %d)" % (len(data), new_md5, len(classes), guard))

    if t.get('min_guard') and guard < t['min_guard']:
        log("  !! Guard 类不足(%d)，疑似异常，跳过" % guard)
        return False
    if t.get('min_classes') and len(classes) < t['min_classes']:
        log("  !! 类数量不足(%d)，疑似异常，跳过" % len(classes))
        return False

    last = state.get('jars', {}).get(name)
    if last is None and t['configs']:
        try:
            sp = json.load(open(t['configs'][0][0], encoding='utf-8')).get('spider', '')
            m = MD5_RE.search(str(sp))
            if m:
                last = m.group(2)
                log("  基准 md5（来自配置声明）: %s" % last)
        except Exception:
            pass
    if last is None:
        # 用公开直链比对（WebDAV 读取大文件容易 IncompleteRead）
        try:
            req = urllib.request.Request(t['public'], headers={'User-Agent': 'Mozilla/5.0'})
            last = md5hex(urllib.request.urlopen(req, timeout=180).read())
            log("  基准 md5（当前线上）: %s" % last)
        except Exception as e:
            log("  读取线上失败: %s" % str(e)[:60])

    if last == new_md5 and not force:
        log("  无更新，跳过")
        state.setdefault('jars', {})[name] = new_md5
        return False

    log("  发现新版本: %s -> %s" % (str(last)[:8], new_md5[:8]))
    if dry:
        log("  --dry-run: 跳过上传")
        return False

    st = dav_put(data, t['remote'], user, pwd, host)
    log("  上传完成 (HTTP %s)" % st)

    online = None
    for _ in range(5):
        try:
            req = urllib.request.Request(t['public'], headers={'User-Agent': 'Mozilla/5.0'})
            online = md5hex(urllib.request.urlopen(req, timeout=90).read())
            if online == new_md5:
                break
        except Exception:
            pass
        time.sleep(3)
    if online != new_md5:
        log("  !! 线上校验失败（线上=%s），中止配置更新" % online)
        return False
    log("  线上校验通过")

    for local, remote in t['configs']:
        if not os.path.exists(local):
            continue
        removed, total = update_config(local, t['public'], new_md5, classes)
        dav_put(open(local, 'rb').read(), remote, user, pwd, host)
        log("  已更新 %s: %d 站，剔除失效站 %d %s"
            % (os.path.basename(local), total, len(removed), removed if removed else ''))

    state.setdefault('jars', {})[name] = new_md5
    return True


def main():
    dry = '--dry-run' in sys.argv
    force = '--force' in sys.argv
    log("=== jar 同步开始 ===")
    user, pwd, host = load_creds()

    state = {}
    if os.path.exists(STATE_FILE):
        try:
            state = json.load(open(STATE_FILE))
        except Exception:
            pass

    changed = False
    for t in TARGETS:
        try:
            if sync_target(t, state, user, pwd, host, dry, force):
                changed = True
        except Exception as e:
            log("  !! [%s] 同步失败: %s" % (t['name'], str(e)[:150]))

    state['last_check'] = datetime.now().isoformat()
    json.dump(state, open(STATE_FILE, 'w'))

    if changed:
        git_commit("chore(auto): spider jar 自动同步更新")
    log("=== 同步结束（有变更: %s）===" % ('是' if changed else '否'))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        log("!! 同步失败: %s" % str(e)[:200])
        sys.exit(1)
