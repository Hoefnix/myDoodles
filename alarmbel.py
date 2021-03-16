# monitor voor aantal zaken
# - deurbel
# - voordeur open/dicht sensor

import datetime
import json
import locale
import os
import random
import requests
import RPi.GPIO as GPIO
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler,HTTPServer


from PIL import Image, ImageStat, ImageDraw, ImageFont
from io  import BytesIO

def homebridge():
	return "192.168.0.10"
	
def httpGet( httpCall, wachten = 4, label="", pushover=True):
	resultaat = requests.Response
	try: 
		resultaat = requests.get(httpCall, timeout=wachten)
	except requests.Timeout as e:
		msg.console("%s\033[31m%s url=%s\ntimeout=%s"%(label,e,httpCall,wachten))
		resultaat.status_code = 999
		pass
	except Exception as e:
		msg.console("%s\033[31mFout url=%s\nxception=%s"%(label,httpCall,e))
		resultaat.status_code = 999
		pass
	return resultaat
	
class messaging( object ):
	def __init__(self):
		return

	def console(self, message = "" ):
		if not message == None:
			print("\033[3m%s\033[0m - %s\033[0m"%(time.strftime("%d%b - %H:%M:%S"),message))

	def pushover(self, titel = "", bericht = "", prio = 0):
		#	deurbel:		affvqzpG7tiY1nTKtGA5Tix4xr19U9
		#	algemeen:		aYs6YxK8qV1KnGV1LEHzQQtFTrCutk
		#	alarmsysteem:	asubmezyekh9hfsrtxsqx9ne85szys
		return
		
		apptoken = 'affvqzpG7tiY1nTKtGA5Tix4xr19U9' # if prioriteit < 2 else 'asubmezyekh9hfsrtxsqx9ne85szys'
		usrtoken = 'udEe5uL7YjuyYLyhQXBjvjnqiGGsf8'
		pushjson = {'token': apptoken, 'user': usrtoken, 'title': titel,'html': 1, "priority": prio ,'message': bericht}

		try:
			requests.post('https://api.pushover.net/1/messages.json', data = pushjson )
		except requests.Timeout as e:
			self.console("Pushover - %s"%e)
		except:
			self.console("Pushover - Fout")

msg = messaging.console("\033[0;0H\033[2JMonitor geluid, deurbel")

deurblpin = 25
voordrpin = 7
plngplong = 11
relais = 8

msg = messaging()

def myIP():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

class Voordeur(object):
	def __init__(self):
		self.start = time.time()
		self.status = -1
		self.trigger(voordrpin)

	def pushme(self):
		msg.pushover("\U0001F6CE De voordeur is open", self.bericht, 1)
		requests.get("http://192.168.0.20:51828/?accessoryId=deurbel&state=true")

	def trigger(self, pin):
		if GPIO.input(pin) != self.status:
			self.status = GPIO.input(pin)
			msg.console("gpio.input(%s) = %s"%(pin, GPIO.input(pin)))
			udp5005.broadcast('{"voordeur":%s}'%GPIO.input(pin))		
			url = "http://"+homebridge()+":51828/?accessoryId=voordeur&state=%s"%("false" if GPIO.input(pin) else "true")
			threading.Thread(target=httpGet,args=[url]).start()

class Deurbel(object):
	def __init__(self):
		locale.setlocale(locale.LC_ALL, "nl_NL.UTF-8")

		extrnip = requests.get("http://myexternalip.com/raw").text.strip()
		self.udp = udpListner(2323, 1)

		self.font = ImageFont.truetype(font="/opt/development/arial.ttf", size=10)
		self.bericht = '<i>Kijk <a href="http://%s:220/stream-voordeur.html">hier</a> voor live beelden</i>'%extrnip
		self.start = 0
		self.width = 320
		self.height= 240

		try:
			r = requests.get("http://127.0.0.1:1964/state")
		except:
			msg.console("Status webcam niet beschikbaar")
		else:
			msg.console("\x1b[34mCamera status: %sline, fps: %s\x1b[0m"%(("on" if r.json()["ok"] else "off"),r.json()["result"]["source"]["captured_fps"]))
			
		self.licht = 0
		self.lichtsterkte()

	def pushme(self):
		msg.pushover("\U0001F6CE Er wordt aangebeld", self.bericht, 1)
