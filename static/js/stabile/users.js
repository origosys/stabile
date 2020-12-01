define([
    "dojo/_base/array",
    "dojo/_base/connect",
    "stabile/grid",
    "steam2/user",
    "steam2/models/Server",
    "dojox/validate",
    "dijit/form/ValidationTextBox",
    "dojox/validate/web",
    "dojox/grid/cells/_base"
],function(arrayUtil, connect, grid, user, Server, validate){

    var users = {

        grid: {},

        _searchQuery: "username:*",
        _statusQuery: "status:all",
        _inited: false,
        storeQuery: "username:*",
        model : function(args){
            return dojo.mixin({
                username: "",
                password: "",
                fullname: "",
                email: "",
                phone: "",
                alertemail: "",
                alertphone: "",
                opemail: "",
                opphone: "",
                privileges: "",
                accounts: "",
                accountsprivileges: "",
                allowfrom: "",
                storagequota: 0,
                nodestoragequota: 0,
                memoryquota: 0,
                vcpuquota: 0,
                externalipquota: 0,
                status: "new"
            }, args || {});
        },

        /** object name - for reflective lookup */
        name : "users",

        sortInfo: 0,

        structure : [
            { field : 'username', name : "Username", width : "170px", hidden: true },
            { field : 'fullname', name : 'Full name', width : "auto" },
            { field : 'email', name : 'Email', width : "auto" },
            { field : 'privileges', name : 'Privileges <a href="//www.origo.io/info/stabiledocs/web/users/privileges" rel="help" target="_blank" class="irigo-tooltip">help</a>', width : "100px" },
            { field : 'action', name : 'Action', width : 'auto', hidden: user.is_readonly,
                formatter : function(val, rowIdx, cell) {
                    var item = this.grid.getItem(rowIdx);
                    return users.getActionButtons(item);
                }
            }
        ],

        dialogStructure : [
            { field : "username", name : "Username",    type : "dijit.form.ValidationTextBox", attrs: {required:"true"}},
            { field : "password", name : "Password",    type : "dijit.form.TextBox", attrs: {type:"password"}},
            { field : "fullname", name : "Full name", type: "dijit.form.ValidationTextBox", attrs: {regExp: ".+", required:true}},
            { field : "email", name : "Email", type: "dijit.form.ValidationTextBox", attrs: {regExp: ".+", required:true}},
            { field : "alertemail", name : "Alert email", type: "dijit.form.TextBox", help: "users/alert-email"},
            { field : "phone", name : "Phone", type: "dijit.form.TextBox"},
            { field : "privileges", name : "Privileges", type: "dijit.form.TextBox", help: "users/privileges"},
            { field : "accounts", name : "Other accounts", type: "dijit.form.TextBox", help: "users/accounts"},
            { field : "accountsprivileges", name : "Privileges to other accounts", type: "dijit.form.TextBox", help: "users/accounts"},
            { field : "allowfrom", name : "Allow login from", type: "dijit.form.TextBox", help: "dashboard/info-tab/allowloginfrom"},

            { field : "storagequota", name : "Storage quota", type: "dijit.form.TextBox", help: "users/quotas", style: "width: 80px;",
                extra: function(item) {return "GB (default: " + home.formatters.readableMBytes(IRIGO.user.defaultstoragequota) + " <span id='storage_usage'></span>)";}
            },
            { field : "nodestoragequota", name : "Node storage quota", type: "dijit.form.TextBox", help: "users/quotas", style: "width: 80px;",
                extra: function(item) {return "GB (default: " + home.formatters.readableMBytes(IRIGO.user.defaultnodestoragequota) + " <span id='nodestorage_usage'></span>)";}
            },
            { field : "memoryquota", name : "Memory quota", type: "dijit.form.TextBox", help: "users/quotas", style: "width: 80px;",
                extra: function(item) {return "GB (default: " + home.formatters.readableMBytes(IRIGO.user.defaultmemoryquota) + " <span id='memory_usage'></span>)";}
            },
            { field : "vcpuquota", name : "vCPU quota", type: "dijit.form.TextBox", help: "users/quotas", style: "width: 80px;",
                extra: function(item) {return " (default: " + IRIGO.user.defaultvcpuquota + " <span id='vcpu_usage'></span>)";}
            },
            { field : "externalipquota", name : "External IP quota", type: "dijit.form.TextBox", help: "users/quotas", style: "width: 80px;",
                extra: function(item) {return " (default: " + IRIGO.user.defaultexternalipquota + " <span id='externalip_usage'></span>)";}
            },
            {
                formatter: function(item) {
                    return '<td>Created</td><td>' + home.timestampToLocaleString(item.created) + '</td>';
                }
            },
            {
                formatter: function(item) {
                    if (item.status == "new") {
                        return "--";
                    } else {
                        return '<td>Modified</td><td>' + home.timestampToLocaleString(item.modified) + '</td>';
                    }
                }
            }
        ],

        store : null,

        getActionButtons : function(item, include_save){
            var busy = ' <img height="18px" alt="busy" src="/stabile/static/img/loader.gif"> ';
            if (user.is_readonly) return "";
            if (item.status == 'deleting') return busy;

            var username = item.username;
            var type = this.name;
            var privileges = item.privileges;

            function actionButton(args){
                args.name = username;
                args.type = type;
                return grid.actionButton(args);
            }

            var enable = actionButton({'action' :"enable", 'id' :username});
            var disable = actionButton({'action' :"disable", 'id' :username});
            var resetpassword = actionButton({'action' :"resetpassword", 'id' :username});
            var _delete = actionButton({'action' :"deleteentirely", 'id' :username, 'confirm' :true});
            var save = (include_save) ? grid.saveButton(type) : "";
            var actions = '';
            if (privileges.indexOf('d')!=-1) actions += enable;
            else if (item.username!=user.username) actions += disable;
            if (privileges.indexOf('d')!=-1) actions += _delete;
            else actions += resetpassword;
            actions += save;
            return actions;
        },
        rowStyler : function(row, item){
            if(item.privileges.indexOf("a") != -1){
                row.customStyles += "font-weight:bold;";
            } else {
                row.customStyles = "cursor:pointer;";
            }
        },
        onBeforeDialog : function(item) {
            $.get("/stabile/users?action=usagestatus&username="+item.username, function(data) {
                $("#storage_usage").text(", usage: " + data.shared_storage.quantity  + " GB");
                $("#nodestorage_usage").text(", usage: " + data.node_storage.quantity  + " GB");
                $("#memory_usage").text(", usage: " + data.memory.quantity  + " GB");
                $("#vcpu_usage").text(", usage: " + data.vcpus.quantity);
                $("#externalip_usage").text(", usage: " + data.external_ips.quantity);
            })
        },
    };

    users.init = function(){
        if (users._inited === true) return "OK";
        else users._inited = true;
        console.log("initializing users", user);

        connect.connect(dijit.byId('users_status_filter_select'), 'onChange', this, this.onStatusFilterChange);
        connect.connect(dijit.byId('users_search_query'), 'onChange', this, this.onSearchQueryChange);

        users.store = stores.users;
        users.domnode = "users-grid";
        users.grid = grid.create(users);
        users.grid.startup();

        dojo.subscribe("users:update", function(task){
            if (task.username) {
                users.grid.refreshRow(task, "username");
            } else {
                users.grid.refresh();
            }
        });

        connect.connect(this.grid, '_onFetchComplete', this, function(rows){
            if (!user.is_readonly) $("#usersNewButton").show();
            if (IRIGO.user.enginelinked) $("#syncusers").show();
        });

        connect.connect(this.grid, 'onDialog', function(item) {
            if (item.status=="new") {
                dijit.byId("username").set("readonly", false).focus();
            } else {
                dijit.byId("username").set("readonly", true);
            }
        });

        this.onShowItem();
    };

    users.onShowItem = function() {
        if (home.usersOnShowItem != null && users.grid.dialog) {
            users.grid.dialog.show(home.usersOnShowItem);
            home.usersOnShowItem = null;
        }
    };


    users.updateFilter = function(){
        var query = this._searchQuery + " AND " + this._statusQuery;
        this.grid.store.query = query;
        this.grid.filter(query, /*rerender*/true);
    };

    users.onSearchQueryChange = function(v){
        if(v){
            this._searchQuery = "username:" +v + "*";
        }
        else{
            this._searchQuery = "username:*";
        }
        this.updateFilter();
    };

    users.onStatusFilterChange = function(value){
        switch(value){
            case "all":
                this._statusQuery = "status:all";
                break;
            default:
                this._statusQuery = "status:" + value;
        }
        this.updateFilter();
    };

    users.syncUsers = function() {
        $("#syncusers").html('Syncing users&hellip; <i class="fa fa-cog fa-spin"></i>').prop("disabled", true);
        return $.get("/stabile/users?action=syncusers", function(res){$("#syncusers").html('Sync users').prop("disabled", false); server.parseResponse(res);});
    }

    window.users = users;
    return users;
});
