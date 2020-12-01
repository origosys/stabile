define([
'dojo/_base/declare',
'dojo/_base/connect',           
'dojo/_base/lang',
'vnc/Viewer',
'rdp/Viewer'
], function(declare, connect, lang, VncViewer, RdpViewer){
    
    return declare('evd.Display', null, {
        // A wrapper around rdp and vnc.
        
        viewer: null,

        constructor: function(args){
            if(args.type == 'rdp'){
                this.viewer = new RdpViewer(args);
            }
            else if(args.type == 'vnc'){
                this.viewer = new VncViewer(args);
            }
            else{
                throw 'display::start no display type supplied';
            }
     
            connect.connect(this.viewer, 'onDestroy', lang.hitch(this, function(){
                this.onDestroy();
            }));
     
            connect.connect(this.viewer, 'onStart', lang.hitch(this, function(){
                this.onStart();
            }));
     
        },
     
        start: function(){
            this.viewer.start();
        },
                     
        stop: function(){
            this.viewer.stop();
        },
     
        onDestroy: function(){},
        onStart: function(){}

    });    
});
