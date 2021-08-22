#!/usr/bin/python3

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import os
import shutil
import json
import subprocess
import uuid
import urllib
from urllib.request import Request


# addon infos
__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
__icon__ = __addon__.getAddonInfo('icon')


# files
keymapfilename = "pipkeymap.xml"
imagefilename = "thumb.png"


'''
Class XBMCMonitor
xbmc monitor with on notification and on settings changed handler
'''
class XBMCMonitor( xbmc.Monitor ):

    # constructor
    def __init__(self):
        self.toggled = False
        self.channelup = False
        self.channeldown = False
        self.channelback = False
        self.changed = False


    # get toggle status
    def get_toggle_status(self):
        ret = self.toggled
        self.toggled = False
        return ret


    # get channel up status
    def get_channel_up_status(self):
        ret = self.channelup
        self.channelup = False
        return ret


    # get channel down status
    def get_channel_down_status(self):
        ret = self.channeldown
        self.channeldown = False
        return ret


    # get channel back status
    def get_channel_back_status(self):
        ret = self.channelback
        self.channelback = False
        return ret


    # called on a notification
    def onNotification(self, sender, method, data):

        if sender == "service.pip":
            xbmc.log("[pip-service] key press detected!", xbmc.LOGINFO)
            if method == "Other.toggle_pip":
                xbmc.log("[pip-service] via notifiyAll: sender=%s, method=%s, data=%s" % (str(sender), str(method), str(data)), xbmc.LOGDEBUG)
                self.toggled= True

            if method == "Other.channel_up_pip":
                xbmc.log("[pip-service] via notifiyAll: sender=%s, method=%s, data=%s" % (str(sender), str(method), str(data)), xbmc.LOGDEBUG)
                self.channelup = True

            if method == "Other.channel_down_pip":
                xbmc.log("[pip-service] via notifiyAll: sender=%s, method=%s, data=%s" % (str(sender), str(method), str(data)), xbmc.LOGDEBUG)
                self.channeldown= True

            if method == "Other.channel_back_pip":
                xbmc.log("[pip-service] via notifiyAll: sender=%s, method=%s, data=%s" % (str(sender), str(method), str(data)), xbmc.LOGINFO)
                self.channelback= True


    # get settings changed status
    def get_settings_changed_status(self):
        changed = self.changed
        self.changed = False
        return changed


    # called on settings changed
    def onSettingsChanged(self):
        xbmc.log("[pip-service] settings have changed.", xbmc.LOGINFO)
        self.changed = True



