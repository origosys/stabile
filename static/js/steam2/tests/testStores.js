define([
"doh", 
"dojo/_base/Deferred",
"dojo/json",
"dojox/data/JsonRestStore",
"dojox/data/AndOrWriteStore",
"dojo/data/ItemFileReadStore",
"stabile/stores",
"../stores",
"../models/Server"
], function(doh, Deferred, JSON, JsonRestStore, AndOrWriteStore, ItemFileReadStore, oldStores, stores, Server){

    var server = new Server({uuid:1, image:'/image1', image2:'/image2'});
    var serverData = [server];
    var imagesByPathData = {identifier: 'path', items:[{path:"/image1",uuid:11},{path:"/image2",uuid:22}]};
    var imagesData = {identifier: 'uuid', items:[{uuid:11, path:'/image1', status:'used'},{uuid:22, path:'/image2', status:'used'}]};

    var serverMockService = function(query){
        var d = new Deferred();
        d.fullLength = serverData.length;
        d.resolve(serverData);
        return d;
    };

    serverMockService.put = function(uuid, jsonText){
        var d = new Deferred();
        d.resolve(JSON.parse(jsonText));
        return d;
    };

    var options  = stores.serversOptions;
    options.service = serverMockService;

    var oldServers = stores.servers;
    var oldImages = oldStores.images;
    var oldImagesByPath = oldStores.imagesByPath;

    doh.register("steam2.tests.testStores", [

        function should_parse_server_response(t){
            var response = "Stroke=OK starting ie6_windows_xp\nStroke=OK starting ubuntu slet igen-0";
            var parsed = stores.parseResponse(response);

            t.is("starting", parsed[0].status);
            t.is("starting ie6_windows_xp", parsed[0].message);

            t.is("starting", parsed[1].status);
            t.is("starting ubuntu slet igen-0", parsed[1].message);

            var errorResponse = "ERROR Image not ready, not starting ubuntu slet igen-0";
            var parsedError = stores.parseResponse(errorResponse);
            
            t.is("Image not ready, not starting ubuntu slet igen-0", parsedError[0].message);

            errorResponse = "\nStroke=ERROR problem destroying ubuntu slet igen 3\n";
            parsedError = stores.parseResponse(errorResponse);

            t.is("problem destroying ubuntu slet igen 3", parsedError[0].message);
            t.is(true, parsedError[0].error);
        }

        // TODO: implement this.

        // {
        //     name: "server_delete_should_transition_status_of_image_to_unused",
        //     setUp: function(){
        //         oldStores.images = new AndOrWriteStore({data: imagesData});
        //         oldStores.imagesByPath = new ItemFileReadStore({data: imagesByPathData});
        //         stores.servers = new stores.ServersDataStore(options);
        //     },
        //     runTest: function(){

        //        var expectedUuidImage1 = 11;
        //        var expectedStatusImage1 = 'unused';
                
        //        stores.servers.deleteItem(server);

        //        var def = new doh.Deferred();                
        //        oldStores.images.fetch({query: {uuid: 11}, onItem: function(item){
        //            if(item.uuid[0] != expectedUuidImage1){
        //                def.callback(new Error("Expected uuid to be: " + expectedUuidImage1));
        //            }
        //            else if(item.status[0] != expectedStatusImage1){
        //                def.callback(new Error("Expected status to be: " + expectedStatusImage1));
        //            }
        //            else{
        //                def.callback(true);
        //            }
        //        }});
        //        return def;
        //     },
        //     tearDown: function(){
        //         stores.servers = oldServers;
        //         oldStores.images = oldImages;
        //         oldStores.imagesByPath = oldImagesByPath;
        //     }
        // },

        // {
        //     name: "server_delete_should_transition_status_of_image2_to_unused",
        //     setUp: function(){
        //         oldStores.images = new AndOrWriteStore({data: imagesData});
        //         oldStores.imagesByPath = new ItemFileReadStore({data: imagesByPathData});
        //         stores.servers = new stores.ServersDataStore(options);
        //     },
        //     runTest: function(){

        //        var expectedUuidImage2 = 22;
        //        var expectedStatusImage2 = 'unused';
                
        //        stores.servers.deleteItem(server);
                
        //        var def = new doh.Deferred(); 
        //        oldStores.images.fetch({query:{uuid: 22}, onItem: function(item){
        //            if(item.uuid[0] != expectedUuidImage2){
        //                def.callback(new Error("Expected uuid to be: " + expectedUuidImage2));
        //            }
        //            else if(item.status[0] != expectedStatusImage2){
        //                def.callback(new Error("Expected status to be: " + expectedStatusImage2));
        //            }
        //            else{
        //                def.callback(true);
        //            }
        //        }});

        //        return def;
        //     },
        //     tearDown: function(){
        //         stores.servers = oldServers;
        //         oldStores.images = oldImages;
        //         oldStores.imagesByPath = oldImagesByPath;
        //     }
        // },

        // {
        //     name: "server_save_should_transition_status_of_image_to_used",
        //     setUp: function(){
        //         oldStores.images = new AndOrWriteStore({data: imagesData});
        //         oldStores.imagesByPath = new ItemFileReadStore({data: imagesByPathData});
        //         stores.servers = new stores.ServersDataStore(options);
        //     },
        //     runTest: function(){
        //        var expectedStatusImage = 'used';
                
        //        var s = stores.servers.newItem(new Server({image: '/image1'}));
        //        stores.servers.save();

        //        var def = new doh.Deferred(); 
        //        oldStores.images.fetch({query: {uuid:11}, onItem: function(item){
        //            if(item.status[0] != expectedStatusImage){
        //                def.errback(new Error("Expected status to be: " + expectedStatusImage + " was: " + item.status[0]));
        //            }
        //            else{
        //                def.callback(true);
        //            }
        //        }});

        //        return def;
        //     },
        //     tearDown: function(){
        //         stores.servers = oldServers;
        //         oldStores.images = oldImages;
        //         oldStores.imagesByPath = oldImagesByPath;
        //     }
        // }
    ]);

});

