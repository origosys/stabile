/*
	Copyright (c) 2004-2011, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/

//>>built
define("dojo/io/script",["../main","../has"],function(_1,_2){
_1.getObject("io",true,_1);
_2.add("script-readystatechange",function(_3,_4){
var _5=_4.createElement("script");
return typeof _5["onreadystatechange"]!=="undefined"&&(typeof _3["opera"]==="undefined"||_3["opera"].toString()!=="[object Opera]");
});
var _6=_2("script-readystatechange")?"onreadystatechange":"load",_7=/complete|loaded/;
_1.io.script={get:function(_8){
var _9=this._makeScriptDeferred(_8);
var _a=_9.ioArgs;
_1._ioAddQueryToUrl(_a);
_1._ioNotifyStart(_9);
if(this._canAttach(_a)){
var _b=this.attach(_a.id,_a.url,_8.frameDoc);
if(!_a.jsonp&&!_a.args.checkString){
var _c=_1.connect(_b,_6,function(_d){
if(_d.type=="load"||_7.test(_b.readyState)){
_1.disconnect(_c);
_a.scriptLoaded=_d;
}
});
}
}
_1._ioWatch(_9,this._validCheck,this._ioCheck,this._resHandle);
return _9;
},attach:function(id,_e,_f){
var doc=(_f||_1.doc);
var _10=doc.createElement("script");
_10.type="text/javascript";
_10.src=_e;
_10.id=id;
_10.async=true;
_10.charset="utf-8";
return doc.getElementsByTagName("head")[0].appendChild(_10);
},remove:function(id,_11){
_1.destroy(_1.byId(id,_11));
if(this["jsonp_"+id]){
delete this["jsonp_"+id];
}
},_makeScriptDeferred:function(_12){
var dfd=_1._ioSetArgs(_12,this._deferredCancel,this._deferredOk,this._deferredError);
var _13=dfd.ioArgs;
_13.id=_1._scopeName+"IoScript"+(this._counter++);
_13.canDelete=false;
_13.jsonp=_12.callbackParamName||_12.jsonp;
if(_13.jsonp){
_13.query=_13.query||"";
if(_13.query.length>0){
_13.query+="&";
}
_13.query+=_13.jsonp+"="+(_12.frameDoc?"parent.":"")+_1._scopeName+".io.script.jsonp_"+_13.id+"._jsonpCallback";
_13.frameDoc=_12.frameDoc;
_13.canDelete=true;
dfd._jsonpCallback=this._jsonpCallback;
this["jsonp_"+_13.id]=dfd;
}
return dfd;
},_deferredCancel:function(dfd){
dfd.canceled=true;
if(dfd.ioArgs.canDelete){
_1.io.script._addDeadScript(dfd.ioArgs);
}
},_deferredOk:function(dfd){
var _14=dfd.ioArgs;
if(_14.canDelete){
_1.io.script._addDeadScript(_14);
}
return _14.json||_14.scriptLoaded||_14;
},_deferredError:function(_15,dfd){
if(dfd.ioArgs.canDelete){
if(_15.dojoType=="timeout"){
_1.io.script.remove(dfd.ioArgs.id,dfd.ioArgs.frameDoc);
}else{
_1.io.script._addDeadScript(dfd.ioArgs);
}
}
return _15;
},_deadScripts:[],_counter:1,_addDeadScript:function(_16){
_1.io.script._deadScripts.push({id:_16.id,frameDoc:_16.frameDoc});
_16.frameDoc=null;
},_validCheck:function(dfd){
var _17=_1.io.script;
var _18=_17._deadScripts;
if(_18&&_18.length>0){
for(var i=0;i<_18.length;i++){
_17.remove(_18[i].id,_18[i].frameDoc);
_18[i].frameDoc=null;
}
_1.io.script._deadScripts=[];
}
return true;
},_ioCheck:function(dfd){
var _19=dfd.ioArgs;
if(_19.json||(_19.scriptLoaded&&!_19.args.checkString)){
return true;
}
var _1a=_19.args.checkString;
return _1a&&eval("typeof("+_1a+") != 'undefined'");
},_resHandle:function(dfd){
if(_1.io.script._ioCheck(dfd)){
dfd.callback(dfd);
}else{
dfd.errback(new Error("inconceivable dojo.io.script._resHandle error"));
}
},_canAttach:function(_1b){
return true;
},_jsonpCallback:function(_1c){
this.ioArgs.json=_1c;
}};
return _1.io.script;
});
