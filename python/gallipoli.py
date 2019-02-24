#!/usr/bin/env python
### BEGIN INIT INFO
# Provides:          gallipoli
# Required-Start:    $all
# Required-Stop:     $all
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: gallipoli
# Description:       gallipoli daemon
### END INIT INFO

####################################
# Python and global infos
__dev__ = ""
__version__ = "0.5" + __dev__
__all__ = ["Logger","LogReader","Parser","State","Message"]

####################################
# Configuration
__serialDevice__ = '/dev/ttyUSB0'
__port__ = 64334
__address__ = '' # '' listen on all devices, for localhost use '127.0.0.1'
__serverversion__ = "gallipoli/" + __version__

__pidfile__ = '/tmp/gallipoli' + __dev__ + '.pid'
__logfile__ = '/var/log/gallipoli' + __dev__ + '.log'
__errfile__ = '/var/log/gallipoli' + __dev__ + '.err'

__html_header__ = '<html><head><style>body { font-family: "Droid Sans Mono",Consolas,"Courier New","Liberation Mono",monospace; white-space: nowrap; } </style> </head> <body>'
__html_footer__ = '</body></html>'

####################################

import sys, time, serial, datetime, struct, binascii, copy
import crcmod, crcmod.predefined
import threading, signal
from daemon import Daemon
import BaseHTTPServer, urllib, cgi, mimetypes, SocketServer, operator

__data__ = {}
__time__ = {}
__modified__ = {}
__lock__ = threading.Lock()

class Logger(object):
	def __init__(self, logFile = '/dev/stdout', errFile = '/dev/stdout'):
		self.logFile = logFile
		self.errFile = errFile

		self.ERROR = 0
		self.INFO = 1
		self.DEBUG = 2
		self.TRACE = 3
	
		self.level = self.INFO

	def log(self, msg):
		i = datetime.datetime.now()
		msg = ("%s %s" % (i, msg))
		if self.logFile == '/dev/stdout':
			 print(msg)
		else:
			file(self.logFile,'a+').write(msg+'\n')

	def logError(self, msg):
		i = datetime.datetime.now()
		msg = ("%s %s" % (i, msg))
		if self.errFile == '/dev/stdout':
			print(msg)
		elif self.errFile != self.logFile:
			file(self.errFile,'a+').write(msg+'\n')
			file(self.logFile,'a+').write(msg+'\n')
		else:
			file(self.errFile,'a+').write(msg+'\n')
	
	def trace(self, msg):
		if self.level >= self.TRACE:
			print ('TRACE ' + msg)

	def debug(self, msg):
		if self.level >= self.DEBUG:
			print ('DEBUG ' + msg)

class LogReader(object):
	def __init__(self, file, logger = Logger()):
		self.file = file
		self.line = ''
		self.linenumber = 0
		self.logger = logger
	def read(self, n):
		if not self.line:
			self.line = '#'
			while self.line and (self.line.startswith('#') 
					or self.line.rstrip('\n\r ').endswith('Deamon start')
					or self.line.rstrip('\n\r ').endswith('SYNC') ):
				self.line = self.file.readline()
				self.linenumber += 1
			self.line = self.line.rstrip('\n\r ')
			i = self.line.rfind(' ')
			if i > -1:
				self.note = self.line[0:i]
				self.line = self.line[i+1:]
		if not self.line:
			return ''
		ret = ''
		i = min(n, len(self.line)/2)
		i = max(i,1)
		c = self.line[0:i*2]
		try:
			ret += binascii.unhexlify(c)
		except TypeError as e:
			self.logger.logError('ERROR TypeError at line %s' % self.linenumber)
		self.line = self.line[i*2:]
		#self.logger.trace('LogReader ret:%s len:%s rest:%s i=%s,n=%s' % (binascii.hexlify(ret), len(ret), self.line, i, n))
		if i<n:
			ret += self.read(n-i)	
		return ret

