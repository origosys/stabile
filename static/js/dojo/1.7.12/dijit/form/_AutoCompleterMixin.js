//>>built
define("dijit/form/_AutoCompleterMixin",["dojo/_base/connect","dojo/data/util/filter","dojo/_base/declare","dojo/_base/Deferred","dojo/dom-attr","dojo/_base/event","dojo/keys","dojo/_base/lang","dojo/on","dojo/query","dojo/regexp","dojo/_base/sniff","dojo/string","dojo/_base/window","./DataList","../registry","./_TextBoxMixin"],function(_1,_2,_3,_4,_5,_6,_7,_8,on,_9,_a,_b,_c,_d,_e,_f,_10){
return _3("dijit.form._AutoCompleterMixin",null,{item:null,pageSize:Infinity,store:null,fetchProperties:{},query:{},list:"",_setListAttr:function(_11){
this._set("list",_11);
},autoComplete:true,highlightMatch:"first",searchDelay:100,searchAttr:"name",labelAttr:"",labelType:"text",queryExpr:"${0}*",ignoreCase:true,maxHeight:-1,_stopClickEvents:false,_getCaretPos:function(_12){
var pos=0;
if(typeof (_12.selectionStart)=="number"){
pos=_12.selectionStart;
}else{
if(_b("ie")){
var tr=_d.doc.selection.createRange().duplicate();
var ntr=_12.createTextRange();
tr.move("character",0);
ntr.move("character",0);
try{
ntr.setEndPoint("EndToEnd",tr);
pos=String(ntr.text).replace(/\r/g,"").length;
}
catch(e){
}
}
}
return pos;
},_setCaretPos:function(_13,_14){
_14=parseInt(_14);
_10.selectInputText(_13,_14,_14);
},_setDisabledAttr:function(_15){
this.inherited(arguments);
this.domNode.setAttribute("aria-disabled",_15);
},_abortQuery:function(){
if(this.searchTimer){
clearTimeout(this.searchTimer);
this.searchTimer=null;
}
if(this._fetchHandle){
if(this._fetchHandle.cancel){
this._cancelingQuery=true;
this._fetchHandle.cancel();
this._cancelingQuery=false;
}
this._fetchHandle=null;
}
},_onInput:function(evt){
this.inherited(arguments);
if(evt.charOrCode==229){
this._onKeyPress(evt);
}
},_onKey:function(evt){
if(this.disabled||this.readOnly){
return;
}
var key=evt.keyCode;
if(evt.altKey||((evt.ctrlKey||evt.metaKey)&&(key!=86&&key!=88))||key==_7.SHIFT){
return;
}
var _16=false;
var pw=this.dropDown;
var _17=null;
this._prev_key_backspace=false;
this._abortQuery();
this.inherited(arguments);
if(this._opened){
_17=pw.getHighlightedOption();
}
switch(key){
case _7.PAGE_DOWN:
case _7.DOWN_ARROW:
case _7.PAGE_UP:
case _7.UP_ARROW:
if(this._opened){
this._announceOption(_17);
}
_6.stop(evt);
break;
case _7.ENTER:
if(_17){
if(_17==pw.nextButton){
this._nextSearch(1);
_6.stop(evt);
break;
}else{
if(_17==pw.previousButton){
this._nextSearch(-1);
_6.stop(evt);
break;
}
}
}else{
this._setBlurValue();
this._setCaretPos(this.focusNode,this.focusNode.value.length);
}
if(this._opened||this._fetchHandle){
_6.stop(evt);
}
case _7.TAB:
var _18=this.get("displayedValue");
if(pw&&(_18==pw._messages["previousMessage"]||_18==pw._messages["nextMessage"])){
break;
}
if(_17){
this._selectOption(_17);
}
case _7.ESCAPE:
if(this._opened){
this._lastQuery=null;
this.closeDropDown();
}
break;
case " ":
if(_17){
_6.stop(evt);
this._selectOption(_17);
this.closeDropDown();
}else{
_16=true;
}
break;
case _7.DELETE:
case _7.BACKSPACE:
this._prev_key_backspace=true;
_16=true;
break;
}
if(_16){
this.item=undefined;
this.searchTimer=setTimeout(_8.hitch(this,"_startSearchFromInput"),1);
}
},_onKeyPress:function(evt){
if(typeof evt.charOrCode=="string"||evt.charOrCode==229){
this.item=undefined;
this.searchTimer=setTimeout(_8.hitch(this,"_startSearchFromInput"),1);
}
},_autoCompleteText:function(_19){
var fn=this.focusNode;
_10.selectInputText(fn,fn.value.length);
var _1a=this.ignoreCase?"toLowerCase":"substr";
if(_19[_1a](0).indexOf(this.focusNode.value[_1a](0))==0){
var _1b=this.autoComplete?this._getCaretPos(fn):fn.value.length;
if((_1b+1)>fn.value.length){
fn.value=_19;
_10.selectInputText(fn,_1b);
}
}else{
fn.value=_19;
_10.selectInputText(fn);
}
},_openResultList:function(_1c,_1d,_1e){
this._fetchHandle=null;
if(this.disabled||this.readOnly||(_1d[this.searchAttr]!==this._lastQuery)){
return;
}
var _1f=this.dropDown.getHighlightedOption();
this.dropDown.clearResultList();
if(!_1c.length&&_1e.start==0){
this.closeDropDown();
return;
}
this.dropDown.createOptions(_1c,_1e,_8.hitch(this,"_getMenuLabelFromItem"));
this._showResultList();
if(_1e.direction){
if(1==_1e.direction){
this.dropDown.highlightFirstOption();
}else{
if(-1==_1e.direction){
this.dropDown.highlightLastOption();
}
}
if(_1f){
this._announceOption(this.dropDown.getHighlightedOption());
}
}else{
if(this.autoComplete&&!this._prev_key_backspace&&!/^[*]+$/.test(_1d[this.searchAttr].toString())){
this._announceOption(this.dropDown.containerNode.firstChild.nextSibling);
}
}
},_showResultList:function(){
this.closeDropDown(true);
this.openDropDown();
this.domNode.setAttribute("aria-expanded","true");
},loadDropDown:function(){
this._startSearchAll();
},isLoaded:function(){
return false;
},closeDropDown:function(){
this._abortQuery();
if(this._opened){
this.inherited(arguments);
this.domNode.setAttribute("aria-expanded","false");
this.focusNode.removeAttribute("aria-activedescendant");
}
},_setBlurValue:function(){
var _20=this.get("displayedValue");
var pw=this.dropDown;
if(pw&&(_20==pw._messages["previousMessage"]||_20==pw._messages["nextMessage"])){
this._setValueAttr(this._lastValueReported,true);
}else{
if(typeof this.item=="undefined"){
this.item=null;
this.set("displayedValue",_20);
}else{
if(this.value!=this._lastValueReported){
this._handleOnChange(this.value,true);
}
this._refreshState();
}
}
},_setItemAttr:function(_21,_22,_23){
var _24="";
if(_21){
if(!_23){
_23=this.store._oldAPI?this.store.getValue(_21,this.searchAttr):_21[this.searchAttr];
}
_24=this._getValueField()!=this.searchAttr?this.store.getIdentity(_21):_23;
}
this.set("value",_24,_22,_23,_21);
},_announceOption:function(_25){
if(!_25){
return;
}
var _26;
if(_25==this.dropDown.nextButton||_25==this.dropDown.previousButton){
_26=_25.innerHTML;
this.item=undefined;
this.value="";
}else{
var _27=this.dropDown.items[_25.getAttribute("item")];
_26=(this.store._oldAPI?this.store.getValue(_27,this.searchAttr):_27[this.searchAttr]).toString();
this.set("item",_27,false,_26);
}
this.focusNode.value=this.focusNode.value.substring(0,this._lastInput.length);
this.focusNode.setAttribute("aria-activedescendant",_5.get(_25,"id"));
this._autoCompleteText(_26);
},_selectOption:function(_28){
this.closeDropDown();
if(_28){
this._announceOption(_28);
}
this._setCaretPos(this.focusNode,this.focusNode.value.length);
this._handleOnChange(this.value,true);
},_startSearchAll:function(){
this._startSearch("");
},_startSearchFromInput:function(){
this._startSearch(this.focusNode.value.replace(/([\\\*\?])/g,"\\$1"));
},_getQueryString:function(_29){
return _c.substitute(this.queryExpr,[_29]);
},_startSearch:function(key){
if(!this.dropDown){
var _2a=this.id+"_popup",_2b=_8.isString(this.dropDownClass)?_8.getObject(this.dropDownClass,false):this.dropDownClass;
this.dropDown=new _2b({onChange:_8.hitch(this,this._selectOption),id:_2a,dir:this.dir,textDir:this.textDir});
this.focusNode.removeAttribute("aria-activedescendant");
this.textbox.setAttribute("aria-owns",_2a);
}
this._lastInput=key;
var _2c=_8.clone(this.query);
var _2d={start:0,count:this.pageSize,queryOptions:{ignoreCase:this.ignoreCase,deep:true}};
_8.mixin(_2d,this.fetchProperties);
var qs=this._getQueryString(key),q;
if(this.store._oldAPI){
q=qs;
}else{
q=_2.patternToRegExp(qs,this.ignoreCase);
q.toString=function(){
return qs;
};
}
this._lastQuery=_2c[this.searchAttr]=q;
var _2e=this,_2f=function(){
var _30=_2e._fetchHandle=_2e.store.query(_2c,_2d);
_4.when(_30,function(res){
_2e._fetchHandle=null;
res.total=_30.total;
_2e._openResultList(res,_2c,_2d);
},function(err){
_2e._fetchHandle=null;
if(!_2e._cancelingQuery){
console.error(_2e.declaredClass+" "+err.toString());
_2e.closeDropDown();
}
});
};
this.searchTimer=setTimeout(_8.hitch(this,function(_31,_32){
this.searchTimer=null;
_2f();
this._nextSearch=this.dropDown.onPage=function(_33){
_2d.start+=_2d.count*_33;
_2d.direction=_33;
_2f();
_32.focus();
};
},_2c,this),this.searchDelay);
},_getValueField:function(){
return this.searchAttr;
},constructor:function(){
this.query={};
this.fetchProperties={};
},postMixInProperties:function(){
if(!this.store){
var _34=this.srcNodeRef;
var _35=this.list;
if(_35){
this.store=_f.byId(_35);
}else{
this.store=new _e({},_34);
}
if(!("value" in this.params)){
var _36=(this.item=this.store.fetchSelectedItem());
if(_36){
var _37=this._getValueField();
this.value=this.store._oldAPI?this.store.getValue(_36,_37):_36[_37];
}
}
}
this.inherited(arguments);
},postCreate:function(){
var _38=_9("label[for=\""+this.id+"\"]");
if(_38.length){
_38[0].id=(this.id+"_label");
this.domNode.setAttribute("aria-labelledby",_38[0].id);
}
this.inherited(arguments);
this.connect(this.focusNode,"onkeypress","_onKeyPress");
},_getMenuLabelFromItem:function(_39){
var _3a=this.labelFunc(_39,this.store),_3b=this.labelType;
if(this.highlightMatch!="none"&&this.labelType=="text"&&this._lastInput){
_3a=this.doHighlight(_3a,this._escapeHtml(this._lastInput));
_3b="html";
}
return {html:_3b=="html",label:_3a};
},doHighlight:function(_3c,_3d){
var _3e=(this.ignoreCase?"i":"")+(this.highlightMatch=="all"?"g":""),i=this.queryExpr.indexOf("${0}");
_3d=_a.escapeString(_3d);
return this._escapeHtml(_3c).replace(new RegExp((i==0?"^":"")+"("+_3d+")"+(i==(this.queryExpr.length-4)?"$":""),_3e),"<span class=\"dijitComboBoxHighlightMatch\">$1</span>");
},_escapeHtml:function(str){
str=String(str).replace(/&/gm,"&amp;").replace(/</gm,"&lt;").replace(/>/gm,"&gt;").replace(/"/gm,"&quot;");
return str;
},reset:function(){
this.item=null;
this.inherited(arguments);
},labelFunc:function(_3f,_40){
return (_40._oldAPI?_40.getValue(_3f,this.labelAttr||this.searchAttr):_3f[this.labelAttr||this.searchAttr]).toString();
},_setValueAttr:function(_41,_42,_43,_44){
this._set("item",_44||null);
if(!_41){
_41="";
}
this.inherited(arguments);
},_setTextDirAttr:function(_45){
this.inherited(arguments);
if(this.dropDown){
this.dropDown._set("textDir",_45);
}
}});
});
