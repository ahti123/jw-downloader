# CLAUDE.md

## Project overview

HLS downloader for ERR Jupiter (Estonian public broadcasting VOD). Single Python script (`jupiter-dl.py`) with three modes: direct m3u8 download, browser-based series scraping, and links cache batch download.

## Key architecture

- `_fetch_single_episode` -- entry point for single downloads; resolves master playlists, downloads video + audio separately, muxes with ffmpeg
- `_fetch_segments` -- downloads HLS segments (supports both TS and fMP4 with init segments); resumes by skipping existing files
- `_scrape_links_from` -- pyppeteer-based browser scraping (currently broken due to old Chromium)
- `_select_maxres_m3u8` / `_select_default_audio` -- variant playlist selection helpers

## ERR API

Content metadata and stream URLs available at:
```
https://services.err.ee/api/v2/vodContent/getContentPageData?contentId=<ID>
```
HLS path: `data.mainContent.medias[0].src.hls` (prefix with `http:`).

Reference: [Kodi plugin](https://github.com/yllar/plugin.video.jupiter.err.ee) for API patterns.

## Development notes

- Python 3, no type annotations used in this project
- Tabs for indentation
- External deps: `requests`, `m3u8`, `pyppeteer`, `urllib3`
- Runtime dep: `ffmpeg` for audio/video muxing
- Downloads use temp directories (`*.tempdir/`) for resume support
- SSL verification is disabled for ERR CDN requests
