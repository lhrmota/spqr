import xbmc
import xbmcgui
import sys
import urlparse
import sqlite3
from sqlite3 import Error
import xbmcaddon
import os
import xbmcvfs
import json
import spqr_library   

# code from http://www.sqlitetutorial.net/sqlite-python/create-tables/
def setupDB():
    database = os.path.join(profile_dir,"spqr.db")
    	
#    xbmc.log("SPQR DB file:"+database)
 
    # create a database connection
    conn = create_connection(database)
    if conn is None:
        xbmc.log("SPQR Error: cannot create the database connection.")
    else:
       # to be used outside this function
       return conn
      
# Database code
def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    try:
     conn = sqlite3.connect(db_file, timeout=30)
     return conn
    except Error as e:
      xbmc.log("SPQR Error: cannot create connection"+' '.join(e))
    return None

def insertVote(conn,songid,user,value):
   """ insert new vote on the corresponding table
   :param songid: song identifier
   :param user: user identifier
   :return: void
   """
   if conn is not None:
      try:	
         sqlText="""INSERT INTO unfulfilledVotes (user,songid,value,date) VALUES (?,?,?,DATE('now'))"""
         xbmc.log("SPQR Trying to insert:"+sqlText)
         c = conn.cursor()
         c.execute(sqlText,(user,songid,value))
         conn.commit()
         # launch notification to update clients
         notifyVotes(conn)
         # immediately deorder playlist? Maybe not, could cause instability with many users...
      except Error as e:
         xbmc.log("SPQR Error: cannot insert into votes: "+' '.join(e))
   else:
      xbmc.log("SPQR Error: cannot insert into votes: no connection available")

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
         
def notifyVotes(conn):
   """Notify all subscribed connections that votes were altered"""
   xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "JSONRPC.NotifyAll", "id":"JSONRPC.NotifyAll","params":{"sender":"SPQR","message":"VoteUpdate","data":'+json.dumps(getAllVotes(conn))+' }}')
   
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

def sendPlaylist(conn,user):
   """Send all relevant info to setup initial playlist display: send playlist, global votes and own votes
   :param conn: DB connection
   :param user: the user id"""
   try:  
      jsonData={
        "playlist":spqr_library.getCurrentPlaylist(),
        "allVotes":getAllVotes(conn),
        "myVotes":getMyVotes(conn,user)}
      xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "JSONRPC.NotifyAll", "id":"JSONRPC.NotifyAll","params":{"sender":"SPQR","message":"GeneralUpdate","data":'+json.dumps(jsonData)+' }}')
   except Error as e:
         xbmc.log("SPQR Error: sendPlaylist failed: "+' '.join(e))
   
   
if __name__ == '__main__':
# Launch point
   xbmc.log("SPQR Starting receive statements addon...")

   # Get profile dir
   params = urlparse.parse_qs('&'.join(sys.argv[1:]))
   #xbmc.log("Keys:"+str(len(params.keys()))+":"+str(len(params)))

   profile_dir = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')).decode('utf-8')
   
   

   if "directive" in params:
       xbmc.log("SPQR Directive:"+params["directive"][0])
       conn=setupDB()
       if params["directive"][0]=="upvote":
          insertVote(conn,params["arg1"][0],params["arg2"][0],1)
       else:
          if params["directive"][0]=="downvote":
             insertVote(conn,params["arg1"][0],params["arg2"][0],-1)
          else:
             # These next two should not be being used anymore...
             # Will write to console, but later must be removed
             if params["directive"][0]=="refreshVotes":
                 xbmc.log("SPQR Unexpected Directive")
             else:
                if params["directive"][0]=="getMyVotes":
                   xbmc.log("SPQR Unexpected Directive")
                else:
                   if params["directive"][0]=="getPlaylist":
                      sendPlaylist(conn,params["arg1"][0])
                   else:
                      xbmc.log("SPQR Unexpected directive:"+params["directive"][0])
       conn.close()
   xbmc.log("SPQR ending receive statements addon...")
