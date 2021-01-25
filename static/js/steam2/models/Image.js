define([
"dojo/_base/lang",
"dojo/_base/connect",
"dojo/_base/declare",
"dojo/_base/Deferred",
"dojo/_base/xhr",
"dojo/dom",
"dojo/dom-construct",
"dojo/on",
"dojo/string",
"dojo/query",
"dijit/tree/ForestStoreModel",
"dijit/form/Button",
"fileTree/FileStore",
"fileTree/Tree",
"steam2/statusColorMap"
], function(lang, connect, declare, Deferred, xhr, dom, domConstruct, on, string, 
query, ForestStoreModel, Button, FileStore, Tree, statusColorMap){

var Image = declare("steam2.models.Image", null, {

    constructor: function(args){
        lang.mixin(this, args);
    }

});

/////////////////
// static methods
/////////////////

Image._restoresInProgress = {};

Image.editDialog = function(image){
    // FIXME: change image backend, change images, factor dialog out.
    require(['stabile/images', 'stabile/menu'], function(images, menu){
        var pane = menu.imagesPane;
        if(!pane.isLoaded){
            var tabs = menu.tabs;

            var h = connect.connect(images, 'init', function(evt) {
                images.grid.dialog.show(image);
                dojo.disconnect(h);
            });

            tabs.selectChild(pane);
        }
        else{
            images.grid.dialog.show(image);
        }
    });
};

Image.getByPath = function(path){
    var def = new Deferred();
    stores.images.fetch({query: {path:path}, onItem: function(image) {
        // Fetch the item with the correct properties?!?
        // since not all the properties are set in the other
        def.resolve(image);
    }});
    return def;
};

// FIXME: Change backend so the identifier is the uuid!
Image.editDialogFromPath = function(path) {
    // We need to translate the image path from server info to an image uuid
    var def = Image.getByPath(path);
    def.then(function(image){
        Image.editDialog(image);
    });
};

Image.getEditDialogLink = function(image, kwargs){
    var onClickAction = string.substitute("steam2.models.Image.editDialogFromPath('${path}');", image);
    var colorStyle = "";

    if(kwargs && kwargs.action){
        onClickAction += kwargs.action + ';';
    }
    onClickAction += 'arguments[0].stopPropagation();return false;';

    if(kwargs && kwargs.colorize){
        colorStyle = 'color:' + statusColorMap.get(image.status); 
    }
    return string.substitute('<a style="${0}" href="#images" onclick="${1}">${2}</a>', [colorStyle, onClickAction, image.name]);
};

Image.showFilesDialog = function(uuid){

    var domId = 'filesTree';
    var dialog = Image._dialog;

    if(Image._tree){
        Image._tree.destroy();
    }
    if(dialog){
        dialog.destroyRecursive();
    }

    var t = [
        '<div style="width:100%; min-height:300px; padding:10px;">',
            '<div id="filesTreeControls">',
                '<div style="float:left"><em>pick files to restore</em></div>',
                '<a href="//www.origo.io/info/stabiledocs/web/images/restore-files" rel="help" target="_blank" id="irigo-restore-files-tooltip">help</a>',
                '<button id="filesRestoreButton' + uuid + '" class="btn btn-success btn-sm pull-right" style="margin-bottom:4px;"',
                'onclick="Image._restoresInProgress[uuid] = true; Image.restore(uuid, Image._tree.getChecked()); dialog.hide();"',
                '>Restore files</button>',
            '</div>',
            '<div style="clear:both"></div>',
            '<div style="overflow:auto;max-height:400px">',
                '<div id="filesTreeLoader" style="text-align:center;overflow:auto"><img src="/stabile/static/img/loader.gif" /></div>',
                '<div id="filesTreeErrorMessage"></div>',
                '<div id="filesTreeWrapper"></div>',
            '</div>',
        '</div>'].join('\n');

    dialog = Image._dialog = new dijit.Dialog({id: "restoreDialog" + uuid});
    console.log("restore dialog", dialog);
    dialog.set('content', t);
    var q = query('#irigo-restore-files-tooltip', dialog.domNode);
    if(q.irigoTooltip){q.irigoTooltip();}

    dialog.set('title', 'Restore Files');

    var image = stores.images.fetchItemByIdentity({
        identity: uuid,
        onItem:function(iimage){
            console.log("got restore image:", uuid, iimage);
            var imageName = steam2.stores.images.getValue(iimage, 'name');
            dialog.set('title', 'Restore Files: ' + imageName);
    }});


    dialog.show();

    dialog.connect(dialog, 'hide', function(){
        if(!Image._restoresInProgress[uuid]){
            Image.unmount(uuid);
        } else {
            console.log("Not unmounting - restore in progress");
        }
    });

    $("#filesRestoreButton" + uuid).on('click', function() {
        Image._restoresInProgress[uuid] = true;
        var def = Image.restore(uuid, Image._tree.getChecked());
        def.then(function(){
            // delete Image._restoresInProgress[uuid];
            // Note: we leave it up to the backend to eventually
            // unmount in this case
        });
        dialog.hide();
    });

    var onMountSuccess = function(){
        // success
        dom.byId('filesTreeLoader').style.display = 'none';
        var node = domConstruct.place('<div>', 'filesTreeWrapper');
        Image.fileTree(uuid, node);
    };

    var onMountError = function(error){
        var errorMessage = "<span class='dijitContentPaneError'><span class='dijitInline dijitIconError'></span>${responseText}</span>";
        dom.byId('filesTreeLoader').style.display = 'none';
        dom.byId('filesTreeControls').style.display = 'none';
        dom.byId('filesTreeErrorMessage').innerHTML = string.substitute(errorMessage, error);
    };

    Image.mount(uuid).then(onMountSuccess, onMountError);
};

Image.actionButton = function(uuid){
    var actionHandler;
    var args = {};
    args.id = uuid;
    args.title = 'browse';
    args.actionHandler = "steam2.models.Image.showFilesDialog('" + uuid + "')";

    var t = '<button type="button" title="${title}" class="action_button browse_icon" id="browse_${id}" onclick="${actionHandler};return false;"></button>';
    return dojo.string.substitute(t, args);
};

Image.fileTree = function(uuid, node){

    var store = new FileStore({
        url: "/stabile/cgi/images.cgi?action=listfiles&uuid=" + uuid,
        pathAsQueryParam: true,
        urlPreventCache: false
    });

    var model = new ForestStoreModel({
        store: store,
        deferItemLoadingUntilExpand: true,
        rootId: '/',
        rootLabel: 'root'
    });

    var tree = new Tree({
        model: model,
        uuid:uuid
    }, dom.byId(node));

    Image._tree = tree;
    return tree;
};

Image.restore = function(uuid, files){
    if(!files || !files['length']){
        IRIGO.toaster([{message: "Please pick some files to restore!"}]);
        return null;
    }
    var load = function(){
    //    console.log('restore load', arguments);
        dojo.publish("message", [{
            message: "Restoring files into iso ...",
            type: "message",
            duration: 3000
        }]);
    };
    var error = function(error){
        console.error('restore error', arguments);
        dojo.publish("message", [{
            message: error.responseText,
            type: "error",
            duration: 3000
        }]);
    };
    var xhrData = {
        url: '/stabile/cgi/images.cgi',
        content: {
            action: 'restorefiles',
            uuid: uuid,
            files: files.join(':')},
        load:load,
        error:error
    };
    var def = xhr.post(xhrData);
    return def;
};

Image.unmount = function(uuid) {
    var load = function(){
        console.log('unmounted ...');
    };
    var error = function(){
        console.error('unmount', arguments);
    };
    var xhrData = {
        url: '/stabile/cgi/images.cgi?action=unmount&uuid=' + uuid,
        load:load,
        error:error
    };
    var def = xhr.get(xhrData);
    return def;
};

Image.mount = function(uuid){
   var load = function(){
       console.log('mounted ...');
   };
   var error = function(){
       console.error('error:', arguments);
   };
   var xhrData = {
       url: '/stabile/cgi/images.cgi?action=mount&uuid=' + uuid,
       load: load,
       error: error
   };
   var def = xhr.get(xhrData);
   return def;
};

Image.getHypervisor = function(imageType){
    switch(imageType){
      case "qcow2":
          return "kvm";
      case "vmdk":
      case "vhd":
      case "vdi":
          return "vbox";
      default:
          return null;
    }
};

return Image;

});

