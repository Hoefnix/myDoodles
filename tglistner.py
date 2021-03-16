#!/usr/bin/python

import json
import subprocess
import sys
import time
import os
from datetime import datetime
import socket
import requests
import threading
from http.server import BaseHTTPRequestHandler,HTTPServer

# Send UDP broadcast packets

MYPORT = 5005

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('', 0))
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

Johannes_Smits = "12463680"

def console(message=None):
	if not message is None:
		print("\033[3m%s\033[0m - %s"%(time.strftime("%H:%M:%S"),message))

def windrichting( hoek ):
	if hoek:
		if		( hoek > 337.5 and hoek <=   360 ):
			return "noorden"
		elif	( hoek >     0 and hoek <=  22.5 ):
			return "noorden"
		elif	( hoek >  22.5 and hoek <=  67.5 ):
			return "noordoosten"
		elif	( hoek >  67.5 and hoek <= 112.5 ):
			return "oosten"
		elif	( hoek > 112.5 and hoek <= 157.5 ):
			return "zuidoosten"
		elif	( hoek > 157.5 and hoek <= 202.5 ):
			return    "zuiden"
		elif	( hoek > 202.5 and hoek <= 247.5 ):
			return "zuidwesten"
		elif	( hoek > 247.5 and hoek <= 292.5 ):
			return "westen"
		elif	( hoek > 292.5 and hoek <= 337.5 ):
			return "noordwesten"
	else:
		return ""
		
def beaufort( wk ):
	if wk:
		beaufort = []
		beaufort.append([   0,  0.29, 0, "\U00002775", "windstil", "Rook stijgt recht omhoog"])
		beaufort.append([ 0.3,  1.59, 1, "\U00002776", "zwakke wind", "Rookpluimen geven richting aan"])
		beaufort.append([ 1.6,  3.39, 2, "\U00002777", "zwakke wind", "Bladeren ritselen, wind voelbaar in het gezicht"])
		beaufort.append([ 3.4,  5.49, 3, "\U00002778", "matige wind", "Bladeren en twijgen voortdurend in beweging"])
		beaufort.append([ 5.5,  7.99, 4, "\U00002779", "matige wind", "Stof en papier dwarrelen op"])
		beaufort.append([ 8.0, 10.79, 5, "\U0000277a", "vrij krachtige wind", "Takken maken zwaaiende bewegingen"])
		beaufort.append([10.8, 13.89, 6, "\U0000277b", "krachtige wind", "Grote takken bewegen en hoed wordt afgeblazen"])
		beaufort.append([13.9, 17.19, 7, "\U0000277c", "harde wind", "Bomen bewegen"])
		beaufort.append([17.2, 20.79, 8, "\U0000277d", "stormachtige wind", "Twijgen breken af"])
		beaufort.append([20.8, 24.49, 9, "\U0000277e", "storm", "Takken breken af, Dakpannen waaien weg"])
		beaufort.append([24.5, 28.49,10, "\U0000277f", "zware storm", "Bomen worden ontworteld"])
		beaufort.append([28.5, 32.69,11, "\U000024eb", "zeer zware storm", "Uitgebreide schade aan bossen en gebouwen"])
		beaufort.append([32.6, 99.99,12, "\U000024ec", "orkaan", "Niets blijft meer overeind"])
		
		for regel in beaufort:
			if regel[0] <= wk <= regel[1]:
				return ( "<b>%s</b> %s"%(regel[4], regel[3]) )
	else:
		return ""

def pictogram( nummer ):
	pictos = []
	pictos.append(["01d","\U0001F31E","zon"])
	pictos.append(["02d","\U000026C5","wolkje zonnetje"])
	pictos.append(["03d","\U00002601","bewolkt"])
	pictos.append(["04d","\U00002601","zwaar bewolkt"])
	pictos.append(["09d","\U0001F327","zware regen"])
	pictos.append(["10d","\U0001F326","regen (zonnetje)"])
	pictos.append(["11d","\U0001F329","onweer"])
	pictos.append(["13d","\U0001F328","sneeuw"])
	pictos.append(["50d","\U0001f32b","mist"])

	pictos.append(["01n","\U0001f314","maan"])
	pictos.append(["02n","\U000026C5","wolkje zonnetje"])
	pictos.append(["03n","\U00002601","bewolkt"])
	pictos.append(["04n","\U00002601","zwaar bewolkt"])
	pictos.append(["09n","\U0001F327","zware regen"])
	pictos.append(["10n","\U0001F326","regen (zonnetje)"])
	pictos.append(["11n","\U0001F329","onweer"])
	pictos.append(["13n","\U0001F328","sneeuw"])
	pictos.append(["50n","\U0001F32b","mist"])

	for regel in pictos:
		if regel[0] == nummer:
			return ( regel[1] )
	return ( nummer )
	
