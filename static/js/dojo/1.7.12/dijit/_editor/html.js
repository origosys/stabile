//>>built
define("dijit/_editor/html",["dojo/_base/array","dojo/_base/lang","dojo/_base/sniff",".."],function(_1,_2,_3,_4){
var _5=document.createElement("form");
_3.add("dom-attributes-explicit",_5.attributes.length==0);
_3.add("dom-attributes-specified-flag",_5.attributes.length>0&&_5.attributes.length<40);
_2.getObject("_editor",true,_4);
_4._editor.escapeXml=function(_6,_7){
_6=_6.replace(/&/gm,"&amp;").replace(/</gm,"&lt;").replace(/>/gm,"&gt;").replace(/"/gm,"&quot;");
if(!_7){
_6=_6.replace(/'/gm,"&#39;");
}
return _6;
};
_4._editor.getNodeHtml=function(_8){
var _9;
switch(_8.nodeType){
case 1:
var _a=_8.nodeName.toLowerCase();
if(!_a||_a.charAt(0)=="/"){
return "";
}
_9="<"+_a;
var _b=[],_c={};
var _d;
if(_3("dom-attributes-explicit")||_3("dom-attributes-specified-flag")){
var i=0;
while((_d=_8.attributes[i++])){
var n=_d.name;
if(n.substr(0,3)!=="_dj"&&(!_3("dom-attributes-specified-flag")||_d.specified)&&!(n in _c)){
var v=_d.value;
if(n=="src"||n=="href"){
if(_8.getAttribute("_djrealurl")){
v=_8.getAttribute("_djrealurl");
}
}
if(_3("ie")===8&&n==="style"){
v=v.replace("HEIGHT:","height:").replace("WIDTH:","width:");
}
_b.push([n,v]);
_c[n]=v;
}
}
}else{
var _e=/^input$|^img$/i.test(_8.nodeName)?_8:_8.cloneNode(false);
var s=_e.outerHTML;
var _f=/[\w-]+=("[^"]*"|'[^']*'|\S*)/gi;
var _10=s.match(_f);
s=s.substr(0,s.indexOf(">"));
_1.forEach(_10,function(_11){
if(_11){
var idx=_11.indexOf("=");
if(idx>0){
var key=_11.substring(0,idx);
if(key.substr(0,3)!="_dj"){
if(key=="src"||key=="href"){
if(_8.getAttribute("_djrealurl")){
_b.push([key,_8.getAttribute("_djrealurl")]);
return;
}
}
var val,_12;
switch(key){
case "style":
val=_8.style.cssText.toLowerCase();
break;
case "class":
val=_8.className;
break;
case "width":
if(_a==="img"){
_12=/width=(\S+)/i.exec(s);
if(_12){
val=_12[1];
}
break;
}
case "height":
if(_a==="img"){
_12=/height=(\S+)/i.exec(s);
if(_12){
val=_12[1];
}
break;
}
default:
val=_8.getAttribute(key);
}
if(val!=null){
_b.push([key,val.toString()]);
}
}
}
}
},this);
}
_b.sort(function(a,b){
return a[0]<b[0]?-1:(a[0]==b[0]?0:1);
});
var j=0;
while((_d=_b[j++])){
_9+=" "+_d[0]+"=\""+(_2.isString(_d[1])?_4._editor.escapeXml(_d[1],true):_d[1])+"\"";
}
if(_a==="script"){
_9+=">"+_8.innerHTML+"</"+_a+">";
}else{
if(_8.childNodes.length){
_9+=">"+_4._editor.getChildrenHtml(_8)+"</"+_a+">";
}else{
switch(_a){
case "br":
case "hr":
case "img":
case "input":
case "base":
case "meta":
case "area":
case "basefont":
_9+=" />";
break;
default:
_9+="></"+_a+">";
}
}
}
break;
case 4:
case 3:
_9=_4._editor.escapeXml(_8.nodeValue,true);
break;
case 8:
_9="<!--"+_4._editor.escapeXml(_8.nodeValue,true)+"-->";
break;
default:
_9="<!-- Element not recognized - Type: "+_8.nodeType+" Name: "+_8.nodeName+"-->";
}
return _9;
};
_4._editor.getChildrenHtml=function(dom){
var out="";
if(!dom){
return out;
}
var _13=dom["childNodes"]||dom;
var _14=!_3("ie")||_13!==dom;
var _15,i=0;
while((_15=_13[i++])){
if(!_14||_15.parentNode==dom){
out+=_4._editor.getNodeHtml(_15);
}
}
return out;
};
return _4._editor;
});