class Parser(object):
	def __init__(self, port, logger = Logger()):
                self.headerFill = {'\x90\x90\x90\x90\x90',
					'\x21\x21\x21\x21\x21',
					'\x22\x22\x22\x22\x22',
					'\xa3\xa3\xa3\xa3\xa3',
					'\x11\x11\x11\x11\x11',
					'\x12\x12\x12\x12\x12',
					'\x93\x93\x93\x93\x93',
					'\x14\x14\x14\x14\x14',
					'\x95\x95\x95\x95\x95',
					'\x96\x96\x96\x96\x96',
					'\x17\x17\x17\x17\x17',
					'\x18\x18\x18\x18\x18',
					'\x99\x99\x99\x99\x99',
					'\x9a\x9a\x9a\x9a\x9a',
					'\x1b\x1b\x1b\x1b\x1b',
					'\x9c\x9c\x9c\x9c\x9c',
					'\x1d\x1d\x1d\x1d\x1d',
					'\x1e\x1e\x1e\x1e\x1e',
					'\x9f\x9f\x9f\x9f\x9f'
					}
		self.headerFill = self.headerFill.union({'\x2b\x2b\x2b\x2b\x2b',
					'\xac\xac\xac\xac\xac',
					'\x14\x14\x14\x14\x14',
					'\x95\x95\x95\x95\x95',
					'\x96\x96\x96\x96\x96',
					'\x17\x17\x17\x17\x17',
					'\x18\x18\x18\x18\x18',
					'\x99\x99\x99\x99\x99',
					'\x9a\x9a\x9a\x9a\x9a',
					'\x1b\x1b\x1b\x1b\x1b',
					'\x9c\x9c\x9c\x9c\x9c'
					}) 
                self.knownCommands = {'\x20\x04', '\x09\x05'}
		self.knownCommands = self.knownCommands.union({'\x01\x00'})
		self.knownCommands = self.knownCommands.union({'\x01\x01', '\x01\x02', '\x01\x04', '\x01\x05', '\x01\x06'})
		self.knownCommands = self.knownCommands.union({'\x80\x01', '\x40\x02', '\x10\x05', '\x38\x06', '\x28\x06'})
		self.knownCommands = self.knownCommands.union({'\x01\x11', '\x01\x12', '\x01\x13', '\x01\x14'})
		self.knownCommands = self.knownCommands.union({'\x80\x11', '\x80\x12', '\x80\x13', '\x80\x14'})
		self.knownCommands = self.knownCommands.union({'\x01\x0e', '\x80\x0e'})
		self.knownCommands = self.knownCommands.union({'\x01\x07', '\x40\x07'})
                self.knownFooter = ['\x03']
		self.port = port
		self.logger = logger
		self.crc_func = crcmod.predefined.mkCrcFun('kermit')
		self.bytes=''
		self.synced = False

	def sync(self):
		self.bytes = self.port.read(5)
		if(len(self.bytes) < 5):
			return False
		syncLog = self.bytes
		while (self.bytes not in self.headerFill) and ('\x82' not in self.bytes[:-1]):
			h = (self.port.read(1))
			if(len(h) < 1):
				#self.logger.debug('++++++ sync End FALSE %s' % self.bytes)
				return False
			syncLog += h
			self.bytes = "%s%s" % (self.bytes[1:6], h)
		#self.logger.trace('sync end %s was %s' % (self.bytes, syncLog))
		self.logger.logError('SYNC %s' % binascii.hexlify(syncLog[:-5]))
		self.synced = True
		return True

	def checkCrc(self):
		msg = self.bytes[:-3]
		crcMsg = binascii.hexlify( "%s%s" % (self.bytes[-2:-1], self.bytes[-3:-2]))
		crc = hex(self.crc_func((msg)))[2:]
		while len(crc) < 4:
			crc = ('%s%s' % ('0', crc ))
		#self.logger.trace('crc %s %s %s %s' % (msg, crcMsg, crc, crc == crcMsg))
		return crc == crcMsg
	def next(self):
		msg = False
                ffmode = False
		while not msg:
			if not self.synced:
				if not self.sync():
					break
			else:
				self.bytes = self.port.read(5)
			if self.bytes in self.headerFill:
				return Message('', self.bytes, isSync=True)
				continue


			if not self.bytes[4:]:
				#self.logger.debug('read less than 5 bytes, exiting')
				break

			p82 = self.bytes.find('\x82')
			separator = ''
			if p82 > -1:
				separator = self.bytes[:p82+1]
				self.bytes = self.bytes[p82+1:]

			if len(self.bytes) < 3:
				self.bytes += (self.port.read(3 - len(self.bytes)))
				if not self.bytes[2:]:
					#self.logger.debug('read less than 3 bytes, exiting')
					break
                        if self.bytes[0:1] == '\xff' and self.bytes[2:3] == '\xff':
                            #self.logger.logError("ffmode")
                            ffmode = True
                            self.bytes = self.bytes.replace('\xff', '')
                            self.bytes += (self.port.read(5 - len(self.bytes))).replace('\xff', '')


			# read rest of the datagram
			# example: '20' is decimal for 32, the length zero based, adding three 
			#          bytes for checksum and stop byte. Adding total 4 bytes
			self.length = int(binascii.hexlify(self.bytes[2:3]), 16)

			#self.logger.trace('got %s and will read %s more bytes' % (self.bytes, self.length))

			# check length
			if self.length > 128:
				self.logger.logError("%s\nERROR LENGTH > 128 %s" % (binascii.hexlify(separator), binascii.hexlify(self.bytes)))
				self.synced = False
				continue
			toread = self.length + 4 + 3 - max(3, len(self.bytes))
			self.bytes += (self.port.read( toread ))
			if(len(self.bytes) < (self.length + 4 + 3) ):
				break;
                        if ffmode:
                            self.bytes = self.bytes.replace('\xff', '')
                            toread = self.length + 4 + 3 - max(3, len(self.bytes))
                            while toread > 0:
                                self.bytes += (self.port.read( toread ))
                                self.bytes = self.bytes.replace('\xff', '')
                                toread = self.length + 4 + 3 - max(3, len(self.bytes))

			msg = Message(separator, self.bytes)

			# check crc
			if not self.checkCrc():
				self.logger.logError("%s\nERROR CRC %s" % (binascii.hexlify(msg.separator), binascii.hexlify(msg.bytes)))
				self.synced = False
				msg = False
				continue

			# check command
			if msg.lengthb+msg.command not in self.knownCommands:
				self.logger.logError("%s\nERROR COMMAND %s" % (binascii.hexlify(msg.separator), binascii.hexlify(msg.bytes)))
				self.synced = False
				msg = False
				continue

			# check footer
			if msg.footer not in self.knownFooter:
				self.logger.logError("%s\nERROR FOOTER %s" % (binascii.hexlify(msg.separator), binascii.hexlify(msg.bytes)))
				self.synced = False
				msg = False
				continue

		try:
			if msg and self.port.note:
				msg.note = self.port.note
		except AttributeError:
			pass
		return msg
