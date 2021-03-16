#!/usr/bin/python

from requests.auth import HTTPBasicAuth
from http.server import BaseHTTPRequestHandler,HTTPServer
from subprocess import Popen, PIPE
from random import randint
from pathlib import Path

import datetime
import ephem
import json
import os
import requests
import socket
import subprocess
import threading
import time

from smits import woonveilig, Messaging, nacht

PORT_NUMBER = 1208
thread = None # voor getstatus() thread	

ventilatie = 0
energie = 0

def lampen():
	return {
		"bureaulamp": "HAA-CFC75B",
		"schemerrgb": "HAA-CFD17E",
		 "sidetable": "HAA-6A7D8F",
		"tvdressoir": "HAA-F8F2A3",
			"rikled": "HAA-406380",
		 "logeerled": "HAA-187767",
		 "gevellamp": "HAA-F9DC1B",
		"rgbexpedit": "HAA-F6F934",
		 "rgbbamboe": "HAA-6A7D8F"
	}


def telegram(message="", chat_id="12463680"):
	#	johannes_smits	=  "12463680"
	#	alarmsysteem	= "-24143102"
	#	christie		=  "15044759"
	
	if not message: return
	
	sendMessage  = "https://api.telegram.org/bot112338525:AAGyQLESoyVnCAdBJZTdaRcgV5KwN3uGipU/sendMessage"
	
	arguments = {}
	arguments["parse_mode"] = "HTML"
	arguments["chat_id"]    = chat_id
	arguments["text"]       = message
	
	try:
		r = requests.get(sendMessage, data=arguments, timeout=5)
	except requests.Timeout as e:
		print("Telegram - %s"%e)
	except:
		print("Telegram - Fout")
		
class haaversion(object):
	def __init__(self):
		versie = ""
		check()
		
	def check(self):
		msg.console("Checking haaversion with %s")
		self.thread = threading.Timer(300, self.check)
		self.thread.start()
		try:
			# get latest version number
			r = requests.get("https://github.com/RavenSystem/esp-homekit-devices/releases/latest")
			versie = r.url[(r.url.rfind("/")-len(r.url))+1:].replace("HAA_","")
		except Exception as e:
			pass
			
class humidity(object):
	def __init__(self, name):
		self.status = 0
		self.interval = 300
		self.name = name
		self.previous = 0
		self.temperature = 0
		self.times = 0
		self.check()
		
	def check(self):
		self.times += 1
		msg.console("Checking humidity with %s"%self.name)
		self.thread = threading.Timer(self.interval, self.check)
		self.thread.start()
		try:
			resultaat = requests.get('http://%s.local:5556'%self.name)
		except Exception as e:
			pass
			msg.error( "%s reageert niet...\n%s"%(self.name, e))
			msg.telegram("%s reageert niet..."%self.name)
			return
			
		if (resultaat.status_code == requests.codes.ok):
			for regel in resultaat.json()["accessories"]:
				for service in regel["services"]:
					for characteristic in service["characteristics"]:
						if characteristic["type"] == "10":
							msg.console( "Luchtvochtigheid badkamer %s%%"%round( characteristic["value"]))
							if abs(self.previous-round( characteristic["value"])) > 5 or self.times > 12:
								self.times = 0
								self.previous = round( characteristic["value"] )
								thingspeak(veld="field3",waarde=self.previous, omschrijving = "Luchtvochtigheid")
								
							if self.previous > 75:
								# reset timer
								msg.console( "Ventilatie standje 2" )
								data = '{"characteristics":[{"aid":1,"iid":9,"value":false},{"aid":1,"iid":9,"value":true}]}'
								requests.put('http://HAA-3D8BA4.local:5556/characteristic', data=data)
								
							elif self.previous in range(65,75):
								# reset timer
								msg.console( "Ventilatie standje 1" )
								data = '{"characteristics":[{"aid":2,"iid":9,"value":false},{"aid":2,"iid":9,"value":true}]}'
								requests.put('http://HAA-3D8BA4.local:5556/characteristic', data=data)

			
						elif characteristic["type"] == "11":
							msg.console( "Temperatuur badkamer %sC"%round( characteristic["value"]))
							if abs(self.temperature-round( characteristic["value"])) > 5:
								self.temperature = round( characteristic["value"] )
								thingspeak(veld="field4",waarde=self.temperature, omschrijving = "Temperatuur")
	def stop(self):
		msg.console("Humidity check stopped...")
		self.thread.cancel()
		
		