#		requests.get("http://192.168.0.20:51828/?accessoryId=deurbel&state=true")
		
	def getfoto(self):
		try:
			r = requests.get("http://127.0.0.1:1964/snapshot")
		except:
			msg.console("Foto ophalen mislukt")
			pass
		else:
			self.foto  = Image.open(BytesIO(r.content))#.rotate(180)
			self.licht = int(ImageStat.Stat(self.foto).mean[0])
			return True
		return False
		
	def lichtsterkte(self):
		self.thread = threading.Timer(300, self.lichtsterkte)
		self.thread.start()
		
		if self.getfoto():
			msg.console("\033[3mLichtsterkte %s\033[0m"%self.licht)
			self.udp.broadcast('{"name":"voordeur","lightlevel":%s,"door":%s}'%(self.licht,GPIO.input(voordrpin)) )

	def sendfoto(self):
		if self.getfoto():
			draw = ImageDraw.Draw(self.foto, 'RGBA')
			font = ImageFont.truetype(font="/opt/development/arial.ttf", size=10)
			locale.setlocale(locale.LC_ALL, "nl_NL.UTF-8")

			tekst = "Er is aangebeld om %s"%time.strftime("%A %d %B om %H:%M.%S").lower()

			draw.line([10,self.height-15, self.width-10, self.height-15], fill=(180, 28, 28, 128), width=15)
			draw.text((15,self.height-20), tekst, (255,255,255), font=font)

			self.foto.save('/tmp/voordeur.jpg', "JPEG")
			if os.path.exists("/tmp/voordeur.jpg"):
				msg.console("Foto wordt verzonden")
				telegram(image="/tmp/voordeur.jpg")
				os.remove("/tmp/voordeur.jpg")
				return True
		return False
		
	def trigger(self, pin):
		msg.console("De bel: gpio.input(%s) = %s"%(pin, GPIO.input(pin)))

		if GPIO.input(pin) == 1 : return
		
		aanbellen()
		
		udp5005.broadcast('{"deurbel":%s}'%GPIO.input(pin))
		msg.console("seconden %s"%(time.time()-self.start))
		if (time.time()-self.start) > 30: # maximaal een foto per seconde
			threading.Thread(target=self.pushme).start()
			self.start = time.time()
			if not self.sendfoto():
				telegram("\U0001F6CE Er wordt aangebeld (...geen foto)")
		else:
			msg.console("Te snel, foto niet verstuurd")

	def stop(self):
		msg.console("Lichtsterkte check wordt gestopt...")
		self.thread.cancel()

class udpListner(object):
	def __init__(self, myport = 5005, seconden = 0):
		self.port = myport
		self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self.start = time.time()
		self.interval = seconden

	def broadcast(self, message = ""):
		if self.interval is 0:
			return
		elif time.time()-self.start > self.interval:
			self.start = time.time()
			msg.console("Sending: \033[33m%s\033[0m"%message)
			self.s.sendto(bytes(message,"UTF-8"),('<broadcast>',self.port))

def telegram( message = None, image = None, chat_id = "-24143102"):
	# telegram adressen
	deurbel			= "-15033899"
	Johannes_Smits	=  "12463680"
	alarmsysteem	= "-24143102"
	
	if not message is None:
		url = "https://api.telegram.org/bot112338525:AAGyQLESoyVnCAdBJZTdaRcgV5KwN3uGipU/sendMessage"
		payload = {"chat_id":chat_id, "text":message, "parse_mode":"HTML"}
		r = requests.get(url, params=payload)	
		return (r.json()["ok"])

	elif not image is None:
		msg.console("sending %s"%image)
		url	= "https://api.telegram.org/bot112338525:AAGyQLESoyVnCAdBJZTdaRcgV5KwN3uGipU/sendPhoto"
		data	= {'chat_id': chat_id}
		files	= {'photo': (image, open(image, "rb"))}
		r = requests.post(url , data=data, files=files)
		return (r.json()["ok"])


