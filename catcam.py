#!/usr/bin/env python3.7

import cv2
import ephem
import json
import locale
import os
import requests
import RPi.GPIO as GPIO
import socket
import subprocess
import threading
import time

from random import randint
import asyncio
from pathlib import Path
from shutil import copyfile

from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler,HTTPServer
from io import BytesIO
from PIL import Image, ImageStat, ImageDraw, ImageEnhance, ImageFont, ImageOps
from requests.auth import HTTPBasicAuth

'''
sensoren voor keukendeur, geluid
bewegingsherkenning via camerabeeld, verzenden fotos
'''
# voor de telegram bot
tgAPIcode	= "112338525:AAGyQLESoyVnCAdBJZTdaRcgV5KwN3uGipU"
botAPIcode	= "328955454:AAEmupBEwE0D7V1vsoB8Xo5YY1wGIFpu6AE"	#kattenluikbot

jhsmChat		=  "12463680" 
luikChat		= "-12086796"

vorigefoto	= time.time()
UDP_PORT	= 5006
PORT_NUMBER	= 3004

PIR  = 10
BTEN = 19
DEUR = 13 # goio2 was 22 #  6
LEDS =  8 # 15
CLED = 24 # 10
MICR = 7 #  0

verbose = False
collstats = 0

geel = "\033[33m"
groen = "\033[32m"

# bufferless VideoCapture
class VideoCapture(object):
	def __init__(self, name):
		self.proceed = True
		self.frame = []
		self.success = False
		self.cap = cv2.VideoCapture(name)
		t = threading.Thread(target=self._reader)
		t.daemon = True
		t.start()
		logging.info(groen+"VideoCaptue running")

  	
	def _reader(self):
		while self.proceed:
			success, frame = self.cap.read()
			if success: 
				self.frame = frame
   
	def read(self):
		while not len(self.frame):
			time.sleep(0.25)
			logging.info("No frame received, retry")

		if len(self.frame):
			try:
				color_coverted = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
				return Image.fromarray(color_coverted)
			except:
				pass
				return []
				
	def release(self):
		self.proceed = False
		self.cap.release()

def convertAlkalineVoltageToCapacity(v):
  if (v >= 1.55):
    return 100
  elif (v <= 0):
    return 0
  elif (v > 1.4):
    return 60.60606*v + 6.060606
  elif (v < 1.1):
    return 8.3022*v
  else:
    return 9412 - 23449*v + 19240*v*v - 5176*v*v*v

def capacity(v):
	'''
	Capacity	100%	90%		80%		70%		60%		50%		40%		30%		20%		10%		0%
	Zero-load	1.59V	1.44V	1.38V	1.34V	1.32V	1.30V	1.28V	1.26V	1.23V	1.20V	1.10V
	330 mW		1.49V	1.35V	1.27V	1.20V	1.16V	1.12V	1.10V	1.08V	1.04V	0.98V	0.62V
	'''
	v=v*0.95
	logging.info("checking capacity %sV"%v)
	return 100 if v > 1.36 else 75 if v > 1.3 else 50 if v > 1.245 else 25 if v > 1.25 else 10 if v > 1.10 else 0 #zero load
#	return 100 if v > 1.235 else 75 if v > 1.12 else 50 if v > 1.12 else 25 if v > 1.06 else 10 if v > 0.98 else 0

def batterij(c):
	return ("\u25A0" * (4 if c > 75 else 3 if c > 50 else 2 if c > 25 else 1 )).ljust(4,"\u25A1")

def weer():
	hetweer = ""
	
	resultaat = httpGet("http://192.168.0.13:1208?temperature")
	if resultaat.status_code != 999:
		hetweer = "%.1f\u02DAC \u2219 "%resultaat.json()["temperature"]

	location = "Capelle aan den IJssel"
	resultaat = httpGet("http://api.openweathermap.org/data/2.5/weather?q=%s&units=metric&lang=nl&APPID=2799a7fec820a086d91e60e3b48fac5a"%location)
	if resultaat.status_code != 999:
		if "city not found" in resultaat.text:
			print("Plaatsnaam (%s) niet gevonden"%location)
		else:
			hetweer += resultaat.json()["weather"][0]["description"]
	return hetweer
	
def thingspeak(veld="field6",waarde=None, omschrijving = ""):
	logging.info("Thingspeak update %s, %s = %s"%(omschrijving, veld, waarde))
#	logging.info("Thingspeak update %s, %s = %s"%(omschrijving, veld, waarde))
	if not waarde is None:
		threading.Thread(target=httpGet, args=("https://api.thingspeak.com/update?key=J4DYH7HQG66U7NXS&%s=%s"%(veld, waarde),)).start()

def config( name ):
	settings = {}
	try:
		path = Path(__file__).parent.absolute()
		with open("%s/common/sibeliusweg.json"%path) as configfile:
			settings = json.load(configfile)
	except:
		print("fout settingsfile %s/common/sibeliusweg.json"%path)
		return ""
		pass
	return settings[name] if name in settings else ""

