#!/usr/bin/python3.7

from pathlib import Path
import json
import RPi.GPIO as GPIO
import time
import requests
import threading
import subprocess
import time

from smits import Messaging as msg

def logger( message ):
	if not message is None:
		print("\033[0m%s - %s%s\033[0m"%(time.strftime("%H:%M:%S"), "\033[31m", message))

class GetConfig():
#	{"type":"config","callback":"83.86.240.150","webhook":"192.168.178.125","udpport":2323,"lichtsterkte":100}
	def __init__(self):
		path = Path(__file__).parent.absolute()
		with open("%s/common/sibeliusweg.json"%path, "r") as configfile:
			self.config = json.load(configfile)
			logger("Config loaded")
		
	def get(self, key):
		if key in self.config:
			return self.config[key]
		return ""

def httpGet( url, auth = None, params = ""):
#	logger( "\033[0;93mhttpGet: %s\033[0m"%url )
	resultaat = requests.Response
	resultaat.status_code = -1
	try:
		resultaat = requests.get( url, params=params, auth=auth )
	except Exception as e:
		logger( "\033[0mhttpget: %s (%s)\033[0m"%(e, url))
	return resultaat
	
def webhookupdate(accesoire, status):
	if status in ("true", "false"):
		resultaat = httpGet("http://%s:51828/?accessoryId=%s&state=%s"%(config.get("webhook"), accesoire, status))
	return resultaat
	
def geluidevent(pin):
	logger("geluidje (%s)"%GPIO.input(pin))
	resettimer("Geluidje")

def resettimer( trigger = "" ):
	try:
		logger("%s, resetting timer on HAA-3D8770.local"%trigger)
		data = '{"characteristics":[{"aid":1,"iid":9,"value":false},{"aid":1,"iid":9,"value":true}]}'
		r = requests.put('http://HAA-3D8770.local:5556/characteristic', data=data)
		
		r = requests.get('http://HAA-3D8770.local:5556/characteristics?id=1.11')
		print( "", r.text )	
	except Exception as e:
		pass
		logger("\033[0;95m%s\033[0m"%e)
		msg().telegram("bureaupir: HAA-3D8770.local niet bereikbaar")
		return False
		

	return True

# ~~~ - ~~~ - ~~~ - ~~~ main ~~~ - ~~~ - ~~~ - ~~~ #

try:
	PIN = 14
	microfoon = 17

	config = GetConfig()

	GPIO.setmode(GPIO.BCM)
	#GPIO.setup(PIN, GPIO.OUT, initial=GPIO.LOW)
	GPIO.setup(microfoon, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
	GPIO.setup(PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

	logger("\033[0;95mStarting v0.5\033[0m")
	ontime = 300

	state = GPIO.input(PIN)
	GPIO.add_event_detect(microfoon, GPIO.RISING, callback=geluidevent, bouncetime=200)
	
	resettimer("Startup")
	seconds = time.time()
	msg().telegram("bureaupir is gestart")
	while True:
		if GPIO.input(PIN) != state:
			state = GPIO.input(PIN)
			if state:
				if (time.time() - seconds) > (ontime - 60) :
					seconds = time.time() if resettimer("Movement") else seconds
#				else:
#					logger("Movement, no hurries %s seconds left till shutdown"%(int(ontime-(time.time() - seconds))))
				webhookupdate("bureau", "true")
			else:
				webhookupdate("bureau", "false")
		time.sleep(1)
				
except KeyboardInterrupt:
	print("ctrl-C")
	GPIO.cleanup()
#	logger("Server wordt opnieuw gestart")
#	subprocess.call("screen -dmS bureaupir python3.7 %s"%__file__, shell=True)