class myHandler(BaseHTTPRequestHandler):
	global deBel
	
	def log_message(self, format, *args):
		return

	def do_HEAD(self):
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()

	def respond(self, response=None, status=200):
		self.send_response(status)
		self.send_header('Content-type','text/html')
		self.end_headers()

		if not response is None:
			try:
				self.wfile.write( bytes(response,"utf-8")  )
			except Exception as e:
				msg.console("\033[31m%s bij %s"%(e, response))
				pass

#	Handler for the GET requests
	def do_GET(self):
		global verbose

		command = self.requestline.replace("GET /","").replace("?","")
		command = command[:command.find("HTTP")].strip()

		if command == "verbose":
			self.respond("Logging on\n")

		elif command.startswith("lightlevel"):
			self.respond("OK")

		elif command.startswith("bel"):
			self.respond("%s"%("OK" if deBel.sendfoto() else "Sorry, geen foto"))
			
		elif command.startswith("relais"):
			GPIO.output(relais,abs(1-GPIO.input(relais)))
			self.respond("gpio is now: %s"%GPIO.input(relais))

# ...............

def aanbellen():
	GPIO.output(plngplong,0)
	time.sleep(0.5)
	GPIO.output(plngplong,1)


msg.console("\033[3mControl-C om te stoppen\033[0m")

status = 0

extrnip = requests.get("http://myexternalip.com/raw").text.strip()
udp5005 = udpListner(5005, 1)
msg.console("\033[92mListening on udp channel 5005\033[0m")

GPIO.setmode(GPIO.BCM)
GPIO.setup(plngplong, GPIO.OUT, initial=GPIO.HIGH)	
GPIO.setup(   relais, GPIO.OUT, initial=GPIO.HIGH)	

GPIO.setup(deurblpin, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(voordrpin, GPIO.IN, GPIO.PUD_UP)

deBel  = Deurbel()
deDeur = Voordeur()

GPIO.add_event_detect(deurblpin, GPIO.BOTH, callback=deBel.trigger )
GPIO.add_event_detect(voordrpin, GPIO.BOTH, callback=deDeur.trigger )
msg.console("\033[92mEvent detects initiated...\033[0m")

# Instellen UDP listener
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # internet, UDP
sock.setblocking(0)
sock.settimeout(10)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('', UDP_PORT)) # udp port 5005

telegram( message = "%s op de %s (%s) is gestart"% (os.path.basename(__file__),socket.gethostname(), myIP()), chat_id="12463680")

server = HTTPServer(('', 1208), myHandler)
srvrThread = threading.Thread(target=server.serve_forever)
srvrThread.daemon = True
srvrThread.start()
msg.console("HTTPlistner actief op poort %d"%1208)
	
try:
	msg.console("\x1b[36m%s gestart\x1b[0m"%__file__)

	while True:
		try :
			jsonstr, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
			jsonstr = jsonstr.decode("utf8")
			msg.console('{"voordeur":%s}'%GPIO.input(voordrpin))
		except socket.timeout:
			continue

except (KeyboardInterrupt):#, RuntimeError, TypeError, NameError, ValueError):
	msg.console("Shutting down...")
	sock.close()
	deBel.stop()

	GPIO.remove_event_detect(deurblpin)
	GPIO.remove_event_detect(voordrpin)
	GPIO.cleanup()

	msg.console("Starting %s..."%__name__)
	subprocess.call("rsync -a /opt/development/alarmbel.py /opt/ && screen -dmS alarmbel python3 %s"%__file__, shell=True)
