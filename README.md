<div align="center">
<img style="max-width:50%;" src="pic/logo.png" alt="NASSAV" />
<br>
</div>

<div align="center">
  <img src="https://img.shields.io/github/stars/Satoing/NASSAV?style=for-the-badge&color=FF69B4" alt="Stars">
  <img src="https://img.shields.io/github/forks/Satoing/NASSAV?style=for-the-badge&color=FF69B4" alt="Forks">
  <img src="https://img.shields.io/github/issues/Satoing/NASSAV?style=for-the-badge&color=FF69B4" alt="Issues">
  <img src="https://img.shields.io/github/license/Satoing/NASSAV?style=for-the-badge&color=FF69B4" alt="License">
</div>

## 项目简介

NASSAV 是一个基于 Python 开发的多源影视资源下载管理工具，支持从多个数据源自动下载、整理和刮削影视资源。

项目采用模块化设计，支持自定义下载器，并提供了完整的元数据管理功能和配套服务。

## 核心特性

- 🎥 多源下载支持：支持 MissAV、Jable、HohoJ、Memo （持续添加中）等多个数据源
- 📝 智能元数据管理：从JavBus自动获取影片信息、封面、海报等元数据
- 🔄 队列管理：支持批量下载任务管理。使用sqlite去重，防止重复下载
- 🌐 远程控制：提供 HTTP API 接口，支持远程控制下载任务
- 🔒 文件锁机制：确保同一时间只有一个下载任务运行
- 🎨 媒体服务器兼容：自动生成 NFO 文件，支持主流媒体服务器

## Jellyfin预览

![](pic/1.png)

## 系统要求

- **稳定的网络连接和代理服务**
- Python 3.11.2 或更高版本
- FFmpeg
- Go 1.22.6 或更高版本（仅用于编译 HTTP 服务器）

## 安装指南

1. 克隆项目并安装依赖：
```bash
git clone https://github.com/Satoing/NASSAV.git
cd NASSAV
pip3 install -r requirements.txt
```

2. 安装 FFmpeg：
```bash
sudo apt install ffmpeg
```

3. 配置项目：
   - 复制 `cfg/configs.json.example` 为 `cfg/configs.json`
   - 修改配置文件中的关键参数：
     - `SavePath`：设置视频保存路径
     - `Proxy`：配置代理服务器地址（如果不需要使用代理，设置成""即可）
     - `Downloader`：配置下载器及其优先级
     - `IsNeedVideoProxy`：下载视频是否优先使用代理（最终都会尝试使用代理和不使用代理）

## 使用方法

### 基本使用

0. 初始化，修改配置文件。主要关注的字段：
    - SavePath：下载保存的位置
    - Proxy：http代理服务器url（如果不需要使用代理，设置成""即可）
    - IsNeedVideoProxy：下载视频是否使用代理
```json
{
    "LogPath": "./logs",
    "SavePath": "/vol2/1000/MissAV",
    "DBPath": "./db/downloaded.db",
    "QueuePath": "./db/download_queue.txt",
    "Proxy": "http://127.0.0.1:7897",
    "IsNeedVideoProxy": false,
}
```

1. 如果本地已有资源，需要先整理目录结构，车牌号大写作为文件夹名字，视频同名放在文件夹里面：

```
...
├── SVGAL-009
│   └── SVGAL-009.mp4
├── STCVS-007
│   └── STCVS-007.mp4
...
```
然后执行`python3 metadata.py`，爬取元数据。最后生成的目录结构：
```
...
├── SVGAL-009
│   ├── metadata.json
│   ├── SVGAL-009-fanart.jpg
│   ├── SVGAL-009.mp4
│   ├── SVGAL-009.nfo
│   └── SVGAL-009-poster.jpg
├── thumb
│   ├── JULIA.jpg
│   ├── ちゃんよた.jpg
│   ├── 七森莉莉.jpg
│   ├── 七泽米亚.jpg
...
```

2. 下载单个资源：
```bash
python3 main.py <车牌号>
```

3. 强制下载（忽略重复检查——下载过程中ctrl-c就会出现这种情况）：
```bash
python3 main.py <车牌号> -f
```

### 使用Docker下載

0. 前置作業如基本使用

1. Build Docker (初次使用才需要)
```bash
(sudo) docker build -t nassav .
```

2. 下載
```bash
(sudo) docker run --rm -v "<本機存片位置>:<cfg/configs.json存片位置>" nassav <車號>
```

### 批量下载

1. 将车牌号添加到 `db/download_queue.txt` 中
2. 设置定时任务：
```bash
20 * * * * cd /path/to/NASSAV && bash cron_task.sh
```

### HTTP API 服务

1. 编译并启动 HTTP 服务器：
```bash
cd backend
go build -o main
./main
```

2. 发送下载请求：
```bash
curl -X POST http://127.0.0.1:49530/process -d "车牌号"
```

### 前后端服务

刮削时下载了大量fanart，故提供一个网页预览。

后端提供了两个API：
1. 获取车牌号列表：/api/videos
2. 获取车牌号详细信息：/api/videos/FPRE-017