def getstate( ip ):	
	resultaat = httpGet( ip, 4, "Muurschakelaar")
	if resultaat.status_code == 200:
		for regel in resultaat.json()["accessories"]:
			for service in regel["services"]:
				for characteristic in service["characteristics"]:
					if "value" in characteristic:
						if characteristic["type"] == "25":
							if characteristic["aid"] =="2":
								msg.console("\033[33m%s - %s\033[0m"%(ip, characteristic["value"]))
								return characteristic["value"]
	return False

class piVeilig( object ):
	def __init__(self):
		self.status = 0
		self.interval = 30
		self.check()
		
	def check(self):
		self.thread = threading.Timer(self.interval, self.check)
		self.thread.start()
		resultaat = httpGet("http://192.168.0.20:8762/status", 4, "Alarmsysteem: ")
		if (resultaat.status_code == requests.codes.ok):
			self.status = int(resultaat.text)
	
	def stop(self):
		msg.console("piVeilig wordt gestopt...")
		self.thread.cancel()
	
class GetConfig():
#	{"type":"config","callback":"83.86.240.150","webhook":"192.168.178.125","udpport":2323,"lichtsterkte":100}
	def __init__(self):
		path = Path(__file__).parent.absolute()
		with open("%s/common/sibeliusweg.json"%path, "r") as configfile:
			self.config = json.load(configfile)

	def get(self, key):
		path = Path(__file__).parent.absolute()
		with open("%s/common/sibeliusweg.json"%path, "r") as configfile:
			self.config = json.load(configfile)
			
		if key in self.config:
			return self.config[key]
		return ""

class energie( object ):
	def __init__(self):
		self.energie = 0
		
class udplistner(object):
	def __init__(self, udpport = 5005):
		# Instellen UDP listener
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # internet, UDP 
		self.sock.setblocking(0)
		self.sock.settimeout(30)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.sock.bind(('', udpport)) # udp port 5005
		
		self.proceed = True
		msg.console("Starting UDP listener on port %s"%udpport)
		threading.Thread(target=self.listen).start()
		
		self.waarden = {"vermogen":0, "buitentemp":0, "temperature":0}
		
	def listen(self):
		while self.proceed:
			try :
				string, addr = self.sock.recvfrom(1024) # buffer size is 1024 bytes
				string = string.decode("utf8").strip()
				if string == "": continue

				msg.console("UDP message %s"%string)
				if "vermogen" in string:
					energie = json.loads(string)["vermogen"]

				elif "badkamer" in string:
				#	{"name":"badkamer", "humidity":72, "temperature":23.3}
					humidity = json.loads(string)["humidity"]
					temperature = json.loads(string)["temperature"]
	

			except socket.timeout:
				continue
				
	def stop(self):
		msg.console("Stopping UDP listner")
		self.proceed = False
		self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self.s.sendto(bytes(' ',"UTF-8"),('<broadcast>',config.get("udpport")))

def thingspeak(veld="field6",waarde=None, omschrijving = ""):
	msg.console("Thingspeak update %s, %s = %s"%(omschrijving, veld, waarde))

	if not waarde is None:
		threading.Thread(target=httpGet, args=("https://api.thingspeak.com/update?key=0Y0TM8Y14DTM54P1&%s=%s"%(veld, waarde),)).start()
		#httpGet("https://api.thingspeak.com/update?key=0Y0TM8Y14DTM54P1&%s=%s"%(veld, waarde))
		
def empty(myString):
	if myString == "nil":
		return True
	elif myString and myString.strip():	#	myString is not None AND myString is not empty or blank
		return False
	return True
	
def isnumeric( waarde ):
    try:
        float( waarde )
        return True
    except ValueError:
        return False
		
