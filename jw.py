import m3u8
import requests, ssl, urllib3
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('url', help='m3u8 file URL')
parser.add_argument('filename', help='target file')
args = parser.parse_args()

urllib3.disable_warnings()
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base_uri = args.url[:args.url.rfind("/")+1]
m3u8_response = requests.get(args.url, verify=False)
m3u8_obj = m3u8.loads(m3u8_response.text)
with open(args.filename, 'wb') as f:
	for segment in m3u8_obj.segments:
		print('Segment', segment.uri)
		seg_response = requests.get(base_uri + segment.uri, verify=False)
		f.write(seg_response.content)
