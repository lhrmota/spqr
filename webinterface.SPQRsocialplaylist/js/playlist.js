var ws, playlistItems, myUpVotes, myDownVotes,
// store the artist currently being browsed:  ID
browsedArtistID,
// store the album being browsed
browsedAlbumID;

window.onload = function() {
	loadSettingsCookies();
	selectLanguage(lang);

	// Create websocket
	console.log("Connecting websocket to:"+'ws://' + window.location.hostname + ':' + kodiPort + '/jsonrpc');
	ws = new WebSocket('ws://' + window.location.hostname + ':' + kodiPort + '/jsonrpc');
	// Upon start
	ws.onopen = function(event) {

		requestPlaylistUpdate();

		// If undefined, ask for alias... Maybe suggest a generated id?
		console.log("userAlias" + userAlias);
		if (typeof userAlias == "undefined") {
			userAlias = window.prompt($.i18n("user-alias-prompt"), "user" + Math.floor((Math.random() * 10007)));
			saveUserAlias();
		}

		
	}

	ws.onmessage = function(event) {
		var j = JSON.parse(event.data);
		//alert(JSON.stringify(event.data));
		if (j.id) { // response  
			//console.log("got response:"+JSON.stringify(j));
			switch (j.id) {
				case "Playlist.GetItems":
					//	update playlist
					// Ignoring: data received as GeneralUpdate
					/*if (j.result.items) {
						//console.log("got playlist:"+JSON.stringify(j));
						addPlaylistData(j.result.items);
					}*/
					break;
				case "Player.GetItem":
					// update current song
					// Ignoring: data received as GeneralUpdate, sent after each playlist change
					//updateCurrentSong(j.result.item);
					break;
				case "Addons.ExecuteAddon":
					break;
				case "AudioLibrary.GetArtists":
				   if (j.result) {
				     displayArtistsData(j.result.artists);  
				   }
				  break;
				case "AudioLibrary.GetAlbums":
				   if (j.result) {
				     displayAlbumData(j.result.albums);  
				   }
				  break;
				case "AudioLibrary.GetSongs":
				   if (j.result) {
				     displayAlbumSongs(j.result.songs);  
				   }
				  break;
				default:
					alert("Unexpected response:" + JSON.stringify(j));
			}
		} else { // notification
			console.log("Notification:" + j.method);
			switch (j.method) {
				case "Player.OnPlay":
					// Ignoring: data received as GeneralUpdate, sent after each playlist change
					//	updateCurrentSong(j.params.data.item);
					break;
				case "Playlist.OnClear":
					addPlaylistData([]);
					break;
				case "Player.OnStop":
					//alert("PLAYER STOPPED");
					clearCurrentSong();
					break;
				case "Playlist.OnAdd":
				case "Playlist.OnRemove":
					// this event is launched when a new song is added/removed... must update display
					// Ignoring: data received as GeneralUpdate, sent after each playlist change
					//	requestPlaylistUpdate();
					break;
				case "AudioLibrary.OnUpdate":
					// this is launched when playlist progresses to a new song
					// Ignoring: data received as GeneralUpdate, sent after each playlist change
				case "Application.OnVolumeChanged":
				case "GUI.OnScreensaverDeactivated":
				case "GUI.OnScreensaverActivated":
				case "Player.OnSpeedChanged":
				case "Player.OnSeek":
				case "Player.OnPause":
					// ignore
					break;
				case "System.OnSleep":
					// TODO show message? fade out contents?
					break;
				case "System.OnWake":
					// TODO reshow contents?
					break;
				case "System.OnQuit":
					// TODO deactivate page...
					break;
				case "Other.VoteUpdate":
					updateVotes(j.params.data)
					break;
			/*	case "Other.MyVotesUpdate":
				   // is this ever received? Don't think so...
					setMyVotes(j.params.data)
					break;*/
				case "Other.GeneralUpdate":
				  updateAll(j.params.data)
				  break;
				default:
					alert("Other method:" + JSON.stringify(event.data));
			}
		}
	}
}

