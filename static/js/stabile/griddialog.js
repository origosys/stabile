define([
'steam2/user',
'steam2/stores',
'dijit/Dialog',
'dojox/html/entities'
], function(user, stores){

var griddialog = function(grid){

    var self = {
        item:null
    };

    var
    _dialog,
    _structure = grid.dialogStructure,
    _dialog_id = "editDialog",
    _handle,
    
    _getAttrsStr = function(obj){
        var attrs = [];
        for(var k in obj){
            var kv = k + '="' + obj[k] + '"';
            attrs.push(kv);
        }
        return attrs.join(' ');
    },
    
    // inserts buttons for each action in dialogActions
    _insertDialogButtons = function(){
        var ihtml = grid.getActionButtons(self.item, true);
        if (dojo.byId('dialogButtons')) dojo.byId('dialogButtons').innerHTML = ihtml;
        if(grid.onDialogButtons){ grid.onDialogButtons(self.item);}
    },
    
    _insertDialogExtras = function(){
        if(grid.dialogExtras){
            dojo.byId("editDialogExtras").innerHTML = grid.dialogExtras(self.item);
        }
    },
    
    _getTitle = function() {
        if(self.item.status == "new"){
            if (grid.name == "networks") return "Connection: Create New";
            else return grid.name + ": Create New";
        }
        else{
            if (grid.name == "users") return grid.name.substring(0,grid.name.length-1) + ": " + self.item.username;
            else return grid.name.substring(0,grid.name.length-1) + ": " + self.item.name;
        }
    };
    
    self.save = function() {
        var form = dijit.byId('dialogForm');
        var dstatus = self.item.status;
        // side effect: shows warnings in UI
        if(form.validate()) {
            if(self.item.status == "new"){
                if (grid.name == "users") {
                    self.item.username = dijit.byId("username").get('value');
                }
                self.item = grid.store.newItem(self.item);
            }

            dojo.forEach(_structure,function(s){
                if(s.field && dijit.byId(s.field)){ // A field may be restricted to only admins /co
                    var value = dijit.byId(s.field).get('value');
                    if ((s.field.endsWith("storagequota") || s.field.endsWith("memoryquota")) && value>0) value = value * 1024;
                    var gridvalue = grid.store.getValue(self.item, s.field);
                    if (typeof value == "boolean") value = value+'';
                    if (value != gridvalue && (grid.name=='monitors' || typeof gridvalue !== "undefined" )) {
                        grid.store.setValue(self.item, s.field, value);
                    }
                }
            });

            //console.log("saving", self.item, grid.store);
            if(grid.onBeforeSave){grid.onBeforeSave(self.item);}
            grid.save({
                onComplete: function(){
                    if(grid.name == "servers"){
            //            home.grid.updatePending = images.grid.updatePending = networks.grid.updatePending = true;
            //            home.grid.refresh();
                    } else if (grid.name == "images" || grid.name == "networks") {
                        home.grid.refresh();
                        servers.grid.refresh();
                        servers.grid.updatePending = home.grid.updatePending = true;
                    }
                    if(dstatus == 'new'){
                        //dojo.publish(grid.name + ':create');
                    } else { // Update corresponding fields in systems store
                        var id = self.item.uuid;
                        if(grid.name == "nodes") {
                            id = self.item.mac;
                        } else if (grid.name == "users") {
                            id = self.item.username;
                        }
                        if (grid.name == "servers") {
                            home.grid.store.fetchItemByIdentity({identity: id,
                                onItem: function(item){
                                    dojo.forEach(_structure,function(s){
                                        if(s.field && dijit.byId(s.field)){ // A field may be restricted to only admins /co
                                            var svalue = item[s.field];
                                            if (typeof svalue == "boolean") svalue = svalue+'';
                                            var value = self.item[s.field];
                                            if (value != svalue) {
                                                console.log("setting", value, svalue);
                                                item[s.field] = value;
                                                home.grid.store.setValue(item, s.field, value);
                                            }
                                        }
                                    });

                                }
                            })
                        }
                    }
                    self.hide();
                },
                onError: function() {console.log("Error saving", self);}
            });
        }
        else{
            console.log("Form not validated");
            return false;
        }
        return self.item;
    };

    self.show = function(item, onlyupdate){
        self.item = item;
        if (onlyupdate) {
            _insertDialogButtons();
        } 
        else{
            if(grid.onBeforeDialog) {
                grid.onBeforeDialog(self.item);
            }

            // var name = self.store.getValue(item, "name");
            var name = self.item.name;
            var items = [];

            dojo.forEach(grid.dialogStructure,
                function(s){
                    var val = self.item[s.field];
                    if (val && (s.field=='managementlink' || s.field=='upgradelink' || s.field=='terminallink') &&  self.item[s.field]=='--') val = '';
                    else if (val && s.field=='mac') val = ((self.item['status']=='shutoff' && self.item['locktonode']!='true')?"":val);
                    else if (s.field=='storagepool') {val = parseInt(val);}
                    else if (val && (s.field.endsWith("storagequota") || s.field.endsWith("memoryquota"))) {val = ((val>0)? Math.round(val/1024) : val) ;}
                    else val = dojox.html.entities.encode(""+val);
//                    else if (val) val = dojox.html.entities.encode(""+val);
//                    else val = "";
                    var dict = {
                        value: val,
                        kvs: _getAttrsStr(s.attrs),
                        type: s.type,
                        field: s.field,
                        autocomplete: "off",
                        label: s.name,
                        style: s.style ? s.style : "",
                        extra: s.extra ? s.extra(self.item) : "",
                        help: s.help ? '<a href="https://www.origo.io/info/stabiledocs/web/' + s.help + '" rel="help" target="_blank" class="irigo-tooltip">help</a>' : "",
                        restricted: s.restricted ? s.restricted : "",
                        checked: (s.type=="dijit.form.CheckBox" && self.item[s.field] && (self.item[s.field]==true || self.item[s.field]=='true'))?"checked":""
                    };
                    if ((s.restricted && !user.is_admin)) {
                        dict.style = "display:none;";
                        if (s.field == "password") dict.autocomplete = "new-password";
                        if (dict.type == "dijit.form.FilteringSelect") dict.type = "dijit.form.Select";
                        var t = [
                            '    <input id="${field}" style="${style}" dojoType="${type}" ${checked} value="${value}" autocomplete="${autocomplete}"></input>',
                            '    ${extra}'
                            ].join('');
                        items.push(dojo.string.substitute(t, dict));
                    }
                    else
                    if(s.formatter){
                        items.push(s.formatter(self.item));
                    } else{
                        var t = [
                            '<td>',
                            '    <div id="${field}label">${label}${help}</div>',
                            '</td>',
                            '<td>',
                            '    <input id="${field}" style="${style}" dojoType="${type}" ${kvs} ${checked} value="${value}" autocomplete="new-password"></input>',
                            '    ${extra}',
                            '</td>'].join('');
                        items.push(dojo.string.substitute(t, dict));
                    }
                });

            var content = items.join('<tr/><tr>');
            content = [
                '<form id="dialogForm" autocomplete="off" dojoType="dijit.form.Form"">',
                '<div id="dialogDiv">',
                '<div style="overflow:auto;">',
                '<table style="width:100%;" class="dialogFormTable"><tr>' + content + '</tr></table>',
                '<div id="editDialogExtras"></div>',
                '</div>',
                '</div>',
                '<div style="padding: 10px 13px 10px 10px; border-top: 1px solid #e5e5e5; height:50px;">',
                '<div id="dialogButtons"></div>',
                '</div>',
                '</form>'].join('');

            _dialog = dijit.byId(_dialog_id);
            if(!_dialog){ // else reuse the last one
                _dialog = new dijit.Dialog(
                {
                    id: _dialog_id,
                    /*
                    onCancel: function(){
                        self.onClose();
                        self.hide();
                        return true;
                    },
                    onClose: function(){
                        self.onClose();
                        self.hide();
                        return true;
                    }, */
                    title: "Settings"
                });
            }
            _dialog.set('content', content);
            _dialog.set('title', _getTitle());
            _dialog.show();

            _insertDialogExtras();
            _insertDialogButtons();

            var q = dojo.query('.irigo-tooltip');
            q.irigoTooltip && q.irigoTooltip();
            if(grid.onDialog){ grid.onDialog(self.item); }

            if(!_handle){
                dojo.subscribe(grid.name + ":update", function(task){
                    self.update(task);
                });
            }
        }
    };

    self.hide = function(){
        dojo.unsubscribe(_handle);
        _handle = null;
        if (_dialog) {
            _dialog.hide();
            _dialog.destroyRecursive();
        }
    };

    self.onClose = function(){
        self.hide();
    };

    self.isOpen = function(){
        return _dialog ? _dialog.open : false;
    };

    self.update = function(task){
        if ((task.status && task.status == "new")) {
            return;
        } else if(task.tab == "nodes"){
            if(self.item.mac && self.item.mac !== task.mac) return;
        } else if(task.tab == "users"){
            if(self.item.username && self.item.username !== task.username) return;
        } else if(self.item.uuid && self.item.uuid !== task.uuid){
            return;
        }

        if (dojo.byId('status') && task.status) {
            self.item.status = task.status;
            dijit.byId('status').set('value', task.status);
        }

        if (dojo.byId('name') && task.name) {
            self.item.name = task.name;
            dijit.byId('name').set('value', task.name);
        }
        self.show(self.item, true);
    };

    return self;
};
window.griddialog = griddialog;
return griddialog;

});