class bericht(object):
	def __init__(self, datefmt="%d-%b %H:%M:%S", level="INFO"):
		self.timefmt = datefmt
		self.level = 5 if level =="DEBUG" else 4 if level == "INFO" else 3 if level == "WARNING" else 2 if level == "ERROR" else 1
		
	def success(self, tekst):
		if tekst:
			print("\033[0K\033[0m%s - \033[32m%s\033[0m"%(time.strftime(self.timefmt),tekst))
			
	def debug(self, tekst):
		if tekst and self.level > 4:
			print("\033[0K\033[0m%s - \033[3m%s\033[0m"%(time.strftime(self.timefmt),tekst))
	
	def info(self, tekst, color="\033[2m"):
		if tekst and self.level > 3:
			print("\033[0K\033[0m%s - \033[33m%s\033[0m"%(time.strftime(self.timefmt),tekst))
			
	def warning(self, tekst):
		if tekst and self.level > 2:
			print("\033[0K\033[0m%s - \033[92m%s\033[0m"%(time.strftime(self.timefmt),tekst))

	def error(self, tekst):
		if tekst and self.level > 1:
			print("\033[0K\033[0m%s - \033[31m%s\033[0m"%(time.strftime(self.timefmt),tekst))

	def critical(self, tekst):
		if tekst and self.level > 0:
			print("\033[0K\033[0m%s - \033[33m%s\033[0m"%(time.strftime(self.timefmt),tekst))

class udpinit(object):
	def __init__(self, myport = 5006):
		self.port = myport
		self.sb = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.sb.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

		self.sl = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # internet, UDP 
		self.sl.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.sl.bind(('', UDP_PORT)) 

	def broadcast(self, message = ""):
		logging.info("Broadcasting: %s"%message)
		try:
			self.sb.sendto(bytes(message,"UTF-8"),('<broadcast>',self.port))
		except Exception as e:
			logging.info("Broadcast failed, reason: {}".format(e))
			pass

	def listen(self, timeout=300):
		try:
			self.sl.settimeout(timeout)
			data, addr = self.sl.recvfrom(1024) # buffer size is 1024 bytes
			return data.decode("utf8").strip()
		except socket.timeout:
			pass
			return ""

udp = udpinit()

def telegram( chat_id="-12086796", message = None, image = None ):
	# chat_id = "12463680"

	if not message is None:
		url = "https://api.telegram.org/bot112338525:AAGyQLESoyVnCAdBJZTdaRcgV5KwN3uGipU/sendMessage"
		payload = {"chat_id":chat_id, "text":message, "parse_mode":"HTML"}
		r = requests.get(url, params=payload)	
		return (r.json()["ok"])

	elif not image is None:
		logging.debug("sending %s"%image)
#		chat_id = "12463680"
		url	= "https://api.telegram.org/bot112338525:AAGyQLESoyVnCAdBJZTdaRcgV5KwN3uGipU/sendPhoto"
		data	= {'chat_id': chat_id}
		files	= {'photo': (image, open(image, "rb"))}
		r = requests.post(url , data=data, files=files)
		return (r.json()["ok"])
	
def httpGet( httpCall, wachten = 5, logger=False):
	resultaat = requests.Response
	try:
		logging.info("\033[33mhttpGet: url=%s, timeout=%s"%(httpCall, wachten)) if logger else None
		resultaat = requests.get(httpCall, timeout=wachten)
	except requests.Timeout as e:
		logging.warning("\033[31mhttpGet: %s: url=%s, timeout=%s"%(e, httpCall, wachten))
		resultaat.status_code = 999
	except:
		logging.error("\033[31mhttpGet fout: url=%s, timeout=%s"%(httpCall,wachten))
		resultaat.status_code = 999
	return resultaat

