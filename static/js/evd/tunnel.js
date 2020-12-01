// dojo.provide('evd.tunnel');

// dojo.require('evd.uid');

// dojo.require('dijit.Dialog');
// dojo.require('dijit.form.Button');
// dojo.require('dijit.form.Form');
// dojo.require('dijit.form.TextBox');
// dojo.require('dojox.NodeList.delegate');

// dojo.require('java.applet');

// (function(/* Window */$){

// var archive = '/stabile/static/applet/evd.jar',

//     id = uid(),
//     start_args,
//     start_node,
//     local_port = 8240,
    
//     code = 'Tunnel',
//     callback = 'tunnel.javatrigger',
//     connected = false,
//     password = '',
    
//     port_dialog = null,
    
//     // EVENTS
//     INJECT = 'tunnel:inject',
//     INIT = 'tunnel:init',
//     DESTROY = 'tunnel:destroy',
//     BIND_ERROR = 'tunnel:bind_error',
//     PASSWORD_ERROR = 'tunnel:password_error',
//     CONNECTED = 'tunnel:connected';
    
//     // event handlers.
// dojo.subscribe(DESTROY, function(obj){
//     connected = false;
//     function doIt(){
//         dojo.destroy(id);
//     }
//     // otherwise browser begins to hang on several requests...?
//     setTimeout(doIt, 0);
// });

// dojo.subscribe(PASSWORD_ERROR, function(obj){
//     dojo.destroy(id);

//     getPassword();

//     dojo.query('#tunnel-password-form').onsubmit(function(e){
//         e.preventDefault();                                     
//         password = this.password.value;
                                 
//         start(start_node, start_args);
//         password_dialog.hide();
//     });
// });

// dojo.subscribe(BIND_ERROR, function(obj){
//     dojo.destroy(id);
//     getPort();
// });

// dojo.subscribe(INIT, function(){
//     connected = true;
// });

// function javatrigger(eventname, id, msg){
//     function f(){
//         dojo.publish('tunnel:' + eventname, [{id:id,msg:msg}]);
//     }
//     setTimeout(f, 0);
// }

// function start(node, args){
//     console.log('evd::start', node, dojo.byId(node), args);
    
//     dojo.publish(tunnel.INJECT);
//     start_args = args;
//     start_node = node;
    
//     if(!connected){

//         $.applet.inject(node, {
//             archive: archive, 
//             id: id,
//             code: code,
//             callback: callback,
//             local_port: local_port,
//             password: password,
//             remote_port: args.remote_port,                                         
//             remote_ip: args.remote_ip,
//             username: args.username,
//             host: args.host
//         });
//     }
//     else{
//         dojo.publish(tunnel.INIT);
//         dojo.publish(tunnel.CONNECTED);
//     }
// }

// var password_dialog = function(){

//     var dialog = new dijit.Dialog({
//         title: "Enter password",
//         style: "width: 250px"
//     });

//     var content = [
//         '<div id="tunnel-password-form" dojoType="dijit.form.Form" style="text-align:center">',
//         '    <div>',
//         '        Password:',
//         '        <input id="tunnel-password" type="password" name="password" dojoType="dijit.form.TextBox" style="width:100px"/>',
//         '    </div>',
//         '    <div style="margin-top:5px;">',
//         '        <button type="submit" dojoType="dijit.form.Button">OK</button>',
//         '    </div>',
//         '</div>'].join('');
//     dialog.set('content', content);
//     return dialog;
//  }();

// function getPortDialog(){
//     if(!port_dialog){
//         return new dijit.Dialog({
//             style: "width: 300px"
//         });
//     }
//     return port_dialog;
// }
    
// function setPortDialogContents(){
//     var new_port = Number(local_port) + 1;

//     var content = [
//         '<div id="tunnel-port-form" dojoType="dijit.form.Form" style="text-align:center">',
//         '    <div>',
//         '        A free local port:',
//         '        <input id="port" type="port" name="port" dojoType="dijit.form.TextBox" style="width:100px" value="' + new_port + '" />',
//         '    </div>',
//         '    <div style="margin-top:5px;">',
//         '        <button type="submit" dojoType="dijit.form.Button">OK</button>',
//         '    </div>',
//         '</div>'].join('');
//     port_dialog.set('title','local port ' + local_port + ' is busy');
//     port_dialog.set('content', content);
// }

// function addPortDialogSubmitHandler(){
//     dojo.connect(dojo.byId('tunnel-port-form'), "onsubmit", function(e){
//         e.preventDefault();                    
//         local_port = this.port.value;
//         port_dialog.hide();
//         start(start_node, start_args);
//     });
// }

// function getPassword(){
//     password_dialog.show();
// }

// function getPort(){
//     port_dialog = getPortDialog();
//     setPortDialogContents();
//     port_dialog.show();
//     addPortDialogSubmitHandler();
// }

// function destroy(){
//     lg("tunnel::destroy", "connected", connected);
//     if(connected){
//         dojo.publish(tunnel.DESTROY);
//     }
// }

//     // destroy: function(){
//     //     lg("tunnel::destroy");
//     //     var def = new dojo.Deferred();

//     //     var h = dojo.connect(this, "onDestroy", function(){
//     //         dojo.disconnect(h);
//     //         def.callback();
//     //     });

//     //     if(dojo.isMac && dojo.isFF){
//     //         // That bitch doesn't call destroy on the applet when removed from the DOM
//     //         if(this._applet){
//     //             this._applet.destroy();
//     //             this._applet = null;
//     //         }
//     //     }

//     //     dojo.destroy('tunnel');
        
//     //     return def;
//     // },

// $.tunnel = {
//     javatrigger: javatrigger,
//     start: start,
//     destroy:destroy,
//     getLocalPort: function(){return local_port;},
    
//     // events
//     INJECT : INJECT,
//     INIT : INIT,
//     DESTROY : DESTROY,
//     BIND_ERROR : BIND_ERROR,
//     PASSWORD_ERROR : PASSWORD_ERROR,
//     CONNECTED : CONNECTED
// };

// })(window);
