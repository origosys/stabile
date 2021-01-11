define([
"dojo/on",
'dojo/_base/lang',
'steam2/statusColorMap',
'steam2/user',
'stabile/griddialog',
'dojox/grid/DataGrid',
'dojo/string',
'stabile/stores'
], function(on, lang, statusColorMap, user){

var grid = {

    // Gets a text representation of an action button with action handlers.
    actionButton: function(args){
        var actionHandler;
        args.title = args.title || args.action;
        if(args.confirm){
            if (args.actionHandler)
                actionHandler = "grid.actionConfirmDialog('" + args.id + "','" + args.action + "','" + args.name + "','" + args.title + "','" + args.type + "','" + args.actionHandler + "')";
            else
                actionHandler = "grid.actionConfirmDialog('" + args.id + "','" + args.action + "','" + args.name + "','" + args.title + "','" + args.type + "')";
        }
        else{
            if (args.actionHandler)
                actionHandler = args.actionHandler + "('" + args.id + "','" + args.action + "','" + args.type + "')";
            else
                actionHandler = "grid.actionHandler('" + args.id + "','" + args.action + "','" + args.type + "')";
        }
        // left out button text intentionally since image replacement didn't work out in IE
        var t = '<button type="button" title="${title}" class="action_button ${action}_icon" id="${action}_${id}" onclick="${actionHandler};return false;"><span>${action}</span></button>';
        args.actionHandler = actionHandler;
        return dojo.string.substitute(t, args);
    },

    actionCheckBox: function(args){
        return '<input id="bulk-action-' + args.id + '" "class="bulk-action" type="checkbox" />';
    },

    // Gets a text representation of a save button.
    // args:
    //    type {String}: grid to save, e.g., images, servers
    saveButton : function(type){
        // returning false, to disable form submit
        var actionHandler = "grid.saveHandler('" + type + "'); return false;";
        var t = '<button type="submit" title="Save" class="btn btn-sm btn-primary pull-right" onclick="${actionHandler}">Save</button>';
        return dojo.string.substitute(t, {'actionHandler':actionHandler});
    },

    // save the contents of the dialog.
    // FIXME: bad naming
    // args:
    //    name {String}: name of grid object
    saveHandler : function(name){
        // FIXME: action "" == "save"
        // We have to set the action since there might be a leftover from an
        // old action
        if (window[name].grid.dialog.item.action) { // action is not initialized for new items //co
            window[name].store.setValue(window[name].grid.dialog.item, 'action', "");
        }
        window[name].grid.dialog.save(); 
     },

    // Shows actions confirm dialog.
    // args:
    //    id {String}: id of item
    //    action {String}: the action to perform
    //    name {String}: the name of the object, e.g., servers, images
    actionConfirmDialog: function(id, action, name, title, type, myactionHandler){
        if(!id || !action || !name || !title || !type){
            console.error("not all arguments supplied!", arguments);
        }
        var actionHandler = "grid.actionHandler";
        if (myactionHandler) actionHandler = myactionHandler;
        var content = [
            '<div align="center" style="margin: 18px;"><p>Are you sure you want to ${title}</p>',
            '<div>',
            '<button class="btn btn-danger btn-sm" onClick="' + actionHandler + '(\'${id}\',\'${action}\',\'${type}\');dijit.byId(\'confirmDialog\').hide()">OK</button> ',
            '<button class="btn btn-info btn-sm" onClick="dijit.byId(\'confirmDialog\').hide()">Cancel</button></button>',
            '</div></div>'].join('');
        content = dojo.string.substitute(content, {'id':id, 'action':action, 'type': type, 'title':title});
        var dialog = dijit.byId('confirmDialog');
        if(!dialog){
            dialog = new dijit.Dialog({ id: 'confirmDialog', style: "width: 300px"});
        }
        dialog.set('title', type + ": " + name);
        dialog.set('content', content);
        dialog.show();
        return dialog;
    },

    alertDialog: function(title, content, myactionHandler, parm1, parm2){
        var content = [
            '<div align="center" style="padding:10px;">',
            content,
            '<div>',
            '<button class="btn btn-primary" onClick="' + myactionHandler + '(\'${parm1}\',\'${parm2}\'); dijit.byId(\'alertDialog\').hide()">OK</button>',
            '</div></div>'].join('');
        content = dojo.string.substitute(content, {'parm1':parm1, 'parm2':parm2});
        var dialog = dijit.byId('alertDialog');
        if(!dialog){
            dialog = new dijit.Dialog({ id: 'alertDialog', style: "width: 300px"});
        }
        dialog.set('title', title);
        dialog.set('content', content );
        dialog.show();
        return dialog;
    },

    // Performs the given action on the given object.
    actionHandler: function(id, action, type){
        var store = stores[type];
        var item = store.fetchItemByIdentity({
            identity: id,
            onItem: function(item, request){
                // HACK: special case when dowloading images.
                // FIXME: move these specialcases away.
                if(action == "download"){
                    // somehow, path isn't of the String type: appending "" to it to ensure that.
                    //window.location.href = (item.path + "").replace('/mnt/stabile/images/', '/stabile/download/');
                    //window.location.href = "/stabile/images?action=download&image=" + escape(item.path + "");
                    window.location.href = "/stabile/images?action=download&uuid=" + item.uuid;
                      return;
                }

                var data = {
                    "items": [{uuid:store.getValue(item, "uuid"), action:action}]
                };

                if (type == "nodes") {
                    data = {"items": [{mac:item.mac, action:action}]};
                } else if (type == "users") {
                    data = {"items": [{username:item.username, action:action}]};
                }

                else if(action == "start"){
                    var value = dijit.byId('mac') && dijit.byId('mac').get('value');
                    if (user.is_admin && value && value!="" & value !="--") {
                        data = {
                            "items": [{uuid:store.getValue(item, "uuid"), action:action, mac:value}]
                        };
                    }
                }
                
                if ((action == 'delete' || action=='deleteentirely') && (type == 'servers' || type == 'images'|| type == 'networks'|| type == 'nodes'|| type == 'users')) {
                    if(window[type].grid.dialog.isOpen()){window[type].grid.dialog.hide();}
                    store.deleteItem(item);
                    store.save({onComplete: function(){
                        if (type == 'servers')
                            home.grid.updatePending = images.grid.updatePending = networks.grid.updatePending = true;
                    }});
                } else {
                    // send action to server
                    dojo.xhrPost({
                        url: "/stabile/" + type,
                        postData: dojo.toJson(data),
                        load: function(response){

                            if (type == 'servers')
                                home.grid.updatePending = images.grid.updatePending = networks.grid.updatePending = true;

                            var newstatus = server.parseResponse(response)["status"];
                            console.log("response", item, newstatus);
                            if((action === "delete" /*|| action === "master" */) && window[type].grid.dialog.isOpen())
                                {window[type].grid.dialog.hide();}

                            // Also update systems on home tab when deleting servers
                            if (action == 'delete' && type == 'servers'){
                                steam2.stores.systems.fetchItemByIdentity({
                                    identity: id,
                                    onItem: function(item, request){
                                        if (action == 'delete') {
                                            home.grid.removeSystem(item);
                                        }
                                    }
                                });
                            }

                        },
                        error: function(error){
                            console.error("grid::actionHandler", error);
                        }
                    });
                }
                dojo.publish(type + ":" + action, item);
            }
        });
    },

    // Creates the grid.
    create: function(args){
    // exceptions are apparantly caught by dojo in onLoad
        if(!args){console.error("args must be supplied");}
        if(!args.store) {console.error("store property must be supplied in args");}
        if(!args.structure) {console.error("structure property must be supplied args");} //
        if(!args.dialogStructure) {console.error("dialogStructure property must be supplied args");}

        dojo.forEach(args.structure, function(s){
            if (s.hidden && user.is_admin) s.hidden = false;
        });

        var self = new dojox.grid.DataGrid({
            singleClickEdit:false,//true,
            clientSort: true,
            sortInfo: args.sortInfo || 1,
            store: args.store,
            structure: args.structure,
            rowSelector: "4px",
            query: args.storeQuery || { },
            queryOptions: { ignoreCase:true, cache:true },
            autoRender: true,
            autoHeight: false,
            rowsPerPage: 2000,
            selectionMode: "single",
            class: args['class'] || "grid-div",

            renderTooltip: function(){
                //var q = dojo.query('.irigo-tooltip', this.domNode);
                var q = dojo.query('.irigo-tooltip');
                if(q.irigoTooltip){q.irigoTooltip();}
            },
            postrender: function(){
                this.renderTooltip();
                if(this.onPostRender) {this.onPostRender();}
            }
            // autoHeight: true // is broken
        }, args.domnode);

        self.model = args.model;
        self.name = args.name;
        self.dialogStructure = args.dialogStructure;
        self.dialogExtras = args.dialogExtras;
        self.rowStyler = args.rowStyler;
        self.updatePending = true;

        if(args.canSort){self.canSort = args.canSort;}

        //Fixme: onDialog no longer used...?
        //self.onDialog = args.onDialog;
        self.onDialogButtons = args.onDialogButtons;
        self.onBeforeDialog = args.onBeforeDialog;
        self.onPostRender = args.onPostRender;
        self.currentEditHandler = null;
        self.onBeforeSave = args.onBeforeSave;
        self.getActionButtons = args.getActionButtons;

        self.dialog = griddialog(self);

        self.onStyleRow = function(row){
            /*var item = self.getItem(row.index);
            if(item){
                var status = self.store.getValue(item,"status");
                var color = statusColorMap.get(status);
                row.customStyles = "cursor:pointer; color:" + color;
                dojo.setStyle(self.getRowNode(row.index), "color", statusColorMap.get(status)); // ugly
                if(self.rowStyler){self.rowStyler(row, item);}
            };*/
        };

        on(self, "styleRow", function(row){
            row.customStyles = "cursor:pointer;";
            var item = self.getItem(row.index);
            if(item){
                //var status = self.store.getValue(item,"status");
                //var color = statusColorMap.get(status);
                var color = statusColorMap.get(item.status);
                //row.customStyles += "color:" + color + ";";
                row.customClasses += " " + color;
                self.focus.styleRow(row);
                //self.edit.styleRow(row);
                //dojo.setStyle(self.getRowNode(row.index), "color", color); // ugly
                if(self.rowStyler){self.rowStyler(row, item);}
            };
        });

        self.onFetchError = function(err,req) {
            //location = "/stabile/auth/login";
        };

        self.refresh = function(){
            var storename;
            if (self.store == stores['servers']) storename = "servers";
            else if (self.store == stores['images']) storename = "images";
            else if (self.store == stores['networks']) storename = "images";
            else if (self.store == stores['systems']) storename = "systems";
            else if (self.store == stores['users']) storename = "users";
            else if (self.store == stores['nodes']) storename = "nodes";
            console.log("refreshing", storename, self);
            self.store.reset();
        };

        self.refreshRow = function(task, idprop) {
            if (!idprop) idprop = "uuid";
            self.store.fetchItemByIdentity({identity: task[idprop],
                onItem: function(item){
                    for (var key in task) {
                        if (key=='id' || key=='sender' || key=='timestamp' || key=='type' || key=='uuid') {;}
                        else if (item[key]) {
                             item[key] = task[key];
                        }
                    }
                    self.store.save();
                    var i = self.getItemIndex(item);
                    if (task.tab == 'images' && images.grid.getRowNode(i)) images.grid.getRowNode(i).style["font-weight"]='';
                    self.updateRow(i);
                    self.updateRowStyles(i);
                    if (window[task.tab].updateSums) window[task.tab].updateSums();
                    //dojo.setStyle(self.getRowNode(i), "color", statusColorMap.get(item.status)); // ugly
                }
            });
        };

        self.handleSelectTab = function(e){
            if(!e || e.id == self.name){
                if (self.updatePending) {
                    self.updatePending = false;
                    console.log("doing pending refresh", self.name);
//                    self.refresh();
                }
                self.refresh();
                var that = this;
                setTimeout(function() {
                    that.renderTooltip();
                }, 1000)
            }
        }


        // save the grid and refresh it
        self.save = function(args){
            if(self.store.isDirty()){
                self.store.save({
                    onComplete: function(){
                        if (!self.store.isDirty()) {
                        //    if (!self.name == "images" && !self.name == "networks") {self.refresh();}
                        }
                        if(args.onComplete){
                            args.onComplete();
                        }
                    },
                    onError: function(){
                        console.log("Error saving grid");
    //                    self.refresh();
                    }
                });
            }
            else{
                IRIGO.toaster([{
                    message: "Nothing to commit!",
                    type: "message",
                    duration: 3000
                }]);
            }
        };

        self.newItem = function(){
            var model = self.model();
            self.dialog.show(model);
        };

        self.itemClickHandler = function(event){
            var item = self.selection.getSelected()[0];
            if(!item){ // e.g. click on header
                return;
            }
            if(event && event.cell && event.cell.field == 'action' || event.cell.steamid == 'console'|| event.cell.steamid == 'terminal'){
                return;
            }
            if(item.id && (item.id=='0' || item.id=='1') && !user.is_admin){ // regular users can not edit built-in networks
                return;
            }
            self.dialog.show(item);
        };

        self.update = function(task){
            var tabid;
            if (dijit.byId('tabContainer')) tabid = dijit.byId('tabContainer').selectedChildWidget.id;
            if(self.dialog.isOpen()){
                return;
            }
            if(task.tab == self.name || task.force){
                self.refresh();
            }
        };

        //dojo.connect(ui_update, 'onUpdate', self, self.update);
        dojo.connect(self, 'onRowClick', self.itemClickHandler);
            return self;
    }// end of create
};

window.grid = grid;
return grid;
});





