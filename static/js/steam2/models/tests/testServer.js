define([
"doh",
"dojo/_base/Deferred",
"../Server",
"../../stores",
"steam2/tests/fixtures"
], 
function(doh, Deferred, Server, fixtures){
           
    doh.register("steam2.models.tests.testServer", [

        function should_show_confirm_dialog_on_delete_action(t){
            var server = new Server();
            server.doAction('delete');
            t.isObject(Server._confirmDialog);
            Server._confirmDialog.hide();
        },

        function should_delete_server_when_user_confirms_delete(t){
            var server = new Server();
            server.doAction('delete');
            t.isObject(Server._confirmDialog);

            var mockSave = function(servers, action, arg){
                t.t(servers);
                t.is('delete', action);
            };
            var orig = Server.save;
            Server.save = mockSave;
            Server.actionConfirmed();
            Server.save = orig;
        },

        function should_update_status_to_destroying_after_destroy(t){
            var orig = Server._save;
            Server._save = function(json){
                var response = "Stroke=OK destroying ie6_windows_xp";
                var def = new Deferred();
                def.callback(response);
                return def;
            };
            steam2.stores.servers.save = function(){};
            
            var server = steam2.stores.servers.newItem({status:"running"});
            var mockDeferred = Server.save(server, "destroy");

            var dohDeferred = new doh.Deferred();
            mockDeferred.then(function(response){
                if(server.status === "destroying"){
                    dohDeferred.callback(true);                    
                }
                else{
                    dohDeferred.errback(new Error("Unexpected Server Status: " + server.status));
                }
            });
            Server._save = orig;
            return dohDeferred;
        },

        function when_mac_arg_supplied_should_get_server_action_with_mac(t){
            var server = new Server({uuid:1, status:"inactive"});
            var action = "start";
            var mac = "1234";

            var serverAction = Server.createAction(server, action, mac);
            t.is(serverAction.action, action);
            t.is(serverAction.mac, mac);
            t.is(serverAction.uuid, 1);
        },

        function  should_get_edit_image_link(t){
            var server = new Server({uuid: 1, image: "/foo", imagename: "foo"});
            var link = server.getEditImageLink();
            var expected = '<a style="" href="#" onclick="steam2.models.Image.editDialogFromPath(\'/foo\');arguments[0].stopPropagation();return false;">foo</a>';
            t.is(expected, link);
        }
    ]);
});