请求结果如下：
```
/api/videos
-----------------------------
[{"id":"ACHJ-057","title":"ACHJ-057 時には勝手に痴女りたい…。Madonna専属 究極美熟女『めぐり』お貸ししますー。","poster":"/file/ACHJ-057/ACHJ-057-poster.jpg"},{"id":"ADN-604","title":"ADN-604 お義父さんは私の事、どう思ってますか？ 七海ティナ","poster":"/file/ADN-604/ADN-604-poster.jpg"},{"id":"AGAV-122","title":"AGAV-122 顔で抜く！！顔面ドアップPOV 関西弁でイチャサド射精管理してくる年上彼女との同棲生活 流川莉央","poster":"/file/AGAV-122/AGAV-122-poster.jpg"},...]

/api/videos/FPRE-017
-----------------------------
{"id":"FPRE-017","title":"FPRE-017 爆乳セレブ痴女に見つめられて犯●れたい 菊乃らん","releaseDate":"2024-02-02","fanarts":["/file/FPRE-017/FPRE-017-fanart-1.jpg","/file/FPRE-017/FPRE-017-fanart-10.jpg","/file/FPRE-017/FPRE-017-fanart-11.jpg","/file/FPRE-017/FPRE-017-fanart-12.jpg","/file/FPRE-017/FPRE-017-fanart-13.jpg","/file/FPRE-017/FPRE-017-fanart-14.jpg","/file/FPRE-017/FPRE-017-fanart-15.jpg","/file/FPRE-017/FPRE-017-fanart-16.jpg","/file/FPRE-017/FPRE-017-fanart-17.jpg","/file/FPRE-017/FPRE-017-fanart-18.jpg","/file/FPRE-017/FPRE-017-fanart-19.jpg","/file/FPRE-017/FPRE-017-fanart-2.jpg","/file/FPRE-017/FPRE-017-fanart-20.jpg","/file/FPRE-017/FPRE-017-fanart-21.jpg","/file/FPRE-017/FPRE-017-fanart-3.jpg","/file/FPRE-017/FPRE-017-fanart-4.jpg","/file/FPRE-017/FPRE-017-fanart-5.jpg","/file/FPRE-017/FPRE-017-fanart-6.jpg","/file/FPRE-017/FPRE-017-fanart-7.jpg","/file/FPRE-017/FPRE-017-fanart-8.jpg","/file/FPRE-017/FPRE-017-fanart-9.jpg","/file/FPRE-017/FPRE-017-fanart.jpg"],"videoFile":"/file/FPRE-017/FPRE-017.mp4"}
```

据此使用Vue实现一个前端，预览list和detail。

list页：
![](pic/gallery-list.png)
detail页：
![](pic/gallery-detail.png)

前端部署方式：
1. 先调整`frontend/src/api/videos.js`中后端的配置：
```js
import axios from 'axios'
const API_BASE = 'http://192.168.31.61:31471' // 改成自己的ip
```
2. 重新生成静态文件到dist目录下：
```bash
cd frontend
npm run build
```
3. 使用nginx部署静态网页：`127.0.0.1:5177`

## 配置说明

### 下载器配置

在 `configs.json` 中可以配置多个下载源及其优先级：

```json
"Downloader": [
    {
        "downloaderName": "MissAV",
        "domain": "missav.ai",
        "weight": 300
    },
    {
        "downloaderName": "Jable",
        "domain": "jable.tv",
        "weight": 500
    },
    {
        "downloaderName": "HohoJ",
        "domain": "hohoj.tv",
        "weight": 0
    }
]
```

### 数据源说明

1. **MissAV**
   - 优点：资源全面，反爬限制较少
   - 缺点：清晰度一般（720p-1080p）

2. **Jable**
   - 优点：中文字幕资源多，清晰度高（1080p）
   - 缺点：反爬限制较严格

3. **HohoJ**
   - 优点：清晰度高（1080p），基本无反爬限制
   - 缺点：中文字幕资源较少

4. **Memo**
   - 优点：资源较新，更新及时
   - 缺点：部分资源需要会员


## 技术实现：MissAV 与 Jable 下载流程

本项目对 MissAV 与 Jable 的下载实现采用“策略模式 + 统一下载管道”。核心思路是：
- 用不同的 Downloader 实现负责“找出可用的 m3u8 播放列表（HLS）链接”。
- 找到 m3u8 后，统一用外部下载器将 HLS 拉取为 TS，再用 ffmpeg 无损转封装为 MP4。
- 元数据（标题、演员、封面等）与下载解耦，统一从 JavBus 抓取，生成 NFO 和封面图。

关键技术点：
- HTTP 抓取：使用 curl_cffi.requests 并设置 impersonate="chrome110" 和常见浏览器 UA/Referer 头，绕过部分站点的反爬/风控。
- 代理与回退：可配置代理，下载失败会在“使用/不使用代理”之间回退重试。
- HLS 解析：对 m3u8 主清单解析，优先选择最高码率/分辨率的分流。
- 视频下载：内置 tools/m3u8-Downloader-Go（二进制）负责 HLS 下载；然后 ffmpeg 进行容器转换（TS -> MP4）。
- 任务编排：按 cfg/configs.json 中 Downloader 的权重顺序尝试，直至成功。

