define([
'dojo/_base/connect',
'dojo/on',
'dijit/registry',
'stabile/grid',
'stabile/stores',
'stabile/formatters',
'steam2/models/Server',
'stabile/ui_update',
// for nodes.html
'dojo/parser',
'dijit/form/Form',
'dijit/form/FilteringSelect',
'dijit/form/Button',
'dojo/date',
'dojo/date/locale'

],function(connect, on, registry, grid, stores, formatters, Server, ui_update, parser, Form, FilteringSelect){

    var sibFormatter = function (item) {
        var sib = "";
        if (item.status != "shutoff" && item.status != "asleep") {
            sib += "<button type=\"button\" title=\"terminal\" class=\"action_button terminal_icon\" " +
                    "onclick=\"w = window.open('/stabile/nodes?action=terminal&mac=" + item.mac + "', '" + item.mac + "'" +
                    "); w.focus(); return false;" +
                    "\"><span>terminal</span></button>";
        }
        if ((item.ipmiip && item.ipmiip!="--") || (item.amtip && item.amtip!="--")) {
            sib += " <button type=\"button\" title=\"sol\" class=\"action_button sol_icon\" " +
                    "onclick=\"w = window.open('/stabile/nodes?action=sol&mac=" + item.mac + "', 'SOL: " + item.mac + "'" +
                    "); w.focus(); return false;" +
                    "\"><span>SOL</span></button>";
        }
        return sib;
    };

var nodes = {
    _inited: false,

    grid: {},

    /** object name - for reflective lookup */
    name: 'nodes',

    store: null,

    sortInfo: 2,

    storeQuery: { mac: '*'},

    structure : [
        {
            field: '_item',
            name: ' ',
            width: '60px',
            steamid: 'terminal',
            formatter: sibFormatter
        },
        {
            field: 'name',
            name: 'Name',
            width: 'auto'
        },
        {
            field: 'status',
            name: 'Status',
            width: '70px',
            formatter: function(value, rowId){
                var item = this.grid.getItem(rowId);
                var heartbeat = item.timestamp * 1000; /*from secs to ms*/
                var localized = dojo.date.locale.format(new Date(heartbeat), {formatLength: 'medium'});
                var maintsleep = (item.maintenance && item.maintenance=='1' && value=='asleep')?' *':'';
                return dojo.string.substitute('<span title="Heartbeat: ${0}">${1}</span>', [localized, value + maintsleep]);
            }
        },
        {
            field: 'ip',
            name: "IP",
            width: "80px"
        },
        {
            field: 'identity',
            name: 'Identity <a href="https://www.origo.io/info/stabiledocs/web/nodes/hypervisor" rel="help" target="_blank" class="irigo-tooltip">help</a>',
            width: "70px"
        },
        {
            field:'cpucores',
            name:"Cores",
            width: "40px",
            cellStyles: "text-align:right;",
            formatter: function(val, rowIdx, cell) {
                var item = this.grid.getItem(rowIdx);
                return val*item.cpucount;
            }
        },
        {
            field: 'cpuload',
            name: "Load",
            width: "40px",
            cellStyles: "text-align:right;",
            formatter: function(val, rowIdx, cell) {
                var item = this.grid.getItem(rowIdx);
                return ((item.status=="running" || item.status=="maintenance")?val:"--");
            }
        },
        {
            field: 'vms',
            name: "VMs",
            width: "32px",
            cellStyles: "text-align:right;"
        },
        {
            field: 'storfree',
            name:"Free stor (MB)",
            formatter: formatters.kbytes2mbs,
            cellStyles: "text-align:right;",
            width: "85px"
        },
        {
            field: 'memfree',
            name:"Free mem (MB)",
            formatter: formatters.kbytes2mbs,
            cellStyles: "text-align:right;",
            width: "85px"
        },
        {
            field: 'memtotal',
            name: "Total mem (MB)",
            formatter: formatters.kbytes2mbs,
            cellStyles: "text-align:right;",
            width: "90px"
        },
        {
            field: 'action',
            name: 'Action <a href="//www.origo.io/info/stabiledocs/web/nodes/actions" rel="help" target="_blank" class="irigo-tooltip">help</a>',
            width: 'auto',
            formatter: function(val, rowIdx, cell) {
                var item = this.grid.getItem(rowIdx);
                return nodes.getActionButtons(item);
            }
        }
    ],

    dialogStructure : [
        { field: "name", name: "Name", type: "dijit.form.TextBox" },
        { field: "status", name: "Status", type: "dijit.form.TextBox" , attrs : {readonly :"readonly"} },
        { field: "mac", name: "Mac address", type: "dijit.form.TextBox" , attrs: {"readonly":"true"}},
        { field: "stortotal", name: "Total node storage (MB)", type: "dijit.form.TextBox" , attrs: {"disabled":"true"}},
        { field: "storfree", name: "Free node storage (MB)", type: "dijit.form.TextBox" , attrs: {"disabled":"true"}},
        { field: "ipmiip", name: "IPMI IP address", type: "dijit.form.TextBox" , attrs: {"readonly":"true"}},
        { field: "amtip", name: "AMT IP address", type: "dijit.form.TextBox" , attrs: {"readonly":"true"}},
        { field: "cpuname", name: "Cpu name", type: "dijit.form.TextBox",
            style: "width: 200px;",
            attrs: {"disabled":"true"} },
        { field: "vmvcpus", name: "Active vCPU's", type: "dijit.form.TextBox" , attrs : {readonly :"readonly"} },
        {
            formatter: function(node){
                if(node.status != 'shutoff' && node.vms>0 && node.vmuuids){
                    var doms = node.vmuuids.split(/, {0,1}/);
                    var domnames = node.vmnames.split(/, {0,1}/);
                    var domusers = node.vmusers.split(/, {0,1}/);
                    var serverStandIn;
                    var serverEditLink = "";
                    for (var i in doms) {
                        //serverStandIn = {uuid:doms[i],name:domnames[i],user:domusers[i]};
                        //serverEditLink += Server.getEditDialogLink(serverStandIn) + " ";
                        serverEditLink += '<a href="#nodes" title="User: ' + domusers[i] + '" onclick="servers.grid.dialog.show(stores.servers.fetchItemByIdentity({identity: \'' + doms[i]  + '\'}));">' + domnames[i] + '</a> ';
                    }
                    return '<td>Servers</td><td>' + serverEditLink + '</td>';
                } else {
                    return '<td>Servers</td><td>No running servers</td>';
                }
            }
        },
        { field: "nfsroot", name: "NFS root", type: "dijit.form.TextBox" , attrs : {readonly :"readonly"} },
        { field: "kernel", name: "Kernel", type: "dijit.form.TextBox" , attrs : {readonly :"readonly"} }
    ],

    canSort: function(index){
        if(index === 4){ // hypervisor
            return false;
        }
        return true;
    },

    getActionButtons : function(item, include_save){
        var type = this.name;
        var name = item.name;
        function actionButton(args){
            args.name = name;
            args.type = type;
            return grid.actionButton(args);
        }
        // var store = stores.nodes;

        // var id = store.getValue(item, 'mac');
        // var status = store.getValue(item, 'status');

        var id = item.mac;
        var status = item.status;
        var vms = item.vms;
        var amtip = item.amtip;
        if (!amtip || amtip === "--") amtip = item.ipmiip;

        var delete_button = (item.identity=='local_kvm')?'':actionButton({'action':"delete", 'id':id, 'confirm':true});
        var reboot_button = (item.identity=='local_kvm')?'':actionButton({'action':"reboot", 'id':id});
        var shutdown_button = (item.identity=='local_kvm')?'':actionButton({'action':"shutdown", 'id':id});
        var reset_button = actionButton({'action':"reset", 'id':id, 'confirm':true});
        var unjoin_button = (item.identity=='local_kvm')?'':actionButton({'action':"unjoin", 'id':id});
        var reload_button = actionButton({'action':"reload", 'id':id});
        var sleep_button = (item.identity=='local_kvm')?'':actionButton({'action':"sleep", 'id':id});
        var wake_button = (item.identity=='local_kvm')?'':actionButton({'action':"wake", 'id':id});
        var maintenance_button = actionButton({'action':"maintenance", 'id':id});
        var carryon_button = actionButton({'action':"carryon", 'id':id});
        var evacuate_button = actionButton({'action':"evacuate", 'id':id});
        var save = include_save ? grid.saveButton(type) : "";
        var buttons = "";

        if(status === "running"){
            if (vms == 0) {
                buttons += reboot_button;
                buttons += shutdown_button;
                buttons += unjoin_button;
                buttons += sleep_button;
            }
            buttons += reload_button;
            buttons += maintenance_button;
        }
        else if(status === "shutdown"){
            buttons += wake_button;
            buttons += delete_button;
            if (amtip && amtip!="--") buttons += reset_button;
        }
        else if(status === "inactive"){
            buttons += wake_button;
            buttons += delete_button;
            if (amtip && amtip!="--") buttons += reset_button;
        //    buttons += maintenance_button;
        }
        else if(status === "asleep"){
            buttons += wake_button;
        }
        else if(status === "maintenance"){
            if (vms == 0) {
                buttons += reboot_button;
                buttons += shutdown_button;
                buttons += unjoin_button;
                buttons += sleep_button;
                if (amtip && amtip!="--") buttons += reset_button;
            } else {
                buttons += evacuate_button;
            }
            buttons += reload_button;
            buttons += carryon_button;
        }
        else if(status === "reboot"){
            buttons += delete_button;
        }
        else if(status === "waking"){
            buttons += '<img height="18px" alt="waking" src="/stabile/static/img/loader.gif"></img>';
            buttons += delete_button;
            if (amtip && amtip!="--") buttons += reset_button;
        }
        else if(status === "sleeping"){
            buttons += '<img height="18px" alt="waking" src="/stabile/static/img/loader.gif"></img>';
            buttons += delete_button;
            if (amtip && amtip!="--") buttons += reset_button;
        }
        else if(status === "shuttingdown"){
            buttons += '<img height="18px" alt="waking" src="/stabile/static/img/loader.gif"></img>';
            buttons += delete_button;
            if (amtip && amtip!="--") buttons += reset_button;
        }
        else if(status === "joining" || status === "unjoining" || status === "unjoin" || status === "reload" || status === "reloading"){
            buttons += '<img height="18px" alt="waking" src="/stabile/static/img/loader.gif"></img>';
            buttons += delete_button;
            if (amtip && amtip!="--") buttons += reset_button;
        }
        
        else{
            console.error("unknown status", status);
        }
        buttons += save;
        return buttons;
    },

    onPostRender: function(){
        //nodes.updateSums();
        // FIXME: item not loaded when servers dialog is used before this...
        // uncommenting for now
        //console.log(dijit.byId('defaultidentity'));
        //nodes.setDefaultNodeIdentity(dijit.byId('defaultidentity').item, stores.nodeIdentities);
        nodes.setDefaultNodeIdentity();
    },

    onDialogButtons : function(item){
        var stortotal_field = dijit.byId('stortotal');
        var stortotal = this.store.getValue(item, 'stortotal');
        stortotal_field.set('value', formatters.kbytes2mbs(stortotal));
        var storfree_field = dijit.byId('storfree');
        var storfree = this.store.getValue(item, 'storfree');
        storfree_field.set('value', formatters.kbytes2mbs(storfree));
    }
};

nodes.setDefaultNodeIdentity = function(){
    // summary: gets the default node identity and sets the value
    //          of the filtering select.

    var nodeIdtyFilteringSelect = registry.byId('defaultidentity');
    // If dojo not been initialized, i.e. we are loading via jQuery
    if (typeof nodeIdtyFilteringSelect == 'undefined') {
        nodeIdtyFilteringSelect = new FilteringSelect({
            id: "defaultidentity",
            name: "defaultidentity",
            store: stores.nodeIdentities,
            searchAttr: "name"
        }, "defaultidentity").startup();
    };

    var nodeSleepAfterFilteringSelect = dijit.byId('sleepafter');
    if (typeof nodeSleepAfterFilteringSelect == 'undefined') {
        nodeSleepAfterFilteringSelect = new FilteringSelect({
            id: "sleepafter",
            name: "sleepafter"
        }, "sleepafter").startup(function(){console.log("started...");});
    };

    stores.nodeIdentities.fetch({
        query: {identity:'default'}, 
        onItem: function(defaultItem){
            nodeIdtyFilteringSelect.set('value', defaultItem.id);
            nodeIdtyFilteringSelect.set('disabled', false);

            nodeSleepAfterFilteringSelect.set('value', defaultItem.sleepafter);
            nodeSleepAfterFilteringSelect.set('disabled', false);
        }
    });
};

nodes.saveDefaultNodeIdentity = function(){
    var sleepafter = dijit.byId("sleepafter").value;
    var hypervisorId = dijit.byId('defaultidentity').get('displayedValue');
    dojo.xhrGet(
    {
        url: "/stabile/nodes?action=setdefaultnodeidentity&hid=" + hypervisorId + "&sleepafter=" + sleepafter,
        load: function(response) {
            // FIXME: clean up this when ready at the server side
            IRIGO.toaster("message", [{
                message: response,
                type: "message",
                duration: 5000
            }
            ]);
            stores.nodeIdentities.close();
            nodes.setDefaultNodeIdentity();
        }
    });
};



nodes.init = function(){
    if (nodes._inited === true) return;
    else nodes._inited = true;

    this.setDefaultNodeIdentity();

    nodes.store = stores.nodes;
    nodes.domnode = "nodes-grid";
    nodes.grid = grid.create(nodes);
    nodes.grid.startup();

    function handleSelectNodesTab(e){
        if(e.id == 'nodes'){
            nodes.grid.refresh();
        }
    }
    dojo.subscribe('tabContainer-selectChild', null, handleSelectNodesTab);

    dojo.subscribe("nodes:update", function(task){
        if (task.uuid || task.mac) nodes.grid.refreshRow(task);
        else nodes.grid.refresh();
    });

    connect.connect(this.grid, '_onFetchComplete', this, function(rows){
        this.updateSums(rows);
    });

};

    nodes.updateSums = function() {
        dojo.xhrGet({
            url : "/stabile/nodes?action=stats",
            handleAs : "json",
            load : function(response, ioArgs) {
                /* Handle a successful callback here */
                //alert (100*response.cpuloadavg);
                var memf = 0;
                if (response.memtotalsum > 0) memf = 100-100*response.memfreesum / response.memtotalsum;
                //if (dogauge) updateGauges(memf, 100*response.cpuloadavg, 100*response.storused/(response.storused+response.storfree));
                var statssummary =
                        "Nodes: " + response.avgs.nodestotal + "&nbsp&nbsp;Cores: " + response.avgs.corestotal + "&nbsp&nbsp;Memory: " +
                        Math.round((response.avgs.memtotalsum - response.avgs.memfreesum)/1024) + " (" + Math.round(response.avgs.memtotalsum/1024) + ") MB"
                        "&nbsp;&nbsp;Load: " + Math.round(response.avgs.cpuloadavg*100)/100;
                var storsummary = response.stortext;

                document.getElementById("statsbox").innerHTML = statssummary;
                document.getElementById("storagestatsbox").innerHTML = storsummary;
                return response;
            },
            error : function(response, ioArgs) {
                console.log("An error occurrerd.", response, ioArgs);
                //return response;
            }
        });
    }

window.nodes = nodes;
return nodes;
});




