import sys
import serial
import requests
import datetime
import time
import json
import threading
import subprocess
import socket

from growatt import hash_password, Timespan, GrowattApi

##############################################################################
#Main program
##############################################################################

#Set COM port config
ser = serial.Serial()
ser.baudrate = 115200
ser.bytesize=serial.EIGHTBITS
ser.parity=serial.PARITY_NONE
ser.stopbits=serial.STOPBITS_ONE
ser.xonxoff=0
ser.rtscts=0
ser.timeout=20
ser.port="/dev/ttyUSB0"


thingspeakapi = '0SSAA5SGLQ0IZQRQ'
#thingspeakapi = 'OBKXBDRQNQQWTVVI'
lasttime = time.time()
gasm3uur = 0
teller	= 0
waarden	= {"laag":0,"hoog":0,"tarief":0,"vermogen":0,"stroom":0,"meterstnd":0, "tydmeting":0, "geleverd":0,"opgewekt":0}
vorige	= {"meterstnd":0, "tydmeting":0, "geleverd":0, "recvlaag": 0, "recvhoog": 0, "dlvrlaag": 0, "dlvrhoog": 0}

stroomtotaal = 0
stroommetngn = 0
	
vermogentotaal = 0
vermogenmetngn = 0

opgewekttotaal = 0
opgewektmetngn = 0


class Solar( object ):
	def __init__( self, user = "growatt@smitssmit.nl", password ="xZfw9Pu*6rq4V@d."):		
		self.user = user
		self.pswd = password
		self.cont = True
		self.opgewekt = 0

		threading.Thread(target=self.lezen).start()
		
	def lezen( self ):	
		while self.cont:
			with GrowattApi() as api:
				api.login(self.user, self.pswd)
				while self.cont:
					try:
						plant_info = api.plant_list()
					
						currentPower = plant_info["data"][0]['currentPower']
						multiplier = 1000 if "k" in currentPower else 1
				
						trtab = str.maketrans("kW","  ")
						currentPower = currentPower.translate(trtab).replace(' ','')
				
						opgewekt = float(currentPower)*multiplier
						console.update(38, "Opwekking op het moment: %s Watt"%opgewekt)
									
					except: 
						pass
						break # bij fout, opnieuw inloggen
						
					time.sleep(15)
				
	def stop( self ):
		self.cont = False

#Open COM port
try: ser.open()
except:
	print ("Fout bij het openen van %s."  % ser.port)
	ser.port="/dev/ttyUSB1"
	try: ser.open()
	except:
		sys.exit ("Fout bij het openen van %s."  % ser.port)
		
