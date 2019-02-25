import xbmc
import sys
import sqlite3
from sqlite3 import Error
import xbmcaddon
import os
import xbmcvfs
import json
import time
import spqr_library	

class EventMonitor(xbmc.Player):
    # song index to keep track of playing order (class attribute)
    songIndex=0
    
    # from forum.kodi.tv/showthread.php?tid338471
    def __init__ (self):
        conn=setupDB()
        moveVotesToPastVotes(conn)
        conn.close()
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
        conn=setupDB()
        orderedPlaylist=reorderPlayList(conn)
        alterPlayList(orderedPlaylist)
        spqr_library.sendPlaylist(conn,orderedPlaylist["currentSongIndex"],orderedPlaylist["playlist"],"none")
        conn.close()
    
    def onQueueNextItem(self):
        xbmc.log("SPQR Spoted onQueueNextItem")
    
    def onAVStarted(self):
        xbmc.log("SPQR Spoted onAVStarted ")
        
    def onPlayBackStopped(self):
        xbmc.log("SPQR Spoted onPlayBackStopped ")
        
    def onPlayBackSeekChapter(self):
        xbmc.log("SPQR Spoted onPlayBackSeekChapter")

# Global vars
# not nedded anymore, since previous songs will be kept in the playlist previousSongId=None

def moveVotesToPastVotes(conn):
   """ When starting a new session, move all votes, independently of having been
       fulfilled or not, to the pastVotes table. This infor might be used to select songs
       when no votes are present, namely on startup
     :param conn: DB connection"""
   try:
      cur = conn.cursor()
      cur.execute("""INSERT INTO pastVotes (user, value,songid,date) SELECT user, value,songid,date"""+
         """ FROM unfulfilledVotes """)
      cur.execute("""INSERT INTO pastVotes (user, value,songid,date) SELECT user, value,songid,date"""+
         """ FROM fulfilledVotes """)
      cur.execute("""DELETE FROM unfulfilledVotes """)
      cur.execute("""DELETE FROM fulfilledVotes """)
      conn.commit()       
      cur.close()
   except Error as e:
      xbmc.log("SPQR Error: moveVotesToPastVotes failed: "+' '.join(e)) 
  
# Creating a new playlist each time was corrupting the playback
# Therefore, previously played songs will not be deleted and upcoming
# songs will merely be reordered.  
def reorderPlayList(conn):
   """ will reorder playlist according to present votes. Song queued next will be kept on top of playlist
    :param conn: DB connection    """
   # Below does not work in v17: getDbId was only introduced in v18
   #infoTag=xbmc.Player().getMusicInfoTag()
#   xbmc.log("SPQR Currently playing track:"+infoTag.getURL()+
#      "*"+infoTag.getAlbumArtist()+"-"+infoTag.getTitle()+"$"+str(infoTag.getTrack()))
#   xbmc.log("SPQR Currently playing track:"+' '.join(dir(infoTag)))
   
   currentSongID=spqr_library.getCurrentSong()["id"]
   
   xbmc.log("SPQR current song id:"+str(currentSongID))
   
   # songs will be organized in three sublists: first, songs with a positive score, second songs
   # with no votes, and, last, songs with negative votes
   # get songs in the current playlist (dequeue))
   playlist=spqr_library.getCurrentPlaylist()
   for song in playlist:
      xbmc.log("SPQR song in playlist:"+str(song["id"])+":"+song["label"].encode('utf-8'))   
      
   currentSongIndex=spqr_library.findSongInPlaylist(playlist,currentSongID)
   
   xbmc.log("SPQR current song index:"+str(currentSongIndex)+" id:"+str(playlist[currentSongIndex]["id"])+":"+
      playlist[currentSongIndex]["label"].encode('utf-8'))
   xbmc.log("SPQR current playlist length:"+str(len(playlist)))#+" first:"+str(currentSongs[0].get("label"))+":"+str(currentSongs[0].get("id")))
   
   # since next two songs are already fixed in playlist, remove their votes from the db
   moveSongsVotesToFulfilledVotes(conn,currentSongID)
   if currentSongIndex+1 < len(playlist):
      moveSongsVotesToFulfilledVotes(conn,playlist[currentSongIndex+1]["id"])
      
   scores=orderVotes(conn)    
   
   # Keep current song and the one queued after it out of ordering: their position will not be changed
   upcomingSongs=playlist[currentSongIndex+2:]
   
   songsWithNoVotes=removeSongsWithVotes(upcomingSongs,scores)   
   
   # duplicate list, will then be filtered
   positiveScores=list(scores)
   negativeScores=splitScores(positiveScores)
   
   xbmc.log("SPQR  positiveScores:"+' '.join(map(str,positiveScores)))
   xbmc.log("SPQR negativeScores:"+' '.join(map(str,negativeScores)))
   
   # concatenate different lists
   # when done for the fist time, there will be no song to remove, thus the previous song must be kept in the playlist
  
   idList=[playlist[currentSongIndex]["id"],playlist[currentSongIndex+1]["id"]]
   
   idList.extend([score[0] for score in positiveScores]);
   idList.extend([song["id"] for song in songsWithNoVotes]);
   idList.extend([score[0] for score in negativeScores]);
   
   for id in idList:
      xbmc.log("SPQR song in playlist after reorder:"+str(id))
      
   return {"currentSongIndex":currentSongIndex,"idList":idList,"playlist":playlist}   

