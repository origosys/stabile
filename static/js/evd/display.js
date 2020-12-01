dojo.provide('evd.display');

dojo.require('evd.vnc');
dojo.require('java.applet');
dojo.require('dojo.string');

(function(/*Window*/$, /*dojo*/d){

    var display = {
    
        _ids: [],
    
        start: function(node, args){
            lg('display::start', node, args);
            var id = new Date().getTime() + '';
            this._ids.push(id);
            args.port = tunnel.getLocalPort();
    
            if(args.type == 'rdp'){
                lg('display:start', 'starting rdp client');
                args.archive = '/stabile/static/applet/rdp.jar?v=1';
                args.code = 'net.propero.rdp.applet.RdpApplet';
                args.log_level = 'info';
                $.applet.inject(node, args);
            }
            else if(args.type == 'vnc'){
                lg('display:start', 'starting vnc client');
                args.archive = '/stabile/static/applet/vnc.jar?v=2';
                vnc.start(node, args);
            }
            else{
                throw 'display::start no display type supplied';
            }
        },
    
        destroy: function(){
            dojo.forEach(this._ids, function(id){                
                dojo.destroy(id);
            });
            this._ids = [];
        }
    };
    
    $.display = display;

})(window, dojo);

