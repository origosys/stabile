//>>built
define("dijit/popup",["dojo/_base/array","dojo/aspect","dojo/_base/connect","dojo/_base/declare","dojo/dom","dojo/dom-attr","dojo/dom-construct","dojo/dom-geometry","dojo/dom-style","dojo/_base/event","dojo/has","dojo/keys","dojo/_base/lang","dojo/on","dojo/_base/window","./place","./BackgroundIframe","."],function(_1,_2,_3,_4,_5,_6,_7,_8,_9,_a,_b,_c,_d,on,_e,_f,_10,_11){
function _12(){
if(this._popupWrapper){
_7.destroy(this._popupWrapper);
delete this._popupWrapper;
}
};
var _13=_4(null,{_stack:[],_beginZIndex:1000,_idGen:1,_createWrapper:function(_14){
var _15=_14._popupWrapper,_16=_14.domNode;
if(!_15){
_15=_7.create("div",{"class":"dijitPopup",style:{display:"none"},role:"presentation"},_e.body());
_15.appendChild(_16);
var s=_16.style;
s.display="";
s.visibility="";
s.position="";
s.top="0px";
_14._popupWrapper=_15;
_2.after(_14,"destroy",_12,true);
}
return _15;
},moveOffScreen:function(_17){
var _18=this._createWrapper(_17);
_9.set(_18,{visibility:"hidden",top:"-9999px",display:""});
},hide:function(_19){
var _1a=this._createWrapper(_19);
_9.set(_1a,"display","none");
},getTopPopup:function(){
var _1b=this._stack;
for(var pi=_1b.length-1;pi>0&&_1b[pi].parent===_1b[pi-1].widget;pi--){
}
return _1b[pi];
},open:function(_1c){
var _1d=this._stack,_1e=_1c.popup,_1f=_1c.orient||["below","below-alt","above","above-alt"],ltr=_1c.parent?_1c.parent.isLeftToRight():_8.isBodyLtr(),_20=_1c.around,id=(_1c.around&&_1c.around.id)?(_1c.around.id+"_dropdown"):("popup_"+this._idGen++);
while(_1d.length&&(!_1c.parent||!_5.isDescendant(_1c.parent.domNode,_1d[_1d.length-1].widget.domNode))){
this.close(_1d[_1d.length-1].widget);
}
var _21=this._createWrapper(_1e);
_6.set(_21,{id:id,style:{zIndex:this._beginZIndex+_1d.length},"class":"dijitPopup "+(_1e.baseClass||_1e["class"]||"").split(" ")[0]+"Popup",dijitPopupParent:_1c.parent?_1c.parent.id:""});
if(_b("bgIframe")&&!_1e.bgIframe){
_1e.bgIframe=new _10(_21);
}
var _22=_20?_f.around(_21,_20,_1f,ltr,_1e.orient?_d.hitch(_1e,"orient"):null):_f.at(_21,_1c,_1f=="R"?["TR","BR","TL","BL"]:["TL","BL","TR","BR"],_1c.padding);
_21.style.display="";
_21.style.visibility="visible";
_1e.domNode.style.visibility="visible";
var _23=[];
_23.push(on(_21,_3._keypress,_d.hitch(this,function(evt){
if(evt.charOrCode==_c.ESCAPE&&_1c.onCancel){
_a.stop(evt);
_1c.onCancel();
}else{
if(evt.charOrCode===_c.TAB){
_a.stop(evt);
var _24=this.getTopPopup();
if(_24&&_24.onCancel){
_24.onCancel();
}
}
}
})));
if(_1e.onCancel&&_1c.onCancel){
_23.push(_1e.on("cancel",_1c.onCancel));
}
_23.push(_1e.on(_1e.onExecute?"execute":"change",_d.hitch(this,function(){
var _25=this.getTopPopup();
if(_25&&_25.onExecute){
_25.onExecute();
}
})));
_1d.push({widget:_1e,parent:_1c.parent,onExecute:_1c.onExecute,onCancel:_1c.onCancel,onClose:_1c.onClose,handlers:_23});
if(_1e.onOpen){
_1e.onOpen(_22);
}
return _22;
},close:function(_26){
var _27=this._stack;
while((_26&&_1.some(_27,function(_28){
return _28.widget==_26;
}))||(!_26&&_27.length)){
var top=_27.pop(),_29=top.widget,_2a=top.onClose;
if(_29.onClose){
_29.onClose();
}
var h;
while(h=top.handlers.pop()){
h.remove();
}
if(_29&&_29.domNode){
this.hide(_29);
}
if(_2a){
_2a();
}
}
}});
return (_11.popup=new _13());
});
