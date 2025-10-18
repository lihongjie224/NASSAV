#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone MissAV/Jable downloader for n8n workflows.

What it does
- Given an AV ID (e.g., ABC-123), it will try to fetch the playable HLS (m3u8) URL
  from MissAV or Jable and download the video to MP4 using ffmpeg.
- It follows the same extraction logic as the project downloaders, but is self-contained.

Requirements
- Python 3.10+
- ffmpeg installed and available in PATH
- pip install curl_cffi

Examples
- Auto try (Jable -> MissAV):
  python3 n8n_missav_jable_downloader.py ABC-123 --save /path/to/save

- Force MissAV only:
  python3 n8n_missav_jable_downloader.py ABC-123 --source missav --missav-domain missav.ai

- Force Jable only:
  python3 n8n_missav_jable_downloader.py ABC-123 --source jable --jable-domain jable.tv

- With proxy and prefer using proxy for video download:
  python3 n8n_missav_jable_downloader.py ABC-123 --proxy http://127.0.0.1:7897 --prefer-proxy true

Notes for proxy
- HTTP grabbing (for HTML/m3u8) uses the proxy via curl_cffi if provided.
- ffmpeg respects HTTP(S)_PROXY environment variables set by this script during download attempts.
"""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Tuple

try:
    from curl_cffi import requests
except Exception as e:
    print("Missing dependency: curl_cffi. Please run: pip install curl_cffi")
    raise

# ------- Common headers (match repo style) -------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


@dataclass
class AVDownloadInfo:
    m3u8: str = ""
    title: str = ""
    avid: str = ""

    def to_json(self, file_path: str, indent: int = 2) -> bool:
        try:
            path = Path(file_path) if isinstance(file_path, str) else file_path
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('w', encoding='utf-8') as f:
                json.dump(asdict(self), f, ensure_ascii=False, indent=indent)
            return True
        except Exception as e:
            print(f"Failed to write json: {e}")
            return False


class DownloaderBase:
    def __init__(self, save_path: str, proxy: Optional[str] = None, timeout: int = 15):
        self.save_path = save_path
        self.proxy = proxy
        self.proxies = {'http': proxy, 'https': proxy} if proxy else None
        self.timeout = timeout
        self.domain = None

    def set_domain(self, domain: str) -> bool:
        if domain:
            self.domain = domain
            return True
        return False

    def _fetch_html(self, url: str, referer: str = "") -> Optional[str]:
        try:
            headers = dict(HEADERS)
            if referer:
                headers["Referer"] = referer
            resp = requests.get(
                url,
                proxies=self.proxies,
                headers=headers,
                timeout=self.timeout,
                impersonate="chrome110",
            )
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            print(f"HTTP request failed: {e}")
            return None

    # Abstracts
    def get_downloader_name(self) -> str:
        raise NotImplementedError

    def get_html(self, avid: str) -> Optional[str]:
        raise NotImplementedError

    def parse_html(self, html: str) -> Optional[AVDownloadInfo]:
        raise NotImplementedError

    def download_info(self, avid: str) -> Optional[AVDownloadInfo]:
        avid = avid.upper()
        out_dir = Path(self.save_path) / avid
        out_dir.mkdir(parents=True, exist_ok=True)

        html = self.get_html(avid)
        if not html:
            print("获取 HTML 失败")
            return None

        # Save raw html for debugging
        try:
            (out_dir / f"{avid}.html").write_text(html, encoding='utf-8')
        except Exception:
            pass

        info = self.parse_html(html)
        if not info:
            print("解析元数据失败")
            return None
        info.avid = info.avid.upper() if info.avid else avid
        info.to_json(out_dir / "download_info.json")
        return info


class MissAVDownloader(DownloaderBase):
    def get_downloader_name(self) -> str:
        return "MissAV"

    def get_html(self, avid: str) -> Optional[str]:
        # Try multiple URL patterns in order
        paths = [
            f"https://{self.domain}/cn/{avid}-uncensored-leak",
            f"https://{self.domain}/cn/{avid}-chinese-subtitle",
            f"https://{self.domain}/cn/{avid}",
            f"https://{self.domain}/dm13/cn/{avid}",
        ]
        for url in paths:
            content = self._fetch_html(url)
            if content:
                return content
        return None

    def parse_html(self, html: str) -> Optional[AVDownloadInfo]:
        info = AVDownloadInfo()
        # 1) Extract UUID string per repo logic
        uuid = self._extract_uuid(html)
        if not uuid:
            print("MissAV: 未找到有效 uuid")
            return None
        playlist_url = f"https://surrit.com/{uuid}/playlist.m3u8"
        best = self._get_highest_quality_m3u8(playlist_url)
        if not best:
            print("MissAV: 未找到有效视频流")
            return None
        m3u8_url, _res = best
        info.m3u8 = m3u8_url

        # 2) Extract metadata (og:title -> avid/title)
        self._extract_metadata(html, info)
        return info

    @staticmethod
    def _extract_uuid(html: str) -> Optional[str]:
        try:
            m = re.search(r"m3u8\|([a-f0-9\|]+)\|com\|surrit\|https\|video", html)
            if not m:
                return None
            return "-".join(m.group(1).split("|")[::-1])
        except Exception:
            return None

    @staticmethod
    def _extract_metadata(html: str, meta: AVDownloadInfo) -> bool:
        try:
            m = re.search(r'<meta property="og:title" content="(.*?)"', html)
            if m:
                title_content = m.group(1)
                cm = re.search(r'^([A-Z]+(?:-[A-Z]+)*-\d+)', title_content)
                if cm:
                    meta.avid = cm.group(1)
                    meta.title = title_content.replace(meta.avid, '').strip()
                else:
                    meta.title = title_content.strip()
            return True
        except Exception:
            return False

    @staticmethod
    def _get_highest_quality_m3u8(playlist_url: str) -> Optional[Tuple[str, str]]:
        try:
            r = requests.get(playlist_url, timeout=10, impersonate="chrome110")
            r.raise_for_status()
            content = r.text
            streams = []
            pattern = re.compile(r'#EXT-X-STREAM-INF:BANDWIDTH=(\d+),.*?RESOLUTION=(\d+x\d+).*?\n(.*)')
            for m in pattern.finditer(content):
                bandwidth = int(m.group(1))
                resolution = m.group(2)
                url = m.group(3).strip()
                streams.append((bandwidth, resolution, url))
            streams.sort(reverse=True, key=lambda x: x[0])
            if streams:
                best = streams[0]
                base = playlist_url.rsplit('/', 1)[0]
                full = f"{base}/{best[2]}" if not best[2].startswith('http') else best[2]
                return full, best[1]
            return None
        except Exception as e:
            print(f"获取最高质量流失败: {e}")
            return None


class JableDownloader(DownloaderBase):
    def get_downloader_name(self) -> str:
        return "Jable"

    def get_html(self, avid: str) -> Optional[str]:
        url = f"https://{self.domain}/videos/{avid}/".lower()
        return self._fetch_html(url)

    def parse_html(self, html: str) -> Optional[AVDownloadInfo]:
        info = AVDownloadInfo()
        # Extract m3u8
        m = re.search(r"var hlsUrl = '(https?://[^']+)'", html)
        if not m:
            print("Jable: 未找到 m3u8")
            return None
        info.m3u8 = m.group(1)
        # Basic metadata from og:title
        self._extract_metadata(html, info)
        return info

    @staticmethod
    def _extract_metadata(html: str, meta: AVDownloadInfo) -> bool:
        try:
            m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            if m:
                title_content = m.group(1)
                cm = re.search(r'([A-Z]+(?:-[A-Z]+)*-\d+)', title_content)
                if cm:
                    meta.avid = cm.group(1)
                    meta.title = title_content.replace(meta.avid, '').strip()
                else:
                    meta.title = title_content.strip()
            return True
        except Exception:
            return False


# -------- ffmpeg based downloader (TS->MP4 or direct MP4) --------
def _run_ffmpeg(cmd: str, env: Optional[dict] = None) -> bool:
    print(f"[ffmpeg] {cmd}")
    try:
        res = subprocess.run(shlex.split(cmd), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if res.returncode != 0:
            print(res.stdout)
            return False
        return True
    except FileNotFoundError:
        print("ffmpeg not found. Please install ffmpeg and ensure it is in PATH.")
        return False


def download_m3u8_to_mp4(m3u8_url: str, out_dir: Path, avid: str, prefer_proxy: bool, proxy: Optional[str]) -> bool:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_ts = out_dir / f"{avid}.ts"
    out_mp4 = out_dir / f"{avid}.mp4"

    # Decide attempt order based on prefer_proxy
    attempts = ["proxy", "noproxy"] if (prefer_proxy and proxy) else ["noproxy", "proxy"]

    # Prepare environment baseline
    base_env = os.environ.copy()

    for mode in attempts:
        env = base_env.copy()
        if mode == "proxy" and proxy:
            env["http_proxy"] = proxy
            env["https_proxy"] = proxy
            print("Using proxy for ffmpeg download")
        else:
            env.pop("http_proxy", None)
            env.pop("https_proxy", None)
            print("Not using proxy for ffmpeg download")

        # Try direct MP4 remux first
        cmd_mp4 = f"ffmpeg -y -loglevel error -i {shlex.quote(m3u8_url)} -c copy -bsf:a aac_adtstoasc {shlex.quote(str(out_mp4))}"
        if _run_ffmpeg(cmd_mp4, env):
            return True

        # Fallback: TS then MP4 (some streams are more stable with TS first)
        cmd_ts = f"ffmpeg -y -loglevel error -i {shlex.quote(m3u8_url)} -c copy -f mpegts {shlex.quote(str(out_ts))}"
        if not _run_ffmpeg(cmd_ts, env):
            continue
        cmd_conv = f"ffmpeg -y -loglevel error -i {shlex.quote(str(out_ts))} -c copy -bsf:a aac_adtstoasc {shlex.quote(str(out_mp4))}"
        if _run_ffmpeg(cmd_conv, env):
            try:
                out_ts.unlink(missing_ok=True)
            except Exception:
                pass
            return True

    return False


# -------- Main wiring for n8n usage --------
def main():
    parser = argparse.ArgumentParser(description="MissAV/Jable downloader for n8n")
    parser.add_argument('avid', type=str, help='AV ID, e.g., ABC-123')
    parser.add_argument('--save', dest='save_path', type=str, required=True, help='Save directory')
    parser.add_argument('--source', choices=['auto', 'missav', 'jable'], default='auto', help='Choose source')
    parser.add_argument('--missav-domain', type=str, default='missav.ai', help='MissAV domain')
    parser.add_argument('--jable-domain', type=str, default='jable.tv', help='Jable domain')
    parser.add_argument('--proxy', type=str, default=None, help='HTTP proxy URL, e.g., http://127.0.0.1:7897')
    parser.add_argument('--prefer-proxy', type=str, default='false', help='Prefer using proxy for video download (true/false)')
    parser.add_argument('--timeout', type=int, default=15, help='Request timeout seconds')

    args = parser.parse_args()

    avid = args.avid.upper()
    save_path = args.save_path
    prefer_proxy = str(args.prefer_proxy).lower() in ("1", "true", "yes")

    # Prepare downloaders
    missav = MissAVDownloader(save_path, proxy=args.proxy, timeout=args.timeout)
    missav.set_domain(args.missav_domain)

    jable = JableDownloader(save_path, proxy=args.proxy, timeout=args.timeout)
    jable.set_domain(args.jable_domain)

    # Choose order (default: Jable first, then MissAV like weight 500 > 300)
    order = []
    if args.source == 'auto':
        order = [jable, missav]
    elif args.source == 'jable':
        order = [jable]
    else:
        order = [missav]

    last_err = None
    for dl in order:
        print(f"尝试使用下载器: {dl.get_downloader_name()}")
        try:
            info = dl.download_info(avid)
            if not info or not info.m3u8:
                print(f"{dl.get_downloader_name()}: 获取 m3u8 失败")
                continue
            print(f"m3u8: {info.m3u8}")
            out_dir = Path(save_path) / avid
            ok = download_m3u8_to_mp4(info.m3u8, out_dir, avid, prefer_proxy, args.proxy)
            if ok:
                print(f"下载完成: {out_dir / (avid + '.mp4')}")
                return 0
            else:
                print(f"{dl.get_downloader_name()}: ffmpeg 下载失败，尝试下一个源")
        except Exception as e:
            print(f"{dl.get_downloader_name()} 失败: {e}")
            last_err = e
            continue

    print("所有下载器均失败")
    if last_err:
        print(str(last_err))
    return 2


if __name__ == '__main__':
    sys.exit(main())
