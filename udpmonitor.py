# monitor voor aantal zaken
# - UDP poort 5005 
# - waarschuwen niemand thuis langer dan 45 minuten

import datetime
import json
import os
import requests
import socket
import subprocess
import time
import ephem
import random
import threading

from smits import Messaging

msg = Messaging()
msg.debug = True

class bitcoin(object):
	def __init__(self):
		print("bitcoin")
		self.previous = 0
		self.proceed = True
		threading.Thread(target=self.checkrate).start()
		
	def checkrate(self):
		print("checkrate")
		while self.proceed:
			r = httpGet("https://blockchain.info/tobtc?currency=EUR&value=1000")
			price = 1000*(1/float(r.text))
			msg.console( "BTC %s euro "%int(price) + ("^" if self.previous>price else "v") )	
			if abs(self.previous-price) > 100:
				self.previous = price
				lichtkrant( "BTC %s euro "%int(price) + ("^" if self.previous>price else "v") )
			time.sleep(60*15)
			
	def stop(self):
		self.proceed = False

class iotListner(object):
	def __init__(self, myport = 2323, seconden = 0):
		# Instellen UDP listener
		self.port = myport
		self.iotudp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # internet, UDP 
		self.iotudp.setblocking(0)
		self.iotudp.settimeout(30)
		self.iotudp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.iotudp.bind(('', myport))
		self.kwh = 0
		self.temperature = 0
		self.proceed = True
		
		threading.Thread(target=self.listen).start()

	def listen(self):
		while self.proceed:
			try:
				jsonstr, addr = self.iotudp.recvfrom(1024) # buffer size is 1024 bytes
				jsonstr = jsonstr.decode("utf8").strip()
				if jsonstr == "": continue

				msg.console("ontvangen via 2323: %s (%s)" % (jsonstr, addr) )
				try: 
					data = json.loads(jsonstr)
				except: 
					continue
					pass
					
				if "name" in data:
					if data["name"] == "tuinhuis":
						temperature = data["temperature"]
						if abs(self.temperature - temperature ) > 0.5:
							lichtkrant("Buiten %.1fC"%temperature)
							self.temperature = temperature 
						
				elif "vermogen" in data:
					msg.console("Vermogen %s"%data["vermogen"]) 
					kwh = data["vermogen"]
					if abs(self.kwh - kwh) > 250:
						lichtkrant("Energie %s Watt"%kwh)
						self.kwh = kwh
						
			except socket.timeout:
				continue
			
	def stop(self):
		self.proceed = False
		self.iotudp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.iotudp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)		
		self.iotudp.sendto(bytes("stop","UTF-8"),('<broadcast>',self.port))


# Instellen UDP listener
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # internet, UDP 
sock.setblocking(0)
sock.settimeout(0.5)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('', UDP_PORT)) # udp port 5005

class udpinit(object):
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
			self.s.sendto(bytes(message,"UTF-8"),('<broadcast>',self.port))

def httpGet( httpCall, wachten = 4, label=""):
	msg.logging( "httpGet: %s"%httpCall )
	resultaat = requests.Response
	try:
		resultaat = requests.get(httpCall, timeout=wachten)
	except requests.Timeout as e:
		msg.console("%s: url=%s, timeout=%s"%(e, httpCall, wachten), "red")
		resultaat.status_code = 999
	except:
		msg.console("Fout: url=%s, timeout=%s"%(httpCall,wachten), "red")
		resultaat.status_code = 999
	return resultaat
	
def lichtkrant( bericht ):
	bericht = bericht.replace(" ","+").strip()
	httpGet("http://192.168.0.242/?tekst=%s"%bericht)
	httpGet("http://192.168.0.241/?tekst=%s"%bericht)
	threading.Timer(20, httpGet, ["http://192.168.0.242/?tekst="]).start()
	threading.Timer(20, httpGet, ["http://192.168.0.241/?tekst="]).start()
	
def getjsonsafe( jsonmessage ):
	if not jsonmessage is None:
		try:
			value = int(json.loads(jsonstr.strip())[jsonmessage])
		except:
			value = ""
			pass
	return value
	
# ---- main ----

msg.telegram("<pre>%s</pre> gestart"%__file__)
msg.console("Ready for action...", "green")

iot = iotListner()
btc = bitcoin()

lichtkrant("Buiten\'C")

huisstatus = {"keukendeur":0}
while True:
	try :
		jsonstr, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
		jsonstr = jsonstr.decode("utf8")
		msg.console("ontvangen via UDP: %s (%s)" % (jsonstr.strip(), addr) )
			
		if "deurbel" in jsonstr:
			lichtkrant( "Deurbel" )
	
		elif "katten" in jsonstr:
			lichtkrant( "Kattenluik" )
			
		elif "voordeur" in jsonstr:
			openofdicht = getjsonsafe("voordeur")
			if openofdicht != "": 
				lichtkrant("Voordeur %s"%("gaat open" if openofdicht else "is dicht") )
			
		elif "alarm" in jsonstr:
			lichtkrant( "Alarm" )
			
		elif "Jackson" in jsonstr:
			try:
				lichtkrant("Jackson is naar " + "buiten gegaan" if int(json.loads(jsonstr.strip())["Jackson"]) == 2 else "binnen gekomen")
			except:
				lichtkrant( jsonstr )

		elif "keukendeur" in jsonstr:
			openofdicht = getjsonsafe("keukendeur")
			if openofdicht != "":
				lichtkrant("Keukendeur %s"%("open" if (openofdicht == 1) else "dicht") )
				if (openofdicht != huisstatus["keukendeur"]):
					huisstatus["keukendeur"] = openofdicht
					opendicht = "true" if openofdicht == 0 else "false"
					msg.console(huisstatus["keukendeur"],"blue")
		else:
			lichtkrant( jsonstr.strip() )
		
	except socket.timeout:
		continue

	except (KeyboardInterrupt):
		sock.close()
		break 

iot.stop()
btc.stop()

msg.console(" Restarting...", "yellow")
subprocess.call("screen -dmS udpmonitor python3.7 %s"%__file__, shell=True)