class SureFlap():
	def __init__(self, username, password):
		self.offset = utcoffset()
		logging.info("UTC offset is %s"%self.offset)

		self.username = username
		self.password = password
		self.endpoint = "https://app.api.surehub.io"
		self.deviceid = randint(1000000000, 9999999999)
		self.resetConnection()
		self.token = ""
		self.household = 0
		self.positions = {}
		self.since = {}
		self.getPetPosition()
		self.flapid = 0
		self.voltage = 0
		self.capacty = 0
		self.online = False
		self.header = {}

	def getToken(self):
		url = self.endpoint + "/api/auth/login"
		data = {}
		data["email_address"] = self.username
		data["password"] = self.password
		data["device_id"] = self.deviceid
		self.header = {}
		
		logging.info("Trying to log in as %s"%self.username)
		response = requests.post(url, data=data)
		if response.status_code == 200:
			logging.success("getToken: Login successful")
			self.token = response.json()["data"]["token"]
			self.header = {"authorization" : "Bearer " + response.json()["data"]["token"]}
			return self.token
		logging.error("getToken failed ")
		return ""

	def getHousehold(self):
		if not self.token:
			self.getToken()

		if self.token:
			url = self.endpoint + "/api/household"
			url += "?with[]=household&with[]=pet&with[]=users&with[]=timezone&with[]=children"
	
			logging.info("Getting household ID")
			response = requests.get(url, headers=self.header)
			if response.status_code == 200:
				logging.debug("Household ID = %s"%response.json()["data"][0]["id"])
				self.household = response.json()["data"][0]["id"]
				return self.household
		logging.error("getHousehold: failed: %s"%response.text)
		return 0
		
	def getDevices(self):
		if not self.household:
			self.getHousehold()

		if self.household:
			url = self.endpoint + "/api/household/%s/device?with[]=position"%self.household
			self.header = {"authorization" : "Bearer " + self.token}

			response = requests.get(url, headers=self.header)
			if response.status_code == 200:
				for device in response.json()["data"]:
					# print( device )
					#	Type 1: Hub
            		#	Type 2:Repeater
               		#	Type 3: Pet Door Connect
               		#	Type 4: Pet Feeder Connect
               		#	Type 5: Programmer
               		#	Type 6: DualScan Cat Flap Connect
					#	---
					#	print( "ID ", device["id"]  )
					#	print( "ProductID ", device["product_id"]  )
					#	print( "Naam ", device["name"]  )
					self.flapid = device["id"] if device["product_id"] == 6 else self.flapid
					logging.info( self.flapid )
			else:
				# force new login, hopefully that will fix the error
				logging.error("getDevices: Fout op: %s"%url)
				logging.error("getDevices: %s"%response.text)
				logging.error("getDevices: Token en household gereset")
				self.token = ""
				self.household = 0

	def updateFlapStatus(self):
		global loop
		while loop:
			time.sleep(300)

			if not self.household: 
				self.getHousehold()

			if self.household:
				if not self.flapid:
					self.getDevices(self)
				
				if self.flapid:
				#	/api/device/$flap/status
					url = self.endpoint + "/api/device/%s/status?with[]=position"%self.flapid
					headers = {"authorization" : "Bearer " + self.token}

					response = requests.get(url, headers=headers)
					if response.status_code == 200:
						if self.voltage != response.json()["data"]["battery"]:
							self.voltage = response.json()["data"]["battery"]
							self.online = response.json()["data"]["online"]
							if not response.json()["data"]["online"]:
								telegram("12463680", "Kattenluik offline")
							
							self.capacty = int(capacity(self.voltage/4))
							logging.info("Kattenluik (%s) is %sline, voltage batterij is %sV"%(self.flapid, onoff, float(response.json()["data"]["battery"])))
					else:
						logging.error("updateFlapStatus: Fout op: %s"%url)
			else:
				# force new login, hopefully that will fix the error
				logging.error("updateFlapStatus Token en household gereset")
				self.token = ""
				self.household = 0
	
	def getFlapStatus(self):
		if not self.household: 
			self.getHousehold()

		if self.household:
			if not self.flapid:
				self.getDevices()
				
			if self.flapid:
			#	/api/device/$flap/status
				url = self.endpoint + "/api/device/%s/status?with[]=position"%self.flapid
				headers = {"authorization" : "Bearer " + self.token}

				response = requests.get(url, headers=headers)
				if response.status_code == 200:
