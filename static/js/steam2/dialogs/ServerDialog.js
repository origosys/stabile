define([
"dojo/_base/lang",
"dojo/_base/declare",
"dojo/_base/array",
"dojo/_base/connect",
"dojo/_base/Deferred",
"dojo/DeferredList",
"dojo/on",
"dojo/dom",
"dojo/dom-construct",
"dojo/string",
"dojo/topic",
"dojox/form/Manager",
"dijit/form/Form",
"dijit/Dialog",
"dijit/registry",
"stabile/stores",
"steam2/user",
"steam2/models/Image",
"steam2/models/Network",
"steam2/models/Node",
"rdp/Viewer",
// used declaratively in form - server.html
"dijit/form/FilteringSelect",
"dijit/form/ValidationTextBox",
"dijit/form/TextBox",
"dijit/form/NumberSpinner",
"dijit/form/Select",
"steam2/FilteringSelectWithDeselect"

], function(lang, declare, arrayUtil, connect, Deferred, DeferredList, on, dom, domConstruct, string, topic,
FormManager, Form, Dialog, registry, stores, user, Image, Network, Node, rdpViewer){


return declare('steam2.dialogs.ServerDialog', [Dialog], {

    content: dojo.cache("steam2.forms","server.html"),

    server:null,

    postCreate: function(){
        this.inherited(arguments);
        this.refreshStores();
        
        var server = this.server;
        // fix inconsistent values
        if(server.autostart == "false"){
            server.autostart = false;
        }

        this._formManager = registry.byId('serverFormManager');
        this._formManager.startup();
        this._formManager.setFormValues(server);

        this.connect(this._formManager, '_onNodeChange', this._onNodeChange);
        this.connect(this._formManager, '_onSaveClick', this._onSaveClick);
        this.connect(this._formManager, '_onMountClick', this._onMountClick);
        this.connect(this._formManager, '_onMoveClick', this._onMoveClick);
        this.connect(this._formManager, '_onImageSelect', this._onImageSelect);
        this.connect(this._formManager, '_onImage2Select', this._onImage2Select);
        this.connect(this._formManager, '_onNetworkSelect', this._onNetworkSelect);
        this.connect(this._formManager, '_onNetwork2Select', this._onNetwork2Select);
        this.connect(this._formManager, '_onKeyboardChange', this._onKeyboardChange);
   
        this.connect(this.server, 'onTunnelConnect', this._onTunnelConnect);
        this.connect(this.server, 'onTunnelDisconnect', this._onTunnelDisconnect);
        this.connect(this.server, 'onViewerStart', this._onViewerStart);
        this.connect(this.server, 'onViewerStop', this._onViewerStop);
   
        this._widgets = this._formManager.formWidgets;

        if(server.status !== 'new'){
            this._imageLink = domConstruct.place('<a id="serverDialogImageDialogLink" href="#servers">Image</a>', 'serverDialogImageDialogLink', 'replace');
            this._image2Link = domConstruct.place('<a id="serverDialogImage2DialogLink" href="#servers">Image 2</a>', 'serverDialogImage2DialogLink', 'replace');
            this._nodeLink = domConstruct.place('<a id="serverDialogNodeDialogLink" href="#servers">Node</a>', 'serverDialogNodeDialogLink', 'replace');
            this._network1Link = domConstruct.place('<a id="serverDialogNetwork1DialogLink" href="#servers">Network</a>', 'serverDialogNetwork1DialogLink', 'replace');
            this._network2Link = domConstruct.place('<a id="serverDialogNetwork2DialogLink" href="#servers">Network 2</a>', 'serverDialogNetwork2DialogLink', 'replace');

            this.connect(this._imageLink, 'click', this.onImageClick);
            this.connect(this._image2Link, 'click', this.onImage2Click);
            this.connect(this._nodeLink, 'click', this.onNodeClick);
            this.connect(this._network1Link, 'click', this.onNetwork1LinkClick);
            this.connect(this._network2Link, 'click', this.onNetwork2LinkClick);

            this.connect(steam2.stores.systems, "onSet", function(item, attr, oldValue, newValue){

                // if we are currently editing the server which is updated
                // apply the updates
                if(server.uuid === item.uuid){
                    this.server = item;
                    // FIXME: should we repopulate all fields in the form?
                    if(attr == 'status'){
                        this._widgets.status.widget.set('value', item.status);                        
                        this.updateForm();
                    }
                }
            });
        }
        this.updateForm();
        var q = dojo.query('.irigo-tooltip', this.domNode);
        q.irigoTooltip && q.irigoTooltip();
    },
   
    onImageClick: function(){
        var server = this.server;
        if(!server.image || server.image === '--'){
            alert('There is no image associated with this server yet! Please pick an image and press save');
            return;
        }
        this.hide();
        Image.editDialogFromPath(server.image);
    },

    onImage2Click: function(){
        var server = this.server;
        if(!server.image2 || server.image2 === '--'){
            alert('There is no secondary image associated with this server!');
            return;
        }

        this.hide();
        Image.editDialogFromPath(server.image2);
    },

    onNodeClick: function(){
        var server = this.server;
        if(!server.mac || server.mac === '--'){
            alert('The server is not present at any node!');
            return;
        }
        this.hide();
        Node.editDialogFromUuid(server.mac);
    },

    onNetwork1LinkClick: function(){
        var server = this.server;
        if(!server.networkuuid1 || server.networkuuid1 === '--'){
            alert('There is no network associated with this server!');
            return;
        }
        this.hide();
        Network.editDialogFromUuid(this.server.networkuuid1);
    },

    onNetwork2LinkClick: function(){
        var server = this.server;
        if(!server.networkuuid2 || server.networkuuid2 === '--'){
            alert('There is no secondary network associated with this server!');
            return;
        }
        this.hide();
        Network.editDialogFromUuid(this.server.networkuuid2);
    },

    save: function(){
        var self = this;
        var server = this.server;
        var formManager = this._formManager;
     
        var formItem = formManager.gatherFormValues();
        if(formItem.status === 'new'){
            server = this.server = steam2.stores.systems.newItem(formItem);
        }
        else{
            // edit
            for(var k in formItem){
                if(lang.exists(k, server)){
                    server[k] = formItem[k];                    
                }
            }
            steam2.stores.systems.changing(server);
        }

        // images are paths not uuids workaround
        // var def = new Deferred();
        // function tryResolve(){
        //     if(def._image && def._image2){
        //         def.resolve({success:true});
        //     }
        // }

        // HACK: workaround missing image uuids
        // var set = steam2.stores.servers.setValue;
        // if(server.image != this._serverImageUuid){
        //     // image changed, it's now a uuid of an image
        //     if(server.image){
        //         stores.images.fetchItemByIdentity({identity: server.image, onItem: function(image) {
        //             // change back to old value to throw the onSet
        //             // event correctly
        //             server.image = self._serverImagePath;
        //             var path = stores.images.getValue(image, 'path');
        //             set(server, 'image', stores.images.getValue(image, 'path'));                    
        //             def._image = true;
        //             tryResolve();
        //         }});
        //     }
        //     else{
        //         server.image = self._serverImagePath;
        //         set(server, 'image', '');
        //         def._image = true;
        //         tryResolve();
        //     }
        // }
        // else{
        //     server.image = this._serverImagePath;
        //     def._image = true;
        //     tryResolve();
        // }

        // if(server.image2 != this._serverImageUuid2){
        //     // image2 changed, it's now a uuid of an image
        //     if(server.image2){
        //         stores.images.fetchItemByIdentity({identity: server.image2, onItem: function(image) {
        //             // change back to old value to throw the onSet
        //             // event correctly
        //             server.image2 = self._serverImagePath2;
        //             var path = stores.images.getValue(image, 'path');
        //             set(server, 'image2', stores.images.getValue(image, 'path'));                    
        //             def._image2 = true;
        //             tryResolve();
        //         }});
        //     }
        //     else{
        //         server.image2 = this._serverImagePath2;
        //         set(server, 'image2', '');
        //         def._image2 = true;
        //         tryResolve();
        //     }
        // }
        // else{
        //     server.image2 = this._serverImagePath2;
        //     def._image2 = true;
        //     tryResolve();
        // }

        // end of workaround for missing image uuids 

        // workaround for empty '' being '--' when POSTing to the backend
        for(var k in server){
            if(server.hasOwnProperty(k)){
                var v = server[k];
                if(v == ''){
                    server[k] = '--';
                }
            }
        }
        
        // inconsitency at the backend.
        // '--' is not empty when autostart 

        if(server.autostart == '--'){
            server.autostart = 'false';
        }

        //  def.then(function(){
            topic.publish("message", {
                message:"Saving " + server.name,
                duration: 2000
            });
            return steam2.stores.systems.save({
                onError: function(){
                    topic.publish("message", {
                        message:"Saving " + server.name + " failed",
                        type: "warning",
                        duration: 2000
                    });
                },
                onComplete:function(){
                    self.hide();
                }
            });
        // });
    },

    onHide: function(){
        var self = this;
        // something fishy with dojo here
        // not everything is finished when the onHide triggers.
        setTimeout(function(){
            self.destroyRecursive();                       
        },0);
    },

    refreshStores: function(){
        var item = this.server;

        // NOTE: closing the store triggered an error in the
        // images grid. 
        if(lang.exists('images.grid.refresh')){
            images.grid.refresh();
        }
        else{
            stores.images.close();
        }
        stores.cdroms.close();
        stores.unusedNetworks.close();        
    },

    _onKeyboardChange:function(){
        var keymap = this._widgets.keyboard.widget.get('value');
        rdpViewer.keymap = keymap;
    },

    _onTunnelDisconnect: function(){
        var tunnelStartButton = this.server.getActionButton('start_tunnel');
        domConstruct.place(tunnelStartButton, 'serverDialogTunnelButton', 'only');
        domConstruct.place('<span>Java Console</span>', 'serverDialogConsoleLink', 'only');
    },

    _onTunnelConnect: function(){
        var tunnelStopButton = this.server.getActionButton('stop_tunnel');
        domConstruct.place(tunnelStopButton, 'serverDialogTunnelButton', 'only');
        domConstruct.place(this.server.getConsoleLink(), 'serverDialogConsoleLink', 'only');
    },

    _onViewerStop: function(){
        var viewerStartButton = this.server.getActionButton('start_viewer');
        domConstruct.place(viewerStartButton, 'serverDialogConsoleButton', 'only');        
    },

    _onViewerStart: function(){
        var viewerStopButton = this.server.getActionButton('stop_viewer');
        domConstruct.place(viewerStopButton, 'serverDialogConsoleButton', 'only');        
    },

    _onNodeChange: function(mac){
        // this value is read from Server when starting it
        this.mac = mac;
    },

    _onSaveClick: function(){
        if(this.validate()){
            this.save();
        }
    },

    _onMountClick: function(){
        var cdrom = this._widgets.cdrom.widget.get('value');
        this.server.mount(cdrom);
    },

    _onMoveClick: function(){
        var mac = this._widgets.mac.widget.get('value');
        this.server.move(mac);
    },

    _onImage2Select: function(){
        // summary: change the query for the other image widget
        var otherImageWidget = this._widgets.image.widget;
        otherImageWidget.query = this.getImageQuery('image');
        this.filterNics();
        this.filterNodes();
    },

    _onImageSelect: function(){
        // summary: change the query for the other image widget
        var otherImageWidget = this._widgets.image2.widget;
        otherImageWidget.query = this.getImageQuery('image2');
        this.filterNics();
        this.filterNodes();
    },
                   
    _onNetworkSelect: function(uuid, name, widget){
        var otherNetworkWidget = this._widgets.networkuuid2.widget;
        otherNetworkWidget.query = this.getNetworkQuery('networkuuid2');
    },

    _onNetwork2Select: function(uuid, name, widget){
        var otherNetworkWidget = this._widgets.networkuuid1.widget;
        otherNetworkWidget.query = this.getNetworkQuery('networkuuid1');
    },
                                     
    getNetworkQuery: function(field){
        // summary: get the query for the given field
        var widget;
        var other;

        if(field === 'networkuuid1'){
            widget = this._widgets.networkuuid1.widget;
            other = this._widgets.networkuuid2.widget.item;
        }
        else if(field === 'networkuuid2'){
            widget = this._widgets.networkuuid2.widget;
            other = this._widgets.networkuuid1.widget.item;
        }
        
        var network = widget.item;
        var complexQuery = 'uuid:*';

        if(other){
            complexQuery += ' AND !uuid:' + other.uuid;
        }

        return {complexQuery:complexQuery};
    },

    getImageQuery: function(field){
        // summary: get the query for the given field
        // field:
        //    the field to get the query for 
        var widget;
        var other;
        if(field === 'image'){
            widget = this._widgets.image.widget;
            other = this._widgets.image2.widget.item;
        }
        else if(field === 'image2'){
            widget = this._widgets.image2.widget;
            other = this._widgets.image.widget.item;
        }
        var image = widget.item;

        var complexQuery = 'user:' + user.username + ' AND status:unused AND !type:iso AND !path:*.master.qcow2';
        if(other){
            complexQuery += ' AND !uuid:' + other.uuid + ' AND type:' + other.type;
        }

        // allow the servers current image to be selected if it has one
        if(image && this._serverImageUuid && field === 'image'){
            complexQuery += ' OR uuid:' + this._serverImageUuid;
        }
        else if(image && this._serverImageUuid2 && field === 'image2'){
            complexQuery += ' OR uuid:' + this._serverImageUuid2;
        }

        return {complexQuery:complexQuery};
    },

    filterNodes: function(){
        // summary: filter nodes to the availble ones cf. hypervisor
        var nodeSelect = this._widgets.mac.widget;
        var image1 = this._widgets.image.widget.item;
        var image2 = this._widgets.image2.widget.item;

        // pick the one that is not empty
        var image = image1 || image2;
        var hypervisor;
        if(image){
            var type = stores.images.getValue(image, 'type');            
            hypervisor = Image.getHypervisor(type);
        }

        switch(hypervisor){
            case "kvm":
                nodeSelect.query = {identity: 'kvm', status: 'running'};
                break;
            case "vmdk":
                nodeSelect.query = {identity: 'vmdk', status: 'running'};
                break;
            default:
                nodeSelect.query = {status: 'running'};
        }
    },

    filterNics: function(){
        // summary: filter nics to the availble ones cf. hypervisor
        var nicSelect = this._widgets.nicmodel1.widget;
        var image1 = this._widgets.image.widget.item;
        var image2 = this._widgets.image2.widget.item;

        // pick the one that is not empty
        var image = image1 || image2;
        var hypervisor;
        if(image){
            var type = stores.images.getValue(image, 'type');            
            hypervisor = Image.getHypervisor(type);
        }

        switch(hypervisor){
            case "kvm":
                nicSelect.query = {hypervisor: '*kvm*'};
                break;
            case "vmdk":
                nicSelect.query = {hypervisor: '*vbox*'};
                break;
            default:
                // show all nics
                nicSelect.query = {};
        }
    },

    updateWidgets: function(){
        // summary: updates the visual stuff in the form
        var server = this.server;
        var byId = dom.byId;

        function disable(widgets){
            arrayUtil.forEach(widgets, function(widgetWrapper){
                widgetWrapper.widget.set('disabled', true);
            });
        }
     
        function enable(widgets){
            arrayUtil.forEach(widgets, function(widgetWrapper){
                widgetWrapper.widget.set('disabled', false);
            });
        }

        //show move row if user is admin.
        if(user.is_admin){
            dojo.query('.serverDialogAdminRow').style("display", "");
        }

        if(server.status === "new"){
            this.set('title', 'Create new server');
            byId('serverDialogStatusRow').style.display = 'none';
            byId('serverDialogUuidRow').style.display = 'none';
            byId('serverDialogTunnelRow').style.display = 'none';
            byId('serverDialogConsoleRow').style.display = 'none';
            byId('serverDialogMountButtonWrapper').style.display = 'none';
            byId('serverDialogMoveButtonWrapper').style.display = 'none';
            byId('serverDialogRdpKeyboardRow').style.display = 'none';
            byId('serverDialogDisplayRow').style.display = 'none';
        }
        else{
            this.set('title', 'Edit Server: ' + server.name);
            byId('serverDialogStatusRow').style.display = '';
            byId('serverDialogActions').innerHTML = server.getActionButtons();

            if(server.isPowered() && user.is_admin){
                byId('serverDialogDisplayRow').style.display = '';
            }
            else{
                byId('serverDialogDisplayRow').style.display = 'none';
            }

            if(server.isPowered()){
                byId('serverDialogMountButtonWrapper').style.display = '';
                byId('serverDialogMoveButtonWrapper').style.display = '';
            }
            else{
                byId('serverDialogMountButtonWrapper').style.display = 'none';
                byId('serverDialogMoveButtonWrapper').style.display = 'none';
            }

            if(server.status === "running"){
                byId('serverDialogTunnelRow').style.display = '';
                byId('serverDialogConsoleRow').style.display = '';
                if(server.display === 'rdp'){
                    byId('serverDialogRdpKeyboardRow').style.display = '';
                }
                else{
                    byId('serverDialogRdpKeyboardRow').style.display = 'none';
                }
            }
            else{
                byId('serverDialogTunnelRow').style.display = 'none';
                byId('serverDialogConsoleRow').style.display = 'none';
                byId('serverDialogRdpKeyboardRow').style.display = 'none';
            }
        }

        var widgets = this._formManager.formWidgets;
        var editWidgets = [
                widgets.boot,
                widgets.diskbus,
                widgets.image,
                widgets.image2,
                widgets.memory,
                widgets.networkuuid1,
                widgets.networkuuid2,
                widgets.nicmodel1,
                widgets.vcpu
            ];

        var readonlyWidgets = [
            widgets.name,
            widgets.autostart,
            widgets.cdrom,
            widgets.mountButton,
            widgets.boot,
            widgets.diskbus,
            widgets.image,
            widgets.image2,
            widgets.memory,
            widgets.networkuuid1,
            widgets.networkuuid2,
            widgets.nicmodel1,
            widgets.vcpu
        ];

        if(server.isPowered()){
            disable(editWidgets);
        }
        else{
            enable(editWidgets);
        }
          
        var hasTunnel = server.hasTunnel();
        if(server.isPowered() && !hasTunnel){
            this._onTunnelDisconnect();
            this._onViewerStop();
        }
        else if(hasTunnel){
            this._onTunnelConnect();
        }
        
        if(server.hasViewer){
            this._onViewerStart();
        }

        if (user.is_readonly) {
            disable(readonlyWidgets);
            document.getElementById("serverDialogTunnelRow").style.display = "none";
            document.getElementById("serverDialogConsoleRow").style.display = "none";
            document.getElementById("serverDialogRdpKeyboardRow").style.display = "none";
            document.getElementById("serverDialogDisplayRow").style.display = "none";
        } else {
            dijit.byId("dialogSaveButton").set('style', 'display:inline');
        }

    },

    updateQueries: function(){
        // summary: update the widget queries in the form.

        var server = this.server;
        var self = this;

        // FIXME: change server to include the uuid instead of the
        // path of images

        var def = new Deferred();
        def.then(function(){
            // wait for the uuids to be set self._serverImageUuid & self._serverImage2Uuid
            self._widgets.image.widget.query = self.getImageQuery('image');
            self._widgets.image2.widget.query = self.getImageQuery('image2');
            self.filterNics();
            self.filterNodes();
        });

        function tryResolve(){
            if(def._image && def._image2){
                def.resolve({success:true});
            }
        }

        // server rep contains image paths
        // lookup the uuid and set the value of the filtering select
        // which is uuid based

        // set the queries even if no image is selected
        if(!server.image || server.image == '--'){
            def._image = true;
            tryResolve();
        }
        else{
            var def1 = Image.getByPath(server.image);
            def1.then(function(item){
                self._serverImageUuid = stores.images.getValue(item, 'uuid');
                self._serverImagePath = stores.images.getValue(item, 'path');
                self._widgets.image.widget.set('value', self._serverImageUuid);

                def._image = true;
                tryResolve();
            });
        }

        if(!server.image2 || server.image2 == '--'){
            this._serverImageUuid2 = '';
            this._serverImagePath2 = '--';
            def._image2 = true;
            tryResolve();
        }
        else{
            var def2 = Image.getByPath(server.image2);
            def2.then(function(item){

                self._serverImageUuid2 = stores.images.getValue(item, 'uuid');
                self._serverImagePath2 = stores.images.getValue(item, 'path');
                self._widgets.image2.widget.set('value', self._serverImageUuid2);

                def._image2 = true;
                tryResolve();
            });
        }
        // end of workaround for missing image uuids 


        if(server.status !== 'new'){
            this._widgets.networkuuid1.widget.query = this.getNetworkQuery('networkuuid1');
            this._widgets.networkuuid2.widget.query = this.getNetworkQuery('networkuuid2');
            
            if(user.is_admin && server.isPowered()){
                var displayUrl = server.getDisplayLink();
                var link = string.substitute('<a id="serverDialogDisplayLink" href="${0}">${0}</a>', [displayUrl]);
                domConstruct.place(link, 'serverDialogDisplayLink', 'replace');
            }

            this._formManager.formWidgets.keyboard.widget.set('value', rdpViewer.keymap);
        }
        else{
            // populate the image widget with the first value from the
            // image store
            var q = stores.images.query(this.getImageQuery('image'), {count:1});
            q.forEach(function(item){
                self._widgets.image.widget.set('value', item.uuid);
            });

        }        
    },

    updateForm: function(){
        this.updateWidgets();
        this.updateQueries();
    }
});

});