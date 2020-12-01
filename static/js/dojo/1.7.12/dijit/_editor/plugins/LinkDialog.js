//>>built
define("dijit/_editor/plugins/LinkDialog",["require","dojo/_base/declare","dojo/dom-attr","dojo/keys","dojo/_base/lang","dojo/_base/sniff","dojo/_base/query","dojo/string","dojo/_base/window","../../_Widget","../_Plugin","../../form/DropDownButton","../range","../selection"],function(_1,_2,_3,_4,_5,_6,_7,_8,_9,_a,_b,_c,_d,_e){
var _f=_2("dijit._editor.plugins.LinkDialog",_b,{buttonClass:_c,useDefaultCommand:false,urlRegExp:"((https?|ftps?|file)\\://|./|/|)(/[a-zA-Z]{1,1}:/|)(((?:(?:[\\da-zA-Z](?:[-\\da-zA-Z]{0,61}[\\da-zA-Z])?)\\.)*(?:[a-zA-Z](?:[-\\da-zA-Z]{0,80}[\\da-zA-Z])?)\\.?)|(((\\d|[1-9]\\d|1\\d\\d|2[0-4]\\d|25[0-5])\\.){3}(\\d|[1-9]\\d|1\\d\\d|2[0-4]\\d|25[0-5])|(0[xX]0*[\\da-fA-F]?[\\da-fA-F]\\.){3}0[xX]0*[\\da-fA-F]?[\\da-fA-F]|(0+[0-3][0-7][0-7]\\.){3}0+[0-3][0-7][0-7]|(0|[1-9]\\d{0,8}|[1-3]\\d{9}|4[01]\\d{8}|42[0-8]\\d{7}|429[0-3]\\d{6}|4294[0-8]\\d{5}|42949[0-5]\\d{4}|429496[0-6]\\d{3}|4294967[01]\\d{2}|42949672[0-8]\\d|429496729[0-5])|0[xX]0*[\\da-fA-F]{1,8}|([\\da-fA-F]{1,4}\\:){7}[\\da-fA-F]{1,4}|([\\da-fA-F]{1,4}\\:){6}((\\d|[1-9]\\d|1\\d\\d|2[0-4]\\d|25[0-5])\\.){3}(\\d|[1-9]\\d|1\\d\\d|2[0-4]\\d|25[0-5])))(\\:\\d+)?(/(?:[^?#\\s/]+/)*(?:[^?#\\s/]{0,}(?:\\?[^?#\\s/]*)?(?:#.*)?)?)?",emailRegExp:"<?(mailto\\:)([!#-'*+\\-\\/-9=?A-Z^-~]+[.])*[!#-'*+\\-\\/-9=?A-Z^-~]+"+"@"+"((?:(?:[\\da-zA-Z](?:[-\\da-zA-Z]{0,61}[\\da-zA-Z])?)\\.)+(?:[a-zA-Z](?:[-\\da-zA-Z]{0,6}[\\da-zA-Z])?)\\.?)|localhost|^[^-][a-zA-Z0-9_-]*>?",htmlTemplate:"<a href=\"${urlInput}\" _djrealurl=\"${urlInput}\""+" target=\"${targetSelect}\""+">${textInput}</a>",tag:"a",_hostRxp:/^((([^\[:]+):)?([^@]+)@)?(\[([^\]]+)\]|([^\[:]*))(:([0-9]+))?$/,_userAtRxp:/^([!#-'*+\-\/-9=?A-Z^-~]+[.])*[!#-'*+\-\/-9=?A-Z^-~]+@/i,linkDialogTemplate:["<table><tr><td>","<label for='${id}_urlInput'>${url}</label>","</td><td>","<input data-dojo-type='dijit.form.ValidationTextBox' required='true' "+"id='${id}_urlInput' name='urlInput' data-dojo-props='intermediateChanges:true'/>","</td></tr><tr><td>","<label for='${id}_textInput'>${text}</label>","</td><td>","<input data-dojo-type='dijit.form.ValidationTextBox' required='true' id='${id}_textInput' "+"name='textInput' data-dojo-props='intermediateChanges:true'/>","</td></tr><tr><td>","<label for='${id}_targetSelect'>${target}</label>","</td><td>","<select id='${id}_targetSelect' name='targetSelect' data-dojo-type='dijit.form.Select'>","<option selected='selected' value='_self'>${currentWindow}</option>","<option value='_blank'>${newWindow}</option>","<option value='_top'>${topWindow}</option>","<option value='_parent'>${parentWindow}</option>","</select>","</td></tr><tr><td colspan='2'>","<button data-dojo-type='dijit.form.Button' type='submit' id='${id}_setButton'>${set}</button>","<button data-dojo-type='dijit.form.Button' type='button' id='${id}_cancelButton'>${buttonCancel}</button>","</td></tr></table>"].join(""),_initButton:function(){
this.inherited(arguments);
this.button.loadDropDown=_5.hitch(this,"_loadDropDown");
this._connectTagEvents();
},_loadDropDown:function(_10){
_1(["dojo/i18n","../../TooltipDialog","../../registry","../../form/Button","../../form/Select","../../form/ValidationTextBox","dojo/i18n!../../nls/common","dojo/i18n!../nls/LinkDialog"],_5.hitch(this,function(_11,_12,_13){
var _14=this;
this.tag=this.command=="insertImage"?"img":"a";
var _15=_5.delegate(_11.getLocalization("dijit","common",this.lang),_11.getLocalization("dijit._editor","LinkDialog",this.lang));
var _16=(this.dropDown=this.button.dropDown=new _12({title:_15[this.command+"Title"],execute:_5.hitch(this,"setValue"),onOpen:function(){
_14._onOpenDialog();
_12.prototype.onOpen.apply(this,arguments);
},onCancel:function(){
setTimeout(_5.hitch(_14,"_onCloseDialog"),0);
}}));
_15.urlRegExp=this.urlRegExp;
_15.id=_13.getUniqueId(this.editor.id);
this._uniqueId=_15.id;
this._setContent(_16.title+"<div style='border-bottom: 1px black solid;padding-bottom:2pt;margin-bottom:4pt'></div>"+_8.substitute(this.linkDialogTemplate,_15));
_16.startup();
this._urlInput=_13.byId(this._uniqueId+"_urlInput");
this._textInput=_13.byId(this._uniqueId+"_textInput");
this._setButton=_13.byId(this._uniqueId+"_setButton");
this.connect(_13.byId(this._uniqueId+"_cancelButton"),"onClick",function(){
this.dropDown.onCancel();
});
if(this._urlInput){
this.connect(this._urlInput,"onChange","_checkAndFixInput");
}
if(this._textInput){
this.connect(this._textInput,"onChange","_checkAndFixInput");
}
this._urlRegExp=new RegExp("^"+this.urlRegExp+"$","i");
this._emailRegExp=new RegExp("^"+this.emailRegExp+"$","i");
this._urlInput.isValid=_5.hitch(this,function(){
var _17=this._urlInput.get("value");
return this._urlRegExp.test(_17)||this._emailRegExp.test(_17);
});
this.connect(_16.domNode,"onkeypress",function(e){
if(e&&e.charOrCode==_4.ENTER&&!e.shiftKey&&!e.metaKey&&!e.ctrlKey&&!e.altKey){
if(!this._setButton.get("disabled")){
_16.onExecute();
_16.execute(_16.get("value"));
}
}
});
_10();
}));
},_checkAndFixInput:function(){
var _18=this;
var url=this._urlInput.get("value");
var _19=function(url){
var _1a=false;
var _1b=false;
if(url&&url.length>1){
url=_5.trim(url);
if(url.indexOf("mailto:")!==0){
if(url.indexOf("/")>0){
if(url.indexOf("://")===-1){
if(url.charAt(0)!=="/"&&url.indexOf("./")!==0){
if(_18._hostRxp.test(url)){
_1a=true;
}
}
}
}else{
if(_18._userAtRxp.test(url)){
_1b=true;
}
}
}
}
if(_1a){
_18._urlInput.set("value","http://"+url);
}
if(_1b){
_18._urlInput.set("value","mailto:"+url);
}
_18._setButton.set("disabled",!_18._isValid());
};
if(this._delayedCheck){
clearTimeout(this._delayedCheck);
this._delayedCheck=null;
}
this._delayedCheck=setTimeout(function(){
_19(url);
},250);
},_connectTagEvents:function(){
this.editor.onLoadDeferred.addCallback(_5.hitch(this,function(){
this.connect(this.editor.editNode,"ondblclick",this._onDblClick);
}));
},_isValid:function(){
return this._urlInput.isValid()&&this._textInput.isValid();
},_setContent:function(_1c){
this.dropDown.set({parserScope:"dojo",content:_1c});
},_checkValues:function(_1d){
if(_1d&&_1d.urlInput){
_1d.urlInput=_1d.urlInput.replace(/"/g,"&quot;");
}
return _1d;
},setValue:function(_1e){
this._onCloseDialog();
if(_6("ie")<9){
var sel=_d.getSelection(this.editor.window);
var _1f=sel.getRangeAt(0);
var a=_1f.endContainer;
if(a.nodeType===3){
a=a.parentNode;
}
if(a&&(a.nodeName&&a.nodeName.toLowerCase()!==this.tag)){
a=_9.withGlobal(this.editor.window,"getSelectedElement",_e,[this.tag]);
}
if(a&&(a.nodeName&&a.nodeName.toLowerCase()===this.tag)){
if(this.editor.queryCommandEnabled("unlink")){
_9.withGlobal(this.editor.window,"selectElementChildren",_e,[a]);
this.editor.execCommand("unlink");
}
}
}
_1e=this._checkValues(_1e);
this.editor.execCommand("inserthtml",_8.substitute(this.htmlTemplate,_1e));
_7("a",this.editor.document).forEach(function(a){
if(!a.innerHTML&&!_3.has(a,"name")){
a.parentNode.removeChild(a);
}
},this);
},_onCloseDialog:function(){
if(this.editor.focused){
this.editor.focus();
}
},_getCurrentValues:function(a){
var url,_20,_21;
if(a&&a.tagName.toLowerCase()===this.tag){
url=a.getAttribute("_djrealurl")||a.getAttribute("href");
_21=a.getAttribute("target")||"_self";
_20=a.textContent||a.innerText;
_9.withGlobal(this.editor.window,"selectElement",_e,[a,true]);
}else{
_20=_9.withGlobal(this.editor.window,_e.getSelectedText);
}
return {urlInput:url||"",textInput:_20||"",targetSelect:_21||""};
},_onOpenDialog:function(){
var a;
if(_6("ie")<9){
var sel=_d.getSelection(this.editor.window);
var _22=sel.getRangeAt(0);
a=_22.endContainer;
if(a.nodeType===3){
a=a.parentNode;
}
if(a&&(a.nodeName&&a.nodeName.toLowerCase()!==this.tag)){
a=_9.withGlobal(this.editor.window,"getSelectedElement",_e,[this.tag]);
}
}else{
a=_9.withGlobal(this.editor.window,"getAncestorElement",_e,[this.tag]);
}
this.dropDown.reset();
this._setButton.set("disabled",true);
this.dropDown.set("value",this._getCurrentValues(a));
},_onDblClick:function(e){
if(e&&e.target){
var t=e.target;
var tg=t.tagName?t.tagName.toLowerCase():"";
if(tg===this.tag&&_3.get(t,"href")){
var _23=this.editor;
_9.withGlobal(_23.window,"selectElement",_e,[t]);
_23.onDisplayChanged();
if(_23._updateTimer){
clearTimeout(_23._updateTimer);
delete _23._updateTimer;
}
_23.onNormalizedDisplayChanged();
var _24=this.button;
setTimeout(function(){
_24.set("disabled",false);
_24.loadAndOpenDropDown().then(function(){
if(_24.dropDown.focus){
_24.dropDown.focus();
}
});
},10);
}
}
}});
var _25=_2("dijit._editor.plugins.ImgLinkDialog",[_f],{linkDialogTemplate:["<table><tr><td>","<label for='${id}_urlInput'>${url}</label>","</td><td>","<input dojoType='dijit.form.ValidationTextBox' regExp='${urlRegExp}' "+"required='true' id='${id}_urlInput' name='urlInput' data-dojo-props='intermediateChanges:true'/>","</td></tr><tr><td>","<label for='${id}_textInput'>${text}</label>","</td><td>","<input data-dojo-type='dijit.form.ValidationTextBox' required='false' id='${id}_textInput' "+"name='textInput' data-dojo-props='intermediateChanges:true'/>","</td></tr><tr><td>","</td><td>","</td></tr><tr><td colspan='2'>","<button data-dojo-type='dijit.form.Button' type='submit' id='${id}_setButton'>${set}</button>","<button data-dojo-type='dijit.form.Button' type='button' id='${id}_cancelButton'>${buttonCancel}</button>","</td></tr></table>"].join(""),htmlTemplate:"<img src=\"${urlInput}\" _djrealurl=\"${urlInput}\" alt=\"${textInput}\" />",tag:"img",_getCurrentValues:function(img){
var url,_26;
if(img&&img.tagName.toLowerCase()===this.tag){
url=img.getAttribute("_djrealurl")||img.getAttribute("src");
_26=img.getAttribute("alt");
_9.withGlobal(this.editor.window,"selectElement",_e,[img,true]);
}else{
_26=_9.withGlobal(this.editor.window,_e.getSelectedText);
}
return {urlInput:url||"",textInput:_26||""};
},_isValid:function(){
return this._urlInput.isValid();
},_connectTagEvents:function(){
this.inherited(arguments);
this.editor.onLoadDeferred.addCallback(_5.hitch(this,function(){
this.connect(this.editor.editNode,"onmousedown",this._selectTag);
}));
},_selectTag:function(e){
if(e&&e.target){
var t=e.target;
var tg=t.tagName?t.tagName.toLowerCase():"";
if(tg===this.tag){
_9.withGlobal(this.editor.window,"selectElement",_e,[t]);
}
}
},_checkValues:function(_27){
if(_27&&_27.urlInput){
_27.urlInput=_27.urlInput.replace(/"/g,"&quot;");
}
if(_27&&_27.textInput){
_27.textInput=_27.textInput.replace(/"/g,"&quot;");
}
return _27;
},_onDblClick:function(e){
if(e&&e.target){
var t=e.target;
var tg=t.tagName?t.tagName.toLowerCase():"";
if(tg===this.tag&&_3.get(t,"src")){
var _28=this.editor;
_9.withGlobal(_28.window,"selectElement",_e,[t]);
_28.onDisplayChanged();
if(_28._updateTimer){
clearTimeout(_28._updateTimer);
delete _28._updateTimer;
}
_28.onNormalizedDisplayChanged();
var _29=this.button;
setTimeout(function(){
_29.set("disabled",false);
_29.loadAndOpenDropDown().then(function(){
if(_29.dropDown.focus){
_29.dropDown.focus();
}
});
},10);
}
}
}});
_b.registry["createLink"]=function(){
return new _f({command:"createLink"});
};
_b.registry["insertImage"]=function(){
return new _25({command:"insertImage"});
};
_f.ImgLinkDialog=_25;
return _f;
});