#					for status in response.json()["data"]:
#						logging.info(( status, response.json()["data"][status] )
					if self.voltage != response.json()["data"]["battery"]:
						self.voltage = response.json()["data"]["battery"]
						if not response.json()["data"]["online"]:
							telegram("12463680", "Kattenluik offline")
							
						self.capacty = int(capacity(self.voltage/4))
						
						onoff = "on" if response.json()["data"]["online"] else "off"
						
						thingspeak("field1",response.json()["data"]["battery"])
						telegram("12463680", "Kattenluik (%s) is %sline, voltage batterij is %sV (%s%%)"%(self.flapid, onoff, float(response.json()["data"]["battery"]),self.capacty))
						logging.info("Kattenluik (%s) is %sline, voltage batterij is %sV"%(self.flapid, onoff, float(response.json()["data"]["battery"])))
				else:
					telegram("12463680", "Informatie over luik niet beschikbaar")
					logging.error("getFlapStatus: Fout op: %s"%url)

			else:
				telegram("12463680", "Luik niet gevonden")
		else:
			# force new login, hopefully that will fix the error
			logging.error("getFlapStatus: Token en household gereset")
			self.token = ""
			self.household = 0

	def getTags(self):
		if not self.household: 
			self.getHousehold()

		if self.household:
			url = self.endpoint + "/api/device/%s/tag?with[]=position"%self.flapid
			headers = {"authorization" : "Bearer " + self.token}

			response = requests.get(url, headers=headers)
			if response.status_code == 200:
				for tag in response.json()["data"] :
					if	 tag['profile'] == 2:
						profile = "outdoor"
					elif tag['profile'] == 3:
						profile = "indoor"
					elif tag['profile'] == 5:
						profile = "intruder"
					#print( tag, profile)
			else:
				# force new login, hopefully that will fix the error
				logging.error("getTags: Fout op: %s"%url)
				logging.error("getTags: token en household gereset")
				self.token = ""
				self.household = 0
				
	def setPetProfile(self):
		if not self.household:
			self.getHousehold()

		if self.household:
			url = self.endpoint
			url += "/api/device/%s/tag/%s"%(self.flapid,"151092")
			headers = {"authorization" : "Bearer " + self.token}

			payload = {"profile":5}

			response = requests.put(url, headers=headers, params=payload)
			print(response.text)

	def setPetPosition(self):
		if not self.household:
			self.getHousehold()

		if self.household:
			url = self.endpoint
			url += "/api/pet/%s/position"%"140104" # testtag id = 140104
			url += "?with[]=position"
			headers = {"authorization" : "Bearer " + self.token}

			payload = {"where":1, "since":"2020-09-08 15:58"}

			response = requests.post(url, headers=headers, params=payload)
			if response.status_code == 200:
				logging.info("setPetPosition: success")
		
	def getPetPosition(self):
		if not self.household:
			self.getHousehold()

		if self.household:
			url = self.endpoint + "/api/household/%s/pet?with[]=position"%self.household
			headers = {"authorization" : "Bearer " + self.token}

			response = requests.get(url, headers=headers)
			if response.status_code == 200:
			#	logging.info("getPetPosition() %s returned status code: %s"%(url,response.status_code))

				for pet in response.json()["data"]:
					# for veld in pet: print(veld, pet[veld])
					if "position" not in pet: return

					since = datetime.strptime(pet["position"]["since"],"%Y-%m-%dT%H:%M:%S+00:00") + timedelta(hours=self.offset) # 2 bij zomertijd, 1 bij wintertijd
					if pet["name"] in self.positions:
						logging.debug("%s%s%s"%(pet["name"].ljust(8), self.positions[pet["name"]], pet["position"]["where"]))
						if self.positions[pet["name"]] != pet["position"]["where"] or self.since[pet["name"]] != since:
							tekst = "{} naar {}".format(pet["name"], ("binnen gekomen" if pet["position"]["where"]==1 else "buiten gegaan") )
							tekst = "Op %s is %s"%(since.strftime("%A %d %B om %H:%M.%S").lower(), tekst)
							self.webhook(pet["name"], ("false" if pet["position"]["where"] == 2 else "true" ))
							telegram("-12086796", tekst)
							logging.info( pet )

					self.positions[pet["name"]] = pet["position"]["where"]
					self.since[pet["name"]] = since
			elif response.status_code == 502:
				logging.warning("getPetPosition: Server responded with 502 Bad Gateway error")
			else:
				# force new login, hopefully that will fix the error
				logging.error("getPetPosition: Fout op: %s, status code: %s"%(url,response.status_code))
				logging.error("getPetPosition: Token en household gereset")
				self.token = ""
				self.household = 0

	def monitorPetPostition(self):
		self.getPetPosition()
		
		for name in self.positions:
			self.webhook(name, ("false" if self.positions[name] == 2 else "true" ))
			
		interval = 15 if night() else 30
		# print( self.positions )

		self.thread = threading.Timer(interval, self.monitorPetPostition)
		self.thread.start()

	def webhook(self, name, position):
		url = "http://"+config("webhook")+":51828/?accessoryId=%s&state=%s"
		httpGet(url%(name, position), 5, False)

	def resetConnection(self):
		self.token = ""
		self.household = 0

	def stop(self):
		self.thread.cancel()

def utcoffset():
	try:
		r = requests.get('https://worldtimeapi.org/api/timezone/Europe/Amsterdam')
		return 1 if r.json().get('utc_offset') == "+01:00" else 2
	except Exception as e:
		logging.error('Error getting timezone', e)
	return 1

