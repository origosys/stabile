define([
"dojo/_base/connect",
'dojo/on',
'dojo/dom',
'dojo/dom-construct',
'steam2/models/Server',
'steam2/statusColorMap',
'steam2/user',
'stabile/grid',
'stabile/stores',
'stabile/formatters',
'helpers/uuid',
'dojox/grid/cells/_base',
'dojo/string',
'dijit/form/Button',
'dijit/layout/BorderContainer',
'dijit/form/NumberSpinner'

], function(connect, on, dom, domConstruct, Server, statusColorMap, user, grid, stores){

    var guacFormatter = function (item) {
        if (item.status != "shutoff" && item.status != "inactive" && item.display == "vnc") {
            var guac = "<button type=\"button\" title=\"console\" class=\"action_button console_icon\" " +
"onclick=\"steam2.models.Server.doAction(arguments[0], '" + item.uuid + "','start_html5_vnc_viewer');return false;" +
                //    "onclick=\"w = window.open('/guacamole/?uuid=" + item.uuid + "', '" + item.uuid + "'" +
                //    ",'" + "menubar=no,status=no,toolbar=no,addressbar=no,location=no,titlebar=no')" +
                //    "); w.focus(); return false;" +
                    "\"><span>console</span></button>";
            return guac;
        } else {
            return "";
        }
    };

    var servers = {

        grid : {},
        _searchQuery: "name:*",
        _statusQuery: "status:all",
        _inited: false,
        storeQuery: "name:*",
        model : function(args){
            return dojo.mixin({
                uuid: Math.uuid().toLowerCase(),
                name: "",
                user: user.username,
                memory: "2048",
                vcpu: "1",
                image: "",
                image2: "",
                diskbus: "virtio",
                cdrom: "--",
                boot: "hd",
                networkuuid1: "--",
                nicmodel1: "virtio",
                //nicmodel1: "rtl8139",
                networkuuid2: "--",
               // nicmodel2: ["rtl8139"],
                status: "new",
                port: 0
            }, args || {});
        },

        // TODO: refactor should be on the model!
        isPowered: function(item){
            switch(item.status){
            case "shutoff":
            case "new":
            case "inactive":
            case "crashed":
            case "destroying":
                return false;
            case "starting":
                if(item.port && item.port){
                    return true;
                }
                // vnc is not ready here
                return false;
            default:
                return true;
            }
        },

        /** object name - for reflective lookup */
        name : "servers",
        store : null,
        sortInfo: 3,
        structure : [
            {
                field: '_item',
                name: ' ',
                width: '30px',
                steamid: 'console',
                formatter: guacFormatter,
                hidden: user.is_readonly
            },
            {
                field: 'name',
                name: 'Name',
                width: 'auto'
            },
            {
                field: 'status',
                name: 'Status <a href="https://www.origo.io/info/stabiledocs/web/servers/status" rel="help" target="_blank" class="irigo-tooltip">help</a>',
                width: '100px',
                formatter: function(val, rowIdx, cell) {
                    var t = '<span style="color:${color}">${val}</span>';
                    var color = statusColorMap.get(val);
//                    if(val != "inactive" && user.is_admin){
                    if(user.is_admin){
                        var store = this.grid.store;
                        var item = this.grid.getItem(rowIdx);
                        if (store.getValue(item, 'macname') && store.getValue(item, 'macname')!="--") {
                            val += " on " + store.getValue(item, 'macname');
                        }
                    }
                    return dojo.string.substitute(t, { color: color, val: val });
                }
            },
            {
                field: 'memory',
                name: 'Mem (MB)',
                width: '64px',
                cellStyles: "text-align:right;",
                type: dojox.grid.cells.Select,
                options: ["256", "512", "1024", "2048", "4096", "8192", "16384"]
            },
            {
                field: 'vcpu',
                name: 'VCPUs',
                width: '48px',
                cellStyles: "text-align:right;",
                // editable:true,
                type: dojox.grid.cells.Select,
                options: ["1","2","3","4"]
                },
            {
                field: 'imagename',
                name: 'Image',
                width: 'auto' },
            {
                field: 'imagetype',
                name: 'Type',
                width: '40px'
            },
            //        { field: 'diskbus', name: 'Bus', width: '40px',
            // editable: true,
            //            type: dojox.grid.cells.Select,
            //            options: ["ide", "scsi"]
            //        },
            {
                field: 'networkname1',
                name: 'Connection',
                width: '140px'
            },
            {
                field: 'action',
                name: 'Action <a href="https://www.origo.io/info/stabiledocs/web/servers/server-actions" rel="help" target="_blank" class="irigo-tooltip">help</a>',
                width: 'auto',
                formatter: function(val, rowIdx, cell) {
                    var item = this.grid.getItem(rowIdx);
                    return servers.getActionButtons(item);
                },
                hidden: user.is_readonly
            }
        ],

        dialogStructure : [
            {
                field:"name",
                name: "Name",
                type:"dijit.form.ValidationTextBox",
                //attrs: {regExp: "[\\s\\w.-]+", required:true}
//                attrs: {regExp: ".+", required:true, readonly: (user.is_readonly?"readonly":false)}
                attrs: {regExp: ".+", required:false}
            },
            {
                field: "status",
                name: "Status",
                type: "dijit.form.TextBox",
                attrs: {readonly:"readonly"}
            },
            {
                field: "uuid",
                name: "UUID",
                type: "dijit.form.TextBox",
                attrs: {readonly:"readonly"}
            },
            // hmm. dijit.form.Select doesn't do any selection on the value from the item???
            // Apparently the values must be of type string to do that.
            // It works with filtering select
            {
                field:"memory",
                name: "Memory",
                type: "dijit.form.FilteringSelect",
                style: "width: 55px;",
                attrs: { store: "stores.memory", searchAttr:"memory" }
            },
            {
                field:"vcpu",
                name: "VCPUs",
                type:"dijit.form.NumberSpinner",
                style: "width: 55px;",
                attrs:{ smallDelta:"1", constraints: "{min:1,max:4,places:0}"}
            },
            {
                field:"diskbus",
                name:"Bus",
                type: "dijit.form.Select",
                attrs:{ store: "stores.diskbus", searchAttr:"type" }
            },
            {
                field:"cdrom",
                name:"CD-rom",
                type: "dijit.form.FilteringSelect",
                extra: function(item){
                    return '<button type="button" id="mount_button" class="btn btn-xs btn-info" onclick="servers.mount()" style="font-size:80%; display:none;">Mount</button>';
                },
                attrs:{
                    store: "stores.cdroms", searchAttr:"name",
                    onChange: "if ((this.value != servers.grid.dialog.item.cdrom || this.value=='--') && servers.grid.dialog.item.status=='running') {" +
                            "$('#mount_button').text((this.value=='--')?'Unmount':'Mount').show(); }" +
                            "else {$('#mount_button').hide();};"
                }
            },
            {
                field:"boot",
                name:"Boot",
                type: "dijit.form.Select",
                attrs:{store: "stores.bootDevices", searchAttr:"name"}
            },
            {
                field: "user",
                name: "User",
                type: "dijit.form.FilteringSelect",
                attrs: {
                    store: "stores.accounts",
                    searchAttr: "id",
                    required:"true",
                    query: "{privileges: /(a|u)/}"
//                    onChange: "stores.accounts.fetch({query: {privileges:'*m*'}}); stores.accounts.close();"
                }
            },
            {
                field:"mac",
                name:'<span id="serverDialogNodeDialogLink">Node</span>',
                type: "dijit.form.FilteringSelect",
                restricted: true,
                extra: function(item){
                    return '<button type="button" id="move_button" class="btn btn-xs btn-info" onclick="servers.move()" style="font-size:80%; display:none;">Move</button>';
                },
                attrs:{
                    store: "stores.nodes", searchAttr:"name", required: false,
                    onChange: "if (this.value != servers.grid.dialog.item.mac && servers.grid.dialog.item.status=='running')" +
                            "   $('#move_button').show();" +
                            " else $('#move_button').hide();"
                }
            },
            {
                field: "locktonode",
                name:"Lock to node",
                type: "dijit.form.CheckBox",
                restricted: true,
                attrs:{onchange: "this.value=this.checked?'true':'false';"}
            },
            {
                field:"image",
                name:'<span id="serverDialogImageDialogLink">Image</a>',
                type:"dijit.form.Select",
                help: "servers/image",
                attrs: {
                    store: "stores.unusedImages",
                    searchAttr: "name",
                    required:true,
                    onChange: "suffix=this.value.substr(this.value.lastIndexOf('.')+1); " +
                        "stores.nodeIdentities.fetch({query: {formats:'*' +suffix+ '*'}, onComplete: servers.updateNetworkInterfaces});"
                }
            },
            {
                field:"image2",
                name:'<span id="serverDialogImage2DialogLink">Image2</span>',
                type:"dijit.form.Select",
                help: "servers/image-2",
                attrs: {store: "stores.unusedImages2", searchAttr: "name"}
            },
            {
                field: "networkuuid1",
                name:'<span id="serverDialogNetwork1DialogLink">Connection</span>',
                type: "dijit.form.Select",
                required:true,
                help: "servers/connection",
                attrs: {store:"stores.unusedNetworks", searchAttr: "name"}
            },
            {
                field: "networkuuid2",
                name: '<span id="serverDialogNetwork2DialogLink">Connection2</span>',
                type: "dijit.form.Select",
                attrs: {store:"stores.unusedNetworks2", searchAttr: "name"}
            },
            {
                field: "nicmodel1",
                name:"NIC model",
                type: "dijit.form.Select",
                help: "servers/network-interface",
                attrs: {store:"stores.networkInterfaces", searchAttr: "type", query: "{hypervisor: '*'}"}
            },
            {
                field: "autostart",
                name:"Auto-start",
                type: "dijit.form.CheckBox",
                restricted: true,
                attrs:{onchange: "this.value=this.checked?'true':'false';"}
            },
            {
                // HTML5 console
                formatter: function(item){
                    if(item.status == "new" || user.is_readonly){
                        return "";
                    }
                    if(item.status != "new" && item.status != "shutoff" && item.status != "inactive" && item.macname){
                       return '<td><div>Console</div></td><td><div>' + guacFormatter(item) + '</div></td>';
                    } else {
                        return "";
                    }
                }
            },
            /*
            {
                // tunnel - obsolete, disabled
                formatter: function(item){
                    if(true || item.status == "new"){
                        return "";
                    }

                    var server = new steam2.models.Server(item);

                    var start = '<button type="button" id="tunnelStartButton" onclick="return false;" title="Start" class="action_button start_icon"><span>start</span></button>',
                        stop    = '<button type="button" id="tunnelStopButton"    onclick="return false;" title="Stop"    class="action_button shutdown_icon"><span>stop</span></button>',
                        display = stores.servers.getValue(item, "display");

                    function getArgs(){
                        return {
                            remote_ip: item.macip,
                            remote_port: item.port,
                            host: window.location.host,
                            username: "irigo-" + user.get()
                        };
                    }

                    function addStartTunnelClickHandler(){
                        dojo.query('#tunnelStartButton').onclick(function(){
                            server._startTunnel();
                            return false;
                        });
                    }

                    function addStopTunnelClickHandler(){
                        dojo.query('#tunnelStopButton').onclick(function(){
                            server._stopTunnel();
                            return false;
                        });
                    }

                    // should be something like jquery live
                    dojo.connect(servers.grid, 'onDialog', function(){
                        addStopTunnelClickHandler();
                        addStartTunnelClickHandler();
                    });

                    dojo.connect(server, 'onTunnelConnect', function(){
                        if (dojo.byId('tunnelStatus')) dojo.byId('tunnelStatus').innerHTML = "Active ";
                        if (dojo.byId('tunnelButton')) dojo.byId('tunnelButton').innerHTML = stop;
                        if (dojo.byId('appletLabel')) dojo.byId("appletLabel").innerHTML = '<a href="' + display + '://127.0.0.1:' + server._tunnel.local_port + '">Java console</a>';
                        // // In dojo 1.6, the jquery.live is availble
                        // // change to that when available
                        addStopTunnelClickHandler();
                    });

                    dojo.connect(server, 'onTunnelDisconnect', function(){
                        if (dojo.byId('tunnelStatus')) dojo.byId('tunnelStatus').innerHTML = "Inactive ";
                        if (dojo.byId('tunnelButton')) dojo.byId('tunnelButton').innerHTML = start;
                        if (dojo.byId('appletLabel')) dojo.byId("appletLabel").innerHTML = "Java console";
                        if (dojo.byId('appletStatus')) dojo.byId("appletStatus").innerHTML = "Click on icon to launch";
                        addStartTunnelClickHandler();
                    });

                    return [
                        '<td>Tunnel<a href="https://www.origo.io/info/stabiledocs/web/servers/console/tunnel" rel="help" target="_blank" class="irigo-tooltip">help</a><span id="tunnelApplet" /></td>',
                        '<td>',
                        '    <span id="tunnelStatus">', server.hasTunnel() ? 'Active' : 'Inactive','&nbsp;</span>',
                        '    <span id="tunnelButton">', server.hasTunnel() ? stop : start, '</span>',
                        '    <img id="tunnel-loading-indicator" height="18px" alt="loading ..." style="display:none;vertical-align:bottom" src="/stabile/static/img/loader.gif" />',
                        '</td>'].join('');
                }
            },
            */
            /*
            {
                // Console applet - obsolete, disabled
                formatter: function(item){
                    if(true || item.status == "new"){
                        return "";
                    }
                    var server = new steam2.models.Server(item);

                    var handle = dojo.connect(servers.grid, 'onDialog', function(){
                        dojo.query('#startServerConsole').onclick(function(){
                            dojo.byId('tunnel-loading-indicator').style.display = 'inline';
                            server.startViewer();
                        });
                        dojo.disconnect(handle);
                    });

                    dojo.connect(server, 'onViewerStop', function(){
                        dojo.byId('tunnel-loading-indicator').style.display = 'none';
                    });

                    dojo.connect(server, 'onTunnelConnect', function(){
                        dojo.byId('tunnel-loading-indicator').style.display = 'none';
                    });

                    dojo.connect(server, 'onViewerStart', function(){
                        dojo.byId('tunnel-loading-indicator').style.display = 'none';
                        dojo.byId('appletStatus').innerHTML = "Started";
                    });

                    dojo.connect(server, 'onViewerStop', function(){
                        var elm = dojo.byId('appletStatus');
                        // NOTE: the dialog could be closed before the vnc window
                        if(elm){
                            elm.innerHTML = "Click on icon to launch";
                        }
                    });

                    return [
                        '<td>',
                        '    <div id="consoleApplet">',
                        '        <span id="appletLabel">Java console</span>',
                        '        <a href="https://www.origo.io/info/stabiledocs/web/servers/console" rel="help" target="_blank" class="irigo-tooltip">help</a>',
                        '    </div>',
                        '</td>',
                        '<td>',
                        '    <span id="appletContainer">',
                        '<a href="#servers" id="startServerConsole">',
                        '    <img src="/stabile/static/gfx/console-icon.png" height="48" width="48" style="vertical-align: middle; margin: 10px;" />',
                        '</a>',
                        '             <img id="display-loading-indicator" height="18px" alt="loading ..." style="display:none;vertical-align:bottom" src="/stabile/static/img/loader.gif" />',
                        '    </span>',
                        '        <span id="appletStatus">Click on icon to launch</span>',
                        '    (key mappings <a href="https://www.origo.io/info/stabiledocs/web/servers/console/key-mappings" rel="help" target="_blank" class="irigo-tooltip">help</a>)',
                        '</td>'].join('');
                }
            },
            {
                field: "keyboard",
                name: "Keyboard layout",
                type: "dijit.form.Select",
                attrs: {store:"stores.rdpKeyboardLayouts", searchAttr: "lang"}
            },
            {
                // Display display address
                formatter: function(item){
                    if(item.status == "new"){
                        return "";
                    }
                    if(user.is_admin && item.status != "new" && item.macname){
                        // complicated because we need to fetch the IP asynchronously
                        // ensure that the dialog is shown
                        var macname = item.macname;
                        var handle = dojo.connect(servers.grid, "onDialog",function(){
                            var durl = (item.port < 5900 ? "rdp://":"vnc://") + item.macip + ":" + item.port;
                            dojo.byId('ip').innerHTML = "<a href=\"" + durl + "\">" + durl + "</a>";
                            dojo.disconnect(handle);
                        });
                        var ret = '<td><div id="iplabel">Display</div></td><td><div id="ip"></div></td>';
                        return ret;
                    }
                    return '<td><div id="iplabel"></div></td><td><div id="ip"></div></td>';
                }
            }
            */
        ],

        updateNetworkInterfaces : function(items) {
            var nicmodel1 = dijit.byId("nicmodel1");
            nicmodel1.setStore(stores.networkInterfaces, nicmodel1.value, {query:{hypervisor: "*"+items[0].hypervisor[0]+"*"}});
            // var nicmodel2 = dijit.byId("nicmodel2");
            // nicmodel2.setStore(stores.networkInterfaces, nicmodel2.value, {query:{hypervisor: "*"+items[0].hypervisor+"*"}});
            var image = dijit.byId('image');
            var image2 = dijit.byId('image2');
            if (image2.value) { // Images available for selection depend on first image
                image2.setStore(stores.unusedImages2, image2.value, {query:{hypervisor: "*"+items[0].hypervisor[0]+"*" }});
            }
        },

        dialogExtras : function(item){
            return "";
        },

        mount: function(){
            var item = servers.grid.dialog.item;
            servers.store.setValue(item, 'action', 'mountcd');
            var value = dijit.byId('cdrom').get('value');
            servers.store.setValue(item, 'cdrom', value);
            servers.store.save();
            var res = servers.store.save();
        },

        move: function(){
            var item = servers.grid.dialog.item;
            servers.store.setValue(item, 'action', 'move');
            var value = dijit.byId('mac').get('value');
            servers.store.setValue(item, 'mac', value);
            servers.store.setValue(item, 'status', 'moving');
            servers.grid.dialog.hide();
            var res = servers.store.save();
            /* res[0].deferred.promise.then(function(e) {
                console.log(e.message);
                if (e.error) {
                    IRIGO.toast(e.message);
                    servers.grid.refresh();
                }
            }); */
        },

        getActionButtons : function(item, include_save){
            if (user.is_readonly) return "";

            var name = item.name;
            var type = this.name;

            function actionButton(args){
                args.name = name;
                args.type = type;
                return grid.actionButton(args);
            }
            var id = item.uuid;//store.getValue(item, 'uuid');
            var status = item.status;//store.getValue(item, 'status');
            
            var start = actionButton({'action':"start", 'id':id});
            var resume = actionButton({'action':"resume", 'id':id});
            var suspend = actionButton({'action':"suspend", 'id':id});
            var shutdown = actionButton({'action':"shutdown", title:'ACPI shutdown, <br />(Note: only works if supported by OS)', 'id':id, confirm:true});
            var destroy = actionButton({'action':"destroy", 'id':id, title:'pull the plug', 'confirm':true});
            var _delete = actionButton({'action':"delete", 'id':id, 'confirm':true});
            var save = include_save ? grid.saveButton(type) : "";
            var busy = ' <img height="18px" alt="busy" src="/stabile/static/img/loader.gif"> ';

            switch(status){
                case "running":
                    return suspend + shutdown + destroy + save;

                case "starting":
                case "nostate":
                    return busy + destroy + save;

                case "paused":
                    return resume + destroy + save;

                case "inactive":
                    return start + _delete + save;
                case "crashed":
                case "shutoff":
                    return start + _delete + save;

                case "new":
                    return save;

                case "upgrading":
                case "suspending":
                case "resuming":
                case "shuttingdown":
                    return busy + destroy;

                case "destroying":
                    return busy + destroy;

                case "moving":
                    return busy;

                default:
                    console.log("servers::getActionButtons", "unknown status: ", status);
                    return "";
            }
        },

        // update the store to include the current server image
        onBeforeDialog : function(item){
            this.item = item;
            stores.cdroms.close();
            if(item.image && item.image){
                stores.unusedImages.url = "/stabile/images?action=listimages&image=" +
                    escape(item.image);
                stores.unusedImages.close();
            }
            else{
                // update the store
                stores.unusedImages.url = "/stabile/images?action=listimages";
                stores.unusedImages.close();
            }
            if(item.image2 && item.image2){
                stores.unusedImages2.url = "/stabile/images?action=listimages&image1=" +
                    escape(item.image) + "&image=" + escape(item.image2);
                stores.unusedImages2.close();
            }
            else{
                // update the store
                stores.unusedImages2.url = "/stabile/images?action=listimages&image1=--";
                stores.unusedImages2.close();
            }
            if(item.networkuuid1 && item.networkuuid1){
                stores.unusedNetworks.url = "/stabile/networks?action=listnetworks&network=" +
                    escape(item.networkuuid1);
                stores.unusedNetworks.close();
            }
            else{
                // update the store
                stores.unusedNetworks.url = "/stabile/networks?action=listnetworks";
                stores.unusedNetworks.close();
            }
            if(item.networkuuid2 && item.networkuuid2){
                stores.unusedNetworks2.url = "/stabile/networks?action=listnetworks&network=" +
                    escape(item.networkuuid1) + "&network1=" + escape(item.networkuuid2);
                stores.unusedNetworks2.close();
            }
            else{
                // update the store
                stores.unusedNetworks2.url = "/stabile/networks?action=listnetworks";
                stores.unusedNetworks2.close();
            }
        },

//        onPostRender: function(){
//            servers.updateSums();
//        },

        canSort: function(index){
            if(index === 9){ // action
                return false;
            }
            if(index === 1){
                // status! Something bug in the dojo dropdown button.
                // it doesn't stop the event onClicks although I have specified it!
                // Tooltip clicks then triggers a sort, and removal of the tooltip content.
                // Therefore returning false.
                return false;
            }
            return true;
        },


        // FIXME: bad naming here
        onDialogButtons : function(item){
            // helpers
            var hide = function(dijitId){
                var elm = dijit.byId(dijitId);
                elm && elm.set('style', 'display:none');
                return elm;
            };
            var disable = function(dijitId){
                var elm = dijit.byId(dijitId);
                elm && elm.set('disabled', true);
                return elm;
            };
            var enable = function(dijitId){
                var elm = dijit.byId(dijitId);
                elm && elm.set('disabled', false);
                return elm;
            };
            var hideRow = function(domId){
                // tr <- td <- input
                dojo.query('#' + domId).parent().parent().style({display:"none"});
            };
            var showRow = function(domId){
                dojo.query('#' + domId).parent().parent().style({display: "table-row"});
            };

            if(servers.isPowered(item) || user.is_readonly){
                if (dijit.byId('dialogForm'))
                        dojo.forEach(dijit.byId('dialogForm').getChildren(), function(input){
                            if (input.id!='uuid') input.set('disabled', true);
                        });
            }
            else{
                    if (dijit.byId('dialogForm'))
                        dojo.forEach(dijit.byId('dialogForm').getChildren(), function(input){
                            input.set('disabled', false);
                        });
            }

            if (!user.is_readonly) {
                // always enable renaming
                enable('name');
                enable('boot');
                enable('autostart');
                enable('locktonode');
                //enable('mount_button');
            }
            if (user.is_admin) {
                //enable('move_button');
                // $('#move_button').show();
            }

            if (item.status == "new") {
                $('#mount_button').hide();
                disable('user');
            } else {
                if (item.status == "shutoff" && !user.is_readonly) {
                    enable('user');
                } else {
                    disable('user');
                }
            }

            var on_node = (new RegExp("\/mnt\/stabile\/node\/")).test(item.image)?true:false;
            if (item.status == "new" || on_node) {
                $('#move_button').hide();
                disable('!($image =~ /\/$user\//)');
            }
            if(item.status == "running" && !user.is_readonly){
                //enable('mount_button').set('style', 'display:inline');
                enable('cdrom');

                var kb = enable('keyboard');
                if (kb) kb.set('value', 'en-us');
                enable('mac');
                if (user.is_admin) {
                    // $('#move_button').show();
                } else {
                    $('#move_button').hide();
                }
            } else {
                $('#mount_button').hide();
                $('#move_button').hide();
            }

            if (servers.isPowered(item) && user.is_admin && !user.is_readonly) {
                showRow('consoleApplet');
                showRow('ip');
                showRow('tunnelStatus');
            } else {
                hideRow('consoleApplet');
                hideRow('ip');
                hideRow('tunnelStatus');
            }

            if (item.display == "rdp" && servers.isPowered(item) && user.is_admin && !user.is_readonly){
                showRow('keyboard');
            }
            else{
                hideRow('keyboard');
            }
        }
    };


    servers.updateFilter = function(){
        var query = this._searchQuery + " AND " + this._statusQuery;
        this.grid.store.query = query;
        this.grid.filter(query, /*rerender*/true);
    };

    servers.onSearchQueryChange = function(v){
        if(v){
            /*this._searchQuery = "name: '*" + v + "*'" +
             " OR status: '" + v + "*'" +
             " OR type: '" + v + "*'" +
             " OR internalip: '" + v + "*'" +
             " OR externalip: '" + v + "*'";*/
            this._searchQuery = "name:" +v + "*";
        }
        else{
            //this._searchQuery = "name: *";
            this._searchQuery = "name:*";
        }
        this.updateFilter();
    };

    servers.onStatusFilterChange = function(value){
        switch(value){
            case "all":
                //this._statusQuery = "uuid:*";
                this._statusQuery = "status:all";
                break;
            default:
                //this._statusQuery = "status:*" + value + '*';
                this._statusQuery = "status:" + value;
        }
        this.updateFilter();
    };

    servers.init = function() {
        if (servers._inited === true) return;
        else servers._inited = true;

        connect.connect(dijit.byId('servers_status_filter_select'), 'onChange', this, this.onStatusFilterChange);
        connect.connect(dijit.byId('servers_search_query'), 'onChange', this, this.onSearchQueryChange);

        servers.store = stores.servers;
        servers.domnode = "servers-grid";
        servers.grid = grid.create(servers);

        connect.connect(this.grid, '_onFetchComplete', this, function(rows){
            this.updateSums(rows);
            if (!user.is_readonly) $("#serversNewButton").show();
        });

        //servers.grid.query = "uuid: '*'";
        servers.grid.startup();

        // ui update
        dojo.subscribe("servers:update", function(task){
            if(dijit.byId('createServerDialog')){ return;}
            console.log("servers update", task);
            if (task.uuid) {
                servers.grid.refreshRow(task);
                home.grid.refresh();
            } else {
                servers.grid.refresh();
                home.grid.refresh();
            }
            var item = servers.grid.dialog.item;
            if(!item || item.uuid !== task.uuid){
                return;
            }
            if (dojo.byId('ip') && task.displayip && task.displayport) {
                var disp = (task.displayport<5900?"rdp://":"vnc://");

                // Why is the local_port arriving from the server?
                // var durl = disp + task.displayip + ":" + task.displayport;
                // changed -- Jakob
                var durl = disp + task.displayip + ":" + task.displayport; //tunnel.getLocalPort();
                dojo.byId('ip').innerHTML = "<a href=\"" + durl + "\">" + durl + "</a>";
                item.port = task.displayport;
                item.macip = task.displayip;
            }
        });

        connect.connect(this.grid.dialog, 'show', this, function(item){
            // summary: create dialog node link.
            var self = this;
            if(item.status != 'new'){
                if(item.image && item.image != '--'){
                    domConstruct.place('<a id="serverDialogImageDialogLink" nohref="#servers">Image</a>', 'serverDialogImageDialogLink', 'replace');
                    on(dom.byId('serverDialogImageDialogLink'), 'click', function(){
                        self.grid.dialog.hide();
                        home.showImageDialog(item.image);
                //        stores.imagesByPath.fetchItemByIdentity({identity: item.image , onItem: function(item) {console.log("fetching", item); stores.images.fetchItemByIdentity({identity: item.uuid, onItem: function(image){window['images'].grid.dialog.show(image);}})}});
                    });
                }
                if(item.image2 && item.image2 != '--'){
                    domConstruct.place('<a id="serverDialogImage2DialogLink" nohref="#servers">Image2</a>', 'serverDialogImage2DialogLink', 'replace');
                    on(dom.byId('serverDialogImage2DialogLink'), 'click', function(){
                        self.grid.dialog.hide();
                        home.showImageDialog(item.image2);
                //        stores.imagesByPath.fetchItemByIdentity({identity: item.image2 , onItem: function(item){stores.images.fetchItemByIdentity({identity: item.uuid, onItem: function(image){window['images'].grid.dialog.show(image);}})}});
                    });
                }
                if(item.networkuuid1 && item.networkuuid1 != '--'){
                    domConstruct.place('<a id="serverDialogNetwork1DialogLink" nohref="#servers">Connection</a>', 'serverDialogNetwork1DialogLink', 'replace');
                    on(dom.byId('serverDialogNetwork1DialogLink'), 'click', function(){
                        self.grid.dialog.hide();
                        networks.grid.dialog.show(stores.networks.fetchItemByIdentity({identity: item.networkuuid1 }));
                    });
                }
                if(item.networkuuid2 && item.networkuuid2 != '--'){
                    domConstruct.place('<a id="serverDialogNetwork2DialogLink" nohref="#servers">Connection2</a>', 'serverDialogNetwork2DialogLink', 'replace');
                    on(dom.byId('serverDialogNetwork2DialogLink'), 'click', function(){
                        self.grid.dialog.hide();
                        networks.grid.dialog.show(stores.networks.fetchItemByIdentity({identity: item.networkuuid2 }));
                    });
                }
                if(user.is_admin && item.mac && item.mac != '--'){
                    domConstruct.place('<a id="serverDialogNodeDialogLink" nohref="#servers">Node</a>', 'serverDialogNodeDialogLink', 'replace');
                    on(dom.byId('serverDialogNodeDialogLink'), 'click', function(){
                        self.grid.dialog.hide();
                        nodes.grid.dialog.show(stores.nodes.fetchItemByIdentity({identity: item.mac }));
                    });
                }
            }
        });

    };

    servers.updateSums = function(rows) {
        var totalvcpus = 0;
        var totalmemory = 0;

        if (!rows) {
            for(var i = 0; i < servers.grid.rowCount; i++){
                sumit(servers.grid.getItem(i));
            }
        } else {
            for(var i in rows){
                sumit(rows[i]);
            }
        }

        function sumit(item) {
            if (item) {
                if (item.status && item.status!="inactive" && item.status!="shutoff") {
                    totalvcpus += parseInt(item.vcpu);
                    totalmemory += parseInt(item.memory);
                }
            }
        }
        var vq = (user.vcpuquota==0)?'&infin;':Math.round(user.vcpuquota);
        var memq = (user.memoryquota==0)?'&infin;': (Math.round(10*user.memoryquota /1024)/10);
        document.getElementById("machines_sum").innerHTML =
                '<span title="Quotas: ' + vq + ' VCPUs, ' + memq + ' GB memory">' +
                "Total VCPUs: " + totalvcpus +
                "&nbsp;&nbsp;Total memory: " + (Math.round(10*totalmemory /1024)/10) +
                "</span>";
    }
    window.servers = servers;
    return servers;
});


