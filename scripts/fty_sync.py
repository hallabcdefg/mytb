#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox spider jar 自动同步脚本（多包版 · v2）
============================================
源站地址封在 jar 里，作者一发新 jar 就换掉失效源站 —— 所以 jar 必须跟着更新。
本脚本定期从上游拉取最新的 spider jar，若有更新就自动上传到 kstore 并改写配置 md5。

同步目标（4 个）：
  1. FTY fan.txt           —— FTY 加固包（Guard 类站），evergreen 顶层 spider 在用
  2. spider.jar (2026)     —— 非 Guard 爬虫站（allinone 65 站在用）
  3. pg_upgraded (2026-08) —— allinone 10 站在用
  4. FTY unified (1.jpg)   —— 与 fan.txt 同源同性质的 FTY 加固包快照，
                              allinone 顶层 spider + 28 个站直引 fty.jar

单个 jar 的流水线（依次串行）：
  下载(异构多源) → HEAD 预检 → 校验 zip/dex → 算 md5 → 与上次比对 → 无更新则跳过
  → 上传 kstore → 校验线上 md5 → 改写引用该 jar 的配置 md5（含补写）
  → 剔除失效站（守护版跳过）→ 写状态

用法：
  python3 fty_sync.py              # 正常同步（无更新则安全退出）
  python3 fty_sync.py --force      # 强制重新上传
  python3 fty_sync.py --dry-run    # 只检查不上传
  python3 fty_sync.py --list       # 列出所有目标
  python3 fty_sync.py --only spider  # 只同步名字含 "spider" 的目标

退出码：0=全部成功；1=有 jar 同步失败

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
import urllib.error
from datetime import datetime
from urllib.parse import urlsplit

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE, '.sync_state.json')
LOG_FILE = os.path.join(BASE, 'logs', 'fty_sync.log')
BAK_DIR = os.path.join(BASE, 'logs', 'config_backup')

# ---------- 上游与同步目标 ----------
# 异构源：同仓库不同 CDN / 不同路径，避免"上游一挂全挂"
_GH = 'https://raw.githubusercontent.com/qist/tvbox/master/jar/'
_CDN = 'https://cdn.jsdelivr.net/gh/qist/tvbox@master/jar/'
_MIRROR = ['https://ghproxy.net/', 'https://gh-proxy.com/']


def _sources(fname):
    """给一个文件名生成异构源列表：原生 raw → jsDelivr → 两个反代。"""
    raw = _GH + fname
    return [raw, _CDN + fname] + [m + raw for m in _MIRROR]


