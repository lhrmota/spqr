var kodiAddress, kodiPort,lang,userAlias;
function loadSettingsCookies() {
	kodiAddress=getCookie("kodiAddress","localhost");
	kodiPort=getCookie("kodiPort",9090);
	lang=getCookie("lang","en");
	userAlias=getCookie("userAlias",undefined);
	console.log("Lang when loading:"+lang);
	
}

function saveSettings() {
	var kodiAddressVal=document.getElementById("kodiAddress").value,
		kodiPortVal=document.getElementById("kodiPort").value,
		langVal=document.getElementById("lang").value;
		
	setCookie("kodiAddress",kodiAddressVal);
	setCookie("kodiPort",kodiPortVal);
	setCookie("lang",langVal);
	setCookie("userAlias",userAlias);
	
	// back to home
	console.log("Back2home");
	window.location.replace("./index.html"); 
}

function saveUserAlias() {
	setCookie("userAlias",userAlias);
}

function updateSettings() {
	document.getElementById("kodiAddress").value=kodiAddress;
	document.getElementById("kodiPort").value=kodiPort;
	document.getElementById("lang").value=lang;
	
	
}
function start() {
	loadSettingsCookies();
	selectLanguage(lang);
	updateSettings();
}