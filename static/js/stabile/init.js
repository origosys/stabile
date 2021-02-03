// Obsolete - not used
define([
'stabile/ui_update',
"dojo/ready",
"dojo/parser",
"dojo/cookie",
"dojo/dom",
"dojo/topic",
"dijit/form/Select",
"dojox/widget/Toaster",
'steam2/user',   
'java/applet',
'stabile/activity',
'stabile/ClearTextBox',
'stabile/backbutton',
'stabile/home',
'steam2/xhrDecorator',
'stabile/menu'

], function(ui_update, ready, parser, cookie, dom, topic, Select, Toaster, user
        ){
        parser.parse();
        if (dom.byId('tktuser')) dom.byId('tktuser').innerHTML = user.tktuser;
        if (dom.byId('tktuser')) dom.byId('tktuser').title = "User privileges: " + user.userprivileges;

        dojo.connect(window, 'onkeypress', function(evt) {
            key = evt.keyCode;
            if (key == dojo.keys.ESCAPE) {
                console.debug("Escape trapped !!");
                dojo.stopEvent(evt);
            } else if (key == dojo.keys.BACKSPACE) {
                if (evt.target.nodeName != "INPUT" && evt.target.nodeName != "TEXTAREA") {
                    dojo.stopEvent(evt);
                    console.debug("Backspace trapped !!", evt);
                }
            }
        });

});

