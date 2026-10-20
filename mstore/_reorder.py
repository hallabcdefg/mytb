#!/usr/bin/env python3.11
"""按用户指定顺序重排所有直连站分类：电视剧 -> 电影 -> 动漫 -> 综艺 -> 体育 -> 其他"""

import json, re

# ============ 用户指定的六段顺序 ============
ORDER = ['电视剧', '电影', '动漫', '综艺', '体育', '其他']

# ============ 分类名 -> 大类 映射 ============
RULES = {
    '电视剧': [
        '连续剧', '电视剧', '剧集', '国产剧', '大陆剧', '内地剧', '港剧', '香港剧', '港台剧', '港澳剧',
        '台剧', '台湾剧', '韩剧', '韩国剧', '日剧', '日本剧', '日韩剧', '欧美剧', '美国剧',
        '泰剧', '泰国剧', '马泰剧', '海外剧', '其他剧', 'Netflix自制剧',
    ],
    '电影': [
        '电影', '电影片', '动作片', '动作', '喜剧片', '喜剧', '爱情片', '爱情', '科幻片', '科幻',
        '恐怖片', '恐怖', '剧情片', '剧情', '战争片', '战争', '惊悚片', '惊悚', '悬疑片', '悬疑',
        '犯罪片', '犯罪', '冒险', '奇幻片', '奇幻', '武侠', '家庭片', '家庭篇', '古装片',
        '历史片', '灾难片', '西部片', '邵氏电影', '4K电影', 'Netflix电影', '动画电影',
        '理论片', '伦理', '伦理片',
    ],
    '动漫': [
        '动漫', '动漫片', '动画片', '国产动漫', '中国动漫', '日韩动漫', '日本动漫',
        '欧美动漫', '港台动漫', '海外动漫', '动漫电影', 'AI动漫', 'AI漫剧', '里番动漫',
        '有声动漫', '漫剧',
    ],
    '综艺': [
        '综艺', '综艺片', '大陆综艺', '日韩综艺', '港台综艺', '欧美综艺',
        '演唱会', '娱乐新闻',
    ],
    '体育': [
        '体育', '体育赛事', '足球', '篮球', 'NBA', 'LPL', '台球', '斯诺克', '网球', '其他赛事',
    ],
    '其他': [
        # 短剧系
        '短剧', '短剧大全', 'AI短剧', 'ai短剧', '爽文短剧', '擦边短剧',
        '女频恋爱', '女恋总裁', '言情总裁', '现代言情', '现代都市', '都市脑洞',
        '古装仙侠', '年代穿越', '穿越年代', '穿越现代', '重生民国', '反转爽剧', '反转爽文',
        '成长逆袭', '闪婚离婚', '悬疑烧脑', '脑洞悬疑',
        # 解说/记录
        '影视解说', '电影解说', '预告解说', '预告片', '纪录片', '记录片', '短片',
        '科普学习', '演员',
        # 伦理/福利
        '港台三级', '韩国伦理', '日本伦理', '西方伦理', '福利', '两性课堂', '写真热舞',
        # 其它
        '儿童儿歌', '新闻资讯', '电影资讯', '资讯', '公告', '头条', '未分类',
    ],
}

# 前置：父分类占位（空壳），应剔除
PARENTS = {'电影', '连续剧', '电视剧', '动漫', '综艺', '体育', '资讯', '公告', '头条', '体育赛事'}

NAME2CAT = {}
for cat, names in RULES.items():
    for n in names:
        NAME2CAT.setdefault(n, cat)


def cat_of(name):
    """返回分类所属大类；未知返回 None"""
    if name in NAME2CAT:
        return NAME2CAT[name]
    # 模糊兜底
    if any(k in name for k in ('剧',)):
        if any(k in name for k in ('短剧', '爽剧', '漫剧', '喜', '恋', '穿越', '逆袭', '离婚', '脑洞', '悬疑', '仙侠', '都市', '民国', '总裁', '言情')):
            return '其他'
        return '电视剧'
    if '动漫' in name or '动画' in name:
        return '动漫'
    if '综艺' in name:
        return '综艺'
    if name.endswith('片') or '电影' in name:
        return '电影'
    if any(k in name for k in ('球', '赛事', 'NBA', 'LPL')):
        return '体育'
    return None


def reorder(names):
    """按 电视剧->电影->动漫->综艺->体育->其他 重排，返回 (新列表, 未识别列表)"""
    buckets = {c: [] for c in ORDER}
    unknown = []
    for n in names:
        if n in PARENTS:
            continue
        c = cat_of(n)
        if c is None:
            unknown.append(n)
        else:
            buckets[c].append(n)
    out = []
    for c in ORDER:
        out.extend(buckets[c])
    return out, unknown


if __name__ == '__main__':
    import sys
    data = json.load(open(sys.argv[1] if len(sys.argv) > 1 else '/workspace/tvbox-api-repo/mstore/allinone.json'))
    total_unknown = {}
    for s in data['sites']:
        if s.get('type') != 1:
            continue
        cats = s.get('categories') or []
        new, unk = reorder(cats)
        for u in unk:
            total_unknown[u] = total_unknown.get(u, 0) + 1
        s['categories'] = new
    print('未识别分类名:', total_unknown if total_unknown else '无 ✓')