class Tuinhuis(object):
	def __init__(self):
		self.temperatuur = 0
		self.thingsspeak = 0
		self.aanuit = 0
		self.deur = 0
		self.interval = randint(275,325)

		resultaat = httpGet("http://192.168.0.13:1208", 4, "Tuinhuis: ")
		if (resultaat.status_code == requests.codes.ok):
			self.aanuit			= resultaat.json()["schakelaar"]
			self.deur			= resultaat.json()["deur"]
			self.temperatuur	= resultaat.json()["temperatuur"]
			self.thingsspeak	= resultaat.json()["temperatuur"]
			msg.console("Tuinhuis: %s, %s, %s"%(self.aanuit, self.deur, self.temperatuur))
		self.check()

	def schakel(self, aanofuit):
		resultaat = httpGet("http://192.168.0.13:1208?schakelaar:%s"%aanofuit, 4, "Tuinhuis: ")
		if (resultaat.status_code == requests.codes.ok):
			self.aanuit = resultaat.json()["schakelaar"]	
		return self.aanuit

	def check(self):
		self.thread = threading.Timer(self.interval, self.check)
		self.thread.daemon = True 
		self.thread.start()

		resultaat = httpGet("http://192.168.0.13:1208", 4, "Tuinhuis: ")
		if (resultaat.status_code == requests.codes.ok):
			self.aanuit = resultaat.json()["schakelaar"]
			self.deur 	= resultaat.json()["deur"]
			self.temperatuur = resultaat.json()["temperatuur"]

		httpGet("http://%s:51828/?accessoryId=schuurdeur&state=%s"%(config.get("webhook"),("true" if self.deur == 0 else "false")))
		return self.aanuit
		
	def stop(self):
		msg.console("Tuinhuis check wordt gestopt...")
		self.thread.cancel()
		
