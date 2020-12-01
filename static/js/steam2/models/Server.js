define([
"dojo/_base/lang",
"dojo/_base/declare",
"dojo/_base/array",
"dojo/_base/connect",
"dojo/dom",
"dojo/dom-construct",
"dojo/string",
"dojo/topic",
"dojox/form/Manager",
"dijit/form/Form",
"dijit/Dialog",
"ssh/Tunnel",
"evd/Viewer",
"steam2/models/Image",
"steam2/models/Network",
"steam2/dialogs/ServerDialog",
"steam2/statusColorMap",
"helpers/uuid",
"../user",

// used declaratively in form - server.html
"dijit/form/FilteringSelect",
"dijit/form/ValidationTextBox",
"dijit/form/NumberSpinner",
"dijit/form/Select"

], function(lang, declare, arrayUtil, connect, dom, domConstruct, string, topic,
FormManager, Form, Dialog, Tunnel, Viewer, Image, Network, ServerDialog, statusColorMap, /*null*/uuid, user) {

var hasCanvas = !!document.createElement('canvas').getContext;

var Server = declare('steam2.models.Server', null, {

    // defaults
    _tunnel: null,
    _viewer: null,

    boot:"hd",
    cdrom: null,
    diskbus: "ide",
    image2:"--",
    image:"--",
    mac: null, // mac of node
    memory: 2048,
    name: null,
    networkuuid1: "1",
    networkuuid2: "--",
    nicmodel1: "rtl8139",
    port: 0,
    status: "new",
    vcpu: 1,
    autostart:false,

    constructor: function(args){
        this.uuid = Math.uuid().toLowerCase();
        lang.mixin(this, args);
    },

    isPowered: function(){
        switch(this.status){
        case "mounting":
        case "unmounting":
        case "resuming":
        case "running":
        case "paused":
        case "shuttingdown":
        case "suspending":
            return true;
        case "starting":
            if(this.port && this.port != '--' && 
               this.mac && this.mac != '--' && 
               this.macip && this.macip != '--'){
                return true;
            }
            // vnc is not ready here
            return false;
        default:
            return false;
        }
    },

    hasTunnel: function(){
        if(this._tunnel){
            return this._tunnel.connected;
        }
        return false;
    },

    getDisplay: function(){
        // this happens when creating a new server
        // the display prop. is not set here for some reason 
        return this.port < 5900 ? 'rdp' : 'vnc';
    },

    getDisplayLink: function(){
        return this.getDisplay() + "://" + this.macip + ":" + this.port;  
    },

    getConsoleLink: function(){
        var t = '<a href="${0}://127.0.0.1:${1}">Java Console</a>';
        return string.substitute(t, [this.getDisplay(), this._tunnel.local_port]);
    },

    getViewerButton: function(){
        if(this.isPowered()){
            if(hasCanvas && this.display === 'vnc'){
                return this.getActionButton('start_html5_vnc_viewer');         
            }
            else{
                if(this.hasViewer){
                    return this.getActionButton('stop_viewer');
                }
                else{
                    return this.getActionButton('start_viewer');        
                }
            }
        }
        return '';
    },

    getEditLink: function(kwargs){
        return Server.getEditLink(this, kwargs);
    },

    getEditImageLink: function(kwargs){
        // a surrogate image 
        var image = {
            path: this.image,
            name: this.imagename,
            status: this.status
        };
        return Image.getEditDialogLink(image, kwargs);
    },

    getEditNetworkLink: function(kwargs){
        var network = {
            uuid: this.networkuuid1,
            name: this.networkname1,
            status: this.status
        };
        return Network.getEditDialogLink(network, kwargs);
    },

    doAction: function(action){

        switch(action){


        case 'edit':
            this.editDialog();
            break;

        case 'delete':
            Server.confirmDialog(this, action);
            break;

        case 'start_viewer':
            this.startViewer();
            break;

        case 'stop_viewer':
            this.stopViewer();
            break;

        case 'start_tunnel':
            this._startTunnel();
            break;

        case 'stop_tunnel':
            this._stopTunnel();
            break;

        case 'start_html5_vnc_viewer':
            this.startHTMLVNCViewer();
            break;


        case 'show_stats':
            var elm = domConstruct.create('iframe', {style: "width:980px;height:560px"});
            var url = '/stabile/static/js/steam2/tests/testStatsChart.html?uuid=' + this.uuid;
            var dialog = new Dialog({
                title: "Server Stats",
                content: elm
            });
            elm.src = url;
            dialog.show();
            break;

        case 'start':
            if(user.is_admin && Server._editDialog && Server._editDialog.mac){
                // start on specific node
                this.mac = Server._editDialog.mac;
                Server.save(this, action, this.mac);
            }
            else{
                Server.save(this, action);
            }
            break;
        default:
            Server.save(this, action);
        }
    },

    getAvailableActions: function(){
        // summary: get all available action for this server
        var actions = this.getActions();
        if(this.isPowered()){
            actions.push('move');
            actions.push('mountcd');
        }
        return actions;
    },

    getActions: function(){
        // summary: get actions for which a button is shown
        // FIXME: bad naming
        switch(this.status){
        case "running":
        case "mounting":
        case "unmounting":
            return ['suspend','shutdown', 'destroy'];

        case "starting":
        case "nostate":
            return ['destroy'];

        case "paused":
            return ['resume','destroy'];

        case "inactive":
        case "crashed":
        case "shutoff":
            return ['start','delete'];

        case "new":
            return [];

        case "suspending":
        case "resuming":
        case "shuttingdown":
            return ['destroy'];

        case "destroying":
        case "moving":
            return ['loading'];

        default:
            console.error("Server", "unknown status: ", status);
            return "";
        }
    },

    getActionButton: function(action){
        if(action === 'loading'){
            return '<img height="20px" style="vertical-align:middle" alt="..." src="/stabile/static/img/loader.gif"></img>';
        }

        var tArgs = {
            uuid: this.uuid,
            action: action,
            title: Server.action2title[action] || action
        };
        tArgs.onClickAction = string.substitute("steam2.models.Server.doAction(arguments[0], '${uuid}','${action}');return false;", tArgs);
        var t = '<button type="button" title="${title}" class="action_button ${action}_icon" onclick="${onClickAction}"><span>${title}</span></button>';
        return string.substitute(t, tArgs);
    },

    getActionButtons: function(){
        var actions;
        if (user.is_readonly) {
            actions = "";
        } else {
            actions = this.getActions();
        }
        var buttons = [];
        var self = this;
        if(dojo.isArray(actions)){
            arrayUtil.forEach(actions, function(action){
                var button = self.getActionButton(action);
                buttons.push(button);
            });
            return buttons.join('');
        }
        // when actions is a pure string parse it straight on.
        return actions;
    },

    _startTunnel: function(onConnect){
        var self = this;
        var tunnel = new Tunnel({
            title: this.name,
            type: this.display,
            remote_ip: this.macip,
            remote_port: this.port,
            host: window.location.host,
            username: "irigo-" + user.username
            });
        this._tunnel = tunnel;
        var handle = connect.connect(tunnel, 'onConnect', function(){
            self.onTunnelConnect();
            onConnect && onConnect();
            connect.disconnect(handle);
        });

        var handle2 = connect.connect(tunnel, 'onDestroy', function(){
            self.onTunnelDisconnect();
            self.stopViewer();
        });

        tunnel.start();
    },

    _stopTunnel: function(){
        if(this._tunnel){
            this._tunnel.stop();
        }
    },

    _startDisplay: function(){
        var args = {
            host: 'localhost',
            port: this._tunnel.local_port,
            title: this.name,
            type: this.getDisplay()
        };

        this._viewer = new Viewer(args);
        
        var handle = connect.connect(this._viewer, 'onDestroy', dojo.hitch(this, function(){
            this.hasViewer = false;
            this._viewer = null;
            this.onViewerStop();
            if(this._tunnel != null){
                this._tunnel.stop();
                this._tunnel = null;
            }
            connect.disconnect(handle);
        }));

        var handle2 = connect.connect(this._viewer, 'onStart', dojo.hitch(this, function(){
            this.hasViewer = true;
            this.onViewerStart();
            connect.disconnect(handle2);
        }));

        this._viewer.start();
    },

    startHTMLVNCViewer: function(){
        Cookies.remove('GUAC_AUTH', { path: '/guacamole'});
        var w = window.open("/guacamole/?uuid=" + this.uuid, this.name);
        w.focus();
    },

    startViewer: function(){
        this.hasViewer = true;
        if(this._viewer != null){
            this._viewer.stop();
        }
        this._startTunnel(dojo.hitch(this, this._startDisplay));
    },

    stopViewer: function(){
        this.hasViewer = false;
        if(this._viewer != null){
            this._viewer.stop();
        }
        else{
            this.onViewerStop();
        }
    },

    onTunnelConnect: function(){
    },

    onTunnelDisconnect: function(){
    },

    onViewerStart: function(){
        Server.onViewerStart(this);
    },

    onViewerStop: function(){
        Server.onViewerStop(this);
    },

    mount: function(cdrom){
        // summary: mount cdrom
        // cdrom:
        //    cdrom to mount
        Server.save(this, 'mountcd', cdrom);
    },

    move: function(mac){
        // summary: move server to node
        // mac:
        //     mac of node to move to.
        Server.save(this, "move", mac);
    },

    editDialog: function(){
        return Server.editDialog(this);
    }
});


Server.postURL = '/stabile/cgi/servers.cgi';
Server.action2title = {
    destroy: 'Pull the plug',
    start_html5_vnc_viewer: 'Start Console',
    start_tunnel:'Start SSH Tunnel',
    stop_tunnel: 'Disconect the SSH Tunnel',
    start_viewer: 'Start Console'
};

Server.onViewerStart = function(server){};
Server.onViewerStop = function(server){};
Server.newDialog = function(){
    var d = new ServerDialog({server:new Server()});
    d.show();
};

    Server.getEditDialogLink = function(server, kwargs){
        var onClickAction = string.substitute("steam2.models.Server.editDialogFromUuid('${uuid}');", server);
        var colorStyle = "";
        var userTitle = "";

        if(kwargs && kwargs.action){
            onClickAction += kwargs.action + ';';
        }
        onClickAction += 'arguments[0].stopPropagation();return false;';

        if(kwargs && kwargs.colorize){
            colorStyle = 'color:' + statusColorMap.get(server.status);
        }
        if (server.user){
            userTitle = 'title="User: ' + server.user + '"';
        }
        return string.substitute('<a style="${0}" ${3} href="#servers" onclick="${1}">${2}</a>',
            [colorStyle, onClickAction, server.name, userTitle]);
    };

    Server.editDialog = function(server){
        require(['stabile/servers', 'stabile/menu'], function(servers, menu){
            var pane = menu.serversPane;
            if(!pane.isLoaded){
                var tabs = menu.tabs;
                var h = connect.connect(servers, 'init', function(evt) {
                    servers.grid.dialog.show(server);
                    dojo.disconnect(h);
                });
                servers.init();
                //tabs.selectChild(pane);
            }
            else{
                servers.grid.dialog.show(server);
            }
        });
    };

    Server.editDialogFromUuid = function(uuid) {
        stores.servers.fetchItemByIdentity({identity: uuid, onItem: function(item) {
            Server.editDialog(item);
        }});
    };

    /*
    Server.editDialog = function(server){
        var self = this;
        var dialog = new ServerDialog({server:server});
        this._editDialog = dialog;

        dialog.connect(dialog, 'onHide', function(){
           self._editDialog = undefined;
        });

        dialog.show();
    };
    */



Server.getEditLink = function(server, kwargs){
    // summary: gets a link that onclick opens the edit dialog.
    // server: 
    //     server with a uuid and name
    // kwargs: Object
    //     * colorize: Boolean?
    //         whether the link should be styled with status color.
    //     * action: String?
    //         an action to perform before opening the dialog
    var onClickAction = string.substitute("steam2.models.Server.doAction(arguments[0], '${uuid}','edit');", server);
    var colorStyle = "";

    if(kwargs && kwargs.action){
        onClickAction += kwargs.action + ';';
    }
    onClickAction += 'return false;';

    if(kwargs && kwargs.colorize){
        colorStyle = 'color:' + statusColorMap.get(server.status); 
    }
    return string.substitute('<a style="${0}" href="#servers" onclick="${1}">${2}</a>', [colorStyle, onClickAction, server.name]);
};

Server.doAction = function(evt, uuid, action){
    // summary: performs action on the given server.
    // evt: DOMEvent
    // uuid: String
    // action: String
    evt.stopPropagation();

    steam2.stores.systems.fetchItemByIdentity({
        identity: uuid,
        onItem: function(server){
            server.doAction(action);
        }
    });
};

Server.createAction = function(server, action, arg){
    // summary: create action representation
    // server: Server
    // action: String
    //     Which action to perform
    // arg: String?
    //     Additional argument, either cdrom or mac. 
    var availableActions = server.getAvailableActions();
    if(availableActions.indexOf(action) == -1){    
        return null;
    }

    switch(action){
    case "move":
        return {
            action: "move",
            mac: arg,
            uuid: server.uuid
        };
    case "mountcd":
        return {
            action: "mountcd",
            cdrom: arg,
            uuid: server.uuid
        };
    case "save":
        return dojox.json.ref.toJson(server, false);
    case "start":
        var _action = {
            action: action,
            uuid: server.uuid
        };
        if(/*mac*/arg){
            _action.mac = arg;
        }
        return _action;
    case "delete":
        // mark the item as deleted in the rest store
        steam2.stores.servers.deleteItem(server);
        // fallthrough!!!
    default:
        return {
            action: action,
            uuid: server.uuid
        };
    }
};

Server.save = function(servers, action, arg){
    // summary:
    if(!lang.isArray(servers)){
        servers = [servers];
    }

    if(action === "delete" && !/*confirmed*/arg){
        Server.confirmDialog(servers, action);
        return;
    }

    // filter to servers where the action is avail. for its status.
    var serverActions = [];
    var serversFiltered = [];
    
    arrayUtil.forEach(servers, function(s){
        var _action = Server.createAction(s, action, arg);
        if(_action){
            serverActions.push(_action);
            serversFiltered.push(s);
        }
    });

    var json = dojo.toJson({items:serverActions});

    var onLoad = function(response){
        var parsed = steam2.stores.parseResponse(response);
        var serverStatus;
        
        // HACK: trigger delete
        // we have aldready deleted the item
        // therefore the steam2.stores.servers
        // delete method is a stub.
        var d = steam2.stores.servers.save();

        // NOTE: We can only use the returned response
        // if the status is the same for all items.
        // FIXME: the backend should return uuid so we can set
        // the status of the items.
        arrayUtil.some(parsed, function(p){

            if(p.error){
                console.log(p.error);
                steam2.stores.servers.reset();
                return false;
            }

            if(serverStatus){
                if(p.status !== serverStatus){
                    // some error, some succes
                    // reload everything ...
                    steam2.stores.servers.reset();
                    serverStatus = null;
                    return false; // end iteration
                }
            }
            serverStatus = p.status;
            return true;
        });

        // if we set the value of the deleted item it's resurrected
        if(serverStatus && serverStatus != 'deleted'){
            // set the status of all items
            arrayUtil.forEach(serversFiltered, function(s){
                steam2.stores.servers.setValue(s, 'status', serverStatus);
            });
        }

        if(this._editDialog){
            if(action == 'delete'){
                this._editDialog.hide();
            }
        }
        return parsed;
    };

    var onError = function(error){
        var parsed = steam2.stores.parseResponse(error.responseText);
        // maybe an error because of an invalid action
        // i.e. a ui update was lost... reset the grid...
        console.log(error);
        steam2.stores.servers.reset();
    };

    var def = Server._save(json);
    return def.then(lang.hitch(this, onLoad), lang.hitch(this, onError));
};

Server._save = function(json){
    return dojo.xhrPost({
        url: this.postURL,
        // FIXME: the backend expects it to be urlencoded!?!
        // headers: { "Content-Type": "application/json" },
        postData: json
    });
};

Server.confirmDialog = function(servers, action){
    if(!lang.isArray(servers)){
        servers = [servers];
    }

    this._confirmItems = servers;
    this._confirmAction = action;

    var t = [
        '<div align="center">',
        '    <p>Are you sure you want to ${0} ${1}:<br>${2}?</p>',
        '    <div>',
        '        <button class="btn btn-warning btn-sm" onClick="steam2.models.Server.actionCanceled();">Cancel</button></button>',
        '        <button class="btn btn-success btn-sm" onClick="steam2.models.Server.actionConfirmed();">${3}</button>',
        '    </div>',
        '</div>'].join('');

    function capitalize(s){
        return s.charAt(0).toUpperCase() + s.slice(1);
    }

    var names = [];
    arrayUtil.forEach(servers, function(s){
        names.push(s.name);
    });
    names = names.join(', ');

    var content = string.substitute(t, [action, servers.length > 1 ? 'servers' : 'server', names, capitalize(action)]);
    if(!this._confirmDialog){
        this._confirmDialog = new Dialog();
    }
    this._confirmDialog.set('title', 'Are you sure?');
    this._confirmDialog.set('content', content);
    this._confirmDialog.show();
};

Server.actionConfirmed = function(){
    Server.save(this._confirmItems, this._confirmAction, true);
    this._confirmItems = null;
    this._confirmAction = null;
    this._confirmDialog.hide();
};

Server.actionCanceled = function(){
    this._confirmData = null;
    this._confirmAction = null;
    this._confirmDialog.hide();
};

return Server;
});