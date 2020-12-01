//>>built
define("dojox/charting/Element",["dojo/_base/lang","dojo/_base/array","dojo/dom-construct","dojo/_base/declare","dojox/gfx","dojox/gfx/utils","dojox/gfx/shape"],function(_1,_2,_3,_4,_5,_6,_7){
return _4("dojox.charting.Element",null,{chart:null,group:null,htmlElements:null,dirty:true,constructor:function(_8){
this.chart=_8;
this.group=null;
this.htmlElements=[];
this.dirty=true;
this.trailingSymbol="...";
this._events=[];
},createGroup:function(_9){
if(!_9){
_9=this.chart.surface;
}
if(!this.group){
this.group=_9.createGroup();
}
return this;
},purgeGroup:function(){
this.destroyHtmlElements();
if(this.group){
_6.forEach(this.group,function(_a){
_7.dispose(_a);
});
if(this.group.rawNode){
_3.empty(this.group.rawNode);
}
this.group.clear();
this.group.removeShape();
_7.dispose(this.group);
this.group=null;
}
this.dirty=true;
if(this._events.length){
_2.forEach(this._events,function(_b){
_b.shape.disconnect(_b.handle);
});
this._events=[];
}
return this;
},cleanGroup:function(_c){
this.destroyHtmlElements();
if(!_c){
_c=this.chart.surface;
}
if(this.group){
var _d;
_6.forEach(this.group,function(_e){
_7.dispose(_e);
});
if(this.group.rawNode){
_d=this.group.bgNode;
_3.empty(this.group.rawNode);
}
this.group.clear();
if(_d){
this.group.rawNode.appendChild(_d);
}
}else{
this.group=_c.createGroup();
}
this.dirty=true;
return this;
},destroyHtmlElements:function(){
if(this.htmlElements.length){
_2.forEach(this.htmlElements,_3.destroy);
this.htmlElements=[];
}
},destroy:function(){
this.purgeGroup();
},getTextWidth:function(s,_f){
return _5._base._getTextBox(s,{font:_f}).w||0;
},getTextWithLimitLength:function(s,_10,_11,_12){
if(!s||s.length<=0){
return {text:"",truncated:_12||false};
}
if(!_11||_11<=0){
return {text:s,truncated:_12||false};
}
var _13=2,_14=0.618,_15=s.substring(0,1)+this.trailingSymbol,_16=this.getTextWidth(_15,_10);
if(_11<=_16){
return {text:_15,truncated:true};
}
var _17=this.getTextWidth(s,_10);
if(_17<=_11){
return {text:s,truncated:_12||false};
}else{
var _18=0,end=s.length;
while(_18<end){
if(end-_18<=_13){
while(this.getTextWidth(s.substring(0,_18)+this.trailingSymbol,_10)>_11){
_18-=1;
}
return {text:(s.substring(0,_18)+this.trailingSymbol),truncated:true};
}
var _19=_18+Math.round((end-_18)*_14),_1a=this.getTextWidth(s.substring(0,_19),_10);
if(_1a<_11){
_18=_19;
end=end;
}else{
_18=_18;
end=_19;
}
}
}
},getTextWithLimitCharCount:function(s,_1b,_1c,_1d){
if(!s||s.length<=0){
return {text:"",truncated:_1d||false};
}
if(!_1c||_1c<=0||s.length<=_1c){
return {text:s,truncated:_1d||false};
}
return {text:s.substring(0,_1c)+this.trailingSymbol,truncated:true};
},_plotFill:function(_1e,dim,_1f){
if(!_1e||!_1e.type||!_1e.space){
return _1e;
}
var _20=_1e.space;
switch(_1e.type){
case "linear":
if(_20==="plot"||_20==="shapeX"||_20==="shapeY"){
_1e=_5.makeParameters(_5.defaultLinearGradient,_1e);
_1e.space=_20;
if(_20==="plot"||_20==="shapeX"){
var _21=dim.height-_1f.t-_1f.b;
_1e.y1=_1f.t+_21*_1e.y1/100;
_1e.y2=_1f.t+_21*_1e.y2/100;
}
if(_20==="plot"||_20==="shapeY"){
var _21=dim.width-_1f.l-_1f.r;
_1e.x1=_1f.l+_21*_1e.x1/100;
_1e.x2=_1f.l+_21*_1e.x2/100;
}
}
break;
case "radial":
if(_20==="plot"){
_1e=_5.makeParameters(_5.defaultRadialGradient,_1e);
_1e.space=_20;
var _22=dim.width-_1f.l-_1f.r,_23=dim.height-_1f.t-_1f.b;
_1e.cx=_1f.l+_22*_1e.cx/100;
_1e.cy=_1f.t+_23*_1e.cy/100;
_1e.r=_1e.r*Math.sqrt(_22*_22+_23*_23)/200;
}
break;
case "pattern":
if(_20==="plot"||_20==="shapeX"||_20==="shapeY"){
_1e=_5.makeParameters(_5.defaultPattern,_1e);
_1e.space=_20;
if(_20==="plot"||_20==="shapeX"){
var _21=dim.height-_1f.t-_1f.b;
_1e.y=_1f.t+_21*_1e.y/100;
_1e.height=_21*_1e.height/100;
}
if(_20==="plot"||_20==="shapeY"){
var _21=dim.width-_1f.l-_1f.r;
_1e.x=_1f.l+_21*_1e.x/100;
_1e.width=_21*_1e.width/100;
}
}
break;
}
return _1e;
},_shapeFill:function(_24,_25){
if(!_24||!_24.space){
return _24;
}
var _26=_24.space;
switch(_24.type){
case "linear":
if(_26==="shape"||_26==="shapeX"||_26==="shapeY"){
_24=_5.makeParameters(_5.defaultLinearGradient,_24);
_24.space=_26;
if(_26==="shape"||_26==="shapeX"){
var _27=_25.width;
_24.x1=_25.x+_27*_24.x1/100;
_24.x2=_25.x+_27*_24.x2/100;
}
if(_26==="shape"||_26==="shapeY"){
var _27=_25.height;
_24.y1=_25.y+_27*_24.y1/100;
_24.y2=_25.y+_27*_24.y2/100;
}
}
break;
case "radial":
if(_26==="shape"){
_24=_5.makeParameters(_5.defaultRadialGradient,_24);
_24.space=_26;
_24.cx=_25.x+_25.width/2;
_24.cy=_25.y+_25.height/2;
_24.r=_24.r*_25.width/200;
}
break;
case "pattern":
if(_26==="shape"||_26==="shapeX"||_26==="shapeY"){
_24=_5.makeParameters(_5.defaultPattern,_24);
_24.space=_26;
if(_26==="shape"||_26==="shapeX"){
var _27=_25.width;
_24.x=_25.x+_27*_24.x/100;
_24.width=_27*_24.width/100;
}
if(_26==="shape"||_26==="shapeY"){
var _27=_25.height;
_24.y=_25.y+_27*_24.y/100;
_24.height=_27*_24.height/100;
}
}
break;
}
return _24;
},_pseudoRadialFill:function(_28,_29,_2a,_2b,end){
if(!_28||_28.type!=="radial"||_28.space!=="shape"){
return _28;
}
var _2c=_28.space;
_28=_5.makeParameters(_5.defaultRadialGradient,_28);
_28.space=_2c;
if(arguments.length<4){
_28.cx=_29.x;
_28.cy=_29.y;
_28.r=_28.r*_2a/100;
return _28;
}
var _2d=arguments.length<5?_2b:(end+_2b)/2;
return {type:"linear",x1:_29.x,y1:_29.y,x2:_29.x+_28.r*_2a*Math.cos(_2d)/100,y2:_29.y+_28.r*_2a*Math.sin(_2d)/100,colors:_28.colors};
return _28;
}});
});
