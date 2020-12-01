define([
'dojo/_base/declare',
'dojo/_base/lang',
'dojo/_base/window',
'dojo/dom-construct',
'dijit/Dialog',
'dijit/form/Button',
'dijit/form/Form',
'dijit/form/TextBox',
'dojox/NodeList/delegate',
'java/applet'
], function(declare, lang, win, domConstruct, Dialog, Button, Form, TextBox, delegate, applet){

var Tunnel = declare('ssh.Tunnel', null, {
    // applet stuff
    callback: 'ssh.Tunnel.javatrigger',
    code: 'Tunnel',
    archive: dojo.moduleUrl("ssh","resources/ssh.jar"),

    connected: false,

    // tunnel params.
    host: null,
    local_port: null,
    remote_port: null,
    remote_ip: null,
    local_port: null,
    username: null,
    id: null,

    // applet inject node
    node:null,

    constructor: function(args){
        lang.mixin(this, args);

        this.id = 'tunnel-' + Tunnel.id;
        Tunnel.id = Tunnel.id + 1;
        if(typeof Tunnel.tunnels[this.id] !== 'undefined'){
            console.log('Tunnel already present');
            domConstruct.destroy(this.id);
        }
        Tunnel.tunnels[this.id] = this;
        Tunnel.local_port = Tunnel.local_port + 1;
        this.local_port = Tunnel.local_port;

        if(!this.node){
            this.node = win.body();
        }
        // FIXME: we are incrementing the port number
        // for each new tunnel.
    },

    start: function(){
        console.log('steam2.tunnel.start');
        
        if(this.connected){
            console.log('Tunnel.start', 'already connected');

            // dojo.publish(tunnel.INIT);
            // dojo.publish(tunnel.CONNECTED);
            return;
        }
        applet.inject(this.node, {
            callback:this.callback,
            code:this.code,
            archive:this.archive,
            cache_archive: this.archive,
            cache_version: '1',
            host:this.host,
            local_port:this.local_port,
            remote_port:this.remote_port,
            remote_ip:this.remote_ip,
            username:this.username,
            password:Tunnel.password,
            id:this.id
        });
    },

    stop: function(){
        this.onDestroy();
    },
    
    onConnect: function(){
        this.connected = true;
    },
                
    onDestroy: function(){
        console.log('steam2.tunnel.onDestroy');
        this.connected = false;
        domConstruct.destroy(this.id);
    },

    onPasswordError: function(){
        console.log('steam2.tunnel.onPasswordError');
        domConstruct.destroy(this.id);
        Tunnel.showPasswordDialog();
        Tunnel.current = this;
    },

    onBindError: function(){
        domConstruct.destroy(this.id);
        Tunnel.portDialog();
    }
});

Tunnel.tunnels = {};
Tunnel.id = 0;
Tunnel.current = null;
Tunnel.password = null;
Tunnel.local_port = 8240; 

Tunnel.INJECT = 'tunnel:inject';
Tunnel.INIT = 'tunnel:init';
Tunnel.DESTROY = 'tunnel:destroy';
Tunnel.BIND_ERROR = 'tunnel:bind_error';
Tunnel.PASSWORD_ERROR = 'tunnel:password_error';
Tunnel.CONNECTED = 'tunnel:connected';

Tunnel.javatrigger = function(eventname, id, msg){
    console.log('Tunnel.javatrigger', arguments);
    var tunnel = this.tunnels[id];    
    var self = this;

    function doIt(){
        switch('tunnel:' + eventname){
        case self.DESTROY:
            tunnel.onDestroy();
            break;
        case self.INIT:
            break;
        case self.CONNECTED:
            tunnel.onConnect();
            break;
        case self.BIND_ERROR:
            tunnel.onBindError();
            break;
        case self.PASSWORD_ERROR:
            tunnel.onPasswordError();
            break;
        default:
            console.log('default case');
        }
    }
    setTimeout(doIt, 0);
};

Tunnel.showPasswordDialog = function(){
    console.log('evd::Tunnel2::showPasswordDialog');
    if(typeof this._passwordDialog === 'undefined'){
        this._passwordDialog = this.passwordDialog();
    }
    this._passwordDialog.show();
};

Tunnel.passwordDialog = function(){

    var dialog = new dijit.Dialog({
        title: "Enter password",
        style: "width: 250px",
        onHide: lang.hitch(this, this.stop)
    });

    var content = [
        '<div id="tunnel2-password-form" dojoType="dijit.form.Form" style="text-align:center">',
        '    <script type="dojo/method" data-dojo-event="onSubmit" data-dojo-args="e">',
        '    ssh.Tunnel.passwordDialogSubmit(e,this);',
        '    </script>',
        '    <div>',
        '        Password:',
        '        <input id="evd-tunnel2-password" type="password" name="password" dojoType="dijit.form.TextBox" style="width:100px"/>',
        '    </div>',
        '    <div style="margin-top:5px;">',
        '        <button type="submit" dojoType="dijit.form.Button">OK</button>',
        '    </div>',
        '</div>'].join('');
    dialog.set('content', content);
    return dialog;
 };

Tunnel.passwordDialogSubmit = function(e, form){
    console.log('evd::Tunnel2::passwordDialogSubmit', arguments);

    e.preventDefault(); 
    this.password = form.get('value').password;
    this._passwordDialog.hide();

    var tunnel = this.current;
    tunnel.start();
};

Tunnel.portDialogSubmit = function(form){
    console.log(arguments, this);

    this.local_port = parseInt(form.get('value').port, 10);
    this._portDialog.hide();
    
    var tunnel = this.current;
    tunnel.local_port = this.local_port;
    tunnel.start();
};

Tunnel.portDialog = function(){
    console.log('evd.Tunne2.portDialog');

    if(typeof this._portDialog == 'undefined'){
        this._portDialog = new Dialog({
            style: "width: 300px",
            onHide: lang.hitch(this, this.stop)
        });
    }

    var content = [
        '<div id="tunnel-port-form" dojoType="dijit.form.Form" style="text-align:center">',
        '    <script type="dojo/method" event="onSubmit">',
        '    ssh.Tunnel.portDialogSubmit(this);return false;',
        '    </script>',
        '    <div>',
        '        A free local port:',
        '        <input id="port" type="port" name="port" dojoType="dijit.form.TextBox" style="width:100px" value="' + this.local_port + '" />',
        '    </div>',
        '    <div style="margin-top:5px;">',
        '        <button type="submit" dojoType="dijit.form.Button">OK</button>',
        '    </div>',
        '</div>'].join('');
    this._portDialog.set('title','local port ' + this.local_port + ' is busy');
    this._portDialog.set('content', content);
    this._portDialog.show();
};

return Tunnel;

});