def circlednr( nummer ):
	waarde = ""
	if nummer in (0,1,2,3,4,5,6,7,8,9,10):
		iconen = ["\u24ea","\u2460","\u2461","\u2462","\u2463","\u2464","\u2465","\u2466","\u2467","\u2468","\u2469"]
		waarde = iconen[nummer]
	return waarde

def supernr( nummer ):
	waarde = ""
	if nummer in (0,1,2,3,4,5,6,7,8,9):
		getallen = ["\u2080","\u2081","\u2082","\u2083","\u2084","\u2085","\u2086","\u2087","\u2088","\u2089"]
		waarde = getallen[nummer]
	return waarde

def strtonum(str):
	try: 
		return int(str) 
	except ValueError: 
		return 0
		
def respond(chatID, bericht = None):
	if not bericht is None:
		bericht = "" + bericht # "<b>"+socket.gethostname()+"</b>\n"+bericht
		payload = {'chat_id':chatID, 'text':bericht, 'parse_mode':'HTML'}
		r = httpGet("https://api.telegram.org/bot112338525:AAGyQLESoyVnCAdBJZTdaRcgV5KwN3uGipU/sendMessage", params=payload)
	return 0

def telegram( chatID = "12463680", bericht = None):
	if not bericht is None:
		bericht = "<b>"+socket.gethostname()+"</b>\n<i>"+bericht+"</i>"
		payload = {'chat_id':chatID, 'text':bericht, 'parse_mode':'HTML'}
		r = httpGet("https://api.telegram.org/bot112338525:AAGyQLESoyVnCAdBJZTdaRcgV5KwN3uGipU/sendMessage", params=payload)
	return

def httpGet( url, auth = None, params = ""):
	console( "\033[33mhttpGet: %s"%url )
	resultaat = requests.Response
	resultaat.status_code = -1
	try:
		resultaat = requests.get( url, params=params, auth=auth )
	except Exception as e:
		console("%s (%s)"%(e, url))
	return resultaat
	
def graden( waarde ):
	return "%d%s"%(waarde, u"\u2103")