//////////////////////////////////
// ALBUM BROWSING
//////////////////////////////////
function displayAlbumSongs(songs) {
   var table = document.getElementById("music-box");
   table.innerHTML="";
   
   // Add top element to go up
   var levelUpAnchor=document.createElement("a");
   levelUpAnchor.className="level-up";
   levelUpAnchor.href="javascript:goUpToArtistAlbums();";
   var levelUp=document.createElement("img");
   levelUp.id="level-up-icon";
   levelUp.src="images/up-arrow40.png";
   var levelUpSpan=document.createElement("span");
   levelUpSpan.innerHTML="  ..";
   levelUpAnchor.appendChild(levelUp);
   levelUpAnchor.appendChild(levelUpSpan);   
   table.appendChild(levelUpAnchor);
   for (i=0; songs && songs.length && i<songs.length;i++) {
      // must have songid as id, in order to use createPlaylistEntry
      songs[i].id=songs[i].songid;
      table.appendChild(createPlaylistEntry(songs[i],false,false));
   } 
}

function goUpToArtistAlbums() {
   browsedAlbumID=false;
   requestArtistAlbums(browsedArtistID);
}

function displayAlbumData(albums) {
   console.log("# albums:"+albums.length);
   
   var table = document.getElementById("music-box");
   table.innerHTML="";
   // Add top element to go up
   var levelUpAnchor=document.createElement("a");
   levelUpAnchor.className="level-up";
   levelUpAnchor.href="javascript:goUpToArtists();";
   var levelUp=document.createElement("img");
   levelUp.id="level-up-icon";
   levelUp.src="images/up-arrow40.png";
   var levelUpSpan=document.createElement("span");
   levelUpSpan.innerHTML="  ..";   
   levelUpAnchor.appendChild(levelUp);
   levelUpAnchor.appendChild(levelUpSpan);   
   table.appendChild(levelUpAnchor);
   for (i=0; i<albums.length;i++) {
      table.appendChild(createAlbumEntry(albums[i]));
   }
}

function goUpToArtists() {
   browsedArtistID=false;
   document.getElementById("level-up-icon").style.visibility="hidden";
   showArtists();
}
function createAlbumEntry(album) {
	var musicInfoDiv = document.createElement("div");
	musicInfoDiv.className = "music-info";

	// Image... Use a default icon when nothing else is available	
	var musicImgDiv = document.createElement("div");
	musicImgDiv.className = "music-img";
	var musicImg = document.createElement("img");
	musicImg.id = "imgAlbum" + album.albumid;	
	musicImg.src="images/music-icon40.png"
	// TODO update image
	

	musicImgDiv.appendChild(musicImg);
	musicInfoDiv.appendChild(musicImgDiv);

	// album info
	var albumNameDiv = document.createElement("div");
	albumNameDiv.className = "music-name"
	var albumAnchor = document.createElement("a");
	albumAnchor.href="javascript:requestAlbumSongs("+album.albumid+")";
	var albumNameHeader = document.createElement("h5");
	albumNameHeader.innerHTML = album.label;
	albumAnchor.appendChild(albumNameHeader);
	albumNameDiv.appendChild(albumAnchor);
	musicInfoDiv.appendChild(albumNameDiv);

	// Votes... Should have a vote at album level? Not obvious... Probably not.
	
	return musicInfoDiv;
}

function requestAlbumSongs(albumid) {
   // update album being browsed
   browsedAlbumID=albumid;
      
   send_message(ws, "AudioLibrary.GetSongs", {
       "filter": {"albumid": browsedAlbumID}
       //,  "properties": ["songid"]
	});
}

function displayArtistsData(artists) {
   console.log("# artists:"+artists.length);
   
   var table = document.getElementById("music-box");
   for (i=0; i<artists.length;i++) {
      table.appendChild(createArtistEntry(artists[i]));
   }
}

