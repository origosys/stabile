//>>built
define("dojox/json/ref",["dojo/_base/kernel","dojox","dojo/date/stamp","dojo/_base/array","dojo/_base/json"],function(_1,_2){
_1.getObject("json",true,_2);
return _2.json.ref={resolveJson:function(_3,_4){
_4=_4||{};
var _5=_4.idAttribute||"id";
var _6=this.refAttribute;
var _7=_4.idAsRef;
var _8=_4.idPrefix||"";
var _9=_4.assignAbsoluteIds;
var _a=_4.index||{};
var _b=_4.timeStamps;
var _c,_d=[];
var _e=/^(.*\/)?(\w+:\/\/)|[^\/\.]+\/\.\.\/|^.*\/(\/)/;
var _f=this._addProp;
var F=function(){
};
function _10(it,_11,_12,_13,_14,_15,_16){
var i,_17,val,id=_5 in it?it[_5]:_12;
if(_5 in it||((id!==undefined)&&_13)){
id=(_8+id).replace(_e,"$2$3");
}
var _18=_15||it;
if(id!==undefined){
if(_9){
it.__id=id;
}
if(_4.schemas&&(!(it instanceof Array))&&(val=id.match(/^(.+\/)[^\.\[]*$/))){
_14=_4.schemas[val[1]];
}
if(_a[id]&&((it instanceof Array)==(_a[id] instanceof Array))){
_18=_a[id];
delete _18.$ref;
delete _18._loadObject;
_17=true;
}else{
var _19=_14&&_14.prototype;
if(_19){
F.prototype=_19;
_18=new F();
}
}
_a[id]=_18;
if(_b){
_b[id]=_4.time;
}
}
while(_14){
var _1a=_14.properties;
if(_1a){
for(i in it){
var _1b=_1a[i];
if(_1b&&_1b.format=="date-time"&&typeof it[i]=="string"){
it[i]=_1.date.stamp.fromISOString(it[i]);
}
}
}
_14=_14["extends"];
}
var _1c=it.length;
for(i in it){
if(i==_1c){
break;
}
if(it.hasOwnProperty(i)){
val=it[i];
if((typeof val=="object")&&val&&!(val instanceof Date)&&i!="__parent"){
_c=val[_6]||(_7&&val[_5]);
if(it!=_d&&(!_c||!val.__parent)){
val.__parent=_16?_16:_18;
}
if(_c){
delete it[i];
var _1d=_c.toString().replace(/(#)([^\.\[])/,"$1.$2").match(/(^([^\[]*\/)?[^#\.\[]*)#?([\.\[].*)?/);
if(_a[(_8+_c).replace(_e,"$2$3")]){
_c=_a[(_8+_c).replace(_e,"$2$3")];
}else{
if((_c=(_1d[1]=="$"||_1d[1]=="this"||_1d[1]=="")?_3:_a[(_8+_1d[1]).replace(_e,"$2$3")])){
if(_1d[3]){
_1d[3].replace(/(\[([^\]]+)\])|(\.?([^\.\[]+))/g,function(t,a,b,c,d){
_c=_c&&_c[b?b.replace(/[\"\'\\]/,""):d];
});
}
}
}
if(_c){
val=_c;
}else{
if(!_11){
var _1e;
if(!_1e){
_d.push(_18);
}
_1e=true;
val=_10(val,false,val[_6],true,_1b);
val._loadObject=_4.loader;
}
}
}else{
if(!_11){
val=_10(val,_d==it,id===undefined?undefined:_f(id,i),false,_1b,_18!=it&&typeof _18[i]=="object"&&_18[i],it);
}
}
}
it[i]=val;
if(_18!=it&&!_18.__isDirty){
var old=_18[i];
_18[i]=val;
if(_17&&val!==old&&!_18._loadObject&&!(i.charAt(0)=="_"&&i.charAt(1)=="_")&&i!="$ref"&&!(val instanceof Date&&old instanceof Date&&val.getTime()==old.getTime())&&!(typeof val=="function"&&typeof old=="function"&&val.toString()==old.toString())&&_a.onUpdate){
_a.onUpdate(_18,i,old,val);
}
}
}
}
if(_17&&(_5 in it||_18 instanceof Array)){
for(i in _18){
if(!_18.__isDirty&&_18.hasOwnProperty(i)&&!it.hasOwnProperty(i)&&!(i.charAt(0)=="_"&&i.charAt(1)=="_")&&!(_18 instanceof Array&&isNaN(i))){
if(_a.onUpdate&&i!="_loadObject"&&i!="_idAttr"){
_a.onUpdate(_18,i,_18[i],undefined);
}
delete _18[i];
while(_18 instanceof Array&&_18.length&&_18[_18.length-1]===undefined){
_18.length--;
}
}
}
}else{
if(_a.onLoad){
_a.onLoad(_18);
}
}
return _18;
};
if(_3&&typeof _3=="object"){
_3=_10(_3,false,_4.defaultId,true);
_10(_d,false);
}
return _3;
},fromJson:function(str,_1f){
function ref(_20){
var _21={};
_21[this.refAttribute]=_20;
return _21;
};
try{
var _22=eval("("+str+")");
}
catch(e){
throw new SyntaxError("Invalid JSON string: "+e.message+" parsing: "+str);
}
if(_22){
return this.resolveJson(_22,_1f);
}
return _22;
},toJson:function(it,_23,_24,_25){
var _26=this._useRefs;
var _27=this._addProp;
var _28=this.refAttribute;
_24=_24||"";
var _29={};
var _2a={};
function _2b(it,_2c,_2d){
if(typeof it=="object"&&it){
var _2e;
if(it instanceof Date){
return "\""+_1.date.stamp.toISOString(it,{zulu:true})+"\"";
}
var id=it.__id;
if(id){
if(_2c!="#"&&((_26&&!id.match(/#/))||_29[id])){
var ref=id;
if(id.charAt(0)!="#"){
if(it.__clientId==id){
ref="cid:"+id;
}else{
if(id.substring(0,_24.length)==_24){
ref=id.substring(_24.length);
}else{
ref=id;
}
}
}
var _2f={};
_2f[_28]=ref;
return _2b(_2f,"#");
}
_2c=id;
}else{
it.__id=_2c;
_2a[_2c]=it;
}
_29[_2c]=it;
_2d=_2d||"";
var _30=_23?_2d+_1.toJsonIndentStr:"";
var _31=_23?"\n":"";
var sep=_23?" ":"";
if(it instanceof Array){
var res=_1.map(it,function(obj,i){
var val=_2b(obj,_27(_2c,i),_30);
if(typeof val!="string"){
val="undefined";
}
return _31+_30+val;
});
return "["+res.join(","+sep)+_31+_2d+"]";
}
var _32=[];
for(var i in it){
if(it.hasOwnProperty(i)){
var _33;
if(typeof i=="number"){
_33="\""+i+"\"";
}else{
if(typeof i=="string"&&(i.charAt(0)!="_"||i.charAt(1)!="_")){
_33=_1._escapeString(i);
}else{
continue;
}
}
var val=_2b(it[i],_27(_2c,i),_30);
if(typeof val!="string"){
continue;
}
_32.push(_31+_30+_33+":"+sep+val);
}
}
return "{"+_32.join(","+sep)+_31+_2d+"}";
}else{
if(typeof it=="function"&&_2.json.ref.serializeFunctions){
return it.toString();
}
}
return _1.toJson(it);
};
var _34=_2b(it,"#","");
if(!_25){
for(var i in _2a){
delete _2a[i].__id;
}
}
return _34;
},_addProp:function(id,_35){
return id+(id.match(/#/)?id.length==1?"":".":"#")+_35;
},refAttribute:"$ref",_useRefs:false,serializeFunctions:false};
});