class openweathermap( object ):
	def __init__(self, locatie =  "capelle%20aan%20den%20ijssel,nl" ):
		self.location = locatie
		self.bericht = ""
		self.lat = 0
		self.lon = 0
		self.tuinlive = True
		
		url = "https://thingspeak.com/channels/88067/charts/6?days=2&dynamic=true&type=spline&width=auto"
		
		if self.weerbeeld():
			self.verwachting(0) # over 3 uur
			self.verwachting(1) # over 6 uur

	def weerbeeld(self):

		resultaat = httpGet("http://api.openweathermap.org/data/2.5/weather?q=%s&units=metric&lang=nl&APPID=2799a7fec820a086d91e60e3b48fac5a"%self.location)
		if "city not found" in resultaat.text:
			self.bericht = "Plaatsnaam (%s) niet gevonden"%self.location
			return False
		weerbericht = resultaat.json()

		self.bericht = "<i>%s (%s)</i>"%(weerbericht["name"],weerbericht["sys"]["country"])
		self.uvindex(weerbericht)
		
		try:
			tuinhuis = httpGet("http://192.168.0.13:1208?temperature").json()["temperature"]
			tuinlive = True
		except:
			tuinhuis = weerbericht["main"]["temp"]
			tuinlive = False
			pass
		
		self.samenstellen(weerbericht, tuinhuis if self.location.startswith("capelle") else None)
		udp.broadcast( weerbericht["weather"][0]["description"] )
		return True
		
	def verwachting(self, factor = 0):
		resultaat = httpGet("http://api.openweathermap.org/data/2.5/forecast?q=%s&units=metric&lang=nl&APPID=2799a7fec820a086d91e60e3b48fac5a"%self.location)
		
		if (resultaat.status_code == requests.codes.ok):
			verwachting = resultaat.json()["list"][factor]
			self.bericht += "\n\nverwachting voor <b>%s</b>\n"%time.strftime("%H:%M", time.localtime(int(verwachting["dt"])))
			self.samenstellen(verwachting)
		
	def uvindex(self, weerbericht):
		lat = float(weerbericht["coord"]["lat"])
		lon = float(weerbericht["coord"]["lon"])
		resultaat = httpGet("http://api.openweathermap.org/data/2.5/uvi?appid=2799a7fec820a086d91e60e3b48fac5a&lat=%f&lon=%f"%(lat,lon))
		self.bericht += ", %s\u1D58\u1d5b\n"%circlednr(int(round(float(resultaat.json()["value"]))))
		
	def samenstellen(self, json, tuin = None):
		if json:
			print (json["weather"][0]["description"], "\n" )
			if json["weather"][0]["description"] in ("mist","nevel") and int(json["clouds"]["all"] == 0):
				# vreemde nevel bij 0% bewolking vervangen voor onbewolkt
				json["weather"][0]["description"] = "onbewolkt"
				json["weather"][0]["icon"] = "01d"
				
			self.bericht += "%s <b>%s</b>, "%(pictogram(json["weather"][0]["icon"]), json["weather"][0]["description"])
			self.bericht += "%s "%graden(tuin) if tuin else graden(json["main"]["temp"])
			self.bericht += "\u2713" if self.tuinlive and tuin else ""

			if int(json["clouds"]["all"]):
 				self.bericht += ", bewolking %s%%"%json["clouds"]["all"]
			if int(json["wind"]["speed"]):
				self.bericht += ", %s"%beaufort(json["wind"]["speed"])
				if "deg" in json["wind"].keys():
					self.bericht += " uit het %s"%windrichting(json["wind"]["deg"])
			if "rain" in json.keys():
				if "3h" in json["rain"].keys():
					if int(json["rain"]["3h"]):
						self.bericht += ", regen %0.1f\u339c"%float(json["rain"]["3h"])
		
#	{"coord":{"lon":139,"lat":35},
#	 "sys":{"country":"JP","sunrise":1369769524,"sunset":1369821049},
#	 "weather":[{"id":804,"main":"clouds","description":"overcast clouds","icon":"04n"}],
#	 "main":{"temp":289.5,"humidity":89,"pressure":1013,"temp_min":287.04,"temp_max":292.04},
#	 "wind":{"speed":7.31,"deg":187.002},
#	 "rain":{"3h":0},
#	 "clouds":{"all":92},
#	 "dt":1369824698,
#	 "id":1851632,
#	 "name":"Shuzenji",
#	 "cod":200}

def AanUit( message ):
	return "aan" if message.endswith("aan") else "uit" if message.endswith("uit") else ""
	