class State(object):
	def __init__(self):
		self.date = None
		self.p33 = False
		self.current = {
			# 1 message length
			# 2 temp
			3 : ['\x10', None], # static enabled
			4 : ['\x00', None], # brenner? 00, 02, ff
			5 : ['\x00', None], # brenner? 00, 10
			6 : ['\x00', None], # static null
			7 : ['\x00', None], # static null
			8 : ['\x00', None], # static null
			9 : ['\x00', None], # static null
			10 : ['\x00', None], # static null
			11 : ['\x00', None], # static null
			12 : ['\x00', None], # static null
			13 : ['\x00', None], # static null
			14 : ['\x00', None], # static null
			15 : ['\x00', None], # static null
			16 : ['\x00', None], # static null
			# 17 temp
			18 : ['\x00', None], # 00, 10
			19 : ['\xf1', None], # f1
			20 : ['\x10', None], # static enabled
			21 : ['\x00', None], # static null
			22 : ['\x00', None], # static null
			23 : ['\x00', None], # static null
			24 : ['\x00', None], # static null
			25 : ['\x00', None], # static null
			26 : ['\x00', None], # static null
			27 : ['\x00', None], # static null
			28 : ['\x00', None], # static null
			29 : ['\x00', None], # static null
			30 : ['\x00', None], # 00, 10
			31 : ['\x00', None], # 00, 01
			# 32 temp
			33 : ['\x00', None], # 
		}


	def consumeMessage(self, msg):
		datetime = msg.getDatetime()
		if datetime:
			self.date = datetime
			return
		if not msg.istTemperatur():
			return
		ret = ''
		for k in self.current.keys():
			nv = msg.getMessageByte(k)
			if k == 33:
				if nv == '\x0a':
					nv = '\x00'
				else:
					nv = '\x01'
			if self.current[k][0] != nv:
				if self.date:
					date = self.date.isoformat(' ')
					if self.current[k][1]:
						diff = divmod((self.date - self.current[k][1]).total_seconds(), 60)
						diffh = divmod(diff[0], 60)
					else:
						diff = [-1, -1]
						diffh = [-1, -1]
					self.current[k][1] = self.date
				else:
					date = 'NOT YET'
					diff = [-1, -1]
					diffh = [-1, -1]
				#debug
				ret += '%s %02d %s->%s diff=%02d:%02d:%02d\n' % (date, k, binascii.hexlify(self.current[k][0]), binascii.hexlify(nv),int(diffh[0]), int(diffh[1]), int(diff[1]) )
				self.current[k][0] = nv
					
		if ret:
			return ret[:-1]
		return