# Not used anymore   
#def removePresentSong(currentSongs,presentSong):
#    """ remove from currentSongs the entry with the ID in presentSong
#    :param currentSongs: song list
#    :param presentSong: currently playing song id"""
#    return [x for x in currentSongs if not x.get("id")==presentSong]
	
def alterPlayList(orderedPlaylist):
   """ apply new Playlist order. first, songs with a positive score, second songs
    with no votes, and, last, songs with negative votes
    :param idList: song id list"""
   # will modify Playlist through JSON RPC:it has add, insert, remove and swap operations
   # simply clearing playlist and creating a new one was corrupting playback
   #debug
   #for id in idList:
#      xbmc.log("SPQR new song list item:"+str(id))

   currentSongIndex=orderedPlaylist["currentSongIndex"]
   idList=orderedPlaylist["idList"]
   playlist=orderedPlaylist["playlist"]
   
   # since two first songs should not be moved, will start changes a bit further
   for idIndex in range(1,len(idList)):
      # TODO was throwing an error of index ou of bounds....
      if currentSongIndex+idIndex>=len(playlist):
         xbmc.log("SPQR adding. Cycle:"+str(idIndex)+"search:"+str(idList[idIndex]))
         addToPlaylist(playlist,currentSongIndex+idIndex,idList[idIndex])
      else:    
         if idList[idIndex]!=playlist[currentSongIndex+idIndex]["id"]:
            #will need to search for song and move to current position
            songIndex=spqr_library.findSongInPlaylist(playlist,idList[idIndex])
            # if not found, must add to playlist
            if songIndex==-1:
               xbmc.log("SPQR adding. Cycle:"+str(idIndex)+"search:"+str(idList[idIndex]))
               addToPlaylist(playlist,currentSongIndex+idIndex,idList[idIndex])
            else:
               # Will swap next position in playlist with songIndex. Maybe it could be more efficient
               # to remove songIndex and insert here, shifting other elements, but that would require 
               xbmc.log("SPQR swaping. Cycle:"+str(idIndex)+"search:"+str(idList[idIndex])+"="
               # an insert and a removal, which might corrupt the playlist...
               +" getting:"+str(songIndex)+"-"+str(playlist[songIndex]["id"])+"*"+playlist[songIndex]["label"].encode('utf-8')
               +" to:"+str(currentSongIndex+idIndex)+"-"+str(playlist[currentSongIndex+idIndex]["id"])+"*"+
               playlist[currentSongIndex+idIndex]["label"].encode('utf-8'))
               jsonRequest=xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Playlist.Swap", '+
                 '"params": { "position1":'+str(currentSongIndex+idIndex)+',"position2":'+str(songIndex)+
                 ', "playlistid": 0 }, "id": 1}')    
               # must also swap in local playlist
               playlist[currentSongIndex+idIndex],playlist[songIndex]=playlist[songIndex],playlist[currentSongIndex+idIndex]
               try:
                  response = json.loads(jsonRequest)
               except UnicodeDecodeError:
                  response = json.loads(jsonRequest.decode('utf-8', 'ignore'))
       
def addToPlaylist(playlist,position,songID):
   jsonRequest=xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Playlist.Insert", '+
     '"params": { "position":'+str(position)+',"item":{"songid":'+str(songID)+
     '}, "playlistid": 0 }, "id": 1}')    
   # must also add to local playlist
   playlist.insert(position,{"id":songID})
   try:
     response = json.loads(jsonRequest)
   except UnicodeDecodeError:
     response = json.loads(jsonRequest.decode('utf-8', 'ignore'))
   
          
def splitScores(scores):
   """ filters the scores in the first argument, keeping positive scores. Negative scores are returned
   in new list
   :param scores: list of lists with elements id and score
   :return list of lists with elements id and score, the latter always negative"""
   negativeScores=[]
   for score in scores[:]:
      if score[1]<0:
         negativeScores.append(score)
         scores.remove(score)
         #xbmc.log("SPQR negative score:"+str(score[1]))
   return negativeScores
   
def removeSongsWithVotes(currentSongs,scores):
   """filters from the list in the first argument all the songs in the second argument"""
   # TODO
   result=[]
   for song in currentSongs:
      if not existsSongWithId(song["id"],scores):
         result.append(song)
         #xbmc.log("SPQR adding song with no votes:"+str(song["id"])) 
   return result
	
def existsSongWithId(id,scores):
   """ checks if id exists in the songs in the scores list
   :param id: numeric
   :param scores: list of lists with elements id and score """
   for score in scores:
      #xbmc.log("SPQR score:"+' '.join(map(str,score)))
      if score[0]==id:
         return True
   return False
   
