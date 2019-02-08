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
        reorderPlayList(conn)
        conn.close()
    
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
   
def reorderPlayList(conn):
   """ will reorder playlist according to present votes.
    :param conn: DB connection    """
   # Below does not work in v17: getDbId was only introduced in v18
   #infoTag=xbmc.Player().getMusicInfoTag()
#   xbmc.log("SPQR Currently playing track:"+infoTag.getURL()+
#      "*"+infoTag.getAlbumArtist()+"-"+infoTag.getTitle()+"$"+str(infoTag.getTrack()))
#   xbmc.log("SPQR Currently playing track:"+' '.join(dir(infoTag)))
   
   jsonGetItemRequest=xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.GetItem","id":"Player.GetItem","params":{"playerid":0}}')    
   try:
#       xbmc.log("SPQR Request:"+jsonGetItemRequest)
       response = json.loads(jsonGetItemRequest)
   except UnicodeDecodeError:
       response = json.loads(jsonGetItemRequest.decode('utf-8', 'ignore'))

   global previousSongId 
   #xbmc.log("SPQR json getItem:"+' '.join(dir(response)))
   xbmc.log("SPQR current song id:"+str(response.get("result").get("item").get("id"))+
      " previous:"+str(previousSongId))
   
   moveCurrentSongsVotesToFulfilledVotes(conn,response.get("result").get("item").get("id"))
   removePreviousSongFromPlaylist()
   
   scores=orderVotes(conn)    
   # songs will be organized in three sublists: first, songs with a positive score, second songs
   # with no votes, and, last, songs with negative votes
   # get songs in the current playlist
   currentSongs=getCurrentPlaylist()
   #pop first one, as it is presently playing
   presentSong=currentSongs.pop()
   songsWithNoVotes=removeSongsWithVotes(currentSongs,scores)   
   
   # duplicate list, will then be filtered
   positiveScores=list(scores)
   negativeScores=splitScores(positiveScores)
   
   xbmc.log("SPQR: positiveScores:"+' '.join(map(str,positiveScores)))
   xbmc.log("SPQR: negativeScores:"+' '.join(map(str,negativeScores)))
   
   alterPlayList(presentSong,positiveScores,songsWithNoVotes,negativeScores)
   
   # is this really needed? Al least to avoid removing first song from playlist at the beginning...
   previousSongId=response.get("result").get("item").get("id")
    
def alterPlayList(presentSong,positiveScores,songsWithNoVotes,negativeScores):
   """ apply new Playlist order. first, songs with a positive score, second songs
    with no votes, and, last, songs with negative votes
    :param presentSong: id of the currently playing song
    :param positiveScores: list of lists with elements id and score, the latter always positive
    :param songsWithNoVotes: list of tuples id, label, type 
    :param negativeScores:list of lists with elements id and score, the latter always negative"""
   # could modify Playlist through JSON RPC, has add, insert, remove and swap operations?
   # will first try to simply clear playlist and create a new one
   
   # concatenate different lists
   idList=[presentSong];
   idList.extend([score[0] for score in positiveScores]);
   idList.extend([song["id"] for song in songsWithNoVotes]);
   idList.extend([score[0] for score in negativeScores]);
   
   #debug
   #for id in idList:
#      xbmc.log("SPQR new song list item:"+str(id))

   xbmc.PlayList(0).clear();
   
   for id in idList:
#      xbmc.log("SPQR id:"+' '.join(map(str,id)))
      jsonRequest=xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Playlist.Add", '+
        '"params": { "item": {"songid": '+str(id)+'}, "playlistid": 0 }, "id": 1}')    
      try:
#       xbmc.log("SPQR Request:"+jsonRequest)
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
   
def getCurrentPlaylist():
   """ get a list with the songs on the current playlist 
   :return: list of tuples id, label, type"""
   jsonRequest=xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Playlist.GetItems","id":"Playlist.GetItems","params":{"playlistid":0}}')    
   try:
#       xbmc.log("SPQR Request:"+jsonRequest)
       response = json.loads(jsonRequest)
   except UnicodeDecodeError:
       response = json.loads(jsonRequest.decode('utf-8', 'ignore'))
   #xbmc.log("SPQR json get Playlist:"+' '.join(dir(response.get("result").get("items"))))
   #for song in response.get("result").get("items"):
#      #xbmc.log("SPQR Playlist item:"+' '.join(song))
#      for key in song:
#         xbmc.log("SPQR Playlist item:"+key+"*"+str(song[key]))
   	
   return response.get("result").get("items")
	
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
	       
def moveCurrentSongsVotesToFulfilledVotes(conn,songid):
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
   
   