def doSomething( string ):
	global udp
	dict = {
		"kattenluik crop":"http://192.168.0.10:3004?crop&",
		"kattenluik licht":"http://192.168.0.10:3004?licht&",
		"kattenluik foto":"http://192.168.0.10:3004?foto&",
		"kattenluik pushover":"http://192.168.0.10:3004?pushover&",
		"kattenluik reset":"http://192.168.0.10:3004?reset&",
		"crop kattenluik ":"http://192.168.0.10:3004?crop&",
		"licht kattenluik":"http://192.168.0.10:3004?licht&",
		"foto kattenluik":"http://192.168.0.10:3004?foto&",
		"pushover kattenluik":"http://192.168.0.10:3004?pushover&",
		"reset kattenluik":"http://192.168.0.10:3004?reset&",
		"bowie licht aan":"http://192.168.0.180/cm?cmnd=Power%20On",
		"bowie licht uit":"http://192.168.0.180/cm?cmnd=Power%20Off",
		"licht aan bowie":"http://192.168.0.180/cm?cmnd=Power%20On",
		"licht uit bowie":"http://192.168.0.180/cm?cmnd=Power%20Off"
		}

	message = string["text"].lower()
	mijnIP = myIP()
	
	if message[:4] == "ping":
		respond(string["from"]["id"], "pong (<code>%s</code>) \U0001F600"%mijnIP )

	if message in dict:
		console("Found in dict")
		resultaat = httpGet("%s%s"%(dict[message],string["from"]["id"]))
		if (resultaat.status_code == requests.codes.ok):
			respond(string["from"]["id"], "<i>%s</i> uitgevoerd"%message.capitalize())
		return
	else:
		console("Command not found in dictionary and that is fine, we're checking other options")

	if message.startswith("lichtkrant") and "lichtkrant" != message:
		message = message.replace("lichtkrant","").strip()
		message = message.replace(" ","+").strip()
		udp.broadcast(message)
					
	elif message == "externalip":
		ipadres = httpGet("http://myexternalip.com/raw").content.decode("utf-8").strip(' \t\n\r')
		respond(string["from"]["id"], "extern ip-adres is %s"%ipadres)
		
	elif message == "weer":
		respond(string["from"]["id"], "Moment, weerbericht wordt opgehaald...")
		try:
			respond(string["from"]["id"], " %s"%openweathermap().bericht)
		except:
			pass
			
	elif message.startswith("weer") and "weer" != message:
		respond(string["from"]["id"], "Moment, weerbericht wordt opgehaald...")
		message = message.replace("weer","").strip()
		respond(string["from"]["id"], " %s"%openweathermap( message ).bericht)

	elif message.startswith("volgers"):
		if "volgers" == message:
			respond(string["from"]["id"], "Onjuiste of geen instanaam\nGebruik:<b>volgers</b> <i>instagramnaam</i>")
		else:
			message = message.replace("volgers","").strip()
			answer = httpGet("https://www.instagram.com/%s/?__a=1"%message)
			if (answer.status_code == requests.codes.ok):
				followers = answer.json()['graphql']['user']['edge_followed_by']['count']
				respond(string["from"]["id"], "%s heeft %s volgers"%(message,followers))
			else:
				respond(string["from"]["id"], "Fout bij ophalen volgers voor %s"%message)
		
	elif message == "energie":		
		try:
			with open("/opt/development/common/energie.json", 'r') as f:
				datastore = json.load(f)
		except:
			respond(string["from"]["id"], "Error opening energie.json")
			
		totalen = ""
		momenteel = "Op dit moment "
		urlThings = "https://thingspeak.com/channels/103107/charts/%s?days=2&min=0.01&dynamic=true&type=spline&width=auto&height=auto" 
		for k, v in datastore.items():
			if k == "hoog":
				url = urlThings%"2"
				totalen += "\n\U0001F50C <a href='%s'>hoogtarief</a> %s kWh"%(url, v)
			elif k == "laag":
				url = urlThings%"1"
				totalen += "\n\U0001F50C <a href='%s'>laagtarief</a> %s kWh"%(url, v)
			elif k == "meterstnd":
				url = urlThings%"4"
				totalen += "\n\U0001F525 <a href='%s'>gas</a> %s m\U000000B3"%(url, v)
			elif k == "tarief":
				momenteel += "%starief, "%("hoog" if v==2 else "laag")
			elif k == "stroom":
				url = urlThings%"5"
				momenteel += "<a href='%s'>stroomafname</a> is %s A, "%(url, v)
			elif k == "vermogen":
				url = urlThings%"3"
				momenteel += "afgenomen <a href='%s'>vermogen</a> is %s kW, "%(url, v)
		respond(string["from"]["id"], "Totalen %s\n%s"%(totalen,momenteel[:-2]))

	elif message == "pulse":
		respond(string["from"]["id"], "Moment, gegevens worden opgehaald...")
		try:
			with open("/opt/development/heartbeat.json", 'r') as f:
				datastore = json.load(f)
			bericht = ""
			now = time.time()
			for k, v in datastore.items():
				print (now, v, int((now-v)/60),k)
				bericht += "[%02d]\t%s\n"%(int((now-v)/60),k)
			respond(string["from"]["id"], bericht)
		except:
			respond(string["from"]["id"], "Error opening heartbeat.json")

	elif "3dprinter" in message:
		aanofuit = "aan" if "aan" in message else "uit" if "uit" in message else ""
		if aanofuit:
			resultaat = httpGet("http://192.168.0.125:1208?printer:%s"%aanofuit)
		else:
			resultaat = httpGet("http://192.168.0.125:1208?printer")
		console( resultaat.text )
		respond(string["from"]["id"], "Printer is %sgezet"%("aan" if int(resultaat.text) == 1 else "uit"))

	elif message[:4] == "help":	
		helptekst  = "\n<b>3dprinter</b> [aan|uit]"
		helptekst += "\n<b>externalip</b>"
		helptekst += "\n<b>ping</b>"
		helptekst += "\n<b>kattenluik</b> [foto|crop|licht|pushover]"
		helptekst += "\n<b>detectie</b> [aan|uit]"
		helptekst += "\n<b>pulse</b>"
		helptekst += "\n<b>energie</b>"
		helptekst += "\n<b>volgers</b> instaname"
		helptekst += "\n<b>weer</b> [plaatsnaam]"
		helptekst += "\n<b>lichtkrant</b> [tekst]"
		respond(string["from"]["id"], helptekst )
	
