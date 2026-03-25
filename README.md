# jupiter-dl

HLS video downloader for [ERR Jupiter](https://jupiter.err.ee) (Estonian Public Broadcasting VOD).

## Requirements

- Python 3
- ffmpeg (for muxing video + audio)
- Dependencies: `pip install -r requirements.txt`

## Usage

**Download by m3u8 URL** (single video):
```
python3 jupiter-dl.py <m3u8-url> <output.mp4>
```
Handles both master playlists (auto-selects max resolution, downloads separate audio, muxes with ffmpeg) and media playlists (direct segment download).

**Scrape series from ERR page** (requires pyppeteer):
```
python3 jupiter-dl.py <jupiter-url> <series-name>
```
Walks all seasons/episodes, intercepts m3u8 URLs, saves metadata and screenshots, writes a links cache file.

**Download from links cache**:
```
python3 jupiter-dl.py <series-name>-linkscache.txt
```
Downloads all episodes listed in a previously generated cache file.

**ERR API shortcut** -- extract m3u8 URL directly without browser scraping:
```
https://services.err.ee/api/v2/vodContent/getContentPageData?contentId=<ID>
```
The content ID is the number in the Jupiter page URL. The HLS URL is at `data.mainContent.medias[0].src.hls` in the JSON response.

## Options

- `-v` -- verbose output

## Known issues

- Browser scraping (`pyppeteer`) uses a bundled Chromium that is too old for the current ERR.ee SPA. Use the API shortcut or a newer browser automation tool instead.
