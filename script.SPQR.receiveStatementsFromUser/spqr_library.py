# definition of some functions used in different other files
import xbmc
import json
import sqlite3
from sqlite3 import Error

def getCurrentPlaylist():
   """ get a list with the songs on the current playlist 
   :return: list of tuples id, label, type"""
   jsonRequest=xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Playlist.GetItems","id":"Playlist.GetItems","params":{"playlistid":0, "properties": ["album", "albumartist","artist"]}}')    
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
   
def sendPlaylist(conn,user):
   """Send all relevant info to setup initial playlist display: send playlist, global votes and own votes. 
   When broadcasting after playlist change, user will be 'none', and thus no own votes will be sent.
   :param conn: DB connection
   :param user: the user id"""
   try:  
      jsonData={
        "playlist":getCurrentPlaylist(),
        "allVotes":getAllVotes(conn)}
      if user!="none":
      	jsonData["myVotes"]=getMyVotes(conn,user)
      	jsonData["user"]=user
      xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "JSONRPC.NotifyAll", "id":"JSONRPC.NotifyAll","params":{"sender":"SPQR","message":"GeneralUpdate","data":'+json.dumps(jsonData)+' }}')
   except Error as e:
         xbmc.log("SPQR Error: sendPlaylist failed: "+' '.join(e))
         
def getMyVotes(conn,user):	
   """Get all votes vy specified user
   :param conn: DB connection
   :param user: the user id"""
   try:
      #xbmc.log("SPQR Getting votes for:"+user)
      cur = conn.cursor()
      cur.execute("""SELECT songid, value FROM unfulfilledVotes WHERE user=? """,(user,))
         
      jsonData={"up":[],"down":[]}
      rows = cur.fetchall()
      for row in rows:
         #xbmc.log("SPQR Row:"+' '.join(map(str,row)))
         if row[1]==1:#upvote
            jsonData["up"].append(row[0])
         else:#downvote
            jsonData["down"].append(row[0])       
      # Was: xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "JSONRPC.NotifyAll", "id":"JSONRPC.NotifyAll","params":{"sender":"SPQR","message":"MyVotesUpdate","data":'+json.dumps(jsonData)+' }}')
      return jsonData
   except Error as e:
         xbmc.log("SPQR Error: getMyVotes failed: "+' '.join(e))
                  
def getAllVotes(conn):
   """Get all votes"""
   try:
   	# get all votes from DB, grouped by songid
   	# must separately get up and down votes
      cur = conn.cursor()
      cur.execute("""SELECT songid,count(*) AS count FROM unfulfilledVotes WHERE value=1 GROUP BY songid """)
      
      jsonDataUp={}
      rows = cur.fetchall()
      for row in rows:
         #xbmc.log("Row:"+' '.join(map(str,row)))
         #xbmc.log("Row:"+str(row[0])+":"+str(row[1]))
         jsonDataUp[row[0]]=row[1]
      
      # down votes
      cur.execute("""SELECT songid,count(*) AS count FROM unfulfilledVotes WHERE value=-1 GROUP BY songid """)
      jsonDataDown={}
      rows = cur.fetchall()
      for row in rows:
         #xbmc.log("SPQR Row:"+str(row[0])+":"+str(row[1]))
         jsonDataDown[row[0]]=row[1]

      jsonData={"up":jsonDataUp,"down":jsonDataDown}

      #Was xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "JSONRPC.NotifyAll", "id":"JSONRPC.NotifyAll","params":{"sender":"SPQR","message":"VoteUpdate","data":'+json.dumps(jsonData)+' }}')
      return jsonData
   except Error as e:
         xbmc.log("SPQR Error: getAllVotes failed: "+' '.join(e))