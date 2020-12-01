define([
"dojo/_base/lang",
"dojo/_base/connect",
"dojo/_base/declare"
], function(lang, connect, declare){

var Model = declare("steam2.models.Model", null, {

    constructor: function(args){
        lang.mixin(this, args);
    }

});

return Model;

});

