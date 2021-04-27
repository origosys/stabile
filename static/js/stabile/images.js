define([
'dojo/_base/array',
'dojo/_base/connect',
'dojo/on',
'dojo/dom',
'dojo/dom-construct',
'stabile/formatters',
'stabile/grid',
'steam2/user',
'stabile/upload',
'stabile/stores',
'steam2/models/Server',
'steam2/models/Image',
'steam2/models/Node',
'helpers/uuid',
// used in the form
'dijit/form/SimpleTextarea',
'dijit/form/ComboBox',
'dijit/form/Form'
], function(arrayUtil, connect, on, dom, domConstruct, formatters, grid, user, upload, stores, Server, Image, Node){

    var images = {

        grid: {},

        /** image model */
        model : function(args){
            return dojo.mixin(
            {
                // FIXME: size / virtualsize is the same
                backup: '--',
                bschedule: 'manually',
                domains: '--',
                master: '--',
                name: "",
                path: '--',
                realsize: 0,
                backupsize: 0,
                size: 0,
                status: "new",
                type: "qcow2",
                user: user.username,
                uuid: Math.uuid().toLowerCase(),
                virtualsize: 10737418240, //10737418240, //can grow up to 10 GB
                storagepool: 0,
                managementlink: "",
                upgradelink: "",
                terminallink: "",
                getPath: function(){
                    this.name = this.name || console.error('name must be set before calling getPath');
                    var t = "/mnt/stabile/images/${user}/${name}.${type}";
                    return dojo.string.substitute(t, {user:user.username, name:this.name, type: this.type});
                },
                onSave: function(){
                    console.log("onSave");
                }
            }, args || {});
        },

        /** object name - for reflective lookup */
        name: 'images',
        sortInfo: 2,

        // initial query
        storeQuery: {
            type: 'user'
//            user: user.username,
//            complexQuery: "type:qcow2 OR type:vmdk OR type:vdi OR type:vhd OR type:img"
        },

        _searchQuery: "name:*",
        _storagepoolQuery:"storagepool:",
        _typeQuery: "type:user",
        _inited: false,

        /** grid structure */
        structure : [
            {
                field: 'name',
                name: 'Name',
                //width: '230px'
                width: 'auto'
            },
            {
                field: 'status',
                name: 'Status    <a href="https://www.origo.io/info/stabiledocs/web/images/status" rel="help" target="_blank" class="irigo-tooltip">help</a>',
                width: '76px'
                // ,

                // formatter: function(val, rowIdx, cell) {
                //     var t = '<span style="color:${color}">${val}</span>';
                //     var color = statusCodes.getColor(val);
                //     return dojo.string.substitute(t, { color: color, val: val });
                // }
            },
            //{ field: 'type', name: 'Type', width: '50px'},
            { field: 'domainnames', name: 'Server(s)', width: 'auto'},
            { field: 'user', name: 'Owner', width: '120px' },
            { field: 'type', name: 'Type', width: '40px' },
            { field: 'realsize', name: 'Usage (GB)', width: '70px',
                cellStyles: "text-align:right;",
                formatter: formatters.bytes2gbs
            },
            { field: 'virtualsize', name: 'Size (GB)', width: '65px',
                cellStyles: "text-align:right;",
                formatter: formatters.bytes2gbs
            },
            { field: 'snap1',
                name: 'Snapshot',
                width: '65px',
                constraint: { formatLength: 'short'},
                formatter: function(val, rowIds, cell){
                    if (isNaN(val)) {
                        return val;
                    }
                    var fn = dojo.hitch({formatLength: 'short'}, formatters.datetime);
                    return fn(Number(val)*1000);
                }
            },
            { field: 'action',
                name: 'Action <a href="//www.origo.io/info/stabiledocs/web/images/image-actions" rel="help" target="_blank" class="irigo-tooltip">help</a>',
                width: 'auto', //
                //    options: ["--", "clone","snapshot","revert","unsnap","master","unmaster","delete"]
                formatter: function(val, rowIdx, cell) {
                    var item = this.grid.getItem(rowIdx);
                    return images.getActionButtons(item);
                },
                hidden: user.is_readonly
            }
        ],

        dialogStructure : [
            {
                field:"name",
                name: "Name",
                type:"dijit.form.ValidationTextBox",
                attrs: {required:false}
            },
            {
                field: "status", name: "Status", type: "dijit.form.TextBox",
                attrs: {readonly:"readonly"}
            },
            {
                field: "uuid",
                name: "UUID",
                type: "dijit.form.TextBox",
                attrs: {readonly:"readonly"}
            },
            {
                field:"type", name: 'Type', type:"dijit.form.Select",
                help: "images/image-type",
                attrs:{ store: "stores.imageTypes", searchAttr:"type"    }
            },
            {
                field:"virtualsize", name:'Virtual Size <span id="humanVirtualSize" style="color:gray"></span>',
                type: "dijit.form.ComboBox",
                help: "images/virtual-size",
                style: "width: 150px;",
                attrs: {store: "stores.virtualSizes",
                    searchAttr:"size",
                    onChange: "images.dialogOnSizeChangeHandler(this, 'humanVirtualSize')"},
                extra: function(item){return " bytes";}
            },
            {
                field:"realsize", name:'Usage <span id="humanRealSize" style="color:gray"></span>',
                type: "dijit.form.TextBox",
                style: "width: 150px;",
                attrs:{readonly:"readonly", onChange: "images.dialogOnSizeChangeHandler(this, 'humanRealSize')"},
                extra: function(item){return " bytes";}
            },
            {
                field:"backupsize", name:'Backup <span id="humanBackupSize" style="color:gray"></span>',
                type: "dijit.form.TextBox",
                style: "width: 150px;",
                attrs:{readonly:"readonly", onChange: "images.dialogOnSizeChangeHandler(this, 'humanBackupSize')"},
                extra: function(item){return " bytes";}
            },
            {
                field:"storagepool", name:'Storage pool', type: "dijit.form.Select",
             //   extra: function(item){
             //     return "<button type=\"button\" id=\"move_button\" dojoType=\"dijit.form.Button\" onclick=\"images.move()\" style=\"font-size:80%;\">Move</button>";
             //   },
                attrs:{
                    store: "stores.storagePools",
                    searchAttr:"id",
                    sortByLabel:"false",
                    onChange: "images.dialogOnStoragepoolChangeHandler(this)"
                }
            },
            {
              field:"mac",
              name:'<span id="imageDialogNodeDialogLink">Node</span>',
              type: "dijit.form.FilteringSelect",
              restricted: true,
              attrs:{store: "stores.nodesReadOnly", searchAttr:"name", required:"false", query: "{storfree: /^\\d\\d/}" }
            },
            {
                formatter: function(image){
                    if(image.status != 'new'){
                        if(image.domains != '--'){
                            // called domains, but only one server right? - NO, masters may be used by multiple domains /co
                            var doms = image.domains.split(/, {0,1}/);
                            var domnames = image.domainnames.split(/, {0,1}/);
                            var serverEditLink = "";
                            for (var i in doms) {
                                serverEditLink += '<a nohref="#images" onclick="servers.grid.dialog.show(stores.servers.fetchItemByIdentity({identity: \'' + doms[i]  + '\'}));">' + domnames[i] + '</a> ';
                            }
                            return '<td>Server</td><td>' + serverEditLink + '</td>';
                        } else {
                            return '<td>Server</td><td>Not used by any of your servers</td>';
                        }
                    } else {
                        return '';
                    }
                }
            },
            {
                formatter: function(item){
                    if (item.status == "new") {
                        return "";
                    } else {
                        var dsnap1 = "--";
                        if (item.snap1 && item.snap1 != "--") {
                            dsnap1 = (new Date(Number(item.snap1)*1000)).toLocaleString();
                        }
                        return [
                            '<td>',
                            '    <div>Snapshot<a href="https://www.origo.io/info/stabiledocs/web/images/snapshot"',
                            '     rel="help" target="_blank" class="irigo-tooltip">help</a>',
                            '    </div>',
                            '</td>',
                            '<td><input id="snap1" dojoType="dijit.form.TextBox" readonly value="' + dsnap1 + '"></td>'].join('\n');
                    }
                }
                //field: "snap1", name:"Snapshot", type: "dijit.form.TextBox",
                //attrs: {readonly:"readonly"}
            },
            {
                field: "master", name:"Master (path)", type: "dijit.form.TextBox",
                restricted: true,
                attrs: {readonly:"readonly"}
            },
            {
                field: "mastername",
                name:"<a nohref=\"#\" onClick=\"home.showImageDialog(null);\">Master</a>",
                type: "dijit.form.TextBox",
                attrs: {readonly:"readonly"}
            },
            {
                field:"backup", name:'Backups',
                type: "dijit.form.FilteringSelect",
                style: "width: 250px;",
                extra: function(item){
                    return '<button type="button" id="restore_button" nodojoType="dijit.form.Button" class="btn btn-xs btn-info" onclick="window.images.restore(); return false;" style="font-size:80%; display: none;">Restore</button>';
                },
                attrs:{store: "stores.backups", searchAttr:"time", sortByLabel:"false", required:"false", value:"--"}
            },
            {
                field:"bschedule", name:'Backup schedule',
                type: "dijit.form.Select",
                help: "images/backup-schedule",
                attrs:{store: "stores.backupSchedules", searchAttr:"schedule", sortByLabel:"false"}
            },
            {
                field:"btime", name:'Last backup',
                type: "dijit.form.TextBox",
                attrs:{readonly:"readonly"},
                formatter: function(item){
//                    return '<td>Last backup</td><td><input id="btime" dojoType="dijit.form.TextBox" readonly value="' + item.btime + '"></td>';
                    if(!isNaN(item.btime) && item.status != "new"){
                        var dval = home.timestampToLocaleString(item.btime);
                        return '<td>Last backup</td><td><input id="btime" dojoType="dijit.form.TextBox" readonly value="' + dval + '"></td>';
                    } else {
                        return '<td>Last backup</td><td><input id="btime" dojoType="dijit.form.TextBox" readonly value="Never"></td>';
                    }
                }
            },
            {
                field:"created", name:'Created',
                type: "dijit.form.TextBox",
                attrs:{readonly:"readonly"},
                formatter: function(item){
                    if(!isNaN(item.created) && item.status != "new"){
                        var dval = home.timestampToLocaleString(item.created);
                        return '<td>Created</td><td><input id="created" dojoType="dijit.form.TextBox" readonly value="' + dval + '"></td>';
                    } else {
                        return '<td>Created</td><td><input id="created" dojoType="dijit.form.TextBox" readonly value="--"></td>';
                    }
                }
            },
            {
                field: "user",
                name: "User",
                type: "dijit.form.FilteringSelect",
                attrs: {
                    store: "stores.imageids",
                    searchAttr: "id",
                    required:"true",
//                    query: "{privileges: /(a|u)/}"
                }
            },
            {
                name: "Path",
                formatter: function(item){
                    if(user.is_admin && item.status != "new"){
                        return '<td>Path</td><td><input id="path" dojoType="dijit.form.TextBox" readonly value="' + item.path + '"></td>';
                    }
                    return "";
                }
            },
            {
                field:"installable",
                name: "Installable",
                type:"dijit.form.CheckBox",
                restricted: false, // only admins
                help: 'images/installable-images',
                attrs:{onchange: "this.value=this.checked?'true':'false';"}
            },
            {
                field:"managementlink",
                name: "Management link",
                type:"dijit.form.TextBox"
            },
            {
                field:"upgradelink",
                name: "Upgrade link",
                type:"dijit.form.TextBox"
            },
            {
                field:"terminallink",
                name: "Terminal link",
                type:"dijit.form.TextBox"
            },
            {
                field:"notes",
                name: "Notes",
                type:"dijit.form.SimpleTextarea",
                style: "width: 90%;"
            }
        ],

        dialogExtras : function(item){
            return "";
        },

        restore: function(){
            var item = images.grid.dialog.item;
            images.store.setValue(item, 'action', 'restore');
            // FIXME: which one is the right one? this
            //var value = ( dijit.byId('backup').get('value') ).replace("+", "--plus--"); //Todo: for some bizarre reason "+"-signs don't survive
            // FIXME: or this?
            var value = ( dijit.byId('backup').get('value') ); // Update: issue fixed in stores.js
            images.store.setValue(item, 'backup', value);
            images.store.save();
            images.grid.dialog.hide();
        },

        doZBackup: function() {
            console.log("Doing ZFS backup");
            $("#dozbackup").html('Backing up&hellip; <i class="fa fa-cog fa-spin"></i>').prop("disabled", true);
            return $.get("/stabile/images?action=zbackup", function(){$("#dozbackup").html('Backup now').prop("disabled", false);});
        },

        getActionButtons : function(item, include_save){
            if (user.is_readonly) return "";

            var name = item.name;
            var type = this.name;

            function actionButton(args){
                args.name = name;
                args.type = type;
                return grid.actionButton(args);
            }

            var id = item.uuid;
            var status = item.status; 
            var snapshot = item.snap1;

            // ['irigo'] == 'irigo' is true
            var _user = item.user; //store.getValue(item, 'user');
            var _type = item.type;

            if (!id) {
                console.log("Error - image has no uuid", item);
                return "";
            }
            var download_button = actionButton({'action':"download", 'id':id});

            var browse_button = steam2.models.Image.actionButton(id);

            var clone_button = actionButton({'action':"clone", 'id':id});
            var convert_button = actionButton({'action':"convert", 'id':id, 'title': 'convert to qcow2'});
            var inject_button = actionButton({'action':"inject", 'id':id, 'title': 'inject drivers'});
            var snapshot_button = actionButton({'action':"snapshot", 'id':id});
            var revert_button = actionButton({'action':"revert", 'id':id, 'confirm':true});
            var unsnap_button = actionButton({'action':"unsnap", 'id':id});
            var master_button = actionButton({'action':"master", 'id':id});
            var unmaster_button = actionButton({'action':"unmaster", 'id':id, 'title': 'unmaster'});
            var rebase_button = actionButton({'action':"rebase", 'id':id, 'title': 'rebase'});
            var backup_button = actionButton({'action':"backup", 'id':id});
            var delete_button = actionButton({'action':"delete", 'id':id, 'confirm':true});
            var save_button = include_save ? grid.saveButton(type) : "";
            var is_master = false;

            var buttons = "";


            if(status == "new"){
                return save_button;
            }

            /*if(status == "used" || status == "unused" || status == "active"){
                if (_type == "qcow2" && (_user == user.username || user.is_admin )) {
                    if(snapshot && snapshot[0] != '--'){
                        buttons += unsnap_button;
                        if(status == "used" || status == "unused") buttons += revert_button;
                    } else {
                        buttons += snapshot_button;
                    }
                }
            }*/

            if(status == "used" || status == "unused" || status == "paused") {
                if(item.storagepool != -1){
                    buttons += browse_button;                                    
                }

                if (_type == "qcow2" && (_user == user.username || user.is_admin )) {
                    var _masterReg = new RegExp("\\.master\\." + _type + "$");
                    is_master = _masterReg.test(item.path)?true:false;

                    if (!is_master && status != "paused") {
                        if(snapshot && snapshot != '--'){
                            buttons += unsnap_button;
                            buttons += revert_button;
                        } else {
                            buttons += snapshot_button;
                        }
                    }
                    if(item.master && item.master!="--" && (status=="unused" || status =="used")) { // this is a child, which may be rebased
                        if (is_master)  buttons += unmaster_button;
                    //    else
                        buttons += rebase_button;
                    }
                    if (item.storagepool != -1) {
                        if (is_master) {
                            is_master = true;
                            if (status=="unused") buttons += unmaster_button;
                        } else {
                            if (status=="unused") buttons += master_button;
                        }
                    }
                }
                if (_type != "iso") {
                    buttons += clone_button;
                }
                if (_type == "qcow2" && (status == "unused" || status == "used") && user.is_admin) {
                    buttons += inject_button;
                }
                if (_type == "img" || _type == "vmdk" || _type == "vhd") {
                    buttons += convert_button;
                }
                // We don't allow downloading of child images, master images may always be downloaded
                if(( /*(!item.master || item.master=="--") && */ (status=="used" || status =="unused") && (item.storagepool != -1))
                        || is_master) buttons += download_button;
            }

            if (
                    (_user == user.username || user.is_admin ) && item.backup!="disabled" &&
                    (status == "used" || status == "unused" || status == "paused" || (status == "active" && item.lvm == 1) )
            ) {
                buttons += backup_button;
            }

            if((status == "unused" || status == "uploading" || status == "downloading") && (_user == user.username || user.is_admin )) {
                buttons += delete_button;
            }

            if (buttons == "" && status != "active" && status.indexOf("backingup")==-1) {
                return '<img height="18px" alt="busy" src="/stabile/static/img/loader.gif">';
            }

            if (user.is_admin || item.user==user.username || status == "backingup") buttons += save_button;

            return buttons;
        },

        onBeforeDialog : function(item){
            if(item.path && item.path != '--'){
                stores.backups.url = "/stabile/images?action=listbackups&image=" +
                        escape(item.uuid);
                stores.backups.close();
            }
            else{
//                stores.backups.url = "/stabile/images?action=listbackups";
                stores.backups.url = '';
                stores.backups.close();
            }
        },

        onDialogButtons: function (item) {
            // update the human size field
            if (dijit.byId('virtualsize')) {
                dijit.byId('virtualsize').onChange();
                // disable resizing of existing images
                dijit.byId('realsize').onChange();
                dijit.byId('backupsize').onChange();
                var status = item.status;

                var disable = function(dijitId){
                    var elm = dijit.byId(dijitId);
                    elm && elm.set('disabled', true);
                    return elm;
                };
                var enable = function(dijitId){
                    var elm = dijit.byId(dijitId);
                    elm && elm.set('disabled', false);
                    return elm;
                };

                if (user.is_readonly) {
                    disable('name');
                }
                if((status != 'new' && status != 'unused'  && status != 'used') || user.is_readonly){
                    disable('virtualsize');
                }
                if(status == 'unused' && (user.is_admin || user.billto=='--' || (user.tktuser==user.billto && item.user==user.username)) && !user.is_readonly) {
                    enable('user');
                } else {
                    disable('user');
                }

                if(user.is_readonly || (item.user!=user.username && !user.is_admin)) {
                    disable('storagepool');
                } else if (status == 'unused') {
                    enable('storagepool');
                } else if (status == 'new') {
                    dijit.byId('storagepool').set('value', 0);
                    disable('storagepool');
                } else if (status == 'used') {
                    if (item.path.indexOf(".master." + item.type) != -1)
                        disable('storagepool');
                    else
                        enable('storagepool');
                } else {
                    disable('storagepool');
                }

                if (item.path.indexOf(".master.qcow2")==-1 || (item.user!=user.username && !user.is_admin)) disable('installable');

                if ((!user.is_admin && item.user!=user.username) || user.is_readonly) {
                    disable('name');
                    disable('notes');
                    disable('backup');
                    disable('backup');
                    disable('bschedule');
                    disable('restore_button');
                }

                if (dijit.byId('backup') && dijit.byId('backup').value=="disabled") {
                    document.getElementById('bschedulelabel').style.display = "none";
                    dijit.byId('bschedule').set('disabled', true).set('style', 'display:none');
                }

                if (status == 'new') {
                    var imgtypes = dijit.byId("type");
                    if (imgtypes) imgtypes.setStore(stores.imageTypes, imgtypes.value, {query:{type: /qcow2|vmdk|vdi|vhd|img/i}});
                }

                if (item.storagepool == -1 || status == 'active' || user.is_readonly) {
                    disable('mac');
                }
                
                if(item.status != "new"){
                    if (dijit.byId('type')) disable('type');
                } else{
                    disable('backup');
                }
            }
            var _masterReg = new RegExp("\.master\." + item.type + "$");
            is_master = _masterReg.test(item.path)?true:false;
            if (dijit.byId('master')) master = dijit.byId('master').value;
            if (master && master!="--") {
//                stores.images.fetch({query: {path:master+'*'}, onComplete: images.updateMasterName});
                stores.images.fetch({query: {path:master}, onComplete: images.updateMasterName});
            } else if (is_master) {
                if (dijit.byId('mastername')) dijit.byId('mastername').set("value", "This image is a master image");
                if (document.getElementById('masternamelabel')) document.getElementById('masternamelabel').innerHTML = "Master";
            } else {
                if (dijit.byId('mastername')) dijit.byId('mastername').set("value","--");
                if (document.getElementById('masternamelabel')) document.getElementById('masternamelabel').innerHTML = "Master";
            }
        },

        onPostRender: function(){
        //    images.updateSums();
        },

        rowStyler : function(row, item){
            var _type = item.type;
            var path = this.store.getValue(item, "path");
            if(path.indexOf(".master." + _type) != -1){
                row.customStyles += "font-weight:bold;";
            } else {
                row.customStyles = "cursor:pointer;";
            }
        },

        // since stop propagation is not working on the help button
        // we disable sorting.
        canSort: function(index){

            if(index === 8){ // action
                return false;
            }
            if(index === 2){
                // status! Something bug in the dojo dropdown button.
                // it doesn't stop the event onClicks although I have specified it!
                // Tooltip clicks then triggers a sort, and removal of the tooltip content.
                // Therefore returning false.
                return false;
            }
            return true;
        },

        // helpers
        dialogOnSizeChangeHandler : function(caller, id){
            var value = Number(caller.value);
            if (!isNaN(value)) {// i.e., not '--'
                dojo.byId(id).innerHTML = Math.round(value / (1024 * 1024 * 1024)) + ' GB';
            }
        },

        dialogOnStoragepoolChangeHandler : function(caller){
            var index = parseInt(caller.value);
            if (user.node_storage_allowed) index += 1; // "On node" is first item in array, so we add one
            var bschedule = dijit.byId("bschedule");
            var hostpath = caller.options[index].item.hostpath;
            var lvm = caller.options[index].item.lvm;
//            console.log("caller", caller.options[index].item);
            if (bschedule && (hostpath == "local" || hostpath == "node") && lvm==1)
                bschedule.setStore(stores.backupSchedules, bschedule.value);
            else
                bschedule.setStore(stores.backupSchedules, bschedule.value, {query:{schedule: /manually|none/i}});
        },

        updateMasterName : function(items) {
            if (items && items.name && dijit.byId("mastername")) {
                dijit.byId("mastername").set("value", items.name);
                if (dojo.byId('masternamelabel')) dojo.byId('masternamelabel').innerHTML =
                    '<a nohref="#" onClick="$.get(\'/stabile/images/' + items.uuid + '\',function(item) {home.showImageItemDialog(item)});">Master</a>'
    //                "<a href=\"#\" onClick=\"home.showImageDialog('" + items.path + "');\">Master</a>"
            } else {
                if (dijit.byId('mastername')) dijit.byId('mastername').set("value","--");
                if (dojo.byId('masternamelabel')) dojo.byId('masternamelabel').innerHTML = "Master";
            }
            stores.images.reset('norender');
        },

        updateMissingBackups : function(filter) {
            if (IRIGO.user.zfsavailable) $("#dozbackup").show();
            else $("#dozbackup").hide();
            if ($("li#imagestab.active").length == 1) {
                var imagesfilter = {domains: '*'};
                var carray;
                if (!home.currentItem) {
                } else if (home.currentItem.issystem) {
                    carray = home.currentItem.children;
                } else {
                    imagesfilter = {domains: home.currentItem.uuid};
                }
                stores.images.close();
                stores.images.fetch({query:imagesfilter, onComplete: function(result){
                    var d = Math.ceil( new Date() / 1000 );
                    var one_day=60*60*24;
                    var unique_imgs = new Array();
                    var no_backup = 0;
                    var no_24_backup = 0;
                    var master_no_backup = 0;
                    var lvm_no_schedule = 0;
                    var no_backup_list = "";
                    var no_24_backup_list = "";
                    var master_no_backup_list = "";
                    var lvm_no_schedule_list = "";
                    var backed_up = 0;

                    for (var i in result) {
                        if (result[i] && result[i].uuid && result[i].domains && result[i].domains!='--' && result[i].type!='iso') {
                            if (unique_imgs[result[i].uuid]) continue; // We have seen this before
                            else unique_imgs[result[i].uuid] = 1;
                            var cmatch = result[i];
                            if (cmatch) {
                                if (cmatch.lvm==1 && (!cmatch.bschedule || cmatch.bschedule=="--" || cmatch.bschedule=="manually")){
                                    lvm_no_schedule++;
                                    lvm_no_schedule_list += cmatch.name + "\n";
                                }
                                if (!cmatch.created || d-cmatch.created > one_day) {
                                    if (!cmatch.btime || cmatch.btime=='--') { // No backup at all
                                        if (cmatch.path.indexOf(".master.qcow2")!=-1) {
                                            if (!cmatch.appid || cmatch.appid=='--') { // no need to back up appstore masters
                                                if (cmatch.path.indexOf("/common/")!=-1) { // Only notify admins of missing common master backups
                                                    if (user.is_admin) {
                                                        master_no_backup++;
                                                        master_no_backup_list += cmatch.name + "\n";
                                                        console.log("missing master backup", cmatch);
                                                    }
                                                } else { // Notify of personal missing master backups
                                                    master_no_backup++;
                                                    master_no_backup_list += cmatch.name + "\n";
                                                }
                                            }
                                        } else {
                                            no_backup++;
                                            no_backup_list += cmatch.name + "\n";
                                            no_24_backup++;
                                            no_24_backup_list += cmatch.name + "\n";
                                        }
                                    } else if (d-cmatch.btime > one_day) { // Backup older than 24h and not a master
                                        if (cmatch.path.indexOf(".master.qcow2")==-1) {
                                            no_24_backup++;
                                            no_24_backup_list += cmatch.name + "\n";
                                        }
                                    } else {
                                        backed_up++;
                                    }
                                } else {
                                    if (cmatch.btime && cmatch.btime!='--') backed_up++;
                                }
                            }
                        }
                    }
                    var u = '<b>Missing backups:</b> ';
                    if (no_backup>0) u += "<span title=\"" + no_backup_list + "\">" + no_backup + " (none)</span>, ";
                    if (no_24_backup>0) u +=  "<span title=\"" + no_24_backup_list + "\">" + no_24_backup + " (none in 24h)</span>, ";
                    if (lvm_no_schedule>0) u +=  "<span title=\"" + lvm_no_schedule_list + "\">" + lvm_no_schedule + " (no schedule)</span>, ";
                    if (master_no_backup>0) u +=  "<span title=\"" + master_no_backup_list + "\">" + master_no_backup + " (masters)</span>, ";
                    u = u.slice(0,-2);
                    u += "";
                    if (no_backup+no_24_backup+lvm_no_schedule+master_no_backup>0)
                        home.missingbackups.innerHTML = u;
                    else if (backed_up>0)
                        home.missingbackups.innerHTML = '<span style="font-size:90%; color:#AAAAAA;">All your images are backed up</span>';
                    else
                        home.missingbackups.innerHTML = '<span style="font-size:90%; color:#AAAAAA;">No missing backups</span>';
                }});
            }
    }

};

    images.init = function(){
        if (images._inited === true) return;
        else images._inited = true;

        images.store = stores.images;
        images.domnode = "images-grid";
        images.grid = grid.create(images);

        // connect listeners for filtering
        connect.connect(dijit.byId('images_search_query'), 'onChange', this, this.onSearchQueryChange);
        connect.connect(dijit.byId('images_storagepool_filter_select'), 'onChange', this, this.onStoragePoolFilterChange);
        connect.connect(dijit.byId('images_type_filter_select'), 'onChange', this, this.onTypeFilterChange);

        connect.connect(this.grid, '_onFetchComplete', this, function(rows){
            this.updateSums(rows);
            if (!user.is_readonly) {
                if (dijit.byId("imagesNewButton")) dijit.byId("imagesNewButton").set("style", "display:inline");
                if (dijit.byId("imagesUploadButton")) dijit.byId("imagesUploadButton").set("style", "display:inline");
            }
            images.updateMissingBackups();
        });

        images.grid.startup();

        var q = dojo.query('#imagesFileUploadHelp');
        if(q.irigoTooltip){q.irigoTooltip();}

        dojo.subscribe('upload:file_uploaded', function(){
            images.grid.refresh();
            stores.cdroms.close();
        });

        // refresh stores on image delete
        dojo.subscribe('images:delete', function(task) {
            if (typeof uploader !== 'undefined' && uploader.files) { // Remove file from uploader if we just uploaded it
                var pathname = task.path.substring(task.path.lastIndexOf("/")+1);
                $.each(uploader.files, function(index, value) {
                    if (value && (value.name == pathname || (value.path && value.path == task.path))) {
                        console.log("Removing upload", pathname);
                        uploader.removeFile(value.id);
                    }
                });
            }
            // update stores.
            stores.cdroms.close();
            stores.masterimages.close();
            stores.unusedImages.close();
            stores.unusedImages2.close();
        });

        dojo.subscribe('images:create', function(){
            stores.masterimages.close();
            stores.unusedImages.close();
            stores.unusedImages2.close();
        });

        // handle ui update while in dialog
        dojo.subscribe("images:update", function(task){
            console.log("images update", task);

            if (task.uuid && images.grid.getRowNode(0)) images.grid.refreshRow(task); // due to bug in Dojo we refresh all if no images at all
            else images.grid.refresh();

            var item = images.grid.dialog.item;

            if(!item || (item.uuid !== task.uuid && item.path !== task.uuid)){
                return;
            }

            if (!images.grid.dialog || !images.grid.dialog.isOpen()) {
                return;
            } // No need to update fields if dialog not showing

            if (dojo.byId('snap1') && task.snap1) {
                if (task.snap1 == "--") {
                    item.snap1 = "--";
                    dijit.byId('snap1').set('value', "--");
                } else {
                    var dsnap1 = (new Date(Number(task.snap1)*1000)).toLocaleString();
                    item.snap1 = dsnap1;
                    dijit.byId('snap1').set('value', dsnap1);
                }
            }

            if (dojo.byId('path') && task.newpath) {
                item.path = task.newpath;
                dijit.byId('path').set('value', task.newpath);
            }
            if (dojo.byId('master') && task.master) {
                item.master = task.master;
                dijit.byId('master').set('value', task.master);
            }
            if (dojo.byId('backup') && task.backup) {
                stores.backups.url = "/stabile/images?action=listbackups&image=" +
                        escape(task.backups);
                stores.backups.close();
            }
            images.grid.dialog.show(item, true);

            if (home.currentItem) {
                stores.unusedImages2.close();
                home.updateVitals(home.currentItem);
            }
        });

        connect.connect(this.grid.dialog, 'show', this, function(image){
            // summary: create dialog node link.
            var self = this;
            if(image.status != 'new'){
                if(user.is_admin && image.mac && image.mac != '--'){
                    domConstruct.place('<a id="imageDialogNodeDialogLink" nohref="#images">Node</a>', 'imageDialogNodeDialogLink', 'replace');
                    on(dom.byId('imageDialogNodeDialogLink'), 'click', function(){
                        self.grid.dialog.hide();
                        nodes.grid.dialog.show(stores.nodes.fetchItemByIdentity({identity: image.mac }));
//                        Node.editDialogFromUuid(image.mac);
                    });
                }
            }
            connect.connect(dijit.byId('backup'), 'onChange', this, this.onBackupChange);
        });

        images.onShowItem();
        images.grid.refresh();
    };

    images.onShowItem = function() {
        if (home.imagesOnShowItem != null && images.grid.dialog) {
            images.grid.dialog.show(home.imagesOnShowItem);
            home.imagesOnShowItem = null;
        }
    };

    images.updateFilter = function(){
        var query = this._searchQuery + " AND " + this._storagepoolQuery + " AND " + this._typeQuery;
        console.log("filtering", query);
        this.grid.store.query = query;
        this.grid.filter(query, /*rerender*/true);
    };

    images.onSearchQueryChange = function(v){
        if (v) {
            this._searchQuery = "name:" +v + "*";
//            this._searchQuery = "name: '*" + v + "*'" +
//                " OR status: '" + v + "*'" +
//                " OR type: '" + v + "*'";
        } else {
            this._searchQuery = "name:*";
//            this._searchQuery = "name:*";
        }
        this.updateFilter();
    };

    images.onStoragePoolFilterChange = function(value){
        switch(value){
            case "all":
                this._storagepoolQuery = "storagepool:all";
//                this._storagePoolQuery = "uuid: *";
                break;
            case "shared_storage_pools":
                this._storagepoolQuery = "storagepool:shared";
//                this._storagePoolQuery = "NOT storagepool: -1";
                break;
            case "node_storage_pools":
                this._storagepoolQuery = "storagepool:node";
                break;
            default:
                alert('wtf? ' + value);
        }
        this.updateFilter();
    };

    images.onBackupChange = function(value) {
        if (value && value != '--') $("#restore_button").show();
        else $("#restore_button").hide();
    };

    images.onTypeFilterChange = function(value){
        switch(value){
            case "all":
                this._typeQuery = "type:all";
//                this._typeQuery = "uuid:*";
                break;
            case "user_images":
                this._typeQuery = "type:user";
//                this._typeQuery = "user:"+user.username+" AND (type:qcow2 OR type:vmdk OR type:vdi OR type:vhd OR type:img)";
                break;
            case "user_master_images":
                this._typeQuery = "type:usermasters";
//                this._typeQuery = "user:"+user.username+" AND path:*.master.*";
                break;
            case "user_cd_roms":
                this._typeQuery = "type:usercdroms";
//                this._typeQuery = "user:"+user.username+" AND type:iso";
                break;
            case "common_master_images":
                this._typeQuery = "type:commonmasters";
//                this._typeQuery = "user:common AND (type:qcow2 OR type:vmdk OR type:vdi OR type:vhd OR type:img)";
                break;
            case "common_cd_roms":
                this._typeQuery = "type:commoncdroms";
//                this._typeQuery = "user:common AND type:iso";
                break;
            default:
                alert('wtf? ' + value);
        }
        this.updateFilter();
    };

    images.updateSums = function(rows) {
        var totalvirtualsize = 0;
        var totalrealsize = 0;
        var totalbackupsize = 0;

        if (!rows) {
            for(var i = 0; i < images.grid.rowCount; i++){
                sumit(images.grid.getItem(i));
            }
        } else {
            for(var i in rows){
                sumit(rows[i]);
            }
        }

        function sumit(item) {
            if (item) {
                if (item.virtualsize && item.virtualsize!="--") totalvirtualsize += parseInt(item.virtualsize);
                if (item.realsize && item.realsize!="--") totalrealsize += parseInt(item.realsize);
                if (item.backupsize && item.backupsize!="--") totalbackupsize += parseInt(item.backupsize);
            }
        }

        var stq = (user.storagequota==0)?'&infin;':Math.round(user.storagequota/1024);
        var nstq = (user.storagequota==0)?'&infin;':Math.round(user.nodestoragequota/1024);
        document.getElementById("storage_sum").innerHTML =
                '<span title="Quotas: ' + stq + ' GB standard, ' + nstq + ' GB on node">Usage: ' + (Math.round(10*totalvirtualsize /1024/1024/1024)/10) + " GB" +
                        "&nbsp;&nbsp;Size: " + (Math.round(10*totalrealsize /1024/1024/1024)/10) + " GB" +
                        "&nbsp;&nbsp;Backup: " + (Math.round(10*totalbackupsize /1024/1024/1024)/10) + " GB" +
                "</span>";
    };
    window.images = images;
    return images;
});