总体流程（入口 main.py）：
1) 初始化去重数据库（SQLite）、读取配置、文件锁避免并发下载。
2) 根据权重，从 DownloaderMgr 依次取出下载器并设置域名。
3) 对目标番号调用 downloader.downloadInfo(avid)：
   - 构造详情页 URL 并抓取 HTML（downloader.getHTML）。
   - 从 HTML 中解析出 m3u8 和基本信息（downloader.parseHTML）。
   - 将 download_info.json 与原始 HTML 落盘便于调试。
4) 调用 downloader.downloadM3u8(m3u8, avid)：
   - 使用 m3u8-Downloader-Go 把 HLS 下载为 TS。
   - 用 ffmpeg 无损转封装为 MP4，并删除中间 TS。
5) 下载成功后，仅进行一次元数据刮削（JavBus），生成 NFO、封面与演员图。

MissAV 的实现细节（src/downloader/missAVDownloader.py）：
- URL 构造（多路回退）：
  - https://{domain}/cn/{avid}-uncensored-leak
  - https://{domain}/cn/{avid}-chinese-subtitle
  - https://{domain}/cn/{avid}
  - https://{domain}/dm13/cn/{avid}
  逐个尝试抓取，直到获得有效 HTML。
- m3u8 提取：
  - 在 HTML 中匹配形如 "m3u8|...|com|surrit|https|video" 的片段，
    通过 _extract_uuid 还原 UUID，拼出主清单 https://surrit.com/{uuid}/playlist.m3u8。
  - 请求主清单后，解析 #EXT-X-STREAM-INF 行，按带宽降序选择最高清晰度流（_get_highest_quality_m3u8）。
- 基本信息：
  - 通过 og:title 提取标题，并从中分离番号（如 ABC-123）。

Jable 的实现细节（src/downloader/jableDownloder.py）：
- 详情页 URL： https://{domain}/videos/{avid}/
- 直接在 HTML 中用正则提取 var hlsUrl = '...'; 即为 m3u8 播放地址。
- 同样通过 og:title 提取标题并分离番号。

统一下载实现（src/downloader/downloaderBase.py）：
- downloadInfo(avid)：
  - getHTML 抓取详情页 HTML；
  - parseHTML 解析出 AVDownloadInfo(m3u8/avid/title)；
  - 将 html 与 download_info.json 保存至 SavePath/AVID/。
- downloadM3u8(url, avid)：
  - 根据 IsNeedVideoProxy 与 Proxy 配置选择是否带代理调用 tools/m3u8-Downloader-Go；
  - 下载为 AVID.ts 后，执行 ffmpeg -i AVID.ts -c copy -f mp4 AVID.mp4；
  - 删除中间 TS 文件。
- HTTP 抓取细节：
  - curl_cffi.requests.get(..., impersonate="chrome110", proxies=..., headers=...)

元数据与 NFO（src/scraper.py；与下载解耦）：
- 统一从 JavBus 抓取标题、演员、时长、发行日期、封面、样品图等。
- 下载图像时带上 Referer，使用 Pillow 将横版封面裁剪为竖版 poster。
- 生成 Jellyfin/Kodi 兼容的 NFO（ElementTree + minidom）。

配置与权重（cfg/configs.json）：
- Downloader 数组按 weight 降序；域名通过 domain 配置。
- Proxy、IsNeedVideoProxy 控制代理行为。

防爬与稳定性：
- 使用浏览器指纹模拟（impersonate）、合理请求头与 Referer。
- 失败回退：
  - MissAV 多路径详情页回退；
  - Jable 若提取失败会切换下一个下载器；
  - 下载阶段在“使用/不使用代理”之间回退重试。

以上实现保证了 MissAV 与 Jable 在不同网络环境与反爬策略下有较高的成功率与可维护性。

## 开发指南

### 添加新的下载器

1. 在 `src/downloader/` 目录下创建新的下载器类
2. 继承 `Downloader` 基类，实现必要的方法：
   - `getDownloaderName()`
   - `getHTML()`
   - `parseHTML()`
3. 在 `DownloaderMgr` 中注册新下载器
4. 在配置文件中添加相应的配置项

示例代码：
```python
class NewDownloader(Downloader):
    def getDownloaderName(self) -> str:
        return "NewDownloader"

    def getHTML(self, avid: str) -> Optional[str]:
        # 实现获取HTML的逻辑
        pass

    def parseHTML(self, html: str) -> Optional[AVDownloadInfo]:
        # 实现解析HTML的逻辑
        pass
```
### 有需求请自行fork修改，如果想要贡献代码发起PR即可

![](pic/IMG_5150.JPG)

## 注意事项

- 使用本项目需要稳定的代理服务
- 请遵守相关法律法规，合理使用本工具
- 建议定期备份数据库文件
- 下载过程中请确保网络稳定
- 下载频率不要过高。否则会被cloudflare安排进贤者时间

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。 