'''
Class M3U
handles m3u download, parsing and url request
'''
class M3U():

    # constructor
    def __init__(self, username, password, ipaddress, port, profile):
        self.update_settings(username, password, ipaddress, port, profile)
        self.m3ulines = None
        self.channel2url = {}
        self.channel2number = {}
        self.number2channel = {}
        self.number2url = {}
        self.channel2id = {}
        self.url = ""
        self.channel = ""


    # update settings
    def update_settings(self, username, password, ipaddress, port, profile):
        self.username = username
        self.password = password
        self.ipaddress = ipaddress
        self.port = port
        self.profile = profile


    # download m3u as pipe from tvheadend server
    def download(self):

        url = 'http://%s:%s/playlist/channels.m3u?profile=%s' % (self.ipaddress, self.port, self.profile)

        # urllib request with Digest auth
        hndlr_chain = []
        mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        mgr.add_password(None, url, self.username, self.password)
        hndlr_chain.append(urllib.request.HTTPDigestAuthHandler(mgr))

        # build request
        director = urllib.request.build_opener(*hndlr_chain)
        req = Request(url, headers={})

        try:
            # get request
            result = director.open(req)

            # read result ans split it to lines
            self.m3ulines = result.read().decode("utf-8").split("\n")
            xbmc.log("[pip-service] download m3u file with %d lines from %s." % (len(self.m3ulines), url), xbmc.LOGINFO)
        except urllib.error.HTTPError:
            xbmc.log("[pip-service] download of m3u file failed - HTTP error 403: forbidden to access %s." % (url), xbmc.LOGWARNING)
        except urllib.error.URLError:
            xbmc.log("[pip-service] download of m3u file failed - connection refused to %s." % (url), xbmc.LOGWARNING)


    # parse m3u file to dict
    def parse(self):

        # #EXTINF:-1 logo="http://192.168.144.67:9981/imagecache/13" tvg-id="efa6b645f9399cc41becd20cceb0d2c2" tvg-chno="1",Das Erste HD
        # http://192.168.144.67:9981/stream/channelid/1169598191?profile=pass

        self.channel2url = {}
        self.channel2number = {}
        self.number2url = {}
        self.number2channel = {}
        if self.m3ulines != None:
            for i, line in enumerate(self.m3ulines):
                # loop line list
                if line.find("logo=") != -1 and line.find("tvg-id=") != -1 and line.find("tvg-chno=") != -1:
                    # split line by tvg-chno
                    parts = line.split("tvg-chno=")

                    if len(parts) > 1:
                        # split line by '",' to get channel name
                        pparts = parts[1].split("\",")

                        if len(pparts) > 1:
                            # create a loopup dictionary key=channel-name and value=url-link
                            name = pparts[1].replace('\n', '')
                            self.channel2url[name] = self.m3ulines[i+1].replace('\n', '')

                            # create a loopup dictionary key=channel-name and value=number
                            number = pparts[0].replace('"', '')
                            self.channel2number[name] = int(number)
                            self.number2channel[int(number)] = name
                            self.number2url[int(number)] = self.channel2url[name]

            xbmc.log("[pip-service] parsed %d channels." % len(self.channel2url), xbmc.LOGINFO)
            if len(self.channel2url) == 0:
                xbmc.log("[pip-service] check m3u file format to be:", xbmc.LOGDEBUG)
                xbmc.log("[pip-service] #EXTINF:-1 logo=\"...\" tvg-id=\"...\" tvg-chno=\"...\",[channel name]", xbmc.LOGDEBUG)
                xbmc.log("[pip-service] http://192.168.1.1:9981/stream/channelid/[....]?profile=%s" % self.profile, xbmc.LOGDEBUG)


    # get pip channel name
    def get_channel_name(self):
        return self.channel


    # set new channel name depending on channel number
    def set_channel_name(self, channelnumber):
        self.channel = self.number2channel[channelnumber]


    # get current active channel the url of it
    def get_url(self):

        # get information for current player item as json reponse
        rpccmd = {
          "jsonrpc": "2.0",
          "method": "Player.GetItem",
          "params": {
            "properties": ["art", "title", "album", "artist", "season", "episode", "duration",
                            "showtitle", "tvshowid", "thumbnail", "file", "fanart","streamdetails"],
            "playerid": 1 },
          "id": "OnPlayGetItem"}
        rpccmd = json.dumps(rpccmd)
        result = xbmc.executeJSONRPC(rpccmd)
        result = json.loads(result)

        try:
            # if a channel label exists create a new channel.pip file that contains the url link
            self.channel = result['result']['item']['label']
            self.url = self.channel2url[self.channel]

        except KeyError:
            self.url = ""

        return self.url, self.channel


    # get all channel ids
    def get_channel_ids(self):

        rpccmd = {"jsonrpc":"2.0","method": "PVR.GetChannels","params": {"channelgroupid": "alltv"},"id": 1}
        rpccmd = json.dumps(rpccmd)
        result = xbmc.executeJSONRPC(rpccmd)
        result = json.loads(result)

        channels = result['result']['channels']
        self.channel2id = {}
        for channel in channels:
            self.channel2id[channel['label']] = channel['channelid']


    # switch to channel
    def switch_channel(self, channelname):

        # get information for current player item as json reponse
        rpccmd = {"id" : 1,
                  "jsonrpc" : "2.0",
                  "method" : "Player.Open",
                  "params" : {
                      "item" : { "channelid" : self.channel2id[channelname] }
                   }
                 }
        rpccmd = json.dumps(rpccmd)
        xbmc.executeJSONRPC(rpccmd)


