# coding=utf-8
#!/usr/bin/python


import os
import sys
import json
from base.spider import Spider
sys.path.append(os.getcwd())
sys.path.append('..')


class Spider(Spider):
    def getName(self):
        return "IKanBot"

    def getDependence(self):
        return []

    def init(self, extend=""):
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'
        }

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        result = {}
        classes = []

        if(filter):
            result['filters'] = self.config['filter']

        cateManual = {
            "电影": "movie",
            "剧集": "tv"
        }

        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })

        result['class'] = classes

        return result

    def homeVideoContent(self):
        result = {}
        videos = []

        rsp = self.fetch("https://www.ikanbot.com/", headers=self.headers)
        root = self.html(rsp.text)

        aList = root.xpath(
            "//div[contains(@class,'row list-wp')]/div[contains(@class,'item')]/a")

        for a in aList:
            vid = a.xpath("./@href")[0]
            vid = self.regStr(vid, "/play/(\\d+)")
            name = a.xpath("./p/text()")[0]
            pic = a.xpath(
                "./div[contains(@class,'cover-wp')]/img/@data-src")[0]
            remarks = ""
            videos.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remarks
            })

        result = {
            'list': videos
        }

        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        videos = []

        if extend:
            fclass = extend['1']
        else:
            fclass = "热门"

        if pg == "1":
            fpg = ""
        else:
            fpg = '-p-{0}'.format(pg)
        url = 'https://www.ikanbot.com/hot/index-{0}-{1}{2}.html'.format(
            tid, fclass, fpg)

        rsp = self.fetch(url, headers=self.headers)
        root = self.html(rsp.text)

        aList = root.xpath(
            "//div[contains(@class,'row list-wp')]/div[contains(@class,'item')]/a")

        for a in aList:
            vid = a.xpath("./@href")[0]
            vid = self.regStr(vid, "/play/(\\d+)")
            name = a.xpath("./p/text()")[0]
            pic = a.xpath(
                "./div[contains(@class,'cover-wp')]/img/@data-src")[0]
            remarks = ""
            videos.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remarks
            })

        result = {
            'list': videos
        }

        return result

    def detailContent(self, array):
        vid = array[0]
        result = {}
        vod_play_from = '$$$'
        playFrom = []
        vod_play_url = '$$$'
        playList = []

        url = 'https://www.ikanbot.com/play/{0}'.format(vid)
        rsp = self.fetch(url, headers=self.headers)
        root = self.html(rsp.text)

        divContent = root.xpath(
            "//div[contains(@class,'result-info')]/div[contains(@class,'item-root')]")[0]
        name = divContent.xpath(
            "./div[contains(@class,'detail')]/h2[contains(@class,'title')]/text()")[0]
        pic = divContent.xpath(
            "./img/@src")[0]
        type = ""
        year = divContent.xpath(
            "./div[contains(@class,'detail')]/h3[contains(@class,'year')]/text()")[0]
        area = divContent.xpath(
            "./div[contains(@class,'detail')]/h3[contains(@class,'country')]/text()")[0]
        actor = ""
        dir = divContent.xpath(
            "./div[contains(@class,'detail')]/h3[contains(@class,'celebrity')]/text()")[0]
        detail = ""

        vod = {
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": pic,
            "type_name": type,
            "vod_year": year,
            "vod_area": area,
            "vod_remarks": "",
            "vod_actor": actor,
            "vod_director": dir,
            "vod_content": detail
        }

        url = 'https://www.ikanbot.com/api/getResN?videoId={0}&mtype=1'.format(
            vid)
        rsp = self.fetch(url, headers=self.headers)
        rsp = rsp.json()
        lnum = 1

        for v in rsp["data"]["list"]:
            playFrom.append("线路" + str(lnum))
            lnum = int(lnum)
            lnum += 1

        vod_play_from = vod_play_from.join(playFrom)

        for vl in rsp["data"]["list"]:
            vodItems = []
            aList = json.loads(vl['resData'])
            for tA in aList:
                vodItems.append(tA['url'])
            joinStr = '#'
            joinStr = joinStr.join(vodItems)
            playList.append(joinStr)

        vod_play_url = vod_play_url.join(playList)

        vod['vod_play_from'] = vod_play_from
        vod['vod_play_url'] = vod_play_url

        result = {
            'list': [
                vod
            ]
        }

        return result

    def searchContent(self, key, quick):
        result = []
        videos = []

        url = 'https://www.ikanbot.com/search?q={0}'.format(
            key)
        rsp = self.fetch(url, headers=self.headers)
        root = self.html(rsp.text)

        vodList = root.xpath(
            "//div[contains(@id,'search-result')]/div[contains(@class,'media')]")

        for vod in vodList:
            vid = vod.xpath("./div[contains(@class,'media-top')]/a/@href")[0]
            vid = self.regStr(vid, "/play/(\\d+)")
            name = vod.xpath(
                "./div[contains(@class,'media-body')]/h5/a/text()")[0]
            pic = vod.xpath(
                "./div[contains(@class,'media-top')]/a/img/@src")[0]
            mark = ""

            videos.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": ""
            })

        result = {
            'list': videos
        }

        return result

    def playerContent(self, flag, url, vipFlags):
        result = {}
        result["parse"] = ""
        result["playUrl"] = ""
        result["url"] = url
        result["header"] = json.dumps(self.headers)

        return result

    config = {
        "player": {},
        "filter": {
            "movie": [
                {
                    "key": 1,
                    "name": "类别",
                    "value": [
                        {"n": "热门", "v": "热门"},
                        {"n": "最新", "v": "最新"},
                        {"n": "经典", "v": "经典"},
                        {"n": "华语", "v": "华语"},
                        {"n": "欧美", "v": "欧美"},
                        {"n": "韩国", "v": "韩国"},
                        {"n": "日本", "v": "日本"},
                        {"n": "动作", "v": "动作"},
                        {"n": "喜剧", "v": "喜剧"},
                        {"n": "爱情", "v": "爱情"},
                        {"n": "科幻", "v": "科幻"},
                        {"n": "悬疑", "v": "悬疑"},
                        {"n": "恐怖", "v": "恐怖"},
                        {"n": "成长", "v": "成长"},
                        {"n": "豆瓣高分", "v": "豆瓣高分"},
                        {"n": "豆瓣Top250", "v": "豆瓣Top250"},
                        {"n": "冷门佳片", "v": "冷门佳片"}

                    ]
                }
            ],
            "tv": [
                {
                    "key": 1,
                    "name": "类别",
                    "value": [
                        {"n": "热门", "v": "热门"},
                        {"n": "美剧", "v": "美剧"},
                        {"n": "英剧", "v": "英剧"},
                        {"n": "韩剧", "v": "韩剧"},
                        {"n": "日剧", "v": "日剧"},
                        {"n": "国产剧", "v": "国产剧"},
                        {"n": "港剧", "v": "港剧"},
                        {"n": "动画", "v": "动画"},
                        {"n": "综艺", "v": "综艺"},
                        {"n": "纪录片", "v": "纪录片"}
                    ]
                }
            ]
        }
    }
    header = {}

    def localProxy(self, param):
        action = {
            'url': '',
            'header': '',
            'param': '',
            'type': 'string',
            'after': ''
        }
        return [200, "video/MP2T", action, ""]
