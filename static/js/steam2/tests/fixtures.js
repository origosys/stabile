define([
"dojo/_base/Deferred",
"dojo/json",
"dojo/text!./images.json",
"dojo/text!./networks.json",
"dojo/text!./nodes.json",
"dojo/text!./servers.json",
"dojox/data/AndOrWriteStore",
"dojo/data/ItemFileReadStore",
"dojox/data/JsonRestStore",
"steam2/models/Server",
"steam2/stores"
], function(Deferred, JSON, images, networks, nodes, servers, AndOrWriteStore, ItemFileReadStore, JsonRestStore, Server, stores){

    images = JSON.parse(images);
    networks = JSON.parse(networks);
    servers = JSON.parse(servers);
    nodes = JSON.parse(nodes);

    var imagesData = {
        identifier: 'uuid',
        label: 'name',
        items: images
    };

    var networksData = {
        identifier: 'uuid',
        label:'name',
        items: networks
    };

    var nodesData = {
        identifier: 'mac',
        items: nodes,
        label: 'name'
    };

    var serversService = function(query){
        var d = new Deferred();
        d.fullLength = servers.length;
        d.callback(servers);
        return d;
    };
    serversService.put = function(id, json){
        var d = new Deferred();
        d.callback(JSON.parse(json));
        return d;
    };

    function  reset(){
        // old stores
        window.stores.networks = new AndOrWriteStore({data: networksData});
        window.stores.nodes = new ItemFileReadStore({data: nodesData});
        window.stores.images = new AndOrWriteStore({data: imagesData});
         
        // new
        steam2.stores.servers = new JsonRestStore({
            target: '/servers/',
            idAttribute: 'uuid',
            schema: {
                prototype: Server.prototype
            },
           service: serversService
        });
    }

    reset();

    return {
        images:images,
        networks:networks,
        servers:servers,
        reset:reset
    };

});