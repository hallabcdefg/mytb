# TVBox 接口配置仓库

TVBox / 影视仓（FongMi 系）壳子使用的配置接口仓库。整合多套本地化采集规则、解析与直播源，所有资源（spider、JS 规则、直播单）均随仓库分发，不依赖外部服务器，开箱即用。

## 目录结构

```
index.json            主接口（jar 系 + drpy2 引擎 + XBPQ/XYQHiker 规则站，212 站点 / 14 解析 / 5 直播）
mstore/               多仓配置（27 个本地子仓，约 2000 站点）
  mstoredc.json       多仓清单（App 配置地址填这个）
  mstorebd.json       多仓仓库入口（storeHouse）
  tokens/             网盘 token 占位文件
DX/                   备用接口（drpy2 引擎，54 站点）+ 全部资源
TVBox/                jar 系全部资源（spider.jar、XBPQ/XYQHiker 规则、JS、cookie 占位）
```

## 接口说明

| 用途 | 路径 |
|---|---|
| 主接口 | `index.json` |
| 多仓清单 | `mstore/mstoredc.json` |
| 备用接口 | `DX/index.json` |

在 App 的设置 → 配置地址里填入上述文件经本仓库分发通道的完整地址即可。

## 托管通道

本仓库使用双 CDN 通道分发：

- 配置类文件（json / js / txt）经 jsDelivr 分发，国内节点多、速度快
- jar 类资源经 GitHub Pages 分发（jsDelivr 不服务 .jar 可执行文件）

两个通道均指向同一仓库的 main 分支，内容保持一致。

## 线路构成

**主接口（index.json）**

- jar 系站点 91 个（spider.jar 随仓库分发，不依赖外网）
- drpy2 引擎站点 54 个（本地 drpy2.min.js + 规则 JS）
- XBPQ / XYQHiker 规则站等 67 个
- 解析 14 条、直播 5 个源

**多仓（mstore/）**

- 27 个本地子仓，约 2000 站点
- 全部 jar / JS 随仓库分发，无外网依赖
- 网盘类站点（阿里 / 夸克 / UC）的 token 为占位文件，填入自己的 token 即可用

**备用接口（DX/index.json）**

- 54 站点 drpy2 引擎，主接口失效时的备胎

## 使用说明

1. 安装影视仓（FongMi 系）App，首次打开给予存储权限
2. 设置 → 配置地址 → 填入主接口完整地址 → 确认
3. 主页数据源即载入；点"直播"查看直播源
4. 想用多仓：把配置地址换成多仓清单地址，或在多仓界面添加仓库入口

## 网盘 token

网盘站点需要自行填 token（占位文件路径如下）：

- 阿里云盘 token：`mstore/tokens/*.txt`
- 夸克 / UC：`TVBox/quark.txt`、`TVBox/uc.txt`
- 阿里 token（jar 系）：`TVBox/token.txt`
