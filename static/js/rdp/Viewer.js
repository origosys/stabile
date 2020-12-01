define([
'dojo/_base/lang',
'dojo/_base/declare',
'dojo/data/ObjectStore',
'dojo/store/Memory',
'dojo/dom-construct',
'java/applet'
], function(lang, declare, ObjectStore, Memory, domConstruct, applet){

    var Viewer = declare('rdp.Viewer', null, {

        started: false,
        title: null,
        host: null,
        port: null,
        node: null,
        archive: require.toUrl("rdp/resources/rdp.jar"),
     
        constructor: function(args){
            lang.mixin(this, args);
            
            this.id = 'rdp-viewer-' + Viewer.id;
            Viewer.id = Viewer.id + 1;
            if(typeof Viewer.viewers[this.id] !== 'undefined'){
                domConstruct.destroy(this.id);
            }
            Viewer.viewers[this.id] = this;
        },
     
        start: function(){
            if(this.started){
                return;
            }
     
            applet.inject(this.node, {
                archive: this.archive,
                cache_archive: this.archive,
                cache_version: "3",
                code: "net.propero.rdp.applet.RdpApplet",
                callback: 'rdp.Viewer.javatrigger',
                port: this.port,
                host: this.host,
                title: this.title,
                id: this.id,
                keymap: Viewer.keymap,
                // if this doesn't work everywhere
                // this.archive.uri + '?v=' + new Date().getTime(),
                classloader_cache: 'false',
                log_level: "info"
            });
        },
     
        stop: function(){
            this.onDestroy();
        },
     
        onDestroy: function(){
            console.log('destroying');

            domConstruct.destroy(this.id);
        },
                             
        onStart: function(){
            console.log('onStart event');

        }
    });

    Viewer.viewers = {};
    Viewer.id = 0;
    Viewer.keymap = 'en-us';

    Viewer.INIT = 'display:init';     
    Viewer.DESTROY = 'display:destroy';

    Viewer.javatrigger = function(eventname, id, msg){
        console.log('rdp::Viewer::javatrigger', arguments);
        var self = this;
        var display = self.viewers[id];
     
        function f(){
            switch('display:' + eventname){
            case self.INIT:
                display.onStart();
                break;
            case self.DESTROY:
                display && display.onDestroy();
                break;
            default:
                console.log('WTF? event:' + eventname + " shouldn't happen");
            }
        }
        setTimeout(f, 0);
    };
     
     var store = new Memory({
         data: [
             {id: "en-us", label: "us" },
             {id:"ar", label:"ar"},
             {id:"da",label:"da"},
             {id:"de",label:"de"},
             {id:"en-gb",label:"en-gb"},
             {id:"es", label:"es"},
             {id:"fi",label:"fi"},
             {id:"fr",label:"fr"},
             {id:"fr-be","label":"fr-be"},
             {id:"hr",label:"hr"},
             {id:"it",label:"it"},
             {id:"ja",label:"ja"},
             {id:"lt",label:"lt"},
             {id:"lv",label:"lv"},
             {id:"mk",label:"mk"},
             {id:"no",label:"no"},
             {id:"pl", label:"pl"},
             {id:"pt", label:"pt"},
             {id:"pt-br", label:"pt-br"},
             {id:"ru",label:"ru"},
             {id:"sl",label:"sl"},
             {id:"sv",label:"sv"},
             {id:"tk",label:"tk"},
             {id:"tr",label:"tr"}
    ]});

    Viewer.keyboardLayouts = new ObjectStore({ objectStore: store });
    return Viewer;
});


