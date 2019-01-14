import xbmc
import sys
import sqlite3
from sqlite3 import Error
import xbmcaddon
import os
import xbmcvfs
import json
import time
   	

class EventMonitor(xbmc.Player):
    # song index to keep track of playing order (class attribute)
    songIndex=0
    
    # from forum.kodi.tv/showthread.php?tid338471
    def __init__ (self):
        self.conn=setupDB()
        monitor=xbmc.Monitor()
        xbmc.Player.__init__(self)
        xbmc.log("EventMonitor launched")
        while not monitor.abortRequested():
           # Sleep/wait for abort for 10 seconds
           if monitor.waitForAbort(10):
              # Abort was requested while waiting. We should exit
              break
        xbmc.log("leaving monitor addon! %s" % time.time(), level=xbmc.LOGNOTICE)
    
    def onPlayBackStarted(self):
        xbmc.log("Spoted onPlayBackStarted")
        EventMonitor.songIndex+=1
        reorderPlayList(self.conn)
    
    def onQueueNextItem(self):
        xbmc.log("Spoted onQueueNextItem")
    
    def onAVStarted(self):
        xbmc.log("Spoted onAVStarted ")
        
    def onPlayBackStopped(self):
        xbmc.log("Spoted onPlayBackStopped ")
        
    def onPlayBackSeekChapter(self):
        xbmc.log("Spoted  onPlayBackSeekChapter")


def reorderPlayList(conn):
    """ will reorder playlist according to present votes.
    """
    infoTag=xbmc.Player().getMusicInfoTag()
    xbmc.log("Currently playing track #:"+str(infoTag.getDbId()))
    
    moveCurrentSongsVotesToFulfilledVotes(conn,infoTag)
    #removeCurrentSonfFromPlaylist(infoTag)
      

    
def moveCurrentSongsVotesToFulfilledVotes(conn,infoTag):
   try:
      cur = conn.cursor()
      cur.execute("""INSERT INTO  fulfilledVotes (user, value,songid,songorder) select user, value,"""+str(infoTag.getDbId())+""" AS songid, """+
        EventMonitor.songIndex+""" AS songorder FROM unfulfilledVotes WHERE songid=? """,(infoTag.getDbId(),))
      cur.execute("""DELETE FROM unfulfilledVotes WHERE songid=? """,(infoTag.getDbId(),))
      conn.commit()       
    
   except Error as e:
      xbmc.log("Error: movePresentSongsVotesToFulfilledVotes failed: "+' '.join(e))
      
def removeCurrentSonfFromPlaylist(infoTag):
   xbmc.Playlist().remove(infoTag.getURL())
         
# code from http://www.sqlitetutorial.net/sqlite-python/create-tables/
def setupDB():
   try:
       # Check for need to create profile dir
       profile_dir = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')).decode('utf-8')
      
       if xbmcvfs.exists(profile_dir):
          xbmc.log("Profile dir:"+profile_dir)
       else:
          xbmcvfs.mkdir(profile_dir)
          xbmc.log("Created profile dir:"+profile_dir)
     
       database = os.path.join(profile_dir,"spqr.db")
       	
       xbmc.log("DB file:"+database)
       
       # create a database connection
       conn = sqlite3.connect(database)
       if conn is None:
           xbmc.log("Error: cannot create the database connection.")
           
       # to be used outside this function
       return conn
   except Error as e:
       xbmc.log("Error: setupDB failed: "+' '.join(e))
       
# Launch point
if __name__ == '__main__':
   # Get profile dir
   xbmc.log("Starting monitor service...Python API:"+xbmc.python)

   EventMonitor()
   
   