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
        xbmc.log("SPQR EventMonitor launched")
        while not monitor.abortRequested():
           # Sleep/wait for abort for 10 seconds
           if monitor.waitForAbort(10):
              # Abort was requested while waiting. We should exit
              break
        xbmc.log("SPQR leaving monitor addon! %s" % time.time(), level=xbmc.LOGNOTICE)
    
    def onPlayBackStarted(self):
        xbmc.log("SPQR Spoted onPlayBackStarted")
        EventMonitor.songIndex+=1
        reorderPlayList(self.conn)
    
    def onQueueNextItem(self):
        xbmc.log("SPQR Spoted onQueueNextItem")
    
    def onAVStarted(self):
        xbmc.log("SPQR Spoted onAVStarted ")
        
    def onPlayBackStopped(self):
        xbmc.log("SPQR Spoted onPlayBackStopped ")
        
    def onPlayBackSeekChapter(self):
        xbmc.log("SPQR Spoted  onPlayBackSeekChapter")

# Global vars
previousSongId=None

def reorderPlayList(conn):
    """ will reorder playlist according to present votes.
    """
    # Below does not work in v17: getDbId was only introduced in v18
    #infoTag=xbmc.Player().getMusicInfoTag()
#    xbmc.log("SPQR Currently playing track:"+infoTag.getURL()+
#       "*"+infoTag.getAlbumArtist()+"-"+infoTag.getTitle()+"$"+str(infoTag.getTrack()))
#    xbmc.log("SPQR Currently playing track:"+' '.join(dir(infoTag)))
    
    jsonGetItemRequest=xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.GetItem","id":"Player.GetItem","params":{"playerid":0}}')    
    try:
#        xbmc.log("SPQR Request:"+jsonGetItemRequest)
        response = json.loads(jsonGetItemRequest)
    except UnicodeDecodeError:
        response = json.loads(jsonGetItemRequest.decode('utf-8', 'ignore'))

    global previousSongId 
    #xbmc.log("SPQR json getItem:"+' '.join(dir(response)))
    xbmc.log("SPQR current song id:"+str(response.get("result").get("item").get("id"))+
       " previous:"+str(previousSongId))
    
    
    moveCurrentSongsVotesToFulfilledVotes(conn,response.get("result").get("item").get("id"))
    removePreviousSongFromPlaylist()
    # will probably need to do this through JSON RPC, has add, insert, remove and swap operations
    #  
    # is this really needed? Al least to avoid removing first song from playlist at the beginning...
    previousSongId=response.get("result").get("item").get("id")
    
def moveCurrentSongsVotesToFulfilledVotes(conn,songid):
   xbmc.log("SPQR moving votes song #:"+str(songid))
   try:
      cur = conn.cursor()
      cur.execute("""INSERT INTO fulfilledVotes (user, value,songid,songorder) SELECT user, value,songid,"""+
        str(EventMonitor.songIndex)+""" AS songorder FROM unfulfilledVotes WHERE songid=? """,(songid,))
      cur.execute("""DELETE FROM unfulfilledVotes WHERE songid=? """,(songid,))
      conn.commit()       
    
   except Error as e:
      xbmc.log("SPQR Error: movePresentSongsVotesToFulfilledVotes failed: "+' '.join(e))
      
def removePreviousSongFromPlaylist():
  global previousSongId
  #will simply remove the first song... Which will be the one last played...
  if previousSongId!=None: # Will be None at the beginning...
      xbmc.log("SPQR removing"+str(previousSongId))
      jsonGetItemRequest=xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Playlist.Remove", "id":"Playlist.Remove","params":{"playlistid":0, "position":0}}')
      try:
#        xbmc.log("SPQR Request:"+jsonGetItemRequest)
        response = json.loads(jsonGetItemRequest)
      except UnicodeDecodeError:
        response = json.loads(jsonGetItemRequest.decode('utf-8', 'ignore'))
        
      #xbmc.log("SPQR removing response:"+' '.join(dir(response)))
  else:
  	   xbmc.log("SPQR NOT removing"+str(previousSongId))
         
# code from http://www.sqlitetutorial.net/sqlite-python/create-tables/
def setupDB():
   try:
       # Check for need to create profile dir
       profile_dir = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')).decode('utf-8')
      
       if xbmcvfs.exists(profile_dir):
          xbmc.log("SPQR Profile dir:"+profile_dir)
       else:
          xbmcvfs.mkdir(profile_dir)
          xbmc.log("SPQR Created profile dir:"+profile_dir)
     
       database = os.path.join(profile_dir,"spqr.db")
       	
       xbmc.log("SPQR DB file:"+database)
       
       # create a database connection
       conn = sqlite3.connect(database)
       if conn is None:
           xbmc.log("SPQR Error: cannot create the database connection.")
           
       # to be used outside this function
       return conn
   except Error as e:
       xbmc.log("SPQR Error: setupDB failed: "+' '.join(e))
       
# Launch point
if __name__ == '__main__':
   # Get profile dir
   xbmc.log("SPQR Starting monitor service...")

   EventMonitor()
   
   
