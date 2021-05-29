#!python3

import argparse, logging, os
import m3u8, requests, ssl, urllib3
from time import sleep

log = logging.getLogger(__name__)

def parse_arguments(arguments_list=None):
	parser = argparse.ArgumentParser()
	parser.add_argument('--verbose', '-v', action='count', default=0)
	parser.add_argument('url', help='m3u8 file URL')
	parser.add_argument('filename', help='target file')
	return parser.parse_args(arguments_list)

def main(args):
	log.addHandler(logging.StreamHandler())
	log.setLevel(logging.DEBUG if args.verbose>0 else logging.INFO)
	log.info(args)

	urllib3.disable_warnings()
	ctx = ssl.create_default_context()
	ctx.check_hostname = False
	ctx.verify_mode = ssl.CERT_NONE

	segmentfiles = _fetch_segments(args.url, '{}.tempdir'.format(args.filename))
	if segmentfiles:
		_assemble_segments(segmentfiles, args.filename)

def _fetch_segments(url, tempdirname):
	if os.path.isdir(tempdirname):
		log.info('Temp dir exists, resuming download')
	else:
		os.mkdir(tempdirname)
		log.debug('Temp dir \'{}\' created'.format(tempdirname))

	segmentfiles = []

	base_uri = url[:url.rfind("/")+1]
	m3u8_response = requests.get(url, verify=False)
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
				seg_response = requests.get(('' if segment.uri[:4]=='http' else base_uri)  + segment.uri, verify=False)
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

if __name__ == '__main__':
	main(parse_arguments())
