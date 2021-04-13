import es, os, re, playerlib, gamethread, effectlib, urllib, time
from time import strftime #strftime("%Y-%m-%d %H:%M:%S")

#
# ztricks
# 20090227 - initial
# 20090228 - tricks and detection working
# 20090302 - spawning clears list
# 20090303 - added player death to reset
# 20090307 - changed drawbox to drawline
#          - recalculated xyz on load
#          - reduced time rate
#          - fixed load and unload
#          - fixed unloading issues
#          - added !info <trick>
#          - changed compareList
#          - player death now clears the players path list
#

rate=0.01								# timer rate
max_idle=10								# seconds
config_file='cstrike/addons/eventscripts/ztricks/zconfig.txt'		# configuration file

global players
players={}
triggers=[]
tricks=[]

def player_spawn(ev):
	global players
	userid=ev['userid']
	check_keys(userid)
	players[userid]['triggerlist'].append(-10)

def check_keys(userid):
	global players
	if not players.has_key(userid):
		players[userid]={}
	if not players[userid].has_key('x'):
		players[userid]['x']=0
		players[userid]['y']=0
		players[userid]['z']=0
		players[userid]['idletime']=0
		players[userid]['triggerlist']=[-1]
		players[userid]['tricklist']=[]
		players[userid]['points']=0
		players[userid]['quiet']=1

def timer():
	gamethread.delayedname(rate, 'timer1', timer)
	playerlist = playerlib.getUseridList("#alive")
	for userid in playerlist:
		check_keys(userid)

		# get this players xyz
		myPlayer = playerlib.getPlayer(userid)
		x = myPlayer.attributes['x']
		y = myPlayer.attributes['y']
		z = myPlayer.attributes['z']

		# compare to idle check
		if x != players[userid]['x'] or y != players[userid]['y'] or z != players[userid]['z']:
			players[userid]['idletime']=time.time()
		else:
			it=time.time() - players[userid]['idletime']
			es.tell(userid, "#lightgreen", "you have been idle for %s seconds"%it)
			if it > max_idle:
				es.msg("#lightgreen", "max idle was hit for player %s (%s)" % (userid, it))
				es.server.cmd("kickid %s" % userid)

		# compare to triggers
		trig=getTrigger(x, y, z)
		if trig >= 0:
			if players[userid]['triggerlist'][-1] != trig:
				if players[userid]['quiet'] == 0: es.tell(userid, "#multi", "#lightgreenyou just triggered #green%s#lightgreen !!" % getTriggerName(trig))
				players[userid]['triggerlist'].append(trig)

				best_score=-1
				best_index=-1
				# score is based on the length of the trick, more=better
				# so find the longest trick that has been completed and go with that.
				for trk in tricks:
					[pathlist, path, points, name]=trk
					if len(pathlist) > best_score and compareList(pathlist, players[userid]['triggerlist']) > 0:
						# new best!
						best_score=len(pathlist)
						best_index=tricks.index(trk)

				if best_score > -1:
					[pathlist, path, points, name]=tricks[best_index]

					# award them some points
					players[userid]['points'] = players[userid]['points'] + int(points)

					# add this trick to the list
					players[userid]['tricklist'].append(best_index)

					# display the message
					es.msg("#multi", "#lightgreen%s just completed #green%s#lightgreen !!" % (getPlayerName(userid), name))
					#es.msg("#multi", "#lightgreen%s just completed #green%s#lightgreen !! worth #green%s#lightgreen points !!" % (getPlayerName(userid), name, points))
					#es.tell(userid, "#multi", "#lightgreenyou now have a total of #green%s#lightgreen points" % players[userid]['points'])


def compareList(pathlist, userlist):
	if len(pathlist) > len(userlist): return -2
	delta=int("-%s" % len(pathlist))

	newlist=[]
	for point in userlist:
		if point in pathlist:
			# this is required!
			newlist.append(point)
		else if point >= 1000:
			# this is optional and not in the list (skip it)
			print "skipping point"
		else:
			# leave this in the list to compare
			newlist.append(point)

	if newlist[delta:] == pathlist:
		return 1
	else:
		return -2

def getPlayerName(userid):
	thePlayer = playerlib.getPlayer(userid)
	return thePlayer.attributes['name']

def loadConfig():
	global triggers
	global tricks
	es.msg("loading configuration")
	print "current directory: %s" % os.getcwd()
	f=open(config_file, 'r')
	if not f:
		es.msg("unable to load configuration")
		return
	triggers=[]
	tricks=[]
	lines=f.readlines()
	for line in lines:
		m=re.match("^(\w+)", line)
		if not m: continue
		[type]=m.groups()

		# tricks are [pathlist, path, points, name]
		if type == "trick":
			m=re.match("trick\t+(.*?)\t+(\d+)\t+(.*)", line)
			if not m: continue
			[path, points, name]=m.groups()
			print "found trick [%s] [%s] [%s]" % (path, points, name)
			#es.msg("- found trick: %s" % name)
			pathlist=path.split(',')
			tricks.append([pathlist, path, points, name])

		# triggers are [id, name, x1, y1, z1, x2, y2, z2]
		if type == "trigger":
			m=re.match("trigger\t+(\d+)\t+(.*?)\t+(.*?)\t+(.*)", line)
			if not m: continue
			[id, point1, point2, name]=m.groups()
			[x1, y1, z1]=re.split(',', point1)
			[x2, y2, z2]=re.split(',', point2)

			[x1, x2]=autoswitch(x1, x2)
			[y1, y2]=autoswitch(y1, y2)
			[z1, z2]=autoswitch(z1, z2)

			triggers.append([id, name, x1, y1, z1, x2, y2, z2])
	#print "triggers"
	#for box in triggers:
	#	#print "- %s" % box
	#
	#print "\ntricks";
	for box in tricks:
		[pathlist, path, points, name]=box
		#print "- %s: points->[%s] path->[%s] pathlist:%s" % (name, points, path, pathlist)

	#es.msg("done.")
	return "found %s triggers, %s tricks" % (len(triggers), len(tricks))