function createArtistEntry(artist) {
	var musicInfoDiv = document.createElement("div");
	musicInfoDiv.className = "music-info";

	// Image... Use a default icon when nothing else is available	
	var musicImgDiv = document.createElement("div");
	musicImgDiv.className = "music-img";
	var musicImg = document.createElement("img");
	musicImg.id = "img" + artist.artistid;	
	musicImg.src="images/music-icon40.png"
	// TODO update image
	

	musicImgDiv.appendChild(musicImg);
	musicInfoDiv.appendChild(musicImgDiv);

	// artist info
	var artistNameDiv = document.createElement("div");
	artistNameDiv.className = "music-name";
	var artistAnchor = document.createElement("a");
	artistAnchor.href="javascript:requestArtistAlbums("+artist.artistid+")";
	var artistNameHeader = document.createElement("h5");
	artistNameHeader.innerHTML = artist.label;
	artistAnchor.appendChild(artistNameHeader);
	artistNameDiv.appendChild(artistAnchor);
	musicInfoDiv.appendChild(artistNameDiv);

	// Votes... Should have a vote at artist level?
	
		
	return musicInfoDiv;
}
function showPlaylist() {
   clearMusicBox();
   // highlight option   
   document.getElementById("playlist-menu").className="menu-highlight";
   requestPlaylistUpdate();
}

function clearMusicBox() {
   document.getElementById("music-box").innerHTML="";
   // also clear menu highlights
   document.getElementById("playlist-menu").className="menu-normal";
   //document.getElementById("songs-menu").className="menu-normal";
   document.getElementById("artists-menu").className="menu-normal";
}



function showArtists(){
   clearMusicBox();
   // highlight option   
   document.getElementById("artists-menu").className="menu-highlight";
   requestArtistsUpdate();
}

function requestArtistsUpdate() {
   // was there an artist being browsed before?
   if(browsedArtistID)
      requestArtistAlbums(browsedArtistID);
   else 
      requestAllArtists();
}

function requestArtistAlbums(artistid) {
   // update artist being browsed
   browsedArtistID=artistid;
   // Can't manage to filter through artistID... Will do it through artist name...
   send_message(ws, "AudioLibrary.GetAlbums", {
       "filter": {"artistid":browsedArtistID}
		//,		"properties": ["artist","artistid"]
	});
}

function requestAllArtists() {
   send_message(ws, "AudioLibrary.GetArtists", {
		"albumartistsonly": true
		//,		"properties": ["artist","artistid"]
	});
}

function showSongs(){
   clearMusicBox();
   // highlight option   
   document.getElementById("songs-menu").className="menu-highlight";
   requestSongsUpdate();
}

function requestSongsUpdate() {
   //TODO
}

//////////////////////////////////
// VOTES
//////////////////////////////////


function setMyVotes(data) {
   console.log("Got my votes:"+JSON.stringify(data));
   myUpVotes=data.up;
   myDownVotes=data.down;   
}

/* Not necessary: comes as first playlist entry
function sendCurrentSongUpdateRequest() {
	send_message(ws, "Player.GetItem", {
		"playerid": 0
	}); // Get song currently playing
}*/

function updateVotes(data) {
	console.log("Updating votes:" + JSON.stringify(data));

	var upVotes = data.up;

	for (var key in upVotes) {
		var upVoteSpan = document.getElementById("upCount" + key);
		//console.log("Updating votes:upCount" + key)
		if(upVoteSpan) upVoteSpan.innerHTML = upVotes[key];
	}

	var downVotes = data.down;

	for (var key in downVotes) {
		var downVoteSpan = document.getElementById("downCount" + key);
		//console.log("Updating votes:downCount" + key)
		if(downVoteSpan) downVoteSpan.innerHTML = downVotes[key];
	}
}

// After updating the playlist, refresh display of own votes.
function refreshMyVotes() {
	console.log("Refreshing my votes:" + myUpVotes + ";" + myDownVotes);
	for (var songid in myUpVotes) {
		console.log("Refreshing up vote:" + "thumbsup" + myUpVotes[songid]);
		if(document.getElementById("thumbsup" + myUpVotes[songid])) document.getElementById("thumbsup" + myUpVotes[songid]).style.color = "Lime";
	}
	for (var songid in myDownVotes)
		if(document.getElementById("thumbsdown" + myDownVotes[songid])) document.getElementById("thumbsdown" + myDownVotes[songid]).style.color = "red";

}

