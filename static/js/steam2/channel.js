define([
'dojo/_base/declare',
'steam2/stores',
'steam2/user'
], function(declare, stores, user){

var Channel = declare('steam2.Channel', null, {

    wait: 500,

    constructor: function(){
        this.subscribe();
    },

    subscribe: function(){
        var channel = "/stabile/ui_update/" + user.username + "~ui_update";
        var self = this;
        dojo.xhrGet({
            handleAs:"json",
            url:channel,
            load: function(tasks){
                self.wait = 500;
                self.publish(tasks);
                self.subscribe();
            },
            error: function(){
                setTimeout(self.subscribe, self.wait);
                self.wait = self.wait * 1.5;
            }
        });
    },

    publish: function(tasks){
        dojo.forEach(tasks, function(ev){
            console.log('steam2.channel.publish', ev);
            if(ev.id == 'servers'){
                var set = stores.servers.setValue;
                var item = stores.servers.byId({identity:ev.uuid});
                if(ev.status){
                    set(item, 'status', ev.status);
                }
                if(ev.displayip){
                    set(item, 'macip', ev.displayip);
                }
                if(ev.displayport){
                    set(item, 'port', ev.displayport);
                }
            }
        });
    }
});

// go ahead and create the channel
new Channel();

});