class Message(object):
	def __init__(self, separator, bytes, isSync=False):
		self.separator = separator
		self.bytes = bytes
		self.sender = self.bytes[0:1]
		self.receiver = self.bytes[1:2]
		self.length = int(binascii.hexlify(self.bytes[2:3]), 16)
		self.lengthb = self.bytes[2:3]
		self.command = self.bytes[3:4]
		self.footer = self.bytes[-1:]
		self.isSync = isSync

	##########################################################################
	def getDatetime(self):
		if not self.istDatum():
			return None
		year = 2000 + self.decodeHexLike(self.getMessageByte(8))
		# Nach dem Einschalten werden eine Handvoll Nachrichten nur mit 00 uebertragen, dann passt der Monat nicht
		if self.getMessageByte(10) == '\x00':
			month = 1
		else:
			month = self.decodeHexLike(self.getMessageByte(10))
		if self.getMessageByte(6) == '\x00':
			day = 1
		else:
			day = self.decodeHexLike(self.getMessageByte(6))
		hour = self.decodeHexLike(self.getMessageByte(5))
		minute = self.decodeHexLike(self.getMessageByte(4))
		second = self.decodeHexLike(self.getMessageByte(3))
		dt = datetime.datetime(year, month, day, hour, minute, second) 
		return dt
		
	##########################################################################
	def getMessageByte(self, p):
		x = 2 + p
		v = self.bytes[x:x+1]
		return v
		
	def decodeHexLike(self, v):
		return int(binascii.hexlify(v), 10)
	
	##########################################################################
	def istDatum(self):
		if self.command != '\x05':
			return False
		if self.sender != '\x10' or self.receiver != '\x20':
			return False
		if self.length < 9 or ( self.length != 16 and self.length != 9):
			return False
		return True
		
	def istTemperatur(self):
		if self.istTemperaturLong():
			return True
		return self.sender == '\x10' and self.receiver == '\x20' and self.command == '\x04' and self.lengthb == '\x20'

	def istTemperaturLong(self):
		#if istTemperatur():
		#	return True
		return self.sender == '\x10' and self.receiver == '\x20' and self.command == '\x02' and self.lengthb == '\x40'

	def istSync(self):
		return self.isSync
		
	##########################################################################
	def getTemperaturAussen(self):
		offset = 0
		if self.istTemperaturLong():
			offset = 32
		return int(binascii.hexlify(self.getMessageByte(2 + offset)), 16)/2.0 - 52.0
		
	def getTemperaturKesselSoll(self):
		offset = 0
		if self.istTemperaturLong():
			offset = 32
		return int(binascii.hexlify(self.getMessageByte(17 + offset)), 16)/2.0

	def getTemperaturKesselIst(self):
		offset = 0
		if self.istTemperaturLong():
			offset = 32
		return int(binascii.hexlify(self.getMessageByte(32 + offset)), 16)/2.0

	def getP33(self):
		offset = 0
		if self.istTemperaturLong():
			offset = 32
		return int(binascii.hexlify(self.getMessageByte(33 + offset)), 16)/2.0
	##########################################################################
	def toString(self):
		return ''

	def dump(self):
		msg = binascii.hexlify(self.bytes)
		if self.istSync():
			return msg
		else:
			return (msg[0:4] + ' ' + msg[4:6] + msg[6:8] + ' ' + msg[8:-6] 
					+ ' ' + msg[-6:-2] + ' ' + msg[-2:])