def orderVotes(conn):
   """ compute new playlist according to votes on the db
     :param conn: DB connection"""
   # TODO think about a robust, meanibgfuk algorithm
   # initially, to test, very simple algorithm: count votes, adding 1 for up, 0.5 for down
   try:
      cur = conn.cursor()
      cur.execute("""DROP TABLE IF EXISTS tempVotes""")
      cur.execute("""CREATE TEMP TABLE tempVotes AS SELECT songid, sum(value) AS votes FROM unfulfilledVotes WHERE value=1 GROUP BY songid """)
      cur.execute("""INSERT INTO tempVotes SELECT songid, sum(value)*.5 AS votes FROM unfulfilledVotes WHERE value=-1 GROUP BY songid """)
      cur.execute("""SELECT songid, sum(votes) AS score FROM tempVotes GROUP BY songid ORDER BY score DESC""")   
      rows = cur.fetchall()
      #for row in rows:
      #   xbmc.log("SPQR new playlist Row:"+' '.join(map(str,row)))
      cur.close()
      return rows      
   except Error as e:
      xbmc.log("SPQR Error: orderVotes failed: "+' '.join(e))
	       
	       
def moveSongsVotesToFulfilledVotes(conn,songid):
   xbmc.log("SPQR moving votes song #:"+str(songid))
   try:
      cur = conn.cursor()
      cur.execute("""INSERT INTO fulfilledVotes (user, value,songid,songorder,date) SELECT user, value,songid,"""+
        str(EventMonitor.songIndex)+""" AS songorder, date FROM unfulfilledVotes WHERE songid=? """,(songid,))
      cur.execute("""DELETE FROM unfulfilledVotes WHERE songid=? """,(songid,))
      conn.commit()       
      cur.close()
   except Error as e:
      xbmc.log("SPQR Error: movePresentSongsVotesToFulfilledVotes failed: "+' '.join(e))
# Not being used      
#def removePreviousSongFromPlaylist():
#  global previousSongId
#  #will simply remove the first song... Which will be the one last played...
#  if previousSongId!=None: # Will be None at the beginning...
#      xbmc.log("SPQR removing: "+str(previousSongId))
#      jsonGetItemRequest=xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Playlist.Remove", "id":"Playlist.Remove","params":{"playlistid":0, "position":0}}')
#      try:
##        xbmc.log("SPQR Request:"+jsonGetItemRequest)
#        response = json.loads(jsonGetItemRequest)
#      except UnicodeDecodeError:
#        response = json.loads(jsonGetItemRequest.decode('utf-8', 'ignore'))
#        
#      xbmc.log("SPQR removing response:"+' '.join(dir(response)))
#  else:
#      xbmc.log("SPQR NOT removing:"+str(previousSongId))
         
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
       conn = sqlite3.connect(database, timeout=10)
       if conn is None:
           xbmc.log("SPQR Error: cannot create the database connection.")
       else:
          if tablesNotCreated(conn):
             createDbTables(conn)
          # to be used outside this function
          return conn
   except Error as e:
       xbmc.log("SPQR Error: setupDB failed: "+' '.join(e))
       
def tablesNotCreated(conn):
   """ Check if necessary tables were already created 
    :param conn: Connection object"""
   # from https://stackoverflow.com/questions/17044259/python-how-to-check-if-table-exists
   # and https://stackoverflow.com/questions/1601151/how-do-i-check-in-sqlite-whether-a-table-exists
   dbcur = conn.cursor()
   dbcur.execute("""
       SELECT COUNT(*)
       FROM sqlite_master WHERE type='table' AND name= 'unfulfilledVotes'""")
   if dbcur.fetchone()[0] == 1:
       dbcur.close()
       return False

   dbcur.close()
   return True
 
def createDbTables(conn):
    cur = conn.cursor()
    # value should be 1 or -1, depending on being up or downvote. No booleans in SQLite! 
    sql_create_unfulfilledvotes_table = """ CREATE TABLE IF NOT EXISTS unfulfilledVotes (
             user TEXT NOT NULL,
             songid INTEGER NOT NULL,
             value INTEGER NOT NULL,
             date TEXT NOT NULL);"""
    cur.execute(sql_create_unfulfilledvotes_table)
    sql_create_fulfilledvotes_table = """CREATE TABLE IF NOT EXISTS fulfilledVotes (
             user TEXT NOT NULL,
             songid INTEGER NOT NULL,
             value INTEGER NOT NULL,
             songorder INTEGER NOT NULL,
             date TEXT NOT NULL); """
    cur.execute(sql_create_fulfilledvotes_table)
    sql_create_pastvotes_table = """CREATE TABLE IF NOT EXISTS pastVotes (
             user text NOT NULL,
             songid integer NOT NULL,
             value integer NOT NULL,
             date TEXT NOT NULL); """
    cur.execute( sql_create_pastvotes_table)
    conn.commit()
    cur.close()
    xbmc.log("SPQR created tables") 
           
# Launch point
if __name__ == '__main__':
   xbmc.log("SPQR Starting monitor service...")
   
   EventMonitor()
   
   