// This was being called a lot of times... That might be causing BD locks
// Removed it to see how things go... 
// Must rethink when this must be called... Maybe never: votes should be broadcast each time a 
// new vote is received by Kodi
/*function requestVotesUpdate() {
	send_message(ws, "Addons.ExecuteAddon", {
		"addonid": "script.SPQR.receiveStatementsFromUser",
		"params": {
			"directive": "refreshVotes",
			"arg1": "",
			"arg2": ""
		}
	});
}
// This is probably also unnecessary: own votes are stored locally...
// Maybe there will be a problem when page is refreshed or closed? Will try to receive these in initial info
function requestMyVotes() {
	send_message(ws, "Addons.ExecuteAddon", {
		"addonid": "script.SPQR.receiveStatementsFromUser",
		"params": {
			"directive": "getMyVotes",
			"arg1": userAlias,
			"arg2": ""
		}
	});
}*/

function upvote(songId) {
   // TODO avoid duplicate votes by same user... Could simply check if already present? Will do so...
   // Later one could cancel vote when clicking again...
   if(!myUpVotes.includes(songId) ){	
   	myUpVotes.push(songId);
   	//	console.log("Upvoting:"+songId);
   	refreshMyVotes();
   	send_message(ws, "Addons.ExecuteAddon", {
   		"addonid": "script.SPQR.receiveStatementsFromUser",
   		"params": {
   			"directive": "upvote",
   			"arg1": songId.toString(),
   			"arg2": userAlias
   		}
   	});
   }
}

function downvote(songId) {
   // TODO avoid duplicate votes by same user...  Could simply check if already present? Will do so...
   // Later one could cancel vote when clicking again...
	if(!myDownVotes.includes(songId) ){	
   	myDownVotes.push(songId);
   	refreshMyVotes();
   	//	console.log("Downvoting:"+songId);
   	send_message(ws, "Addons.ExecuteAddon", {
   		"addonid": "script.SPQR.receiveStatementsFromUser",
   		"params": {
   			"directive": "downvote",
   			"arg1": songId.toString(),
   			"arg2": userAlias
   		}
   	});
   }
}

////////////////////////////////////////////////
// PLAYLIST DISPLAY
////////////////////////////////////////////////
function updateAll(data) {
   addPlaylistData(data.playlist);
   updateVotes(data.allVotes);
   // will only update when votes are present and refer to my user alias 
   if(data.user && data.user==userAlias){
      myUpVotes=data.myVotes.up;
      myDownVotes=data.myVotes.down;
      refreshMyVotes();
   }
}
function requestPlaylistUpdate() {
	send_message(ws, "Addons.ExecuteAddon", {
		"addonid": "script.SPQR.receiveStatementsFromUser",
		"params": {
			"directive": "getPlaylist",
			"arg1": userAlias,
			"arg2": ""
		}
	});
	// Was before:
	/*"Playlist.GetItems", {
		"playlistid": 0,
		"properties": ["album", "albumartist","artist"]
	}); // Get current playlist
	*/
}

function clearCurrentSong() {
	document.getElementById("text-song-name").innerHTML = $.i18n("nothing-playing");
	document.getElementById("text-song-performer").innerHTML ="";
	document.getElementById("text-song-album").innerHTML = "";
}
function updateCurrentSong(item) {
	console.log("Got CURRENT SONG:"+JSON.stringify(item));
	if(item){
		document.getElementById("text-song-name").innerHTML = item.label;
		var artistsNames;
   	if(item.albumartist && item.albumartist.length>0)
	  		artistsNames=item.albumartist;
		else 
	  		artistsNames=item.artist;
		document.getElementById("text-song-performer").innerHTML = artistsNames[0];
		for (var i = 1; i < artistsNames.length; i++)
	  		document.getElementById("text-song-performer").innerHTML += ", " + artistsNames[i];
	
		if (item.album)
			document.getElementById("text-song-album").innerHTML = item.album;
		// TODO program progress bar update
	} 	
}

