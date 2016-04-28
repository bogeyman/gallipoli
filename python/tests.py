import unittest
import StringIO
from gallipoli import *
import binascii


logger = Logger('/dev/null', '/dev/null')
#logger = Logger()
#logger.level = logger.TRACE
#logger.level = logger.DEBUG



class TestParser(unittest.TestCase):

	# einmal Zeilenende, dann weiter
	def test_LogReader1(self):
		msg = '909090\n1a1a\neeaaccdd11552233\n'
		lr = LogReader(StringIO.StringIO(msg), logger)
		self.assertEqual(lr.read(5), binascii.unhexlify('9090901a1a'))
		self.assertEqual(lr.read(3), binascii.unhexlify('eeaacc'))
		self.assertEqual(lr.read(20), binascii.unhexlify('dd11552233'))

	# Zeilen uebergreifend
	def test_LogReader2(self):
		msg = '909090\n1a1a\neeaaccdd11552233\n'
		lr = LogReader(StringIO.StringIO(msg), logger)
		self.assertEqual(lr.read(2), binascii.unhexlify('9090'))
		self.assertEqual(lr.read(4), binascii.unhexlify('901a1aee'))
		self.assertEqual(lr.read(2), binascii.unhexlify('aacc'))
		self.assertEqual(lr.read(10), binascii.unhexlify('dd11552233'))

	# einmal Zeilenende, dann weiter
	def test_LogReader1_date(self):
		msg = '2015-04-12 19:22:34.34234 909090\n1.1.2002 13:37 1a1a\n21.5.1977 eeaaccdd11552233\n'
		lr = LogReader(StringIO.StringIO(msg), logger)
		self.assertEqual(lr.read(5), binascii.unhexlify('9090901a1a'))
		self.assertEqual(lr.read(3), binascii.unhexlify('eeaacc'))
		self.assertEqual(lr.read(20), binascii.unhexlify('dd11552233'))

	# Zeilen uebergreifend
	def test_LogReader2_date(self):
		msg = '2015-04-12 19:22:34.34234 909090\n1.1.2002 13:37 1a1a\n21.5.1977 eeaaccdd11552233\n'
		lr = LogReader(StringIO.StringIO(msg), logger)
		self.assertEqual(lr.read(2), binascii.unhexlify('9090'))
		self.assertEqual(lr.read(4), binascii.unhexlify('901a1aee'))
		self.assertEqual(lr.read(2), binascii.unhexlify('aacc'))
		self.assertEqual(lr.read(10), binascii.unhexlify('dd11552233'))

	# einmal Zeilenende, dann weiter
	def test_LogReader_ignores(self):
		msg = '909090\n#1a1a\neeaaccdd11552233\nwill be ignored: Deamon start\nwill be ignored: SYNC\nffeeddcc'
		lr = LogReader(StringIO.StringIO(msg), logger)
		self.assertEqual(lr.read(5), binascii.unhexlify('909090eeaa'))
		self.assertEqual(lr.read(1), binascii.unhexlify('cc'))
		self.assertEqual(lr.read(20), binascii.unhexlify('dd11552233' + 'ffeeddcc'))


	# einfacher Parser test, nur sync
	def test_parser_sync1(self):
		msg = binascii.unhexlify('9090909090')
		parser = Parser(StringIO.StringIO(msg), logger)
		self.assertTrue(parser.next())
		self.assertFalse(parser.next())

	# einfacher Parser test, nur sync
	def test_parser_sync2(self):
		msg = binascii.unhexlify('90909090902121212121')
		parser = Parser(StringIO.StringIO(msg), logger)
		self.assertTrue(parser.next())
		self.assertTrue(parser.next())
		self.assertFalse(parser.next())


	# einfache Nachricht mit sync
	def test_parser_msg1(self):
		sync1 = '9f9f9f9f9f'
		msg1 = 'fc8210200905005333220393150409ecd303'
		msg2 = 'fc8210200905005433220393150409e24f03'
		msg = binascii.unhexlify(sync1 + msg1 + msg2)
		parser = Parser(StringIO.StringIO(msg), logger)
		self.assertEqual(binascii.hexlify(parser.next().bytes), sync1)
		self.assertEqual(binascii.hexlify(parser.next().bytes), msg1[4:])
		self.assertEqual(binascii.hexlify(parser.next().bytes), msg2[4:])
		self.assertFalse(parser.next())

	# einfache Nachricht mit sync
	def test_parser_msg2(self):
		sync1 = '9f9f9f9f9f'
		crcError = 'fc8210200905005333220393150409ecd203'
		msg2 = 'fc8210200905005433220393150409e24f03'
		msg = binascii.unhexlify(sync1 + crcError + msg2)
		parser = Parser(StringIO.StringIO(msg), logger)
		self.assertEqual(binascii.hexlify(parser.next().bytes), sync1)
		self.assertEqual(binascii.hexlify(parser.next().bytes), msg2[4:])
		self.assertFalse(parser.next())

	# regress test
	def test_parser_msg3(self):
		sep1 = '82'
		msg1 = '1b10010510e80403'
		sep2 = '06'
		msg = binascii.unhexlify(sep1 + msg1 + sep2)
		parser = Parser(StringIO.StringIO(msg), logger)
		msg = parser.next()
		self.assertEqual(binascii.hexlify(msg.separator), sep1)
		self.assertEqual(binascii.hexlify(msg.bytes), msg1)
		self.assertFalse(parser.next())

	# regress test
	def test_parser_msg4(self):
		sync1 = '2222222222'
		sep1 = '82'
		msg1 = '1b10010510e80403'
		sep2 = '06'
		msg = binascii.unhexlify(sync1 + sep1 + msg1 + sep2)
		parser = Parser(StringIO.StringIO(msg), logger)
		self.assertEqual(binascii.hexlify(parser.next().bytes), sync1)
		msg = parser.next()
		self.assertEqual(binascii.hexlify(msg.separator), sep1)
		self.assertEqual(binascii.hexlify(msg.bytes), msg1)
		self.assertFalse(parser.next())

	# regress test
	def test_parser_msg5(self):
		sep1 = '9082'
		msg1 = '1b10010510e80403'
		sep2 = '06'
		msg = binascii.unhexlify(sep1 + msg1 + sep2)
		parser = Parser(StringIO.StringIO(msg), logger)
		msg = parser.next()
		self.assertEqual(binascii.hexlify(msg.separator), sep1)
		self.assertEqual(binascii.hexlify(msg.bytes), msg1)
		self.assertFalse(parser.next())



	# einfache Nachricht mit sync
	def test_message_getBytes1(self):
		inmsg1 = 'fc8210200905005433220393150409e24f03'
		inmsg = binascii.unhexlify(inmsg1)
		parser = Parser(StringIO.StringIO(inmsg), logger)
		msg = parser.next()
		self.assertTrue(msg.sender == '\x10', binascii.hexlify(msg.sender))
		self.assertTrue(msg.receiver == '\x20', binascii.hexlify(msg.receiver))
		self.assertTrue(msg.footer == '\x03', binascii.hexlify(msg.footer))
		p = 0
		self.assertTrue(msg.getMessageByte(p) == '\x09', binascii.hexlify(msg.getMessageByte(p)) )
		p = 1
		self.assertTrue(msg.getMessageByte(p) == '\x05', binascii.hexlify(msg.getMessageByte(p)) )
		p = 2
		self.assertTrue(msg.getMessageByte(p) == '\x00', binascii.hexlify(msg.getMessageByte(p)) )
		p = 3
		self.assertTrue(msg.getMessageByte(p) == '\x54', binascii.hexlify(msg.getMessageByte(p)) )
		p = 4
		self.assertTrue(msg.getMessageByte(p) == '\x33', binascii.hexlify(msg.getMessageByte(p)) )

	# einfacher Parser test, einschaltsequenz
	def test_parser_sync3(self):
		msg = binascii.unhexlify('7d8210ff0100004e2b037d8210ff0100ff3624037d8210ff0100004e2b037d8210ff0100004e2b037d8210ff0100004e2b037d8210ff0100190ea603ff8210202004811000000000000000000000000000000001100000000000000000000000a70ad8ac03')
		parser = Parser(StringIO.StringIO(msg), logger)
		self.assertTrue(parser.sync())
		self.assertTrue(parser.sync())
		self.assertTrue(parser.sync())
		self.assertTrue(parser.sync())
		self.assertTrue(parser.sync())
		self.assertTrue(parser.sync())
		self.assertTrue(parser.sync())
		self.assertFalse(parser.sync())

	# Parser test, einschaltsequenz
	def test_parser1(self):
		msg = binascii.unhexlify('7d8210ff0100004e2b037d8210ff0100ff3624037d8210ff0100004e2b037d8210ff0100004e2b037d8210ff0100004e2b037d8210ff0100190ea603ff8210202004811000000000000000000000000000000001100000000000000000000000a70ad8ac03')
		parser = Parser(StringIO.StringIO(msg), logger)
		self.assertTrue(parser.next())
		self.assertTrue(parser.next())
		self.assertTrue(parser.next())
		self.assertTrue(parser.next())
		self.assertTrue(parser.next())
		self.assertTrue(parser.next())
		self.assertTrue(parser.next())
		self.assertFalse(parser.next())

	# Parser test, einschaltsequenz
	def test_parser2(self):
		a = ['7d8210ff0100004e2b03',
		'7d8210ff0100ff362403',
		'7d8210ff0100004e2b03',
		'7d8210ff0100004e2b03',
		'7d8210ff0100004e2b03',
		'7d8210ff0100190ea603',
		'ff8210202004811000000000000000000000000000000001100000000000000000000000a70ad8ac03',
		'fc8210200905005433220393150409e24f03']
		msg =  binascii.unhexlify(''.join(a))
		parser = Parser(StringIO.StringIO(msg), logger)
		self.assertEqual(binascii.hexlify(parser.next().bytes), a[0][4:])
		self.assertEqual(binascii.hexlify(parser.next().bytes), a[1][4:])
		self.assertEqual(binascii.hexlify(parser.next().bytes), a[2][4:])
		self.assertEqual(binascii.hexlify(parser.next().bytes), a[3][4:])
		self.assertEqual(binascii.hexlify(parser.next().bytes), a[4][4:])
		self.assertEqual(binascii.hexlify(parser.next().bytes), a[5][4:])
		self.assertEqual(binascii.hexlify(parser.next().bytes), a[6][4:])
		self.assertEqual(binascii.hexlify(parser.next().bytes), a[7][4:])
		self.assertFalse(parser.next())



if __name__ == '__main__':
    unittest.main()

