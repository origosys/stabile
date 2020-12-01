define([
'dojo/_base/declare',
'dojo/_base/lang',
'dojo/dom-construct',
'java/applet'
], function(declare, lang, domConstruct, applet){

var Viewer = declare('vnc.Viewer', null, {
            
    started: false,

    title: null,
    host: null,
    port: null,
    node: null,
    archive: require.toUrl("vnc/resources/vnc.jar"),

    constructor: function(args){
        lang.mixin(this, args);
        
        this.id = 'vnc-viewer-' + Viewer.id;
        Viewer.id = Viewer.id + 1;
        if(typeof Viewer.viewers[this.id] !== 'undefined'){
            console.log('Viewer already present');
            domConstruct.destroy(this.id);
        }
        Viewer.viewers[this.id] = this;
    },

    start: function(){
        if(this.started){
            console.log('error already started');
            return;
        }

        var args = {
            port: this.port,
            host: this.host,
            title: this.title,
            id: this.id,
            log_level:'info'
        };
    
        args.archive = this.archive;
        args.cache_archive = this.archive;
        args.cache_version = "1";
        args.code = 'com.tigervnc.VncApplet';
        args.new_window = "Yes";
        args.show_controls = 'no';
        args.callback = 'vnc.Viewer.javatrigger';

        // NOTE: 
        // Static variables are shared accross applets
        // tigervnc uses static variables so it fucks up.
        // Disabling the classloader cache
        args.classloader_cache = 'false';
        applet.inject(this.node, args);
    },

    stop: function(){
        this.onDestroy();
    },

    onDestroy: function(){
        var self = this;
        function doIt(){
            domConstruct.destroy(this.id);
        }
        setTimeout(doIt, 0);
    },
                         
    onStart: function(){
        
    }
});

Viewer.viewers = {};
Viewer.INIT = 'display:init';
Viewer.DESTROY = 'display:destroy';

Viewer.id = 0;
Viewer.javatrigger = function(evtName, id, msg){
    console.log('vnc::Viewer::javatrigger', arguments);
    var self = this;
    var display = self.viewers[id];

    function f(){
        switch('display:' + evtName){
        case self.INIT:
            display.onStart();
            break;
        case self.DESTROY:
            display && display.onDestroy();
            break;
        default:
            console.log('WTF? event:' + evtName + " shouldn't happen");
        }
    }
    setTimeout(f, 0);
};

return Viewer;

});

