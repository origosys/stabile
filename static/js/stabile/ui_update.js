define([
'dojo/_base/array',
'dojo/_base/xhr',
'dojo/topic',
'steam2/user'
], function(arrayUtil, xhr, topic, user){

var basewait = 500;
var timeout = 0;
var ui_update = {

    init: function(){
        this.subscribe();
    },

    wait: basewait,
    url: "/stabile/ui_update/" + user.username + "~ui_update",
    session: null,
    lasttimestamp: null,
    lastev: null,

    subscribe: function(){
        var self = this;
        if (!user.username) {
            ui_update.logout();
        } else if (ui_update.logged_out) {
            // do nothing
        } else {
//            console.log("GETTING", ui_update.url, "basewait", basewait, "timeout", timeout);
// Using jQuery
/*
            $.ajax({
                url: ui_update.url,
                success: function (tasks) {
                    ui_update.wait = basewait;
                    if (ui_update.publish(tasks)) ui_update.subscribe();
                },
                dataType: "json",
                timeout: timeout,
                error: function(tasks) {
                    console.log("ui_update error", tasks);
                    setTimeout(ui_update.subscribe, ui_update.wait);
                    ui_update.wait = ui_update.wait * 1.5;
                }
            })
*/
// Unsing Dojo
            xhr.get({
                "handleAs":"json",
                "timeout":timeout,
                "url":ui_update.url,
                "load": function(tasks){
                    ui_update.wait = basewait;
                    if (ui_update.publish(tasks)) ui_update.subscribe();
                },
                "error": function(tasks){
                    console.log("ui_update error", tasks);
                    setTimeout(ui_update.subscribe, ui_update.wait);
                    ui_update.wait = ui_update.wait * 1.5;
                }
            });
        }
    },

    publish: function(tasks){
        var loggedin = true;
        var dup = false;
        if (tasks && tasks.length && tasks.length>0) {
            arrayUtil.forEach(tasks, function(ev){
                console.log("received", ev);
                if (dup || (ui_update.lastev && ev.type == "serial" && ev.serial == ui_update.lastev)
                ) {
                    console.log("got duplicate task");
                    dup = true;
                } else if(ev.type == "update") {
                    if (ev.message) {
                        console.log("Also got ui message", ev);
                        IRIGO.toaster([{message: ev.message}]);
                    }
                    console.log("publishing", ev.tab + ":update", ev);
                    topic.publish(ev.tab + ":update", ev);
                } else if(ev.type == "removal"){
                    topic.publish(ev.tab + ":removal", ev);
                } else if(ev.type == "session") {
                    ui_update.url = ev.url;
                    ui_update.session = ev.session;
                } else if(ev.type == "logout"){
                    ui_update.logout(ev.message);
                    loggedin = false;
                } else if(ev.type == "message" && ev.message){
                    console.log("Got ui message", ev.message);
                    IRIGO.toaster([{message: ev.message}]);
                } else if (ev.type == "serial" && ev.serial) {
                    ui_update.lastev = ev.serial;
                }
                if (ev.download) {
                    console.log("Starting downloader UI...");
                    if (!upload.inited) upload.init();
                    var nfile = new plupload.File({name: ev.name, size: ev.size, destroy: function(){;}  });
                    nfile.url = "http://download";
                    nfile.path = ev.download;
                    uploader.files.push(nfile);
                    upload.updateList();
                    var download = new plupload.Downloader(nfile);
                    download.start();
                    uploader.start();
                }
                if ( ev.backup ) {
                    console.log("Updating missing backups...");
                    images.updateMissingBackups();
                }
//            if (ev.timestamp) ui_update.lastev = ev;
            });
        } else {
            console.log("network error", tasks);
            setTimeout(ui_update.subscribe, ui_update.wait);
            ui_update.wait = ui_update.wait * 1.5;
            return false;
        }
        return loggedin;
    },

    logout: function(msg) {
        var loginUrl = '/stabile/login';
        if (location.pathname != '' || location.hash!='') loginUrl += "?back=" + location.pathname + location.hash;
        if (!msg) msg = "Your session has timed out!";
        topic.publish("message", {
            message: msg,
            duration: 2000,
            type:"warning"
        });
        var to_login_page = function(){
            window.location.href = loginUrl;
        };
        setTimeout(to_login_page, 2000);
    },
    
    // hook: pull style observer pattern.
    // used from grid and gridDialog.
    onUpdate: function(task){}
    
};

ui_update.init();
window.ui_update = ui_update;

});
