define([
'dojo/_base/declare',
'dijit/layout/TabContainer',
'dijit/layout/ContentPane',
'steam2/user'
], function(declare, TabContainer, ContentPane, user){


var Menu = declare('stabile.Menu', null, {

    // dom ids of panes.
    // ids: ["home", "servers", "images", "networks"],
    // ids: ["home"],

    constructor: function(args, node){
        this.node = node;

        var tabs = this.tabs = new TabContainer({
            id: "tabContainer",
            'class':"tabContainer"
        });

        this.homePane = this.getContentPane('home');
        this.serversPane = this.getServersPane();
        this.imagesPane = this.getImagesPane();
        this.networksPane = this.getNetworksPane();
        
        tabs.addChild(this.homePane);
        tabs.addChild(this.serversPane);
        tabs.addChild(this.imagesPane);
        tabs.addChild(this.networksPane);


        if(user.is_admin){
            this.nodesPane = this.getNodesPane('nodes');
            tabs.addChild(this.nodesPane);
            require(['stabile/stores'], function(){
                stores.nodes.fetch({query:{mac: "*"}}); // initialize store
            });
        }

        tabs.placeAt(this.node);
        tabs.startup();
    },

    // gets a new dijit content pane.
    getContentPane: function(name){
        var title = 'Dashboard';
        //if (name == "servers") title = "machines";
        //if (name == "images") title = "disks";
        return new ContentPane({
            id: name,
            title: title,
            href: "/stabile/static/html/" + name + ".html",
            // we have a corresponding object For each pane,i.d.,home.init(), servers.init() ...
            // is called onload
            onLoad: function(){
                window[name].init();
            }
        });
    },

    getServers2Pane: function(){
        return new ContentPane({
            title: 'Servers',
            id: 'servers',
            href: '/stabile/static/html/servers2.html',
            onLoad: function(){
                require(['steam2/ServersGrid'], function(ServersGrid){
                    var grid = new ServersGrid({}, 'servers2-grid');
                    grid.startup();        
                });     
            }
        });
    },

    getServersPane: function(){
        return new ContentPane({
            title: 'Servers',
            id: 'servers',
            preload: true,
            href: '/stabile/static/html/servers.html',
            onLoad: function(){
                require(['stabile/servers'], function(){
                    servers.init();
                });     
            }
        });
    },

    getImagesPane: function(){
        return new ContentPane({
            title: 'Images',
            id: 'images',
            preload: true,
            href: '/stabile/static/html/images.html',
            onLoad: function(){
                require(['stabile/images'], function(){
                    images.init();
                });
            }
        });
    },

    getNetworksPane: function(){
        return new ContentPane({
            title: 'Connections',
            id: 'networks',
            preload: true,
            href: '/stabile/static/html/networks.html',
            onLoad: function(){
                require(['stabile/networks'], function(){
                    networks.init();
                });
            }
        });
    },

    getNodesPane: function(){
        return new ContentPane({
            title: 'Nodes',
            id: 'nodes',
            href: '/stabile/static/html/nodes.html',
            onLoad: function(){
                require(['stabile/nodes'], function(){
                    nodes.init();
                });
            }
        });
    },

    add: function(){
        // adds the menu to the dom, if the user has no servers the welcome tab is shown.

        // wrapped in functions to get the count of servers
        // from the async datastore

        // add as first tab ... 
    }
});  

var menu = new Menu({}, "tabs");
window.menu = menu;
return menu;

});
