//>>built
define("dojox/gfx/svg",["dojo/_base/lang","dojo/_base/sniff","dojo/_base/window","dojo/dom","dojo/_base/declare","dojo/_base/array","dojo/dom-geometry","dojo/_base/Color","./_base","./shape","./path"],function(_1,_2,_3,_4,_5,_6,_7,_8,g,gs,_9){
var _a=g.svg={};
_a.useSvgWeb=(typeof window.svgweb!="undefined");
var _b=_2("ios"),_c=_2("android"),_d=_2("chrome")||(_c&&_c>=4)?"auto":"optimizeLegibility";
function _e(ns,_f){
if(_3.doc.createElementNS){
return _3.doc.createElementNS(ns,_f);
}else{
return _3.doc.createElement(_f);
}
};
function _10(_11){
if(_a.useSvgWeb){
return _3.doc.createTextNode(_11,true);
}else{
return _3.doc.createTextNode(_11);
}
};
function _12(){
if(_a.useSvgWeb){
return _3.doc.createDocumentFragment(true);
}else{
return _3.doc.createDocumentFragment();
}
};
_a.xmlns={xlink:"http://www.w3.org/1999/xlink",svg:"http://www.w3.org/2000/svg"};
_a.getRef=function(_13){
if(!_13||_13=="none"){
return null;
}
if(_13.match(/^url\(#.+\)$/)){
return _4.byId(_13.slice(5,-1));
}
if(_13.match(/^#dojoUnique\d+$/)){
return _4.byId(_13.slice(1));
}
return null;
};
_a.dasharray={solid:"none",shortdash:[4,1],shortdot:[1,1],shortdashdot:[4,1,1,1],shortdashdotdot:[4,1,1,1,1,1],dot:[1,3],dash:[4,3],longdash:[8,3],dashdot:[4,3,1,3],longdashdot:[8,3,1,3],longdashdotdot:[8,3,1,3,1,3]};
_5("dojox.gfx.svg.Shape",gs.Shape,{setFill:function(_14){
if(!_14){
this.fillStyle=null;
this.rawNode.setAttribute("fill","none");
this.rawNode.setAttribute("fill-opacity",0);
return this;
}
var f;
var _15=function(x){
this.setAttribute(x,f[x].toFixed(8));
};
if(typeof (_14)=="object"&&"type" in _14){
switch(_14.type){
case "linear":
f=g.makeParameters(g.defaultLinearGradient,_14);
var _16=this._setFillObject(f,"linearGradient");
_6.forEach(["x1","y1","x2","y2"],_15,_16);
break;
case "radial":
f=g.makeParameters(g.defaultRadialGradient,_14);
var _17=this._setFillObject(f,"radialGradient");
_6.forEach(["cx","cy","r"],_15,_17);
break;
case "pattern":
f=g.makeParameters(g.defaultPattern,_14);
var _18=this._setFillObject(f,"pattern");
_6.forEach(["x","y","width","height"],_15,_18);
break;
}
this.fillStyle=f;
return this;
}
f=g.normalizeColor(_14);
this.fillStyle=f;
this.rawNode.setAttribute("fill",f.toCss());
this.rawNode.setAttribute("fill-opacity",f.a);
this.rawNode.setAttribute("fill-rule","evenodd");
return this;
},setStroke:function(_19){
var rn=this.rawNode;
if(!_19){
this.strokeStyle=null;
rn.setAttribute("stroke","none");
rn.setAttribute("stroke-opacity",0);
return this;
}
if(typeof _19=="string"||_1.isArray(_19)||_19 instanceof _8){
_19={color:_19};
}
var s=this.strokeStyle=g.makeParameters(g.defaultStroke,_19);
s.color=g.normalizeColor(s.color);
if(s){
rn.setAttribute("stroke",s.color.toCss());
rn.setAttribute("stroke-opacity",s.color.a);
rn.setAttribute("stroke-width",s.width);
rn.setAttribute("stroke-linecap",s.cap);
if(typeof s.join=="number"){
rn.setAttribute("stroke-linejoin","miter");
rn.setAttribute("stroke-miterlimit",s.join);
}else{
rn.setAttribute("stroke-linejoin",s.join);
}
var da=s.style.toLowerCase();
if(da in _a.dasharray){
da=_a.dasharray[da];
}
if(da instanceof Array){
da=_1._toArray(da);
for(var i=0;i<da.length;++i){
da[i]*=s.width;
}
if(s.cap!="butt"){
for(var i=0;i<da.length;i+=2){
da[i]-=s.width;
if(da[i]<1){
da[i]=1;
}
}
for(var i=1;i<da.length;i+=2){
da[i]+=s.width;
}
}
da=da.join(",");
}
rn.setAttribute("stroke-dasharray",da);
rn.setAttribute("dojoGfxStrokeStyle",s.style);
}
return this;
},_getParentSurface:function(){
var _1a=this.parent;
for(;_1a&&!(_1a instanceof g.Surface);_1a=_1a.parent){
}
return _1a;
},_setFillObject:function(f,_1b){
var _1c=_a.xmlns.svg;
this.fillStyle=f;
var _1d=this._getParentSurface(),_1e=_1d.defNode,_1f=this.rawNode.getAttribute("fill"),ref=_a.getRef(_1f);
if(ref){
_1f=ref;
if(_1f.tagName.toLowerCase()!=_1b.toLowerCase()){
var id=_1f.id;
_1f.parentNode.removeChild(_1f);
_1f=_e(_1c,_1b);
_1f.setAttribute("id",id);
_1e.appendChild(_1f);
}else{
while(_1f.childNodes.length){
_1f.removeChild(_1f.lastChild);
}
}
}else{
_1f=_e(_1c,_1b);
_1f.setAttribute("id",g._base._getUniqueId());
_1e.appendChild(_1f);
}
if(_1b=="pattern"){
_1f.setAttribute("patternUnits","userSpaceOnUse");
var img=_e(_1c,"image");
img.setAttribute("x",0);
img.setAttribute("y",0);
img.setAttribute("width",f.width.toFixed(8));
img.setAttribute("height",f.height.toFixed(8));
img.setAttributeNS(_a.xmlns.xlink,"xlink:href",f.src);
_1f.appendChild(img);
}else{
_1f.setAttribute("gradientUnits","userSpaceOnUse");
for(var i=0;i<f.colors.length;++i){
var c=f.colors[i],t=_e(_1c,"stop"),cc=c.color=g.normalizeColor(c.color);
t.setAttribute("offset",c.offset.toFixed(8));
t.setAttribute("stop-color",cc.toCss());
t.setAttribute("stop-opacity",cc.a);
_1f.appendChild(t);
}
}
this.rawNode.setAttribute("fill","url(#"+_1f.getAttribute("id")+")");
this.rawNode.removeAttribute("fill-opacity");
this.rawNode.setAttribute("fill-rule","evenodd");
return _1f;
},_applyTransform:function(){
var _20=this.matrix;
if(_20){
var tm=this.matrix;
this.rawNode.setAttribute("transform","matrix("+tm.xx.toFixed(8)+","+tm.yx.toFixed(8)+","+tm.xy.toFixed(8)+","+tm.yy.toFixed(8)+","+tm.dx.toFixed(8)+","+tm.dy.toFixed(8)+")");
}else{
this.rawNode.removeAttribute("transform");
}
return this;
},setRawNode:function(_21){
var r=this.rawNode=_21;
if(this.shape.type!="image"){
r.setAttribute("fill","none");
}
r.setAttribute("fill-opacity",0);
r.setAttribute("stroke","none");
r.setAttribute("stroke-opacity",0);
r.setAttribute("stroke-width",1);
r.setAttribute("stroke-linecap","butt");
r.setAttribute("stroke-linejoin","miter");
r.setAttribute("stroke-miterlimit",4);
r.__gfxObject__=this.getUID();
},setShape:function(_22){
this.shape=g.makeParameters(this.shape,_22);
for(var i in this.shape){
if(i!="type"){
this.rawNode.setAttribute(i,this.shape[i]);
}
}
this.bbox=null;
return this;
},_moveToFront:function(){
this.rawNode.parentNode.appendChild(this.rawNode);
return this;
},_moveToBack:function(){
this.rawNode.parentNode.insertBefore(this.rawNode,this.rawNode.parentNode.firstChild);
return this;
}});
_5("dojox.gfx.svg.Group",_a.Shape,{constructor:function(){
gs.Container._init.call(this);
},setRawNode:function(_23){
this.rawNode=_23;
this.rawNode.__gfxObject__=this.getUID();
}});
_a.Group.nodeType="g";
_5("dojox.gfx.svg.Rect",[_a.Shape,gs.Rect],{setShape:function(_24){
this.shape=g.makeParameters(this.shape,_24);
this.bbox=null;
for(var i in this.shape){
if(i!="type"&&i!="r"){
this.rawNode.setAttribute(i,this.shape[i]);
}
}
if(this.shape.r!=null){
this.rawNode.setAttribute("ry",this.shape.r);
this.rawNode.setAttribute("rx",this.shape.r);
}
return this;
}});
_a.Rect.nodeType="rect";
_5("dojox.gfx.svg.Ellipse",[_a.Shape,gs.Ellipse],{});
_a.Ellipse.nodeType="ellipse";
_5("dojox.gfx.svg.Circle",[_a.Shape,gs.Circle],{});
_a.Circle.nodeType="circle";
_5("dojox.gfx.svg.Line",[_a.Shape,gs.Line],{});
_a.Line.nodeType="line";
_5("dojox.gfx.svg.Polyline",[_a.Shape,gs.Polyline],{setShape:function(_25,_26){
if(_25&&_25 instanceof Array){
this.shape=g.makeParameters(this.shape,{points:_25});
if(_26&&this.shape.points.length){
this.shape.points.push(this.shape.points[0]);
}
}else{
this.shape=g.makeParameters(this.shape,_25);
}
this.bbox=null;
this._normalizePoints();
var _27=[],p=this.shape.points;
for(var i=0;i<p.length;++i){
_27.push(p[i].x.toFixed(8),p[i].y.toFixed(8));
}
this.rawNode.setAttribute("points",_27.join(" "));
return this;
}});
_a.Polyline.nodeType="polyline";
_5("dojox.gfx.svg.Image",[_a.Shape,gs.Image],{setShape:function(_28){
this.shape=g.makeParameters(this.shape,_28);
this.bbox=null;
var _29=this.rawNode;
for(var i in this.shape){
if(i!="type"&&i!="src"){
_29.setAttribute(i,this.shape[i]);
}
}
_29.setAttribute("preserveAspectRatio","none");
_29.setAttributeNS(_a.xmlns.xlink,"xlink:href",this.shape.src);
_29.__gfxObject__=this.getUID();
return this;
}});
_a.Image.nodeType="image";
_5("dojox.gfx.svg.Text",[_a.Shape,gs.Text],{setShape:function(_2a){
this.shape=g.makeParameters(this.shape,_2a);
this.bbox=null;
var r=this.rawNode,s=this.shape;
r.setAttribute("x",s.x);
r.setAttribute("y",s.y);
r.setAttribute("text-anchor",s.align);
r.setAttribute("text-decoration",s.decoration);
r.setAttribute("rotate",s.rotated?90:0);
r.setAttribute("kerning",s.kerning?"auto":0);
r.setAttribute("text-rendering",_d);
if(r.firstChild){
r.firstChild.nodeValue=s.text;
}else{
r.appendChild(_10(s.text));
}
return this;
},getTextWidth:function(){
var _2b=this.rawNode,_2c=_2b.parentNode,_2d=_2b.cloneNode(true);
_2d.style.visibility="hidden";
var _2e=0,_2f=_2d.firstChild.nodeValue;
_2c.appendChild(_2d);
if(_2f!=""){
while(!_2e){
if(_2d.getBBox){
_2e=parseInt(_2d.getBBox().width);
}else{
_2e=68;
}
}
}
_2c.removeChild(_2d);
return _2e;
}});
_a.Text.nodeType="text";
_5("dojox.gfx.svg.Path",[_a.Shape,_9.Path],{_updateWithSegment:function(_30){
this.inherited(arguments);
if(typeof (this.shape.path)=="string"){
this.rawNode.setAttribute("d",this.shape.path);
}
},setShape:function(_31){
this.inherited(arguments);
if(this.shape.path){
this.rawNode.setAttribute("d",this.shape.path);
}else{
this.rawNode.removeAttribute("d");
}
return this;
}});
_a.Path.nodeType="path";
_5("dojox.gfx.svg.TextPath",[_a.Shape,_9.TextPath],{_updateWithSegment:function(_32){
this.inherited(arguments);
this._setTextPath();
},setShape:function(_33){
this.inherited(arguments);
this._setTextPath();
return this;
},_setTextPath:function(){
if(typeof this.shape.path!="string"){
return;
}
var r=this.rawNode;
if(!r.firstChild){
var tp=_e(_a.xmlns.svg,"textPath"),tx=_10("");
tp.appendChild(tx);
r.appendChild(tp);
}
var ref=r.firstChild.getAttributeNS(_a.xmlns.xlink,"href"),_34=ref&&_a.getRef(ref);
if(!_34){
var _35=this._getParentSurface();
if(_35){
var _36=_35.defNode;
_34=_e(_a.xmlns.svg,"path");
var id=g._base._getUniqueId();
_34.setAttribute("id",id);
_36.appendChild(_34);
r.firstChild.setAttributeNS(_a.xmlns.xlink,"xlink:href","#"+id);
}
}
if(_34){
_34.setAttribute("d",this.shape.path);
}
},_setText:function(){
var r=this.rawNode;
if(!r.firstChild){
var tp=_e(_a.xmlns.svg,"textPath"),tx=_10("");
tp.appendChild(tx);
r.appendChild(tp);
}
r=r.firstChild;
var t=this.text;
r.setAttribute("alignment-baseline","middle");
switch(t.align){
case "middle":
r.setAttribute("text-anchor","middle");
r.setAttribute("startOffset","50%");
break;
case "end":
r.setAttribute("text-anchor","end");
r.setAttribute("startOffset","100%");
break;
default:
r.setAttribute("text-anchor","start");
r.setAttribute("startOffset","0%");
break;
}
r.setAttribute("baseline-shift","0.5ex");
r.setAttribute("text-decoration",t.decoration);
r.setAttribute("rotate",t.rotated?90:0);
r.setAttribute("kerning",t.kerning?"auto":0);
r.firstChild.data=t.text;
}});
_a.TextPath.nodeType="text";
_5("dojox.gfx.svg.Surface",gs.Surface,{constructor:function(){
gs.Container._init.call(this);
},destroy:function(){
this.defNode=null;
this.inherited(arguments);
},setDimensions:function(_37,_38){
if(!this.rawNode){
return this;
}
this.rawNode.setAttribute("width",_37);
this.rawNode.setAttribute("height",_38);
return this;
},getDimensions:function(){
var t=this.rawNode?{width:g.normalizedLength(this.rawNode.getAttribute("width")),height:g.normalizedLength(this.rawNode.getAttribute("height"))}:null;
return t;
}});
_a.createSurface=function(_39,_3a,_3b){
var s=new _a.Surface();
s.rawNode=_e(_a.xmlns.svg,"svg");
s.rawNode.setAttribute("overflow","hidden");
if(_3a){
s.rawNode.setAttribute("width",_3a);
}
if(_3b){
s.rawNode.setAttribute("height",_3b);
}
var _3c=_e(_a.xmlns.svg,"defs");
s.rawNode.appendChild(_3c);
s.defNode=_3c;
s._parent=_4.byId(_39);
s._parent.appendChild(s.rawNode);
return s;
};
var _3d={_setFont:function(){
var f=this.fontStyle;
this.rawNode.setAttribute("font-style",f.style);
this.rawNode.setAttribute("font-variant",f.variant);
this.rawNode.setAttribute("font-weight",f.weight);
this.rawNode.setAttribute("font-size",f.size);
this.rawNode.setAttribute("font-family",f.family);
}};
var C=gs.Container,_3e={openBatch:function(){
this.fragment=_12();
},closeBatch:function(){
if(this.fragment){
this.rawNode.appendChild(this.fragment);
delete this.fragment;
}
},add:function(_3f){
if(this!=_3f.getParent()){
if(this.fragment){
this.fragment.appendChild(_3f.rawNode);
}else{
this.rawNode.appendChild(_3f.rawNode);
}
C.add.apply(this,arguments);
}
return this;
},remove:function(_40,_41){
if(this==_40.getParent()){
if(this.rawNode==_40.rawNode.parentNode){
this.rawNode.removeChild(_40.rawNode);
}
if(this.fragment&&this.fragment==_40.rawNode.parentNode){
this.fragment.removeChild(_40.rawNode);
}
C.remove.apply(this,arguments);
}
return this;
},clear:function(){
var r=this.rawNode;
while(r.lastChild){
r.removeChild(r.lastChild);
}
var _42=this.defNode;
if(_42){
while(_42.lastChild){
_42.removeChild(_42.lastChild);
}
r.appendChild(_42);
}
return C.clear.apply(this,arguments);
},_moveChildToFront:C._moveChildToFront,_moveChildToBack:C._moveChildToBack};
var _43={createObject:function(_44,_45){
if(!this.rawNode){
return null;
}
var _46=new _44(),_47=_e(_a.xmlns.svg,_44.nodeType);
_46.setRawNode(_47);
_46.setShape(_45);
this.add(_46);
return _46;
}};
_1.extend(_a.Text,_3d);
_1.extend(_a.TextPath,_3d);
_1.extend(_a.Group,_3e);
_1.extend(_a.Group,gs.Creator);
_1.extend(_a.Group,_43);
_1.extend(_a.Surface,_3e);
_1.extend(_a.Surface,gs.Creator);
_1.extend(_a.Surface,_43);
_a.fixTarget=function(_48,_49){
if(!_48.gfxTarget){
if(_b&&_48.target.wholeText){
_48.gfxTarget=gs.byId(_48.target.parentElement.__gfxObject__);
}else{
_48.gfxTarget=gs.byId(_48.target.__gfxObject__);
}
}
return true;
};
if(_a.useSvgWeb){
_a.createSurface=function(_4a,_4b,_4c){
var s=new _a.Surface();
if(!_4b||!_4c){
var pos=_7.position(_4a);
_4b=_4b||pos.w;
_4c=_4c||pos.h;
}
_4a=_4.byId(_4a);
var id=_4a.id?_4a.id+"_svgweb":g._base._getUniqueId();
var _4d=_e(_a.xmlns.svg,"svg");
_4d.id=id;
_4d.setAttribute("width",_4b);
_4d.setAttribute("height",_4c);
svgweb.appendChild(_4d,_4a);
_4d.addEventListener("SVGLoad",function(){
s.rawNode=this;
s.isLoaded=true;
var _4e=_e(_a.xmlns.svg,"defs");
s.rawNode.appendChild(_4e);
s.defNode=_4e;
if(s.onLoad){
s.onLoad(s);
}
},false);
s.isLoaded=false;
return s;
};
_a.Surface.extend({destroy:function(){
var _4f=this.rawNode;
svgweb.removeChild(_4f,_4f.parentNode);
}});
var _50={connect:function(_51,_52,_53){
if(_51.substring(0,2)==="on"){
_51=_51.substring(2);
}
if(arguments.length==2){
_53=_52;
}else{
_53=_1.hitch(_52,_53);
}
this.getEventSource().addEventListener(_51,_53,false);
return [this,_51,_53];
},disconnect:function(_54){
this.getEventSource().removeEventListener(_54[1],_54[2],false);
delete _54[0];
}};
_1.extend(_a.Shape,_50);
_1.extend(_a.Surface,_50);
}
return _a;
});
