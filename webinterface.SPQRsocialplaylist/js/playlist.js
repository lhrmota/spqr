var ws, playlistItems, myUpVotes, myDownVotes;

window.onload = function() {
	loadSettingsCookies();
	selectLanguage(lang);

	// Create websocket
	ws = new WebSocket('ws://' + kodiAddress + ':' + kodiPort + '/jsonrpc');
	// Upon start
	ws.onopen = function(event) {

		requestPlaylistUpdate();

		// If undefined, ask for alias... Maybe suggest a generated id?
		console.log("userAlias" + userAlias);
		if (typeof userAlias == "undefined") {
			userAlias = window.prompt($.i18n("user-alias-prompt"), "user" + Math.floor((Math.random() * 10007)));
			saveUserAlias();
		}

		// refresh myVotes with data from the DB
		requestMyVotes();
	}

	ws.onmessage = function(event) {
		var j = JSON.parse(event.data);
		//alert(JSON.stringify(event.data));
		if (j.id) { // response  
			//console.log("got response:"+JSON.stringify(j));
			switch (j.id) {
				case "Playlist.GetItems":
					//	update playlist
					if (j.result.items) {
						//console.log("got playlist:"+JSON.stringify(j));
						addPlaylistData(j.result.items);
					}
					break;
				case "Player.GetItem":
					// update current song
					//updateCurrentSong(j.result.item);
					break;
				case "Addons.ExecuteAddon":
					break;
				default:
					alert("Unexpected response:" + alert(JSON.stringify(j)));
			}
		} else { // notification
			console.log("Notification:" + JSON.stringify(j));
			switch (j.method) {
				case "Player.OnPlay":
					// TODO should remove this function and do everything in addPlaylistData...
					//updateCurrentSong(j.params.data.item);
					break;
				case "Playlist.OnClear":
					addPlaylistData([]);
					break;
				case "Player.OnStop":
					//alert("PLAYER STOPPED");
					break;
				case "Playlist.OnAdd":
				case "Playlist.OnRemove":
					// this event is launched when a new song is added/removed... must update display
					requestPlaylistUpdate();
					break;
				case "AudioLibrary.OnUpdate":
					//TODO this is launched when playlist progresses to a new song
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
				case "Other.MyVotesUpdate":
					setMyVotes(j.params.data)
					break;
					
				default:
					alert("Other method:" + JSON.stringify(event.data));
			}
		}
	}
}

function requestMyVotes() {
	send_message(ws, "Addons.ExecuteAddon", {
		"addonid": "script.SPQR.receiveStatementsFromUser",
		"params": {
			"directive": "getMyVotes",
			"arg1": userAlias,
			"arg2": ""
		}
	});
}

function setMyVotes(data) {
   console.log("Got my votes:"+JSON.stringify(data));
   myUpVotes=data.up;
   myDownVotes=data.down;   
}

function requestPlaylistUpdate() {
	send_message(ws, "Playlist.GetItems", {
		"playlistid": 0,
		"properties": ["album", "albumartist","artist"]
	}); // Get current playlist
}

/*function sendCurrentSongUpdateRequest() {
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

function updateCurrentSong(item) {
	console.log("Got CURRENT SONG:"+JSON.stringify(item));
	
	document.getElementById("text-song-name").innerHTML = item.label;
	if (item.albumartist)
		document.getElementById("text-song-performer").innerHTML = item.albumartist[0];
	// TODO add other artists
	if (item.album)
		document.getElementById("text-song-album").innerHTML = item.album;
	// TODO program progress bar update 	
}

function addPlaylistData(jsonData) {
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
	// ADD JSON DATA TO THE TABLE AS ROWS.
	for (var i = 1; i < jsonData.length; i++) {  
		var newRow = createPlaylistEntry(jsonData[i]);
		table.appendChild(newRow);
	}

   
	// Refresh current song--- Can only be done after receiving the playlist
	// Now done when receiving playlist data	
	//sendCurrentSongUpdateRequest();
}

function createPlaylistEntry(item) {
	//console.log("SPQR creating playlist entry:"+JSON.stringify(item));

	var newPlaylistItem = {};
	newPlaylistItem.label = item.label;
	newPlaylistItem.id = item.id;
	newPlaylistItem.albumartist = item.albumartist;
	newPlaylistItem.album = item.album;

	var musicInfoDiv = document.createElement("div");
	musicInfoDiv.className = "music-info";

	// Image... Use a default icon when nothing else is available	
	var musicImgDiv = document.createElement("div");
	musicImgDiv.className = "music-img";
	var musicImg = document.createElement("img");
	musicImg.className = "fas fa-music";
	musicImg.id = "img" + item.id;
	musicImg.src="images/MaxPixel.freegreatpicture.com-Music-Icon-Button-Outline-Player-Play-Audio-2935460.svg";	
	// TODO update image
	

	musicImgDiv.appendChild(musicImg);
	musicInfoDiv.appendChild(musicImgDiv);

	// track info
	var musicNameDiv = document.createElement("div");
	musicNameDiv.className = "music-name";
	var musicNameHeader = document.createElement("h6");
	musicNameHeader.innerHTML = item.label;
	musicNameDiv.appendChild(musicNameHeader);
	var musicNameArtist = document.createElement("p");
	// sometimes album artist seems to be defined in 'albumartist', other times in 'artist'...
	// Must check where the content is... Will prioritize 'albumartist'.
	var artistsNames;
	if(item.albumartist.length>0)
		artistsNames=item.albumartist;
	else 
		artistsNames=item.artist;
	musicNameArtist.innerHTML = artistsNames[0];
	for (var i = 1; i < artistsNames.length; i++)
		musicNameArtist.innerHTML += ", " + artistsNames[i];
	musicNameDiv.appendChild(musicNameArtist);
	var musicNameAlbum = document.createElement("p");
	musicNameAlbum.innerHTML = item.album;
	musicNameDiv.appendChild(musicNameAlbum);

	musicInfoDiv.appendChild(musicNameDiv);

	// Votes...
	var thumbsUpDiv = document.createElement("div");
	var thumbsUpAnchor = document.createElement("a");
	var thumbsUpSpan = document.createElement("span");
	thumbsUpSpan.className = "glyphicon glyphicon-thumbs-up";
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
	thumbsDownSpan.className = "glyphicon glyphicon-thumbs-down";
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
	// push to global playlist	
	playlistItems.push(newPlaylistItem);
	
	return musicInfoDiv;
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

// This was being called a lot of times... That might be causing BD locks
// Removed it to see how things go... 
// Must rethink when this must be called
function requestVotesUpdate() {
	send_message(ws, "Addons.ExecuteAddon", {
		"addonid": "script.SPQR.receiveStatementsFromUser",
		"params": {
			"directive": "refreshVotes",
			"arg1": "",
			"arg2": ""
		}
	});
}

function upvote(songId) {
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

function downvote(songId) {
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
