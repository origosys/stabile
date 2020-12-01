//>>built
define("dijit/focus",["dojo/aspect","dojo/_base/declare","dojo/dom","dojo/dom-attr","dojo/dom-construct","dojo/Evented","dojo/_base/lang","dojo/on","dojo/domReady","dojo/_base/sniff","dojo/Stateful","dojo/_base/window","dojo/window","./a11y","./registry","./main"],function(_1,_2,_3,_4,_5,_6,_7,on,_8,_9,_a,_b,_c,_d,_e,_f){
var _10=_2([_a,_6],{curNode:null,activeStack:[],constructor:function(){
var _11=_7.hitch(this,function(_12){
if(_3.isDescendant(this.curNode,_12)){
this.set("curNode",null);
}
if(_3.isDescendant(this.prevNode,_12)){
this.set("prevNode",null);
}
});
_1.before(_5,"empty",_11);
_1.before(_5,"destroy",_11);
},registerIframe:function(_13){
return this.registerWin(_13.contentWindow,_13);
},registerWin:function(_14,_15){
var _16=this,_17=_14.document&&_14.document.body;
if(_17){
var mdh=on(_17,"mousedown",function(evt){
_16._justMouseDowned=true;
setTimeout(function(){
_16._justMouseDowned=false;
},13);
if(evt&&evt.target&&evt.target.parentNode==null){
return;
}
_16._onTouchNode(_15||evt.target,"mouse");
});
var fih=on(_17,"focusin",function(evt){
if(!evt.target.tagName){
return;
}
var tag=evt.target.tagName.toLowerCase();
if(tag=="#document"||tag=="body"){
return;
}
if(_d.isTabNavigable(evt.target)){
_16._onFocusNode(_15||evt.target);
}else{
_16._onTouchNode(_15||evt.target);
}
});
var foh=on(_17,"focusout",function(evt){
_16._onBlurNode(_15||evt.target);
});
return {remove:function(){
mdh.remove();
fih.remove();
foh.remove();
mdh=fih=foh=null;
_17=null;
}};
}
},_onBlurNode:function(_18){
if(this._clearFocusTimer){
clearTimeout(this._clearFocusTimer);
}
this._clearFocusTimer=setTimeout(_7.hitch(this,function(){
this.set("prevNode",this.curNode);
this.set("curNode",null);
}),0);
if(this._justMouseDowned){
return;
}
if(this._clearActiveWidgetsTimer){
clearTimeout(this._clearActiveWidgetsTimer);
}
this._clearActiveWidgetsTimer=setTimeout(_7.hitch(this,function(){
delete this._clearActiveWidgetsTimer;
this._setStack([]);
}),100);
},_onTouchNode:function(_19,by){
if(this._clearActiveWidgetsTimer){
clearTimeout(this._clearActiveWidgetsTimer);
delete this._clearActiveWidgetsTimer;
}
var _1a=[];
try{
while(_19){
var _1b=_4.get(_19,"dijitPopupParent");
if(_1b){
_19=_e.byId(_1b).domNode;
}else{
if(_19.tagName&&_19.tagName.toLowerCase()=="body"){
if(_19===_b.body()){
break;
}
_19=_c.get(_19.ownerDocument).frameElement;
}else{
var id=_19.getAttribute&&_19.getAttribute("widgetId"),_1c=id&&_e.byId(id);
if(_1c&&!(by=="mouse"&&_1c.get("disabled"))){
_1a.unshift(id);
}
_19=_19.parentNode;
}
}
}
}
catch(e){
}
this._setStack(_1a,by);
},_onFocusNode:function(_1d){
if(!_1d){
return;
}
if(_1d.nodeType==9){
return;
}
if(this._clearFocusTimer){
clearTimeout(this._clearFocusTimer);
delete this._clearFocusTimer;
}
this._onTouchNode(_1d);
if(_1d==this.curNode){
return;
}
this.set("prevNode",this.curNode);
this.set("curNode",_1d);
},_setStack:function(_1e,by){
var _1f=this.activeStack,_20=_1f.length-1,_21=_1e.length-1;
if(_1e[_21]==_1f[_20]){
return;
}
this.set("activeStack",_1e);
var _22,i;
for(i=_20;i>=0&&_1f[i]!=_1e[i];i--){
_22=_e.byId(_1f[i]);
if(_22){
_22._hasBeenBlurred=true;
_22.set("focused",false);
if(_22._focusManager==this){
_22._onBlur(by);
}
this.emit("widget-blur",_22,by);
}
}
for(i++;i<=_21;i++){
_22=_e.byId(_1e[i]);
if(_22){
_22.set("focused",true);
if(_22._focusManager==this){
_22._onFocus(by);
}
this.emit("widget-focus",_22,by);
}
}
},focus:function(_23){
if(_23){
try{
_23.focus();
}
catch(e){
}
}
}});
var _24=new _10();
_8(function(){
var _25=_24.registerWin(_c.get(document));
if(_9("ie")){
on(window,"unload",function(){
if(_25){
_25.remove();
_25=null;
}
});
}
});
_f.focus=function(_26){
_24.focus(_26);
};
for(var _27 in _24){
if(!/^_/.test(_27)){
_f.focus[_27]=typeof _24[_27]=="function"?_7.hitch(_24,_27):_24[_27];
}
}
_24.watch(function(_28,_29,_2a){
_f.focus[_28]=_2a;
});
return _24;
});