class Woonkamer(object):
	def __init__(self):
		self.temperatuur = 0
		self.staandelamp = 0
		self.aanuit = False
		self.lichtaan = zononder()-5400
		self.lichtuit = self.uittijd()
		
		self.buroaanuit = 0
		self.bureaulcht = 0
		self.voordlicht = 0
		self.lichtsterkte = 0
		
		self.thread = None
		self.interval = randint(275,325)
		
		self.check()
		
	def uittijd(self):
		today = datetime.date.today() # wanneer is het
		# hoeveel seconden zijn er al verstreken vandaag
		seconds_since_midnight = time.time() - time.mktime(today.timetuple())
		# hoeveel zijn er nog over... 24x60x60 seconden in een dag minus 
		seconden_tot_middernacht = 86400 - seconds_since_midnight 
		# tel er not wat seconden er bij
		return time.time() + seconden_tot_middernacht + randint(900,2700)
		
	def schakel(self, aanofuit):
		if aanofuit == "flp": aanofuit = "off" if self.aanuit == 1 else "on"
		aanofuit = "false" if aanofuit == "uit" else "true"
		msg.console("schakelen (self.aanuit: %s), %s"%(self.aanuit, aanofuit) )
		try:
			data = '{"characteristics":[{"aid":2, "iid":9, "value":%s}]}'%aanofuit
			requests.put('http://HAA-A62F21.local:5556/characteristic', data=data) # muurschakelaar
			self.aanuit = True if aanofuit == "true" else False
		except: pass
		return self.aanuit	
				
	def automatisch(self):
		if time.time() > self.lichtaan:
			msg.console( "Het is tijd om lichten aan te doen (t > %s)"%showtime(self.lichtaan), "blue")
			if self.lichtsterkte < config.get("lichtsterkte"):
				msg.console( "aanuit: %s "%(self.aanuit), "blue")
				if self.aanuit == 0:
					if self.schakel("aan"):
						self.aanuit = 1
						msg.pushover("Woonkamerlicht automatisch aan (%s)"%self.voordlicht)
						self.lichtaan = zononder()-3600
			else:
				msg.console( "Maar het is nog te licht (%s > %s)"%(self.lichtsterkte,config.get("lichtsterkte")), "blue")
			
		elif time.time() > self.lichtuit:
		#	alleen als we niet thuis zijn (alarmsysteem staat aan) dan moet licht automatisch uit
			if alarmsysteem.status != 0 and self.aanuit == 1:	
				if not self.schakel("uit"):
					self.aanuit = 0
					msg.pushover("Woonkamerlicht automatisch uitgedaan")

		if	time.time() > self.lichtaan:
		#	is het licht al aan, kan nog aan het wachten zijn op voldoende donker
			if self.aanuit == 1:		
				self.lichtaan = zononder()-3600
				
		elif time.time() > self.lichtuit:
		#	is het licht al uit, zoniet nog even laten anders gaat het nooit uit
			if self.aanuit == 0:		
				self.lichtuit = self.uittijd()
				
	def lichtmeting(self):
		resultaat = httpGet("http://192.168.0.10:3004?lightlevel")
		if (resultaat.status_code == requests.codes.ok):
			self.lichtsterkte = int(resultaat.json()["lightlevel"])
			#msg.console("Lichtsterkte bij kattenluik %s"%self.lichtsterkte, "blue")

	def check(self):
		self.thread = threading.Timer(self.interval, self.check)
		self.thread.daemon = True 
		self.thread.start()
		
		self.lichtmeting()
		self.aanofuit()

		msg.console("De verlichting is %s"%("aan" if self.aanuit else "uit"), "blue")

		self.automatisch()
		msg.console("Status bijgewerkt, licht aan tussen %s en %s"%(showtime(self.lichtaan),showtime(zononder())), "blue")

		return self.aanuit
	
	def aanofuit(self):
		resultaat = httpGet( "http://HAA-A62F21.local:5556", 4, "Muurschakelaar")
		if resultaat.status_code == 200:
			try:
				for regel in resultaat.json()["accessories"]:
					for service in regel["services"]:
						for characteristic in service["characteristics"]:
							if characteristic["type"] == "25":
								if characteristic["aid"] == 2:
									msg.console("\033[33mMuurschakelaar HAA-A62F21 - %s\033[0m"%(characteristic["value"]))
									self.aanuit = characteristic["value"]
			except: pass
	
	def stop(self):
		msg.console("Woonkamer check wordt gestopt...", "blue")
		self.thread.cancel() if self.thread else None
	
def showtime(tijd):
	lokaletijd = time.localtime(tijd)
	weekdagen = {0:"zondag",1:"maandag",2:"dinsdag",3:"woensdag",4:"donderdag",5:"vrijdag",6:"zaterdag"}
	dag = weekdagen[int(time.strftime("%w", lokaletijd))]
	return "%s %s"%(dag, time.strftime("%H:%M", lokaletijd))
	
def waarde( w ):
	if type(w) is float: 
		return w
	elif type(w) is int: 
		return w
	else:
		return -99
		
def zononder():
	capijs		= ephem.Observer()
	capijs.lat	= '51.916905'
	capijs.long	=  '4.563472'
		
	sun = ephem.Sun() # define sun as object of interest
#	sun.compute(capijs)
	return ephem.localtime(capijs.next_setting(sun)).timestamp()

def nacht():
	o = ephem.Observer()
	o.lat  = '51.916905'
	o.long =  '4.563472'
		
	sun = ephem.Sun() # define sun as object of interest
	sunrise = o.next_rising(sun)
	sunset  = o.next_setting(sun)

	return 1 if (ephem.localtime(sunrise) < ephem.localtime(sunset)) else 0

#	this class will handles any incoming request from the browser 
class myHandler(BaseHTTPRequestHandler):
	def log_message(self, format, *args):
		return

	def do_HEAD(self, contenttype="text/html"):
		self.send_response(200)
		self.send_header("Content-type", contenttype)
		self.end_headers()

	def respond(self, response=None, contenttype="text/html"):
		self.send_response(200)
		self.send_header("Content-type", contenttype)
		self.end_headers()
		self.write( response )

	def failure(self, response=None, contenttype="text/html"):
		msg.console("Response to %s: %s"%(self.client_address[0],response))
		self.send_response(500)
		self.send_header("Content-type", contenttype)
		self.end_headers()
		self.write( response )
		
	def write(self, response):
		if not response is None:
			try:
				self.wfile.write( bytes(response,"utf-8")  )
			except Exception as e:
				msg.console("\033[31m%s bij %s"%(e, response))
				pass