function addPlaylistData(jsonData) {
   if (jsonData) {
   	//reset playlist
   	playlistItems = [];
   
   	// function adapted from
   	// https://www.encodedna.com/javascript/populate-json-data-to-html-table-using-javascript.htm 
   	// EXTRACT VALUE FOR HTML HEADER.     
   	var col = [];
   	for (var i = 0; i < jsonData.length; i++) {
   		for (var key in jsonData[i]) {
   			if (col.indexOf(key) === -1) {
   				col.push(key);
   			}
   		}
   	}
   
   	// clear current playlist
   	var table = document.getElementById("music-box");
   	table.innerHTML = "";
   
   	// first line is dealt differently, as it has a special place and interface...
   	updateCurrentSong(jsonData[0]);
   	removeCurrentSongFromMyVotes(jsonData[0]);
   	
   	//Must check if playlist is being displayed... Only in that case will the other songs be shown.
   	if(showingPlaylist()){ 
      	// ADD JSON DATA TO THE TABLE AS ROWS.
   	  for (var i = 1; i < jsonData.length; i++) {
   	     // Store in playlist
   	     var newPlaylistItem = {};
   	     newPlaylistItem.label = jsonData[i].label;
   	     newPlaylistItem.id = jsonData[i].id;
   	     newPlaylistItem.albumartist = jsonData[i].albumartist;
           newPlaylistItem.album = jsonData[i].album;  
           // push to global playlist	
           playlistItems.push(newPlaylistItem);	     
   	     
   	     var newRow = createPlaylistEntry(jsonData[i],true,true);
   		  table.appendChild(newRow);
   	  }
   	}
   }
	// Refresh current song--- Can only be done after receiving the playlist
	// Now done when receiving playlist data	
	//sendCurrentSongUpdateRequest();
}

function removeCurrentSongFromMyVotes(songData) {
	var indexToRemove=-1;
	for(var i=0; myUpVotes && i!=myUpVotes.length;i++)
		if(songData && songData.id && myUpVotes[i]==songData.id){
			indexToRemove=i;
			break;
		}
	if(indexToRemove!=-1)
		myUpVotes.splice(indexToRemove, 1);
	
	indexToRemove=-1;
	for(i=0; myDownVotes && i!=myDownVotes.length;i++)
		if(myDownVotes[i]==songData.id){
			indexToRemove=i;
			break;
		}
	if(indexToRemove!=-1)
		myDownVotes.splice(indexToRemove, 1);
}

function showingPlaylist() {
   return document.getElementById("playlist-menu").className=="menu-highlight";
}

// showArtist,showAlbum are boolean, to decide if album and artist info is shown
function createPlaylistEntry(item,showArtist,showAlbum) {
	//console.log("SPQR creating playlist entry:"+JSON.stringify(item));

	var musicInfoDiv = document.createElement("div");
	musicInfoDiv.className = "music-info";

	// Image... Use a default icon when nothing else is available	
	var musicImgDiv = document.createElement("div");
	musicImgDiv.className = "music-img";
	var musicImg = document.createElement("img");
	musicImg.className = "fa fa-music";
	musicImg.id = "img" + item.id;
	// wasn't showing in remote clients,,, Permissions seem ok...
	musicImg.src="images/Play-Audio40.jpg";	
	// TODO update image
	

	musicImgDiv.appendChild(musicImg);
	musicInfoDiv.appendChild(musicImgDiv);

	// track info
	var musicNameDiv = document.createElement("div");
	musicNameDiv.className = "music-name";
	var musicNameHeader = document.createElement("h6");
	musicNameHeader.innerHTML = item.label;
	musicNameDiv.appendChild(musicNameHeader);
	if(showArtist){
   	var musicNameArtist = document.createElement("p");
	  // sometimes album artist seems to be defined in 'albumartist', other times in 'artist'...
	  // Must check where the content is... Will prioritize 'albumartist'.
     var artistsNames;
	  if(item.albumartist && item.albumartist.length>0)
	  	  artistsNames=item.albumartist;
	  else 
		  artistsNames=item.artist;
	  if(artistsNames && artistsNames.length>0) musicNameArtist.innerHTML = artistsNames[0];
	  for (var i = 1; artistsNames && i < artistsNames.length; i++)
		 musicNameArtist.innerHTML += ", " + artistsNames[i];
	  musicNameDiv.appendChild(musicNameArtist);
	 }
	 if(showAlbum){
   	var musicNameAlbum = document.createElement("p");
	   musicNameAlbum.innerHTML = item.album;
	   musicNameDiv.appendChild(musicNameAlbum);
   }
	musicInfoDiv.appendChild(musicNameDiv);

	// Votes...
	var thumbsUpDiv = document.createElement("div");
	var thumbsUpAnchor = document.createElement("a");
	var thumbsUpSpan = document.createElement("span");
	thumbsUpSpan.className = "fa fa-thumbs-up";
	thumbsUpSpan.setAttribute("aria-hidden", true);
	thumbsUpSpan.id = "thumbsup" + item.id;
	thumbsUpAnchor.appendChild(thumbsUpSpan);
	thumbsUpAnchor.href = "javascript:upvote(" + item.id + ");"
	thumbsUpDiv.appendChild(thumbsUpAnchor);
	var thumbsUpCountSpan = document.createElement("span");
	thumbsUpCountSpan.className = "badge";
	thumbsUpCountSpan.id = "upCount" + item.id;
	thumbsUpCountSpan.innerHTML = "0";
	thumbsUpDiv.appendChild(thumbsUpCountSpan);
	musicInfoDiv.appendChild(thumbsUpDiv);
	var thumbsDownDiv = document.createElement("div");
	var thumbsDownAnchor = document.createElement("a");
	var thumbsDownSpan = document.createElement("span");
	thumbsDownSpan.className = "fa fa-thumbs-down";
	thumbsDownSpan.setAttribute("aria-hidden", true);
	thumbsDownSpan.id = "thumbsdown" + item.id;
	thumbsDownAnchor.appendChild(thumbsDownSpan);
	thumbsDownAnchor.href = "javascript:downvote(" + item.id + ");"
	thumbsDownDiv.appendChild(thumbsDownAnchor);
	var thumbsDownCountSpan = document.createElement("span");
	thumbsDownCountSpan.className = "badge";
	thumbsDownCountSpan.id = "downCount" + item.id;
	thumbsDownCountSpan.innerHTML = "0";
	thumbsDownDiv.appendChild(thumbsDownCountSpan);
	musicInfoDiv.appendChild(thumbsDownDiv);
	// menu. Replaced by links on the thumbs	
	/*var ellipsisIcon=document.createElement("i");
      ellipsisIcon.className="fa fa-ellipsis-v";
      musicInfoDiv.appendChild(ellipsisIcon);
    musicInfoDiv.appendChild(createMenuForSong(item.id));
    */
	
	
	return musicInfoDiv;
}



