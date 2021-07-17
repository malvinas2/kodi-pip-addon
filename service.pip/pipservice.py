#!/usr/bin/python3
import xbmc
import xbmcaddon
import xbmcgui
import os
import shutil
import json

# addon infos
__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
__icon__ = __addon__.getAddonInfo('icon')
 

# pathes and files
resourcepath = "/storage/.kodi/addons/service.pip/resources/"
configpath = "/storage/.config/"
keymappath = "/storage/.kodi/userdata/keymaps/"
keymapfile = "pipkeymap.xml"
autostartfile = "autostart.sh"
imagefile = "/tmp/thumb.png"
settingsfile = "/tmp/pipsettings.json"

# parameters
x = 20
y = 110
w = 280
h = 160


# get addon settings
def get_settings():

  settings = {}

  # get addon settings and convert them to a dictionary
  settings['top'] = bool(__addon__.getSetting('top'))
  settings['left'] = bool(__addon__.getSetting('left'))
  settings['xgap'] = int(__addon__.getSetting('xgap'))
  settings['ygap'] = int(__addon__.getSetting('ygap'))
  settings['width'] = int(__addon__.getSetting('width'))
  settings['height'] = int(__addon__.getSetting('height'))
  settings['ipaddress'] = str(__addon__.getSetting('ipaddress'))
  settings['port'] = str(__addon__.getSetting('port'))
  settings['username'] = str(__addon__.getSetting('username'))
  settings['password'] = str(__addon__.getSetting('password'))

  # serialize settings into file
  json.dump(settings, open(settingsfile, 'w' ))

  return settings


# install files
def install_files():
  if not os.path.exists(keymappath + keymapfile):
    # add keymap
    shutil.copy(resourcepath + keymapfile, keymappath + keymapfile)

  if not os.path.exists(configpath + autostartfile):
    # add autostart.sh
    shutil.copy(resourcepath + autostartfile, configpath + autostartfile)
  else:
    # append autostart.sh if required
    fobj = open(configpath + autostartfile, "r")
    data = fobj.read()
    fobj.close()
    if data.find("service.pip/pipffmpeg.sh") == -1:
      fobj = open(configpath + autostartfile, "a")

      out = "\n(\n"
      out = "%s  sleep 20\n" % out
      out = "%s  /storage/.kodi/addons/service.pip/pipffmpeg.py\n" % out
      out = "%s)&\n" % out

      data = fobj.write(out)
      fobj.close()


# main
if __name__ == '__main__':

  # just during installation
  install_files()

  xbmc.log('[pip-service] Starting', xbmc.LOGINFO)
  Once = True 

  # start a xbmc monitor
  monitor = xbmc.Monitor()

  # loop until monitor reports an abort
  while not monitor.waitForAbort(1):

    # get settings
    settings = get_settings()
    xbmc.log('[pip-service] Settings: %s' % str(settings), xbmc.LOGINFO)

    # get current windows ID
    winId = xbmcgui.getCurrentWindowId()

    # get dimensions
    wwin = winId.getWidth()
    hwin = winId.getHeight()
    w = settings['width']
    h = settings['height']
    if settings['left']:
      x = settings['xgap']
    else:
      x = wwin - settings['xgap'] - w
    if settings['top']:
      y = settings['ygap']
    else:
      y = hwin - settings['ygap'] - h

    # if video fullscreen window ID
    if winId == 12005:

      # wait 0.5 seconds
      xbmc.sleep(500)

      if Once:
        # get windows handle just once
        winHdl = xbmcgui.Window(winId)
        Once = False
      else:
        try:
          # remove 2nd image control
          winHdl.removeControl(imgHdl2)
          del imgHdl2
        except:
          pass

      # create 1st image control
      imgHdl = xbmcgui.ControlImage(x, y, w, h, imagefile)

      # add 1st control to windows handle
      winHdl.addControl(imgHdl)

      # wait 0.5 seconds
      xbmc.sleep(500)

      # create 2nd image control
      imgHdl2 = xbmcgui.ControlImage(x, y, w, h, imagefile)

      # add 2nd control to windows handle
      winHdl.addControl(imgHdl2)

      # remove 1st control
      winHdl.removeControl(imgHdl)
      del imgHdl

    else:
      # remove handle if windows ID has changed
      try:
        winHdl.removeControl(imgHdl)
        del imgHdl
      except:
        pass
      try:
        winHdl.removeControl(imgHdl2)
        del imgHdl2
      except:
        pass

  # clean up al objects
  try:
    winHdl.removeControl(imgHdl)
    del imgHdl
  except:
    pass
  try:
    winHdl.removeControl(imgHdl2)
    del imgHdl2
  except:
    pass
  xbmc.log('[refresh-pip] Finished, exiting', xbmc.LOGINFO)