class MyDaemon(Daemon):
	
	def initSerial(self):
		self.port = serial.Serial(__serialDevice__, baudrate=9600, timeout=30.0, 
			bytesize=serial.EIGHTBITS, stopbits=serial.STOPBITS_ONE, 
			parity=serial.PARITY_NONE, xonxoff=False, rtscts=False, dsrdtr=False)

	def closeSerial(self):
		if self.port:
			self.port.close()

	def handler(self, signum = None, frame = None):
		self.logger.logError ('Signal handler called with signal' + str( signum ))
		self.closeSerial()
		self.logger.logError ('Deamon stop')
		sys.exit(0)
	def ignoreHandler(self, signum = None, frame = None):
		pass

	def run(self):
		signal.signal(signal.SIGPIPE, self.ignoreHandler)
		for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT]:
			signal.signal(sig, self.handler)
		self.logger = Logger(__logfile__, __errfile__)
		self.logger.logError('Deamon start')
		self.initCounter = 0;
		while self.initCounter < 20:
			try:
				self.initSerial()
				self.initCounter = 20
			except SerialException as e:
				self.logger.logError('SerialException caught counter=%s' % self.initCounter)
				self.initCounter += 1
				if self.initCounter == 20:
					raise ValueError('Could not initalize the serial port, tried multiple times...') 
				time.sleep(3) # delays for 3 seconds

		self.parser = Parser(self.port, self.logger)

		# start http thread
		httpThread = HttpThread()
		httpThread.setDaemon(True)
		httpThread.start()

		# Now begin to read data
		while True:
			self.msg = self.parser.next()
			if not self.msg:
				self.logger.logError('LOST CONNECTION, TERMINATING...')
				break
			# ignore sync messages
			if self.msg.istSync():
				continue
			# save values for the stats
			with __lock__:
				key = self.msg.sender + self.msg.receiver + self.msg.lengthb + self.msg.command
				i = datetime.datetime.now()
				__time__[key] = ("%s" % i)
				if key not in __data__.keys() or __data__[key] != self.msg.bytes:
					__modified__[key] = ("%s" % i)
					__data__[key] = self.msg.bytes
					self.logger.log(binascii.hexlify(self.msg.bytes))


class HttpRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	server_version = __serverversion__
	def do_GET(self):
		try:
			"""Serve a GET request."""
			self.send_response(200)
			with __lock__:
				if self.path == "/munin-temperature":
					self.muninTemperature()
				else:
					self.dump()
			self.wfile.close()
		except:
			try:
				e = sys.exc_info()[0]
				self.wfile.write('Error: %s' % e)
			except:
				pass
	
	# Do not write http logs to stderr!
	def log_message(self, format, *args):
		#sys.stderr.write("%s - - [%s] %s\n" % (self.client_address[0], 
		#		self.log_date_time_string(), format%args))
		pass

	# print all temperatures for munin
	def muninTemperature(self):
		self.send_header("Content-type", "text/plain")
		self.end_headers()
		key = '\x10\x20\x40\x02'
		if __data__[key]:
			msg = Message('', __data__[key])
		if msg:
			output = ''
			output += 'temperature1.value %.2f\n' % msg.getTemperaturAussen()
			output += 'temperature2.value %.2f\n' % msg.getTemperaturKesselSoll()
			output += 'temperature3.value %.2f\n' % msg.getTemperaturKesselIst()
			output += 'temperature4.value %.2f\n' % msg.getP33()
			output += 'temperaturep7.value %.2f\n' % (int(binascii.hexlify(msg.getMessageByte( 7 )), 16)/2.0)
			output += 'temperaturep8.value %.2f\n' % (int(binascii.hexlify(msg.getMessageByte( 8 )), 16)/2.0)
			output += 'temperaturep12.value %.2f\n' % (int(binascii.hexlify(msg.getMessageByte( 12 )), 16)/2.0)
			output += 'temperaturep13.value %.2f\n' % (int(binascii.hexlify(msg.getMessageByte( 13 )), 16)/2.0)
			output += 'temperaturep17.value %.2f\n' % (int(binascii.hexlify(msg.getMessageByte( 17 )), 16)/2.0)
			output += 'temperaturep18.value %.2f\n' % (int(binascii.hexlify(msg.getMessageByte( 18 )), 16)/2.0)
			output += 'temperaturep20.value %.2f\n' % (int(binascii.hexlify(msg.getMessageByte( 20 )), 16)/2.0)
			output += 'temperaturep21.value %.2f\n' % (int(binascii.hexlify(msg.getMessageByte( 21 )), 16)/2.0)
			output += 'temperaturep23.value %.2f\n' % (int(binascii.hexlify(msg.getMessageByte( 23 )), 16)/2.0)
			output += 'temperaturep24.value %.2f\n' % (int(binascii.hexlify(msg.getMessageByte( 24 )), 16)/2.0)
			output += 'temperaturep27.value %.2f\n' % (int(binascii.hexlify(msg.getMessageByte( 27 )), 16)/2.0)
			output += 'temperaturep31.value %.2f\n' % (int(binascii.hexlify(msg.getMessageByte( 31 )), 16)/2.0)
			output += 'temperaturep32.value %.2f\n' % (int(binascii.hexlify(msg.getMessageByte( 32 )), 16)/2.0)
			self.wfile.write(output)

	# Dump the global message cache
	def dump(self):
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write(__html_header__)
		if self.path.endswith('time'): 
			keys = []
			for k in sorted(__time__.items(), key=operator.itemgetter(1)):
				keys.append(k[0])
			keys.reverse()
		elif self.path.endswith('modified'): 
			keys = []
			for k in sorted(__modified__.items(), key=operator.itemgetter(1)):
                                keys.append(k[0])
			keys.reverse()
		else:
			keys = sorted(__data__.keys())
		for key in keys:
			msg = Message('', __data__[key])
			time = __time__[key]
			modified = __modified__[key]
			key = binascii.hexlify(key)
			self.wfile.write( 'time:' + time + ' modified:' + modified + ' length:' + str(msg.length) + ' key:' + key + '<br/>' )
			self.wfile.write( msg.dump() )
			self.wfile.write( '<br/>' )
			for i in range(2, msg.length+2):
				t = int(binascii.hexlify(msg.getMessageByte( i )), 16)/2.0
				if(t > 0.0):
					self.wfile.write( "p%s=%.2f " % (i,t))
			self.wfile.write( '<br/>' )
			self.wfile.write( '<br/>' )
		self.wfile.write(__html_footer__)

class MultiThreadedHTTPServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    pass

class HttpThread(threading.Thread):
	def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
		super(HttpThread,self).__init__()
		self.target = target
		self.name = name
		return

	def run(self):
		HandlerClass = HttpRequestHandler
		#ServerClass  = BaseHTTPServer.HTTPServer
		ServerClass  = MultiThreadedHTTPServer
		Protocol     = "HTTP/1.0"

		server_address = (__address__, __port__)

		HandlerClass.protocol_version = Protocol
		httpd = ServerClass(server_address, HandlerClass)

		sa = httpd.socket.getsockname()
		#print "Serving HTTP on", sa[0], "port", sa[1], "..."
		httpd.serve_forever()

if __name__ == "__main__":
	daemon = MyDaemon(__pidfile__,'/dev/stdin','/dev/stdout','/dev/stderr')
	if len(sys.argv) == 2:
		if 'start' == sys.argv[1]:
			daemon.start()
		elif 'stop' == sys.argv[1]:
			daemon.stop()
		elif 'restart' == sys.argv[1]:
			daemon.restart()
		else:
			print ("Unknown command")
			sys.exit(2)
		sys.exit(0)
	else:
		print ("usage: %s start|stop|restart" % sys.argv[0])
		sys.exit(2)

