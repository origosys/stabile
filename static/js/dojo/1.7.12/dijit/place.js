//>>built
define("dijit/place",["dojo/_base/array","dojo/dom-geometry","dojo/dom-style","dojo/_base/kernel","dojo/_base/window","./Viewport","."],function(_1,_2,_3,_4,_5,_6,_7){
function _8(_9,_a,_b,_c){
var _d=_6.getEffectiveBox(_9.ownerDocument);
if(!_9.parentNode||String(_9.parentNode.tagName).toLowerCase()!="body"){
_5.body().appendChild(_9);
}
var _e=null;
_1.some(_a,function(_f){
var _10=_f.corner;
var pos=_f.pos;
var _11=0;
var _12={w:{"L":_d.l+_d.w-pos.x,"R":pos.x-_d.l,"M":_d.w}[_10.charAt(1)],h:{"T":_d.t+_d.h-pos.y,"B":pos.y-_d.t,"M":_d.h}[_10.charAt(0)]};
var s=_9.style;
s.left=s.right="auto";
if(_b){
var res=_b(_9,_f.aroundCorner,_10,_12,_c);
_11=typeof res=="undefined"?0:res;
}
var _13=_9.style;
var _14=_13.display;
var _15=_13.visibility;
if(_13.display=="none"){
_13.visibility="hidden";
_13.display="";
}
var bb=_2.position(_9);
_13.display=_14;
_13.visibility=_15;
var _16={"L":pos.x,"R":pos.x-bb.w,"M":Math.max(_d.l,Math.min(_d.l+_d.w,pos.x+(bb.w>>1))-bb.w)}[_10.charAt(1)],_17={"T":pos.y,"B":pos.y-bb.h,"M":Math.max(_d.t,Math.min(_d.t+_d.h,pos.y+(bb.h>>1))-bb.h)}[_10.charAt(0)],_18=Math.max(_d.l,_16),_19=Math.max(_d.t,_17),_1a=Math.min(_d.l+_d.w,_16+bb.w),_1b=Math.min(_d.t+_d.h,_17+bb.h),_1c=_1a-_18,_1d=_1b-_19;
_11+=(bb.w-_1c)+(bb.h-_1d);
if(_e==null||_11<_e.overflow){
_e={corner:_10,aroundCorner:_f.aroundCorner,x:_18,y:_19,w:_1c,h:_1d,overflow:_11,spaceAvailable:_12};
}
return !_11;
});
if(_e.overflow&&_b){
_b(_9,_e.aroundCorner,_e.corner,_e.spaceAvailable,_c);
}
var s=_9.style;
s.top=_e.y+"px";
s.left=_e.x+"px";
s.right="auto";
return _e;
};
return (_7.place={at:function(_1e,pos,_1f,_20){
var _21=_1.map(_1f,function(_22){
var c={corner:_22,pos:{x:pos.x,y:pos.y}};
if(_20){
c.pos.x+=_22.charAt(1)=="L"?_20.x:-_20.x;
c.pos.y+=_22.charAt(0)=="T"?_20.y:-_20.y;
}
return c;
});
return _8(_1e,_21);
},around:function(_23,_24,_25,_26,_27){
var _28=(typeof _24=="string"||"offsetWidth" in _24)?_2.position(_24,true):_24;
if(_24.parentNode){
var _29=_3.getComputedStyle(_24).position=="absolute";
var _2a=_24.parentNode;
while(_2a&&_2a.nodeType==1&&_2a.nodeName!="BODY"){
var _2b=_2.position(_2a,true),pcs=_3.getComputedStyle(_2a);
if(/relative|absolute/.test(pcs.position)){
_29=false;
}
if(!_29&&/hidden|auto|scroll/.test(pcs.overflow)){
var _2c=Math.min(_28.y+_28.h,_2b.y+_2b.h);
var _2d=Math.min(_28.x+_28.w,_2b.x+_2b.w);
_28.x=Math.max(_28.x,_2b.x);
_28.y=Math.max(_28.y,_2b.y);
_28.h=_2c-_28.y;
_28.w=_2d-_28.x;
}
if(pcs.position=="absolute"){
_29=true;
}
_2a=_2a.parentNode;
}
}
var x=_28.x,y=_28.y,_2e="w" in _28?_28.w:(_28.w=_28.width),_2f="h" in _28?_28.h:(_4.deprecated("place.around: dijit.place.__Rectangle: { x:"+x+", y:"+y+", height:"+_28.height+", width:"+_2e+" } has been deprecated.  Please use { x:"+x+", y:"+y+", h:"+_28.height+", w:"+_2e+" }","","2.0"),_28.h=_28.height);
var _30=[];
function _31(_32,_33){
_30.push({aroundCorner:_32,corner:_33,pos:{x:{"L":x,"R":x+_2e,"M":x+(_2e>>1)}[_32.charAt(1)],y:{"T":y,"B":y+_2f,"M":y+(_2f>>1)}[_32.charAt(0)]}});
};
_1.forEach(_25,function(pos){
var ltr=_26;
switch(pos){
case "above-centered":
_31("TM","BM");
break;
case "below-centered":
_31("BM","TM");
break;
case "after-centered":
ltr=!ltr;
case "before-centered":
_31(ltr?"ML":"MR",ltr?"MR":"ML");
break;
case "after":
ltr=!ltr;
case "before":
_31(ltr?"TL":"TR",ltr?"TR":"TL");
_31(ltr?"BL":"BR",ltr?"BR":"BL");
break;
case "below-alt":
ltr=!ltr;
case "below":
_31(ltr?"BL":"BR",ltr?"TL":"TR");
_31(ltr?"BR":"BL",ltr?"TR":"TL");
break;
case "above-alt":
ltr=!ltr;
case "above":
_31(ltr?"TL":"TR",ltr?"BL":"BR");
_31(ltr?"TR":"TL",ltr?"BR":"BL");
break;
default:
_31(pos.aroundCorner,pos.corner);
}
});
var _34=_8(_23,_30,_27,{w:_2e,h:_2f});
_34.aroundNodePos=_28;
return _34;
}});
});