class camera(object):
	def __init__(self):
		self.lichtsterkte = 100
		self.getframe()
		self.width, self.height = self.foto.size
		self.prvious = self.foto.load()
		self.current = self.prvious
		self.loop = True

		self.sleepsecs = 2
		self.vorigefoto = time.time()
		self.font = ImageFont.truetype(font="/opt/development/arial.ttf", size=16)
	
		self.threshold	= 100	# wanneer classificeren we een pixel anders (ietsje lichter of donkerder)?
		self.sensitivity = 450	# hoeveel pixels mogen er anders zijn voordat we er wat over zeggen
		
		threading.Thread(target=self.beweging, args=()).start()
		
		self.chatid = "-12086796"
		#self.chatid = "12463680"
		
		logging.info(("Bewegingsdetectie is actief"))
		logging.info("\033[32mImage size is %s x %s"%(self.width, self.height))

	def beweging(self):
		logging.info("\033[32mBewegingsdetectie gestart, interval is %s seconden"%self.sleepsecs)		
		while self.loop:
			# Swap comparison buffers
			self.prvious = self.current

			starttijd = time.time()
			if not self.getframe():
				time.sleep(0.1)
				continue
			
			changedPixels = 0
			for x in range(1, self.width, 4):
				# Scan one line of image then check sensitivity for movement
				for y in range(1, self.height, 3):
					# Just check green channel as it's the highest quality channel
					pixdiff = abs(self.prvious[x,y][1] - self.current[x,y][1])
					if pixdiff > self.threshold:
						changedPixels += 1
						if changedPixels > self.sensitivity: break
				if changedPixels > self.sensitivity: break

			logging.debug("\033[32m Changed pixels: %s Sensitivity %s"%(changedPixels, self.sensitivity))				
			if changedPixels > self.sensitivity:
				logging.info("\033[32m Changed pixels: %s Sensitivity %s"%(changedPixels, self.sensitivity))				
				self.sendfoto() if not GPIO.input(DEUR) else None

			time.sleep(abs(self.sleepsecs-(time.time()-starttijd)))

	def getframe(self):
		'''
	#	r = requests.get("http://127.0.0.1:1964/?action=snapshot")
		flap = cv2.VideoCapture("rtsp://192.168.0.68/live/ch00_1")
		success, frame = flap.read()
		if success:
#			convert from openCV2 to PIL. Notice the COLOR_BGR2RGB which  
#			means that the color is converted from BGR to RGB
			color_coverted = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
			self.foto = Image.fromarray(color_coverted)
			flap.release()
		'''
		self.foto = stream.read()
		if self.foto:
			self.width, self.height = self.foto.size
			
			self.cropped = self.foto.crop((self.width/4,self.height/4, self.width-(self.width/2), self.height-(self.height/4)))
			self.lichtsterkte = int(ImageStat.Stat(self.cropped).mean[0])
			if self.lichtsterkte in range(200, 255):
				enhancer = ImageEnhance.Brightness(self.foto)
				factor = 0.5 #darkens the image
				self.foto = enhancer.enhance(factor)
				
			self.cropped = self.foto.crop((self.width/4,self.height/4, self.width-(self.width/2), self.height-(self.height/4)))
			self.lichtsterkte = int(ImageStat.Stat(self.cropped).mean[0])
			if self.lichtsterkte not in range(5, 230):
				return False

			self.foto = self.foto.crop((0,0, self.width-(self.width/3), self.height))
			self.width, self.height = self.foto.size

			self.current = self.foto.load()
		return True if self.foto else False

	def stop(self):
		logging.info("%s wordt gestopt..."%self.__class__.__name__.capitalize())
		self.loop = False

	def cropper(self, chatid="12463680"):
		if self.getframe():
			self.cropped.save('/var/tmp/catcam.jpg')
			chatid = chatid if chatid != "" else self.chatid
			telegram(chatid, image = "/var/tmp/catcam.jpg")

			return True
		return False
		
	def lux(self, chatid="12463680"):
		chatid = chatid if chatid != "" else self.chatid
		telegram(chatid, "Lichtsterkte bij kattenluik is %s"%self.lichtsterkte)

	def manual(self, chatid=""):
		if self.getframe():
		#	self.foto = ImageOps.autocontrast(self.foto, cutoff=5, ignore=None)			
		#	self.sendfoto()
			
			self.foto.save('/var/tmp/catcam.jpg')
			chatid = chatid if chatid != "" else self.chatid
			telegram(chatid, image = "/var/tmp/catcam.jpg")
			
			return True
		return False
			
	def sendfoto(self, chatid = ""):
		chatid = chatid if chatid != "" else self.chatid

		if (time.time() - self.vorigefoto) > 15: # zit er x seconden tussen om spamming te voorkomen
#			self.foto = ImageOps.autocontrast(self.foto, cutoff=1, ignore=None)
			self.vorigefoto = time.time()
			
			draw = ImageDraw.Draw(self.foto, 'RGBA')
			locale.setlocale(locale.LC_ALL, "nl_NL.UTF-8")

			tekst = "Op %s gebeurt er wat. (%s)"%(time.strftime("%A %d %B om %H:%M").lower(),self.lichtsterkte)
			color = "green" if kattenluik.capacty > 50 else "orange" if kattenluik.capacty > 25 else "red"
			wrtxt = weer()
			x,y = draw.textsize(wrtxt, font=self.font)
			
			draw.line([10, self.height-18, self.width-10, self.height-18], fill=(180, 28, 28, 128), width=20)
			draw.text((15, self.height-27), tekst, (255,255,255), font=self.font)
			
			font = ImageFont.truetype(font="/opt/development/arial.ttf", size=16)
			draw.text((self.width-15-x,self.height-27), wrtxt, (255,255,255), font=font)
			
			font = ImageFont.truetype(font="/opt/development/arial.ttf", size=18)
			draw.text((15,15), batterij(kattenluik.capacty), fill=color, font=font)

			self.foto.save('/var/tmp/catcam.jpg')
			if not GPIO.input(DEUR):
				telegram(chatid, image = "/var/tmp/catcam.jpg")  
			else: 
				logging.info("Camera: Keukendeur open, foto niet verzonden")
		else:
			logging.info("Camera: Te snel, foto niet verzonden")
			time.sleep(15)

		# reset de bewegingsdetectie
		if self.getframe():
			self.prvious = self.foto.load()
			self.current = self.foto.load()

