import crcmod, datetime, crcmod.predefined, argparse, binascii, sys
from gallipoli import *

parser = argparse.ArgumentParser()
parser.add_argument('filename')
args = parser.parse_args()

filename = args.filename
if filename == '-':
	filename = '/dev/stdin'
f = open(filename,"r")
logger = Logger()
#logger.level = logger.TRACE
#logger.level = logger.DEBUG
parser = Parser(LogReader(f, logger), logger)
cache = {}
print 'start'
while True:
	msg = parser.next()
	if not msg:
		break;
	#if msg.command not in cache.keys() or cache[msg.command] != msg.bytes:
	#	cache[msg.command] = msg.bytes
	if msg.separator:
		print ('%s' % binascii.hexlify(msg.separator))
	print ('%s' % binascii.hexlify(msg.bytes))
	sys.stderr.flush()
	sys.stdout.flush()
f.close()