'''
Class FFMPEG
controls ffmpeg process
'''
class FFMpeg():

    # constructor
    def __init__(self, imagefilename, tmpfolder, username, password, fps, addoptions, width):
        self.update_settings(tmpfolder, username, password, fps, addoptions, width)
        self.imagefile = tmpfolder + "/" + imagefilename
        self.proc = ""
        self.urlold = ""
        self.flgStarted = False

        # remove "old" image file
        if os.path.exists(self.imagefile):
            os.remove(self.imagefile)


    # update settings
    def update_settings(self, tmpfolder, username, password, fps, addoptions, width):
        self.tmpfolder = tmpfolder
        self.username = username
        self.password = password
        self.fps = fps
        self.addopts = addoptions
        self.width = width


    # test if ffmpeg is available
    def test(self):
        ret = False
        try:
            process = subprocess.Popen( ['ffmpeg', '-version'],
                                        stderr=subprocess.PIPE,
                                        stdout=subprocess.PIPE)
            process.communicate()
            exit_code = process.wait()
            if exit_code == 0:
                ret = True
            else:
                ret = False
        except FileNotFoundError:
            ret = False

        return ret


    # check if ffmpeg process is running
    def running(self):
        try:
            ret = self.proc.poll() == None
        except AttributeError:
            ret = False
        return ret


    # stop ffmpeg process if running
    def stop(self):
        self.urlold = ""
        if self.running():
            self.proc.kill()

        # remove "old" thumb.png
        if os.path.exists(self.imagefile):
            os.remove(self.imagefile)

        self.flgStarted = False


    # started status
    def started(self):
        return self.flgStarted


    # start a ffmpeg process
    def start(self, url, restart):

        if (url != self.urlold and url != "") or restart:
            # if a new current link is requested generate url with username and password
            urlauth = url.replace('http://', 'http://%s:%s@' % (self.username, self.password))

            # terminate process that may be still running
            self.stop()

            # create ffmpeg command to capture very second a new image from the IPTV url
            cmd = ['ffmpeg',
                   '-nostdin',
                   '-i', urlauth,
                   '-an',
                   '-ss', '00:00:08.000',
                   '-f', 'image2',
                   '-vf', 'fps=%d,scale=%d:-1' % (self.fps, self.width),
                   '-qscale:v', '10',
                   '-y',
                   '-update', 'true',
                   '-vcodec', 'mjpeg',
                   '-atomic_writing', 'true',
                   self.imagefile]

            for item in self.addopts.split(' '):
                if item != '':
                    cmd.append(item)

            # create and run ffmpeg process with the defined command
            self.proc = subprocess.Popen(cmd,
              stdout = open('%s/pipffmpeg_stdout.log' % self.tmpfolder, 'w'),
              stderr = open('%s/pipffmpeg_stderr.log' % self.tmpfolder, 'a'))
            self.flgStarted = True

            # remember current link in order to wait for next new channel request
            self.urlold = url


