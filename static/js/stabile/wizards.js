define([
"steam2/user",
"steam2/models/Server",
// "stabile/menu",
"stabile/upload",
"stabile/images",
"stabile/servers",
"stabile/networks",
"steam2/stores",
"dijit/form/ComboBox"
], function(user, Server, /* menu,*/ upload, images, servers, networks, newStores){
var wizards = {};
var dialog;

wizards.server = {
    installtype: "cdrom",
    managementlink: null,
    create: function(){
        if(dijit.byId('createServerDialog') !== undefined){
            // destroy the existing and its children
            dijit.byId('createServerDialog').destroyRecursive();
        }

        dialog = new dijit.Dialog({ title: "Build new stack", id: 'createServerDialog'});
        var wizard = new dojox.widget.Wizard({style: "width: 700px; height: 600px;"});
        wizards.server.done.done = false;

        function step_one(){
            return [
              '<form method="" action="" class="">',
              '  <p class="wizardInfoPane">',
              '    <a href="//docs.irigo.com/topics/byhsd2" rel="help" target="_blank" class="irigo-text">help</a>',
              '  </p>',
              '  <p>',
              '    <label for="server_name" style="width:200px;">Choose a name for your new server:</label>',
              '    <div id="server_name"></div>',
              '  </p>',
              '  <p>',
              '    <label for="master_select" style="width:200px;">Clone a preinstalled system:</label>',
              '      <div id="master_select"></div>',
              '  </p>',
              '  <p>',
              '    <label for="cdrom_select" style="width:200px;">Or install a new operating system:</label>',
              '    <div id="cdrom_select"></div>',
              '  </p>',
              '  <p>',
              '    <label for="image_select" style="width:200px;">Or use your own image:</label>',
              '    <div id="image_select"></div>',
              '  </p>',
              '  <p>',
              '    You may <a href="#images" onclick="wizards.server.select_images_tab();">upload</a> your own CD-rom, upload a preinstalled system (master' +
                        ' image) or upload your own image on the storage tab.',
              '  </p>',
              '  <p class="wizardInfoPane" id="server_notes" style="display:none;">',
              '  </p>',
              '</form>'].join('');
        }

        function set_default_name(servername) {
            dijit.byId("server_name").setValue(servername);
        }
        function set_default_cdrom(item) {
          dijit.byId("master_select").setValue(item.path);
        }

        function init_step_one(){
            var server_name = new dijit.form.ValidationTextBox(
            {
                name: 'server_name',
                type: 'text',
                required: true,
                style: "width:180px"
            }, 'server_name');
            var cdrom_select = new dijit.form.FilteringSelect(
            {
                name: 'cdrom_select',
                type: 'text',
                required: false,
                store: stores.cdroms,
             //   value: '/mnt/stabile/images/common/ubuntu-9.10-server-amd64.iso',
                query: {installable: 'true'},
                searchAttr: 'name',
                onChange: update_cdrom_notes,
                style: "width:250px"
            }, 'cdrom_select');
            var master_select = new dijit.form.FilteringSelect(
            {
                name: 'master_select',
                type: 'text',
                required: false,
                store: stores.masterimages,
                query: {installable: 'true'},
                searchAttr: 'name',
                onChange: update_master_notes,
                style: "width:250px"
            }, 'master_select');
            var image_select = new dijit.form.FilteringSelect(
            {
                name: 'image_select',
                type: 'text',
                required: false,
                store: stores.unusedImages,
                searchAttr: 'name',
                onChange: update_image_notes,
                style: "width:250px"
            }, 'image_select');
        }

        function update_cdrom_notes(path) {
            stores.cdroms.close();
            stores.cdroms.fetchItemByIdentity({identity: path,
                onItem: function(item, request){
                    var server_notes = document.getElementById("server_notes");
                    if (item) {
                        if (item.notes && item.notes!="") {
                            server_notes.innerHTML = item.notes;
                            server_notes.style.display = "block";
                        } else {
                            server_notes.innerHTML = "";
                            server_notes.style.display = "none";
                        }
                        dijit.byId('master_select').setValue('');
                        dijit.byId('image_select').setValue('');
                    }
                }
            });
        }
        function update_master_notes(path) {
            stores.masterimages.close();
            stores.masterimages.fetchItemByIdentity({identity: path,
                onItem: function(item, request){
                    var server_notes = document.getElementById("server_notes");
                    if (item) {
                        if (item.notes && item.notes!="") {
                            server_notes.innerHTML = item.notes;
                            server_notes.style.display = "block";
                        } else {
                            server_notes.innerHTML = "";
                            server_notes.style.display = "none";
                        }
                        dijit.byId('cdrom_select').setValue('');
                        dijit.byId('image_select').setValue('');
                    }
                }
            });
        }

        function update_image_notes(path) {
            stores.unusedImages.close();
            stores.unusedImages.fetchItemByIdentity({identity: path,
                onItem: function(item, request){
                    var server_notes = document.getElementById("server_notes");
                    if (item) {
                        if (item.notes && item.notes!="") {
                            server_notes.innerHTML = item.notes;
                            server_notes.style.display = "block";
                        } else {
                            server_notes.innerHTML = "";
                            server_notes.style.display = "none";
                        }
                        dijit.byId('cdrom_select').setValue('');
                        dijit.byId('master_select').setValue('');
                    }
                }
            });
        }
        function step_two(){
            return [
                '<form method="" action="" class="createServerForm">',
                '<p class="wizardInfoPane">',
              '<a href="//docs.irigo.com/topics/6dy" rel="help" target="_blank" class="irigo-text">help</a>',
                '</p>',
                '<p>',
                '<label>Memory:</label>',
                '<select id="server_memory" name="server_memory" style="width:80px">',
                '<option>256</option>',
                '<option>512</option>',
                '<option>1024</option>',
                '<option selected="selected">2048</option>',
                '<option>4096</option>',
                '<option>8192</option>',
                '<option>16384</option>',
                '</select>MB',
                '</p>',
                '<p id="server_disk">',
                '<label for="server_disk_size">Total disk size:',
                '<a href="//docs.irigo.com/topics/vjgbT8" rel="help" target="_blank" class="irigo-tooltip">help</a>',
                '</label>',
                '<input id="server_disk_size" style="width: 6em" />GB',
                '</p>',
                '<p>',
                '<label>VCPUs: </label>',
                '<input id="server_vcpus" name="server_vcpus" style="width:80px" />',
                '</p>',
                '<p>',
                '<label>Instances: </label>',
                '<input id="server_instances" name="server_instances" style="width:80px" />',
                '</p>',
                '</form>'].join('');
        }

        function init_step_two(){
            dijit.form.NumberSpinner(
            {
                value: 20,
                smallDelta: 1,
                constraints: {
                    min: 1,
                    max: 500,
                    places: 0
                },
                name: "server_disk_size"
            }, 'server_disk_size');

            dijit.form.ComboBox({}, 'server_memory');
            dijit.form.NumberSpinner(
            {
                value: 1,
                smallDelta: 1,
                constraints: {
                    min: 1,
                    max: 4,
                    places: 0
                }
            }, 'server_vcpus');

            dijit.form.NumberSpinner(
            {
                value: 1,
                smallDelta: 1,
                constraints: {
                    min: 1,
                    max: 10,
                    places: 0
                }
            }, 'server_instances');
        }

        function step_three(){
            return [
                '<form method="" action="" class="createServerForm">',
                '<p class="wizardInfoPane">',
              '<a href="//docs.irigo.com/topics/u3Hd5" rel="help" target="_blank" class="irigo-text">help</a>',
                '</p>',
/*                '<p>',
                '<label style="width:240px;">Create a new network:</label>',
                '<input id="network_create" dojoType="dijit.form.CheckBox" checked="checked" />',
                '</p>',
                '<p>',
                '<label style="width:240px;">Or select an existing:</label>',
                '<div id="network_select"></div>',
                '</p>',*/
                '<p>',
                '<label style="width:240px;">Start server(s):</label>',
                '<input id="server_start" dojoType="dijit.form.CheckBox" checked="checked" />',
                '</p>',
//                '<p>',
//                '<label style="width:240px;">Start administration console:</label>',
//                '<input id="server_start_console" dojoType="dijit.form.CheckBox" checked="checked" />',
//                '</p>',       
                '<p>',
                '<label style="width:240px;">Allocate internal IP address(es):</label>',
                '<input id="allocate_internalip" checked name="ip" dojoType="dijit.form.RadioButton" />',
                '</p>',
                '<p>',
                '<label style="width:240px;">Allocate IP address mapping(s):</label>',
                '<input id="allocate_ipmapping" name="ip" dojoType="dijit.form.RadioButton" />',
                '</p>',
                '<p>',
                '<label style="width:240px;">Allocate external IP address(es):</label>',
                '<input id="allocate_externalip" name="ip" dojoType="dijit.form.RadioButton" />',
                '</p>',
                '<p class="wizardInfoPane" id="finish_notes" style="display:none;">',
                '</p>',
                '<p id="consoleApplet"></p>',
                '</form>'].join('');
        }

        function init_step_three(){
            /*var network_select = new dijit.form.FilteringSelect(
            {
                name: 'network_select',
                type: 'text',
                required: true,
                store: stores.networks,
                searchAttr: 'name'
            }, 'network_select');*/
        }

        var step_one_pane = new dojox.widget.WizardPane(
        {
            content: step_one(),
            passFunction: wizards.server.validateStepOne
        });

        var step_two_pane = new dojox.widget.WizardPane(
        {
            content: step_two(),
            passFunction: wizards.server.validateStepTwo
        });

        var step_three_pane = new dojox.widget.WizardPane(
        {
            content: step_three(),
            passFunction: wizards.server.validateStepThree,
            doneFunction: wizards.server.done
        });

//        stores.images.fetch({query: {user: user.username}});
//        stores.images.close();

        wizard.addChild(step_one_pane);
        wizard.addChild(step_two_pane);
        wizard.addChild(step_three_pane);

        dialog.set('content',wizard);

        init_step_one();

        stores.images.fetch({query: {user: user.username}, onComplete: function(items) {
            i = (items?items.length+1:1);
            testName(i);
        }});

        function testName(i) {
            //testname = user.username +  '-server' + i;
            testname = user.username +  '-server-' + Math.uuid().toLowerCase().substr(0,4);
            testpath = "/mnt/stabile/images/" + user.username  + "/" + testname + " image.qcow2";
            var master = dijit.byId('master_select').value;            
            if (master != '') {
                testpath = master.replace(/(\/.+\/)(\w+)(\/.+)/,"$1" + user.username + "/" + testname + " image.qcow2");
            }
            stores.images.fetch({query: {path: testpath}, onComplete: function(items2) {
                if (items2 && items2.length>0) {
                    i = i + 1;
                    testName(i);
                }
                else (set_default_name(testname));
            }});
        }


      stores.masterimages.fetch({query: {path: "*lamp*"}, onItem: set_default_cdrom});
      init_step_two();
      init_step_three();
      var qText = dojo.query('.irigo-text');
      var qTooltip = dojo.query('.irigo-tooltip');

      if(qText.irigoText){qText.irigoText();}
      if(qTooltip.irigoTooltip){qTooltip.irigoTooltip();}
      dialog.show();
    },

    select_images_tab: function() {
        dijit.byId('createServerDialog').hide();
        upload.showDialog();
    },

    startConsole: function(uuid) {
        var goon = function(item){
            var ip = item[0].macip[0];
            var port = item[0].port[0];
            var name = item[0].name[0];
            console.log("Got: " + ip + ":" + port + ":" + name + ":" + user.get());

            var args = {
                host: window.location.host,
                remote_ip: ip,
                local_port: 8240,
                // lang: dijit.byId("keyboard").get('value'),
                // screen_size: dijit.byId("screensize").get('value'),
                window_title: name,
                remote_port: port,
                username: "irigo-" + user.get(),
                display_type: "vnc",
                append_to: "consoleApplet"
            };
            display.start("consoleApplet", args);
        };
        stores.servers.close();
        stores.servers.fetch({query: {uuid: uuid}, onComplete: goon});
        ui_update.onUpdate({id: "servers", force: "true"});
    },

    done: function(){
        if (wizards.server.done.done) {
            //alert("Already done!");
            dialog.hide()
            return;
        } else {
            wizards.server.done.done = true;
        }
        
        var cdrom = dijit.byId('cdrom_select').value;
        var master = dijit.byId('master_select').value;
        var image2 = "";
        var ownimage = dijit.byId('image_select').value;
        var ownimagename = dijit.byId('image_select').displayedValue;

        var name = dojo.byId('server_name').value;
        var memory = dijit.byId('server_memory').value;
        var disk_size = dojo.byId('server_disk_size').value *1024*1024*1024; // disk size in bytes
        var vcpus = dijit.byId('server_vcpus').value;
        var instances = dijit.byId('server_instances').value;
        var instances_done = 0;

        var image = images.model(
        {
            name: name + ' image' + "-" + instances_done,
            virtualsize: disk_size
        });

        var network = networks.model(
        {
            name: name + ' network' + "-" + instances_done,
            type: 'ipmapping',
            internalip: 'new'
        });

        var server = new Server({
            cdrom: cdrom,
            boot: "cdrom",
            name: name + "-" + instances_done,
            memory: memory,
            vcpu: vcpus,
            image: image.getPath(),
            imagename: image.name
        });

        // new image
        var imageItem = null;
        var networkItem = null;
        var serverItem = null;


        function saveFailed(e){
            IRIGO.toaster("A wizard error ocurred: " + e);
        }

        function saveImageFailed(e){
            console.log("Problem creating image:" + image.name);
            stores.images.revert();
            stores.images.close();
            saveFailed(e);
        }

        function saveNetworkFailed(e){
            console.log("Problem creating network:" + network.name);
            if (imageItem != null) {
                stores.images.setValue(imageItem, "action", "delete");
                stores.images.save({onComplete: function(){
                                      stores.networks.revert();
                                      stores.networks.close();
                                      saveFailed(e);
                                    }});
            } else {
                saveFailed(e);
            }
        }

        function saveServerFailed(e){
            console.log("Problem creating server: " + server.name);
            if (networkItem != null) {
                stores.networks.setValue(networkItem, "action", "delete");
                stores.networks.save();
            }
            if (imageItem != null) {
                stores.images.setValue(imageItem, "action", "delete");
                stores.images.save({onComplete: function(){
                                      stores.servers.revert();
                                      stores.servers.close();
                                      saveFailed(e);
                                    }});
            } else {
                stores.servers.revert();
                stores.servers.close();
                saveFailed(e);                
            }
            saveFailed(e);
        }

        function startNetwork(uuid) {
            var postData = "{\"identifier\": \"uuid\", \"label\": \"uuid\", \"items\":[{\"action\": \"activate\", \"uuid\": \"" + uuid + "\"}]}";
            var xhrArgs = {
                url: "/stabile/networks",
                postData: postData,
                load: function(data){
                    ;
                },
                error: function(error){
                    saveNetworkFailed(error);
                }
            }
            var deferred = dojo.xhrPost(xhrArgs);
        }

        function startServer(uuid) {
            var postData = "{\"identifier\": \"uuid\", \"label\": \"uuid\", \"items\":[{\"action\": \"start\", \"uuid\": \"" + uuid + "\"}]}";
            var xhrArgs = {
                url: "/stabile/servers",
                postData: postData,
                load: function(data){
                    startNetwork(networkItem.uuid);
                    var finish_notes = document.getElementById("finish_notes");
                    finish_notes.innerHTML += "<br>Your server is being started!<br><br>" +
                            "<!--  Click <a href='#' onclick='wizards.server.startConsole(\"" + uuid  + "\");'>here</a> to access your servers console. -->";
                    //home.refresh();
                },
                error: function(error){
                    ;
                }
            }
            var deferred = dojo.xhrPost(xhrArgs);
        }

        function finish(){
            if(dojo.byId('server_start').checked === true) startServer(server.uuid);
            else startNetwork(networkItem.uuid);
            dijit.byId('server_start').set("disabled", true);
            dijit.byId('allocate_internalip').set("disabled", true);
            dijit.byId('allocate_ipmapping').set("disabled", true);
            dijit.byId('allocate_externalip').set("disabled", true);

            instances_done++;
            if (instances_done < instances) {

                imageItem.status[0] = "used"; // We have not read new image status, so update locally
                image = images.model(
                {
                    name: name + ' image' + "-" + instances_done,
                    virtualsize: disk_size
                });

                network = networks.model(
                {
                    name: name + ' network' + "-" + instances_done,
                    type: 'ipmapping',
                    internalip: 'new'
                });

                server = servers.model(
                {
                    cdrom: cdrom,
                    boot: "cdrom",
                    name: name + "-" + instances_done,
                    memory: memory,
                    vcpu: vcpus,
                    image: image.getPath(),
                    imagename: image.name
                });

                console.log("More instances requested: " + instances_done );
                begin();
            } else {
                console.log("Updating all tabs...");

//                stores.servers.fetch({query: {user: user.username}});
//                stores.servers.close();
                newStores.servers.reset();
                stores.networks.fetch({query: {user: user.username}});
                stores.networks.close();
                stores.images.fetch({query: {user: user.username}});
                stores.images.close();

//                ui_update.onUpdate({id: "networks", force: "true"});
//                ui_update.onUpdate({id: "images", force: "true"});
//                ui_update.onUpdate({id: "servers", force: "true"});
                if (user.is_admin) ui_update.onUpdate({id: "nodes", force: "true"});
                home.refresh();
            }
            
//            dialog.hide();
//            wizards.server.done.done = true;

        }

        function get_networkid(items){
            if (items && items[0]) {
                server.networkid1 = items[0].id;
                server.networkuuid1 = networkItem.uuid;
                server.networkname1 = networkItem.name;
                network.id = items[0].id;
                var subnet = networks.getFirstThreeOctetsbyVlan(network.id);
                var internalip = items[0].internalip;
                var externalip = items[0].externalip;
                console.log("Server configured with network id: " + network.id);
                var networknotes;
                if (dojo.byId('allocate_internalip').checked === true) {
                    networknotes = "Your server has been assigned the internal IP address: " + internalip +
                    " (with subnet: " + subnet + ".0/255.255.255.0, default gateway and name server: " + subnet + ".1)";
                } else if (dojo.byId('allocate_ipmapping').checked === true) {
                    networknotes = "Your server has been assigned the internal IP address: " + internalip +
                    " (with subnet: " + subnet + ".0/255.255.255.0, default gateway and name server: " + subnet + ".1)" +
                    "<br>Your server has also been assigned an external IP address: " + externalip;
                } else if (dojo.byId('allocate_externalip').checked) {
                    networknotes = "Your server has been assigned the external IP address: " + externalip;
                }
                var finish_notes = document.getElementById("finish_notes");
                finish_notes.innerHTML += networknotes;
                finish_notes.style.display = "block";
            } else {
                stores.networks.fetchItemByIdentity({identity: "1",
                    onItem: function(item, request){
                        if (item) {
                            server.networkid1 =  item.nextid;
                            server.networkuuid1 = networkItem.uuid;
                            server.networkname1 = networkItem.name;
                            console.log("Server will be configured with network id: " + item.nextid);
                        } else {
                            console.log("Server will be configured with only outgoing network");
                        }
                        var finish_notes = document.getElementById("finish_notes");
                        finish_notes.innerHTML += "There was a problem configuring your servers network access.<br>";
                        finish_notes.style.display = "block";
                    }
                });                
            }
            save_server();

        }

        function save_server(response){
//            if(dojo.byId('server_start').checked === true) server.action = "start";
            serverItem = stores.servers.newItem(server);
            stores.servers.save({onComplete: finish, onError: saveServerFailed });
        }

        function save_network(){
            if (dojo.byId('allocate_internalip').checked === true) network.type = "internalip";
            else if (dojo.byId('allocate_ipmapping').checked === true) network.type = "ipmapping";
            else if (dojo.byId('allocate_externalip').checked === true) network.type = "externalip";
            console.log("Creating network...");
            networkItem = stores.networks.newItem(network);
            stores.networks.save({onComplete: get_networks, onError: saveNetworkFailed });
        }

        function get_networks(){
            stores.networks.fetch({query: {user: user.username}}); // just to make sure calling close() doesn't make problems...
            stores.networks.close();
//            stores.networks.fetch({query: {uuid: network.uuid}, onComplete: finish});
            stores.networks.fetch({query: {uuid: network.uuid}, onComplete: get_networkid});
        }

        function make_clone() {
            stores.images.save({onComplete: get_clone, onError: saveImageFailed });
        }

        function get_clone() {
        // Get the path of the cloned image
            var clone = master;
            //clone = clone.replace(/(\/mnt\/home\/images\/)(.+)(\/.+)/,"$1" + user.username + "$3");
            clone = clone.replace(/(\/.+\/)(\w+)(\/.+)/,"$1" + user.username + "$3");
            if (clone.indexOf(".clone")!=-1) {
                clone = clone.substring(0, clone.indexOf(".clone")) + ".clone";                                
            } else {
                clone = clone.substring(0, clone.indexOf(".master.qcow2")) + ".clone";
            }
            if (image2 && image2!="" && image2 !="--") {
                //image2 = image2.replace(/(\/mnt\/home\/images\/)(.+)(\/.+)/,"$1" + user.username + "$3");
                image2 = image2.replace(/(\/\w+\/)(.+)(\/.+)/,"$1" + user.username + "$3");
                image2 = image2.substring(0, image2.indexOf(".master.qcow2")) + ".clone";
            }
            stores.images.close();
            stores.images.fetch({query: {path: clone+"*"}, onComplete: function(items) {
                if (items && items.length>0) {
                    for (i=0; i<items.length; i++) {
                        console.log(items[i].path[0] + ":" + items[i].status[0]);
                        if (items[i].status[0] == "cloning" && items[i].path[0].indexOf(".master.qcow2")==-1) {
                            console.log("Found clone: " + items[i].path[0] + ":" + items[i].name[0]);
                            imageItem = items[i];
                            server.image = items[i].path[0];
                            server.imagename = items[i].name[0];
                            server.boot = "hd";
                            break;
                        }
                    }
                    if (image2 && image2!="" && image2 !="--") {

                        stores.images.fetch({query: {path: image2+"*"}, onComplete: function(items) {
                            if (items && items.length>0) {
                                for (i=0; i<items.length; i++) {
                                    if (items[i].status[0] == "cloning") {
                                        console.log("Found clone2: " + items[i].path[0] + ":" + items[i].name[0]);
                                        server.image2 = items[i].path[0];
                                        server.image2name = items[i].name[0];
                                        break;
                                    }
                                }
                                save_network();
                            } else {
                                console.log("No clone2 found..." + clone);
                                saveImageFailed();
                            }
                        }, onError: saveImageFailed});

                    } else {
                        save_network();
                    }
                } else {
                    console.log("No clone " + clone + " found of " + master);
                    saveImageFailed();
                }
            }, onError: saveImageFailed});
        }

        function save_image(){
            if (wizards.server.installtype == "cdrom" ) {
                imageItem = stores.images.newItem(image);
                imageItem.path[0] = image.getPath();
                stores.images.save({onComplete: save_network, onError: saveImageFailed });
            }
            else if (wizards.server.installtype == "master") {
                stores.images.fetch({query: {path: master}, onComplete: function(items) {
                    if (items && items.length==1) {
                        stores.images.setValue(items[0], "action","clone");
                        wizards.server.managementlink = items[0].managementlink[0];
                        if (items[0].image2 && items[0].image2[0]!="" && items[0].image2[0]!="--") {
                            image2 = items[0].image2[0];
                            stores.images.fetch({query: {path: image2}, onComplete: function(items2) {
                                if (items2 && items2.length==1) {
                                    console.log("Cloning secondary image: " + image2);
                                    stores.images.setValue(items2[0], "action","clone");
                                    make_clone();
                                }                                
                            }, onError: saveImageFailed});
                        } else {
                            image2 = "";
                            make_clone();
                        }
                    }
                }, onError: saveImageFailed});
            }
            else if (wizards.server.installtype == "ownimage") {
                server.image = ownimage;
                server.imagename = ownimagename;
                server.boot = "hd";
                save_network();
            }
        }

        function begin(){
            save_image();
        }

        begin();

    },
    validateStepOne: function(){
        wizards.server.installtype = "cdrom"
        var os = dijit.byId('cdrom_select').value;
        if (!os || os === '--') {
            os = dijit.byId('master_select').value;
            wizards.server.installtype = "master";
        }
        if (!os || os === '--'){
            os = dijit.byId('image_select').value;
            wizards.server.installtype = "ownimage";
        }
        var name = dojo.byId('server_name').value;

        if(!name || name === ""){
            return "Please name the server";
        }
        if(!os || os === '--'){
            wizards.server.installtype = "cdrom";
            return "Please choose an OS";
        }
        var server_disk = document.getElementById("server_disk");
        if (dijit.byId('cdrom_select').value=='') server_disk.style.display = "none";
        else server_disk.style.display = "block";
        return null;
    },

    validateStepTwo: function(){
        var disk_size = dijit.byId('server_disk_size').value;
        var memory = dijit.byId('server_memory').value;
        var vcpus = dijit.byId('server_vcpus').value;
        var instances = dijit.byId('server_instances').value;
        if(!disk_size){
            return "Please choose disk size";
        }
        if(!memory){
            return "Please choose memory size";
        }
        if(!vcpus){
            return "Please number of VCPUs";
        }
        if (user.memoryquota > 0 && memory > user.memoryquota) {
            return "This is over your current quota. Please choose a smaller amount of memory (RAM).";
        }
        if (user.vcpuquota > 0 && instances * vcpus > user.vcpuquota) {
            return "This is over your current quota. Please choose a lower number of VCPUs or instances.";
        }

        return null;
    },

    validateStepThree: function(){
        /*var network_select = dijit.byId('network_select').value;
        var network_create = dijit.byId('network_create').checked;
        if (!network_create && !network_select) {
            return "Please select an existing network or check checkbox to create one"
        }*/
        return null;
    }
};
window.wizards = wizards;

})