/////////////////////////////////////////////////////
// MESSAGES TRANSMISSION
/////////////////////////////////////////////////////
function send_message(webSocket, method, params, id) {
	if (!id) id = method;
	var msg = {
		"jsonrpc": "2.0",
		"method": method,
		"id": id
	};
	if (params) {
		msg.params = params;
	}
	console.log("Sending:" + JSON.stringify(msg))
	webSocket.send(JSON.stringify(msg));
}

function sendNotify() {
	send_message(ws, "JSONRPC.NotifyAll", {
		"sender": "button",
		"message": "Test notification",
		"data": {
			"item": "test"
		}
	});
}


// menu. Replaced by links on the thumbs
/*
function createMenuForSong(songid) {
    // from https://getbootstrap.com/docs/3.3/components/
    var menu=document.createElement("div");
    menu.className="dropup"; // Up because of last item's menu: was not showing
    
    var button=document.createElement("button");
    button.className="btn btn-default dropdown-toggle";
    button.type="button";
    button.id="dropdownMenu"+songid;
    button.setAttribute("data-toggle","dropdown");
    button.setAttribute("aria-haspopup",true);
    button.setAttribute("aria-expanded",true);
    button.innerHTML="...</span>";
    menu.appendChild(button);   
    
    var ul=document.createElement("ul");
    ul.className="dropdown-menu dropdown-menu-right";
    ul.setAttribute("aria-labelledby","dropdownMenu"+songid);
    var liUpvote=document.createElement("li");
    var anchorUpvote=document.createElement("a");
    anchorUpvote.href="javascript:upvote("+songid+");";
    anchorUpvote.innerHTML=$.i18n( "Upvote!");
    liUpvote.appendChild(anchorUpvote);
    ul.appendChild(liUpvote);
    var liDownvote=document.createElement("li");
    var anchorDownvote=document.createElement("a");
    anchorDownvote.href="javascript:downvote("+songid+");";
    anchorDownvote.innerHTML=$.i18n( "Downvote!");
    liDownvote.appendChild(anchorDownvote);
    ul.appendChild(liDownvote);
    menu.appendChild(ul);
    
    return menu;
}
*/