'''
Class PIP
controls display of picture-in-picture
'''
class PIP():

    # constructor
    def __init__(self, imagefilename, keymapfile):

        self.imagefilename = imagefilename
        self.imagefile = "/tmp/" + imagefilename
        self.keymapfile = keymapfile
        self.uuidfile = None

        self.settings = {}
        self.imgHdl = None
        self.img = False
        self.labelHdl = None
        self.channelnumber = 1

        self.x = 20
        self.y = 110
        self.w = 320
        self.h = 260

        self.winId = 12005
        self.winHdl = xbmcgui.Window(self.winId)


    # install keymap file
    def install(self):

        # path evaluation
        resourcepath = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('path')) + "resources/data/"
        keymappath = xbmcvfs.translatePath("special://home/userdata/keymaps/")

        # copy or overwrite keymap xml
        shutil.copy(resourcepath + self.keymapfile, keymappath + self.keymapfile)


    # get addon settings
    def get_settings(self, addon):

        # get addon settings and convert them to a dictionary
        if addon.getSetting('top') == 'true':
            self.settings['top'] = True
        else:
            self.settings['top'] = False

        if addon.getSetting('left') == 'true':
            self.settings['left'] = True
        else:
            self.settings['left'] = False

        self.settings['xgap'] = int(addon.getSetting('xgap'))
        self.settings['ygap'] = int(addon.getSetting('ygap'))
        self.settings['width'] = int(addon.getSetting('width'))
        self.settings['height'] = int(addon.getSetting('height'))
        self.settings['fps'] = int(addon.getSetting('fps'))
        self.settings['ipaddress'] = str(addon.getSetting('ipaddress'))
        self.settings['port'] = str(addon.getSetting('port'))
        self.settings['username'] = str(addon.getSetting('username'))
        self.settings['password'] = str(addon.getSetting('password'))
        self.settings['profile'] = str(addon.getSetting('profile'))
        self.settings['tmpfolder'] = str(addon.getSetting('tmpfolder'))
        self.settings['ffmpegopts'] = str(addon.getSetting('ffmpegopts'))

        self.imagefile = "%s/%s" % (self.settings['tmpfolder'], self.imagefilename)

        # return settings as dictionary
        return self.settings


    # display picture-in-picture image if avaiable
    def show_image(self):

        # get current windows ID
        winId = xbmcgui.getCurrentWindowId()

        # if video fullscreen window ID
        if winId == self.winId and os.path.exists(self.imagefile):
            if not self.img:
                # define dimensions
                wwin = self.winHdl.getWidth()
                hwin = self.winHdl.getHeight()
                xbmc.log("[pip-service] windows size: %d x %d" % (wwin, hwin), xbmc.LOGINFO)
                self.w = self.settings['width']
                self.h = self.settings['height']
                if self.settings['left']:
                    self.x = self.settings['xgap']
                else:
                    self.x = wwin - self.settings['xgap'] - self.w
                if self.settings['top']:
                    self.y = self.settings['ygap']
                else:
                    self.y = hwin - self.settings['ygap'] - self.h
                xbmc.log("[pip-service] x and y: %d x %d" % (self.x, self.y), xbmc.LOGINFO)

                # create image control
                self.imgHdl = xbmcgui.ControlImage(self.x, self.y, self.w, self.h, self.imagefile)
                self.imgHdl.setAnimations([('visible', 'effect=fade end=100 time=300 delay=300',)])

                # add image control to windows handle
                self.winHdl.addControl(self.imgHdl)

                # add channel number label control to windows handle
                self.labelHdl = xbmcgui.ControlLabel(self.x + 5, self.y, 125, 125, str(self.channelnumber))
                self.winHdl.addControl(self.labelHdl)

                self.img = True


            # set channel number label text
            self.labelHdl.setLabel(str(self.channelnumber))

            # add to latest captured image a unique id in order to force reload the image via setImage function
            olduuidfile = self.uuidfile
            self.uuidfile = self.imagefile.replace(".png", "%s.png" % str(uuid.uuid4()))
            try:
                # copy thumb.png to thumb[uuid].png
                shutil.copy(self.imagefile, self.uuidfile)

                # set new image file
                self.imgHdl.setImage(self.uuidfile, useCache = False)
            except FileNotFoundError:
                pass

            # remove already set image file if it exists
            if olduuidfile != None:
                if os.path.exists(olduuidfile):
                    os.remove(olduuidfile)


    def hide_image(self):
        # remove handle if windows ID has changed
        if self.img:
            self.winHdl.removeControl(self.imgHdl)
            del self.imgHdl
            self.winHdl.removeControl(self.labelHdl)
            del self.labelHdl
            self.img = False


    def set_channel_number(self, number):
        self.channelnumber = number