#	Handler for the GET requests
	def do_GET(self):
		global expedit
		global bureaulamp
			
		command = self.requestline.replace("GET /","").replace("?","")
		command = command[:command.find("HTTP")].strip()

		if "getpid" == command:
			self.respond( "%s"%os.getpid() )
			
		elif "nacht" == command:
			self.respond( "1" if nacht() else "0" )
			
		elif command.startswith("woonkamer"):
			if	command.endswith("temperatuur"):
				self.respond("{\"temperature\":%s}"%(woonkamer.temperatuur) )
			else:
				if command.endswith(("aan","uit")):
					aanofuit = "aan" if command.endswith("aan") else "uit"
					woonkamer.schakel("aan" if command.endswith("aan") else "uit")
				self.respond("%s"%woonkamer.aanuit)
			
		elif command.startswith("staandelamp"):			
			self.respond("%s"%langelamp(command[-3:] if command.endswith(("aan","uit")) else ""))

		elif command.startswith("lichies"):
			if command.endswith("brightness"):
				level = 0
				resultaat = httpGet("http://192.168.0.100/cm?cmnd=dimmer",1)
				if (resultaat.status_code == requests.codes.ok):
					level = json.loads(resultaat.text)["Dimmer"]
				self.respond("%s"%level)
				
			elif command.endswith("power"):
				onoff = 0
				resultaat = httpGet("http://192.168.0.100/cm?cmnd=power",1,"lichies",False)
				if (resultaat.status_code == requests.codes.ok):
					onoff = json.loads(resultaat.text)["POWER"]
				onoff = 0 if onoff == "OFF" else 1 if onoff == "ON" else 0
				self.respond("%s"%onoff)
			
		elif command.startswith("vermogen"):
			self.respond("%s"%verbruik.energie)
			
		elif command.startswith("ring"):
			print("De deurbel...")
			try:
				resultaat = requests.get("http://192.168.0.2:1208/bel")
			except:
				pass
			self.respond("Foto is aangevraagd",500)
			
		elif command.startswith("help"):
			tekst	 =	""
			tekst	+=	"achterdeur<br>"
			tekst	+=	"bureau [aan|uit]<br>"
			tekst	+=	"bureaulux<br>"		
			tekst	+=	"lichtsterkte<br>"
			tekst	+=	"lux<br>"		
			tekst	+=	"staandelamp [aan|uit]<br>"
			tekst	+=	"temperatuur<br>"
			tekst	+=	"welterusten<br>"
			tekst	+=	"woonkamer [aan|uit]<br>"
			self.respond(tekst)
		else:
			msg.console( "Opdracht niet begrepen: %s%s"%(command, self.client_address))				
			self.respond("Opdracht niet begrepen: %s"%command)				
		return
		
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

# -------------- ~ main ~ ------------------------------------------

msg = Messaging().console ("Initialisatie...\n" )
config = GetConfig()
udp = udplistner(config.get("udpport"))

verbruik 	 = energie()
woonkamer 	 = Woonkamer()
alarmsysteem = piVeilig()
badkamer	 = humidity("HAA-347FCC")

server = HTTPServer(('', config.get("httpport") ), myHandler)
msg.console("HTTPServer on %s"%config.get("httpport"))
try: server.serve_forever() # Wait forever for incoming http requests
except KeyboardInterrupt:
	msg.console("ctrl-c ontvangen, afsluiten...")
	server.socket.close()
	pass
	
msg.console("(Timer)Threads worden gestopt, momentje...")

udp.stop()
woonkamer.stop()
alarmsysteem.stop()
badkamer.stop()

msg.console("Server wordt opnieuw gestart")
subprocess.call("/usr/bin/screen -dmS listner python3.7 /opt/development/httplistner.py", shell=True)