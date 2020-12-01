//>>built
define("dijit/form/_ExpandingTextAreaMixin",["dojo/_base/declare","dojo/dom-construct","dojo/_base/lang","dojo/_base/window"],function(_1,_2,_3,_4){
var _5;
return _1("dijit.form._ExpandingTextAreaMixin",null,{_setValueAttr:function(){
this.inherited(arguments);
this.resize();
},postCreate:function(){
this.inherited(arguments);
var _6=this.textbox;
if(_5==undefined){
var te=_2.create("textarea",{rows:"5",cols:"20",value:" ",style:{zoom:1,fontSize:"12px",height:"96px",overflow:"hidden",visibility:"hidden",position:"absolute",border:"5px solid white",margin:"0",padding:"0",boxSizing:"border-box",MsBoxSizing:"border-box",WebkitBoxSizing:"border-box",MozBoxSizing:"border-box"}},_4.body(),"last");
_5=te.scrollHeight>=te.clientHeight;
_4.body().removeChild(te);
}
this.connect(_6,"onresize","_resizeLater");
this.connect(_6,"onfocus","_resizeLater");
_6.style.overflowY="hidden";
},startup:function(){
this.inherited(arguments);
this._resizeLater();
},_onInput:function(e){
this.inherited(arguments);
this.resize();
},_estimateHeight:function(){
var _7=this.textbox;
_7.rows=(_7.value.match(/\n/g)||[]).length+1;
},_resizeLater:function(){
this.defer("resize");
},resize:function(){
var _8=this.textbox;
function _9(){
var _a=false;
if(_8.value===""){
_8.value=" ";
_a=true;
}
var sh=_8.scrollHeight;
if(_a){
_8.value="";
}
return sh;
};
if(_8.style.overflowY=="hidden"){
_8.scrollTop=0;
}
if(this.busyResizing){
return;
}
this.busyResizing=true;
if(_9()||_8.offsetHeight){
var _b=_9()+Math.max(_8.offsetHeight-_8.clientHeight,0);
var _c=_b+"px";
if(_c!=_8.style.height){
_8.style.height=_c;
_8.rows=1;
}
if(_5){
var _d=_9(),_e=_d,_f=_8.style.minHeight,_10=4,_11,_12=_8.scrollTop;
_8.style.minHeight=_c;
_8.style.height="auto";
while(_b>0){
_8.style.minHeight=Math.max(_b-_10,4)+"px";
_11=_9();
var _13=_e-_11;
_b-=_13;
if(_13<_10){
break;
}
_e=_11;
_10<<=1;
}
_8.style.height=_b+"px";
_8.style.minHeight=_f;
_8.scrollTop=_12;
}
_8.style.overflowY=_9()>_8.clientHeight?"auto":"hidden";
if(_8.style.overflowY=="hidden"){
_8.scrollTop=0;
}
}else{
this._estimateHeight();
}
this.busyResizing=false;
}});
});
