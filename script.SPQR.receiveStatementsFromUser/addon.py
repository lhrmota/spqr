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

class EventMonitor(xbmc.Player):
    # from forum.kodi.tv/showthread.php?tid338471
    def __init__ (self):
        monitor=xbmc.Monitor()
        xbmc.Player.__init__(self)
        xbmc.log("EventMonitor launched")
        #while not monitor.abortRequested():
        #    if monitor.waitForAbort(10):
        #        break
    
    def onPlayBackStarted(self):
        xbmc.log("Spoted onPlayBackStarted")
        reorderPlayList()
    
    def onQueueNextItem(self):
        xbmc.log("Spoted onQueueNextItem")
    
    def onAVStarted(self):
        xbmc.log("Spoted onAVStarted ")


def reorderPlayList():
    """ will reorder playlist according to present votes.
    """
    # move next song's votes to fulfilledVotes

# code from http://www.sqlitetutorial.net/sqlite-python/create-tables/
def setupDB():
    database = os.path.join(profile_dir,"spqr.db")
    	
    xbmc.log("DB file:"+database)
    
    # value should be 1 or -1, depending on being up or downvote. No booleans in SQLite! 
    sql_create_unfulfilledvotes_table = """ CREATE TABLE IF NOT EXISTS unfulfilledVotes (
             user text NOT NULL,
             songid integer NOT NULL,
             value integer NOT NULL);"""
    sql_create_fulfilledvotes_table = """CREATE TABLE IF NOT EXISTS fulfilledVotes (
             user text NOT NULL,
             songid integer NOT NULL,
             value integer NOT NULL,
             songorder integer NOT NULL); """
 
    # create a database connection
    conn = create_connection(database)
    if conn is not None:
        # create votes tables
        create_table(conn, sql_create_unfulfilledvotes_table)
        create_table(conn, sql_create_fulfilledvotes_table)
    else:
        xbmc.log("Error: cannot create the database connection.")
        
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
     conn = sqlite3.connect(db_file)
     return conn
    except Error as e:
      xbmc.log("Error: cannot create connection"+' '.join(e))
      print(e)
    return None

def create_table(conn, create_table_sql):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
        conn.commit()
    except Error as e:
      xbmc.log("Error: cannot create table:"+' '.join(e))
      print(e)

def insertVote(conn,songid,user,value):
   """ insert new vote on the corresponding table
   :param songid: song identifier
   :param user: user identifier
   :return: void
   """
   if conn is not None:
      try:	
         sqlText="""INSERT INTO unfulfilledVotes (user,songid,value) VALUES (?,?,?)"""
         xbmc.log("Trying to insert:"+sqlText)
         c = conn.cursor()
         c.execute(sqlText,(user,songid,value))
         conn.commit()
         xbmc.log("Insertion finished")
         # launch notification to update clients
         notifyVotes(conn)
         # immediately deorder playlist? Maybe not, could cause instability with many users...
      except Error as e:
         xbmc.log("Error: cannot insert into votes"+' '.join(e))
         print(e)
   else:
      xbmc.log("Error: cannot insert into votes: no connection available")

def notifyVotes(conn):
   """Notify all subscribed connections that votes were altered"""
   try:
   	# get all votes from DB, grouped by songid
   	# must separately get up and down votes
      cur = conn.cursor()
      cur.execute("""SELECT songid,count(*) AS count FROM unfulfilledVotes WHERE value=1 GROUP BY songid """)
      
      jsonDataUp={}
      rows = cur.fetchall()
      for row in rows:
         #xbmc.log("Row:"+' '.join(map(str,row)))
         xbmc.log("Row:"+str(row[0])+":"+str(row[1]))
         jsonDataUp[row[0]]=row[1]
      
      # down votes
      cur.execute("""SELECT songid,count(*) AS count FROM unfulfilledVotes WHERE value=-1 GROUP BY songid """)
      jsonDataDown={}
      rows = cur.fetchall()
      for row in rows:
         #xbmc.log("Row:"+' '.join(map(str,row)))
         #xbmc.log("Row:"+str(row[0])+":"+str(row[1]))
         jsonDataDown[row[0]]=row[1]


      jsonData={"up":jsonDataUp,"down":jsonDataDown}

      xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "JSONRPC.NotifyAll", "id":"JSONRPC.NotifyAll","params":{"sender":"SPQR","message":"VoteUpdate","data":'+json.dumps(jsonData)+' }}')
   except Error as e:
         xbmc.log("Error: notifyVotes failed: "+' '.join(e))

def getMyVotes(conn,user):	
   """Get all votes vy specified user
   :param conn: DB connection
   :param user: the user id"""
   try:
      xbmc.log("Getting votes for:"+user)
      cur = conn.cursor()
      cur.execute("""SELECT songid, value FROM unfulfilledVotes WHERE user=? """,(user,))
         
      jsonData={"up":[],"down":[]}
      rows = cur.fetchall()
      for row in rows:
         #xbmc.log("Row:"+' '.join(map(str,row)))
         #xbmc.log("Row:"+str(row[0])+":"+str(row[1]))
         if row[1]==1:#upvote
            jsonData["up"].append(row[0])
         else:#downvote
            jsonData["down"].append(row[0])                 
      xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "JSONRPC.NotifyAll", "id":"JSONRPC.NotifyAll","params":{"sender":"SPQR","message":"MyVotesUpdate","data":'+json.dumps(jsonData)+' }}')
   except Error as e:
         xbmc.log("Error: getMyVotes failed: "+' '.join(e))
   
def select_all_votes(conn):
    """
    Query all rows in the votes table and log their value
    :param conn: the Connection object
    :return:
    """
    try:
      cur = conn.cursor()
      cur.execute("""SELECT count(*) FROM params["directive"][0]""")
    	
      rows = cur.fetchall()
    	
      for row in rows:
         xbmc.log(row)
    except Error as e:
         xbmc.log("Error: cannot select votes"+' '.join(e))

# Launch point
if __name__ == '__main__':
   # Get profile dir
   xbmc.log("Starting addon...")

   params = urlparse.parse_qs('&'.join(sys.argv[1:]))
   #xbmc.log("Keys:"+str(len(params.keys()))+":"+str(len(params)))

   # Check for need to create profile dir
   profile_dir = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')).decode('utf-8')
   if xbmcvfs.exists(profile_dir):
       xbmc.log("Profile dir:"+profile_dir)
   else:
       xbmcvfs.mkdir(profile_dir)
       xbmc.log("Created profile dir:"+profile_dir)
  
   

   if "directive" in params:
       xbmc.log("Directive:"+params["directive"][0])
       conn=setupDB()
       if params["directive"][0]=="upvote":
          insertVote(conn,params["arg1"][0],params["arg2"][0],1)
       else:
          if params["directive"][0]=="downvote":
             insertVote(conn,params["arg1"][0],params["arg2"][0],-1)
          else:
             if params["directive"][0]=="refreshVotes":
                 notifyVotes(conn)
             else:
                if params["directive"][0]=="getMyVotes":
                   getMyVotes(conn,params["arg1"][0])
                else:
                   xbmc.log("Unexpected directive:"+params["directive"][0])
                   
   monitor=None
   xbmc.log("Will launch monitor..."+str(monitor))
   if monitor!=None:
      monitor=EventMonitor() # launching event monitor 
   	