def vertaal(p1):
	p1 = p1.strip()
	if not p1: return ""
	elif   p1.startswith("1-3:0.2.8"):
		return(p1.ljust(50)+" Version information for P1 output")
	elif p1.startswith("0-0:1.0.0"):
		return(p1.ljust(50)+" Date-time stamp of the P1 message")
	elif p1.startswith("0-0:96.1.1"):
		return(p1.ljust(50)+" Equipment identifier")
	elif p1.startswith("1-0:1.8.1"):
		return(p1.ljust(50)+" Meter Reading electricity delivered to client (Tariff 1) in 0,001 kWh")
	elif p1.startswith("1-0:1.8.2"):
		return(p1.ljust(50)+" Meter Reading electricity delivered to client (Tariff 2) in 0,001 kWh")
	elif p1.startswith("1-0:2.8.1"):
		return(p1.ljust(50)+" Meter Reading electricity delivered by client (Tariff 1) in 0,001 kWh")
	elif p1.startswith("1-0:2.8.2"):
		return(p1.ljust(50)+" Meter Reading electricity delivered by client (Tariff 2) in 0,001 kWh")
	elif p1.startswith("0-0:96.14.0"):
		return(p1.ljust(50)+" Tariff indicator electricity")
	elif p1.startswith("1-0:1.7.0"):
		return(p1.ljust(50)+" Actual electricity power delivered (+P) in 1 Watt resolution")
	elif p1.startswith("1-0:2.7.0"):
		return(p1.ljust(50)+" Actual electricity power received (-P) in 1 Watt resolution")
	elif p1.startswith("0-0:96.7.21"):
		return(p1.ljust(50)+" Number of power failures in any phase")
	elif p1.startswith("0-0:96.7.9"):
		return(p1.ljust(50)+" Number of long power failures in any phase")
	elif p1.startswith("1-0:99.97.0"):
		return(p1.ljust(50)+" Power Failure Event Log (long power failures)")
	elif p1.startswith("1-0:32.32.0"):
		return(p1.ljust(50)+" Number of voltage sags in phase L1")
	elif p1.startswith("1-0:32.36.0"):
		return(p1.ljust(50)+" Number of voltage swells in phase L1")
	elif p1.startswith("0-0:96.13.1"):
		return(p1.ljust(50)+" Text message max 1024 characters.")
	elif p1.startswith("0-0:96.13.0"):
		return(p1.ljust(50)+" ")
	elif p1.startswith("1-0:31.7.0"):
		return(p1.ljust(50)+" Instantaneous current L1 in A resolution.")
	elif p1.startswith("1-0:21.7.0"):
		return(p1.ljust(50)+" Instantaneous active power L1 (+P) in W resolution")
	elif p1.startswith("1-0:22.7.0"):
		return(p1.ljust(50)+" Instantaneous active power L1 (-P) in W resolution")
	elif p1.startswith("0-1:24.1.0"):
		return(p1.ljust(50)+" andere apparaten op de M-Bus")
	elif p1.startswith("0-1:96.1.0"):
		return(p1.ljust(50)+" identificatie van de gasmeter")
	elif p1.startswith("0-1:24.2.1"):
		return(p1.ljust(50)+" Tijd van gasmeting en meterstand")
	elif p1.startswith("!"):
		return(p1.ljust(50)+" Einde bericht")
	elif p1.startswith("/KFM5KAIFA-METER"):
		return(p1.ljust(50))
	else:
		return(p1.strip()+" \t onbekende code %s")
		
class udpinit(object):
	def __init__(self, myport = 5005):
		self.port = myport
		self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

	def broadcast(self, message = ""):
		console.update(11,"Sending: %s"%message)
		self.s.sendto(bytes(message,"UTF-8"),('<broadcast>',self.port))
		
class Console( object ):
	def __init__( self ):
		self.regels = []
		for i in range(1, 41):
			self.regels.append("")
			
	def update(self, nummer, tekst):
		self.regels[nummer]  = "[%s] "%time.strftime("%H:%M:%S") if nummer > 3 else ""
		self.regels[nummer] += tekst
		return self
		
	def direct(self, i, tekst):
		self.regels[i]  = "[%s] "%time.strftime("%H:%M:%S") if i < 15 else ""
		self.regels[i] += tekst
		print("\033[%s;1H\033[2K%02d|%s"%(i, i, self.regels[i]))	
		return self
		
	def display( self ):
		print("\033[;H\033[2J")
		for i in range(1, 40):
			print("\033[%s;1H\033[2K%02d|%s"%(i,i, self.regels[i]))
		return self
			
console = Console()

class rekenen( object ):
	def __init__( self):
		self.vorige = 0
		self.laatst = 0

	def verschil( self, waarde=0 ):
		self.laatst = (waarde - self.vorige) if self.vorige else 0
		self.vorige = waarde
		return self.laatst

def telegram( chat_id="12463680", message = None, image = None ):
	#	johannes_smits	=  "12463680"
	#	alarmsysteem	= "-24143102"
	if not message is None:
		url = "https://api.telegram.org/bot112338525:AAGyQLESoyVnCAdBJZTdaRcgV5KwN3uGipU/sendMessage"
		payload = {"chat_id":chat_id, "text":message, "parse_mode":"HTML"}
		r = requests.get(url, params=payload)	
		return (r.json()["ok"])
		
	elif not image is None:
		url	= "https://api.telegram.org/bot112338525:AAGyQLESoyVnCAdBJZTdaRcgV5KwN3uGipU/sendPhoto"
		data	= {'chat_id': chat_id}
		files	= {'photo': (image, open(image, "rb"))}
		r = requests.post(url, data=data, files=files)
		return (r.json()["ok"])
		
