define([
"dojo/_base/xhr",
"dojo/cookie"
], 
function(xhr, cookie){
    
    var user = {
        is_admin: null,
        username: null,
        storagequota: null,
        memoryquota: null,
        vcpuquota: null,
        externalipquota: null
    };
    if (typeof IRIGO === 'undefined') IRIGO = [];

    user.load = function() {
        var url = "/stabile/users?action=listids";
        xhr.get({
            sync: true,
            url : url,
            handleAs : "json",
            load : function(response) {
                user.privileges = response.items[0].privileges;
                user.userprivileges = response.items[0].userprivileges;
                user.is_admin = (user.privileges.indexOf('a') != -1);
                user.is_readonly = (user.privileges.indexOf('r') != -1);
                user.node_storage_allowed = (user.privileges.indexOf('n') != -1) || user.is_admin;
                var tktuser
                tktuser = response.items[0].tktuser;
                if (!tktuser)
                    tktuser = cookie("tktuser");
                var account = cookie("steamaccount");
                if (account) user.username = account;
                else user.username = tktuser;
                user.tktuser = tktuser;
                user.storagequota = Math.max(0, response.items[0].storagequota);
                user.nodestoragequota = Math.max(0, response.items[0].nodestoragequota);
                user.memoryquota = Math.max(0, response.items[0].memoryquota);
                user.vcpuquota = Math.max(0, response.items[0].vcpuquota);
                user.externalipquota = Math.max(0, response.items[0].externalipquota);
                user.rxquota = Math.max(0, response.items[0].rxquota);
                user.txquota = Math.max(0, response.items[0].txquota);

                user.defaultstoragequota = Math.max(0, response.items[0].defaultstoragequota);
                user.defaultnodestoragequota = Math.max(0, response.items[0].defaultnodestoragequota);
                user.defaultmemoryquota = Math.max(0, response.items[0].defaultmemoryquota);
                user.defaultvcpuquota = Math.max(0, response.items[0].defaultvcpuquota);
                user.defaultexternalipquota = Math.max(0, response.items[0].defaultexternalipquota);
                user.defaultrxquota = Math.max(0, response.items[0].defaultrxquota);
                user.defaulttxquota = Math.max(0, response.items[0].defaulttxquota);

                user.fullname =  response.items[0].fullname;
                user.phone =  response.items[0].phone;
                user.opphone =  response.items[0].opphone;
                user.opfullname =  response.items[0].opfullname;
                user.email = response.items[0].email;
                user.opemail = response.items[0].opemail;
                user.alertemail = response.items[0].alertemail;
                user.allowfrom = response.items[0].allowfrom;
                user.allowinternalapi = response.items[0].allowinternalapi;
                user.lastlogin = response.items[0].lastlogin;
                user.lastloginfrom = response.items[0].lastloginfrom;
                if (response.items[0].hasOwnProperty("engine")) {
                    user.zfsavailable = response.items[0].engine.zfsavailable;
                    user.engineid = response.items[0].engine.engineid;
                    user.enginename = response.items[0].engine.enginename;
                    user.engineuser = response.items[0].engine.engineuser;
                    user.enginelinked = response.items[0].engine.enginelinked;
                    user.downloadmasters = response.items[0].engine.downloadmasters;
                    user.externaliprangestart = response.items[0].engine.externaliprangestart;
                    user.externaliprangeend = response.items[0].engine.externaliprangeend;
                    user.proxyiprangestart = response.items[0].engine.proxyiprangestart;
                    user.proxyiprangeend = response.items[0].engine.proxyiprangeend;
                    user.proxygw = response.items[0].engine.proxygw;
                    user.disablesnat = response.items[0].engine.disablesnat;
                    user.imagesdevice = response.items[0].engine.imagesdevice;
                    user.backupdevice = response.items[0].engine.backupdevice;
                    user.vmreadlimit = response.items[0].engine.vmreadlimit;
                    user.vmwritelimit = response.items[0].engine.vmwritelimit;
                    user.vmiopsreadlimit = response.items[0].engine.vmiopsreadlimit;
                    user.vmiopswritelimit = response.items[0].engine.vmiopswritelimit;
                }
                user.showcost = response.items[0].showcost;
                user.billto = response.items[0].billto;
                user.appstoreurl = response.items[0].appstoreurl;
                IRIGO.user = user;
            },
            error : function(response) {
                console && console.log('An error occurred.', response);
            }
        });
    }
    user.releasepressure = function() {
        var url = "/stabile/users?action=releasepressure";
        xhr.get({
            sync: true,
            url : url,
            handleAs : "text",
            load : function(response) {
            },
            error : function(response) {
                console && console.log('An error occurred.', response);
            }
        });
    }
    user.load();
    return user;
});

