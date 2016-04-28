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
state = State()

print('start')
while True:
	msg = parser.next()
	if not msg:
		print('stop')
		break;
	#if msg.command not in cache.keys() or cache[msg.command] != msg.bytes:
	#	cache[msg.command] = msg.bytes
	datetime = msg.getDatetime()
	try:
		note = msg.note
	except AttributeError:
		note = ''

	#if msg.separator:
	#	print (' %s=%i' % (binascii.hexlify(msg.separator) , len(msg.separator)) )

	t1=''
	t2=''
	t3=''
	t4=''
	ret=''
	if datetime:
		print ('%s=%i \n -> %s logtime:"%s"' % (msg.dump(), len(msg.bytes) , datetime.isoformat(' '), note))
	elif msg.istTemperatur():
		t1 = 'Aussen=%.2f' % msg.getTemperaturAussen()
		t2 = 'KesselSoll=%.2f' % msg.getTemperaturKesselSoll()
		t3 = 'KesselIst=%.2f' % msg.getTemperaturKesselIst()
		t4 = 'P33=%.2f' % msg.getP33()
		print ('%s=%i\n -> %s %s %s logtime:"%s"' % (msg.dump(), len(msg.bytes) , t1, t2, t3, note))
	elif msg.istSync():
		print ('%s=%i' % (binascii.hexlify(msg.bytes), len(msg.bytes) ))
	else:
		print ('%s=%i\n -> %s' % (msg.dump(), len(msg.bytes), msg.toString()) )
#	ret = state.consumeMessage(msg)
	if ret:
		print ret + ' %s %s %s %s' % (t1, t2, t3, t4)
		sys.stderr.flush()
		sys.stdout.flush()
f.close()