def serialReopen():
	ser.close()
	ser.port = "/dev/ttyUSB0"
	try: ser.open()
	except:
		ser.port = "/dev/ttyUSB1"
		try: ser.open()
		except:
			sys.exit ("Fout bij het reopenening van %s."  % ser.port)
	console.update(11, "Serial %s reopenend"%ser.port )

def pulse():
	filename = "/opt/development/heartbeat.json"
	try:
		with open(filename, 'r') as f: datastore = json.load(f)
	except:
		datastore = {}
		pass
		
	datastore["energie"] = time.time() # wordt automatisch toegevoegd indien niet aanwezig
	console.update(7, "Pulse({'energie':%s})"%datastore["energie"])

	with open(filename, 'w') as f:
		json.dump(datastore, f)

class Thingspeak( object ):
	def __init__( self ):
		self.interval = 60
		self.thread = None
		self.meterstand = 0
		self.tijdmeting = 0
		self.field1 = self.field2 = self.field3 = self.field4 = self.field5 = self.field6 = self.field8 = 0
		self.ticks = time.time()

		self.schrijven()
				
	def schrijven( self ):
		global stroomtotaal, vermogentotaal, stroommetngn, vermogenmetngn
		
		pulse()
		
		gasm3uur = (waarden["meterstnd"]-vorige["meterstnd"]) if vorige["tydmeting"] != 0 else 0
		console.update(5, "Gas gebruik %s"%gasm3uur)

		vorige["meterstnd"] = waarden["meterstnd"]
		vorige["tydmeting"] = waarden["tydmeting"]
			
		stroom = stroomtotaal/(stroommetngn if stroommetngn else 1)
		vermogen = vermogentotaal/(vermogenmetngn if vermogenmetngn else 1)
		opgewekt = opgewekttotaal/(opgewektmetngn if opgewektmetngn else 1)
		
		vermogen -= opgewekt
	
		console.update(8, "Thingspeak update gestart")
		
		update  = ""
		update += "&field1=%0.3f"%waarden["laag"] if waarden["laag"]-self.field1 > 0.1 else ""
		update += "&field2=%0.3f"%waarden["hoog"] if waarden["hoog"]-self.field2 > 0.1 else ""
		update += "&field8=%0.3f"%waarden["geleverd"] if waarden["geleverd"]-self.field8 > 0.1 else ""
		update += "&field3=%0.3f"%vermogen if vermogen != self.field3 else ""
		update += "&field4=%0.3f"%waarden["meterstnd"] if waarden["meterstnd"]-self.field4 > 0.1 else ""
		update += "&field5=%0.3f"%stroom if stroom - self.field5 > 0.1 else ""
		update += "&field6=%0.3f"%gasm3uur if gasm3uur > self.field6 else ""

		self.field1 = waarden["laag"]
		self.field2 = waarden["hoog"]
		self.field3 = vermogen
		self.field4 = waarden["meterstnd"]
		self.field5 = stroom
		self.field6 = gasm3uur
		self.field8 = waarden["geleverd"]

		stroomtotaal = 0
		stroommetngn = 0
			
		vermogentotaal = 0
		vermogenmetngn = 0

		console.update(9, update)
		self.interval = 60
		if update:
			self.ticks = time.time()

			try:
				r = requests.get("https://api.thingspeak.com/update?api_key=%s%s" % (thingspeakapi, update), timeout=1)
				self.interval = 900 
				console.update(8, "Update ThingSpeak is gelukt, volgende update over %s seconden"%self.interval)
			except requests.exceptions.Timeout:
				console.update(8, "Update ThingSpeak mislukt. Volgende poging over %s seconden"%self.interval)
				pass
			except:
				console.update(8, "Update ThingSpeak mislukt, vage shit. Volgende poging over %s seconden"%self.interval)
				pass
		else:
			console.update(8, "Niets om ThingSpeak mee te updaten. Volgende update over %s seconden"%self.interval)
			if (time.time() - self.ticks) > self.interval*2:  
				sys.exit("Lijkt niets meer binnen te komen, herstart")

		console.display()
		
		self.thread = threading.Timer(self.interval, self.schrijven)
		self.thread.start()

	def klaar(self):
		console.direct(19, "Stoppen van Thingspeak timer")
		self.thread.cancel()

