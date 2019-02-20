# definition of some functions used in different other files
import xbmc
import json

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