TARGETS = [
    {
        'name': 'FTY fan.txt',
        'upstreams': _sources('fan.txt'),
        'remote': 'mstore/qist/jar/fan.txt',
        'public': 'https://20328.kstore.space/mstore/qist/jar/fan.txt',
        'configs': [
            (os.path.join(BASE, 'mstore', 'qist', 'fty.json'), 'mstore/qist/fty.json'),
            (os.path.join(BASE, 'mstore', 'evergreen.json'), 'mstore/evergreen.json'),
        ],
        'min_guard': 30,     # 实测 Guard 45，留余量
        'min_classes': 60,   # 实测 75
    },
    {
        'name': 'spider.jar(2026)',
        'upstreams': _sources('spider.jar'),
        'remote': 'mstore/jars/spider_2026.jar',
        'public': 'https://20328.kstore.space/mstore/jars/spider_2026.jar',
        'configs': [
            (os.path.join(BASE, 'mstore', 'allinone.json'), 'mstore/allinone.json'),
        ],
        'min_classes': 2000,  # 实测 2987
    },
    {
        'name': 'pg_upgraded(2026-08)',
        'upstreams': _sources('pg_upgraded.jar'),
        'remote': 'mstore/jars/pg_2026.jar',
        'public': 'https://20328.kstore.space/mstore/jars/pg_2026.jar',
        'configs': [
            (os.path.join(BASE, 'mstore', 'allinone.json'), 'mstore/allinone.json'),
        ],
        'min_classes': 800,   # 实测 1070
    },
    {
        # 统一 FTY jar（饭太硬／梵泰英同一作者）。与 fan.txt 同源同性质（都是
        # classes.dex + ftyguard_v7/v8.so + ftyshinidie.guard 的加固壳），
        # 只是发布路径不同：本目标追 DodgeZhang 仓库伪装成 1.jpg 的那一份快照。
        # allinone 顶层 spider + 28 个站直引 fty.jar 都指向它。
        'name': 'FTY unified(1.jpg)',
        'upstreams': [
            'https://raw.githubusercontent.com/DodgeZhang/tvbox/main/fantaiying/jar/1.jpg',
            'https://cdn.jsdelivr.net/gh/DodgeZhang/tvbox@main/fantaiying/jar/1.jpg',
            'https://ghproxy.net/https://raw.githubusercontent.com/DodgeZhang/tvbox/main/fantaiying/jar/1.jpg',
            'https://gh-proxy.com/https://raw.githubusercontent.com/DodgeZhang/tvbox/main/fantaiying/jar/1.jpg',
        ],
        'remote': 'mstore/jars/fty.jar',
        'public': 'https://20328.kstore.space/mstore/jars/fty.jar',
        'configs': [
            (os.path.join(BASE, 'mstore', 'allinone.json'), 'mstore/allinone.json'),
            (os.path.join(BASE, 'mstore', 'allinone_v3.json'), 'mstore/allinone_v3.json'),
        ],
        'no_dex_scan': True,  # 加固版：真实类在 .so/.guard 内，dex 无明文类；只验包完整性
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


def _norm_path(u):
    """取 jar 引用里 ;md5; 之前的 URL 段，返回其 path（小写、去尾斜杠）。

    与域名解耦：无论换成 CDN 域名 / http→https / 路径多一个斜杠，都能识别为同一 jar。
    """
    s = str(u).split(';md5;')[0].split(';')[0].strip()
    try:
        return urlsplit(s).path.rstrip('/').lower()
    except Exception:
        return s.lower()


def try_one(url):
    """下载并校验：合法 zip 且含 .dex。区分 HTTP 层失败与内容层失败。"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        return None, 'HTTP %s %s' % (e.code, e.reason or '')
    except Exception as e:
        return None, '%s: %s' % (type(e).__name__, str(e)[:70])
    if data[:2] != b'PK':
        return None, '非 zip 文件头'
    bio = io.BytesIO(data)
    if not zipfile.is_zipfile(bio):
        return None, 'zip 中央目录损坏（下载被截断）'
    with zipfile.ZipFile(bio) as z:
        if not any(n.endswith('.dex') for n in z.namelist()):
            return None, 'zip 内无 classes.dex'
    return data, None


def head_info(url, timeout=30):
    """HEAD 拿 Content-Length（弱判据，仅用于省带宽，不替代 md5）。"""
    try:
        req = urllib.request.Request(url, method='HEAD',
                                     headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.headers.get('Content-Length')
    except Exception:
        return None


def fetch(urls, tries=2, state=None, name=None):
    """多源下载；上次成功的源优先；4xx（非 429）判定为上游缺失，该源不再重试。"""
    if state is not None and name:
        good = state.get('last_good_upstream', {}).get(name)
        if good in urls:
            urls = [good] + [u for u in urls if u != good]
    last = ''
    for idx, u in enumerate(urls, 1):
        for i in range(tries):
            data, err = try_one(u)
            if data is not None:
                log("  源 %d 下载成功（%d bytes）" % (idx, len(data)))
                if state is not None and name:
                    state.setdefault('last_good_upstream', {})[name] = u
                return data
            last = err or '未知错误'
            log("  源 %d 第 %d 次失败(%s)" % (idx, i + 1, last))
            # 4xx（除 429 限流）属上游缺失，重试无意义
            if err.startswith('HTTP 4') and '429' not in err:
                log("  源 %d 返回 %s，属上游缺失，跳到下一源" % (idx, err))
                break
            time.sleep(2)
    raise RuntimeError('全部源下载失败，最后错误: ' + last)


def dex_classes(data):
    cs = set()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for n in z.namelist():
            if not n.endswith('.dex'):
                continue
            d = z.read(n)
            if len(d) < 0x44 or d[:4] != b'dex\n':
                continue
            sz = struct.unpack('<I', d[0x38:0x3C])[0]
            off = struct.unpack('<I', d[0x3C:0x40])[0]
            for i in range(sz):
                o = struct.unpack('<I', d[off + i * 4:off + i * 4 + 4])[0]
                s = o
                sh = 0
                ln = 0
                while True:
                    if s >= len(d):
                        break
                    b = d[s]
                    ln |= (b & 0x7F) << sh
                    s += 1
                    if not (b & 0x80):
                        break
                    sh += 7
                    if sh > 35:
                        break
                if s + ln > len(d):
                    continue
                c = d[s:s + ln].decode('utf-8', 'ignore')
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


def backup_config(path, remote):
    """上传前把本地配置另存一份带时间戳的备份，便于回滚。"""
    try:
        os.makedirs(BAK_DIR, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
        dst = os.path.join(BAK_DIR, '%s.%s.json' % (os.path.basename(path), ts))
        with open(path, 'rb') as f:
            data = f.read()
        with open(dst, 'wb') as f:
            f.write(data)
        log("  已备份 -> %s" % os.path.relpath(dst, BASE))
    except Exception as e:
        log("  (备份失败，继续: %s)" % str(e)[:60])


def update_config(path, jar_public, new_md5, new_classes, no_dex_scan=False):
    """更新配置里该 jar 的 md5 声明，并剔除新 jar 中已不存在的类的站点。

    关键：**没有 md5 的引用也要补写**，否则客户端不会重新下载新包。
    no_dex_scan=True 时（守护版 jar，dex 无明文类），只改 md5，绝不剔除站点。
    """
    cfg = json.load(open(path, encoding='utf-8'))
    spider = str(cfg.get('spider', ''))
    jar_path = _norm_path(jar_public)
    spider_is = _norm_path(spider) == jar_path

    if spider_is:
        if ';md5;' in spider:
            cfg['spider'] = MD5_RE.sub(lambda m: m.group(1) + new_md5, spider, count=1)
        else:
            cfg['spider'] = '%s;md5;%s' % (jar_public, new_md5)

    removed, sites, appended, replaced = [], [], 0, 0
    for s in cfg.get('sites', []):
        jar = str(s.get('jar', ''))
        api = str(s.get('api', ''))
        uses = (not jar and spider_is) or (_norm_path(jar) == jar_path)
        if uses and jar:
            if ';md5;' in jar:
                s['jar'] = MD5_RE.sub(lambda m: m.group(1) + new_md5, jar, count=1)
                replaced += 1
            else:
                # 补写 md5 —— 与顶层 spider 字段保持一致
                s['jar'] = '%s;md5;%s' % (jar, new_md5)
                appended += 1
        # 守护版 jar 无法扫描类名，跳过剔除逻辑（否则会误删全部 csp 站）
        if uses and api.startswith('csp_') and not no_dex_scan:
            if 'Lcom/github/catvod/spider/%s;' % api[4:] not in new_classes:
                removed.append(str(s.get('key', '')))
                continue
        sites.append(s)

    # 剔除熔断：单次剔除超过阈值即中止，避免上游异常导致配置被大范围删站
    total_before = len(cfg.get('sites', []))
    threshold = max(10, int(total_before * 0.1))
    if len(removed) > threshold:
        log("  !! 单次剔除 %d 站（共 %d，阈值 %d），超过熔断阈值，"
            "已中止本次配置写入（原文件未动）" % (len(removed), total_before, threshold))
        log("  !! 被剔除清单: %s" % ','.join(removed[:30]))
        return None, total_before

    cfg['sites'] = sites
    backup_config(path, path)
    json.dump(cfg, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    log("  %s: %d 站（改写 md5 %d / 补写 md5 %d / 剔除 %d %s）"
        % (os.path.basename(path), len(sites), replaced, appended, len(removed),
           removed if removed else ''))
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

    # HEAD 预检（弱判据）：体积与上次观测一致时跳过下载，省带宽
    if not force:
        obs = state.get('obs', {}).get(name)
        cl = head_info(t['upstreams'][0])
        if cl and obs and obs.get('size') == int(cl):
            log("  上游 Content-Length 与上次一致（%s），跳过下载" % cl)
            state.setdefault('jars', {}).setdefault(name, obs.get('md5'))
            return False

    data = fetch(t['upstreams'], state=state, name=name)
    new_md5 = md5hex(data)
    classes = dex_classes(data)
    guard = sum(1 for c in classes if 'Guard' in c)
    log("  上游: %d bytes, md5=%s, 类 %d (Guard %d)" % (len(data), new_md5, len(classes), guard))

    # 校验（绝对阈值 + 相对漂移双保险）
    prev = state.get('obs', {}).get(name)
    if t.get('no_dex_scan'):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names = z.namelist()
            has_guard_res = any(('guard' in n.lower() or n.endswith('.so')) for n in names)
            if not has_guard_res:
                log("  !! 未发现守护资源(.so/.guard)，疑似异常，跳过")
                return False
            log("  ✓ 守护版 jar 校验通过（资源 %d 项）" % len(names))
        except Exception as e:
            log("  !! jar 无法解析: %s，跳过" % str(e)[:60])
            return False
    else:
        if t.get('min_guard') and guard < t['min_guard']:
            log("  !! Guard 类不足(%d < %d)，疑似异常，跳过" % (guard, t['min_guard']))
            return False
        if t.get('min_classes') and len(classes) < t['min_classes']:
            log("  !! 类数量不足(%d < %d)，疑似异常，跳过" % (len(classes), t['min_classes']))
            return False

    if prev:
        dsz = abs(len(data) - prev['size']) / max(prev['size'], 1)
        if dsz > 0.5:
            log("  !! 体积突变 %.0f%%（%d -> %d），疑似异常，跳过"
                % (dsz * 100, prev['size'], len(data)))
            return False
        if not t.get('no_dex_scan') and prev.get('classes'):
            dc = abs(len(classes) - prev['classes']) / max(prev['classes'], 1)
            if dc > 0.5:
                log("  !! 类数突变 %.0f%%（%d -> %d），疑似异常，跳过"
                    % (dc * 100, prev['classes'], len(classes)))
                return False

    last = state.get('jars', {}).get(name)
    # 基准 md5 恢复顺序：状态文件 → 线上该 jar 文件（权威）→ 配置声明（兜底）
    # 注意：不能无条件读配置顶层 spider！只有当目标 jar 确实是顶层 spider 时它才有效，
    # 否则会把别的 jar 的 md5 当成自己的基准，误判"有更新"并反复上传。
    if last is None:
        try:
            req = urllib.request.Request(t['public'], headers={'User-Agent': 'Mozilla/5.0'})
            last = md5hex(urllib.request.urlopen(req, timeout=180).read())
            log("  基准 md5（线上直链）: %s" % last)
        except Exception as e:
            log("  读取线上失败: %s" % str(e)[:60])
    if last is None and t['configs']:
        jar_path = _norm_path(t['public'])
        for local, _r in t['configs']:
            try:
                cfg = json.load(open(local, encoding='utf-8'))
            except Exception:
                continue
            # 顶层 spider 是同一个 jar 时，取其 md5 作为兜底基准
            if _norm_path(str(cfg.get('spider', ''))) == jar_path:
                m = MD5_RE.search(str(cfg.get('spider', '')))
                if m:
                    last = m.group(2)
                    log("  基准 md5（来自配置顶层 spider）: %s" % last)
                    break
            # 否则在 sites 里找第一个引用该 jar 且带 md5 的站
            for s in cfg.get('sites', []):
                if _norm_path(str(s.get('jar', ''))) == jar_path:
                    m = MD5_RE.search(str(s.get('jar', '')))
                    if m:
                        last = m.group(2)
                        log("  基准 md5（来自配置站点引用）: %s" % last)
                        break
            if last:
                break
    if last is None:
        log("  !! 无法恢复上次 md5，为避免误判跳过本次同步")
        return False

    if last == new_md5 and not force:
        log("  无更新，跳过")
        state.setdefault('jars', {})[name] = new_md5
        state.setdefault('obs', {})[name] = {'size': len(data), 'classes': len(classes),
                                             'md5': new_md5}
        return False

    log("  发现新版本: %s -> %s" % (str(last)[:8], new_md5[:8]))
    if dry:
        log("  --dry-run: 跳过上传")
        return False

    st = dav_put(data, t['remote'], user, pwd, host)
    log("  上传完成 (HTTP %s)" % st)
    upload_ok = isinstance(st, int) and 200 <= st < 300

    # 回读校验：尽力而为（先 WebDAV 再公网 CDN，多次重试）。
    # 关键：只要上传返回 2xx，即视为服务端已接受该文件；即便回读因 kstore
    # 瞬时抖动（超时/断连）失败，也继续更新配置与状态——否则一旦遇到临时网络
    # 抖动，真正的新版本会被卡住、客户端永远拿不到新 jar。下次运行会再次复核，
    # 保证最终一致。注：这也顺带修复了 state 中残留旧 md5 导致的每周重复上传。
    online = None
    for _ in range(6):
        try:
            try:
                online = md5hex(dav_get(t['remote'], user, pwd, host))
            except Exception:
                req = urllib.request.Request(t['public'], headers={'User-Agent': 'Mozilla/5.0'})
                online = md5hex(urllib.request.urlopen(req, timeout=90).read())
            if online == new_md5:
                break
        except Exception:
            pass
        time.sleep(3)
    if online == new_md5:
        log("  线上校验通过")
    elif upload_ok:
        log("  ⚠ 回读校验未通过（线上=%s），但上传已返回 HTTP %s，"
            "视为成功并继续更新配置（下次运行将复核）" % (online, st))
    else:
        log("  !! 上传失败（HTTP %s）且回读校验未通过（线上=%s），中止配置更新"
            % (st, online))
        return False

    for local, remote in t['configs']:
        if not os.path.exists(local):
            continue
        removed, total = update_config(local, t['public'], new_md5, classes,
                                       no_dex_scan=bool(t.get('no_dex_scan')))
        if removed is None:
            # 触发熔断，配置未改写，跳过上传并以失败上报
            log("  !! %s 因熔断未写入，本方目标中止" % os.path.basename(local))
            return False
        dav_put(open(local, 'rb').read(), remote, user, pwd, host)
        log("  已上传 %s" % remote)

    state.setdefault('jars', {})[name] = new_md5
    state.setdefault('obs', {})[name] = {'size': len(data), 'classes': len(classes),
                                         'md5': new_md5}
    return True


def main():
    if '--list' in sys.argv:
        for t in TARGETS:
            print('%-24s remote=%s' % (t['name'], t['remote']))
        return 0

    dry = '--dry-run' in sys.argv
    force = '--force' in sys.argv
    only = None
    if '--only' in sys.argv:
        i = sys.argv.index('--only')
        if i + 1 < len(sys.argv):
            only = sys.argv[i + 1].lower()

    log("=== jar 同步开始 ===")
    user, pwd, host = load_creds()

    state = {}
    if os.path.exists(STATE_FILE):
        try:
            state = json.load(open(STATE_FILE))
        except Exception:
            pass

    targets = TARGETS
    if only:
        targets = [t for t in TARGETS if only in t['name'].lower()]
        if not targets:
            log("没有匹配 --only=%s 的目标" % only)
            return 2

    changed, failed, results = False, [], []
    for t in targets:
        try:
            ok = sync_target(t, state, user, pwd, host, dry, force)
            results.append({'name': t['name'], 'status': 'updated' if ok else 'no_change'})
            if ok:
                changed = True
        except Exception as e:
            msg = str(e)[:150]
            failed.append(t['name'])
            results.append({'name': t['name'], 'status': 'failed', 'error': msg})
            log("  !! [%s] 同步失败: %s" % (t['name'], msg))

    state['last_check'] = datetime.now().isoformat()
    json.dump(state, open(STATE_FILE, 'w'), ensure_ascii=False, indent=2)

    if changed and not dry:
        git_commit("chore(auto): spider jar 自动同步更新")

    summary = {
        'finished_at': datetime.now().isoformat(),
        'changed': changed,
        'results': results,
        'failed': failed,
    }
    log("=== 同步结束（有变更: %s / 失败: %s）==="
        % ('是' if changed else '否', ','.join(failed) or '无'))
    log("SUMMARY_JSON " + json.dumps(summary, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        log("!! 同步失败: %s" % str(e)[:200])
        sys.exit(1)