'''
Main function
'''
if __name__ == '__main__':

    # init pip
    xbmc.log('[pip-service] Starting', xbmc.LOGINFO)
    pip = PIP(imagefilename, keymapfilename)

    # install files, e.g. keymap to userdata
    pip.install()

    # get settings
    settings = pip.get_settings(__addon__)

    # init m3u
    m3u = M3U(settings['username'],
              settings['password'],
              settings['ipaddress'],
              settings['port'],
              settings['profile'])

    # download and parse channels
    m3u.download()
    m3u.parse()

    # get all available channel ids
    m3u.get_channel_ids()

    # start a xbmc monitor
    monitor = XBMCMonitor()

    # init ffmpeg
    ffmpeg = FFMpeg(imagefilename,
                    settings['tmpfolder'],
                    settings['username'],
                    settings['password'],
                    settings['fps'],
                    settings['ffmpegopts'],
                    settings['width'])

    # test if ffmpeg executable is available
    if ffmpeg.test():

        # loop until monitor reports an abort
        sleeptime = float(1/settings['fps'])
        while not monitor.waitForAbort(sleeptime):

            if monitor.get_settings_changed_status():

                # udpate pip settings
                settings = pip.get_settings(__addon__)

                # update m3u settings
                m3u.update_settings(settings['username'],
                                    settings['password'],
                                    settings['ipaddress'],
                                    settings['port'],
                                    settings['profile'])

                # download and parse channels
                m3u.download()
                m3u.parse()

                # update ffmpeg settings
                ffmpeg.update_settings( settings['tmpfolder'],
                                        settings['username'],
                                        settings['password'],
                                        settings['fps'],
                                        settings['ffmpegopts'],
                                        settings['width'])


            if monitor.get_toggle_status():
                if ffmpeg.started():
                    # stop picture in picture capturing
                    ffmpeg.stop()
                    xbmc.log("[pip-service] stopped ffmpeg process.", xbmc.LOGDEBUG)

                else:
                    # start picture in picture capturing using ffmpeg
                    url, channelname = m3u.get_url()
                    channelnumber = m3u.channel2number[channelname]
                    pip.set_channel_number(channelnumber)

                    if url == "":
                        xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(__addonname__, "No URL found ...", 2000, __icon__))
                        xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(__addonname__, "Not started ...", 2000, __icon__))
                    else:
                        ffmpeg.start(url, False)
                        xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(__addonname__, "Starting ...", 5000, __icon__))
                        xbmc.log("[pip-service] started ffmpeg process.", xbmc.LOGDEBUG)


            if monitor.get_channel_back_status():
                # switch back to pip channel
                channelname = m3u.get_channel_name()
                m3u.switch_channel(channelname)

                # stop picture in picture capturing
                ffmpeg.stop()
                xbmc.log("[pip-service] stopped ffmpeg process.", xbmc.LOGDEBUG)


            if monitor.get_channel_up_status():
                # switch one channel up of pip channel
                channelname = m3u.get_channel_name()
                channelnumber = m3u.channel2number[channelname]

                if (channelnumber + 1) in m3u.number2url:
                    url = m3u.number2url[channelnumber + 1]

                    # restart picture in picture capturing
                    ffmpeg.stop()
                    ffmpeg.start(url, False)

                    pip.set_channel_number(channelnumber + 1)
                    m3u.set_channel_name(channelnumber + 1)


            if monitor.get_channel_down_status():
                # switch one channel down of pip channel
                channelname = m3u.get_channel_name()
                channelnumber = m3u.channel2number[channelname]

                if (channelnumber - 1) in m3u.number2url:
                    url = m3u.number2url[channelnumber - 1]

                    # restart picture in picture capturing
                    ffmpeg.stop()
                    ffmpeg.start(url, False)

                    pip.set_channel_number(channelnumber - 1)
                    m3u.set_channel_name(channelnumber - 1)


            if ffmpeg.started() and not ffmpeg.running():
                # restart ffmpeg
                ffmpeg.start(url, True)
                xbmc.log("[pip-service] re-started ffmpeg process for %s." % url, xbmc.LOGWARNING)

            if ffmpeg.started():
                # display picture-in-picture if a capture image from ffmpeg process is available
                pip.show_image()
            else:
                pip.hide_image()

        # stop ffmpeg process if running
        ffmpeg.stop()

    else:
        xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(__addonname__, "No ffmpeg executable found ...", 2000, __icon__))
        xbmc.log("[pip-service] no ffmpeg executable available!", xbmc.LOGERROR)


    # clean up the rest
    del ffmpeg
    del m3u
    del monitor
    del pip
    del __addon__

    xbmc.log('[pip-service] finished, exiting', xbmc.LOGINFO)