class myHandler(BaseHTTPRequestHandler):
	global catcam, logging 

	def log_message(self, format, *args):
		return

	def do_HEAD(self):
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()

	def respond(self, response=None, status=200):
		logging.debug("\033[12G\033[35mResponse: %s"%response)
		self.send_response(status)
		self.send_header('Content-type','text/html')
		self.end_headers()

		if not response is None:
			try:
				self.wfile.write( bytes(response,"utf-8")  )
			except Exception as e:
				logging.info("\033[31m%s bij %s"%(e, response))
				pass

#	Handler for the GET requests
	def do_GET(self):
		command = self.requestline.replace("GET /","").replace("?","")
		command = command[:command.find("HTTP")].strip()
		logging.debug("Opdracht ontvangen: "+command) if command != "" else None

		if command == "debug":
			logging.level = 5 # DEBUG
			self.respond("Debug on\n")
			
		elif command == "info":
			logging.level = 4 # INFO
			self.respond("Debug off\n")

		elif command == "flits":
			flits()
			self.respond("flits")
			
		elif command.startswith("reset"):
			command = command.replace("reset&","")
			telegram(command, "%s wordt gereset"%__file__) if command != "" else None
			self.respond("%s wordt gereset"%__file__)
			global udp
			udp.broadcast("kattenluik reset")
			self.respond("Done\n",200)

		elif command.startswith("crop"):
			logging.info( command.replace("crop&","") )
			if catcam.cropper(command.replace("crop&","")):
				self.respond("Cropped foto is onderweg naar %s"%command.replace("crop&","") )
			else:
				self.respond("Cropped foto mislukt", 500 )

		elif command.startswith("lightlevel"):
			self.respond("{\"lightlevel\":%s}"%catcam.lichtsterkte)

		elif command.startswith("foto"):
			command = command.replace("&","").replace("foto","")
			if catcam.manual(command):			
				self.respond("Foto is onderweg naar %s"%command)
			else:
				self.respond("Foto is mislukt",500)
				
		elif command.startswith("ring"):
			try:
				resultaat = requests.get("http://192.168.0.2:1208/bel")
			except:
				pass
			else:
				self.respond("Foto is aangevraagd",500)
		else:	
			response  = "\"keukendeur\":%s,"%GPIO.input(DEUR)
			response += "\"lichtsterkte\":%s,"%catcam.lichtsterkte
			self.respond("{%s}"%response )

# ...178?command=foto&telegram=12345678
# ...178?command=aan&gpio=1&telegram=12345678
			
def flits():
	if GPIO.input(CLED) == GPIO.HIGH:
		GPIO.output(CLED,GPIO.LOW)
		# start een timer thread om de lamp na x seconden weer uit te zetten
		threading.Timer(3, GPIO.output, [CLED, GPIO.HIGH]).start()
	
def night():
	# where am i 
	o = ephem.Observer()
	o.lat  = '51.916905'
	o.long =  '4.563472'

	# define sun as object of interest
	s = ephem.Sun()
	sunrise = o.next_rising(s)
	sunset  = o.next_setting(s)
	
	return 1 if (ephem.localtime(sunrise) < ephem.localtime(sunset)) else 0

class webhook(object):
	# periodiek update van de status van de verschillende onderdelen (homebridge/httpwebhooks)
	def __init__(self):
		try:
			path = Path(__file__).parent.absolute()
			with open("%s/common/sibeliusweg.json"%path, "r") as configfile:
				config = json.load(configfile)["sibeliusweg"]
			self.webhook = config["webhook"]
		except:
			self.webhook = "192.168.0.10"
			pass

		self.interval = 120
		self.updatetimer = threading.Timer(self.interval, self.update)

		self.url = "http://"+self.webhook+":51828/?accessoryId=%s&state=%s"
		self.updatetimer.start()

	def update(self):
		httpGet(self.url%("achterdeur", "true" if GPIO.input(DEUR) == 0 else "false"), 5, False)

		self.updatetimer = threading.Timer(self.interval, self.update)
		self.updatetimer.start()
	
	def stop(self):
		logging.info("%s wordt gestopt..."%self.__class__.__name__.capitalize())
		self.updatetimer.cancel() 

def deurevent():
	global udp, loop

	deurstatus = -1 
	logging.info( "Deur monitoring gestart, de deur is nu %s"%("open" if GPIO.input(DEUR) else "dicht") )

	url = "http://"+homebridge.webhook+":51828/?accessoryId=achterdeur&state=true"
	threading.Thread(target=httpGet,args=[url]).start()
	
	while loop:
		nieuwstatus = GPIO.input(DEUR)
		if deurstatus != nieuwstatus:
			if deurstatus in (0,1): udp.broadcast("{\"keukendeur\":%s}"%nieuwstatus)
			deurstatus = nieuwstatus
