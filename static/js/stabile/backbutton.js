// Discard - no longer relevant
define([
'dojo/_base/array',
'dojo/hash',
'dojo/topic',
'dijit/registry'
], function(arrayUtil, hash, topic, registry){

var backButton = {};

backButton.onHashChange = function(){
    var hashValue = hash().slice(1);
    if(menu){
        if(arrayUtil.indexOf(menu.ids, hashValue) != -1){
            if (registry.byId('tabContainer')) {
                registry.byId('tabContainer').selectChild(registry.byId(hash));
            }
        }
    }
};

// set the # the _ is to avoid the window moving to the hash tag
// topic.subscribe('tabContainer-selectChild', null, function(e){ hash('_' + e.id);});
topic.subscribe('/dojo/hashchange', null, backButton.onHashChange);

});
