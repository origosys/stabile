dojo.provide("evd.rdp");

dojo.require("evd.applet");
dojo.require("dojo.string");

(function(/*window*/$, /*dojo*/d){
     
    $.rdp = {
    
        start: function(node, args){
            // NOTE: something fishy about Rdisplay, although former session
            // (socket, streams) are shutdown when we share the JVM -
            // because of same jar name - a connection exception is thrown!
            // we avoid that by appending a version to the JAR!
            $.applet.inject(node, {
                archive: '/stabile/static/applet/rdp.jar?v=' + new Date().getTime(),
                code: "net.propero.rdp.applet.RdpApplet",
                port: args.port,
                host: args.host,
                title: args.title,
                log_level: "warn"
            });
        }
    };

})(window, dojo);