#			udp.broadcast("{\"keukendeur\":%s}"%deurstatus)
			url = "http://"+homebridge.webhook+":51828/?accessoryId=achterdeur&state=" + ("false" if deurstatus else "true")
			threading.Thread(target=httpGet,args=[url]).start()

		time.sleep(3)

def lux(foto):
	width, height = foto.size
	cropped = foto.crop((width/4,height/4,width-(width/2),height-(height/4)))
	return int(ImageStat.Stat(cropped).mean[0])

class geluid(object):
	def __init__(self):
		global kattenluik

		self.getframe()
		self.fotos    = [(self.foto,datetime.today())] * 10
		self.font = ImageFont.truetype(font="/opt/development/arial.ttf", size=16)
		self.whereabouts = {}

		fotomoment = self.fotos[0]
		draw = ImageDraw.Draw(fotomoment[0], 'RGBA')
		tijd = fotomoment[1].strftime("%A %d %B om %H:%M").lower()
		
		width, height = fotomoment[0].size
		draw.line([10,height-18, width-10, height-18], fill=(0,80,80), width=20)
		
		tekst = "Op %s is catcam gestart."%tijd
		draw.text((15,height-27), tekst, (255,255,255), font=self.font)

		wrtxt = weer()
		x,y = draw.textsize(wrtxt, font=self.font)
		draw.text((width-15-x,height-27), wrtxt, (255,255,255), font=self.font)
		
		color = "green" if kattenluik.capacty > 50 else "orange" if kattenluik.capacty > 25 else "red"
		draw.text((15,15), batterij(kattenluik.capacty), fill=color, font=self.font)

		fotomoment[0].save('/var/tmp/catcam.jpg')
		telegram("12463680", image = "/var/tmp/catcam.jpg")

		# = { "jackson": {"where: 2, "since": "20200101-12:00"} }

		for name in kattenluik.positions:
			self.whereabouts[name] = {}
			self.whereabouts[name]["where"] = kattenluik.positions[name]
			self.whereabouts[name]["since"] = kattenluik.since[name]

		for name in self.whereabouts:
			logging.info( "%s : %s"%(name.rjust(9), self.whereabouts[name]) )
		self.movement()
		
	def getframe(self):
		'''
		flap = cv2.VideoCapture("rtsp://192.168.0.68/live/ch00_1")
		success, frame = flap.read()
		if success:
#			convert from openCV2 to PIL. Notice the COLOR_BGR2RGB which means that 
#			the color is converted from BGR to RGB
			color_coverted = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
			self.foto = Image.fromarray(color_coverted)
			flap.release()
		'''	
		self.foto = stream.read()
		if self.foto:	
			if lux(self.foto) not in range(3, 230): return False
			
			w, h = self.foto.size
			self.foto = self.foto.crop((0,0,w-(w/3),h))
		return True if self.foto else False

	def movement(self):
		global kattenluik

		# self.fotos is eem lijstje met fotos die genomen zijn toen er een geluidje gedetecteerd werd kattenluik
		# registreert tijd wanneer een kat binnen is gekomen. Iedere 5 seconden wordt gekeken of een kat binnen
		# is gekomen door positions met locaties te vergelijken bij verschil dan wordt de foto uit het lijstje
		# gepakt met een opname tijd het dichtst maar wel eerder dan de tijd van de geregistreerde beweging

		for name in kattenluik.positions:
			luik = {}
			luik["where"] = kattenluik.positions[name]
			luik["since"] = kattenluik.since[name]

			if luik != self.whereabouts[name]:
				self.whereabouts[name]["where"] = kattenluik.positions[name]
				self.whereabouts[name]["since"] = kattenluik.since[name]

				logging.info( "Geluid: %s %s"%(name, ("binnen gekomen" if self.whereabouts[name]["where"]==1 else "buiten gegaan")) )

				fotomoment = self.fotos[0]
				kleinste = 999999
				for foto, tijd in self.fotos:
					if self.whereabouts[name]["since"] > tijd:
						diff = self.whereabouts[name]["since"] - tijd
						seconds = diff.seconds 
					else:
						diff = tijd - self.whereabouts[name]["since"]
						seconds = -1*diff.seconds 
						
					logging.info("%s - %s = %s"%(self.whereabouts[name]["since"],tijd,seconds))
					if abs(seconds) < kleinste:
						kleinste = seconds	
						fotomoment = (foto,tijd)

				logging.success("Het wordt die van %s (%s)"%(fotomoment[1],kleinste))
				self.sendfoto(fotomoment, name)

		self.thread = threading.Timer(5, self.movement)
		self.thread.start()
		return None

	def sendfoto(self, fotomoment, name):
		draw = ImageDraw.Draw(fotomoment[0], 'RGBA')
		tijd = fotomoment[1].strftime("%A %d %B om %H:%M").lower()
		tekst = "Op %s kwam %s naar %s."%(tijd, name, ("binnen" if self.whereabouts[name]["where"]==1 else "buiten") )
		tekst = tekst if self.whereabouts[name]["where"]==1 else tekst.replace("kwam","ging")
		color = "green" if kattenluik.capacty > 50 else "orange" if kattenluik.capacty > 25 else "red"
		wrtxt = weer()
		x,y = draw.textsize(wrtxt, font=self.font)

		width, height = fotomoment[0].size
		draw.line([10,height-18, width-10, height-18], fill=(0,80,0), width=20)
		draw.text((15,height-27), tekst, (255,255,255), font=self.font)
		draw.text((width-15-x,height-27), wrtxt, (255,255,255), font=self.font)
		draw.text((15,15), batterij(kattenluik.capacty), fill=color, font=self.font)

		fotomoment[0].save('/var/tmp/catcam.png') 
		telegram( image = "/var/tmp/catcam.png")

	def detected(self, pin):
		if self.getframe():
			self.fotos.append((self.foto,datetime.today().replace(microsecond=0)))
			self.fotos.pop(0)
			trigger = "Geluid"
			logging.debug( "Geluid: Foto toegevoegd aan het lijstje" )
			for name in self.whereabouts: logging.debug( "Geluid: \"%s\" : %s"%(name, self.whereabouts[name]) )
		else:
			logging.error( "Detected: Foto niet gelukt" )

	def stop(self):
		self.thread.cancel()

