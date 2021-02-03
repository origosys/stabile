define([
"dojo/_base/connect",
"dojo/_base/lang",
"dojo/_base/array",
"dojo/topic",
"dojox/data/ClientFilter",
"dojox/data/JsonQueryRestStore",
"steam2/Service",
"steam2/models/Server",
"steam2/models/Image",
'stabile/ui_update',
"stabile/stores"
], function(connect, lang, arrayUtil, topic, ClientFilter, JsonRestStore, Service, Server, Image){

var parseResponse = function(response){
    // Not used anywhere!!
    // summary: parse the response on successful actions
    // response: String
    console.log("parsing response in steam2!!")
    var lines = response.split("\n");

    // Does not seem to be used
    function parseLine(line){
        line = line.slice(line.indexOf("=") + 1);
        // OK suspending ubuntu slet igen-0
        var parts = line.split(" ");
        var status = parts[0];
        var serverStatus = parts[1];
        var message = line.slice(status.length + 1);
        if(status == "OK"){
            return {status:status, message: message};
        } else {
            return {status:status, message:message, error:true};
        }
    }

    var results = [];

    arrayUtil.forEach(lines, function(l){
        if(l){
            var parsed = parseLine(l);

            dojo.publish("message", [{
                message: parsed.message,
                type: parsed.error ? "warning" : "message",
                duration: 3000
            }]);

            results.push(parsed);
        }
    });

    return results;
};

var reloadSystems = function() {
    systemsDataStore = new JsonRestStore({
        target: '/stabile/systems', // + (ui_update.session?"?s="+ui_update.session:""),
        idAttribute: 'uuid',
        syncMode:false,
        schema: {
            prototype: Server.prototype
        },
        cacheByDefault: true
    });
    return systemsDataStore;
};

var systemsDataStore = new JsonRestStore({
    target: '/stabile/systems/', // + (ui_update.session?"?s="+ui_update.session:""),
    idAttribute: 'uuid',
    syncMode:false,
    schema: {
       prototype: Server.prototype
    },
    query: {uuid:'*'},
    cacheByDefault: true
});

dojox.data.JsonRestStore.prototype.reset = function(uuid){
    this.clearCache();
    // remove all the existing elements from the index
//    console.log("Deleting from Dojo (systems)", this.target);
    for (idx in dojox.rpc.Rest._index) {
        if (uuid && uuid!=='norender') {
            if (dojox.rpc.Rest._index[idx].uuid == uuid) {
//                console.log("Deleting uuid from Dojo (systems): " + idx + ", " + uuid);
                delete dojox.rpc.Rest._index[idx];
            }
        } else if (idx.match("^" + this.target)) {
//            console.log("Deleting from Dojo (systems): " + idx);
            delete dojox.rpc.Rest._index[idx];
        }
    };
    this._updates = [];
    // clear the query cache
    //this.fetch({queryOptions:{cache:false}});
    //this.fetch({query:{uuid:"*"},queryOptions:{cache:false}});
    //this.close();
    //this.revert();

    console.log("refreshed target", this.target);
    if (uuid!=='norender') {
        if (this.target.match("systems")) {
            console.log("not rendering systems");
            home.grid.render();
        } else if (this.target.match("servers")) {
            console.log("rendering servers");
            servers.grid.render();
        } else if (this.target.match("images")) {
            console.log("rendering images");
            images.grid.render();
        } else if (this.target.match("networks")) {
            console.log("rendering networks");
            networks.grid.render();
        } else if (this.target.match("nodes")) {
            console.log("rendering nodes");
            nodes.grid.render();
        } else if (this.target.match("users")) {
            console.log("rendering users");
            users.grid.render();
        }
    }
    // very, very ugly :(
    setTimeout(function() {q = dojo.query('.irigo-tooltip'); q.irigoTooltip && q.irigoTooltip();},1000);
    return true;
}

var imagesDataStore = JsonRestStore({
    service: new Service('/stabile/images?action=list&_=/'),
    idAttribute: 'uuid',
    schema: {
        prototype: Image.prototype
    }
});



steam2.stores = {
    systems:systemsDataStore,
    images:imagesDataStore,
    parseResponse:parseResponse,
    reloadSystems:reloadSystems
};

topic.subscribe("servers:update", function(server){

    var port = server.displayport || server.port;
    var macip = server.displayip || server.macip;

    //delete server['id'];
    //delete server['displayip'];
    //delete server['displayport'];

    if(port){
        server.port = port;
    }
    if(macip){
        server.macip = macip;
    }


    function update(uitem){
        if(uitem && server['status']){
            console.log("servers:update (refreshing home tab)", uitem.status, server.status);
            systemsDataStore.setValue(uitem, 'status', server.status);
            var i = home.grid.getItemIndex(uitem);
            if (i!=-1) {
            //    console.log("updating row",i,uitem.name, uitem.system);
                home.grid.updateRow(i);
            }
            if (uitem.system) {
                systemsDataStore.fetchItemByIdentity({identity: uitem.system,
                    onItem: function(sysitem){
                        var j = home.grid.getItemIndex(sysitem);
                        if (j!=-1) home.grid.updateRow(j);
             //           console.log("updating system row",j, sysitem.name);
                }})
            }
            if (home.currentItem) home.updateVitals(home.currentItem);
            else home.updateVitals("update");
        }
    }
    if (server.uuid) {
//        systemsDataStore.fetchItemByIdentity({identity: server.uuid,
//            onItem: update,
//            onError: function() {;}
//        });
    }
});

//steam2.stores.images.fetch({});
//This for some reason causes this store to be reloaded from server whenever the image store in "steam1" is refreshed...
//connect.connect(stores.images, 'revert', function(){
//    steam2.stores.images.fetch({});
//});

return steam2.stores;

});

