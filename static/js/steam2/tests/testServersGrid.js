define([
"doh", 
"dojo/_base/Deferred",
"dojox/data/JsonRestStore",
"../ServersGrid",
"../models/Server"
], function(doh, Deferred, JsonRestStore, Grid, Server){

    var dataItems = [{
        "uuid" : "1",
        "display" : "vnc",
        "nicmac2" : "00:B7:4D:E6:AD:4f",
        "imagename" : "ubuntu slet igen image-0",
        "user" : "jakob@cabo.dk",
        "mac" : "--",
        "image2name" : "--",
        "name" : "ubuntu slet igen 3",
        "cdrom" : "/mnt/stabile/images/common/ubuntu-10.04-server-amd64.iso",
        "networkname2" : "nat",
        "nicmac1" : "00:d0:47:af:CC:8E",
        "port" : "5993",
        "diskbus" : "ide",
        "boot" : "cdrom",
        "memory" : 2048,
        "image2type" : "--",
        "vcpu" : 1,
        "networkid2" : "--",
        "autostart" : "true",
        "status" : "shutoff",
        "networkid1" : "1",
        "networkuuid1" : "1",
        "networkname1" : "network",
        "timestamp" : "1336459295.77002",
        "nicmodel1" : "rtl8139",
        "networkuuid2" : "0",
        "image" : "/mnt/stabile/images000/jakob@cabo.dk/ubuntu slet igen image-0.qcow2",
        "image2" : "--",
        "macname" : "--",
        "notes" : "--",
        "action" : "--",
        "macip" : "--",
        "imagetype" : "qcow2"
    },{
        "uuid" : "2",
        "display" : "vnc",
        "nicmac2" : "00:B7:4D:E6:AD:4f",
        "imagename" : "ubuntu slet igen image-0",
        "user" : "jakob@cabo.dk",
        "mac" : "--",
        "image2name" : "--",
        "name" : "ubuntu slet igen 3",
        "cdrom" : "/mnt/stabile/images/common/ubuntu-10.04-server-amd64.iso",
        "networkname2" : "nat",
        "nicmac1" : "00:d0:47:af:CC:8E",
        "port" : "5993",
        "diskbus" : "ide",
        "boot" : "cdrom",
        "memory" : 2048,
        "image2type" : "--",
        "vcpu" : 1,
        "networkid2" : "--",
        "autostart" : "true",
        "status" : "shutoff",
        "networkid1" : "1",
        "networkuuid1" : "1",
        "networkname1" : "network",
        "timestamp" : "1336459295.77002",
        "nicmodel1" : "rtl8139",
        "networkuuid2" : "0",
        "image" : "/mnt/stabile/images000/jakob@cabo.dk/ubuntu slet igen image-0.qcow2",
        "image2" : "--",
        "macname" : "--",
        "notes" : "--",
        "action" : "--",
        "macip" : "--",
        "imagetype" : "qcow2"
    }];
    
    var mockService = function(query){
        var d = new Deferred();
        d.fullLength = dataItems.length;
        d.callback(dataItems);
        return d;
    };

    var jsonStore = new JsonRestStore({
        target: '/foo/bar',
        idAttribute: 'uuid',
        schema: {
            prototype: Server.prototype
        },
        service: mockService
    });

    doh.register("steam2.tests.testServersGrid", [

        function shouldParseResponse(t){
            var j = jsonStore.fetch({onItem: function(i){console.log(i);}});

            // var response = "Stroke=OK starting ie6_windows_xp\nStroke=OK starting ubuntu slet igen-0";
            // var parsed = stores.parseResponse(response);

            // t.is("starting", parsed[0].status);
            // t.is("starting ie6_windows_xp", parsed[0].message);

            // t.is("starting", parsed[1].status);
            // t.is("starting ubuntu slet igen-0", parsed[1].message);            
        },

        function shouldGetActionButtons(t){
            var grid = new Grid({store:jsonStore});
            var fetch = jsonStore.fetch({});
            // NOTE: our stub service returns immediately
            // with the results
            var actions = grid.getBulkActions(fetch.results);
            t.is("destroy", actions.destroy);
            t.is("start", actions.start);
            t.is("delete", actions.delete);
            var actionsCount = 0;
            for(var a in actions){actionsCount++;};
            t.is(3, actionsCount);
        }
    ]);

    return {
        store: jsonStore
    };

});