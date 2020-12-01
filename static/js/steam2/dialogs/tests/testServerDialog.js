define([
"doh",
"steam2/tests/fixtures",
"dojo/_base/Deferred",
"dojo/json",
"dojo/dom",
"dojox/data/AndOrWriteStore",
"dojo/data/ItemFileReadStore",
"../ServerDialog",
"../../models/Server",
"../../stores",
"../../user",
"dojox/data/JsonRestStore"
], 
function(doh, fixtures, Deferred, JSON, dom, AndOrWriteStore, ItemFileReadStore, ServerDialog, Server, stores, user, JsonRestStore){

    var server = new Server(fixtures.servers[0]);
    var dialog = new ServerDialog({server:server});
           
    doh.register("steam2.dialogs.tests.testServerDialog", [

        function widget_values_should_be_set_according_to_server_model(t){


            var actualImageUuid = dialog._widgets.image.widget.get('value');
            var expectedImageUuid = 1;
            t.is(expectedImageUuid, actualImageUuid);

            var actualImage2Uuid = dialog._widgets.image2.widget.get('value');
            var expectedImage2Uuid = '';
            t.is(expectedImage2Uuid, actualImage2Uuid);

            var actualNetworkUuid = dialog._widgets.networkuuid1.widget.get('value');
            var expectedNetworkUuid = 10;
            t.is(expectedNetworkUuid, actualNetworkUuid);
        },

        function image2_query_shold_exclude_uuid_of_image1_and_exclude_common_user(t){

            var imageQuery = dialog.getImageQuery('image');
            var image2Query = dialog.getImageQuery('image2');

            var expectedImageQuery = "user:" + user.username + " AND status:unused AND !type:iso AND !path:*.master.qcow2 OR uuid:1";
            var expectedImage2Query = "user:" + user.username + " AND status:unused AND !type:iso AND !path:*.master.qcow2 AND !uuid:1 AND type:qcow2";

            t.is(expectedImageQuery, imageQuery.complexQuery);
            t.is(expectedImage2Query, image2Query.complexQuery);

        },

        function networkuuid2_query_should_exclude_1(t){

            var n1 = dialog._widgets.networkuuid1.widget.get('value');
            t.is("10", n1);
            var nQ2 = dialog.getNetworkQuery('networkuuid2');
            var expectedQ2 = "uuid:* AND !uuid:10";
            t.is(expectedQ2, nQ2.complexQuery);

        },

        function status_update_should_update_status_field(t){

            var statusWidget = dialog._widgets.status.widget;
            t.is('inactive', statusWidget.get('value'));
            steam2.stores.servers.setValue(server, 'status', 'running');
            t.is('running', statusWidget.get('value'));

        },

        function when_image_type_is_qcow2_dialog_should_show_only_qcow2_compatible_running_nodes(t){
            
            var nodesWidget = dialog._widgets.mac.widget;
            var query = nodesWidget.query;

            t.is("kvm", query.identity);
            t.is("running", query.status);
        },

        function should_craete_new_server_from_dialog(t){
            
            // this gives a type error because of something in the
            // dijit Dialog, fuck it... we need to destroy the
            // serverFormManager widget  
            dialog.destroyRecursive();

            var server = new Server({uuid:100});
            dialog = new ServerDialog({server:server});
            var actions = dialog.save();
            
            t.is(1, actions.length);

            var def = new doh.Deferred();
            var action = actions[0];

            action.deferred.then(function(item){
                if(item.uuid !== "100"){
                    def.errback(new Error("Unexpected server uuid:" + item.uuid));
                }
                else{
                    def.callback(true);
                }
            });
            return def;
        }
    ]);

});