function selectLanguage(language){
'use strict';
	

	$.i18n().locale = language;
	$.i18n().load( 'js/translation-' + $.i18n().locale + '.json', $.i18n().locale );
	console.log("Selected language:"+$.i18n().locale);
	// Translate everything...
	$('body').i18n();
}

function updateLanguage() {
	var selectedLanguage = $( '.language option:selected' ).val();
	if(selectedLanguage!=language){
		var baseAddress=window.location.href.split('?')[0];
		window.location.replace(baseAddress+"?lang="+selectedLanguage)
	}
}
// Enable debug
$.i18n.debug = true;


