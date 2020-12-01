//>>built
define("dojox/gfx/shape",["./_base","dojo/_base/lang","dojo/_base/declare","dojo/_base/window","dojo/_base/sniff","dojo/_base/connect","dojo/_base/array","dojo/dom-construct","dojo/_base/Color","./matrix"],function(g,_1,_2,_3,_4,_5,_6,_7,_8,_9){
var _a=g.shape={};
var _b={};
var _c={};
var _d=0,_e=_4("ie")<9;
function _f(_10){
var _11={};
for(var key in _10){
if(_10.hasOwnProperty(key)){
_11[key]=_10[key];
}
}
return _11;
};
_a.register=function(_12){
var t=_12.declaredClass.split(".").pop();
var i=t in _b?++_b[t]:((_b[t]=0));
var uid=t+i;
_c[uid]=_12;
return uid;
};
_a.byId=function(id){
return _c[id];
};
_a.dispose=function(_13){
delete _c[_13.getUID()];
++_d;
if(_e&&_d>10000){
_c=_f(_c);
_d=0;
}
};
_2("dojox.gfx.shape.Shape",null,{constructor:function(){
this.rawNode=null;
this.shape=null;
this.matrix=null;
this.fillStyle=null;
this.strokeStyle=null;
this.bbox=null;
this.parent=null;
this.parentMatrix=null;
var uid=_a.register(this);
this.getUID=function(){
return uid;
};
},getNode:function(){
return this.rawNode;
},getShape:function(){
return this.shape;
},getTransform:function(){
return this.matrix;
},getFill:function(){
return this.fillStyle;
},getStroke:function(){
return this.strokeStyle;
},getParent:function(){
return this.parent;
},getBoundingBox:function(){
return this.bbox;
},getTransformedBoundingBox:function(){
var b=this.getBoundingBox();
if(!b){
return null;
}
var m=this._getRealMatrix(),gm=_9;
return [gm.multiplyPoint(m,b.x,b.y),gm.multiplyPoint(m,b.x+b.width,b.y),gm.multiplyPoint(m,b.x+b.width,b.y+b.height),gm.multiplyPoint(m,b.x,b.y+b.height)];
},getEventSource:function(){
return this.rawNode;
},setShape:function(_14){
this.shape=g.makeParameters(this.shape,_14);
this.bbox=null;
return this;
},setFill:function(_15){
if(!_15){
this.fillStyle=null;
return this;
}
var f=null;
if(typeof (_15)=="object"&&"type" in _15){
switch(_15.type){
case "linear":
f=g.makeParameters(g.defaultLinearGradient,_15);
break;
case "radial":
f=g.makeParameters(g.defaultRadialGradient,_15);
break;
case "pattern":
f=g.makeParameters(g.defaultPattern,_15);
break;
}
}else{
f=g.normalizeColor(_15);
}
this.fillStyle=f;
return this;
},setStroke:function(_16){
if(!_16){
this.strokeStyle=null;
return this;
}
if(typeof _16=="string"||_1.isArray(_16)||_16 instanceof _8){
_16={color:_16};
}
var s=this.strokeStyle=g.makeParameters(g.defaultStroke,_16);
s.color=g.normalizeColor(s.color);
return this;
},setTransform:function(_17){
this.matrix=_9.clone(_17?_9.normalize(_17):_9.identity);
return this._applyTransform();
},_applyTransform:function(){
return this;
},moveToFront:function(){
var p=this.getParent();
if(p){
p._moveChildToFront(this);
this._moveToFront();
}
return this;
},moveToBack:function(){
var p=this.getParent();
if(p){
p._moveChildToBack(this);
this._moveToBack();
}
return this;
},_moveToFront:function(){
},_moveToBack:function(){
},applyRightTransform:function(_18){
return _18?this.setTransform([this.matrix,_18]):this;
},applyLeftTransform:function(_19){
return _19?this.setTransform([_19,this.matrix]):this;
},applyTransform:function(_1a){
return _1a?this.setTransform([this.matrix,_1a]):this;
},removeShape:function(_1b){
if(this.parent){
this.parent.remove(this,_1b);
}
return this;
},_setParent:function(_1c,_1d){
this.parent=_1c;
return this._updateParentMatrix(_1d);
},_updateParentMatrix:function(_1e){
this.parentMatrix=_1e?_9.clone(_1e):null;
return this._applyTransform();
},_getRealMatrix:function(){
var m=this.matrix;
var p=this.parent;
while(p){
if(p.matrix){
m=_9.multiply(p.matrix,m);
}
p=p.parent;
}
return m;
}});
_a._eventsProcessing={connect:function(_1f,_20,_21){
return _5.connect(this.getEventSource(),_1f,_a.fixCallback(this,g.fixTarget,_20,_21));
},disconnect:function(_22){
_5.disconnect(_22);
}};
_a.fixCallback=function(_23,_24,_25,_26){
if(!_26){
_26=_25;
_25=null;
}
if(_1.isString(_26)){
_25=_25||_3.global;
if(!_25[_26]){
throw (["dojox.gfx.shape.fixCallback: scope[\"",_26,"\"] is null (scope=\"",_25,"\")"].join(""));
}
return function(e){
return _24(e,_23)?_25[_26].apply(_25,arguments||[]):undefined;
};
}
return !_25?function(e){
return _24(e,_23)?_26.apply(_25,arguments):undefined;
}:function(e){
return _24(e,_23)?_26.apply(_25,arguments||[]):undefined;
};
};
_1.extend(_a.Shape,_a._eventsProcessing);
_a.Container={_init:function(){
this.children=[];
},openBatch:function(){
},closeBatch:function(){
},add:function(_27){
var _28=_27.getParent();
if(_28){
_28.remove(_27,true);
}
this.children.push(_27);
return _27._setParent(this,this._getRealMatrix());
},remove:function(_29,_2a){
for(var i=0;i<this.children.length;++i){
if(this.children[i]==_29){
if(_2a){
}else{
_29.parent=null;
_29.parentMatrix=null;
}
this.children.splice(i,1);
break;
}
}
return this;
},clear:function(){
var _2b;
for(var i=0;i<this.children.length;++i){
_2b=this.children[i];
_2b.parent=null;
_2b.parentMatrix=null;
}
this.children=[];
return this;
},_moveChildToFront:function(_2c){
for(var i=0;i<this.children.length;++i){
if(this.children[i]==_2c){
this.children.splice(i,1);
this.children.push(_2c);
break;
}
}
return this;
},_moveChildToBack:function(_2d){
for(var i=0;i<this.children.length;++i){
if(this.children[i]==_2d){
this.children.splice(i,1);
this.children.unshift(_2d);
break;
}
}
return this;
}};
_2("dojox.gfx.shape.Surface",null,{constructor:function(){
this.rawNode=null;
this._parent=null;
this._nodes=[];
this._events=[];
},destroy:function(){
var _2e=function(s){
_a.dispose(s);
s.parent=null;
if(s.children&&s.children.length){
_6.forEach(s.children,_2e);
s.children=null;
}
};
_6.forEach(this.children,_2e);
this.children=null;
_6.forEach(this._nodes,_7.destroy);
this._nodes=[];
_6.forEach(this._events,_5.disconnect);
this._events=[];
this.rawNode=null;
if(_4("ie")){
while(this._parent.lastChild){
_7.destroy(this._parent.lastChild);
}
}else{
this._parent.innerHTML="";
}
this._parent=null;
},getEventSource:function(){
return this.rawNode;
},_getRealMatrix:function(){
return null;
},isLoaded:true,onLoad:function(_2f){
},whenLoaded:function(_30,_31){
var f=_1.hitch(_30,_31);
if(this.isLoaded){
f(this);
}else{
var h=_5.connect(this,"onLoad",function(_32){
_5.disconnect(h);
f(_32);
});
}
}});
_1.extend(_a.Surface,_a._eventsProcessing);
_2("dojox.gfx.Point",null,{});
_2("dojox.gfx.Rectangle",null,{});
_2("dojox.gfx.shape.Rect",_a.Shape,{constructor:function(_33){
this.shape=g.getDefault("Rect");
this.rawNode=_33;
},getBoundingBox:function(){
return this.shape;
}});
_2("dojox.gfx.shape.Ellipse",_a.Shape,{constructor:function(_34){
this.shape=g.getDefault("Ellipse");
this.rawNode=_34;
},getBoundingBox:function(){
if(!this.bbox){
var _35=this.shape;
this.bbox={x:_35.cx-_35.rx,y:_35.cy-_35.ry,width:2*_35.rx,height:2*_35.ry};
}
return this.bbox;
}});
_2("dojox.gfx.shape.Circle",_a.Shape,{constructor:function(_36){
this.shape=g.getDefault("Circle");
this.rawNode=_36;
},getBoundingBox:function(){
if(!this.bbox){
var _37=this.shape;
this.bbox={x:_37.cx-_37.r,y:_37.cy-_37.r,width:2*_37.r,height:2*_37.r};
}
return this.bbox;
}});
_2("dojox.gfx.shape.Line",_a.Shape,{constructor:function(_38){
this.shape=g.getDefault("Line");
this.rawNode=_38;
},getBoundingBox:function(){
if(!this.bbox){
var _39=this.shape;
this.bbox={x:Math.min(_39.x1,_39.x2),y:Math.min(_39.y1,_39.y2),width:Math.abs(_39.x2-_39.x1),height:Math.abs(_39.y2-_39.y1)};
}
return this.bbox;
}});
_2("dojox.gfx.shape.Polyline",_a.Shape,{constructor:function(_3a){
this.shape=g.getDefault("Polyline");
this.rawNode=_3a;
},setShape:function(_3b,_3c){
if(_3b&&_3b instanceof Array){
this.inherited(arguments,[{points:_3b}]);
if(_3c&&this.shape.points.length){
this.shape.points.push(this.shape.points[0]);
}
}else{
this.inherited(arguments,[_3b]);
}
return this;
},_normalizePoints:function(){
var p=this.shape.points,l=p&&p.length;
if(l&&typeof p[0]=="number"){
var _3d=[];
for(var i=0;i<l;i+=2){
_3d.push({x:p[i],y:p[i+1]});
}
this.shape.points=_3d;
}
},getBoundingBox:function(){
if(!this.bbox&&this.shape.points.length){
var p=this.shape.points;
var l=p.length;
var t=p[0];
var _3e={l:t.x,t:t.y,r:t.x,b:t.y};
for(var i=1;i<l;++i){
t=p[i];
if(_3e.l>t.x){
_3e.l=t.x;
}
if(_3e.r<t.x){
_3e.r=t.x;
}
if(_3e.t>t.y){
_3e.t=t.y;
}
if(_3e.b<t.y){
_3e.b=t.y;
}
}
this.bbox={x:_3e.l,y:_3e.t,width:_3e.r-_3e.l,height:_3e.b-_3e.t};
}
return this.bbox;
}});
_2("dojox.gfx.shape.Image",_a.Shape,{constructor:function(_3f){
this.shape=g.getDefault("Image");
this.rawNode=_3f;
},getBoundingBox:function(){
return this.shape;
},setStroke:function(){
return this;
},setFill:function(){
return this;
}});
_2("dojox.gfx.shape.Text",_a.Shape,{constructor:function(_40){
this.fontStyle=null;
this.shape=g.getDefault("Text");
this.rawNode=_40;
},getFont:function(){
return this.fontStyle;
},setFont:function(_41){
this.fontStyle=typeof _41=="string"?g.splitFontString(_41):g.makeParameters(g.defaultFont,_41);
this._setFont();
return this;
}});
_a.Creator={createShape:function(_42){
switch(_42.type){
case g.defaultPath.type:
return this.createPath(_42);
case g.defaultRect.type:
return this.createRect(_42);
case g.defaultCircle.type:
return this.createCircle(_42);
case g.defaultEllipse.type:
return this.createEllipse(_42);
case g.defaultLine.type:
return this.createLine(_42);
case g.defaultPolyline.type:
return this.createPolyline(_42);
case g.defaultImage.type:
return this.createImage(_42);
case g.defaultText.type:
return this.createText(_42);
case g.defaultTextPath.type:
return this.createTextPath(_42);
}
return null;
},createGroup:function(){
return this.createObject(g.Group);
},createRect:function(_43){
return this.createObject(g.Rect,_43);
},createEllipse:function(_44){
return this.createObject(g.Ellipse,_44);
},createCircle:function(_45){
return this.createObject(g.Circle,_45);
},createLine:function(_46){
return this.createObject(g.Line,_46);
},createPolyline:function(_47){
return this.createObject(g.Polyline,_47);
},createImage:function(_48){
return this.createObject(g.Image,_48);
},createText:function(_49){
return this.createObject(g.Text,_49);
},createPath:function(_4a){
return this.createObject(g.Path,_4a);
},createTextPath:function(_4b){
return this.createObject(g.TextPath,{}).setText(_4b);
},createObject:function(_4c,_4d){
return null;
}};
return _a;
});