class udpinit(object):
	def __init__(self, myport = 5005):
		self.port = myport
		self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

	def broadcast(self, message = ""):
		console("Sending: %s"%message)
		self.s.sendto(bytes(message,"UTF-8"),('<broadcast>',self.port))

class telegrambot(object):
	def __init__(self):
		self.url = "https://api.telegram.org/bot112338525:AAGyQLESoyVnCAdBJZTdaRcgV5KwN3uGipU/getUpdates"
		self.interval = 2
		self.offset = 0

		self.polling()
		
	def polling(self):
		payload = 'offset=%s'%self.offset
		try:
			response = requests.post( self.url, params=payload, timeout=3)
		except Exception as e:
			self.starter()
			return
		
		if (response.status_code == requests.codes.ok):
			if response.json()["ok"]:								# lees de berichten in				
				for element in response.json()["result"]:		# voor het geval als er meerdere berichten staan te wachten
					msge = "message"
					if msge not in element:
						msge = "edited_message" 
						if msge not in element:
							self.start()
							return						# niet geinteresseerd in andere berichten

					for key in element[msge]:		# wat voor een soort bericht is het
						if	 key == "group_chat_created":
							break
						elif key == "new_chat_participant":
							break
						elif key == "new_chat_photo":
							break
						elif key == "text":
							console("%s (%s)"%(element[msge], element["update_id"] ))
							doSomething(element[msge])
							self.offset = element["update_id"] + 1
		self.starter()
		
	def starter(self):
		self.thread = threading.Timer(self.interval, self.polling)
		self.thread.start()
									
	def stop(self):
		console("Telegram bot wordt gestopt...")
		self.thread.cancel()


#	this class will handles any incoming request from the browser 
class myHandler(BaseHTTPRequestHandler):
	def log_message(self, format, *args):
		return

	def do_HEAD(self):
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()

	def respond(self, response=None):
		console("\033[12G\033[35mResponse: %s\033[K\033[F"%response)
		self.send_response(200)
		self.send_header('Content-type','text/html')
		self.end_headers()
		
		if not response is None:
			try:
				self.wfile.write( bytes(response,"utf-8")  )
			except Exception as e:
				console("\033[31m%s bij %s"%(e, response))
				pass

#	Handler for the GET requests
	def do_GET(self):
		command = self.requestline.replace("GET /","").replace("?","")
		command = command[:command.find("HTTP")].strip()
		
		console( command )
		if "getpid" == command:
			self.respond( "%s"%os.getpid() )
		elif "weer" == command:
			self.respond( weerbericht( "html" ) )

def myIP():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

response = httpGet("https://api.telegram.org/bot112338525:AAGyQLESoyVnCAdBJZTdaRcgV5KwN3uGipU/getMe")
if (response.status_code == requests.codes.ok):
	console("%s is gestart"%__file__)
	console("server: [%s]"%socket.gethostname() )
	
	result = response.json()["result"]
	console("botname: %s (%s)"%(result["username"],result["first_name"]))

#	tekst = "@%s (%s) op de %s (%s) is gestart "% (result["username"], result["first_name"], socket.gethostname(), myIP())
#	telegram( bericht = tekst )

try:
	udp = udpinit()
	rgb = udpinit(1208)

	tgbot = telegrambot()

	server = HTTPServer(('', 5005), myHandler)
	console("Actief op poort %d"%5005)
	server.serve_forever() # Wait forever for incoming http requests
	
except KeyboardInterrupt:
	print(time.strftime("%a om %H:%M:%S")+ " Shutting down...")
	server.shutdown()
	server.socket.close()
	tgbot.stop()
	
	print("Done, restarting...")
	console("%s wordt gestart"%__file__)
	subprocess.call("screen -dmS telegram python3 %s"%__file__, shell=True)