define([
"dojo/on",
"dojo/_base/connect",
"dojo/cookie",
"steam2/statusColorMap",
"steam2/stores",
"steam2/models/Server",
"steam2/models/Image",
"steam2/models/Network",
"stabile/stores",
"dojox/grid/DataGrid",
"dojox/grid/TreeGrid",
"dijit/tree/ForestStoreModel",
"steam2/ServersGrid",
"steam2/ServersGridFormatters",
'stabile/griddialog',
"steam2/user",
"stabile/formatters",
'helpers/uuid',
"dijit/form/FilteringSelect",
"dijit/form/Select",
'dijit/InlineEditBox',
'dijit/form/RadioButton',
'dijit/form/Select',
'dijit/layout/BorderContainer',
'dojox/widget/Wizard',
'stabile/stats',
'stabile/wizards',
//'stabile/menu',
'stabile/systembuilder',
'stabile/ui_update',
'steam2/StatsChart',
"dijit/form/HorizontalSlider",
"dijit/form/HorizontalRuleLabels",
"dijit/form/SimpleTextarea",
"dijit/layout/ContentPane",
"dijit/Tree"
], function(on, connect, cookie, statusColorMap, newStores, Server, Image, Network, stores, DataGrid, TreeGrid, ForestStoreModel,
            ServersGrid, serverFormatters, griddialog, user, formatters) {

    var home = {
        _inited: false,
        chartsid: null,
        sliderCreated: false,
        chartsShown: false,
        chartSlider: null,
        chartCpuLoad: null,
        chartIO: null,
        chartNetworkActivity: null,

        saveServerValue : function(uuid, key, value, identifier) {
            if (uuid) {
//                jvalue = value.replace(/\+/g, "\\u002b");
                jvalue = value;
                if (!identifier) identifier = "uuid";
                var url;
                var postData;
                if (key=='downloadmasters' ||key=='disablesnat' || key.indexOf('externalip')==0 || key.indexOf('proxy')==0 || key.indexOf('vm')==0) {
                    url = "/stabile/systems/";
                    postData = { "action": "updateengineinfo" };
                    postData[key] = jvalue;
                } else if (identifier == "username") {
                    url = "/stabile/systems/";
                    postData = { "username": uuid, "action": "updateaccountinfo" };
                    postData[key] = jvalue;
                } else {
                    url = "/stabile/systems";
                    var items = [];
                    items[0][key] = jvalue;
                    items[0][identifier] = uuid;
                    postData = {"identifier": identifier, "label": identifier, "items": items};
                }
                $.ajax({
                    url: url,
                    type: 'PUT',
                    data: postData,
                    dataType: 'json',
                    success: function(data) {
                        server.parseResponse(data);
                        if (identifier == "username") {
                            if (data.indexOf("ERROR")==-1) {
                                if (value == '--') value = '';
                                user[key] = value;
                                home.grid.refresh();
                            } else {
                                dijit.byId("info_"+key+"_field").set('value', user[key]); // revert
                            }
                        }
                    },
                    complete: function(data) {
                        console.log("not parsing", data);
                    }
                });
            }
        },
        resetToAccountInfo : function() {
            if (!IRIGO.user.is_readonly) {
                $.get("/stabile/systems/?action=resettoaccountinfo", function(res) {
                    home.grid.refresh();
                    server.parseResponse(res);
                });
            }
        },
        showResetInfo: function() {
            grid.actionConfirmDialog('resettoaccountinfo', 'resettoaccountinfo', user.fullname, "reset? Your systems and servers contact info will be set to your account's info.", 'reset info', 'home.resetToAccountInfo');
        },
        restoreEngine: function() {
            var restoreid = dijit.byId("enginerestore")._getSelectedOptionsAttr().item.id[0];
            var restoretext;
            if (restoreid != user.engineid) {
                restoretext = "overwrite this engine's entire configuration from a backup of another engine with id: " + restoreid;
            } else {
                restoretext = "overwrite this engine's entire configuration from a previous backup of this engine?";
            }
            grid.actionConfirmDialog('restoreengine', 'restore1', user.enginename, restoretext, 'restore', 'home.updateEngine');
        },
        updateEngine : function(action) {
            var irigouser;
            var irigopwd;
            var engineid = IRIGO.user.engineid || dojo.byId('engineid').value;
            var enginename = dijit.byId('info_enginename_field').value || IRIGO.user.enginename;
            var engineurl = document.location.href.substring(0,document.location.href.lastIndexOf("/"));
            var data;
            if (!action) action = (user.enginelinked?"unlinkengine":"linkengine");

            if (action == 'restoreengine') {
                data = {
                    "items": [{restorefile:dijit.byId("enginerestore").value, engineuser:user.engineuser}]
                };
            } else if (!user.enginelinked) {
                if (!dojo.byId('irigouser')) return;
                irigouser = dojo.byId('irigouser').value;
                irigopwd = dojo.byId('irigopwd').value;
                data = [{user:irigouser, pwd:irigopwd, enginename:enginename,
                        engineid:engineid, engineurl:engineurl}];
            } else {
                data = {
                    "items": [{enginename:enginename, engineid:engineid, engineurl:engineurl}]
                };
            }
            if (!action) {
                $('#linkenginebutton').html('Update&hellip; <i class="fa fa-cog fa-spin"></i>');
            } else if (action == 'updateenginename') {
                if (enginename == IRIGO.user.enginename) return; // do nothing if enginename not changed
                else action = 'updateengine';
            } else {
                $('#' + action + 'button').html($('#' + action + 'button').html() + '&hellip; <i class="fa fa-cog fa-spin"></i>');
            }
            $('.linkengine').attr('disabled', true);

            var message;
            dojo.xhrPost({
                url: "/stabile/users?action=" + action,
                postData: dojo.toJson(data),
                load: function(response){
                    if (response.indexOf("Invalid credentials")!=-1) {
                        message = "Invalid credentials";
                    } else if (response.indexOf("Engine linked")!=-1) {
                        user.load();
                        user.releasepressure();
                        home.updateVitals('update');
                        user.enginelinked = true;
                        user.enginename = enginename;
                        document.title = enginename;
                        message = "Engine is now linked to Stabile Registry";
                        dojo.byId("info_linkengine_button").innerHTML = home.unlinkenginemsg;
                        stores.engines.close();
                        home.engines_field.setStore(stores.engines);
                        q = dojo.query('.irigo-tooltip'); q.irigoTooltip && q.irigoTooltip();
                    } else if (response.indexOf("Engine unlinked")!=-1 || response.indexOf("Unknown engine")!=-1) {
                        user.load();
                        user.releasepressure();
                        user.enginelinked = false;
                        dojo.byId("info_linkengine_button").innerHTML = home.linkenginemsg;
                        $("#engines_span").hide();
                        stores.engines.close();
                        home.engines_field.setStore(stores.engines);
                        q = dojo.query('.irigo-tooltip'); q.irigoTooltip && q.irigoTooltip();
                        message = "Engine is now unlinked";
                    } else if (response.indexOf("Engine updated")!=-1) {
                        user.enginename = enginename;
                        document.title = enginename;
                        user.load();
                        user.releasepressure();
                        home.updateVitals('update');
                        message = "Engine updated";
                    } else if (response.indexOf("Engine and users updated")!=-1) {
                        user.load();
                        user.releasepressure();
                        document.title = user.enginename;
                        home.updateVitals('update');
                        message = "Engine and users updated on Stabile Registry";
                        stores.engines.close();
                        dijit.byId("engines").setStore(stores.engines);
                    } else if (response.indexOf("not linked")!=-1) {
                        message = "There was a problem. Is engine already linked with another account?";
                    } else if (response.indexOf("Invalid credentials")!=-1) {
                        message = "Invalid credentials";
                    } else {
                        if (response.indexOf('Status=')!=-1)
                            message = response.substring(response.indexOf('Status=')+7);
                        else
                        	message = response;
                    }
                    IRIGO.toaster([{
                        message: message,
                        type: "message",
                        duration: 3000
                    }]);
                    if (home.linkEngineDialog) home.linkEngineDialog.hide();
                    console.log(response);
                },
                error: function(error){
                    console.error("Problem linking engine!", error);
                }
            });
            return false;
        },
        changePassword : function() {
            if (!IRIGO.user.is_readonly) {
                var form = dijit.byId('changepasswordform');
                if(form.validate()) {
                    var newpassword = $("#newpassword").val();
                    $.get("/stabile/users/?action=changepassword&password=" + newpassword, function (res) {
                        var result = server.parseResponse(res);
                        if (result.status == 'OK') {
                            home.changePasswordDialog.hide();
                        }
                    });
                }
            }
        },
        showChangePassword : function() {
            if (!home.changePasswordDialog) {
                home.changePasswordDialog = new dijit.Dialog({ id: 'changePasswordDialog', style: "width: 520px; max-height:400px; overflow: auto;"
                });
            }
            home.changePasswordDialog.set('title',"Change your password");
            var one = [
                '<form method="#home" onsubmit="home.changePassword();return false;" class="wizardForm" id="changepasswordform" dojoType="dijit.form.Form">',
                '<table border="0" style="margin:20px;">',
                '<tr id="tr_newpassword"><td class="wizardLabel">',
                '<label>New password:</label>',
                '</td><td class="wizardLabel">',
                '<input id="newpassword" data-dojo-type="dijit.form.ValidationTextBox" required="true" type="password" autocomplete="new-password" style="width:300px;" value="" />',
                '</td></tr>'].join('');
            one += [
                '<tr id="tr_confirmpassword"><td class="wizardLabel">',
                '<label>Confirm password:</label>',
                '</td><td class="wizardLabel">',
                '<input id="confirmpassword" data-dojo-type="dijit.form.ValidationTextBox" required="true" type="password" autocomplete="new-password" style="width:300px;" value="" />',
                '</td></tr>'].join('');
            one += [
                '<tr><td colspan="2">&nbsp;</td></tr>',
                '<tr><td></td></td><td align="right">',
                '<button id="updateenginebutton" class="btn btn-sm btn-success linkengine" type="submit"',
                ' onClick="home.changePassword(); return false;"',
                '>',
                'Submit',
                '</button> ',
                '</td></tr>',
                '</table>',
                '</span>',
                '</form>'].join('');

            home.changePasswordDialog.set('content',one);
            home.changePasswordDialog.show();
        },
        showLinkEngine : function() {
            user.load(); // reload user.enginename
            if (!home.linkEngineDialog) {
                home.linkEngineDialog = new dijit.Dialog({ id: 'linkEngineDialog', style: "nowidth: 520px; max-height:400px; overflow: auto;"
                });
            }
            var helplink = '<a id="irigo-link-tooltip" href="https://www.origo.io/info/stabiledocs/web/dashboard/info-tab/linkengine" rel="help" target="_blank" class="irigo-tooltip">help</a>';
            if (!user.enginelinked) {
                home.linkEngineDialog.set('title',"Link this engine to Stabile Registry " + helplink);
            } else {
                home.linkEngineDialog.set('title',"Engine linking " + helplink);
            }
            var one = [
                '<form method="#home" onsubmit="home.updateEngine();return false;" class="wizardForm" id="linkengineForm" dojoType="dijit.form.Form">',
                '<table border="0" style="margin:20px;">',
                '<tr id="tr_engineid"><td class="wizardLabel">',
                '<label>Engine ID:</label>',
                '</td><td class="wizardLabel">',
                '<input id="engineid" style="width:280px;" readonly disabled value="' + user.engineid + '"/>',
                '</td></tr>',
                '<tr id="tr_enginename"><td class="wizardLabel">',
                '<label>Engine name:</label>',
                '</td><td class="wizardLabel">',
                '<input id="enginename" style="width:280px;" readonly disabled value="' + (user.enginename?user.enginename:user.username+"'s Engine") + '" />',
                '</td></tr>'].join('');
            if (!user.enginelinked) {
                one += [
                        '<tr id="tr_username"><td colspan="2">',
                        '<h4>Stabile Registry credentials</h4>',
                        '</td></tr>',
                        '<tr id="tr_username"><td class="wizardLabel">',
                        '<label>Username:</label>',
                        '</td><td class="wizardLabel">',
                        '<input id="irigouser" required disabled value="' + user.username + '" style="width:160px;" />',
                        '</td></tr>',
                        '<tr id="tr_password"><td class="wizardLabel">',
                        '<label>Password:</label>',
                        '</td><td class="wizardLabel">',
                        '<input id="irigopwd" required type="password" style="width:160px;" />',
                        '</td></tr>'].join('');
                one += ['<tr><td></td><td align="right">',
                    '<button id="linkenginebutton" class="btn btn-sm btn-success linkengine" type="submit" style="margin: 2px;">',
                    'Link',
                    '</button>',
                    '</td></tr>',
                    '</table>',
                    '</span>',
                    '</form>'].join('');
            } else {
                one += [
                '<tr id="tr_engineuser"><td class="wizardLabel" >',
                '<label>Engine owner:</label>',
                '</td><td class="wizardLabel">',
                '<input id="engineuser" style="width:280px;" readonly disabled value="' + (user.engineuser?user.engineuser:'') + '" />',
                '</td></tr>',
                '<tr id="tr_enginerestore"><td class="wizardLabel">',
                '<label>Restore config and DB:</label>',
                '</td><td class="wizardLabel">',
                '<select id="enginerestore" style="width:280px;" dojoType="dijit.form.Select" store="stores.engineBackups" sortbylabel="false"></select> ',
                '<button id="restoreenginebutton" class="btn btn-xs btn-info linkengine" disabled type="button"',
                ' onClick="home.restoreEngine();"',
                '>',
                'Restore&hellip;',

                '</button>',
                '</td></tr>',
                '<tr><td colspan="2">&nbsp;</td></tr>',
                '<tr><td></td></td><td align="left">',
                '<button id="updateenginebutton" class="btn btn-sm btn-success linkengine" type="button"',
                ' onClick="home.updateEngine(\'updateengine\');"',
                '>',
                'Push config',
                '</button> ',

                '<button id="backupenginebutton" class="btn btn-sm btn-primary linkengine" type="button"',
                ' onClick="home.updateEngine(\'backupengine\');"',
                '>',
                'Backup config and DB',
                '</button> ',
                '<button id="linkenginebutton" class="btn btn-sm btn-danger linkengine" type="button"',
                ' onClick="home.updateEngine();"',
                '>',
                'Unlink',
                '</button> ',
                '</td></tr>',
                '</table>',
                '</span>',
                '</form>'].join('');
            }

            home.linkEngineDialog.set('content',one);
            var q = dojo.query('#irigo-link-tooltip', home.linkEngineDialog.domNode);
            if(q.irigoTooltip){q.irigoTooltip();};
            home.linkEngineDialog.show();
            stores.engineBackups.close();
            stores.engineBackups.fetch({query:{path: "*"}, onComplete: function(items) {if (items[0].path[0]!="#") {$("#restoreenginebutton").prop("disabled", false); dijit.byId("enginerestore").setStore(stores.engineBackups);} }});
        },
        setNotesValue : function(notesval, gridItem, fieldid) {
            var field = dijit.byId("info_" + fieldid + "_field");
            if (field) {
                field.cancel();
                field.set('onChange', null);
                field.set('value', notesval);
                field.set('onChange', function(){
                    home.grid.updateSystem(fieldid);
                });
            } else {
                field = new dijit.InlineEditBox({
                    id: "info_" + fieldid + "_field",
                    autoSave: false,
                    buttonSave: "Save",
                    buttonCancel: "Cancel",
                    editor: "dijit.form.SimpleTextarea",
                    width: "100%", height: "360px",
                    value: notesval,
                    onChange : home.grid.updateSystem(fieldid),
                    editorParams: {height:'', extraPlugins: ['dijit._editor.plugins.AlwaysShowToolbar']},
                    renderAsHTML: true
                }, dojo.byId(fieldid));
            }
            document.getElementById("info_" + fieldid).style.display = "block";
            if (user.is_readonly) {
                if (!field.disabled) field.setDisabled(true);
            } else {
                if (field.disabled) field.setDisabled(false);
            }
        },
        setFieldValue : function(fieldname, value) {
            var field = dijit.byId(fieldname);
            if (!field) {
                console.log("field not found", fieldname);
            } else {
                var onch = field.get('onChange');
                field.set('onChange', null);
                if (fieldname=="info_lastlogin_field") {
                    var newval = home.timestampToLocaleString(value);
                    if (newval != field.get('value')) field.set('value', newval);
                } else if (fieldname=="info_lastloginfrom_field" && value=='') {
                    field.set('value', '--');
                } else if (fieldname.indexOf("vmreadlimit")!=-1 || fieldname.indexOf("vmwritelimit")!=-1) {
                    var newval = ""+Math.round(value/1024/1024);
                    if (newval!=field.get('value')) field.set('value', newval);
                } else {
                    if (value!=field.get('value')) field.set('value', value);
                }
                field.set('onChange', onch);
                if (user.is_readonly) {
                    if (!field.disabled) field.setDisabled(true);
                } else {
                    if (field.disabled) field.setDisabled(false);
                }
            }
        },
        startServer : function(uuid) {
            home.saveServerValue(uuid, "action", "start");
        },
        grid: null,
        vitals: "",
        currentItem: null,
        currentCores: 0,
        totalServers: null,
        activeServers: null,
        currentUptimeMonth: null,
        currentUsageMonth: null,
        currentInternalip: null,
        currentExternalip: null,
        currentManagementlink: null,
        currentTerminallink: null,
        user: user,

        imagesOnShowItem: null,
        networksOnShowItem: null,
        servicesFilter: "service: '*'",
        userprops: ['fullname','email','phone','opfullname','opemail','opphone','alertemail','services','name','allowfrom',
                        'lastlogin','lastloginfrom', 'allowinternalapi', 'downloadmasters', 'disablesnat', 'enginename',
                        'externaliprangestart', 'externaliprangeend', 'proxyiprangestart', 'proxyiprangeend', 'proxygw',
                        'vmreadlimit', 'vmiopsreadlimit', 'vmwritelimit', 'vmiopswritelimit'],
        linkenginemsg: 'This engine is not linked to Stabile Registry <span style="float:right; display:block"><a href="#home" onClick="home.showLinkEngine()" >Link Engine...</a> <a id="irigo-externaliprangestart-tooltip" href="https://www.origo.io/info/stabiledocs/web/dashboard/info-tab/linkengine" rel="help" target="_blank" class="irigo-tooltip">help</a></span>',
        unlinkenginemsg: 'This engine is linked to Stabile Registry <span style="float:right; display:block"><a href="#home" onClick="home.showLinkEngine()">Engine linking...</a> <a id="irigo-externaliprangestart-tooltip" href="https://www.origo.io/info/stabiledocs/web/dashboard/info-tab/linkengine" rel="help" target="_blank" class="irigo-tooltip">help</a></span>',

        updateUser: function() {
            user.load();
            home.updateVitals('update');
        },
        updateVitals: function(gridItem) {
            home.vitals = document.getElementById('vitals');
            home.missingmonitors = document.getElementById('missingmonitors');
            home.missingbackups = document.getElementById('missingbackups');
            home.missingmonitors.innerHTML = "";
            home.currentCores = 0;
            //if (home.missingbackups) home.missingbackups.innerHTML = "";
            var vitals_system = document.getElementById('vitals_system');
            var vitals_server = document.getElementById('vitals_server');
            var info_server = document.getElementById('info_server');
            var info_notes = document.getElementById('info_notes');
            var info_contacts = document.getElementById('info_contacts');
            var info_security = document.getElementById('info_security');
            var info_name = document.getElementById('info_name');
            var info_recovery = document.getElementById('info_recovery');
            var appstatus = document.getElementById('appstatus');
            var appid = document.getElementById('appid');
            var info_resettoaccountinfo_tr = document.getElementById('info_resettoaccountinfo_tr');
            var info_linkengine_tr = document.getElementById("info_linkengine_tr");
            var info_linkengine = document.getElementById("info_linkengine_button");
            var info_downloadmasters_tr = document.getElementById("info_downloadmasters_tr");
            var home_add_empty = document.getElementById("home_add_empty");
            var v;
            var sysmemory = 0; var asysmemory = 0;
            var sysvcpu = 0; var asysvcpu = 0;
            var images=0; var images2=0; var aimages=0; var aimages2=0; var cdroms=0; var networks=0;

            if (gridItem=="update" || gridItem==null) {
                home.grid.store.fetch({query:{uuid: "*"}, onComplete: function(res) {
                    if (home.currentItem && home.currentItem!=null) {
                        home.updateVitals(home.currentItem);
                    } else {
                        home.updateVitals(res);
                    }
                }});

            // Display vitals - no items selected, gridItem contains array with all items
            } else if (gridItem && (gridItem.length || gridItem.length==0)) {
                var itemsHash = [];
                var nodesHash = [];
                var mac;
                var domstatus;
                var maccpucores;
                v = "<div id=\"vitalsHeader\"><h3>All systems</h3></div>";
                for (i in gridItem) {
                    if (gridItem[i].issystem) {
                        var children = gridItem[i].children;
                        for (j in children) {
                            if (children[j].memory && !children[j].issystem & !itemsHash[children[j].uuid]) {
                                sysmemory += children[j].memory;
                                if (children[j].status!="inactive" && children[j].status!="shutoff") {
                                    asysmemory += children[j].memory;
                                    if (children[j].status=="running" || children[j].status=="paused") asysvcpu += children[j].vcpu;
                                    aimages++;
                                    if (children[j].image2!="--") aimages2++;
                                }
                                sysvcpu += children[j].vcpu;
                                images++;
                                if (children[j].image2!="--") images2++;
                                if (children[j].cdrom!="--") cdroms++;
                                networks++;
                                if (children[j].networkid2!="--") networks++;
                                itemsHash[children[j].uuid] = 1;

                                domstatus = children[j].status;
                                mac = children[j].macname;
                                maccpucores = parseInt(children[j].maccpucores);
                                if (domstatus!='shutoff' && domstatus!='inactive' &&
                                        mac && mac!='--' && maccpucores && maccpucores != '--') {
                                    if (nodesHash[mac]) {
                                        nodesHash[mac] = nodesHash[mac]+1;
                                    } else {
                                        nodesHash[mac] = 1;
                                        home.currentCores = home.currentCores+maccpucores;
                                    }
                                }
                            }
                        }
                    } else {
                        if (gridItem[i].memory && !gridItem[i].issystem && !itemsHash[gridItem[i].uuid]) {
                            sysmemory += parseInt(gridItem[i].memory);
                            sysvcpu += parseInt(gridItem[i].vcpu);
                            images++;
                            if (gridItem[i].image2!="--") images2++;
                            if (gridItem[i].cdrom!="--") cdroms++;
                            networks++;
                            if (gridItem[i].networkid2!="--") networks++;
                            itemsHash[gridItem[i].uuid] = 1;
                            if (gridItem[i].status!="inactive" && gridItem[i].status!="shutoff") {
                                asysmemory += parseInt(gridItem[i].memory);
                                if (gridItem[i].status=="running" || gridItem[i].status=="paused") asysvcpu += parseInt(gridItem[i].vcpu);
                                aimages++;
                                if (gridItem[i].image2!="--") aimages2++;
                            }
                            domstatus = gridItem[i].status;
                            mac = gridItem[i].macname;
                            maccpucores = parseInt(gridItem[i].maccpucores);
                            if (domstatus!='shutoff' && domstatus!='inactive' &&
                                    mac && mac!='--' && maccpucores && maccpucores != '--') {
                                if (nodesHash[mac]) {
                                    nodesHash[mac] = nodesHash[mac]+1;
                                } else {
                                    nodesHash[mac] = 1;
                                    home.currentCores = home.currentCores+maccpucores;
                                }
                            }
                        }
                    }
                }
                v += "<b>Total servers:</b> " + images + " (" + sysvcpu + " vCPU" + (sysvcpu>1?"s, ":", ") +
                        sysmemory + " MB memory" + ")<br>";
                v += "<b>Active servers:</b> " + aimages + " (" + asysvcpu + " vCPU" + (asysvcpu>1?"s, ":", ") +
                        asysmemory + " MB memory" + ")<br>";
                v += "<b>Images:</b> " + (images + images2);
                v += " (" + (aimages + aimages2) + " active) ";
                if (cdroms>0) v += "<b>CDs:</b> " + cdroms;
                v += "<br><b>Connections:</b> " + networks + "<br>";
                if (user.is_admin || user.node_storage_allowed) {
                    v += "<b>Active nodes:</b>  <span title=\"" + Object.keys(nodesHash).join(", ") + "\">" + Object.keys(nodesHash).length +
                            " (" + home.currentCores + " cores)</span><br>";
                }
                home.vitals.innerHTML = v;

                if (home.totalServers==null) {
                    home.totalServers = images;
                    home.activeServers = aimages;
                } else {
                    home.totalServers = images;
                    home.activeServers = aimages;
                }
//                home.monitoringGrid.updateMissingMonitors();
                appstatus.innerHTML = "";
                appid.innerHTML = "";
                for (var i in home.userprops) { // Set fullname, email, alertemail, etc.
                    var prop = home.userprops[i];
                    if (user[prop] && user[prop]!="--") {
                        home.setFieldValue("info_"+prop+"_field" , user[prop]);
                    } else {
                        home.setFieldValue("info_"+prop+"_field" , "");
                    }
                }
                home.setNotesValue("", null, "notes");
                home.setNotesValue("", null, "recovery");
                document.getElementById('info_header').innerHTML = "Account";
                info_name.style.display = "none";
                info_contacts.style.display = "block";
                info_security.style.display = "block";
                $("#info_rtfs").hide();
                info_recovery.style.display = "none";
                vitals_server.style.display = "none";
                vitals_system.style.display = "none";
                info_server.style.display = "none";
                info_notes.style.display = "none";
                if (user.is_readonly) info_resettoaccountinfo_tr.style.display = "none";
                else info_resettoaccountinfo_tr.style.display = "";
                if (user.is_readonly || !user.is_admin) {
                    info_linkengine_tr.style.display = "none";
                    info_downloadmasters_tr.style.display = "none";
                    //home_add_empty.style.display = "none";
                    $(".info-engine").hide();
                } else {
                    if (user.enginelinked) info_linkengine.innerHTML = home.unlinkenginemsg;
                    else info_linkengine.innerHTML = home.linkenginemsg;
                    info_linkengine_tr.style.display = "table-row";
                    info_downloadmasters_tr.style.display = "table-row";
                    q = dojo.query('.irigo-tooltip'); q.irigoTooltip && q.irigoTooltip();
                    $(".info-engine").show();
                }
                $(".info-security").show();
                $(".info-account").show();
                $(".info-system").hide();
                $(".info-services").hide();

                // Display vitals for a system
            } else if (gridItem.issystem == 1) {
                nodesHash = [];
                v = '<div id="vitalsHeader"><div style="width:97%;"><div class="row"><span class="col-sm-6" style="display:inline-block;"><h3>Stack: '+ gridItem.name + '</h3></span><span style="display:inline-block; text-align:right;">';
                v += '<span class="terminal"><button dojoType="dijit.form.Button" class="btn btn-info btn-xs" '
                    + ((user.is_readonly)?'disabled ':'')
                    + 'id="terminal_button" type="button" onclick="systembuilder.system.terminal();";>Terminal</button>';
                v += '<span style="padding: 0 0 4px 6px;"><a id="terminal_in_tab" class="manage_in_tab" style="margin-right:10px;" href="#home" class="small" onclick="systembuilder.system.terminal_in_tab();">in new tab</a></span></span>';
                v += '<span class="manage_system"><button class="btn btn-success btn-xs" '
                    + ((user.is_readonly)?'disabled ':'')
                    + 'id="manage_system_button" type="button" onclick="systembuilder.system.manage();">Manage</button>';
                v += '<span style="padding: 0 0 4px 6px;"><a id="manage_in_tab" class="manage_in_tab" href="#home" class="small" onclick="systembuilder.system.manage_in_tab();">in new tab</a></span></span>';
                v += "</span></div></div>";
                for (i in gridItem.children) {
                    if (gridItem.children[i].memory && !gridItem.children[i].issystem) {
                        sysmemory += parseInt(gridItem.children[i].memory);
                        sysvcpu += parseInt(gridItem.children[i].vcpu);
                        images++;
                        if (gridItem.children[i].image2!="--") images2++;
                        if (gridItem.children[i].cdrom!="--") cdroms++;
                        networks++;
                        if (gridItem.children[i].networkid2!="--") networks++;

                        if (gridItem.children[i].status!="inactive" && gridItem.children[i].status!="shutoff") {
                            asysmemory += parseInt(gridItem.children[i].memory);
                            if (gridItem.children[i].status=="running" || gridItem.children[i].status=="paused") {
                                asysvcpu += parseInt(gridItem.children[i].vcpu);
                            }
                            aimages++;
                            if (gridItem.children[i].image2!="--") aimages2++;
                        }
                        domstatus = gridItem.children[i].status;
                        mac = gridItem.children[i].macname;
                        maccpucores = parseInt(gridItem.children[i].maccpucores);
                        if (domstatus!='shutoff' && domstatus!='inactive' &&
                                mac && mac!='--' && maccpucores && maccpucores != '--') {
                            if (nodesHash[mac]) {
                                nodesHash[mac] = nodesHash[mac]+1;
                            } else {
                                nodesHash[mac] = 1;
                                home.currentCores = home.currentCores+maccpucores;
                            }
                        }
                    }
                }
                var imageItem = stores.images.fetchItemByIdentity({identity: gridItem.imageuuid});
                var serverLink = '<a href="#home" onclick="servers.grid.dialog.show(stores.servers.fetchItemByIdentity({identity:\'' + imageItem.domains + '\'}));">' + imageItem.domainnames + '</a>';
                v += "<b>Administration server:</b> " + serverLink + "<br>";
                v += "<b>Total servers:</b> " + images + " (" + sysvcpu + " vCPU" + (sysvcpu>1?"s, ":", ") +
                        sysmemory + " MB memory" + ")<br>";
                v += "<b>Active servers:</b> " + aimages + " (" + asysvcpu + " vCPU" + (asysvcpu>1?"s, ":", ") +
                        asysmemory + " MB memory" + ")<br>";
                v += "<b>Total images:</b> " + (images + images2);
                v += " (" + (aimages + aimages2) + " active)<br>";
                if (cdroms>0) v += "<b>CDs:</b> " + cdroms + ", ";
                v += "<b>Connections:</b> " + networks + "<br>";
                if (user.is_admin || user.node_storage_allowed) v += "<b>Active nodes:</b>  <span title=\"" + Object.keys(nodesHash).join(", ") + "\">" + Object.keys(nodesHash).length + " (" + home.currentCores + " cores)</span><br>";
                home.vitals.innerHTML = v;
                v += "<b>Created:</b> " + home.timestampToLocaleString(gridItem.created) + "<br>";
                v += "<b>UUID:</b> " + gridItem.uuid + "<br>";
                home.vitals.innerHTML = v;
                home.totalServers = images;
                home.activeServers = aimages;
//                home.monitoringGrid.updateMissingMonitors();
                appid.innerHTML = "";

                for (var k in home.userprops) { // Set fullname, email, alertemail, etc.
                    var kprop = home.userprops[k];
                    if (gridItem[kprop] && gridItem[kprop]!="--") {
                        home.setFieldValue("info_"+kprop+"_field" , gridItem[kprop]);
                    } else if (user[kprop] && user[kprop]!="--") {
                        home.setFieldValue("info_"+kprop+"_field" , user[kprop]);
                    } else {
                        home.setFieldValue("info_"+kprop+"_field" , "");
                    }
                }

                var sysnotesval = (gridItem.notes && gridItem.notes!="--")?gridItem.notes:"";
                home.setNotesValue(sysnotesval, gridItem, "notes");
                var recoverynotesval = (gridItem.recovery && gridItem.recovery!="--")?gridItem.recovery:"";
                home.setNotesValue(recoverynotesval, gridItem, "recovery");
                document.getElementById('info_header').innerHTML = "Stack";
                info_name.style.display = "block";
                info_contacts.style.display = "block";
                info_security.style.display = "none";
                $("#info_rtfs").show();
                info_recovery.style.display = "block";
                vitals_server.style.display = "none";
                vitals_system.style.display = "inline";
                info_server.style.display = "none";
                info_notes.style.display = "inline";
                info_resettoaccountinfo_tr.style.display = "none";
                info_linkengine_tr.style.display = "none";
                info_downloadmasters_tr.style.display = "none";

                $(".info-services").show();
                $(".info-security").hide();
                $(".info-engine").hide();
                $(".info-account").hide();
                $(".info-system").show();

                var url = "/stabile/images?action=listimages"; //images&image=listall";
                if (stores.unusedImages2.url != url) {
                    stores.unusedImages2.url = url;
                }
                home.currentManagementlink = '';
                home.currentTerminallink = '';
                if (home.currentItem.imageuuid) {
                    $.get("/stabile/images/" + home.currentItem.imageuuid, function(item) {home.updateManagementlink(item)});
                } else {
                    home.updateManagementlink(null);
                }

                // Display vitals for a server
            } else {
                var serverLink = '<a href="#home" onclick="servers.grid.dialog.show(stores.servers.fetchItemByIdentity({identity: \'' + gridItem.uuid  + '\'}));">' + gridItem.name + '</a>';

                var imageLink = '<a href="#home" onclick="$.get(\'/stabile/images/' + gridItem.imageuuid + '\',  function(item) {home.showImageItemDialog(item)});">' + gridItem.imagename + '</a>';
                var image2Link = '<a href="#home" onclick="$.get(\'/stabile/images/' + gridItem.imageuuid2 + '\',  function(item) {home.showImageItemDialog(item)});">' + gridItem.image2name + '</a>';

                var cdrom = gridItem.cdrom;
                var networkLink = '<a href="#home" onclick="networks.grid.dialog.show(stores.networks.fetchItemByIdentity({identity: \'' + gridItem.networkuuid1  + '\'}));">' + gridItem.networkname1 + '</a>';
                var networkLink2 = '<a href="#home" onclick="networks.grid.dialog.show(stores.networks.fetchItemByIdentity({identity: \'' + gridItem.networkuuid2  + '\'}));">' + gridItem.networkname2 + '</a>';
                var status = gridItem.status;
                aimages = (status=="inactive" || status=="shutoff")?0:1;

                if (gridItem.cdrom && gridItem.cdrom!="--") cdrom = gridItem.cdrom.substring(gridItem.cdrom.lastIndexOf("/")+1);

                appstatus.innerHTML = "";
                appid.innerHTML = "";

                v = '<div id="vitalsHeader"><div style="width:97%;"><div class="row"><span class="col-sm-6" style="display:inline-block;"><h3>Server: '+ serverLink + '</h3></span><span class="col-sm-6" style="display:inline-block; text-align: right;">';
                v += '<span class="terminal"><button dojoType="dijit.form.Button" class="btn btn-info btn-xs" '
                    + ((user.is_readonly)?'disabled ':'')
                    + 'id="terminal_button" type="button" onclick="systembuilder.system.terminal();";>Terminal</button>';
                v += '<span style="padding: 0 0 4px 6px;"><a id="terminal_in_tab" class="manage_in_tab" style="margin-right:10px;" href="#home" class="small" onclick="systembuilder.system.terminal_in_tab();">in new tab</a></span></span>';
                v += '<span class="manage_system"><button class="btn btn-success btn-xs" '
                    + ((user.is_readonly)?'disabled ':'')
                    + 'id="manage_system_button" type="button" onclick="systembuilder.system.manage();">Manage</button>';
                v += '<span style="padding: 0 0 4px 6px;"><a id="manage_in_tab" class="manage_in_tab" href="#home" class="small" onclick="systembuilder.system.manage_in_tab();">in new tab</a></span></span>';
                v += "</span></div></div>";
                v += (aimages>0?"<b>Active server:</b> ":"</h3></div><b>Inactive server</b>: ") + gridItem.vcpu + " vCPU" + (gridItem.vcpu>1?"s, ":", ") +
                gridItem.memory + " MB memory" + "<br>" +
                "<b>Primary image:</b> " + imageLink + "<br>" +
                (gridItem.image2=="--"?"":"<b>2nd image:</b> " + image2Link + "<br>") +
                (gridItem.cdrom=="--"?"":"<b>CD:</b> " + cdrom + (gridItem.boot=="hd"?"<br>":" (boot)<br>") ) +

                        "<b>Connection:</b> " +
                // (!gridItem.networkid1 || gridItem.networkid1=="0" || gridItem.networkid1=="1"?" Only outgoing network connectivity<br>":networkLink + "<span id='vitals_network'></span><br>") +
                networkLink + "<span id='vitals_network'></span><br>" +

                (gridItem.networkid2=="--"?"":"<b>2nd connection:</b> " +
                // (!gridItem.networkid2 || gridItem.networkid2=="0" || gridItem.networkid2=="1"?" Only outgoing network connectivity<br>":networkLink2 + "<span id='vitals_network2'></span><br>"));
                networkLink2 + "<span id='vitals_network2'></span><br>");

                if (gridItem.status!='shutoff' && gridItem.status!='inactive' &&
                        (user.is_admin || user.node_storage_allowed) && (gridItem.maccpucores && gridItem.maccpucores!='--'))
                    v += "<b>Node:</b> <span title=\"" + gridItem.mac + "\">" + gridItem.macname + " (" + gridItem.maccpucores + " cores)" + "</span><br>";

                v += "<b>Created:</b> " + home.timestampToLocaleString(gridItem.created) + "<br>";
                home.vitals.innerHTML = v;
                if (gridItem.networktype1 == "gateway" && gridItem.networkid1>1) {
                    stores.networks.fetchItemByIdentity({identity: gridItem.networkuuid1, onItem: home.updateVitals_network});
                    home.servicesFilter = "service: 'ping' OR service: 'diskspace'";
                //    stores.unusedImages2.url = url;
                } else if (gridItem.networkuuid1 && gridItem.networkuuid1!="0" && gridItem.networkuuid1!="1") {
                    stores.networks.fetchItemByIdentity({identity: gridItem.networkuuid1, onItem: home.updateVitals_network});
                    home.servicesFilter = "service: '*'";
                    var url = "/stabile/images?action=listimages"; //images&image=listall";
                    stores.unusedImages2.url = url;
                } else {
                    home.servicesFilter = "service: 'diskspace'";
                }

                if (gridItem.networkuuid2 && gridItem.networkuuid2!="--" &&
                        gridItem.networkuuid2!="0" && gridItem.networkuuid2!="1") {
                    stores.networks.fetchItemByIdentity({identity: gridItem.networkuuid2, onItem: home.updateVitals_network2});
                }

                if (home.info_system_field) {
                    home.info_system_field.set('value',gridItem.system);
                } else {
                    home.info_system_field = new dijit.form.FilteringSelect({
                        id: "info_system_field",
                        value: gridItem.system,
                        store: stores.systemsSelect
                    }, dojo.byId("info_system_field"));
                }
                if (user.is_readonly) {
                    if (!home.info_system_field.disabled) {
                        home.info_system_field.setDisabled(true);
                        document.getElementById("updateSystemButton").style.display = "none";
                    }
                } else {
                    if (home.info_system_field.disabled) {
                        home.info_system_field.setDisabled(false);
                        document.getElementById("updateSystemButton").style.display = "inline";
                    }
                }

                for (var j in home.userprops) { // Set fullname, email, alertemail, etc.
                    var uprop = home.userprops[j];
                    if (gridItem[uprop] && gridItem[uprop]!="--") {
                        home.setFieldValue("info_"+uprop+"_field" , gridItem[uprop]);
                    } else if (user[uprop] && user[uprop]!="--") {
                        home.setFieldValue("info_"+uprop+"_field" , user[uprop]);
                    } else {
                        home.setFieldValue("info_"+uprop+"_field" , "");
                    }
                }

                var notesval = (gridItem.notes && gridItem.notes!="--")?gridItem.notes:"";
                home.setNotesValue(notesval, gridItem, "notes");
                var recoveryval = (gridItem.recovery && gridItem.recovery!="--")?gridItem.recovery:"";
                home.setNotesValue(recoveryval, gridItem, "recovery");
                home.totalServers = 1;
                home.activeServers = aimages;
                document.getElementById('info_header').innerHTML = "Server";
//                home.monitoringGrid.updateMissingMonitors();

                info_name.style.display = "block";
                info_contacts.style.display = "block";
                info_security.style.display = "none";
                $("#info_rtfs").show();
                info_recovery.style.display = "block";
                vitals_server.style.display = "inline";
                vitals_system.style.display = "none";
                info_server.style.display = "inline";
                info_notes.style.display = "inline";
                info_resettoaccountinfo_tr.style.display = "none";
                info_linkengine_tr.style.display = "none";
                info_downloadmasters_tr.style.display = "none";

                $(".info-services").show();
                $(".info-security").hide();
                $(".info-engine").hide();
                $(".info-account").hide();
                $(".info-system").show();

                home.currentManagementlink = '';
                home.currentTerminallink = '';
                $.get("/stabile/images/" + home.currentItem.imageuuid, function(item) {home.updateManagementlink(item)});
            }
        },

        updateVitals_network: function(network) {
            var vitals_network = document.getElementById('vitals_network');
            var content = "";
            if (!network || !vitals_network) {
                ;
            } else if (network.type=="ipmapping") {
                home.currentExternalip = network.externalip;
                home.currentInternalip = network.internalip;
                content = " (" + network.internalip +
                        " / <a href=\"http://" + network.externalip + "\" target=\"_blank\">" + network.externalip + "</a>)";
            } else if (network.type=="externalip") {
                home.currentExternalip = network.externalip;
                home.currentInternalip = null;
                content = " (<a href=\"http://" + network.externalip + "\" target=\"_blank\">" + network.externalip + "</a>)";
            } else if (network.type=="internalip") {
                home.currentExternalip = null;
                home.currentInternalip = network.internalip;
                content = " (" + network.internalip + ")";
            } else {
                home.currentExternalip = null;
                home.currentInternalip = null;
            }
            if (network && (network.type=="ipmapping" || network.type=="externalip")) {
                if (network.status == "down" || network.status == "nat") {
                    content += " <span style=\"color:#CCCCCC\"> disabled</span>";
                }
            }
            if (vitals_network) vitals_network.innerHTML = content;
        },

        updateVitals_network2: function(network) {
            var vitals_network = document.getElementById('vitals_network2');
            var content = "";
            if (!network || !vitals_network) {
                ;
            } else if (network.type=="ipmapping") {
                content = " (" + network.internalip +
                        " / <a href=\"http://" + network.externalip + "\" target=\"_blank\">" + network.externalip + "</a>)";
            } else if (network.type=="externalip") {
                content = " (<a href=\"http://" + network.externalip + "\" target=\"_blank\">" + network.externalip + "</a>)";
            } else if (network.type=="internalip") {
                content = " (" + network.internalip + ")";
            }
            if (network.type=="ipmapping" || network.type=="externalip") {
                if (network.status == "down" || network.status == "nat") {
                    content += " <span style=\"color:#CCCCCC\"> disabled</span>))";
                }
            }
            if (vitals_network) vitals_network.innerHTML = content;
        },

        updateManagementlink: function(image) {
            var appstatus = document.getElementById('appstatus');
            var appid = document.getElementById('appid');
            var link = "";
            var tlink = "";
            var applink = "";
            var info = "";
            var appinfo = "";

            console.log("updating managementlink", image);
            if (image && image.appid) {
                if (IRIGO.user.appstoreurl)
                    applink = IRIGO.user.appstoreurl + "#app-" + image.appid;
                else
                    applink = "https://www.stabile.io/cloud#app-" + image.appid;
            }
            if (image && image.managementlink && image.managementlink!='--') {
                link = image.managementlink.replace(/\{uuid\}/, home.currentItem.networkuuid1);
                link = link.replace(/\{externalip\}/, home.currentExternalip);
                link = link.replace(/\{internalip\}/, home.currentInternalip);
                if (link.indexOf("/")!=0) link = "/stabile/" + link;
                //console.log("replacing", image.managementlink, home.currentItem.networkuuid1, link);
            } else {
                console.log("no managementlink");
                home.currentManagementlink = '';
            }
            if (image && image.terminallink && image.terminallink!='--') {
                tlink = image.terminallink.replace(/\{uuid\}/, home.currentItem.networkuuid1);
                tlink = tlink.replace(/\{externalip\}/, home.currentExternalip);
                tlink = tlink.replace(/\{internalip\}/, home.currentInternalip);
                if (tlink.indexOf("/")!=0) tlink = "/stabile/" + tlink;
                //console.log("got terminal", tlink, image.terminallink);
            } else {
                console.log("no terminallink");
                home.currentTerminallink = '';
            }

            $(".manage_system").hide();
            $(".terminal").hide();
            //document.getElementById("manage_system_button").style.display= 'none';
            //document.getElementById("terminal_button").style.display= 'none';
            if (tlink != "" && tlink != "--") {
                if (home.currentItem.status == "running" || home.currentItem.status == "degraded" || home.currentItem.status == "upgrading") {
                    home.currentTerminallink = tlink + "?nocache=" +  Math.random().toString(36).substring(7);
                    $(".terminal").show();
                    //document.getElementById("terminal_button").style.display= 'inline';
                }
            }
            if (link != "" && link != "--") {
                if (home.currentItem.status == "running" || home.currentItem.status == "degraded" || home.currentItem.status == "upgrading") {
                    home.currentManagementlink = link + "?nocache=" +  Math.random().toString(36).substring(7);
                    $(".manage_system").show();
                    //document.getElementById("manage_system_button").style.display= 'inline';
                } else {
                    info = "<span style=\"color:#CCCCCC\">(Stack is currently " + home.currentItem.status + ").</span>";
                    home.currentManagementlink = '';
                }
            }
            appstatus.innerHTML = info;
            if (image && image.version != "" && image.version != "--") {
                appinfo = "You are running version " + image.version + " of this stack. ";
            }
            if (image && image.appid != "" && image.appid != "--") {
                appinfo += "Read more at <a href=\"" + applink + "\" target=\"_blank\" id=\"appstorelink\">the registry</a>";
            }
            appid.innerHTML = appinfo;
        },

        updateUptime: function() {
            var param="";
            if (home.currentItem && home.currentItem.issystem) {
                var ym = home.currentUptimeMonth;
                param = "&uuid=" + home.currentItem.uuid + "&yearmonth=" + ym + "&issystem=1";
            } else {
                var uuid = home.currentItem?home.currentItem.uuid:"";
                var ym = home.currentUptimeMonth;
                param = "&uuid=" + uuid + "&yearmonth=" + ym;
            }
            dojo.xhrGet({
                url: "/stabile/systems?action=listuptime&format=html" + param,
                load: function(response) {
                    var uptime = document.getElementById("uptime");
                    uptime.innerHTML = response;
                }
            });
        },

        usageCSV: function() {
            var param="";
            var url="";
            if (home.currentUsageMonth == "current") {
                url = "/stabile/users?action=usage&format=csv";
                param = home.currentItem?"&uuid="+home.currentItem.uuid:"";
            } else {
                url = "/stabile/users?action=usage&format=csv";
                var year = home.currentUsageMonth.substr(0,4);
                var month = home.currentUsageMonth.substr(5,2);
                param = "&year=" + year + "&endmonth=" + month;
            }
            return url + param;
        },

        updateUsage: function() {
            var tabid;
            if (dijit.byId('homeTabs')) tabid = dijit.byId('homeTabs').selectedChildWidget.id;
            if (!home.currentItem) dijit.byId("usage_select").set("disabled", false);
                var param="";
                var url="";
                if (home.currentUsageMonth == "current") {
                    url = "/stabile/users?action=usagestatus&format=html";
                    param = home.currentItem?"&uuid="+home.currentItem.uuid:"";
                } else {
                    url = "/stabile/users?action=usageavgstatus&format=html";
                    var year = home.currentUsageMonth.substr(0,4);
                    var month = home.currentUsageMonth.substr(5,2);
                    param = "&year=" + year + "&month=" + month;
                }
                dojo.xhrGet({
                    url: url + param,
                    load: function(response) {
                        var usage = document.getElementById("usage");
                        usage.innerHTML = response;
                    }
                });
                dojo.xhrGet({
                    url: "/stabile/users?action=usage" + param,
                    handleAs : "json",
                    load: function(response) {
                        var total_cost = document.getElementById("total_cost");
                        if (response)
                            total_cost.innerHTML = (home.currentUsageMonth == "current")?"Projected cost/month: " + response.totalcost : "Total cost for month: " + response.totalcostavg;
                    }
                });
        },

        updateMonitoring: function() {
            var tabid;
            //if (dijit.byId('homeTabs')) tabid = dijit.byId('homeTabs').selectedChildWidget.id;
            //if (tabid && tabid=="monitoringContentPane") {
            //    console.log("updating monitoring for:", home.currentItem);
                home.monitoringGrid.refresh();
                if (!home.currentItem || home.currentItem.issystem) {
                    $("#new_monitor_button").hide();
                    //dijit.byId("new_monitor_button").set('style', 'display:none');
                } else {
                    $("#new_monitor_button").show();
                    //dijit.byId("new_monitor_button").set('style', 'display:inline');
                }
                //dijit.byId('monitoringContentPane').set('style','width:500px'); // Adjust width...
            //}
        },

        updateOSList: function() {
            var param="";
            if (home.currentItem) {
                param = "&uuid=" + home.currentItem.uuid;
            }
            dojo.xhrGet({
                url: "/stabile/systems?action=register\&format=html" + param,
                load: function(response) {
                    var oslist = document.getElementById("oslist");
                    oslist.innerHTML = response;
                    $("#oslistcsv_link")[0].href ="/stabile/systems/?action=register&format=csv" + param;
                }
            });
        },

        updatePackages: function() {
            home.updateOSList();
            var param="";
            if (home.currentItem) {
                param = "&uuid=" + home.currentItem.uuid;
            }
            dojo.xhrGet({
                url: "/stabile/systems?action=packages\&format=html" + param,
                load: function(response) {
                    var packs = document.getElementById("packages");
                    packs.innerHTML = response;
                    $("#packlistcsv_link")[0].href ="/stabile/systems/?action=packages&format=csv" + param;
                }
            });
        },

        loadPackages: function() {
            if (home.currentItem) {
                var data = {
                    "items": [{uuid:home.currentItem.uuid, action:"load", issystem:home.currentItem.issystem}]
                };
                $("#load_packages").prop("disabled", true).html('Scanning&hellip; <i class="fa fa-cog fa-spin"></i>');;
                $("#clear_packages").prop("disabled", true);
                dojo.xhrPost({
                    url: "/stabile/systems?action=packages", // + (ui_update.session?"&s="+ui_update.session:""),
                    postData: dojo.toJson(data),
                    load: function(response){
                        home.updatePackages();
                        server.parseResponse(response);
                        $("#load_packages").prop("disabled", false).html('Rescan server(s)&hellip;');
                        if (!user.is_readonly) $("#clear_packages").prop("disabled", false);
                    },
                    error: function(error){
                        $("#load_packages").prop("disabled", false).html('Rescan server(s)&hellip;');
                        $("#clear_packages").prop("disabled", false);
                        er("grid::actionHandler", error);
                    }
                });
            }
        },

        clearPackages: function() {
            var data;
            if (home.currentItem) {
                data = {
                    "items": [{uuid:home.currentItem.uuid, action:"remove", issystem:home.currentItem.issystem}]
                };
            } else {
                data = {
                    "items": [{uuid:"*", action:"remove", issystem:1}]
                };
            }

            dojo.xhrPost({
                url: "/stabile/systems?action=packages", // + (ui_update.session?"&s="+ui_update.session:""),
                postData: dojo.toJson(data),
                load: function(response){
                    home.updatePackages();
                    server.parseResponse(response);
                },
                error: function(error){
                    er("grid::actionHandler", error);
                }
            });
        },

        showImageItemDialog: function(item) {
            if (images.grid.dialog) {
                images.grid.dialog.show(item);
            } else {
                console.log("Error - no image dialog");
            }
        },

        showImageDialog: function(path) {
            if (path == null && servers.grid.dialog) {
                path = servers.grid.dialog.item.image;
            } else if (path == null && images.grid.dialog) {
                path = images.grid.dialog.item.master;
            }
            // var url = "/stabile/images?action=list"; //images&image=listall";
            // if (stores.unusedImages2.url != url) {
            //     stores.unusedImages2.url = url;
            //     stores.unusedImages2.close();
            // }

            // We need to translate the image path from server info to an image uuid
            // unusedImages2 uses path as identifier
            $.get('/stabile/images/?path=' + encodeURIComponent(path) ,function(item) {home.showImageItemDialog(item)});

            // stores.unusedImages2.fetchItemByIdentity({identity: path, onItem: function(item0) {
            //     // images uses uuid as identifier
            //     stores.images.fetchItemByIdentity({identity: item0.uuid, onItem: function(item) {
            //         if (images.grid.dialog) {
            //             images.grid.dialog.show(item);
            //         } else {
            //             home.imagesOnShowItem = item;
            //             dijit.byId('tabs').selectChild(dijit.byId('images'));
            //         }
            //     }});
            // }});
        },

/*
        showDialog: function(uuid, type) {
            if (uuid == null) {
                var ids;
                if (type == "serverimage") {
                    ids = images.grid.dialog.item.domains;
                    type = "servers";
                } else if (type == "networkimage") {
                    ids = networks.grid.dialog.item.domains;
                    type = "servers";
                } else if (type == "image2server") {
                    ids = servers.grid.dialog.item.image2;
                    type = "images";
                } else if (type == "network1server") {
                    ids = servers.grid.dialog.item.networkuuid1;
                    type = "networks";
                } else if (type == "network2server") {
                    ids = servers.grid.dialog.item.networkuuid2;
                    type = "networks";
                } else if (type == "nodeserver") {
                    ids = servers.grid.dialog.item.mac;
                    type = "nodes";
                } else if (type == "nodeimage") {
                    ids = images.grid.dialog.item.mac;
                    type = "nodes";
                }
                if (ids.indexOf(", ")!=-1) ids = ids.substring(0,ids.indexOf(", "));
                uuid = ids;
            }

            require(['stabile/' + type, 'stabile/menu'], function(grid, menu){
                stores[type].fetchItemByIdentity({identity: uuid, onItem: function(item) {
                   var pane = menu[type + 'Pane'];
                   if(!pane.isLoaded){
                       // init the server grid and dialog
                       var tabs = menu.tabs;
                       var h = connect.connect(grid, 'init', function(evt) {
                           grid.grid.dialog.show(item);
                           dojo.disconnect(h);
                       });
                       tabs.selectChild(pane);
                    }
                    else{
                        grid.grid.dialog.show(item);
                    }
                }});
            });
        },
*/

        deviceHandler: function(item_id, action) {
            var dev = dijit.byId(item_id).get("value");
            var stortype = "backup";
            if (action.indexOf("format")==0) {
                if (action=="formatimagesdevice") stortype = "images";
                $("#info_" + stortype + "zfs_button").html('Formatting&hellip; <i class="fa fa-cog fa-spin"></i>').prop("disabled", true);
                var url = "/stabile/images?action=initializestorage&activate=1&type=" + stortype;
                console.log("configuring storage...", dev, action, stortype);
                url += "&device=" + dev;
                $.get(url, function(response) {
                    if (response.indexOf("Status=OK")==0) {
                        home.user[stortype + "device"] = dev;
                        if (stortype=="backup") {
                            home.toggleBackupButtons(dijit.byId("info_backupdevice_field"));
                            stores.backupDevices.close();
                            dijit.byId("info_backupdevice_field").setStore(stores.backupDevices);
                        } else {
                            home.toggleImagesButtons(dijit.byId("info_imagesdevice_field"));
                            stores.imagesDevices.close();
                            dijit.byId("info_imagesdevice_field").setStore(stores.imagesDevices);
                        }
                        home.user.load();
                    } else if (response.toLowerCase().indexOf("status=error")==0) {
                        IRIGO.toast(response.substring(12));
                        dijit.byId("info_backupdevice_field").setStore(stores.backupDevices);
                        dijit.byId("info_imagesdevice_field").setStore(stores.imagesDevices);
                    }
                    $("#info_" + stortype + "zfs_button").html('Format this device').prop("disabled", false)
                });
            } else {
                if (action=="setimagesdevice") stortype = "images";
                $("#info_" + stortype + "device_button").html('Configuring&hellip; <i class="fa fa-cog fa-spin"></i>').prop("disabled", true);
                var url = "/stabile/images?action=setstoragedevice&type=" + stortype;
                console.log("configuring storage...", dev, action, stortype);
                url += "&device=" + dev;
                $.get(url, function(response) {
                    if (response.indexOf("Status=OK")==0) {
                        home.user[stortype + "device"] = dev;
                        if (stortype=="backup") {
                            home.toggleBackupButtons(dijit.byId("info_backupdevice_field"));
                            stores.backupDevices.close();
                            dijit.byId("info_backupdevice_field").setStore(stores.backupDevices);
                        } else {
                            home.toggleImagesButtons(dijit.byId("info_imagesdevice_field"));
                            stores.imagesDevices.close();
                            dijit.byId("info_imagesdevice_field").setStore(stores.imagesDevices);
                        }
                        home.user.load();
                    } else if (response.toLowerCase().indexOf("status=error")==0) {
                        IRIGO.toast(response.substring(12));
                        dijit.byId("info_backupdevice_field").setStore(stores.backupDevices);
                        dijit.byId("info_imagesdevice_field").setStore(stores.imagesDevices);
                    }
                    $("#info_" + stortype + "device_button").html('Use this device').prop("disabled", false)
                });
            }
        },

        toggleImagesButtons: function(item) {
            var label = item._getSelectedOptionsAttr().label;
            $("#info_imagesdevice_button").toggle(home.user.imagesdevice!=item.get("value") && (label.indexOf("not mounted")==-1 || label.indexOf("zfs")!=-1));
            $("#info_imageszfs_button").toggle(home.user.imagesdevice!=item.get("value") && label.indexOf("not mounted")!=-1);
        },
        toggleBackupButtons: function(item) {
            var label = item._getSelectedOptionsAttr().label;
            $("#info_backupdevice_button").toggle(home.user.backupdevice!=item.get("value") && (label.indexOf("not mounted")==-1 || label.indexOf("zfs")!=-1));
            $("#info_backupzfs_button").toggle(home.user.backupdevice!=item.get("value") && label.indexOf("not mounted")!=-1);
        }

    };

    home.charts = {
    };

    home.createRegisterGrid = function(domId){
        var layout = [
            {
                field: 'name',
                name: 'Name',
                width: '100px'
            },
            {
                field: 'hostname',
                name: 'Hostname',
                width: '100px'
            },
            {
                field: 'os',
                name: 'OS',
                width: '200px'
            }
        ];

        // create a new grid:
        var grid = new dojox.grid.DataGrid({
            store : stores.register,
            structure : layout,
            selectionMode: "single",
            keepSelection: true,
         //   sortInfo: 1,
            autoHeight : true,
            rowsPerPage: 2000,
            clientSort: true
        });

        grid.name = 'register';

        grid.refresh = function(){
            var filter;
            if (home.currentItem) {
                if (home.currentItem.issystem) {
                    filter = {uuid: home.currentItem.uuid};
                } else {
                    filter = {uuid: home.currentItem.uuid};
                }
            } else {
                filter = {uuid: '*'};
            }
            //console.log("filtering", home.currentItem, filter);
            grid.filter(filter, true);
        };

        dojo.byId(domId).appendChild(grid.domNode);
        grid.startup();
        return grid;
    }


    home.createPackagesGrid = function(domId){
        var layout = [
            {
                field: 'app_display_name',
                name: 'Application',
                width: '150px'
            },
            {
                field: 'app_version',
                name: 'Version',
                width: '100px'
            },
            {
                field: 'app_publisher',
                name: 'Publisher',
                width: '150px'
            }
        ];

        // create a new grid:
        var grid = new dojox.grid.DataGrid({
            store : stores.packages,
            structure : layout,
            selectionMode: "single",
            keepSelection: true,
            sortInfo: 1,
            autoHeight : true,
            rowsPerPage: 2000,
            clientSort: true
        });

        grid.name = 'packages';

        grid.loadPackages = function(){
            if (home.currentItem) {
                var data = {
                    "items": [{uuid:home.currentItem.uuid, action:"load"}]
                };

                dojo.xhrPost({
                    url: "/stabile/systems?action=packages", // + (ui_update.session?"&s="+ui_update.session:""),
                    postData: dojo.toJson(data),
                    load: function(response){
                        grid.refresh();
                        server.parseResponse(response);
                    },
                    error: function(error){
                        er("grid::actionHandler", error);
                    }
                });
            }
        }

        grid.refresh = function(){
            var filter;
            if (home.currentItem) {
                filter = {uuid: home.currentItem.uuid};
            } else {
                filter = {uuid: '*'};
            }
            grid.filter(filter, true);
        };

        dojo.byId(domId).appendChild(grid.domNode);
        grid.startup();
        return grid;
    }

//** MONITORING GRID **//

    home.createMonitoringGrid = function(domId){
        var layout = [
            {
                field: 'opstatus',
                name: 'Opstatus',
                hidden: true
                //formatter: function(val, rowIdx, cell) {
                //    var item = home.monitoringGrid.getItem(rowIdx);
                //    return ((item.status=="disabled")?7:item.opstatus);
                //}
            },
            {
                field: 'id',
                name: 'ID',
                hidden: true
            },
            {
                field: 'servername',
                name: 'Server',
                width: '140px'
            },
            {
                field: 'service',
                name: 'Service',
                width: '80px'
            },
            {
                field: 'status',
                name: 'Status',
                width: '60px'
            },
            {
                field: 'last_check',
                name: 'Last check',
                formatter: timestampToTime,
                width: '80px'
            },
            {
                field: 'action',
                name: 'Action',
                width: '120px',
                formatter: function(val, rowIdx, cell) {
                    if (home.monitoringGrid) {
                        var item = home.monitoringGrid.getItem(rowIdx);
                        return home.monitoringGrid.getActionButtons(item);
                    }
                }
            }
        ];

        // create a new grid:
        var grid = new dojox.grid.DataGrid({
            store : stores.monitors,
            structure : layout,
            selectionMode: "single",
            keepSelection: false,
            sortInfo: 4,
            autoHeight : false,
            rowsPerPage: 2000,
            height: "210px",
            clientSort: true
        });

        grid.name = 'monitors';
        grid.currentServer = null;

        grid.dialogStructure = [
            { field: "servername", name: "Server", type: "dijit.form.TextBox", attrs : {readonly :"readonly"}},
            { field: "serveruuid", name: "Server uuid", type: "dijit.form.TextBox", attrs : {readonly :"readonly"}},
            {
                field:"service",
                name:"Service",
                type: "dijit.form.Select",
                attrs:{ store: "stores.monitorsServices", searchAttr:"service", onChange: "home.monitoringGrid.adaptDialog(this.value);"}
            },
            { field: "email", name: "Alert email", type: "dijit.form.TextBox", required: true, attrs : {readonly :"readonly"}},
            { field: "serverip", name: "IP address", type: "dijit.form.TextBox", attrs : {readonly :"readonly"}, style: "width: 120px;"},
            { field: "port", name: "Port", type: "dijit.form.TextBox", style: "width: 40px;"},
            { field: "request", name: "Request", type: "dijit.form.TextBox"},
            { field: "okstring", name: "Look for", type: "dijit.form.TextBox"},
            { field: "status", name: "Status", type: "dijit.form.TextBox" , attrs : {readonly :"readonly"}, style: "width: 40px;" },
            { field: "last_detail", name: "Last result", type: "dijit.form.SimpleTextarea" ,
                attrs : {readonly :"readonly"}, style: "height: 90px"
            },
            { field: "last_check", name: "Last check", type: "dijit.form.TextBox" , attrs : {readonly :"readonly"} },
            { field: "first_failure", name: "Down since", type: "dijit.form.TextBox" , attrs : {readonly :"readonly"} },
            { field: "desc", name: "Notes", type: "dijit.form.SimpleTextarea" ,
                style: "height: 40px",
                attrs : (user.is_readonly?{readonly :"readonly"}:{})
            },
            { field: "ack", name: "Acknowledged", type:  "dijit.form.TextBox", attrs : {readonly :"readonly"} },
            { field: "ackcomment", name: "Ack.comment", type:  "dijit.form.TextBox",
                attrs : (user.is_readonly?{readonly :"readonly"}:{})
            }
        ];

        grid.model = function(args){
            var email = home.currentItem.alertemail;
            if (!email || email == "" || email == "--") email = user.alertemail;
            if (!email || email == "" || email == "--") email = home.currentItem.opemail;
            if (!email || email == "" || email == "--") email = user.opemail;
            if (!email || email == "" || email == "--") email = home.currentItem.email;
            if (!email || email == "" || email == "--") email = user.email;
            var serverip = home.currentInternalip;
            if (!serverip  || serverip == '--') serverip = home.currentExternalip;
            if (serverip == '--') serverip = '';
            return dojo.mixin(
                    {
                        opstatus: "new",
                        status: "new",
                        id: home.currentItem.uuid + ":ping",
                        desc: "",
                        service: "ping",
                        email: email,
                        serverip: serverip,
                        serveruuid: home.currentItem.uuid,
                        servername: home.currentItem.name,
                        port:'',
                        request:'',
                        okstring: ''
                    //    last_check: Math.round((new Date())/1000)
                    }, args || {});
        }

        grid.actionButton = function(args){
            var actionHandler;
            args.title = args.title || args.action;
            if(args.confirm){
                actionHandler = "grid.actionConfirmDialog('" + args.id + "','" + args.action + "','" + args.name + "','" + args.title + "','" + args.type + "', 'home.monitoringGrid.actionHandler')";
            }
            else{
                actionHandler = "home.monitoringGrid.actionHandler('" + args.id + "','" + args.action + "','" + args.type + "')";
            }
            // left out button text intentionally since image replacement didn't work out in IE
            var t = '<button type="button" title="${title}" class="action_button ${action}_icon" id="${action}_${id}" onclick="${actionHandler};return false;"><span>${action}</span></button>';
            args.actionHandler = actionHandler;
            return dojo.string.substitute(t, args);
        }

        grid.saveButton = function(type){
            // returning false, to disable form submit
            var actionHandler = "home.monitoringGrid.saveHandler('" + type + "'); return false;";
            var t = '<button type="submit" title="Save" class="btn btn-sm btn-success pull-right" onclick="${actionHandler}">'
                    + '<span>save</span></button>';
            return dojo.string.substitute(t, {'actionHandler':actionHandler});
        }

        grid.saveHandler = function(type) {
            //grid.store.changing(grid.dialog.item);
            grid.dialog.save();
        }

        grid.actionHandler = function(id, action, type) {
            var item = grid.store.fetchItemByIdentity({
                identity: id,
                onItem: function(item, request){
                    if (action == 'delete') {
                        //grid.store.changing(item);
                        //grid.store.reset(item.id);
                        grid.store.deleteItem(item);
                        grid.store.save();
                        home.updateUptime();
                    } else {
                        var data;
                        var ackcomment = dojo.byId("ackcomment");
                        if (action == 'acknowledge' && ackcomment && ackcomment.value) {
                            data = {
                                "items": [{id:id, action: action, ackcomment: ackcomment.value}]
                            };
                        } else {
                            data = {
                                "items": [{id:id, action: action}]
                            };
                        }
                        // send action to server
                        dojo.xhrPost({
                        //    url: "/stabile/systems/monitors/?id=" + id, // + (ui_update.session?"&s="+ui_update.session:""),
                            url: "/stabile/systems/monitors/" + id,
                            postData: dojo.toJson(data),
                            load: function(response){
                                if (action=="disable" && response.indexOf("OK disable")!=-1) {
                                    item.status = "disabled";
                                    item.opstatus = "9";
                                    grid.sort();
                                } else if (action=="enable" && response.indexOf("OK enable")!=-1) {
                                    item.status = "checking";
                                    item.opstatus = "";
                                    grid.sort();
                                } else if (action=="acknowledge" && response.indexOf("OK acknowledge")!=-1) {
                                    grid.refresh();
                                }
                                server.parseResponse(response);
                            },
                            error: function(error){
                                er("grid::actionHandler", error);
                            }
                        });
                        dojo.publish(type + ":" + action, [item]);
                    }
                }
            });

            if(grid.dialog.isOpen()){grid.dialog.hide();}
        }

        grid.itemClickHandler = function(event){
            var item = home.monitoringGrid.selection.getSelected()[0];
            if(!item){ // e.g. click on header
                return;
            }
            if(event && event.cell && event.cell.field == 'action'){
                ;
            } else {
                home.monitoringGrid.dialog.show(item);
            }
        };

        grid.onBeforeSave = function(item) {
            if (item.status == "new") {
                item.id = item.serveruuid + ":" + item.service;
                item.status = 'checking';
            }
        }

        grid.adaptDialog = function(service) {
            document.getElementById("requestlabel").innerHTML = "Request";
            document.getElementById("okstringlabel").innerHTML = "Look for";
            if (service == "ping") {
                grid.hideRow("portlabel");
                grid.hideRow("requestlabel");
                grid.hideRow("okstringlabel");
                grid.showRow("serveriplabel");
            } else if (service == "imap" || service == "imaps" || service == "ldap") {
                grid.hideRow("portlabel");
                grid.showRow("requestlabel");
                grid.showRow("okstringlabel");
                grid.showRow("serveriplabel");
            } else if (service == "telnet") {
                grid.showRow("portlabel");
                grid.hideRow("requestlabel");
                grid.showRow("okstringlabel");
                grid.showRow("serveriplabel");
            } else if (service == "smtp" || service == "smtps") {
                document.getElementById("requestlabel").innerHTML = "From";
                document.getElementById("okstringlabel").innerHTML = "To";
                grid.showRow("portlabel");
                grid.showRow("okstringlabel");
                grid.showRow("requestlabel");
                grid.showRow("serveriplabel");
            } else if (service == "diskspace") {
                document.getElementById("requestlabel").innerHTML = "Min. free %";
                document.getElementById("okstringlabel").innerHTML = '<a href="https://www.origo.io/info/stabiledocs/web/dashboard/monitoring-tab/partitions/" rel="help" target="_blank" class="irigo-tooltip">help</a>' + "Partitions";
                grid.hideRow("portlabel");
                grid.hideRow("serveriplabel");
                grid.showRow("okstringlabel");
                grid.showRow("requestlabel");
            } else {
                grid.showRow("portlabel");
                grid.showRow("okstringlabel");
                grid.showRow("requestlabel");
                grid.showRow("serveriplabel");
            }
            if (home.currentItem && home.currentItem.networktype1 == 'gateway') {
                $("#serverip").prop("readonly", false);
            } else {
                $("#serverip").prop("readonly", true);
            }
            q = dojo.query('.irigo-tooltip'); q.irigoTooltip && q.irigoTooltip();
        }

        grid.onDialogButtons = function(item){
            // helpers
            var hide = function(dijitId){
                var elm = dijit.byId(dijitId);
                elm && elm.set('style', 'display:none');
                return elm;
            };
            var show = function(dijitId){
                var elm = dijit.byId(dijitId);
                elm && elm.set('style', 'display:inline');
                return elm;
            };
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
            var hideRow = grid.hideRow = function(domId){
                // tr <- td <- input
                dojo.query('#' + domId).parent().parent().style({display:"none"});
            };
            var showRow = grid.showRow = function(domId){
                dojo.query('#' + domId).parent().parent().style({display: "table-row"});
            };
            var last_check = dojo.byId("last_check");
            if (last_check) last_check.value = timestampToDatetime(item.last_check);
            if (item.opstatus==0) {
                var first_failure = dojo.byId("first_failure");
                if (first_failure) first_failure.value = timestampToDatetime(item.first_failure);
            } else {
                hideRow("first_failurelabel");
            }
            if (item.opstatus>0) {
                hideRow("ackcommentlabel");
                hideRow("acklabel");
            }
            var ack = dojo.byId("ack");
            if (ack) {
                if (ack.value>0) {
                    ack.value = timestampToDatetime(item.ack);
                    disable("ackcomment");
                } else {
                    hideRow("acklabel");
                }
            }

            if(item.status == "new"){
                hideRow("last_detail");
                hideRow("last_checklabel");
                hideRow("acklabel");
                hideRow("ackcommentlabel");
            } else {
                disable("service");
            }

            var service = dijit.byId('service');
            if (service) {
                // "service: 'http' OR service: 'ping'"
                service.setStore(stores.monitorsServices, service.value, {query:home.servicesFilter});
                //service.setStore(stores.monitorsServices, service.value, {query:home.servicesFilter});
            }
        }

        grid.refresh = function(){
            var filter;
        //    if (!home.currentItem) home.currentItem = home.grid.selection.getSelected()[0];
            if (home.currentItem && home.currentItem.issystem) {
                grid.store.clearCache();
                filter = {system: home.currentItem.uuid};
            } else if (home.currentItem) {
                filter = {serveruuid: home.currentItem.uuid};
            } else {
                filter = {id: '*'};
            }
//            console.log("filtering:", filter);
            grid.store.reset();
            grid.filter(filter, true);
            grid.updateMissingMonitors(filter);
        };

        grid.updateMissingMonitors = function(filter) {
            var tabid;
            if (dijit.byId('homeTabs')) tabid = dijit.byId('homeTabs').selectedChildWidget.id;

            if (tabid=="monitoringContentPane") {
                if (!filter) filter = {id: '*'};
                grid.store.fetch({query:filter, onComplete: function(result){
                    var pingmonitors=0;
                    var diskmonitors=0;
                    var pingmonitors_list="";
                    var diskmonitors_list="";
                    for (var i in result) {
                        if (result[i].status!="inactive" && result[i].status!="shutoff") {
                            if (result[i].service == "ping") {
                                pingmonitors++;
                            }
                            if (result[i].service == "diskspace") {
                                diskmonitors++;
                            }
                        }
                    }
                    var v = "";
                    var ns = home.activeServers;
                    if (ns-pingmonitors>0 || ns-diskmonitors>0) {
                        v = "<span style=\"color:red;\"><span style=\"font-weight:bold;\">Missing monitors: </span>";
                        if (ns-pingmonitors>0) v += "<span title=\"" + pingmonitors_list + "\">" + (ns-pingmonitors) + " ping</span>";
                        if (ns-diskmonitors>0) v += ((ns-pingmonitors>0)?", ":"") + "<span title=\"" + diskmonitors_list + "\">" + (ns-diskmonitors) + " diskspace</span>";
                        v += "</span>";
                    }
                    home.missingmonitors.innerHTML = v;
                }});
            }
        }

        grid.save = function(args) {
            if(grid.store.isDirty()){
                grid.store.save({
                    onComplete: function(res){
                        if (!grid.store.isDirty()) {
                            grid.refresh();
                        }
                        if(args.onComplete){
                            args.onComplete();
                        }
                    },
                    onError: function(e){
                        console.log("ERROR saving", e);
                        // Most likely error
                        IRIGO.toast("Please use a valid IP address");
                        grid.refresh();
                    }
                });
            }
            else{
                IRIGO.toaster([{
                    message: "Nothing new to commit!",
                    type: "message",
                    duration: 3000
                }]);
            }
        }

        grid.getActionButtons = function(item, include_save){
            if (user.is_readonly) return "";
            var id = item.id;
            var opstatus = item.opstatus;
            var status = item.status;
            var save = include_save ? grid.saveButton('monitor') : "";

            var delete_button = grid.actionButton({'action':"delete", 'id':id, 'confirm': false,
                'name': item.name + ' on ' + item.servername, actionHandler: home.monitoringGrid.actionHandler,
                    'title': 'delete', 'type': 'monitor'});

            var enable = grid.actionButton({'action':"enable", 'id':id, 'type': 'monitor'});
            var disable = grid.actionButton({'action':"disable", 'id':id, 'type': 'monitor'});
            var acknowledge = grid.actionButton({'action':"acknowledge", 'id':id, 'type': 'monitor'});

            var buttons = "";
            if (status != "new") {
                if (status == "disabled") buttons += enable;
                else buttons += disable;
                buttons += delete_button;
            }
            if (opstatus==0 && item.ack==0 && !item.checking) {
                buttons += acknowledge;
            }
            buttons += save;
            return buttons;
        }

        grid.dialog = griddialog(grid);

        grid.newItem = function() {
            var model = grid.model();
            grid.dialog.show(model);
        }

        grid.refreshRow = function(task, idprop) {
            if (!idprop) idprop = "id";
            grid.store.fetchItemByIdentity({identity: task[idprop],
                onItem: function(item){
                   for (var key in task) {
                       if (key=='id' || key=='sender' || key=='timestamp' || key=='type' || key=='uuid') {;}
                       else if (item[key]) {
                            item[key] = task[key];
                       }
                   }
                   grid.store.save();
                   grid.refresh();
// This does for some reason not work reliably - we update entire table instead.
/*
                   var i = grid.getItemIndex(item);
                   console.log("refreshing monitor " + i + " " + statusColorMap.get(item.status), task, item);
                   grid.updateRowStyles(i);
                   grid.updateRow(i);
                   dojo.setStyle(grid.getRowNode(i), "color", statusColorMap.get(item.status)); // ugly
                   grid.render();
*/
                }
            });
        };

        grid.onStyleRow = function(row){
            row.customStyles = "cursor:pointer;";
            var item = grid.getItem(row.index);
            if(item){
                var status = item.status;
                var color = statusColorMap.get(status);
                row.customStyles += "color:" + color + ";";
            }
        };
        dojo.byId(domId).appendChild(grid.domNode);
        grid.startup();

        return grid;
    }

//** SYSTEMS GRID **//

    home.createStatusGrid = function(domId){

        var layout = [
            //{
            //    type: "dojox.grid._CheckBoxSelector",
            //    width: '10%'
            //},
            {
                field: '_item',
                name: 'Name',
                width: (230+(user.is_readonly?80:0)) + 'px',
                formatter: serverFormatters.viewerName
            },
            /*{
                field: 'name',
                name: 'Name',
                width: 'auto',
                editable: true
            },*/
            {
                field: '_item',
                name: 'Status',
                width: '70px',
                formatter: function(val, rowIdx) {
                    if (val.issystem) {
                        var inistatus;
                        var status;
                        var degraded = false;
                        for (l in val.children) {
                            status = val.children[l].status;
                            if (status && !val.children[l].issystem) {
                                if (!inistatus) inistatus = status;
                                if (status != inistatus
                                        && !(status+inistatus=='shutoffinactive')
                                        && !(status+inistatus=='inactiveshutoff')) degraded = true;
                            }
                        }
                        if (degraded) status = 'degraded';
                        else status = inistatus;
                        if (val.issystem) val.status = status;
                        return status;
                    } else {
                        return(val.status);
                    }
                }
            },
            {
                field: '_item',
                hidden: user.is_readonly,
                name: 'Action' + ' <a href="https://www.origo.io/info/stabiledocs/web/dashboard/actions/" rel="help" target="_blank" class="irigo-tooltip">help</a>',
                width: 'auto',
                formatter: function(item) {
                    q = dojo.query('.irigo-tooltip'); q.irigoTooltip && q.irigoTooltip();
                    return grid.getActionButtons(item);
                }
            }
        ];

        var treeModel = new dijit.tree.ForestStoreModel({
            store: newStores.systems,
            deferItemLoadingUntilExpand: false,
            rootId: 'systems',
            rootLabel: 'root'
        //    query:{nodetype: "parent"},
        //    childrenAttrs: ['children']
        });
        newStores.systems.grid = home.grid;

        // create a new grid:
        //var grid = new dojox.grid.DataGrid({
        var grid = new dojox.grid.TreeGrid({
            treeModel: treeModel,
            structure : layout,
            selectionMode: "single",
            keepSelection: true,
            rowsPerPage: 2000,
            defaultOpen: false,
        //    sortInfo: 2,
            autoRender: true,
            autoHeight : false
        }, domId);
        grid.canSort = function(col){ if(Math.abs(col) == 3) {
            return false; } else { return false; } };

        grid.rendering = false,
        grid.hasSelection = false,

        grid.getActionButtons = function(item){
            var uuid = item.uuid;
            var issystem = item.issystem;
            var remove_button = grid.actionButton({'action':"delete_system", 'uuid':uuid, 'confirm': false,
                'name': item.name , actionHandler: grid.actionHandler,
                'title': 'remove system', 'type': 'stack'});
            var delete_button = grid.actionButton({'action':"removesystem", 'uuid':uuid, 'confirm': true,
                'name': item.name , actionHandler: grid.actionHandler,
                'title': 'completely delete stack and delete associated servers, images and connections', 'type': 'stack'});
            var start_button = grid.actionButton({'action':"start", 'uuid':uuid, 'confirm': false,
                'name': item.name , actionHandler: grid.actionHandler,
                'title' : "start/resume" + (item.issystem?" all":""), 'type': 'stack'});
            var shutdown_button = grid.actionButton({'action':"shutdown", 'uuid':uuid, 'confirm': false,
                'name': item.name , actionHandler: grid.actionHandler,
                'title' : "shutdown" + (item.issystem?" all":""), 'type': 'stack'});
            var suspend_button = grid.actionButton({'action':"suspend", 'uuid':uuid, 'confirm': false,
                'name': item.name , actionHandler: grid.actionHandler,
                'title' : "suspend" + (item.issystem?" all":""), 'type': 'stack'});
            var resume_button = grid.actionButton({'action':"resume", 'uuid':uuid, 'confirm': false,
                'name': item.name , actionHandler: grid.actionHandler,
                'title' : "resume" + (item.issystem?" all":""), 'type': 'stack'});
            var destroy_button = grid.actionButton({'action':"destroy", 'uuid':uuid, 'confirm': true,
                'name': item.name , actionHandler: grid.actionHandler,
                'title' : "pull the plug" + (item.issystem?" on all":""), 'type': 'stack'});
            var backup_button = grid.actionButton({'action':"backup", 'uuid':uuid, 'confirm': false,
                'name': item.name , actionHandler: grid.actionHandler,
                'title' : "backup" + (item.issystem?" all":""), 'type': 'stack'});


            var buttons = "";
            if (item.status=="running") {
                buttons += shutdown_button;
                buttons += suspend_button;
                buttons += destroy_button;
                buttons += backup_button;
            } else if (item.status=="shutoff") {
                buttons += start_button;
//                if (issystem != 1) buttons += delete_button;
                buttons += delete_button;
                buttons += backup_button;
            } else if (item.status=="paused") {
                buttons += resume_button;
                buttons += destroy_button;
                buttons += backup_button;
            } else if (item.status=="inactive") {
                buttons += start_button;
//                if (issystem != 1) buttons += delete_button;
                buttons += destroy_button;
                buttons += delete_button;
            } else if (item.status=="shuttingdown" || item.status=="upgrading") {
                buttons += destroy_button;
            } else if (!item.status || item.status=="--") {
            } else {
                buttons += start_button;
                buttons += shutdown_button;
                buttons += destroy_button;
                buttons += backup_button;
            }
            if (issystem == 1) {
                buttons += remove_button;
            }
            return buttons;
        },

        grid.actionButton = function(args){
            var actionHandler;
            args.title = args.title || args.action;
            if(args.confirm){
                actionHandler = "grid.actionConfirmDialog('" + args.uuid + "','" + args.action + "','" + args.name + "','" + args.title + "','" + args.type + "', 'home.grid.actionHandler')";
            }
            else{
                actionHandler = "home.grid.actionHandler('" + args.uuid + "','" + args.action + "','" + args.type + "')";
            }
            // left out button text intentionally since image replacement didn't work out in IE
            var t = '<button type="button" title="${title}" class="action_button ${action}_icon" uuid="${action}_${uuid}" onclick="${actionHandler};return false;"><span>${action}</span></button>';
            args.actionHandler = actionHandler;
            return dojo.string.substitute(t, args);
        },

        grid.actionHandler = function(uuid, action, type) {
            var item = grid.store.fetchItemByIdentity({
                identity: uuid,
                onItem: function(item, request){
                    if (action == 'delete_system') {
                        grid.deleteSystem(item);
                    } else {
                        var data;
                        data = {
                            "items": [{uuid:uuid, action:action, issystem: item.issystem}]
                        };
                        // send action to server
                        dojo.xhrPost({
                            url: "/stabile/systems/" + uuid, // + (ui_update.session?"?s="+ui_update.session:""),
                            postData: dojo.toJson(data),
                            load: function(response){
                                if (action == 'removesystem') {
                                    if (networks.grid && networks.grid.refresh) networks.grid.refresh();
                                    if (images.grid && images.grid.refresh) images.grid.refresh();
                                    if (servers.grid && servers.grid.refresh) servers.grid.refresh();
                                //    grid.deleteSystem(item);
                                    home.monitoringGrid.store.reset();
                                    home.updateMonitoring();
                                    home.updateUsage();
                                }
                                home.grid.updatePending = servers.grid.updatePending = images.grid.updatePending = networks.grid.updatePending = true;

                                server.parseResponse(response);
                            },
                            error: function(error){
                                console.error("grid::actionHandler", error);
                            }
                        });
                        dojo.publish(type + ":" + action, [item]);
                    }
                }
            });
        },

        grid.deleteSystem = function(item) {
            grid.selection.deselect(item);
            var haschildren = (item.children)?true:false;
            if (item == home.currentItem) home.currentItem = null;
            grid.store.deleteItem(item);
            grid.store.save({
                onComplete: function() {
                    home.updateUptime();
                    home.updateVitals("update");
                    home.updateUsage();
                    stores.systemsSelect.close();
                    if (haschildren) grid.refresh();
                },
                onError: function(err) { console.debug("error: ", err) }
            });
        },

        grid.addSystem = function() {
            var model = {
                uuid: Math.uuid().toLowerCase(),
                systemstatus: "new",
                issystem: 1,
                name: "New Stack"
            };
            var item = grid.store.newItem(model);
            grid.store.save({
                onComplete: function() { grid.selection.select(item); stores.systemsSelect.close();},
                onError: function(err) { console.debug("error: ", err) }

            });
        };

        grid.updateSystem = function(prop) {
            if (!home.currentItem) home.currentItem = home.grid.selection.getSelected()[0];
            if (prop && dijit.byId("info_"+prop+"_field")) {
                if (home.currentItem && (home.currentItem[prop] || home.currentItem[prop]=='')) {
                    var curpropvalue = home.currentItem[prop];
                    var curfieldvalue = dijit.byId("info_"+prop+"_field").value;
                    if (curpropvalue == "--") curpropvalue = "";
                    if (!(curfieldvalue=="" && prop=="name") &&  curpropvalue != curfieldvalue) {
                        console.log("saving item value",prop,curpropvalue,curfieldvalue,home.currentItem);
                        grid.store.changing(home.currentItem);
                        if (!curfieldvalue) curfieldvalue = "--";
                        home.currentItem[prop] = curfieldvalue;
                        grid.store.save({
                            onComplete: function() {
                                if (prop=="system") {
                                    grid.refresh();
                                    grid.selection.clear();
                                } else if (!dijit.byId("info_"+prop+"_field").value) {
                                    home.currentItem = home.grid.selection.getSelected()[0];
                                    var field = dijit.byId("info_"+prop+"_field");
                                    if (home.currentItem[prop] == '--' || home.currentItem.issystem) {
                                        home.currentItem[prop] = user[prop];
                                    }
                                    field.set('value', home.currentItem[prop]);
                                } else if (prop=="name") {
                                    stores.systemsSelect.close();
                                    grid.refresh();
                                    servers.grid.updatePending = true;
                                    networks.grid.updatePending = true;
                                } else {
                                }
                            },
                                onError: function(err) { console.debug("error: ", err) }
                        });
                    }
                } else if (user[prop] || user[prop]==="") {
                    var value = dijit.byId("info_"+prop+"_field").value;
                    if (prop.indexOf("vmreadlimit")==0 || prop.indexOf("vmwritelimit")==0) value = value*1024*1024;
                    if (dijit.byId("info_"+prop+"_field").checked===false) value = "--";
                    if (dijit.byId("info_"+prop+"_field").checked===true) value = "1";
                    if (value != user[prop]) {
                        if (!value) value = '--';
                        console.log("Saving server value", prop, user[prop], value, dijit.byId("info_"+prop+"_field").checked);
                        home.saveServerValue(user.username, prop, value, "username");
                        user[prop] = value;
                    }
                } else {
                    console.log("Not saving", prop);
                }
            } else {
                console.log("Not Saving", prop);
            }
        };

        grid.refresh = function(){
            treeModel.store.reset();
//            treeModel.store.close();
//            treeModel.store.fetch({query:{name:"*"},queryOptions:{cache:false}});
//            var filter = {uuid: "*"};
//            treeModel.store.fetch(filter);
            treeModel.store.fetch({
                    onItem: function(item) {
                        home.currentItem = home.grid.selection.getSelected()[0];
                        home.updateVitals(home.currentItem);
                        servers.grid.refresh();
                        stores.systemsSelect.close();
                    }
            })
            //grid.filter(filter, true);
            //treeModel.store = newStores.reloadSystems();
            //grid.treeModel = treeModel;
//            grid.render();
        };

        grid.redraw = function(){
            if (!home.currentItem) home.currentItem = home.grid.selection.getSelected()[0];
            if (home.currentItem) {
                grid.rendering = true;
                grid.selection.deselect(home.currentItem);
                grid.render();
                grid.selection.select(home.currentItem);
                grid.rendering = false;
            }
        };

        self.update = function(task){
            console.log("updating systems " + task.uuid + " " + task.tab);
            if (task.uuid && (task.tab=="servers" || task.tab=="systems")) {
                grid.store.fetchItemByIdentity({identity: task.uuid,
                    onItem: function(item){
                        for (var key in task) {
                            if (key=='id' || key=='sender' || key=='timestamp' || key=='type' || key=='uuid') {;}
                            else if (item[key]) {
                                 item[key] = task[key];
                            }
                        }
                        grid.store.save();
                        var i = grid.getItemIndex(item);
                        grid.updateRow(i);
                        grid.updateRowStyles(i);
                        console.log("updating row",i, item.uuid, item.system);
                    }
                });
            }
            home.updateVitals("update");

        };

        grid.updatePending = false;

        //if (dojo.byId(domId)) dojo.byId(domId).appendChild(grid.domNode);
        grid.startup();

        return grid;
    };// end createStatusGrid

    home.changeAccount = function(account) {
        if (account && account != user.username) {
            var msg = "";
            ui_update.logged_out = true;
            if (account.indexOf("<span")==0) {
                msg = "Logging out";
                setTimeout(
                    function() {document.location = "/stabile/auth/logout?s=" + ui_update.session},
                    700
                )
            } else {
                msg = "Switching to account: " + account
                var back = '';
                if (location.href.indexOf("index-i.html")!=-1) {
                    back = "&back=/stabile/index-i.html";
                }
                setTimeout(
                    function() {document.location = "/stabile/auth/autologin?account="+account+"&username="+user.username+back+"&s=" + ui_update.session},
                    700
                )
            }
            console.log(msg);
            IRIGO.toaster([{message: msg, type: "message",duration: 2000}]);

        }
    }

    home.logout = function() {
        console.log("logging out of engine");
        $.get("/stabile/auth/logout?s=" + ui_update.session);
    }

    home.changeEngine = function(url) {
        if (home.engines_field.getOptions().length>1) {
            $("#engines_span").show();
            if (url && url != "#" && document.location.href.indexOf(url)==-1) {
                setTimeout(function() {document.location = url},700)
                var msg = "Switching to engine " + url;
                console.log(msg, url);
                IRIGO.toaster([{message: msg, type: "message",duration: 2000}]);
            }
        }
    }

    home.init = function() {
        if (home._inited === true) return;
        else home._inited = true;

        if ($('#tktuser')) $('#tktuser').prop('innerHTML', user.tktuser);
        if ($('#tktuser')) $('#tktuser').prop('title', "User privileges: " + user.userprivileges);

        var grid = home.createStatusGrid("systemsGrid");
        home.grid = grid;
        home.grid.sort();
        home.monitoringGrid = home.createMonitoringGrid("monitoringGrid");
        home.monitoringGrid.sort();

        if (dojo.cookie('installaccount')) {
            home.install_account = dojo.cookie('installaccount');
        }
        if (dojo.cookie('installsystem')) {
            home.install_system = dojo.cookie('installsystem');
            systembuilder.system.create();
        }

        var month=new Array();
        month[0]="Jan";
        month[1]="Feb";
        month[2]="Mar";
        month[3]="Apr";
        month[4]="May";
        month[5]="Jun";
        month[6]="Jul";
        month[7]="Aug";
        month[8]="Sep";
        month[9]="Oct";
        month[10]="Nov";
        month[11]="Dec";
        var d = new Date();
        var m = d.getMonth();
        var y = d.getYear() + 1900;
        var m1;
        var y1;
        var ym;
        var um = {yearmonth: "current", name: "Current usage"};
        stores.usageMonths.newItem(um);
        for (i=0; i<12; i++) {
            y1 = (m-i<0)?y-1:y;
            m1 = (m-i<0)?12+m-i:m-i;
            ym = {yearmonth: y1+"-"+("0"+(m1+1)).substr(-2), name: month[m1]+" "+y1};
            um = {yearmonth: y1+"-"+("0"+(m1+1)).substr(-2), name: "Average usage for: " + month[m1]+" "+y1};
            stores.uptimeMonths.newItem(ym);
            stores.usageMonths.newItem(um);
        }

        var q = dojo.query('.irigo-tooltip');
        if(q.irigoTooltip){q.irigoTooltip();};

        home.grid.store.fetch({query:{uuid: "*"}, onComplete: home.updateVitals});

        dojo.connect(grid,"onStyleRow",function(row){
        //on(grid, "styleRow", function(row){
            row.customStyles = "cursor:pointer;";
            var item = grid.getItem(row.index);
            if(item){
                var status = grid.store.getValue(item,"status");
                var color = statusColorMap.get(status);
//                if (row.customStyles.indexOf(color)==-1) {
//                    row.customStyles = "color:" + color + ";";
//                }
                if (row.over) {
                    if (row.customClasses.indexOf("dojoxGridRowOver"))
                        row.customClasses = row.customClasses.substring(0, row.customClasses.indexOf("dojoxGridRowOver"));
                }
                row.customClasses += " " + color;
                //if (row.selected) {
                //    row.customStyles += "font-weight:bold;";
                //}
            };
        });

        home.account_field = new dijit.form.Select(
        {
            name: 'account',
            sortByLabel: false,
            onChange: home.changeAccount
        }, 'account');
        home.account_field.setStore(stores.accounts);

        home.engines_field = new dijit.form.Select(
            {
                name: 'engines',
                sortByLabel: false,
                onChange: home.changeEngine
            }, 'engines');
        home.engines_field.setStore(stores.engines);

        if (home.account_field) home.account_field.set('title',
"Active account: " + user.username + "\n\
Account privileges: " + user.privileges + "\n\
Logged in as: " + user.tktuser + ((user.userprivileges)?"\n\Privileges: " + user.userprivileges:"")
        );

        if (home.engines_field) {
            home.engines_field.set('title',
                "Active engine: " + user.enginename + "\n\
Engine linked to Stabile Registry: " + ((user.enginelinked)?"yes":"no") + ((user.engineid)?"\nEngine ID: " + user.engineid:"")
            );
        }
        if (user.enginename) document.title = user.enginename;

        if (user.is_readonly) {
            document.getElementById("clear_packages").style.display = "none";
            document.getElementById("add_system").style.display = "none";
            $("#manage_system_button").attr("disabled", true);
            $("#updateSystemButton").attr("disabled", true);
            $("#new_monitor_button").attr("disabled", true);
            $("#clear_packages").attr("disabled", true);
            $("#info_resettoaccountinfo_button").removeAttr("onclick");
        }
        if (user.is_admin && window.innerWidth>840) {
            $("#nodestab").show();
            $("#userstab").show();
            $("#clear_activity_button").show();
        } else {
            $("#nodestab").hide();
            $("#userstab").hide();
        }

        home.grid._onRowClicked = home.grid.onRowClick;
        home.grid.onRowClick = function(ev) {
            if (ev.target.localName == "button") {
                ; // do nothing
            } else {
                home.grid._onRowClicked(ev);
            }
        }
        on(grid, "click", function(ev){
            if (ev.target.localName != "td" && ev.target.localName != "button") {
                home.currentItem = null;
                if (grid.hasSelection && grid.selection.getSelected()) {
                    grid.hasSelection = false;
                    home.updateMonitoring();
                    home.updatePackages();
                    home.updateUptime();
                    home.updateUsage();
                }
                for (var i in grid.selection.getSelected()) {
                    var selItem = grid.selection.getSelected()[i];
                    grid.selection.deselect(selItem);
                }
            }
        });
        on(grid, "selected", function(rowIndex){
            var item = grid.getItem(rowIndex);
            if (item!=null && !grid.rendering) {
                grid.hasSelection = true;
                console.log("selected", item);
                home.currentItem = item;
                for (var i in grid.selection.getSelected()) {
                    var selItem = grid.selection.getSelected()[i];
                    if (selItem != item) {
                        grid.selection.deselect(selItem);
                        console.log("deselecting", selItem);
                    }
                }
                if (!user.is_readonly) $("#load_packages").show();
                dijit.byId("usage_select").set("value", "current");
                dijit.byId("usage_select").set("disabled", true);
                home.updateMonitoring();
                home.updatePackages();
                home.updateUptime();
                home.updateUsage();
                home.updateVitals(home.currentItem);
            }
        });
        on(grid, "deselected", function(rowIndex){
            var item = grid.getItem(rowIndex);
            if (grid.selection.getSelected().length==0 && !grid.rendering
                    && !grid.hasSelection
                    ) {
                console.log("deselected", item);
                home.currentItem = null;
                home.updateVitals("update");
                $("#load_packages").hide()
                dijit.byId("usage_select").set("disabled", false);
                home.updateMonitoring();
                home.updatePackages();
                home.updateUptime();
                home.updateUsage();
            }
        });

        connect.connect(home.monitoringGrid, "onRowClick", home.monitoringGrid, home.monitoringGrid.itemClickHandler);

        dojo.subscribe("systems:update", function(task){
            console.log("systems update", task);
            if (task.uuid) {
                home.grid.update(task);
            } else {
                home.grid.refresh();
            }
        });
        dojo.subscribe("monitors:update", function(task){
//            console.log("monitors update", task);
            if (task.uuid) {
                home.monitoringGrid.refreshRow(task);
            } else {
                home.updateMonitoring();
            }
        });
        dojo.subscribe("users:update", function(task){
            console.log("users update", task);
            home.updateUser();
        });
        dojo.subscribe("home:removal", function(task){
            console.log("system removed", task.uuid, dijit.byId('createSystemDialog').get("sysuuid"));
            var duuid = dijit.byId('createSystemDialog').get("sysuuid");
            if(dijit.byId('createSystemDialog') !== undefined && (duuid == task.uuid || duuid == task.domuuid))
                dijit.byId('createSystemDialog').hide();
        });

        if (user.showcost && user.showcost!="0") {
            document.getElementById("total_cost").style.display="inline";
         //   document.getElementById("cost_warning").style.display="block";
        }

        dojo.connect(grid, "onSelected", function(rowIndex){
            home.initApexCharts();
            home.updateApexCharts();
        });
        dojo.connect(grid, "onDeselected", function(rowIndex){
            home.initApexCharts();
        });

        dojo.subscribe("homeTabs-selectChild", function(child){

            if (child.id === "usageContentPane"){
                home.updateUsage();

            } else if (child.id === "monitoringContentPane"){
                home.updateMonitoring();

            } else if (child.id === "packagesContentPane"){
                home.updatePackages();

            } else if(child.id === "statisticsContentPane"){
                home.initApexCharts();
                if (home.currentItem) home.updateApexCharts();
            }
        });

        $('#statisticsTab').on('shown.bs.tab', function (e) {
            home.chartsShown=true;
            home.initApexCharts();
            if (home.currentItem) home.updateApexCharts();
        })
        home.bodyResize();
    };

    window.home = home;
    if (location.hash.substring(1) == 'chpwd') {
        location = "#home";
        home.showChangePassword();
    } else if (location.hash.indexOf('installsystem')!=-1) {
        home.install_system = location.hash.substr(location.hash.indexOf('installsystem') + 14);
        if (home.install_system.indexOf("-name=")!=-1) {
            home.install_name = home.install_system.substr(home.install_system.indexOf("-name=")+6);
            home.install_system = home.install_system.substring(0, home.install_system.indexOf("-name="));
        }
        systembuilder.system.create();
    }

    function bodyResize() {
        console.log("body resized");
        setTimeout(function() {q = dojo.query('.irigo-tooltip'); q.irigoTooltip && q.irigoTooltip();},1000);
        document.getElementById("homeTabs").style.height =
            (document.getElementById("homeContent").offsetHeight - document.getElementById("homeNav").offsetHeight) + "px";
    }
    home.bodyResize = bodyResize;

    home.initSlider = function() {
        if((!home.sliderCreated || !home.currentItem) && home.chartsShown) {
            if (!home.chartSlider) {
                home.chartSlider = new dijit.form.HorizontalSlider({
                    name: "slider",
                    value: 0,
                    minimum: 0,
                    maximum: 11,
                    discreteValues: 12,
                    showButtons: false,
                    intermediateChanges: true,
                    style: {width: "84%", marginLeft: "32px", marginBottom: 0, marginTop: 0, display: "none"},
                    onChange: function(value) {
                    //    home.updateCharts();
                        home.updateApexCharts();
                    }
                }, "slider");
                var labels    = ['5min', '30', '60',   '2h',   '12',   '24',    '2d',    '14',    '28',      '2m',      '6',       '12'];
                var sliderLabels = new dijit.form.HorizontalRuleLabels({
                    container:"bottomDecoration",
                    labels: labels
                }, "rules" );
            }

            document.getElementById("statsInfo").style.display = "block";
            document.getElementById("slider").style.display = "none";
            $("#chartsPanel").hide();
            home.sliderCreated = true;
        }
    }

    function getStatsQuery(){
        var secs = [ 300,  1800,  3600, 2*3600, 12*3600, 24*3600, 2*86400, 14*86400, 28*86400, 2*2592000, 6*2592000, 12*2592000 ];
        var value = home.chartSlider.get('value');
        var until = Math.round((new Date()).getTime() / 1000);
        return {
            from: new Date(new Date().getTime() - 1000 * secs[value]),
            to: new Date(),
            last_s: secs[value],
            until_s: until,
            from_s: until - secs[value]
        };
    }
    home.getStatsQuery = getStatsQuery;

    function timestampToDatetime(timestamp){
        if (timestamp == null || timestamp == ""|| timestamp == "--") return "--";
        d = new Date(timestamp*1000);
        return d.toLocaleDateString() + " " + d.toLocaleTimeString();
        //return d.getMonth() + "/" + d.getDate() + "/" + (d.getYear()+1900) + " " + d.toLocaleTimeString();
    };

    function timestampToTime(timestamp){
        if (timestamp == null || timestamp == ""|| timestamp == "--") return "--";
        d = new Date(timestamp*1000);
        return d.toLocaleTimeString();
    };

    home.timestampToLocaleString = function(timestamp) {
        if (timestamp == null || timestamp == ""|| timestamp == "--") return "--";
        d = new Date(timestamp*1000);

        function pad(n){return n<10 ? '0'+n : n}
        return d.getFullYear()+'-'
        + pad(d.getMonth()+1)+'-'
        + pad(d.getDate())+'  '
        + pad(d.getHours())+':'
        + pad(d.getMinutes())+':'
        + pad(d.getSeconds())+' '

//        return d.toLocaleString();
    };

    home.formatters = formatters;

    home.initApexCharts = function() {
        home.initSlider(); // old init function
        if (home.apexsliderCreated) return;
        var options = {
          chart: {
              height: 200,
              type: 'area',
              nogroup: 'metrics',
              animations: {
                enabled: false,
                easing: 'linear',
                dynamicAnimation: {
                  speed: 1000
                }
              },
              toolbar: {
                  show: true,
                  tools: {
                    download: true,
                    selection: true,
                    zoom: true,
                    zoomin: true,
                    zoomout: false,
                    pan: true
                  },
                  autoSelected: 'zoom'
              }
          },
          markers: {
            size: 3
          },
          colors: ['#008FFB'],
          stroke: {
              curve: 'smooth',
              lineCap: 'butt',
              width: 2
          },
          dataLabels: {enabled: false},
          series: [],
          noData: {text: 'Loading...'},
          xaxis: {
              type: 'datetime',
              labels: {
              formatter: function (value, timestamp) {
                if (timestamp > 100000) {
                  var d = new Date(timestamp * 1000);
                  var h = ("0" + d.getHours()).substr(-2);
                  var m = ("0" + d.getMinutes()).substr(-2);
                  var s = ("0" + d.getSeconds()).substr(-2);
                  var dstring = d.getDate() + "/" + (1+d.getMonth()) + " " + h + ":" + m + ":" + s;
                  return dstring;
                }
              }
            }
          },
          yaxis: {
              labels: {
                minWidth: "100px"
              },
              forceNiceScale: true,
              decimalsInFloat: 2
          }
        }

        home.cpu_options = $.extend(true, {}, options); // Deep clone object
        home.cpu_options.title = {text: 'CPU Load'};
        home.cpu_options.chart.id = 'cpu';
        home.cpu_options.colors = ['#008FFB'];
        home.chart_cpu = new ApexCharts(document.querySelector("#chartCpuLoad"), home.cpu_options);

        home.disk_options = $.extend(true, {}, options); // Deep clone object
        home.disk_options.title = {text: 'Disk I/O (kbytes/s)'};
        home.disk_options.chart.id = 'disk';
        home.disk_options.colors = ['#2980b9', '#e74c3c'];
        home.chart_disk = new ApexCharts(document.querySelector("#chartIO"), home.disk_options);

        home.net_options = $.extend(true, {}, options); // Deep clone object
        home.net_options.title = {text: 'Network traffic (kbytes/s)'};
        home.net_options.chart.id = 'network';
        home.net_options.colors = ['#f39c12', '#9b59b6'];
        home.chart_net = new ApexCharts(document.querySelector("#chartNetworkActivity"), home.net_options);

        home.chart_cpu.render();
        home.chart_disk.render();
        home.chart_net.render();

        home.apexsliderCreated = true;
    }

    home.updateApexCharts = function(uuid) {
      if (!uuid && home.currentItem) uuid = home.currentItem.uuid;
      if (!uuid) {console.log("Unable to chart - no uuid"); return;}
      var until = Math.round((new Date()).getTime() / 1000);
      var from = until - 60*5;
      var last = 60*5;
      var args;
      if (home.chartSlider) args = getStatsQuery();
      if (args) {
        from = args.from_s;
        until = args.until_s;
        last = args.last_s;
      }
//      var url = "/graphite/graphite.wsgi/render?format=json&from=" + from + "&until=" + until + "&target=domains." + uuid + ".cpuLoad";
      var url = "/stabile/systems?action=getmetrics&last=" + last + "&uuid=" + uuid + "&metric=cpuLoad";
      $.getJSON(url, function(response) {
        if (response.length > 0) {
            var rawdata = response[0].datapoints;
            home.chart_cpu.updateSeries([{
              name: 'CPU load',
              data: prepApexData(rawdata)
            }]);
            if (rawdata.length<2) home.chart_cpu.updateOptions({xaxis:{ max: 1 }});
            else if (rawdata[rawdata.length-2][0] == null) home.chart_cpu.updateOptions({xaxis:{ max: rawdata[rawdata.length-2][1] }}); // update x-axis to compensate for possible missing last data point
            home.chart_cpu.resetSeries(); // reset zoom - for some reason it gets bungled for this chart
        } else {
            home.chart_cpu.updateOptions({noData:{text:"No data"}, series:[]})
        }
      });

//      url = "/graphite/graphite.wsgi/render?format=json&from=" + from + "&until=" + until + "&target=domains." + uuid + ".wr_kbytes_s";
      url = "/stabile/systems?action=getmetrics&last=" + last + "&uuid=" + uuid + "&metric=wr_kbytes_s";
      $.getJSON(url, function(response) {
        if (response.length > 0) {
            var rawdata_1 = response[0].datapoints;
        //    url = "/graphite/graphite.wsgi/render?format=json&from=" + from + "&until=" + until + "&target=domains." + uuid + ".rd_kbytes_s";
            url = "/stabile/systems?action=getmetrics&last=" + last + "&uuid=" + uuid + "&metric=rd_kbytes_s";
            $.getJSON(url, function(response) {
              var rawdata_2 = response[0].datapoints;
              home.chart_disk.updateSeries([
                {
                  name: 'Disk writes',
                  data: prepApexData(rawdata_1)
                },
                {
                  name: 'Disk reads',
                  data: prepApexData(rawdata_2)
                }
              ])
            });
        } else {
            home.chart_disk.updateOptions({noData:{text:"No data"}, series:[]})
        }
      });

//      url = "/graphite/graphite.wsgi/render?format=json&from=" + from + "&until=" + until + "&target=domains." + uuid + ".rx_kbytes_s";
      url = "/stabile/systems?action=getmetrics&last=" + last + "&uuid=" + uuid + "&metric=rx_kbytes_s";
      $.getJSON(url, function(response) {
        if (response.length > 0) {
            var rawdata_1 = response[0].datapoints;
        //    url = "/graphite/graphite.wsgi/render?format=json&from=" + from + "&until=" + until + "&target=domains." + uuid + ".tx_kbytes_s";
            url = "/stabile/systems?action=getmetrics&last=" + last + "&uuid=" + uuid + "&metric=tx_kbytes_s";
            $.getJSON(url, function(response) {
              var rawdata_2 = response[0].datapoints;
              home.chart_net.updateSeries([
                {
                  name: 'Traffic in',
                  data: prepApexData(rawdata_1)
                },
                {
                  name: 'Traffic out',
                  data: prepApexData(rawdata_2)
                }
              ])
            });
        } else {
            home.chart_net.updateOptions({noData:{text:"No data"}, series:[]})
        }
      });
        document.getElementById("statsInfo").style.display = "none";
        document.getElementById("slider").style.display = "block";
        $("#chartsPanel").show();

    }

    function prepApexData(rdata) {
      var data = [];
      rdata.forEach(
        function(item, index) {
          data.push({"x": item[1], "y": item[0]})
        }
      )
//      return {series: [{name: "name", data: data}]};
      return data;
    };

});
