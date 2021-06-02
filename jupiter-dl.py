#!python3

import argparse, logging, os
import m3u8, ssl
from requests import get
from urllib3 import disable_warnings
from time import sleep
import asyncio
from pyppeteer import launch

log = logging.getLogger(__name__)

def parse_arguments(arguments_list=None):
	parser = argparse.ArgumentParser()
	parser.add_argument('--verbose', '-v', action='count', default=0)
	parser.add_argument('url', 
		help='ERR series link for web scraping; m3u8 file URL fir single download; links cachefile for series download')
	parser.add_argument('filename', help='target file', nargs='?', default=None)
	return parser.parse_args(arguments_list)

async def main(args):
	log.addHandler(logging.StreamHandler())
	log.setLevel(logging.DEBUG if args.verbose>0 else logging.INFO)
	log.info(args)

	disable_warnings()
	ctx = ssl.create_default_context()
	ctx.check_hostname = False
	ctx.verify_mode = ssl.CERT_NONE

	if args.url[args.url.rfind(".")+1:] == 'm3u8':
		_fetch_single_episode(args.url, args.filename)
	elif args.url.rfind('-linkscache.txt') > 0:
		with open(args.url, 'r') as cf:
			_download_cached_links(cf)
	else:
		with open('{}-linkscache.txt'.format(args.filename), 'w') as cf:
			await _scrape_links_from(args.url, args.filename, cf)

########

def _fetch_single_episode(url, filename):
	segmentfiles = _fetch_segments(url, '{}.tempdir'.format(filename))
	if segmentfiles:
		_assemble_segments(segmentfiles, filename)

def _fetch_segments(url, tempdirname):
	if os.path.isdir(tempdirname):
		log.info('Temp dir exists, resuming download')
	else:
		os.mkdir(tempdirname)
		log.debug('Temp dir \'{}\' created'.format(tempdirname))

	segmentfiles = []

	base_uri = url[:url.rfind("/")+1]
	m3u8_response = get(url, verify=False)
	m3u8_obj = m3u8.loads(m3u8_response.text)
	for segment in m3u8_obj.segments:
		segmentfilename = '{}/{}'.format(tempdirname, segment.uri[segment.uri.rfind('/')+1:])
		segmentfiles.append(segmentfilename)
		if os.path.isfile(segmentfilename):
			log.debug('skipping {}'.format(segmentfilename))
			continue
		log.info(segment.uri)
		retries = 3
		while retries:
			try:
				seg_response = get(('' if segment.uri[:4]=='http' else base_uri)  + segment.uri, verify=False)
				with open(segmentfilename, 'wb') as sf:
					sf.write(seg_response.content)
				break
			except ConnectionResetError:
				retries -= 1
				log.error('\tConnectionResetError exception, retry #{}'.format(3-retries))
				sleep(2)
		if retries == 0:
			log.error('Failed too many times, finishing')
			return False

	return segmentfiles

def _assemble_segments(segmentfiles, target_filename):
	log.info('Assembling {} files...'.format(len(segmentfiles)))
	with open(target_filename, 'wb') as f:
		for sfname in segmentfiles:
			with open(sfname, 'rb') as sf:
				f.write(sf.read())
				print('.', end='', flush=True)
	print('')
	log.info('Downloaded to {}'.format(target_filename))

########

