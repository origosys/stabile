define([
"dojo/_base/array",
"dojo/_base/connect",
"stabile/grid",
"steam2/user",
"steam2/models/Server",
"dojox/grid/cells/_base"
],function(arrayUtil, connect, grid, user, Server){

    var networks = {

        grid: {},

        _searchQuery: "name:*",
        _statusQuery: "status:all",
        _inited: false,
        storeQuery: "name:*",
        model : function(args){
            return dojo.mixin({
                uuid: Math.uuid().toLowerCase(),
                name: "",
                id: "",
                internalip: "",
                externalip: "",
                ports:"",
                domainnames: "",
                type: "internalip",
                status: "new"
            }, args || {});
        },

        /** object name - for reflective lookup */
        name : "networks",

        sortInfo: ((user.is_admin)?-4:-3),

        structure : [
            {
                field : 'id',
                name : "ID",
                width : "36px",
                hidden: true
            },
            {
                field : 'type',
                name : 'Type',
                width : "70px"
            },
            {
                field : 'name',
                name : 'Name',
                width : "auto"
            },
            {
                field : 'status',
                name : 'Status' //,
                //formatter : function(val, rowIdx, cell){
                //   var t = '<div class="${cssclass}">${status}</div>';
                //   var cssclass = "";
                //   if(status == "down"){
                //     status = "";
                //     cssclass = "status_indicator down_icon";
                //   }
                //   if(status == "up"){
                //     status = "";
                //     cssclass = "status_indicator up_icon";
                //   }
                //   if(status == "nat"){
                //     status = "";
                //     cssclass = "status_indicator break_icon";
                //   }
                //   return dojo.string.substitute(t, { cssclass : cssclass, status :status });

                ///    var item = this.grid.getItem(rowIdx);
                ///    if (item.type == "gateway" && val == "nat") return "up";
                ///    else return val;
                //}
            },
            {
                field : 'domainnames',
                name : 'Used by',
                width : "auto"
            },
            {
                field : 'internalip',
                name : 'Internal IP',
                width : "100px"
            },
            {
                field : 'externalip',
                name : 'External IP',
                width : "100px"
            },
            { field : 'action', name : 'Action', width : 'auto',
                formatter : function(val, rowIdx, cell) {
                    var item = this.grid.getItem(rowIdx);
                    return networks.getActionButtons(item);
                },
                hidden: user.is_readonly
            }
        ],

        dialogStructure : [
            { field : "name",        name : "Name",    type : "dijit.form.TextBox"},
            { field : "type",        name : "Type", type: "dijit.form.Select",
                attrs:{ store: "stores.networkTypes", searchAttr:"type", onChange: "networks.updateIPFields(this.value);"}},
            { field : 'id',          name : "ID", type : "dijit.form.TextBox", width : "50px", restricted: true,
                attrs:{ onChange: "networks.updateIPPrefix(this.value);"}},
            {
                field: "uuid",
                name: "UUID",
                type: "dijit.form.TextBox",
                style: "width: 275px;",
                attrs: {readonly:"readonly"}
            },
            { field : "status",      name : "Status",  type : "dijit.form.TextBox", attrs : {readonly :"readonly"}},
            { field : 'internalip',  type : "dijit.form.ValidationTextBox",
                name : 'Internal IP <span id="internalipprefix" style="color:gray;"></span>',
                width : "150px",
                attrs : {
                    regExp : "--|25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?",
                    invalidMessage : "Invalid ip."
                }
            },
            {
                field : 'externalip',
                type : "dijit.form.TextBox",
                name : 'External IP',
                width : "150px",
                attrs : {readonly :"readonly"}
            },
            {
                field : 'ports',
                type : "dijit.form.TextBox",
                name : 'Allowed ports',
                help: "networks/ports",
                width : "150px"
            },
            {
                formatter: function(network){
                    // summary: links to server dialog for each server.
                    if(network.status == 'new'){
                        return '';
                    }

                    if(network.domains != '--'){

                        var domainnames = network.domainnames.split(/,\s|,/);
                        var uuids = network.domains.split(/,\s|,/);
                        //var uuids = network.domains[0].split(/,\s|,/);
                        var domains = [];

                        // create a new array that we can sort by name
                        arrayUtil.forEach(uuids, function(d, i){
                            domains.push({uuid: d, name: domainnames[i]});
                        });

                        // sort the servers
                        domains = domains.sort(function(a,b){
                            if(a.name == b.name){ return 0;}
                            if(a.name > b.name){ return 1;}
                            return -1;
                        });

                        var html = [];
                        arrayUtil.forEach(domains, function(d, i){
                            var serverEditLink = '<a href="#networks" onclick="servers.grid.dialog.show(stores.servers.fetchItemByIdentity({identity: \'' + d.uuid  + '\'}));">' + d.name + '</a>';
                            html.push('<li>' + serverEditLink + '</li>');
                        });

                        return '<td valign="top" style="width:60px">Servers</td><td><ul style="list-style:none;padding:0;margin:0;">' + html.join('') + '<ul></td>'; 
                    }
                    return '';
                }  
            }
        ],

        store : null,

        getActionButtons : function(item, include_save){
            if (user.is_readonly) return "";

            var name = item.name;
            var type = this.name;
            function actionButton(args){
                args.name = name;
                args.type = type;
                return grid.actionButton(args);
            }

            // var store = stores.networks;
            // var id = store.getValue(item, 'uuid');
            // var status = store.getValue(item, 'status');

            var id = item.uuid;
            var status = item.status;

            var up = actionButton({'action' :"activate", 'id' :id});
            var down = actionButton({'action' :"stop", 'id' :id, 'confirm':true});
            var _delete = actionButton({'action' :"delete", 'id' :id, 'confirm' :true});
            var _break = actionButton({'action' :"deactivate", 'id' :id});
            var save = include_save ? grid.saveButton(type) : "";

            if (id == 0 || id == 1) {return "";}

            if(status == "down"){
                return (!item.domains || item.domains=="--"?_delete + (item.type=="gateway"?up:""):up) + save;
            }

            if(status == "up"){
                return (item.type=="gateway"?down: _break) + save;
            }

            if(status == "new"){
                return save;
            }

            if(status == "--"){
                return up + (item.domains=="--"?_delete:"");
            }

            if(status == "nat"){
                if ((item.internalip!="--" || item.externalip!="--") && item.domains!="--") return up  + (item.type=="gateway"?down:"") + save;
                else return (item.type=="gateway"?down:"") + save + (item.domains=="--"?_delete:"");
            }
            console.error("WTF? unknown status : ", status);
        },

        onBeforeDialog : function(item){
            stores.networkTypes.close();
        },

        updateIPFields : function(type) {

            function showRow(inputId){
                dojo.query('#' + inputId).closest('tr').style('display', '');
            }
            function hideRow(inputId){
                dojo.query('#' + inputId).closest('tr').style('display', 'none');
            }

            var internalip = dijit.byId("internalip");
            var externalip = dijit.byId("externalip");
            var namefield = dijit.byId("name");
            var typefield = dijit.byId("type");
            var ports = dijit.byId("ports");
            var status = dijit.byId("status").value;
            var uuid = dijit.byId('uuid').value;

            if (user.is_readonly) {
                namefield.disabled = true;
            }
            if (status== "new" || uuid == "0" || uuid == "1") {
                hideRow('uuid');
            }
            if (type == "gateway") {
                hideRow('externalip');
                hideRow('internalip');
                hideRow('ports');

                internalip.set('value', '--');
                externalip.set('value', '--');
            } else if (type == "internalip") {
                showRow('internalip');
                hideRow('externalip');
                hideRow('ports');
                externalip.set('value', '--');
                var id = dijit.byId('id').value;
                networks.updateIPPrefix(id);
            } else if (type == "ipmapping") {
                showRow('internalip');
                showRow('externalip');
                showRow('ports');
                var id = dijit.byId('id').value;
                networks.updateIPPrefix(id);
            } else if (type == "externalip") {
                hideRow('internalip');
                showRow('externalip');
                showRow('ports');
                var id = dijit.byId('id').value;
                networks.updateIPPrefix(id);
            }
            if (status == "up" || user.is_readonly) {
                ports.disabled = true;
                internalip.disabled = true;
            }
        },

        updateIPPrefix : function(id) {
            if(!id || ((id==="1" || id==="0") && !user.is_admin)){return;}
            if (dijit.byId('type')) { // If dialog has been closed, just return
                var type = dijit.byId('type').value;
                if (type == "ipmapping" || type == "internalip") {
                    var first_three_ip_octets = networks.getFirstThreeOctetsbyVlan(id);
                    dojo.byId('internalipprefix').innerHTML = first_three_ip_octets + '.';
                }
            }
        },

        getFirstThreeOctetsbyVlan : function(vlanid){
            vlanid += '';
            if(vlanid.length > 2){
                vlanid = Number(vlanid.substr(0, vlanid.length-2)) + '.' + Number(vlanid.substr(vlanid.length-2));
            }
            else{
                vlanid = "0." + vlanid;
            }
            return "10." + vlanid;
        },

        getOctetFour : function(ip){
            if(ip == "--"){return "--";}
            return ip.split('.')[3];
        },

        onDialogButtons : function(item){
            //var status = this.store.getValue(item, 'status');
            var internalip_field = dijit.byId('internalip');
            var status = item.status;
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

            if(status == 'new'){
                //dijit.byId('internalip').set('disabled', true);
            } else {
                var id = this.store.getValue(item, 'id');
                networks.updateIPPrefix(id);
                var internalip = this.store.getValue(item, 'internalip');
                if (internalip_field) internalip_field.set('value', networks.getOctetFour(internalip));
                var domains = this.store.getValue(item, 'domains');
                if (id<2 || (domains && domains.indexOf(",")!=-1) || item.status == 'up' || user.is_readonly) {
                    if (dijit.byId("type")) disable('type');
                } else {
                     if (dijit.byId("type")) enable('type');
                }
                if(dijit.byId('id')) disable('id');
            }
        },

        onBeforeSave : function(item){
            var vlanid = stores.networks.getValue(item, "id");
            if(vlanid){
                var ip_octet_four = stores.networks.getValue(item, "internalip");

                var isIPSet = function(){
                    return ip_octet_four === '--' ? false  : true;
                };
                var internalip;
                if(isIPSet()) {
                    internalip  = networks.getFirstThreeOctetsbyVlan(vlanid) + '.' + ip_octet_four;
                }
                else{
                    internalip = '--';
                }
                stores.networks.setValue(item, "internalip", internalip);
            }
            var ports = dijit.byId("ports");
            if (ports && ports.value=="") stores.networks.setValue(item, "ports", "--");
        }
    };

    networks.init = function(){
        if (networks._inited === true) return "OK";
        else networks._inited = true;

        connect.connect(dijit.byId('networks_status_filter_select'), 'onChange', this, this.onStatusFilterChange);
        connect.connect(dijit.byId('networks_search_query'), 'onChange', this, this.onSearchQueryChange);

        this.store = stores.networks;
        this.domnode = "networks-grid";
        this.grid = grid.create(this);
        if (!user.is_readonly) {
            if (dijit.byId("networksNewButton")) dijit.byId("networksNewButton").set("style", "display:inline");
        }

        connect.connect(this.grid, '_onFetchComplete', this, function(rows){
            this.updateSums(rows);
            if (!user.is_readonly) $("#networksNewButton").show();
        });

        this.grid.startup();

        dojo.subscribe("networks:update", function(task){
            if (task.uuid) networks.grid.refreshRow(task);
            else networks.grid.refresh();
        });
        this.onShowItem();
    };

    networks.onShowItem = function() {
        if (home.networksOnShowItem != null && networks.grid.dialog) {
            networks.grid.dialog.show(home.networksOnShowItem);
            home.networksOnShowItem = null;
        }
    };

    networks.updateFilter = function(){
        var query = this._searchQuery + " AND " + this._statusQuery;
        this.grid.store.query = query;
        this.grid.filter(query, /*rerender*/true);
    };

    networks.onSearchQueryChange = function(v){
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

    networks.onStatusFilterChange = function(value){
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

    networks.updateSums = function(rows) {
        var totalIntIPs = 0;
        var totalExtIPs = 0;
        var rx = 0;
        var tx = 0;
        var item;
        if (!rows) {
           for(var i = 0; i < networks.grid.rowCount; i++){
               sumit(networks.grid.getItem(i));
           }
        } else {
            for(var i in rows){
                sumit(rows[i]);
            }
        }

        function sumit(item) {
            if (item && item.type) {
                if (item.type=="internalip") {
                    totalIntIPs += 1;
                } else if (item.type=="externalip") {
                    totalExtIPs += 1;
                } else if (item.type=="ipmapping") {
                    totalIntIPs += 1;
                    totalExtIPs += 1;
                }
                if (item.rx) rx = Math.round(item.rx / 1024 / 1024);
                if (item.tx) tx = Math.round(item.tx / 1024 / 1024);
            }
        }

        var rxq = (user.rxquota===0)?'&infin;':Math.round(user.rxquota/1024/1024);
        var txq = (user.txquota===0)?'&infin;':Math.round(user.txquota/1024/1024);
        var exq = (user.externalipquota===0)?'&infin;' : user.externalipquota;
        document.getElementById("ips_sum").innerHTML =
                '<span title="Quotas: ' + exq + ' external IP\'s, ' + rxq + "/" + txq  + ' GB RX/TX">' +
                "Total external IP's: " + totalExtIPs +
                "&nbsp;&nbsp;Total internal IP's: " + totalIntIPs +
                "&nbsp;&nbsp;Total RX/TX: " + Math.round(rx/1024) + "/" + Math.round(tx/1024) + " GB" +
                "</span>";
    };

    window.networks = networks;
    return networks;
});

