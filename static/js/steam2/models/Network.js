define([
"dojo/_base/lang",
"dojo/_base/connect",
"dojo/_base/declare",
"dojo/string",
"stabile/stores",
"steam2/statusColorMap"
], function(lang, connect, declare, string, stores, statusColorMap){

var Network = declare("steam2.models.Network", null, {

    constructor: function(args){
        lang.mixin(this, args);
    }

});

/////////////////
// static methods
/////////////////

Network.editDialog = function(network){
    require(['stabile/networks', 'stabile/menu'], function(networks, menu){
        var pane = menu.networksPane;
        if(!pane.isLoaded){
            var tabs = menu.tabs;

            var h = connect.connect(networks, 'init', function(evt) {
                networks.grid.dialog.show(network);
                dojo.disconnect(h);
            });

            tabs.selectChild(pane);
        }
        else{
            networks.grid.dialog.show(network);
        }
    });
};

Network.editDialogFromUuid = function(uuid) {
    stores.networks.fetchItemByIdentity({identity: uuid, onItem: function(item) {
        Network.editDialog(item);
    }});
};

Network.getEditDialogLink = function(network, kwargs){
    var onClickAction = string.substitute("steam2.models.Network.editDialogFromUuid('${uuid}');", network);
    var colorStyle = "";

    if(kwargs && kwargs.action){
        onClickAction += kwargs.action + ';';
    }
    onClickAction += 'arguments[0].stopPropagation();return false;';

    if(kwargs && kwargs.colorize){
        colorStyle = 'color:' + statusColorMap.get(network.status); 
    }
    return string.substitute('<a style="${0}" href="#networks" onclick="${1}">${2}</a>', [colorStyle, onClickAction, network.name]);
};

return Network;

});

