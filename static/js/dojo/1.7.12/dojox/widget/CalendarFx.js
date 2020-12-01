//>>built
define("dojox/widget/CalendarFx",["dojo","dijit","dojox","dojo/require!dojox/widget/FisheyeLite"],function(_1,_2,_3){
_1.provide("dojox.widget.CalendarFx");
_1.require("dojox.widget.FisheyeLite");
_1.declare("dojox.widget._FisheyeFX",null,{addFx:function(_4,_5){
_1.query(_4,_5).forEach(function(_6){
new _3.widget.FisheyeLite({properties:{fontSize:1.1}},_6);
});
}});
_1.declare("dojox.widget.CalendarFisheye",[_3.widget.Calendar,_3.widget._FisheyeFX],{});
});
