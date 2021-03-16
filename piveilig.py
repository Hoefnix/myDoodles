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

actief = False

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
				
	def listen(self):
		while self.proceed:
			try :
				string, addr = self.sock.recvfrom(1024) # buffer size is 1024 bytes
				string = string.decode("utf8").strip()
				if string == "": continue
				if "voordeur" in string:
					msg.console( string )
					try:
						if int(json.loads(string.strip())["voordeur"]) == 1:
							if actief: threading.Thread(target=sirene).start()
					except: pass

				elif "keukendeur" in string:
					msg.console( string )
					try:
						if int(json.loads(string.strip())["keukendeur"]) == 1:
							if actief: threading.Thread(target=sirene).start()
					except: pass

				else:
					msg.console( "\033[2m%s"%string )


			except socket.timeout:
				continue
				
	def stop(self):
		msg.console("Stopping UDP listner")
		self.proceed = False
		self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self.s.sendto(bytes(' ',"UTF-8"),('<broadcast>',5005))

class messaging( object ):
	def __init__(self):
		self.debug = False
		self.chat_id = "12463680" # johannes_smits
		self.parse_mode = "HTML"
		self.bot = "bot112338525:AAGyQLESoyVnCAdBJZTdaRcgV5KwN3uGipU"
		
	def console(self, message=None, colour=None):
		if not message is None:
			if colour == "red":
				kleur = "\033[31m"
			elif colour == "green":
				kleur = "\033[92m"
			elif colour == "yellow":
				kleur = "\033[93m"
			elif colour == "blue":
				kleur = "\033[94m"
			else:
				kleur = "\033[0m"
			
			print("\033[K\033[3m%s\033[0m - %s%s\033[0m"%(time.strftime("%H:%M:%S"), kleur, message))
		return self

	def telegram(self, message = None, image = None):
		#	johannes_smits	=  "12463680"
		#	alarmsysteem	= "-24143102"
		#	christie			=  "15044759"
		if not message is None:
			self.message = message
			threading.Thread(target=self.mergelet).start()
		else:
			self.console("Niets om te verzenden")		
		return self
		
	def mergelet(self):
		sendMessage  = "https://api.telegram.org/%s/sendMessage"%self.bot

		arguments = {}
		arguments["parse_mode"] = self.parse_mode
		arguments["chat_id"]    = self.chat_id
		arguments["text"]       = self.message
		
		try:
			r = requests.get(sendMessage, data=arguments, timeout=5)
		except requests.Timeout as e:
			self.console("Telegram - %s"%e)
		except:
			self.console("Telegram - Fout")

class GetConfig( object ):
#	{"type":"config","callback":"83.86.240.150","webhook":"192.168.178.125","udpport":2323,"lichtsterkte":100}
	def __init__(self):
		path = Path(__file__).parent.absolute()
		with open("%s/common/sibeliusweg.json"%path, "r") as configfile:
			self.config = json.load(configfile)

	def get(self, key):
		if key in self.config:
			return self.config[key]
		return ""

#	this class will handles any incoming request from the browser 
class myHandler(BaseHTTPRequestHandler):
	def log_message(self, format, *args):
		return

	def do_HEAD(self, contenttype="text/html"):
		self.send_response(200)
		self.send_header("Content-type", contenttype)
		self.end_headers()

	def respond(self, response=None, contenttype="text/html"):
#		msg.console("Response to %s: %s"%(self.client_address[0],response))
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
		global actief
		global msg
			
		command = self.requestline.replace("GET /","").replace("?","")
		command = command[:command.find("HTTP")].strip()

		if command.startswith("trigger"):
#			msg.console( command.replace("trigger=","") )
			if actief: threading.Thread(target=sirene).start()
			self.respond("{\"alarmsysteem\":%s}"%actief)

		elif command == "status":
#			msg.console( "(status) Alarmsysteem is %s"%("actief" if actief else "uit"))
			self.respond("1" if actief else "0")
		
		elif command == "aan":
			actief = True
			msg.console("(aan) Alarmsysteem is %s"%("actief" if actief else "uit"))
			msg.telegram("(aan) Alarmsysteem is %s"%("actief" if actief else "uit"))			
			self.respond("1" if actief else "0")

		elif command == "uit":
			actief = False
			msg.console( "(uit) Alarmsysteem is %s"%("actief" if actief else "uit"))
			msg.telegram( "(uit) Alarmsysteem is %s"%("actief" if actief else "uit"))
			self.respond("1" if actief else "0")
			
		elif command == "deurbel":
			msg.console( "De deurbel")
			self.respond("1" if actief else "0")
	
		else:
			tekst	 =	"Opdracht niet begrepen, geldige commando's zijn:"
			tekst	+=	"http://<ip>:8762?trigger<br>"
			tekst	+=	"http://<ip>:8762?arm<br>"
			tekst	+=	"http://<ip>:8762?disarm<br>"
			tekst	+=	"http://<ip>:8762?status<br>"
			
			msg.console( "Opdracht niet begrepen: %s%s"%(command, self.client_address))				
			self.respond(tekst)
		return
		
def sirene():
	for x in range(10, 0, -1):
		if actief:
			msg.console("bliep %s"%x)
			time.sleep(x)    # pause ? seconds
			continue
		break

	while actief:
		msg.console("Wiehuwiewhuwie.... alarm gaat af")
		msg.telegram("Wiehuwiewhuwie.... alarm gaat af")
		time.sleep(60)    # pause 60 seconds

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

msg = messaging().console ("Initialisatie...\n" )
config = GetConfig()
udp = udplistner(5005)

server = HTTPServer(('', 8762 ), myHandler)
try: server.serve_forever() # Wait forever for incoming http requests
except KeyboardInterrupt:
	msg.console("ctrl-c ontvangen, afsluiten...")
	server.socket.close()
	pass
	
udp.stop()
msg.console("Server wordt opnieuw gestart")
subprocess.call("/usr/bin/screen -dmS piveilig python3.7 %s"%__file__, shell=True)