def getTriggerName(i):
	for box in triggers:
		if box[0] == i:
			return box[1]
	return "error"

def getTrigger(px, py, pz):
	# check each defined trigger to see if xyz matches and return the triggers id
	for box in triggers:
		[id, name, x1, y1, z1, x2, y2, z2]=box
		if (px > int(x1) and px < int(x2)) or (px > int(x2) and px < int(x1)):
			if (py > int(y1) and py < int(y2)) or (py > int(y2) and py < int(y1)):
				if (pz > int(z1) and pz < int(z2)) or (pz > int(z2) and pz < int(z1)):
					return id
	return -1

def load():
	loadConfig()
	es.addons.registerSayFilter(sayFilter)
	gamethread.delayedname(rate, 'timer1', timer)
	es.msg("ztricks loaded")

def unload():
	r=gamethread.cancelDelayed('timer1')
	es.msg("disabling timer: %s" % r)
	es.addons.unregisterSayFilter(sayFilter)
	es.msg("ztricks unloaded")

def sayFilter(userid, text, teamOnly):
	global players
	text_noquote = text.strip('"')
	words = text_noquote.split(" ")
	cmd = words[0].lower()

	if cmd in ['rank', '!rank', '!score']:
		es.msg("#lightgreen", "%s has %s points!" % (getPlayerName(userid), players[userid]['points']))
		return (0, "", 0)

	if cmd == "!info":
		if len(words) == 1:
			es.tell(userid, "#lightgreen", "usage: !info awp2awp")
			return (0, "", 0)
		req=words[1].lower()
		# find the trick with that name
		for box in tricks:
			[pathlist, path, points, name]=box
			if name == req:
				# create a string for each path
				namelist=[]
				for p in pathlist:
					namelist.append(getTriggerName(p))
				es.tell(userid, "#lightgreen", "[ztricks] trick %s is %s" % (req, " -> ".join(namelist)) )
				return (0, "", 0)
		es.tell(userid, "#lightgreen", "[ztricks] unknown trick %s" % req)
		return (0, "", 0)

	#if cmd == "!zdownload":
	#	es.msg("downloading new configuration file..")
	#
	#	#>>> import urllib
	#	#>>> opener = urllib.FancyURLopener({})
	#	#>>> f = opener.open("http://www.python.org/")
	#	#>>> f.read()
	#
	#	opener = urllib.FancyURLopener({})
	#	f = opener.open("http://es.darksidebio.com/es/zconfig.txt")
	#	if not f:
	#		es.msg("unable to open")
	#		return (0, "", 0)
	#	data=f.read()
	#
	#	#mysock = urllib.urlopen("http://es.darksidebio.com/es/zconfig.txt")
	#	#data = mysock.read()
	#
	#	oFile = open(config_file,'wb')
	#	oFile.write(data)
	#	oFile.close
	#
	#	loadConfig()
	#	return (0, "", 0)

	if cmd == "!drawbox":
		es.msg("drawing")
		for trigger in triggers:
			[id, name, x1, y1, z1, x2, y2, z2]=trigger
			effectlib.drawLine([x1,y1,z1], [x2,y2,z2], model="materials/sprites/laser.vmt",halo="materials/sprites/halo01.vmt",seconds=120,width=10,red=255,green=255,blue=255)
			#effectlib.drawBox([x1, y1, z1], [x2, y2, z2], red=255, green=255, blue=255, width=10, seconds=1)
			#es.msg("[debug] drawbox %s %s" % ([x1,y1,z1], [x2,y2,z2]))
		return (0, "", 0)

	if cmd == "!quiet":
		c=players[userid]['quiet']
		if c == 1:
			es.tell(userid, "#lightgreen", "you will now see more messages")
			players[userid]['quiet']=0
		else:
			es.tell(userid, "#lightgreen", "debug messages have been disabled")
			players[userid]['quiet']=1
		return (0, "", 0)

	if cmd == "!reload":
		es.msg("reloading configuration")
		es.msg(loadConfig())
		return (0, "", 0)

	return (userid, text, teamOnly)

def player_death(ev):
	global players
	userid=ev['userid']
	players[userid]['triggerlist']=[-10]

def autoswitch(a, b):
	aa=int(a) + 100000
	bb=int(b) + 100000
	if aa < bb:
		#es.msg("warning switching values %s and %s" % (a,b))
		return [b, a]
	return [a, b]