kWhHoog = rekenen()
kWhLaag = rekenen()

fouten = 0

console.update(1, "Uitlezen energiemeter (%s)"%ser.port)
console.update(2, "\033[3mControl-C om te stoppen\033[0m").display()

udp = udpinit( 2323 )

try:
	things = Thingspeak()
	watts = Solar()

	ticks = time.time()
	while True:
		p1_line = ' '
		regel = 10
		while (p1_line[0] != "!"):
			try: 
				p1_raw = ser.readline().decode("utf-8")
			except KeyboardInterrupt:
				watts.stop()
				sys.exit('Afsluiten...')
			except:
				console.update(7,"Fout bij het lezen van seriele poort")
				fouten += 1
				if fouten < 10: continue
				ser.close()
				sys.exit("Te veel leesfouten %s."  % ser.port)
				
			fouten	= 0
			p1_str	= str(p1_raw)
			p1_line	= p1_str.strip()
			
			waarden["geleverd"] = 0
			
			if not p1_line : p1_line = " " 

			if   (p1_line.startswith("1-0:1.8.1")):
				waarden["laag"] = float(p1_line.split("(")[1].split("*")[0])
				kWhLaag.verschil(waarden["laag"])
				
			elif (p1_line.startswith("1-0:1.8.2")):
				try:
					waarden["hoog"] = float(p1_line.split("(")[1].split("*")[0])
					kWhHoog.verschil(waarden["hoog"])
				except: pass
				
			elif (p1_line.startswith("1-0:2.8.1")):
				waarden["geleverd"] += float(p1_line.split("(")[1].split("*")[0])

			elif (p1_line.startswith("1-0:2.8.2")):
				waarden["geleverd"] += float(p1_line.split("(")[1].split("*")[0])
				
			elif (p1_line.startswith("0-0:96.14.0")):
				waarden["tarief"] = int(p1_line.split("(")[1].split(")")[0])
				
			elif (p1_line.find("1-0:1.7.0") != -1):
				waarden["vermogen"] = int(p1_line.split("(")[1].split("*")[0].replace(".",""))
				vermogentotaal += waarden["vermogen"]
				vermogenmetngn += 1
				
			elif (p1_line.find("1-0:2.7.0") != -1):
				waarden["opgewekt"] = int(p1_line.split("(")[1].split("*")[0].replace(".",""))
				opgewekttotaal += waarden["opgewekt"]
				opgewektmetngn += 1
				
			elif (p1_line.startswith("1-0:31.7.0")):
				waarden["stroom"] = int(p1_line.split("(")[1].split("*")[0].replace(".",""))
				stroomtotaal += waarden["stroom"] 
				stroommetngn += 1
				
			elif (p1_line.startswith("0-1:24.2.1")):
				waarden["tydmeting"] = int(p1_line.replace("0-1:24.2.1", "").split(")")[0][1:12])
				waarden["meterstnd"] = float(p1_line.split("(")[2].split("*")[0])
			
			regel = 10 if regel > 49 else regel+1
			console.update(regel, "\033[1;32m%s\033[0m"%vertaal(p1_line))
			
		console.update(4, "\033[1;33m%s\033[0m"%json.dumps(waarden) )
		console.update(6, "Gebruik: H%0.3f, L%0.3f (%s)"%(kWhHoog.laatst, kWhLaag.laatst, waarden["vermogen"]))
		
		teller += 1
		if teller > 10: # eens in de 10 lezingen de html schrijven
			teller = 0
			with open("/tmp/energie.json", 'w') as f: json.dump(waarden, f)
			with open("/opt/development/common/energie.json", 'w') as f: json.dump(waarden, f)
				
			udp.broadcast("{\"vermogen\":%s}"%waarden["vermogen"])
				
#			console.update(5, "Energie.html geschreven\n")		
		console.display()

except SystemExit as e:
	telegram( message = "Energiemeter - %s"%e )
	
	console.direct(11, "Closing %s"%ser.port)
	ser.close()
	console.direct(17,"Stopping thingspeak update timer")
	things.klaar()	
	console.direct(18,"Starting %s"%__file__)
	#subprocess.call("screen -dmS energie python3 %s"%__file__, shell=True)