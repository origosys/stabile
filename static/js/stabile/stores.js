// JSLint defined globals
/*global dojo:false, dijit:false, window:false */
define([
'dojo/data/ItemFileWriteStore',
'dojox/data/AndOrWriteStore',
'dojo/data/ItemFileReadStore',
//'dojo/store/Memory',
'dojox/data/JsonRestStore',
'dojox/data/JsonQueryRestStore',
'dojox/data/AndOrReadStore'
], function(){

var server = {
    parseResponse: function(response) {
      var responsearray = response.split("\n");
      var a = "";
      var status = "";
      for ( var i = 0; i<responsearray.length; i++ ){
        var res = responsearray[i];
        if (res != "") {
          status = res.substring(res.indexOf("=")+1,res.indexOf(" "));
          res = res.substring(res.indexOf(" ")+1);
          a += res + "<br>";
        }
      }
      if(a != ""){
          var msg =  [{message: a, type: "message",duration: 5000}];
          IRIGO.toaster(msg);
      }
      return {status:status, message:a};
    },

    saveEverythingFn: function(url){
        return function(saveCompleteCallback, saveFailedCallback, newFileContentString){
            var store = this;
            newFileContentString = newFileContentString.replace(/\+/g, "\\u002b"); //%2b Plus signs don't get across
//            newFileContentString = newFileContentString.replace("+", "\u002b"); //%2b
            newFileContentString = newFileContentString.replace(/=/g, "\\u003d"); //%3d
//            newFileContentString = encodeURIComponent(newFileContentString);
            dojo.xhrPost(
            {
                url: url,
//                postData: dojo.toJson(dojo.fromJson(newFileContentString)), // this unprettifies the string
                postData: newFileContentString, 
                    error: saveFailedCallback,
                load: function(response) {
                    var parsed = server.parseResponse(response);
                    // FIXME: waiting for the serverside to be updated.
                    if(parsed.message.substr(6, 26) == 'Image already exists'){
                        saveFailedCallback("An image with that name already exists!");
                    }
                    else{
                        saveCompleteCallback();
                    }
                }
            });
            IRIGO.toaster([
                {
                    message: "Processing ...",
                    type: "message",
                    duration: 2000
                }]);

        };
    }
};

var stores = {
    register: new dojox.data.JsonRestStore({
        target:"/stabile/systems?action=register/",
        idAttribute:"uuid"
    }),

    packages: new dojox.data.JsonRestStore({
        target:"/stabile/systems?action=packages/",
        idAttribute:"id"
    }),

    monitors: new dojox.data.JsonRestStore({
        target:"/stabile/systems/monitors/",
        idAttribute:"id",
        syncMode:false,

        cacheByDefault: true,
        urlPreventCache: true,
        clearOnClose: true,

        reset: function(id){
            // remove all the existing elements from the index
            for (idx in dojox.rpc.Rest._index) {
                if (idx.match("monitors")) {
                    if (!id || dojox.rpc.Rest._index[idx].id == id) {
                 //       console.log("Deleting from Dojo: " + idx);
                        delete dojox.rpc.Rest._index[idx];
                    }
                }
            };
            this._updates = [];
            // clear the query cache
            this.clearCache();
        //    this.revert();
        }
    }),

//    uptimeMonths: new dojo.store.Memory(),

    uptimeMonths: new dojo.data.ItemFileWriteStore({data: {identifier: "yearmonth", label: "name", items: []}}),
    usageMonths: new dojo.data.ItemFileWriteStore({data: {identifier: "yearmonth", label: "name", items: []}}),

    monitorsServices: new dojox.data.AndOrReadStore({
        data: {identifier: "service", label: "name", items: [
            {service:"ping", monitor:"fping.monitor", name:"ping"},
            {service:"diskspace", monitor:"stabile-diskspace.monitor", name:"diskspace"},
            {service:"http", monitor:"http_tppnp.monitor", name:"http"},
            {service:"https", monitor:"http_tppnp.monitor", name:"https"},
            {service:"smtp", monitor:"smtp3.monitor", name:"smtp"},
            {service:"smtps", monitor:"smtp3.monitor", name:"smtp (tls)"},
            {service:"imap", monitor:"imap.monitor", name:"imap"},
            {service:"imaps", monitor:"imap-ssl.monitor", name:"imaps"},
            {service:"ldap", monitor:"ldap.monitor", name:"ldap"},
            {service:"telnet", monitor:"telnet.monitor", name:"telnet"}
        ]}
    }),

    systemsSelect: new dojo.data.ItemFileReadStore({
        url:  "/stabile/systems?action=flatlist",
        urlPreventCache: true,
        clearOnClose: true
    }),

//    servers: new dojox.data.AndOrWriteStore({
//            url : "/stabile/servers?action=list",
//        urlPreventCache: true,
//        clearOnClose: true
//    }),

    servers: new dojox.data.JsonRestStore({
        target: "/stabile/servers",
        idAttribute:"uuid",
        syncMode:false,
        cacheByDefault: false,
        urlPreventCache: true,
        clearOnClose: true
    }),

    serversReadOnly: new dojo.data.ItemFileReadStore({
        url: "/stabile/servers?action=list",
        urlPreventCache: true,
        clearOnClose: true
    }),

    images: new dojox.data.JsonRestStore({
        target:"/stabile/images",
        idAttribute:"uuid",
        syncMode:false,
        cacheByDefault: false,
        clearOnClose:true,
        urlPreventCache:true
    }),

    networks: new dojox.data.JsonRestStore({
        target:"/stabile/networks",
        idAttribute:"uuid",
        syncMode:false,
        cacheByDefault: false,
        clearOnClose:true,
        urlPreventCache: true
    }),

    users: new dojox.data.JsonRestStore({
        target:"/stabile/users",
        idAttribute:"username",
        syncMode:false,
        cacheByDefault: false,
        clearOnClose:true,
        urlPreventCache: true
    }),

    nodesReadOnly: new dojo.data.ItemFileReadStore({
        url:"/stabile/nodes?action=listnodes",
        clearOnClose:true,
        urlPreventCache:true
    }),

    nodes: new dojox.data.JsonRestStore({
        target:"/stabile/nodes",
        idAttribute:"mac",
        syncMode:false,
        cacheByDefault: false,
        clearOnClose:true,
        urlPreventCache:true
    }),

    networksReadOnly: new dojo.data.ItemFileReadStore({
        url:"/stabile/networks?action=list",
        clearOnClose:true,
        urlPreventCache: true
    }),

    unusedNetworks: new dojox.data.AndOrWriteStore({
        url:"/stabile/networks?action=listnetworks",
        clearOnClose:true,
        urlPreventCache: true
    }),

    unusedNetworks2: new dojo.data.ItemFileReadStore({
        url:"/stabile/networks?action=listnetworks",
        clearOnClose:true,
        urlPreventCache: true
    }),

    cdroms: new dojo.data.ItemFileReadStore({
        url:"/stabile/images?action=listcdroms",
        clearOnClose:true,
        urlPreventCache: true
    }),

    ids: new dojo.data.ItemFileReadStore({
        url:"/stabile/users?action=listids",
        clearOnClose:true,
        urlPreventCache:true
    }),

    imageids: new dojo.data.ItemFileReadStore({
        url:"/stabile/users?action=listaccounts&common=1",
        clearOnClose:true,
        urlPreventCache:true
    }),

    accounts: new dojo.data.ItemFileReadStore({
        url:"/stabile/users?action=listaccounts",
        clearOnClose:true,
        urlPreventCache:true
    }),

    engines: new dojo.data.ItemFileReadStore({
        url:"/stabile/users?action=listengines",
        clearOnClose:true,
        urlPreventCache:true
/*        data: {
            identifier: "href", label: "name", items: [
                {href: "#", name: "Compute"}
            ]
        } */
    }),

    imagesDevices: new dojo.data.ItemFileReadStore({
        url:"/stabile/images?action=listimagesdevices",
        clearOnClose:true,
        urlPreventCache:true
    }),
    backupDevices: new dojo.data.ItemFileReadStore({
        url:"/stabile/images?action=listbackupdevices",
        clearOnClose:true,
        urlPreventCache:true
    }),

    engineBackups: new dojo.data.ItemFileReadStore({
        url:"/stabile/users?action=listenginebackups",
        clearOnClose:true,
        urlPreventCache:true
    }),

    nodeIdentities: new dojo.data.ItemFileReadStore({
        url: "/stabile/nodes?action=listnodeidentities",
        clearOnClose: true,
        urlPreventCache:true
    }),

    unusedImages: new dojo.data.ItemFileReadStore({
        url:"/stabile/images?action=listimages",
        clearOnClose:true,
        urlPreventCache:true
    }),

    unusedImages2: new dojo.data.ItemFileReadStore({
        url:"/stabile/images?action=listimages",
        clearOnClose:true,
        urlPreventCache:true
    }),

    backups: new dojo.data.ItemFileReadStore({
//        url:"/stabile/images?action=listbackups",
        clearOnClose:true,
        urlPreventCache:true
    }),

    backupSchedules: new dojo.data.ItemFileReadStore({
        data: {
            identifier: "schedule", label: "name", items: [
                {schedule: "manually", name: "Manually"},
                {schedule: "none", name: "Clear backups"},
                {schedule: "daily7", name: "Daily, 1 week"},
                {schedule: "daily14", name: "Daily, 2 weeks"}
            ]
        }
    }),

    storagePools: new dojo.data.ItemFileReadStore({
        url:"/stabile/images?action=liststoragepools&dojo=1",
        clearOnClose:true,
        urlPreventCache:true
    }),

    imagesByPath: new dojo.data.ItemFileReadStore({
        url: "/stabile/images?action=listimages&image=all", //listall",
        clearOnClose:true,
        urlPreventCache:true
    }),

    masterimages: new dojo.data.ItemFileReadStore({
        url:"/stabile/images?action=listmasterimages",
        clearOnClose:true,
        urlPreventCache: true
    }),

    memory: new dojo.data.ItemFileReadStore({
        data: {
            identifier: "memory",
            label: "memory",
            items: [{memory:256},{memory:512},{memory:1024},{memory:2048},
            {memory:4096},{memory:8192},{memory:12288},{memory:16384},{memory:24576},{memory:32768}]}
    }),
    diskbus: new dojo.data.ItemFileReadStore({
        data: {identifier: "type", label: "type", items: [{type:"ide"},{type:"scsi"},{type:"virtio"}]}
    }),
    networkInterfaces: new dojo.data.ItemFileReadStore({
        data: {identifier: "type", label: "name", items: [
            {type:"virtio", hypervisor:"kvm,vbox", name: "Paravirtualized Network"},
            {type:"rtl8139", hypervisor:"kvm", name: "Realtek 8139 (fast)"},
            {type: "ne2k_pci", hypervisor:"kvm", name: "Realtek NE2000 (fast)"},
            {type:"e1000", hypervisor:"kvm", name: "Intel Pro/1000"},
            {type:"i82551", hypervisor:"kvm", name: "Intel 82551 (fast)"},
            {type: "i82557b", hypervisor:"kvm", name: "Intel i82557b (fast)"},
            {type: "i82559er", hypervisor:"kvm", name: "Intel i82559er (fast)"},
            {type:"pcnet", hypervisor:"kvm", name: "PCnet (fast)"},
            {type:"Am79C973", hypervisor:"vbox", name: "PCnet-FAST III"},
            {type:"Am79C970A", hypervisor:"vbox", name: "PCnet-PCI II"},
            {type:"82540EM", hypervisor:"vbox", name: "Intel Pro/1000 MT Desktop"},
            {type:"82543GC", hypervisor:"vbox", name: "Intel Pro/1000 T Server"},
            {type:"82545EM", hypervisor:"vbox", name: "Intel Pro/1000 MT Server"}
            ]}
    }),
    bootDevices: new dojo.data.ItemFileReadStore({
        data: {identifier: "device", label: "device", items: [{device: "hd"},{device: "cdrom"},{device: "network"}]}
    }),
    imageTypes: new dojo.data.ItemFileReadStore({
        data: {
            identifier: "type", label: "type", items: [
                {type: "qcow2"},
                {type: "vdi"},
                {type: "iso"},
                {type: "vmdk"},
                {type: "img"}
            ]
        }
    }),
    networkTypes: new dojo.data.ItemFileReadStore({
/*        data: {
            identifier: "type", label: "name", items: [
                {type: "gateway", name: "Gateway"},
                {type: "internalip", name: "Internal IP"},
                {type: "ipmapping", name: "IP mapping"},
                {type: "externalip", name: "External IP"}
            ]
        }*/
        url:"/stabile/networks?action=listnetworktypes",
        clearOnClose:true,
        urlPreventCache: true
    }),
    virtualSizes: new dojo.data.ItemFileReadStore({
        data: {
            identifier: "size", label: "size", items: [
                {size: "10737418240", label: "10GB"}, {size: "21474836480", label: "20GB"},
                {size: "42949672960", label: "40GB"}, {size: "64424509440", label: "60GB"},
                {size: "85899345920", label: "80GB"}, {size: "107374182400", label: "100GB"},
                {size: "128849018880", label: "120GB"}, {size: "257698037760", label: "240GB"},
                {size: "549755813888", label: "512GB"}, {size: "1099511627776", label: "1024GB"},
                {size: "2199023255552", label: "2048GB"}

            ]
        }
    }),
  rdpKeyboardLayouts: new dojo.data.ItemFileReadStore(
    {
      data: {
        identifier: "lang", label: "lang", items: [
{lang:"en-us"},
{lang:"ar"},
{lang:"da"},
{lang:"de"},
{lang:"en-gb"},
{lang:"es"},
{lang:"fi"},
{lang:"fr"},
{lang:"fr-be"},
{lang:"hr"},
{lang:"it"},
{lang:"ja"},
{lang:"lt"},
{lang:"lv"},
{lang:"mk"},
{lang:"no"},
{lang:"pl"},
{lang:"pt"},
{lang:"pt-br"},
{lang:"ru"},
{lang:"sl"},
{lang:"sv"},
{lang:"tk"},
{lang:"tr"}
        ]
      }
    }
  ),
  rdpScreenSize: new dojo.data.ItemFileReadStore({
    data: {
      identifier: "size", label: "size", items: [
        {size: "800x600"}, {size: "1280x1024"}]
    }
  })
};

// on store save post everything to server
stores.images._saveEverything = server.saveEverythingFn("/stabile/images");
stores.servers._saveEverything = server.saveEverythingFn("/stabile/servers");
stores.networks._saveEverything = server.saveEverythingFn("/stabile/networks");
stores.nodes._saveEverything = server.saveEverythingFn("/stabile/nodes");

window.stores = stores;           
window.server = server;

return stores;
});
