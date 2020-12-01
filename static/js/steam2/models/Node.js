define([
"dojo/_base/lang",
"dojo/_base/connect",
"dojo/_base/declare",
"dojo/string",
"stabile/stores"
], function(lang, connect, declare, string){

var Node = declare("steam2.models.Node", null, {

    constructor: function(args){
        lang.mixin(this, args);
    }

});

/////////////////
// static methods
/////////////////

Node.editDialog = function(node){
    require(['stabile/nodes', 'stabile/menu'], function(nodes, menu){
        var pane = menu.nodesPane;
        if(!pane.isLoaded){
            var tabs = menu.tabs;

            var h = connect.connect(nodes, 'init', function(evt) {
                nodes.grid.dialog.show(node);
                dojo.disconnect(h);
            });

            tabs.selectChild(pane);
        }
        else{
            nodes.grid.dialog.show(node);
        }
    });
};

Node.editDialogFromUuid = function(uuid) {
    stores.nodes.fetchItemByIdentity({identity: uuid, onItem: function(item) {
        Node.editDialog(item);
    }});
};

Node.getEditDialogLink = function(node){
    var onClickAction = string.substitute("steam2.models.Node.editDialogFromUuid('${uuid}');return false;", node);
    return string.substitute('<a href="#nodes" onclick="${0}">${1}</a>', [onClickAction, node.name]);
};


return Node;

});

