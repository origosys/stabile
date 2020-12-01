/*
	Copyright (c) 2004-2011, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/

//>>built
define("dojo/selector/acme",["../_base/kernel","../has","../dom","../_base/sniff","../_base/array","../_base/lang","../_base/window"],function(_1,_2,_3){
var _4=_1.trim;
var _5=_1.forEach;
var _6=function(){
return _1.doc;
};
var _7=(_6().compatMode)=="BackCompat";
var _8=">~+";
var _9=false;
var _a=function(){
return true;
};
var _b=function(_c){
if(_8.indexOf(_c.slice(-1))>=0){
_c+=" * ";
}else{
_c+=" ";
}
var ts=function(s,e){
return _4(_c.slice(s,e));
};
var _d=[];
var _e=-1,_f=-1,_10=-1,_11=-1,_12=-1,_13=-1,_14=-1,_15,lc="",cc="",_16;
var x=0,ql=_c.length,_17=null,_18=null;
var _19=function(){
if(_14>=0){
var tv=(_14==x)?null:ts(_14,x);
_17[(_8.indexOf(tv)<0)?"tag":"oper"]=tv;
_14=-1;
}
};
var _1a=function(){
if(_13>=0){
_17.id=ts(_13,x).replace(/\\/g,"");
_13=-1;
}
};
var _1b=function(){
if(_12>=0){
_17.classes.push(ts(_12+1,x).replace(/\\/g,""));
_12=-1;
}
};
var _1c=function(){
_1a();
_19();
_1b();
};
var _1d=function(){
_1c();
if(_11>=0){
_17.pseudos.push({name:ts(_11+1,x)});
}
_17.loops=(_17.pseudos.length||_17.attrs.length||_17.classes.length);
_17.oquery=_17.query=ts(_16,x);
_17.otag=_17.tag=(_17["oper"])?null:(_17.tag||"*");
if(_17.tag){
_17.tag=_17.tag.toUpperCase();
}
if(_d.length&&(_d[_d.length-1].oper)){
_17.infixOper=_d.pop();
_17.query=_17.infixOper.query+" "+_17.query;
}
_d.push(_17);
_17=null;
};
for(;lc=cc,cc=_c.charAt(x),x<ql;x++){
if(lc=="\\"){
continue;
}
if(!_17){
_16=x;
_17={query:null,pseudos:[],attrs:[],classes:[],tag:null,oper:null,id:null,getTag:function(){
return _9?this.otag:this.tag;
}};
_14=x;
}
if(_15){
if(cc==_15){
_15=null;
}
continue;
}else{
if(cc=="'"||cc=="\""){
_15=cc;
continue;
}
}
if(_e>=0){
if(cc=="]"){
if(!_18.attr){
_18.attr=ts(_e+1,x);
}else{
_18.matchFor=ts((_10||_e+1),x);
}
var cmf=_18.matchFor;
if(cmf){
if((cmf.charAt(0)=="\"")||(cmf.charAt(0)=="'")){
_18.matchFor=cmf.slice(1,-1);
}
}
if(_18.matchFor){
_18.matchFor=_18.matchFor.replace(/\\/g,"");
}
_17.attrs.push(_18);
_18=null;
_e=_10=-1;
}else{
if(cc=="="){
var _1e=("|~^$*".indexOf(lc)>=0)?lc:"";
_18.type=_1e+cc;
_18.attr=ts(_e+1,x-_1e.length);
_10=x+1;
}
}
}else{
if(_f>=0){
if(cc==")"){
if(_11>=0){
_18.value=ts(_f+1,x);
}
_11=_f=-1;
}
}else{
if(cc=="#"){
_1c();
_13=x+1;
}else{
if(cc=="."){
_1c();
_12=x;
}else{
if(cc==":"){
_1c();
_11=x;
}else{
if(cc=="["){
_1c();
_e=x;
_18={};
}else{
if(cc=="("){
if(_11>=0){
_18={name:ts(_11+1,x),value:null};
_17.pseudos.push(_18);
}
_f=x;
}else{
if((cc==" ")&&(lc!=cc)){
_1d();
}
}
}
}
}
}
}
}
}
return _d;
};
var _1f=function(_20,_21){
if(!_20){
return _21;
}
if(!_21){
return _20;
}
return function(){
return _20.apply(window,arguments)&&_21.apply(window,arguments);
};
};
var _22=function(i,arr){
var r=arr||[];
if(i){
r.push(i);
}
return r;
};
var _23=function(n){
return (1==n.nodeType);
};
var _24="";
var _25=function(_26,_27){
if(!_26){
return _24;
}
if(_27=="class"){
return _26.className||_24;
}
if(_27=="for"){
return _26.htmlFor||_24;
}
if(_27=="style"){
return _26.style.cssText||_24;
}
return (_9?_26.getAttribute(_27):_26.getAttribute(_27,2))||_24;
};
var _28={"*=":function(_29,_2a){
return function(_2b){
return (_25(_2b,_29).indexOf(_2a)>=0);
};
},"^=":function(_2c,_2d){
return function(_2e){
return (_25(_2e,_2c).indexOf(_2d)==0);
};
},"$=":function(_2f,_30){
return function(_31){
var ea=" "+_25(_31,_2f);
var _32=ea.lastIndexOf(_30);
return _32>-1&&(_32==(ea.length-_30.length));
};
},"~=":function(_33,_34){
var _35=" "+_34+" ";
return function(_36){
var ea=" "+_25(_36,_33)+" ";
return (ea.indexOf(_35)>=0);
};
},"|=":function(_37,_38){
var _39=_38+"-";
return function(_3a){
var ea=_25(_3a,_37);
return ((ea==_38)||(ea.indexOf(_39)==0));
};
},"=":function(_3b,_3c){
return function(_3d){
return (_25(_3d,_3b)==_3c);
};
}};
var _3e=_6().documentElement;
var _3f=!(_3e.nextElementSibling||"nextElementSibling" in _3e);
var _40=!_3f?"nextElementSibling":"nextSibling";
var _41=!_3f?"previousElementSibling":"previousSibling";
var _42=(_3f?_23:_a);
var _43=function(_44){
while(_44=_44[_41]){
if(_42(_44)){
return false;
}
}
return true;
};
var _45=function(_46){
while(_46=_46[_40]){
if(_42(_46)){
return false;
}
}
return true;
};
var _47=function(_48){
var _49=_48.parentNode;
var i=0,_4a=_49.children||_49.childNodes,ci=(_48["_i"]||-1),cl=(_49["_l"]||-1);
if(!_4a){
return -1;
}
var l=_4a.length;
if(cl==l&&ci>=0&&cl>=0){
return ci;
}
_49["_l"]=l;
ci=-1;
for(var te=_49["firstElementChild"]||_49["firstChild"];te;te=te[_40]){
if(_42(te)){
te["_i"]=++i;
if(_48===te){
ci=i;
}
}
}
return ci;
};
var _4b=function(_4c){
return !((_47(_4c))%2);
};
var _4d=function(_4e){
return ((_47(_4e))%2);
};
var _4f={"checked":function(_50,_51){
return function(_52){
return !!("checked" in _52?_52.checked:_52.selected);
};
},"first-child":function(){
return _43;
},"last-child":function(){
return _45;
},"only-child":function(_53,_54){
return function(_55){
return _43(_55)&&_45(_55);
};
},"empty":function(_56,_57){
return function(_58){
var cn=_58.childNodes;
var cnl=_58.childNodes.length;
for(var x=cnl-1;x>=0;x--){
var nt=cn[x].nodeType;
if((nt===1)||(nt==3)){
return false;
}
}
return true;
};
},"disabled":function(_59,_5a){
return function(_5b){
return _5b.disabled;
};
},"enabled":function(_5c,_5d){
return function(_5e){
return !_5e.disabled;
};
},"contains":function(_5f,_60){
var cz=_60.charAt(0);
if(cz=="\""||cz=="'"){
_60=_60.slice(1,-1);
}
return function(_61){
return (_61.innerHTML.indexOf(_60)>=0);
};
},"not":function(_62,_63){
var p=_b(_63)[0];
var _64={el:1};
if(p.tag!="*"){
_64.tag=1;
}
if(!p.classes.length){
_64.classes=1;
}
var ntf=_65(p,_64);
return function(_66){
return (!ntf(_66));
};
},"nth-child":function(_67,_68){
var pi=parseInt;
if(_68=="odd"){
return _4d;
}else{
if(_68=="even"){
return _4b;
}
}
if(_68.indexOf("n")!=-1){
var _69=_68.split("n",2);
var _6a=_69[0]?((_69[0]=="-")?-1:pi(_69[0])):1;
var idx=_69[1]?pi(_69[1]):0;
var lb=0,ub=-1;
if(_6a>0){
if(idx<0){
idx=(idx%_6a)&&(_6a+(idx%_6a));
}else{
if(idx>0){
if(idx>=_6a){
lb=idx-idx%_6a;
}
idx=idx%_6a;
}
}
}else{
if(_6a<0){
_6a*=-1;
if(idx>0){
ub=idx;
idx=idx%_6a;
}
}
}
if(_6a>0){
return function(_6b){
var i=_47(_6b);
return (i>=lb)&&(ub<0||i<=ub)&&((i%_6a)==idx);
};
}else{
_68=idx;
}
}
var _6c=pi(_68);
return function(_6d){
return (_47(_6d)==_6c);
};
}};
var _6e=(_1.isIE<9||_1.isIE==9&&_1.isQuirks)?function(_6f){
var clc=_6f.toLowerCase();
if(clc=="class"){
_6f="className";
}
return function(_70){
return (_9?_70.getAttribute(_6f):_70[_6f]||_70[clc]);
};
}:function(_71){
return function(_72){
return (_72&&_72.getAttribute&&_72.hasAttribute(_71));
};
};
var _65=function(_73,_74){
if(!_73){
return _a;
}
_74=_74||{};
var ff=null;
if(!("el" in _74)){
ff=_1f(ff,_23);
}
if(!("tag" in _74)){
if(_73.tag!="*"){
ff=_1f(ff,function(_75){
return (_75&&(_75.tagName==_73.getTag()));
});
}
}
if(!("classes" in _74)){
_5(_73.classes,function(_76,idx,arr){
var re=new RegExp("(?:^|\\s)"+_76+"(?:\\s|$)");
ff=_1f(ff,function(_77){
return re.test(_77.className);
});
ff.count=idx;
});
}
if(!("pseudos" in _74)){
_5(_73.pseudos,function(_78){
var pn=_78.name;
if(_4f[pn]){
ff=_1f(ff,_4f[pn](pn,_78.value));
}
});
}
if(!("attrs" in _74)){
_5(_73.attrs,function(_79){
var _7a;
var a=_79.attr;
if(_79.type&&_28[_79.type]){
_7a=_28[_79.type](a,_79.matchFor);
}else{
if(a.length){
_7a=_6e(a);
}
}
if(_7a){
ff=_1f(ff,_7a);
}
});
}
if(!("id" in _74)){
if(_73.id){
ff=_1f(ff,function(_7b){
return (!!_7b&&(_7b.id==_73.id));
});
}
}
if(!ff){
if(!("default" in _74)){
ff=_a;
}
}
return ff;
};
var _7c=function(_7d){
return function(_7e,ret,bag){
while(_7e=_7e[_40]){
if(_3f&&(!_23(_7e))){
continue;
}
if((!bag||_7f(_7e,bag))&&_7d(_7e)){
ret.push(_7e);
}
break;
}
return ret;
};
};
var _80=function(_81){
return function(_82,ret,bag){
var te=_82[_40];
while(te){
if(_42(te)){
if(bag&&!_7f(te,bag)){
break;
}
if(_81(te)){
ret.push(te);
}
}
te=te[_40];
}
return ret;
};
};
var _83=function(_84){
_84=_84||_a;
return function(_85,ret,bag){
var te,x=0,_86=_85.children||_85.childNodes;
while(te=_86[x++]){
if(_42(te)&&(!bag||_7f(te,bag))&&(_84(te,x))){
ret.push(te);
}
}
return ret;
};
};
var _87=function(_88,_89){
var pn=_88.parentNode;
while(pn){
if(pn==_89){
break;
}
pn=pn.parentNode;
}
return !!pn;
};
var _8a={};
var _8b=function(_8c){
var _8d=_8a[_8c.query];
if(_8d){
return _8d;
}
var io=_8c.infixOper;
var _8e=(io?io.oper:"");
var _8f=_65(_8c,{el:1});
var qt=_8c.tag;
var _90=("*"==qt);
var ecs=_6()["getElementsByClassName"];
if(!_8e){
if(_8c.id){
_8f=(!_8c.loops&&_90)?_a:_65(_8c,{el:1,id:1});
_8d=function(_91,arr){
var te=_3.byId(_8c.id,(_91.ownerDocument||_91));
if(!te||!_8f(te)){
return;
}
if(9==_91.nodeType){
return _22(te,arr);
}else{
if(_87(te,_91)){
return _22(te,arr);
}
}
};
}else{
if(ecs&&/\{\s*\[native code\]\s*\}/.test(String(ecs))&&_8c.classes.length&&!_7){
_8f=_65(_8c,{el:1,classes:1,id:1});
var _92=_8c.classes.join(" ");
_8d=function(_93,arr,bag){
var ret=_22(0,arr),te,x=0;
var _94=_93.getElementsByClassName(_92);
while((te=_94[x++])){
if(_8f(te,_93)&&_7f(te,bag)){
ret.push(te);
}
}
return ret;
};
}else{
if(!_90&&!_8c.loops){
_8d=function(_95,arr,bag){
var ret=_22(0,arr),te,x=0;
var _96=_95.getElementsByTagName(_8c.getTag());
while((te=_96[x++])){
if(_7f(te,bag)){
ret.push(te);
}
}
return ret;
};
}else{
_8f=_65(_8c,{el:1,tag:1,id:1});
_8d=function(_97,arr,bag){
var ret=_22(0,arr),te,x=0;
var _98=_97.getElementsByTagName(_8c.getTag());
while((te=_98[x++])){
if(_8f(te,_97)&&_7f(te,bag)){
ret.push(te);
}
}
return ret;
};
}
}
}
}else{
var _99={el:1};
if(_90){
_99.tag=1;
}
_8f=_65(_8c,_99);
if("+"==_8e){
_8d=_7c(_8f);
}else{
if("~"==_8e){
_8d=_80(_8f);
}else{
if(">"==_8e){
_8d=_83(_8f);
}
}
}
}
return _8a[_8c.query]=_8d;
};
var _9a=function(_9b,_9c){
var _9d=_22(_9b),qp,x,te,qpl=_9c.length,bag,ret;
for(var i=0;i<qpl;i++){
ret=[];
qp=_9c[i];
x=_9d.length-1;
if(x>0){
bag={};
ret.nozip=true;
}
var gef=_8b(qp);
for(var j=0;(te=_9d[j]);j++){
gef(te,ret,bag);
}
if(!ret.length){
break;
}
_9d=ret;
}
return ret;
};
var _9e={},_9f={};
var _a0=function(_a1){
var _a2=_b(_4(_a1));
if(_a2.length==1){
var tef=_8b(_a2[0]);
return function(_a3){
var r=tef(_a3,[]);
if(r){
r.nozip=true;
}
return r;
};
}
return function(_a4){
return _9a(_a4,_a2);
};
};
var nua=navigator.userAgent;
var wk="WebKit/";
var _a5=(_1.isWebKit&&(nua.indexOf(wk)>0)&&(parseFloat(nua.split(wk)[1])>528));
var _a6=_1.isIE?"commentStrip":"nozip";
var qsa="querySelectorAll";
var _a7=(!!_6()[qsa]&&(!_1.isSafari||(_1.isSafari>3.1)||_a5));
var _a8=/\\[>~+]|n\+\d|([^ \\])?([>~+])([^ =])?/g;
var _a9=function(_aa,pre,ch,_ab){
return ch?(pre?pre+" ":"")+ch+(_ab?" "+_ab:""):_aa;
};
var _ac=/([^[]*)([^\]]*])?/g;
var _ad=function(_ae,_af,att){
return _af.replace(_a8,_a9)+(att||"");
};
var _b0=function(_b1,_b2){
_b1=_b1.replace(_ac,_ad);
if(_a7){
var _b3=_9f[_b1];
if(_b3&&!_b2){
return _b3;
}
}
var _b4=_9e[_b1];
if(_b4){
return _b4;
}
var qcz=_b1.charAt(0);
var _b5=(-1==_b1.indexOf(" "));
if((_b1.indexOf("#")>=0)&&(_b5)){
_b2=true;
}
var _b6=(_a7&&(!_b2)&&(_8.indexOf(qcz)==-1)&&(!_1.isIE||(_b1.indexOf(":")==-1))&&(!(_7&&(_b1.indexOf(".")>=0)))&&(_b1.indexOf(":contains")==-1)&&(_b1.indexOf(":checked")==-1)&&(_b1.indexOf("|=")==-1));
if(_b6){
var tq=(_8.indexOf(_b1.charAt(_b1.length-1))>=0)?(_b1+" *"):_b1;
return _9f[_b1]=function(_b7){
try{
if(!((9==_b7.nodeType)||_b5)){
throw "";
}
var r=_b7[qsa](tq);
r[_a6]=true;
return r;
}
catch(e){
return _b0(_b1,true)(_b7);
}
};
}else{
var _b8=_b1.match(/([^\s,](?:"(?:\\.|[^"])+"|'(?:\\.|[^'])+'|[^,])*)/g);
return _9e[_b1]=((_b8.length<2)?_a0(_b1):function(_b9){
var _ba=0,ret=[],tp;
while((tp=_b8[_ba++])){
ret=ret.concat(_a0(tp)(_b9));
}
return ret;
});
}
};
var _bb=0;
var _bc=_1.isIE?function(_bd){
if(_9){
return (_bd.getAttribute("_uid")||_bd.setAttribute("_uid",++_bb)||_bb);
}else{
return _bd.uniqueID;
}
}:function(_be){
return (_be._uid||(_be._uid=++_bb));
};
var _7f=function(_bf,bag){
if(!bag){
return 1;
}
var id=_bc(_bf);
if(!bag[id]){
return bag[id]=1;
}
return 0;
};
var _c0="_zipIdx";
var _c1=function(arr){
if(arr&&arr.nozip){
return arr;
}
var ret=[];
if(!arr||!arr.length){
return ret;
}
if(arr[0]){
ret.push(arr[0]);
}
if(arr.length<2){
return ret;
}
_bb++;
if(_1.isIE&&_9){
var _c2=_bb+"";
arr[0].setAttribute(_c0,_c2);
for(var x=1,te;te=arr[x];x++){
if(arr[x].getAttribute(_c0)!=_c2){
ret.push(te);
}
te.setAttribute(_c0,_c2);
}
}else{
if(_1.isIE&&arr.commentStrip){
try{
for(var x=1,te;te=arr[x];x++){
if(_23(te)){
ret.push(te);
}
}
}
catch(e){
}
}else{
if(arr[0]){
arr[0][_c0]=_bb;
}
for(var x=1,te;te=arr[x];x++){
if(arr[x][_c0]!=_bb){
ret.push(te);
}
te[_c0]=_bb;
}
}
}
return ret;
};
var _c3=function(_c4,_c5){
_c5=_c5||_6();
var od=_c5.ownerDocument||_c5;
_9=(od.createElement("div").tagName==="div");
var r=_b0(_c4)(_c5);
if(r&&r.nozip){
return r;
}
return _c1(r);
};
_c3.filter=function(_c6,_c7,_c8){
var _c9=[],_ca=_b(_c7),_cb=(_ca.length==1&&!/[^\w#\.]/.test(_c7))?_65(_ca[0]):function(_cc){
return _1.query(_c7,_c8).indexOf(_cc)!=-1;
};
for(var x=0,te;te=_c6[x];x++){
if(_cb(te)){
_c9.push(te);
}
}
return _c9;
};
return _c3;
});