async def _scrape_links_from(url, target_filename, links_cachefile):
	seasons_el = None
	episodes_el = None		# 2-dim array: [season][episode]
	season_index = 0
	episode_index = 0

	# browser setup
	browser = await launch()
	page = await browser.newPage()
	await page.setViewport({
			'width': 1920,
			'height': 1080,
			'deviceScaleFactor': 1,
		})

	# setup m3u8 interception
	await page.setRequestInterception(True)
	m3u8urls = []
	page.on('request', lambda request: asyncio.ensure_future(_intercept_request(request, m3u8urls)))

	# prep metadata dir
	metadata_dirname = '{}.meta'.format(target_filename)
	os.mkdir(metadata_dirname)

	# launch
	log.debug('opening {}'.format(url))
	await page.goto(url)

	while True:
		episode_filename = '{}-S{:02d}E{:02d}'.format(target_filename, season_index+1, episode_index+1)
		log.info(episode_filename)
		'''await page.waitForSelector(
			'#content-bg > div > app-menu > mat-sidenav-container > mat-sidenav-content > app-content > div > div > div.content-container.ng-star-inserted.not-scrolling > div > div.main-content-lead > p:nth-child(2)',
			{'visible': True}
		)'''

		# storing some meta
		await page.screenshot({'path': os.path.join(metadata_dirname, '{}.png'.format(episode_filename))})
		description = await _fetch_description(page)
		with open(os.path.join(metadata_dirname, '{}.txt'.format(episode_filename)), 'w') as df:
			df.write(description)

		seasons_el = await page.JJ('mat-expansion-panel mat-panel-title')
		episodes_el = await page.JJ('mat-list-item')
		log.debug('elements detected: {} seasons, {} episodes'.format(len(seasons_el), len(episodes_el)))

		# videostream
		if m3u8urls:
			m3u8_response = get(m3u8urls[0], verify=False)
			m3u8_obj = m3u8.loads(m3u8_response.text)
			maxres_url = _select_maxres_m3u8(m3u8_obj)
			log.info(maxres_url)
			links_cachefile.write('{} "{}.mp4"\r\n'.format(maxres_url, episode_filename))
		else:
			log.error('Error: no m3u8 master found!')
		m3u8urls.clear()

		# next episode
		if episode_index+1 < len(episodes_el):
			episode_index += 1
			log.debug('moving to episode {}'.format(episode_index+1))
			await episodes_el[episode_index].click()
			# sleep(5)
		elif season_index+1 < len(seasons_el):
			season_index += 1
			episode_index = 0
			log.debug('moving to season {}'.format(season_index+1))
			await seasons_el[season_index].click()
		else:
			log.debug('{} seasons walked'.format(season_index+1))
			break

	# await page.screenshot({'path': 'example.png'})
	await browser.close()

async def _intercept_request(request, m3u8urls):
	# log.debug('_intercept_request {}'.format(request.url))
	if request.url[request.url.rfind(".")+1:] == 'vtt':
		log.info('subtitles found {}'.format(request.url))
	elif request.url[request.url.rfind(".")+1:] == 'm3u8':
		log.info('stream master found {}'.format(request.url))
		m3u8urls.append(request.url)
	await request.continue_()

def _select_maxres_m3u8(m3u8_obj):
	if m3u8_obj.is_variant:
		max_stream = None
		max_res = (0, 0)
		for v in m3u8_obj.playlists:
			if v.stream_info.resolution > max_res:
				max_res = v.stream_info.resolution
				max_stream = v.uri
		return max_stream
	else:
		return m3u8_obj.uri

async def _fetch_description(page):
	#content-bg > div > app-menu > mat-sidenav-container > mat-sidenav-content > app-content > div > div > div.content-container.ng-star-inserted.not-scrolling > div > div.main-content-lead > p:nth-child(2)
	desc_el = await page.JJ('div.main-content-lead > p:nth-child(2)')
	if desc_el:
		desc_prop = await desc_el[0].getProperty('textContent')
		desc = await desc_prop.jsonValue()
		return desc
	else:
		log.warning('Description element not found')
		return None

########

def _download_cached_links(links_cachefile):
	for ln in map(lambda s: s.strip().partition(' '), links_cachefile):
		log.debug(ln)
		if os.path.isfile(ln[2]):
			log.debug('file downloaded already {}'.format(ln[2]))
		else:
			_fetch_single_episode(ln[0], ln[2])

########

if __name__ == '__main__':
	asyncio.get_event_loop().run_until_complete(main(parse_arguments()))
