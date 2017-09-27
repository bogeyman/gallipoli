import serial, binascii, sys

# 4800 <- kaputt
# 9600
# 19200
# 38400 
# 57600 <- kaputt
# 115200 <- kaputt
# 230400 <- kaputt
# bytesize FIVEBITS, SIXBITS, SEVENBITS, EIGHTBITS
# parity PARITY_NONE, PARITY_EVEN, PARITY_ODD PARITY_MARK, PARITY_SPACE
# stopbits STOPBITS_ONE, STOPBITS_ONE_POINT_FIVE, STOPBITS_TWO
serialDevice = '/dev/ttyUSB0'

while True:
    try:
	port = serial.Serial(serialDevice, baudrate=9600, timeout=60.0, bytesize=serial.EIGHTBITS, stopbits=serial.STOPBITS_ONE, parity=serial.PARITY_NONE, xonxoff=False, rtscts=False, dsrdtr=False)
        rcv = port.read(40)
        hex = binascii.hexlify(rcv)
        # print hex + " " + repr(rcv)
        print hex
        sys.stderr.flush()
        sys.stdout.flush()
    except Exception as e:
        pass
