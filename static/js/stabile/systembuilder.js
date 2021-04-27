define([
    'dojo/io/script',
    'dojo/cookie',
    "steam2/user",
    "steam2/models/Server",
//    "stabile/menu",
    "stabile/upload",
    "stabile/images",
    "stabile/servers",
    "stabile/networks",
    "steam2/stores",
    "dijit/form/ComboBox",
    "dijit/form/Form",
    "dijit/form/Select",
    "dijit/layout/StackContainer",
    "dijit/layout/StackController",
    "dijit/layout/ContentPane"
], function(ioScript, cookie, user, Server, /*menu,*/ upload, images, servers, networks, newStores){
    var systembuilder = {};
    var hostname = location.hostname;
    var subdom = hostname;
    if (hostname.substring( hostname.indexOf(".")+1 ).indexOf(".")>0) // check if hostname has more than one "."
        subdom = hostname.substring( hostname.indexOf(".")+1 );
    subdom = "." + subdom;
    var dialog;

    systembuilder.system = {
        managementlink: null,
        upgradelink: null,
        done: false,
        reshowing: false,
        cancelled: false,
        cur_sys_tpl: null,
        showInputs: false,
        homeExcerpt: null,
        create: function(){
            if(dijit.byId('createSystemDialog') !== undefined){
                // destroy the existing and its children
                //dijit.byId('createSystemDialog').destroyRecursive();
                dialog = dijit.byId('createSystemDialog');
                dialog.set("title", "Install Stack <a href=\"https://www.origo.io/info/stabiledocs/web/dashboard/new-stack/settings/\" rel=\"help\" target=\"_blank\" class=\"irigo-tooltip\">help</a>");
                systembuilder.system.done = false;
                systembuilder.system.reshowing = true;
            } else {
                dialog = new dijit.Dialog({
                    title: "Install Stack <a href=\"https://www.origo.io/info/stabiledocs/web/dashboard/new-stack/settings/\" rel=\"help\" target=\"_blank\" class=\"irigo-tooltip\">help</a>",
                    id: 'createSystemDialog',
                    style: "width: 90%; left:5%; overflow: auto;"
                });
                dialog.connect(dialog, "hide", function(e){
                    if (dojo.byId("manageSystemIframe")) dojo.byId("manageSystemIframe").src = '';
                });
            }

// Clear the cookies
            dojo.cookie("installsystem", '', {path: '/', expires: 'Sat, 01-Jan-2000 00:00:00 GMT'});
            dojo.cookie("installsystem", '', {path: '/', expires: 'Sat, 01-Jan-2000 00:00:00 GMT'});
            dojo.cookie("installsystem", '', {path: '/', domain: subdom, expires: 'Sat, 01-Jan-2000 00:00:00 GMT'});
            dojo.cookie("installsystem", '', {path: '/', domain: location.hostname, expires: 'Sat, 01-Jan-2000 00:00:00 GMT'});
            dojo.cookie("installaccount", '', {path: '/', domain: subdom, expires: 'Sat, 01-Jan-2000 00:00:00 GMT'});
            dojo.cookie("installaccount", '', {path: '/', domain: location.hostname, expires: 'Sat, 01-Jan-2000 00:00:00 GMT'});

            function step_one(){
                var one = [
                    '<form onsubmit="systembuilder.system.build();return false;" class="wizardForm" id="wizardForm" dojoType="dijit.form.Form">',
                    '<table border="0" style="margin:0 8px 20px 8px;">',
                    '<tr id="tr_master"><td class="wizardLabel">',
                        '<label>Select&nbsp;Stack to&nbsp;install:</label>',
                        '</td><td class="wizardLabel">',
                        '<select id="wizard_master" />',
                        '</td></tr>',
                    '</table>',
                    '<div dojoType="dijit.layout.StackContainer" style="overflow:auto; padding:0 10px 10px 10px;" id="wizardContainer">',

                    '<div dojoType="dijit.layout.ContentPane" id="wizardSubForm0">',
                    '<div><h3>',
                    '<img src="/stabile/static/img/loader.gif" style="vertical-align:middle; margin-right:20px;" alt="loading..." />',
                    '</h3></div>',
                    '</div>',

                    '<div dojoType="dijit.layout.ContentPane" id="wizardSubForm1">',
                    '<div nostyle="margin-left:auto; font-family:sans-serif; margin-right:auto; text-align:center; padding-top:15%; border: 0px solid;"><h3>',
                    '<img src="/stabile/static/img/loader.gif" style="vertical-align:middle; margin-right:20px;" alt="loading..." />',
                    'Loading stack settings...',
                    '</h3></div>',
                    '</div>',
                    '<div dojoType="dijit.layout.ContentPane" nostyle="left:0;" id="wizardSubForm2">',
                    '<p id="wizardTitle"></p>',
                    '<p class="well well-sm" id="wizardHelp" style="max-height:50vh; overflow:auto; width: 100%;">',
                    '<table border="0">',
                    '<tr id="tr_name" style="display:inherit;"><td class="wizardLabel">',
                        '<label>Name:</label>',
                        '</td><td class="wizardLabel">',
                        '<input id="wizard_name" />',
                        '</td></tr>',
                    '<tr id="tr_account"><td class="wizardLabel">',
                        '<label>Install to account:</label>',
                        '</td><td class="wizardLabel">',
                        '<select id="wizard_account" name="wizard_account">',
                        '</select>',
                        '</td></tr>',
                    '<tr id="tr_diskbus" class="wizardRow"><td class="wizardLabel">',
                        '<label>Disk bus:</label>',
                        '</td><td class="wizardLabel">',
                        '<select id="wizard_diskbus" name="wizard_diskbus">',
                        '<option value="virtio">Paravirtualized Network</option>',
                        '</select>',
                        '</td></tr>',
                    '<tr id="tr_memory" class="wizardRow"><td class="wizardLabel">',
                        '<label>Memory:</label>',
                        '</td><td class="wizardLabel">',
                        '<select id="wizard_memory" name="wizard_memory">',
                        '<option>256</option>',
                        '<option>512</option>',
                        '<option selected >1024</option>',
                        '<option>2048</option>',
                        '<option>4096</option>',
                        '<option>8192</option>',
                        '<option>16384</option>',
                        '</select>MB',
                        '</td></tr>',
                    '<tr id="tr_vcpu" class="wizardRow"><td class="wizardLabel">',
                        '<label>VCPUs: </label>',
                        '</td><td class="wizardLabel">',
                        '<input id="wizard_vcpu" name="wizard_vcpu" style="width:16px" />',
                        '</td></tr>',
                    '<tr id="tr_networktype1" class="wizardRow"><td class="wizardLabel">',
                        '<label>Connection:</label>',
                        '</td><td class="wizardLabel">',
                        '<select id="wizard_networktype1" name="wizard_networktype1">',
                        '<option value="ipmapping">IP mapping</option>',
                        '<option value="internalip">Internal ip address</option>',
                        '<option value="externalip">External ip address</option>',
                        '</select>',
                        '</td></tr>',
                    '<tr id="tr_ports" class="wizardRow"><td class="wizardLabel">',
                        '<label>Ports:</label>',
                        '</td><td class="wizardLabel">',
                        '<input id="wizard_ports" /> <span class="small">E.g. "80, 443". Leave empty to allow traffic to all tcp/udp ports</span>',
                        '</td></tr>',
                    '<tr id="tr_nicmodel1" class="wizardRow"><td class="wizardLabel">',
                        '<label>NIC model:</label>',
                        '</td><td class="wizardLabel">',
                        '<select id="wizard_nicmodel1" name="wizard_nicmodel1">',
                        '<option value="virtio">Paravirtualized Network</option>',
                        '</select>',
                        '</td></tr>',
                    '<tr id="tr_storagepool" class="wizardRow"><td class="wizardLabel">',
                        '<label>Storage:</label>',
                        '</td><td class="wizardLabel">',
                        '<select id="wizard_storagepool" name="wizard_storagepool">',
                        '<option value="-1">On node</option>',
                        '<option value="0">Shared</option>',
                        '</select>',
                        '</td></tr>',
                    '<tr id="tr_storagepool2" class="wizardRow"><td class="wizardLabel">',
                        '<label>Data storage:</label>',
                        '</td><td class="wizardLabel">',
                        '<select id="wizard_storagepool2" name="wizard_storagepool2">',
                        '<option value="0">Shared</option>',
                        '<option value="-1">On node</option>',
                        '</select>',
                        '</td></tr>',
                    '<tr id="tr_image2" class="wizardRow"><td class="wizardLabel">',
                        '<label>Data image master:</label>',
                        '</td><td class="wizardLabel">',
                        '<input id="wizard_image2" /> <span class="small">secondary image for data storage</span>',
                        '</td></tr>',
                    '<tr id="tr_cdrom" class="wizardRow"><td class="wizardLabel">',
                        '<label>CD-rom:</label>',
                        '</td><td class="wizardLabel">',
                        '<select id="wizard_cdrom" name="wizard_cdrom">',
                        '<option value="--">--</option>',
                        '</select>',
                        '</td></tr>',
                    '<tr id="tr_boot" class="wizardRow"><td class="wizardLabel">',
                        '<label>Boot device:</label>',
                        '</td><td class="wizardLabel">',
                        '<select id="wizard_boot" name="wizard_boot">',
                        '<option value="--">hd</option>',
                        '</select>',
                        '</td></tr>',
                    '<tr id="tr_bschedule" class="wizardRow"><td class="wizardLabel">',
                        '<label>Backup:</label>',
                        '</td><td class="wizardLabel">',
                        '<select id="wizard_bschedule" name="wizard_bschedule">',
                        '<option selected value="">None</option>',
                        '<option value="daily7">Daily, 7 days</option>',
                        '<option value="daily14">Daily, 14 days</option>',
                        '</select>',
                        '</td></tr>',
                    '<tr id="tr_monitors" class="wizardRow"><td class="wizardLabel">',
                        '<label>Monitors:</label>',
                        '</td><td class="wizardLabel">',
                        '<select id="wizard_monitors" name="wizard_monitors">',
                        '<option selected value="">None</option>',
                        '<option value="ping,diskspace">Ping and diskspace</option>',
                        '<option value="ping">Ping</option>',
                        '<option value="diskspace">Diskspace</option>',
                        '</select>',
                        '</td></tr>',
                    '<tr id="tr_instances" class="wizardRow"><td class="wizardLabel">',
                        '<label>Server instances:</label>',
                        '</td><td class="wizardLabel">',
                        '<input id="wizard_instances" name="wizard_instances" />',
                        '</td></tr>',
                    '<tr id="tr_start" class="wizardRow"><td class="wizardLabel">',
                        '<label>Start server(s):</label>',
                        '</td><td class="wizardLabel">',
                        '<span id="wizard_start" name="wizard_start" />',
                        '</td></tr>',
                    '<tr id="tr_managementlink" style="display:none"><td class="wizardLabel">',
                        '<label>Management link:</label>',
                        '</td><td class="wizardLabel">',
                        '<input id="wizard_managementlink" />',
                        '</td></tr>',
                    '<tr id="tr_appid" style="display:none"><td class="wizardLabel">',
                        '<label>App ID:</label>',
                        '</td><td class="wizardLabel">',
                        '<input id="wizard_appid" />',
                        '</td></tr>',
                    '</table>',
                    '</div>',
                    '</div>',
                    '<!-- p class="wizardInfoPane" id="finish_notes" style="display:none;" -->',
                    '<!-- /p -->',
                    '<div style="padding: 10px 13px 40px 10px; border-top: 1px solid #e5e5e5;">',
                    '<span class="pull-left">Hide preconfigured settings: ',
                    '<input id="wizard_recomended_settings" name="wizard_recomended_settings" />',
                    '</span>',
                    '<button id="buildsystembutton" class="btn btn-sm btn-primary pull-right" type="submit">',
                    'Install',
                    '</button>',
                    '</div>',
                    '</form>'].join('');
                return one;
            }

            function set_default_name(servername) {
                dijit.byId("wizard_name").setValue(servername);
                dijit.byId("wizard_name").focus();
            }

            function init_step_one(){
                var wizard_name = new dijit.form.ValidationTextBox(
                {
                    name: 'wizard_name',
                    type: 'text',
                    required: true,
                    style: "width:250px",
                    tabindex: 1
                }, 'wizard_name');
                var wizard_account = new dijit.form.Select(
                {
                    name: 'wizard_account',
                    type: 'text',
                    required: false,
                    store: stores.accounts,
                    value: user.username,
                    query: {privileges: /n|a|u|^$/},
                    onChange: systembuilder.system.updateWizardAccounts,
                    style: "width:250px"
                }, 'wizard_account');
                var wizard_master = new dijit.form.Select(
                {
                    name: 'wizard_master',
                    type: 'text',
                    required: false,
                    store: stores.masterimages,
                    query: {installable: 'true', status: '*used'},
                    searchAttr: 'name',
                    onChange: systembuilder.system.on_change_master,
                    style: "width:250px"
                }, 'wizard_master');
                dijit.form.ComboBox({style: "width:64px"}, 'wizard_memory');
                dijit.form.NumberSpinner(
                {
                    value: 1,
                    smallDelta: 1,
                    constraints: {
                        min: 1,
                        max: 4,
                        places: 0
                    },
                    style: "width: 32px;"
                }, 'wizard_vcpu');

                dijit.form.NumberSpinner(
                {
                    value: 1,
                    smallDelta: 1,
                    constraints: {
                        min: 1,
                        max: 100,
                        places: 0
                    },
                    style: "width: 40px;"
                }, 'wizard_instances');
                dijit.form.Select({}, 'wizard_storagepool');
                dijit.form.Select({}, 'wizard_storagepool2');
                dijit.form.Select({store: stores.diskbus, value: 'virtio'}, 'wizard_diskbus');
                dijit.form.Select({store: stores.networkInterfaces, value: 'virtio'}, 'wizard_nicmodel1');
                dijit.form.Select({store: stores.cdroms, value: '--'}, 'wizard_cdrom');
                dijit.form.Select({store: stores.bootDevices, value: 'hd'}, 'wizard_boot');
                dijit.form.Select({}, 'wizard_networktype1');
                dijit.form.TextBox({disabled: false}, 'wizard_ports');
                dijit.form.Select({}, 'wizard_bschedule');
                dijit.form.Select({}, 'wizard_monitors');
                dijit.form.TextBox({disabled: false, style: {width:"400px"}}, 'wizard_image2');
                dijit.form.CheckBox({checked: false}, 'wizard_start');
                dijit.form.TextBox({disabled: true}, 'wizard_managementlink');
                dijit.form.TextBox({style: "width:30px"}, 'wizard_appid');
                dijit.form.CheckBox({checked: !systembuilder.system.showInputs, onChange: systembuilder.system.showRecomendedInputs}, 'wizard_recomended_settings');
                $("#buildsystembutton").prop("disabled", true);
            }

            dialog.set('content',step_one());
            init_step_one();
            q = dojo.query('.irigo-tooltip'); q.irigoTooltip && q.irigoTooltip();
            stores.masterimages.close();
            if (systembuilder.system.reshowing) {
                dijit.byId('wizard_master').setStore(stores.masterimages, '--', {query: {installable: 'true', status: '*used'}});
                dijit.byId("wizard_account").setStore(stores.accounts, user.username);
                dijit.byId("wizard_diskbus").setStore(stores.diskbus, 'virtio');
                dijit.byId("wizard_nicmodel1").setStore(stores.networkInterfaces, 'virtio');
                dijit.byId("wizard_cdrom").setStore(stores.cdroms, '--');
                dijit.byId("wizard_boot").setStore(stores.bootDevices, 'hd');
            }

            if (user.privileges.indexOf("n")==-1 && !user.is_admin) dijit.byId("wizard_storagepool").set('disabled', true);
            if (user.privileges.indexOf("n")==-1 && !user.is_admin) dijit.byId("wizard_storagepool2").set('disabled', true);

            dialog.show();

            function testName(i) {
                testname = 'New Stack ' + Math.uuid().toLowerCase().substr(0,4);
                testpath = "/mnt/stabile/images/" + user.username  + "/" + testname + " image.qcow2";
                var mast = dijit.byId('wizard_master').value;
                if (mast != '') {
                    testpath = mast.replace(/(\/.+\/)(\w+)(\/.+)/,"$1" + user.username + "/" + testname + " image.qcow2");
                }
                stores.images.fetch({query: {path: testpath, installable: "true", status: "*used"}, onComplete: function(items2) {
                    if (items2 && items2.length>0) {
                        i = i + 1;
                        testName(i);
                    }
                    else (set_default_name(testname));
                }});
            }
        },

        updateWizardAccounts: function() {
            document.getElementById("tr_account").style.display = "none";
            if (dijit.byId("wizard_account").options.length<=1) {
                document.getElementById("tr_account").style.display = "none";
            }
            else if (home.install_account) {
                home.install_account = '';
                dijit.byId("wizard_account").set('disabled', true);
            } else {
                dijit.byId("wizard_account").set('disabled', false);
            }
        },

        on_change_master: function(path) {
            console.log("master changed", path, home.install_sytem);
            if (home.install_system) { // Don't fire onchange if we are loading a system from the app store
                console.log("installing app from app store", home.install_system);
                stores.masterimages.fetch( {query: {appid: home.install_system, installable: "true"}, onComplete:
                    function(items) {
                        if (items.length && items.length>0) {
                            dijit.byId("wizard_master").setValue(items[0].path[0]);
                            home.install_system = '';
                            location.hash = 'home';
                        } else {
                            IRIGO.toast("The master image was not found! Please make sure your engine is configured to downlod master images from Stabile Registry.");
                            home.install_system = '';
                            location.hash = 'home';
                            systembuilder.system.on_change_master('--');
                        }
                    }
                })
            } else if (path == '--') {
                $("#buildsystembutton").prop("disabled", true);
                if (systembuilder.system.homeExcerpt) {
                    document.getElementById("wizardSubForm0").innerHTML = systembuilder.system.homeExcerpt;
                    dijit.byId("wizardContainer").selectChild(dijit.byId("wizardSubForm0"), true);
                } else {
                    document.getElementById("wizardSubForm0").innerHTML =
                            '<div style="margin-left:auto; font-family:sans-serif; margin-right:auto; text-align:center; padding-top:15%; border: 0px solid;"><h3><img src="/stabile/static/img/loader.gif" style="vertical-align:middle; margin-right:20px;" alt="loading..." /></h3></div></div>';

                    dijit.byId("wizardContainer").selectChild(dijit.byId("wizardSubForm0"), true);

                    var topic_url = "https://www.origo.io/appstore.cgi?action=engineappstore";
                    var topicargs = {
                        url: topic_url,
                        callbackParamName: 'callback'
                    };
                    var dfd = ioScript.get(topicargs);

                    dfd.then(function(js){
                        if (js && js.app) {
                            systembuilder.system.homeExcerpt = js.app.summary;
                            document.getElementById("wizardSubForm0").innerHTML = systembuilder.system.homeExcerpt;
                        }
                    });
                }

            } else {
                dijit.byId("wizardContainer").selectChild(dijit.byId("wizardSubForm1"), true);
                $("#buildsystembutton").prop("disabled", true);
                stores.masterimages.fetch({
                    query: {path: path, installable: "true", status: "*used"},
                    onComplete: systembuilder.system.load_changed_master,
                    onError: systembuilder.system.master_not_found
                });
            }
        },
        load_changed_master: function(item) {
            console.log("master changed", item);
            if (item[0]) {
                var appid = item[0].appid[0];
                if (appid && appid!='--') { // && IRIGO.user.enginelinked) {
                    console.log("loading app", appid);
                    systembuilder.currentManagementlink = item[0].managementlink;
                    systembuilder.system.prepareSystem(appid);
                } else {
                    console.log("loading unknown app", item[0].managementlink[0]);
                    if (item[0].managementlink[0] && item[0].managementlink[0]!='') {
                        var usys = [];
                        usys.managementlink = item[0].managementlink[0];
                        usys.upgradelink = item[0].upgradelink[0];
                        if (item[0].terminallink) usys.terminallink = item[0].terminallink[0];
                        if (item[0].image2) usys.image2 = item[0].image2[0];
                        systembuilder.currentManagementlink = item[0].managementlink[0];
                        systembuilder.system.loadSystem(usys);
                    } else {
                        systembuilder.currentManagementlink = '';
                        systembuilder.system.loadSystem();
                    }
                }
            } else {
                systembuilder.currentManagementlink = '';
                console.log("no master selected");
            }
        },
        lookup_master: function(str) {
        //    stores.masterimages.close();
            stores.masterimages.fetch({
                query: {path: str, installable: "true", status: "*used"},
                onComplete: systembuilder.system.set_master,
                onError: systembuilder.system.master_not_found
            });
        },
        set_master: function(item) {
            if (!item.length || item.length==0)
                systembuilder.system.master_not_found();
            else
                dijit.byId("wizard_master").setValue(item[0].path[0]);
        },
        master_not_found: function() {
            console.log("Master not found");
            home.install_system = '';
            $("#buildsystembutton").hide();
            document.getElementById("wizardHelp").innerHTML =
                    'The master image was not found <a id="wizardHelpDefault" rel="help" target="_blank" class="irigo-tooltip" href="https://www.origo.io/info/stabiledocs/web/dashboard/new-stack/">help</a>';
            q = dojo.query('.irigo-tooltip'); q.irigoTooltip && q.irigoTooltip();

            var prop;
            var wform = dijit.byId('wizardForm');
            dojo.forEach(wform.getChildren(), function(input) {
                prop = input.id.substring(7);
                var element = document.getElementById("tr_"+prop);
                if (element) element.style.display="none";
            });

        },

        lookup_cdrom: function(str) {
            stores.cdroms.fetch({
                query: {path: str},
                onComplete: systembuilder.system.set_cdrom,
                onError: systembuilder.system.cdrom_not_found
            });
        },
        set_cdrom: function(item) {
            if (!item.length || item.length==0)
                systembuilder.system.cdrom_not_found();
            else
                dijit.byId("wizard_cdrom").setValue(item[0].path[0]);
        },
        cdrom_not_found: function() {
            console.log("CDrom not found");
        },

        prepareSystem: function(args){
            if (args) {
                var topic_url = "/stabile/systems?action=appstore&appid=" + args;
                var topicargs = {
                    url: topic_url,
                    callbackParamName: 'callback'
                };
                var dfd = ioScript.get(topicargs);

                dfd.then(function(js){
                    if (js && js.app) {
                        var sys = js.app;
                        systembuilder.system.loadSystem(sys);
                    } else {
                        systembuilder.system.loadSystem();
                    }
                });
            } else {
                systembuilder.system.loadSystem();
            }
        },

        showRecomendedInputs: function(hide) {
            var prop;
            systembuilder.system.showInputs = !hide;
            if (hide) {
                console.log("hiding inputs", hide, cur_sys_tpl);
                dojo.query(".wizardRow").forEach(function(node){
                    prop = node.id.substring(3);
                    if ((cur_sys_tpl && cur_sys_tpl[prop] && cur_sys_tpl[prop]!='')) {
                        //node.style = "display:none;";
                        node.style.display = "";
                        console.log(node.style.display, prop, cur_sys_tpl[prop]);
                    }
                })
            } else {
                console.log("showing inputs", hide);
                dojo.query(".wizardRow").forEach(function(node){
                    node.style.display="inherit";
                })
            }
        },

        loadSystem: function(sys_tpl) {
            console.log("Loading system", sys_tpl);
            //for (prop in sys_tpl) {
            //    console.log(prop, sys_tpl[prop]);
            //}
            var prop;
            var wform = dijit.byId('wizardSubForm2');
            if (sys_tpl) cur_sys_tpl = sys_tpl;
            else cur_sys_tpl = null;
            dojo.forEach(wform.getDescendants(), function(input) {
                prop = input.id.substring(7);
                if (sys_tpl && sys_tpl[prop]) {
                    if (prop=="start" && sys_tpl[prop] == "false") {// Tick or untick start checkbox
                        input.setValue(false);
                    } else if (prop=="master") {
                        if (input.value.indexOf(sys_tpl[prop])==-1) {// Incomplete path - look up complete path
                            console.log("got incomplete path, looking up", sys_tpl[prop]);
                            systembuilder.system.lookup_master("*/" + sys_tpl[prop]);
                        }
                    } else if (prop=="image2") {
                        if (sys_tpl[prop] == '--') input.setValue('')
                        else input.setValue(sys_tpl[prop]);
                    } else if (prop=="cdrom") {
                        if (input.value.indexOf(sys_tpl[prop]) == -1 && sys_tpl[prop] != '--') {// Incomplete path - look up complete path
                            console.log("got cdrom incomplete path, looking up", sys_tpl[prop]);
                            systembuilder.system.lookup_cdrom("*/" + sys_tpl[prop]);
                        }

                    } else if (prop=="name") {
                        if (home.install_name) {
                            input.setValue(decodeURIComponent(home.install_name));
                            home.install_name = '';
                        } else {
                            input.setValue(sys_tpl[prop]);
                        }
                    } else if (sys_tpl[prop]) {
                        input.setValue(sys_tpl[prop]);
                    }
                    if (prop!="name" && prop!="master" && prop!="appid" && prop!="managementlink" && prop!="upgradelink" && prop!="version") {
                        if (sys_tpl[prop] && !systembuilder.system.showInputs) {
                            document.getElementById("tr_"+prop).style.display="none";
                        } else {
                            document.getElementById("tr_"+prop).style.display="inherit";
                        }
                    }
                } else {
                    if (prop=="name") {
                        //var testname = 'New App ' + Math.uuid().toLowerCase().substr(0,4);
                        var testname = dijit.byId("wizard_master").attr("displayedValue");
                        if (home.install_name) {
                            testname = home.install_name;
                            home.install_name = '';
                        }
                        input.set("value", testname);
                    } else if (prop!="master" && prop!="appid" && prop!="managementlink" && prop!="upgradelink" && prop!="version") {
                        if (document.getElementById("tr_"+prop)) document.getElementById("tr_"+prop).style.display="inherit";
                    }
                }
            });
            if (sys_tpl && sys_tpl.name) {
                document.getElementById("wizardTitle").innerHTML = "<span title=\"Version: " + sys_tpl.version + "\">" + sys_tpl.name + "</span>";
            } else {
                document.getElementById("wizardTitle").innerHTML = "";
            }
            if (sys_tpl && sys_tpl.appid) {
                document.getElementById("wizardTitle").innerHTML += " <a class=\"dimlink\" target=\"_blank\" href=\"https://www.stabile.io/registry#app-" + sys_tpl.appid + "\">(view in Stabile Registry)</a>";
            }
            if (sys_tpl && sys_tpl.managementlink && sys_tpl.managementlink!='' && sys_tpl.upgradelink && sys_tpl.upgradelink!='') {
                dijit.byId('wizard_managementlink').set("value", sys_tpl.managementlink);
                document.getElementById("wizardTitle").innerHTML += " <span class=\"alert alert-info small teaser\" title=\"This stack may be managed by clicking the 'manage' button after installing\" style=\"float:right; font-size:13px; padding:8px\">This stack is manageable and upgradable</span>";
            } else if (sys_tpl && sys_tpl.managementlink && sys_tpl.managementlink!='') {
                dijit.byId('wizard_managementlink').set("value", sys_tpl.managementlink);
                document.getElementById("wizardTitle").innerHTML += " <span class=\"alert alert-info small teaser\" title=\"This stack may be managed by clicking the 'manage' button after installing\" style=\"float:right; font-size:13px; padding:8px\">This stack is manageable</span>";
            } else if (systembuilder.currentManagementlink) {
                dijit.byId('wizard_managementlink').set("value", systembuilder.currentManagementlink);
                document.getElementById("wizardTitle").innerHTML += " <span class=\"alert alert-info small teaser\" title=\"This stack may be managed by clicking the 'manage' button after installing\" style=\"float:right; font-size:13px; padding:8px\">This stack is manageable</span>";
            }
            document.getElementById("wizardTitle").innerHTML = "<h3>" + document.getElementById("wizardTitle").innerHTML + "</h3>";
            if (sys_tpl && sys_tpl.name) {
                var desc = '';
                if (sys_tpl.thumbnail) {
                    var thumb = sys_tpl.thumbnail;
                    if (thumb.indexOf("http") != 0) thumb = "https://www.origo.io" + thumb;
                    desc += '<div style="text-align:center; margin-bottom:20px;"><img style="max-height:80px;" src="' + thumb + '"></div>';
                }
                desc += sys_tpl.description || 'This stack is waiting for a nice description from its owner...';
                document.getElementById("wizardHelp").innerHTML = desc;
            } else {
                document.getElementById("wizardHelp").innerHTML =
                    'You are about to install a new stack from a custom master image.';
                q = dojo.query('.irigo-tooltip'); q.irigoTooltip && q.irigoTooltip();
            }
            dialog.show();
            document.getElementById("wizardHelp").style.display="block";
            dijit.byId("wizardContainer").selectChild(dijit.byId("wizardSubForm2"), true);
            $("#buildsystembutton").prop("disabled", false);
            $("#wizardHelp").scrollTop(0);
            systembuilder.system.updateWizardAccounts();
        },

        manage_in_tab: function(force) {
            systembuilder.system.cancelled = false;
            var manloc = home.currentManagementlink;
            if (home.currentItem && home.currentItem.status == 'upgrading' && !force) {
                manloc = '/stabile/static/html/upgrading.html';
            }
            window.open(manloc,'_blank');
        },
        terminal_in_tab: function() {
            var manloc = home.currentTerminallink;
            window.open(manloc,'_blank');
        },

        manage: function(managementlink, force, systemname, sysuuid) {
            console.log("Managing", systemname, sysuuid);
            if (!managementlink) managementlink = home.currentManagementlink;
            if (!managementlink) {
                IRIGO.toast("No management interface specified for this system");
                return;
            }
            console.log("Managing system:", managementlink);
            systembuilder.system.cancelled = false;
            if (!systemname && home.currentItem) systemname = home.currentItem.name;

        // Loading external URL's in iframe is no longer supported by most browsers
            if (managementlink.indexOf("http")==0) {
                systembuilder.system.manage_in_tab(force);
                return;
            }

            var dialog;
            if(dijit.byId('createSystemDialog') !== undefined){
                dialog = dijit.byId('createSystemDialog');
                if (systemname) dialog.set("title", "Manage: " + systemname);
            } else {
                dialog = new dijit.Dialog({
                    title: "Manage: " + systemname,
                    id: 'createSystemDialog',
                    resizable: true,
                    style: "width: 90%; overflow: auto;"
                });
                dialog.connect(dialog, "hide", function(e){
                    if (dojo.byId("manageSystemIframe")) dojo.byId("manageSystemIframe").src = '';
                });
            }
            if (sysuuid) dialog.set("sysuuid", sysuuid);
            else if (home.currentItem) dialog.set("sysuuid", home.currentItem.uuid);

            dojo.connect(dialog,"hide",function(o){
                systembuilder.system.cancelled = true;
            });

            if (home.currentItem && home.currentItem.status == 'upgrading' && !force) {
                var content = '<iframe src="/stabile/static/html/upgrading.html" id="manageSystemIframe" style="height:75vh;"></iframe>';
                dialog.set('content', content);
            } else {
                var content = '<iframe src="/stabile/static/html/loading.html" id="manageSystemIframe" style="height:75vh;"></iframe>';
                dialog.set('content', content);
                systembuilder.system.loadIframe(0, dialog, managementlink);
            }
            dialog.show();

        },
        terminal: function() {
            systembuilder.system.manage(home.currentTerminallink, false, "Terminal: " + home.currentItem.name);
        },

        close: function() {
            if(dijit.byId('createSystemDialog') !== undefined){
                dijit.byId('createSystemDialog').hide();
            }
        },

        upgrade: function(internalip) {
            IRIGO.toaster([{
                message: "Hang on, upgrading your app...",
                type: "message",
                duration: 2000
            }]);
            dojo.byId("manageSystemIframe").src = '/stabile/static/html/upgrading.html';

            dojo.xhrGet({
                url: "/stabile/systems?action=upgradesystem&internalip=" + internalip,
                failOK: true,
                timeout: 10000,
                handleAs : "json",
                load: function(response) {
                    if (response.message) {
                        IRIGO.toaster([{
                            message: response.message,
                            type: "message",
                            duration: 2000
                        }]);
                    }
                },
                error: function(response) {
                    console.log("got an error upgrading");
                }
            });

            dojo.subscribe("upgrade:update", function(task){
                if (task.managementlink && task.progress && task.progress==100) {
                    grid.alertDialog("Data export done", task.status + "<br><br>", "systembuilder.system.manage", task.managementlink, true);
                }
            });
        },

        loadIframe: function(i, d, link) {
            dojo.xhrGet({
                url: link,
                failOK: true,
                timeout: 30000,
                load: function(response) {
                    dojo.byId("manageSystemIframe").src = link;
                },
                error: function(response) {
                    console.log("got an error loading iframe", i);
                    if (systembuilder.system.cancelled==false) {
                        if (i<12) {
                            console.log("Loading in 1 sec...", link, i);
                            setTimeout(systembuilder.system.loadIframe, 1000,i+1, d, link);
                        } else {
                            console.log("giving up loading iframe");
                            IRIGO.toast("Management interface for this stack is not ready...");
                            dojo.byId("manageSystemIframe").src = "/stabile/static/html/notready.html";
                        }
                    }
                }
            });
        },

        build: function(){
            if (!systembuilder.system.done) {
                var appid = dijit.byId('wizard_appid').get('value');
                if (dijit.byId("wizard_account").options.length>1 && dijit.byId("wizard_account").value!=user.username) {
                    console.log("Keeping app", appid, subdom);
                    dojo.cookie("installsystem", appid, {path: '/', domain: subdom});
                    home.changeAccount(dijit.byId("wizard_account").value);
                    return;
                }
                $("#buildsystembutton").html('Installing&hellip; <i class="fa fa-cog fa-spin"></i>').prop("disabled", true);

                dojo.forEach(dijit.byId('wizardForm').getChildren(), function(input) {
                    input.set('disabled', true);
                });

                var name = dijit.byId('wizard_name').value;
                var master = dijit.byId('wizard_master').value + "";
                var memory = dijit.byId('wizard_memory').value;
                var vcpu = dijit.byId('wizard_vcpu').get('value');
                var network = dijit.byId('wizard_networktype1').value;
                var ports = dijit.byId('wizard_ports').value;
                var nicmodel = dijit.byId('wizard_nicmodel1').value;
                var diskbus = dijit.byId('wizard_diskbus').value;
                var storagepool = dijit.byId('wizard_storagepool').value;
                var storagepool2 = dijit.byId('wizard_storagepool2').value;
                var cdrom = dijit.byId('wizard_cdrom').value;
                var boot = dijit.byId('wizard_boot').value;
                var bschedule = dijit.byId('wizard_bschedule').value;
                var monitors = dijit.byId('wizard_monitors').value;
                var image2 = dijit.byId('wizard_image2').value;
                var instances = dijit.byId('wizard_instances').get('value');
                var start = dijit.byId('wizard_start').checked;
                var managementlink = dijit.byId('wizard_managementlink').get('value');

                var postData = '{"items":[{' +
                        '"action": "buildsystem", '+
                        '"name": "' + name + '",' +
                        '"master": "' + master + '",' +
                        '"memory": ' + memory + ',' +
                        '"vcpu": ' + vcpu + ',' +
                        '"networktype1": "' + network + '",' +
                        '"ports": "' + ports + '",' +
                        '"nicmodel1": "' + nicmodel + '",' +
                        '"diskbus": "' + diskbus + '",' +
                        '"storagepool": "' + storagepool + '",' +
                        '"storagepool2": "' + storagepool2 + '",' +
                        '"cdrom": "' + cdrom + '",' +
                        '"boot": "' + boot + '",' +
                        '"bschedule": "' + bschedule + '",' +
                        '"monitors": "' + monitors + '",' +
                        '"image2": "' + image2 + '",' +
                        '"instances": ' + instances + ',' +
                        '"managementlink": "' + managementlink + '",' +
                        '"appid": "' + appid + '",' +
                        '"start": ' + (start?1:0) +
                        '}]}';
                var xhrArgs = {
                    url: "/stabile/systems",
                    postData: postData,
                    load: function(data){
                        home.grid.refresh();
                        if (networks.grid && networks.grid.refresh) networks.grid.refresh();
                        if (images.grid && images.grid.refresh) images.grid.refresh();
                        if (servers.grid && servers.grid.refresh) servers.grid.refresh();
                        systembuilder.system.done = true;
                        $("#buildsystembutton").text("done").prop("disabled", false).hide();
                        var nid = /Status=OK sysuuid: (\S+)/.exec(data);
                        var sysuuid;
                        if (nid && nid.length>1) sysuuid = nid[1];
                        home.updateVitals("update");
                        home.monitoringGrid.refresh();
                        home.updateUsage();

                        var oq = /\S+=ERROR (Over quota .+)/i.exec(data);
                        var overquota;
                        if (oq && oq.length>1) overquota = oq[1];

                        if (overquota) {
                            IRIGO.toast("You have exceeded one or more of your ressource qoutas: " + overquota + "<br>Please contact your local administrator or Origo Systems if you want to raise your quota");
                            console.log("Over quota", overquota);
                            dialog.hide();
                        } else if (managementlink && start) {
                            var n = /Status=OK Network .* saved: (\S+)/i.exec(data);
                            var errors = /\S+=ERROR (.+)/i.exec(data);
                            if (errors && errors.length>1) {
                                IRIGO.toast("Error: " + errors[1]);
                                dialog.hide();
                            } else if (n && n.length>1) {
                                console.log("managing", data, n);
                                var l = managementlink.replace(/\{uuid\}/, n[1]);
                                if (!$('#createSystemDialog').is(":hidden")) systembuilder.system.manage(l, null, name, sysuuid);
                            } else {
                                console.log("not managing", data, n);
                                dialog.hide();
                            }
                        } else {
                            console.log("not managing", managementlink, start);
                            dialog.hide();
                        }

                        //var n=data.match(/external IP\: (.+)/g);
                        //if (n && managementlink && start) {
                        //    var link = "http://" + n[0].substring(12) + managementlink;
                        //    dijit.byId('wizard_managementlink').set('value', link);
                        //    dialog.set('href',link);
                        //} else {
                        //    dialog.hide();
                        //}
                    },
                    error: function(error){
                        ;
                    }
                }
                var deferred = dojo.xhrPost(xhrArgs);
                //console.log("Building system", master, name, memory, vcpus, instances, network);
            } else {
                console.log("systembulder done");
                dialog.hide();
            }

            /*function finish(){
                console.log("Updating all tabs...");
                //newStores.systems.reset();
                stores.networks.fetch({query: {user: user.username}});
                stores.networks.close();
                stores.images.fetch({query: {user: user.username}});
                stores.images.close();
                if (user.is_admin) ui_update.onUpdate({id: "nodes", force: "true"});
                home.grid.refresh();
            }*/
        }
    };
    window.systembuilder = systembuilder;
})



