#!/usr/bin/python3.7

import json
import requests
import sys, getopt, socket
from pathlib import Path

'''
(23) Name: HAA-CFCAB1
(20) Manufacturer: RavenSystem
(30) Serial Number: 18FE34CFCAB1
(21) Model: HAA
(52) Firmware Revision: 0.7.2
(25) On: False
(11) Current Temperature: 20.9375
'''

HAA_VERSION = ""





def getIP(d):
	try:
		data = socket.gethostbyname(d)
		return data
	except Exception:
	# fail gracefully!
		pass
		return "0.0.0.0"
        
def httpGet( httpCall, wachten = 5, label=""):
	resultaat = requests.Response
	try:
		resultaat = requests.get(httpCall, timeout=wachten)
	except requests.Timeout as e:
		print("\u2514\033[31m Timeout on: %s\033[0m"%httpCall)
		resultaat.status_code = 999
	except Exception as e:
		print("\u2514\033[31m Error on: %s\033[0m"%httpCall)
		resultaat.status_code = 999
	return resultaat
	
def getstate( url, ip="0.0.0.0", name = "", pjsn=False, aleenversie=False, mac="", update=False):
	regels = {}
	
	types = {}
	types['2.23'] = "Name: %s"
	types['3.20'] = "Author: %s"
	types['4.30'] = "Device name: %s"
	types['5.21'] = "Firmware name: %s"
	types['6.52'] = "Firmware version: %s"
	types['9.11'] = "Temperature :%s\u1D52C"
	types['9.25'] = "Device %s is on: %s%s"
	types['10.3'] = "Something (10.3): %s"
	types['10.8'] = "Brightness: %s%%"
	types['10.23'] = "Something (10.23): %s"
	types['10.D3'] = "Default duration: %s seconds"
	types['11.D4'] = "Remaining duration: %s seconds"
	types['11.13'] = "Hue: %s"
	types['12.10'] = "Humidity: %s%%"
	types['12.23'] = "12.23 %s"
	types['12.2F'] = "Saturation: %s"
	types['101.37'] = "Something (101.37): %s"
	types['1001.37'] = "Something (1001.37): %s"
	types['13.23'] = "Something (13.23): %s"
	types['31.10'] = "Humidity: %s%%"
	types['32.23'] = "Something (32.23): %s"
	types['1011.F0000101-0218-2017-81BF-AF2B7C833922'] = "Update: %s"
	types['1012.F0000102-0218-2017-81BF-AF2B7C833922'] = "Setup: %s"

	print( "\n\u250C\033[33m "+url+" ("+ip+", "+name+")\033[0m")

	resultaat = httpGet( url )
	if resultaat.status_code == 200:
		if not resultaat.text: return
		if pjsn: print( resultaat.json(), "\n" )

		if pjsn or "accessories" not in resultaat.json(): print( resultaat.json(), "\n" )

		values = {}

		for regel in resultaat.json()["accessories"]:
			for service in regel["services"]:
				for characteristic in service["characteristics"]:
#					print(characteristic)
					if "value" in characteristic:
						values["%s.%s.%s"%(characteristic["aid"],characteristic["iid"],characteristic["type"])] = characteristic["value"] 
		
		for type in values: 
			if aleenversie and not type[2:] == '6.52': continue

			if type[2:] in ("101.37","3.20","5.21","4.30","1001.37", "13.23"): continue
			
			if type[2:] == '9.25':
				print(u'\u251C', types[type[2:]]%(type[0:1], "\033[%sm"%(92 if values[type] else 91), values[type]),"\033[0m")
				continue
				
			if type[2:] == '6.52' and values[type] != HAA_VERSION:
				print(u'\u251C', types[type[2:]]%values[type], "\033[36m(%s availlable)\033[0m"%HAA_VERSION)
				continue
			
			if not values[type]: continue # if value is empty don't print it
			print(u'\u251C', types[type[2:]]%("\033[93m%s\033[0m"%values[type]))	
		
		if update:
			print("\033[35mTriggering setup/update mode for %s\033[0m"%ip)
			print("\033[35m...Sending trigger\033[0m")
			data = '{"characteristics":[{"aid":1,"iid":9,"value":false},{"aid":1,"iid":9,"value":true}'
			for x in range(0,8):
				data += ',{"aid":1,"iid":9,"value":false},{"aid":1,"iid":9,"value":true}'
			data += ']}'
			requests.put('http://%s:5556/characteristic'%ip, data=data)

def updateip():
	with open('%s/readhaa.json'%Path(__file__).parent.absolute()) as json_file:
		data = json.load(json_file)
		print ("updateing ", len(data["devices"]), " devices")
		for i in range(0, len(data["devices"]) ):
			ip = getIP("%s.local"%data['devices'][i]['name'])
			data['devices'][i]['ip'] = ip
			print(ip, data['devices'][i]['name'], data['devices'][i]['description'])
			
	with open('%s/readhaa.json'%Path(__file__).parent.absolute(), 'w') as outfile:
		json.dump(data, outfile, indent=4, sort_keys=True)
	
# --------- ~~~ main ~~~ ---------

arguments = len(sys.argv) - 1
if len(sys.argv) - 1 > 0:
	updt = False
	pjsn = False
	vers = False
	alle = False
	
	try:
		opts, args = getopt.getopt(sys.argv[1:],"hrjai:uv",["ip=","update","all","json","version","refresh"])
		
	except getopt.GetoptError:
		print('%s [-h | -i <ipnmbr> [-u | -j]]'%__file__)
		sys.exit(2)
	
	for opt, arg in opts:
#		print(opt,arg)
		if opt == '-h':
			print('%s [-h | -a | -i <ipnmbr> [-u]]'%__file__)
			sys.exit()
			
		elif opt in ('-a', "--all"):
			alle = True
			
		elif opt in ("-i", "--ip"):
			ipadres = arg
			
		elif opt in ("-u", "--update"):
			updt = True
			
		elif opt in ("-j", "--json"):
			pjsn = True
			
		elif opt in ("-v", "--version"):
			vers = True
			
		elif opt in ("-r", "--refresh"):
			updateip()
			sys.exit(0)
			
	# get latest version number
	r = httpGet(" https://github.com/RavenSystem/haa/releases/latest")
	HAA_VERSION = r.url[(r.url.rfind("/")-len(r.url))+1:].replace("HAA_","")
	print("Current HAA version: ", HAA_VERSION)
		
	with open('%s/readhaa.json'%Path(__file__).parent.absolute()) as json_file:
		data = json.load(json_file)
		if "devices" in data:			
			for device in data['devices']:
				ip = device['ip']
				device['ip'] = ip
				if not alle: 
					len = 3 if int(ipadres) > 100 else 2 if int(ipadres) > 10 else 1
					if int(ipadres) == int(ip[-len:].replace(".","")):
						getstate("http://%s.local:5556"%device['name'], ip=ip, update=updt, aleenversie=vers, name=device['description'], mac=device['name'], pjsn=pjsn)
						if "json" in device: print("\u2514\033[36m "+device["json"]+"\033[0m")
						break
				else:
					getstate("http://%s.local:5556"%device['name'], ip=ip, update=updt, aleenversie=vers, name=device['description'], mac=device['name'], pjsn=pjsn)
					if "json" in device: print("\u2514\033[36m "+device["json"]+"\033[0m")
					
print("\nUDP logger: nc -kulnw0 45678")