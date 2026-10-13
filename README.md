# TVBox / 影视仓 接口部署仓库

由 5 个本地包（点心T3、半本地包tvbox、潇洒单线路、xmbjm、xmbjm 7.04更新）+ 2 个 GitHub 仓库知识整合而成。
所有本地路径（`./`、`clan://localhost`、`http://127.0.0.1:9978`）已全部改写为远程绝对地址，开箱即用。

## 接口地址

> 以下地址基于 `https://cdn.jsdelivr.net/gh/hallabcdefg/mytb@main`（GitHub + jsDelivr 国内可达 CDN）。
> 若你的 GitHub 用户名/仓库名不同，把全局替换成你自己的即可。

| 用途 | 地址 |
|---|---|
| **主接口**（推荐，单仓 212 站点） | `https://cdn.jsdelivr.net/gh/hallabcdefg/mytb@main/index.json` |
| **小猫多仓**（27 个本地子仓，约 2000 站点） | `https://cdn.jsdelivr.net/gh/hallabcdefg/mytb@main/xmbjm/xmbjmdc.json` |
| **点心备用接口**（54 站点 drpy2） | `https://cdn.jsdelivr.net/gh/hallabcdefg/mytb@main/DX/index.json` |

多仓 App（影视仓 / 影迷 / EasyBox）也可以直接加这个仓库入口：
`https://cdn.jsdelivr.net/gh/hallabcdefg/mytb@main/xmbjm/xmbjmbd.json`

## 影视仓配置方法

1. 安装影视仓（FongMi 系）App，首次打开给予存储权限
2. 设置 → 配置地址 → 粘贴上面的**主接口**地址 → 确认
3. 主页数据源即载入；点"直播" Tab 看直播，点"推送"可用 Alist/WebDAV 挂载（多仓 App）
4. 想用小猫多仓：设置里把配置地址换成**小猫多仓**地址，或在多仓界面添加仓库

## 线路构成

**主接口（index.json）**
- 潇洒单线路 jar 系 91 站点（`TVBox/spider.jar`，本地 jar 不依赖外网）
- 点心T3 drpy2 系 54 站点（本地 drpy2.min.js + 规则 JS）
- XBPQ / XYQHiker 规则站等 67 站点
- 解析 14 条（全部实测存活）、直播 5 个源（电视直播M3U/TXT、云星日记、咪咕IPTV、范明明IPV6）

**小猫多仓（xmbjm/，源自「小猫不寂寞」7.04 本地包）**
- 27 个本地子仓：道长 drpy（293 站）、JS影视剧（215）、夜猫子（144）、以一敌十（134）、香雅情（131）、多多家庭版（128）、星辰（127）、运输车（106）、小胡（93）、菜妮丝（84）、饭太硬（65）、肥猫（64）、南风（60）等
- 全部 jar/JS 随仓库分发，无外网依赖
- 网盘类站点（阿里/夸克/UC）的 token 已改为占位文件，填入自己的 token 即可用

**点心备用（DX/index.json）**：54 站点 drpy2 引擎，主接口失效时的备胎

## 本次优化记录（砍掉失效线路）

对全部 1402 个远程引用做了存活探测（DNS / TCP / HTTP 三级判别，区分"真死"与"地域屏蔽"）：

- 砍掉主接口失效站点 2 个（HG影视APP、快看APP）、失效解析 13 条、失效直播 1 条、重复解析 4 条
- 小猫多仓砍掉失效采集站等 112 个站点、失效解析 166 条、失效直播 1 条、失效 spider 配置 1 个
- 剔除 4 个成人频道条目与 4 个已失效的外链多仓（作者站 s2.pub、小暴脾气、荷城茶秀外链、运输车外链——其中小暴脾气改指向本地小米仓，运输车外链与本地仓重复）
- 地域屏蔽但国内已知可用的源（如范明明IPV6）保留

## token 占位文件

网盘站点需要自行填 token（路径见仓库内 `xmbjm/tokens/` 与 `TVBox/*.txt`）：

- 阿里云盘 token：`xmbjm/tokens/*.txt`（原包使用说明里有获取教程）
- 夸克/UC：`TVBox/quark.txt`、`TVBox/uc.txt`
- 阿里 token（潇洒系）：`TVBox/token.txt`

## 目录结构

```
index.json            主接口（影视仓直接填这个）
xmbjm/                小猫不寂寞 7.04 多仓（27 子仓，约 2000 站点）
  xmbjmdc.json        多仓清单（ App 填这个）
  xmbjmbd.json        多仓仓库入口（storeHouse）
  tokens/             网盘 token 占位
DX/                   点心T3 备用接口 + 全部资源
TVBox/                潇洒单线路全部资源（spider.jar、XBPQ/XYQHiker 规则、JS、cookie 占位）
```

## 推送到 GitHub（部署步骤）

```bash
cd tvbox-api-repo
git init
git add .
git commit -m "tvbox api: merged xiaosa + dianxin + xmbjm 7.04, dead lines removed"
git branch -M main
git remote add origin https://github.com/hallabcdefg/mytb.git
git push -u origin main
```

推送后等 1-2 分钟 jsDelivr 缓存刷新，接口即可用。
改仓库名/用户名时，全局替换所有 json 里的 `https://cdn.jsdelivr.net/gh/hallabcdefg/mytb@main`。
