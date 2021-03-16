#!/usr/bin/python3.7

import os
import time
import requests
import subprocess
import glob
import threading
import random
import glob, os
import imageio
import json
import traceback

from datetime import datetime
from smits import Messaging
from instabot import Bot, utils
#from InstagramAPI import InstagramAPI
    
def telegram( chat_id="-12086796", message = None, image = None , video=None, animation=None, caption=None):
	chat_id = "12463680"
	
	if not message is None:
		url = "https://api.telegram.org/bot112338525:AAGyQLESoyVnCAdBJZTdaRcgV5KwN3uGipU/sendMessage"
		payload = {"chat_id":chat_id, "text":message, "parse_mode":"HTML"}
		r = requests.get(url, params=payload)	
		return (r.json()["ok"])
		
	if not image is None:
		print("\033[31msending %s\033[0m"%image)
		url	= "https://api.telegram.org/bot112338525:AAGyQLESoyVnCAdBJZTdaRcgV5KwN3uGipU/sendPhoto"
		data= {'chat_id': chat_id, 'parse_mode':"HTML"}
		if not caption is None: data['caption'] = caption
		files	= {'photo': (image, open(image, "rb"))}
		r = requests.post(url , data=data, files=files)
		return (r.json()["ok"])
		
	if not animation is None:
		print("\033[31msending %s\033[0m"%animation)
		url	= "https://api.telegram.org/bot112338525:AAGyQLESoyVnCAdBJZTdaRcgV5KwN3uGipU/sendAnimation"
		data= {'chat_id': chat_id, 'parse_mode':"HTML"}
		if not caption is None: data['caption'] = caption
		files	= {'animation': (animation, open(animation, "rb"))}
		r = requests.post(url , data=data, files=files)
		return (r.json()["ok"])
		
	if not video is None:
		print("\033[96msending %s\033[0m"%video)
		url	= "https://api.telegram.org/bot112338525:AAGyQLESoyVnCAdBJZTdaRcgV5KwN3uGipU/sendVideo"
		data= {'chat_id': chat_id, 'parse_mode':"HTML"}
		if not caption is None: data['caption'] = caption
		files	= {'video': (video, open(video, "rb"))}
		r = requests.post(url , data=data, files=files)
		return (r.json()["ok"])


def httpGet( httpCall, wachten = 4, label="", pushover=True):
	resultaat = requests.Response
	try: 
		resultaat = requests.get(httpCall, timeout=wachten)
	except requests.Timeout as e:
		msg.console("%s\033[31m%s url=%s\ntimeout=%s"%(label,e,httpCall,wachten))
		msg.pushover("%s, timeout bij url %s"%(label,httpCall))
		resultaat.status_code = 999
		pass
	except Exception as e:
		msg.console("%s\033[31mFout url=%s\nxception=%s"%(label,httpCall,e))
		msg.pushover("%s, fout bij url %s"%(label,httpCall))
		resultaat.status_code = 999
		pass
	return resultaat
		
def followed( bot, user, previous ):
	try:
		user_id = bot.get_user_id_from_username(user)
		myFollowers = int( bot.get_user_info(user_id, False)["follower_count"] )
		bot.logger.info("\033[0;93mAantal followers van %s is %s, vorige %s\033[0m"%(user, myFollowers, previous))
	except:
		pass
		return previous
	
	logmsg = ""
	if previous != myFollowers:
		if previous:
			bot.logger.info("\033[0;33mAantal followers is veranderd met %s\033[0m"%(myFollowers-previous))
			opneer = "-" if myFollowers < previous else "+"
			logmsg = "%s %s%s %s"%(user, opneer, abs(myFollowers-previous), myFollowers)
			logmsg = logmsg.replace("thekittycat","")
			logmsg = logmsg.replace(".","")
			bot.logger.info(logmsg)
			lichtkrant(logmsg)
	return myFollowers, logmsg


def lichtkrant(bericht):
	bericht = bericht.replace("+","%2B").strip()
	bericht = bericht.replace(" ","+").strip()
	httpGet("http://192.168.0.242/?tekst=%s"%bericht)
	httpGet("http://192.168.0.241/?tekst=%s"%bericht)
	threading.Timer(30, httpGet, ["http://192.168.0.242/?tekst="]).start()
	threading.Timer(30, httpGet, ["http://192.168.0.241/?tekst="]).start()

class getmedias( object ):
	def __init__( self ):
		self.account = {"wijzeggen":"pidce7-vanbyr-qIpcip"}
		self.account = {"johsm":"/rgrqsLdqNjf4XB"}
		self.bot = Bot()
		self.bot.logger.info("Starting Instelegram bot")
		self.accounts = {}
		self.stories = []
		
		for name in self.account: self.bot.login(username=name, password=self.account[name])

	def getStory(self, user):
		user_id = self.bot.get_user_id_from_username(user)		
		self.bot.api.get_user_stories(user_id)
		if "reel" in self.bot.api.last_json:
			if self.bot.api.last_json["reel"] == None:
				self.bot.logger.info("\033[0;96m{} has no story\033[0m".format(user))
				return
			
		if int(self.bot.api.last_json["reel"]["media_count"]) > 0:
			for item in self.bot.api.last_json["reel"]["items"]:
				caption = datetime.fromtimestamp(item["taken_at"]).strftime("%A at %-H:%M")
				caption = "<a href=\"instagram.com/{}/\">{}</a> | {}".format(user, user, caption) 
									