## -- main -- ##
try:
	loop = True # voor deurevent
	
	logging = bericht(level="INFO")

	logging.info("%s is gestart"%__file__)
	path = Path(__file__).parent.absolute()
	logging.debug("%s/common/sibeliusweg.json"%path)

	locale.setlocale(locale.LC_ALL, "nl_NL.UTF-8")
	stream = VideoCapture("rtsp://192.168.0.68/live/ch00_1")

	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # internet, UDP 
	sock.settimeout(600)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.bind(('', UDP_PORT)) 
	logging.info("UDP listener draait")

	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BOARD)
	GPIO.setup([LEDS], GPIO.OUT, initial=GPIO.HIGH)
	GPIO.setup(CLED, GPIO.OUT, initial=GPIO.HIGH)
	GPIO.setup([PIR, DEUR], GPIO.IN, pull_up_down=GPIO.PUD_UP)

	catcam = camera()
	GPIO.output(LEDS,GPIO.LOW)
	logging.info("GPIO is ingesteld")

	server = HTTPServer(('', PORT_NUMBER), myHandler)
	srvrThread = threading.Thread(target=server.serve_forever)
	srvrThread.daemon = True
	srvrThread.start()
	logging.info("HTTPlistner actief op poort %d"%PORT_NUMBER)
	
	homebridge = webhook() # update homebridge met status
	
	logging.info("Setting up SureFlap monitoring...")
	kattenluik = SureFlap("surepet@smitssmit.nl", "cZtFtGTRKw7W8MJ")
	kattenluik.monitorPetPostition()
	kattenluik.getDevices()
	kattenluik.getFlapStatus()
	kattenluik.setPetPosition()
#	kattenluik.setPetProfile()
	kattenluik.getTags()
	logging.success("SureFlap monitoring activated")

	sound = geluid()
	GPIO.setup(MICR, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
	GPIO.add_event_detect(MICR, GPIO.RISING, callback=sound.detected, bouncetime=3000) 
	logging.success( "Geluidsevent is ingesteld")
	
	threading.Thread(target=deurevent, daemon=True).start()
	threading.Thread(target=kattenluik.updateFlapStatus, daemon=True).start()

	logging.info("Klaar. Ctrl-c voor een herstart")
	
	telegram("12463680", "%s gestart"%__file__)

	while True:
		try:
#			print( weer() )
			
			data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
			data = data.decode("utf8").strip()
			
			if "kattenluik" in data:
				logging.info("Received over UDP: %s"%data)
				if "reset" in data:
					raise KeyboardInterrupt

		except socket.timeout:
			kattenluik.getFlapStatus()
			continue

except (KeyboardInterrupt):# , RuntimeError, TypeError, NameError, ValueError):
	logging.info("Herstart...")
	loop = False
	catcam.stop()
	homebridge.stop()
	kattenluik.stop()
	sound.stop()
	
	stream.release()
	
	server.socket.close()
	
	sock.close()	# close UDP socket
	GPIO.cleanup()

	try:
		copyfile("%s%s"%("/opt/development/",os.path.basename(__file__)),__file__)
	except:
		logging.error( "Kopieren %s%s mislukt"%("/opt/development/",os.path.basename(__file__))) 
		pass
	else:
		logging.info( "Starting %s%s"%("/opt/development/",os.path.basename(__file__)))
		subprocess.call("screen -dmS catcam python3 %s"%__file__, shell=True)