#				with open("story.json", "w+") as write_file: json.dump(item, write_file)
				if int(item["media_type"]) == 1:  # photo
					story_url = item["image_versions2"]["candidates"][0]["url"]
											
					filename = story_url.split("/")[-1].split(".")[0] + ".jpg"		
					if filename in self.stories: # al verstuurd?
						self.bot.logger.info("\033[0;96m{}'s story allready sent to you\033[0m".format(user))
						continue
						
					self.bot.api.download_story(filename, story_url, user)

					self.stories.append(filename)
					if len(self.stories) > 20:
						self.stories.pop(0)

					filename = "stories/{}/{}".format(user, filename)
					if telegram(image=filename, caption=caption):
						os.remove( filename )
					
				elif int(item["media_type"]) == 2:  # video
					story_url = item["video_versions"][0]["url"]

					filename = story_url.split("/")[-1].split(".")[0] + ".mp4"
					if filename in self.stories: #al verstuurd?
						self.bot.logger.info("\033[0;96m{}'s story allready sent\033[0m".format(user))
						continue
					
					self.bot.api.download_story(filename, story_url, user)

					self.stories.append(filename)
					if len(self.stories) > 20:
						self.stories.pop(0)
							
					filename = "stories/{}/{}".format(user, filename)
					if telegram(video=filename, caption=caption):
						os.remove( filename )
				else:
					self.bot.logger.info("\033[0;91mUnexpected media format for {}'s story\033[0m".format(user))

	def getPosts(self, user, send, like):
		if not user in self.accounts: self.accounts[user] = []
		try:
			medialist = self.bot.get_user_medias(user, False)
			self.bot.logger.info("{} - {} posts".format(user, len(medialist)))
			
			for mediaId in medialist:
				if not mediaId in self.accounts[user]:			
					url = self.bot.get_link_from_media_id( int(mediaId.split('_')[0]) )

					media_info	= self.bot.get_media_info(mediaId)[0]
					with open("media_info_{}.json".format(user), "w+") as write_file: json.dump(media_info, write_file)
					
					if media_info["caption"] == None: continue
					
					timestamp	= media_info["caption"]['created_at_utc']
					mediatype	= media_info['media_type']
					caption		= media_info["caption"]["text"]	
					likes		= media_info['like_count']
					uren		= int(((time.time()+time.timezone) - timestamp)/3600)
					elapsed 	= "{} dagen".format(int(uren/24)) if uren>24 else "{} uren".format(uren)
	
					if uren < 48:						
						caption = "<a href=\"{}\">{}</a> | {} likes | {}\n\n{}".format(url, user, likes, elapsed, caption) 				
						if media_info['media_type'] == 2: 
							file = self.bot.download_video(mediaId)
							for file in glob.glob("videos/0_{}_{}.*".format(user,mediaId)):
								if telegram(video=file, caption=caption):
									os.remove( file )
		
						elif media_info['media_type'] == 8: # carousel
							for file in glob.glob("photos/*.*"): os.remove( file )
						
							self.bot.logger.info("\033[0;96m{}\033[0m".format(user, media_info['carousel_media_count']))
							frames = int( media_info['carousel_media_count'] )
							
							for photo in media_info['carousel_media']:
								print("Downloading {}...".format(photo['pk']))	
								self.bot.download_photo(photo['pk'])
								
							images = []
							for file in glob.glob("photos/{}_*.jpg".format(user)):
								images.append(imageio.imread(file))
								
							file = 'photos/{}.gif'.format(user)
							imageio.mimsave('photos/{}.gif'.format(user), images, duration=2)
							
							if telegram(animation='photos/{}.gif'.format(user), caption=caption):
								if telegram(video='photos/{}.gif'.format(user), caption=caption):
									os.remove( 'photos/{}.gif'.format(user) )
						else:
							self.bot.download_photo(mediaId)
							for file in glob.glob("photos/{}_{}.*".format(user,mediaId)):
								if telegram(image=file, caption=caption):
									os.remove( file )
					if like:
						if self.bot.blocked_actions["likes"]:
							self.bot.logger.warning("\033[Your `LIKE` action is blocked, skipping like\033[0m")
						else:
							_r = self.bot.api.like(mediaId)
							if _r == "feedback_required":
								self.bot.logger.error("`Like` action has been BLOCKED...!!!")
								self.bot.blocked_actions["likes"] = True
								continue
	
					self.accounts[user].append(mediaId)
					if len(self.accounts[user]) > 20:
						self.accounts[user].pop(0)

		except Exception as e:
			self.bot.logger.info( e )
			traceback.print_exc()
			pass
			
def main():
	accounts = {"leannesmits":0, "christie_smit":0, "valerievermaire":0,"bvermaire":0,"connylieftink":0, "jacksonthekittycat":0, "nacho.thekittycat":0, "kyon_thecocker":0, "fiiiiinley":0,"allodragon":0,"jackalopelegs":0,"metzsjors":0}
	#accounts = {"leannesmits":0}
	followers = {"jacksonthekittycat", "nacho.thekittycat"}
	integram = getmedias()
	integram.bot.logger.info("Instelegram bot is gestart...")

	sendTgrm = True # eerste run hoeven niet alle oude post's gestuurd te worden
	likeThem = False
	
	try:
		os.chdir("/tmp")
		while True:
			lichtkrantmsg = ""
			
			for name in accounts:
				try:
					integram.getStory( name )	
					integram.getPosts( name, sendTgrm, likeThem)
				
					if name in followers: 
						accounts[name], logmsg = followed(integram.bot, name, accounts[name])
						lichtkrantmsg += logmsg
				except Exception as e:
					integram.bot.logger.info( e )
			
			if lichtkrantmsg: lichtkrant( lichtkrantmsg ) 
			sendTgrm = False
			likeThem = True	
			time.sleep( 600 )

	except KeyboardInterrupt:
		print("\r\033[2K\033[35mctrl-c, afsluiten...\033[0m")
		pass

main()	