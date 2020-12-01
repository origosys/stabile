//>>built
require({cache:{"url:dijit/templates/TreeNode.html":"<div class=\"dijitTreeNode\" role=\"presentation\"\n\t><div data-dojo-attach-point=\"rowNode\" class=\"dijitTreeRow\" role=\"presentation\" data-dojo-attach-event=\"onmouseenter:_onMouseEnter, onmouseleave:_onMouseLeave, onclick:_onClick, ondblclick:_onDblClick\"\n\t\t><img src=\"${_blankGif}\" alt=\"\" data-dojo-attach-point=\"expandoNode\" class=\"dijitTreeExpando\" role=\"presentation\"\n\t\t/><span data-dojo-attach-point=\"expandoNodeText\" class=\"dijitExpandoText\" role=\"presentation\"\n\t\t></span\n\t\t><span data-dojo-attach-point=\"contentNode\"\n\t\t\tclass=\"dijitTreeContent\" role=\"presentation\">\n\t\t\t<img src=\"${_blankGif}\" alt=\"\" data-dojo-attach-point=\"iconNode\" class=\"dijitIcon dijitTreeIcon\" role=\"presentation\"\n\t\t\t/><span data-dojo-attach-point=\"labelNode\" class=\"dijitTreeLabel\" role=\"treeitem\" tabindex=\"-1\" aria-selected=\"false\" data-dojo-attach-event=\"onfocus:_onLabelFocus\"></span>\n\t\t</span\n\t></div>\n\t<div data-dojo-attach-point=\"containerNode\" class=\"dijitTreeContainer\" role=\"presentation\" style=\"display: none;\"></div>\n</div>\n","url:dijit/templates/Tree.html":"<div class=\"dijitTree dijitTreeContainer\" role=\"tree\">\n\t<div class=\"dijitInline dijitTreeIndent\" style=\"position: absolute; top: -9999px\" data-dojo-attach-point=\"indentDetector\"></div>\n</div>\n"}});
define("dijit/Tree",["dojo/_base/array","dojo/_base/connect","dojo/cookie","dojo/_base/declare","dojo/_base/Deferred","dojo/DeferredList","dojo/dom","dojo/dom-class","dojo/dom-geometry","dojo/dom-style","dojo/_base/event","dojo/fx","dojo/_base/kernel","dojo/keys","dojo/_base/lang","dojo/on","dojo/topic","./focus","./registry","./_base/manager","./_Widget","./_TemplatedMixin","./_Container","./_Contained","./_CssStateMixin","dojo/text!./templates/TreeNode.html","dojo/text!./templates/Tree.html","./tree/TreeStoreModel","./tree/ForestStoreModel","./tree/_dndSelector"],function(_1,_2,_3,_4,_5,_6,_7,_8,_9,_a,_b,_c,_d,_e,_f,on,_10,_11,_12,_13,_14,_15,_16,_17,_18,_19,_1a,_1b,_1c,_1d){
var _1e=_4("dijit._TreeNode",[_14,_15,_16,_17,_18],{item:null,isTreeNode:true,label:"",_setLabelAttr:{node:"labelNode",type:"innerText"},isExpandable:null,isExpanded:false,state:"UNCHECKED",templateString:_19,baseClass:"dijitTreeNode",cssStateNodes:{rowNode:"dijitTreeRow",labelNode:"dijitTreeLabel"},_setTooltipAttr:{node:"rowNode",type:"attribute",attribute:"title"},buildRendering:function(){
this.inherited(arguments);
this._setExpando();
this._updateItemClasses(this.item);
if(this.isExpandable){
this.labelNode.setAttribute("aria-expanded",this.isExpanded);
}
this.setSelected(false);
},_setIndentAttr:function(_1f){
var _20=(Math.max(_1f,0)*this.tree._nodePixelIndent)+"px";
_a.set(this.domNode,"backgroundPosition",_20+" 0px");
_a.set(this.rowNode,this.isLeftToRight()?"paddingLeft":"paddingRight",_20);
_1.forEach(this.getChildren(),function(_21){
_21.set("indent",_1f+1);
});
this._set("indent",_1f);
},markProcessing:function(){
this.state="LOADING";
this._setExpando(true);
},unmarkProcessing:function(){
this._setExpando(false);
},_updateItemClasses:function(_22){
var _23=this.tree,_24=_23.model;
if(_23._v10Compat&&_22===_24.root){
_22=null;
}
this._applyClassAndStyle(_22,"icon","Icon");
this._applyClassAndStyle(_22,"label","Label");
this._applyClassAndStyle(_22,"row","Row");
},_applyClassAndStyle:function(_25,_26,_27){
var _28="_"+_26+"Class";
var _29=_26+"Node";
var _2a=this[_28];
this[_28]=this.tree["get"+_27+"Class"](_25,this.isExpanded);
_8.replace(this[_29],this[_28]||"",_2a||"");
_a.set(this[_29],this.tree["get"+_27+"Style"](_25,this.isExpanded)||{});
},_updateLayout:function(){
var _2b=this.getParent();
if(!_2b||!_2b.rowNode||_2b.rowNode.style.display=="none"){
_8.add(this.domNode,"dijitTreeIsRoot");
}else{
_8.toggle(this.domNode,"dijitTreeIsLast",!this.getNextSibling());
}
},_setExpando:function(_2c){
var _2d=["dijitTreeExpandoLoading","dijitTreeExpandoOpened","dijitTreeExpandoClosed","dijitTreeExpandoLeaf"],_2e=["*","-","+","*"],idx=_2c?0:(this.isExpandable?(this.isExpanded?1:2):3);
_8.replace(this.expandoNode,_2d[idx],_2d);
this.expandoNodeText.innerHTML=_2e[idx];
},expand:function(){
if(this._expandDeferred){
return this._expandDeferred;
}
this._wipeOut&&this._wipeOut.stop();
this.isExpanded=true;
this.labelNode.setAttribute("aria-expanded","true");
if(this.tree.showRoot||this!==this.tree.rootNode){
this.containerNode.setAttribute("role","group");
}
_8.add(this.contentNode,"dijitTreeContentExpanded");
this._setExpando();
this._updateItemClasses(this.item);
if(this==this.tree.rootNode){
this.tree.domNode.setAttribute("aria-expanded","true");
}
var def,_2f=_c.wipeIn({node:this.containerNode,duration:_13.defaultDuration,onEnd:function(){
def.callback(true);
}});
def=(this._expandDeferred=new _5(function(){
_2f.stop();
}));
_2f.play();
return def;
},collapse:function(){
if(!this.isExpanded){
return;
}
if(this._expandDeferred){
this._expandDeferred.cancel();
delete this._expandDeferred;
}
this.isExpanded=false;
this.labelNode.setAttribute("aria-expanded","false");
if(this==this.tree.rootNode){
this.tree.domNode.setAttribute("aria-expanded","false");
}
_8.remove(this.contentNode,"dijitTreeContentExpanded");
this._setExpando();
this._updateItemClasses(this.item);
if(!this._wipeOut){
this._wipeOut=_c.wipeOut({node:this.containerNode,duration:_13.defaultDuration});
}
this._wipeOut.play();
},indent:0,setChildItems:function(_30){
var _31=this.tree,_32=_31.model,_33=[];
_1.forEach(this.getChildren(),function(_34){
_16.prototype.removeChild.call(this,_34);
},this);
this.state="LOADED";
if(_30&&_30.length>0){
this.isExpandable=true;
_1.forEach(_30,function(_35){
var id=_32.getIdentity(_35),_36=_31._itemNodesMap[id],_37;
if(_36){
for(var i=0;i<_36.length;i++){
if(_36[i]&&!_36[i].getParent()){
_37=_36[i];
_37.set("indent",this.indent+1);
break;
}
}
}
if(!_37){
_37=this.tree._createTreeNode({item:_35,tree:_31,isExpandable:_32.mayHaveChildren(_35),label:_31.getLabel(_35),tooltip:_31.getTooltip(_35),dir:_31.dir,lang:_31.lang,textDir:_31.textDir,indent:this.indent+1});
if(_36){
_36.push(_37);
}else{
_31._itemNodesMap[id]=[_37];
}
}
this.addChild(_37);
if(this.tree.autoExpand||this.tree._state(_37)){
_33.push(_31._expandNode(_37));
}
},this);
_1.forEach(this.getChildren(),function(_38){
_38._updateLayout();
});
}else{
this.isExpandable=false;
}
if(this._setExpando){
this._setExpando(false);
}
this._updateItemClasses(this.item);
if(this==_31.rootNode){
var fc=this.tree.showRoot?this:this.getChildren()[0];
if(fc){
fc.setFocusable(true);
_31.lastFocused=fc;
}else{
_31.domNode.setAttribute("tabIndex","0");
}
}
return new _6(_33);
},getTreePath:function(){
var _39=this;
var _3a=[];
while(_39&&_39!==this.tree.rootNode){
_3a.unshift(_39.item);
_39=_39.getParent();
}
_3a.unshift(this.tree.rootNode.item);
return _3a;
},getIdentity:function(){
return this.tree.model.getIdentity(this.item);
},removeChild:function(_3b){
this.inherited(arguments);
var _3c=this.getChildren();
if(_3c.length==0){
this.isExpandable=false;
this.collapse();
}
_1.forEach(_3c,function(_3d){
_3d._updateLayout();
});
},makeExpandable:function(){
this.isExpandable=true;
this._setExpando(false);
},_onLabelFocus:function(){
this.tree._onNodeFocus(this);
},setSelected:function(_3e){
this.labelNode.setAttribute("aria-selected",_3e);
_8.toggle(this.rowNode,"dijitTreeRowSelected",_3e);
},setFocusable:function(_3f){
this.labelNode.setAttribute("tabIndex",_3f?"0":"-1");
},_onClick:function(evt){
this.tree._onClick(this,evt);
},_onDblClick:function(evt){
this.tree._onDblClick(this,evt);
},_onMouseEnter:function(evt){
this.tree._onNodeMouseEnter(this,evt);
},_onMouseLeave:function(evt){
this.tree._onNodeMouseLeave(this,evt);
},_setTextDirAttr:function(_40){
if(_40&&((this.textDir!=_40)||!this._created)){
this._set("textDir",_40);
this.applyTextDir(this.labelNode,this.labelNode.innerText||this.labelNode.textContent||"");
_1.forEach(this.getChildren(),function(_41){
_41.set("textDir",_40);
},this);
}
}});
var _42=_4("dijit.Tree",[_14,_15],{store:null,model:null,query:null,label:"",showRoot:true,childrenAttr:["children"],paths:[],path:[],selectedItems:null,selectedItem:null,openOnClick:false,openOnDblClick:false,templateString:_1a,persist:true,autoExpand:false,dndController:_1d,dndParams:["onDndDrop","itemCreator","onDndCancel","checkAcceptance","checkItemAcceptance","dragThreshold","betweenThreshold"],onDndDrop:null,itemCreator:null,onDndCancel:null,checkAcceptance:null,checkItemAcceptance:null,dragThreshold:5,betweenThreshold:0,_nodePixelIndent:19,_publish:function(_43,_44){
_10.publish(this.id,_f.mixin({tree:this,event:_43},_44||{}));
},postMixInProperties:function(){
this.tree=this;
if(this.autoExpand){
this.persist=false;
}
this._itemNodesMap={};
if(!this.cookieName&&this.id){
this.cookieName=this.id+"SaveStateCookie";
}
this._loadDeferred=new _5();
this.inherited(arguments);
},postCreate:function(){
this._initState();
var _45=this;
this._connects.push(on(this.domNode,on.selector(".dijitTreeNode","keypress"),function(evt){
_45._onKeyPress(_12.byNode(this),evt);
}),on(this.domNode,on.selector(".dijitTreeNode","keydown"),function(evt){
_45._onKeyDown(_12.byNode(this),evt);
}));
if(!this.model){
this._store2model();
}
this.connect(this.model,"onChange","_onItemChange");
this.connect(this.model,"onChildrenChange","_onItemChildrenChange");
this.connect(this.model,"onDelete","_onItemDelete");
this._load();
this.inherited(arguments);
if(this.dndController){
if(_f.isString(this.dndController)){
this.dndController=_f.getObject(this.dndController);
}
var _46={};
for(var i=0;i<this.dndParams.length;i++){
if(this[this.dndParams[i]]){
_46[this.dndParams[i]]=this[this.dndParams[i]];
}
}
this.dndController=new this.dndController(this,_46);
}
},_store2model:function(){
this._v10Compat=true;
_d.deprecated("Tree: from version 2.0, should specify a model object rather than a store/query");
var _47={id:this.id+"_ForestStoreModel",store:this.store,query:this.query,childrenAttrs:this.childrenAttr};
if(this.params.mayHaveChildren){
_47.mayHaveChildren=_f.hitch(this,"mayHaveChildren");
}
if(this.params.getItemChildren){
_47.getChildren=_f.hitch(this,function(_48,_49,_4a){
this.getItemChildren((this._v10Compat&&_48===this.model.root)?null:_48,_49,_4a);
});
}
this.model=new _1c(_47);
this.showRoot=Boolean(this.label);
},onLoad:function(){
},_load:function(){
this.model.getRoot(_f.hitch(this,function(_4b){
var rn=(this.rootNode=this.tree._createTreeNode({item:_4b,tree:this,isExpandable:true,label:this.label||this.getLabel(_4b),textDir:this.textDir,indent:this.showRoot?0:-1}));
if(!this.showRoot){
rn.rowNode.style.display="none";
this.domNode.setAttribute("role","presentation");
rn.labelNode.setAttribute("role","presentation");
rn.containerNode.setAttribute("role","tree");
}
this.domNode.appendChild(rn.domNode);
var _4c=this.model.getIdentity(_4b);
if(this._itemNodesMap[_4c]){
this._itemNodesMap[_4c].push(rn);
}else{
this._itemNodesMap[_4c]=[rn];
}
rn._updateLayout();
this._expandNode(rn).addCallback(_f.hitch(this,function(){
this._loadDeferred.callback(true);
this.onLoad();
}));
}),function(err){
console.error(this,": error loading root: ",err);
});
},getNodesByItem:function(_4d){
if(!_4d){
return [];
}
var _4e=_f.isString(_4d)?_4d:this.model.getIdentity(_4d);
return [].concat(this._itemNodesMap[_4e]);
},_setSelectedItemAttr:function(_4f){
this.set("selectedItems",[_4f]);
},_setSelectedItemsAttr:function(_50){
var _51=this;
this._loadDeferred.addCallback(_f.hitch(this,function(){
var _52=_1.map(_50,function(_53){
return (!_53||_f.isString(_53))?_53:_51.model.getIdentity(_53);
});
var _54=[];
_1.forEach(_52,function(id){
_54=_54.concat(_51._itemNodesMap[id]||[]);
});
this.set("selectedNodes",_54);
}));
},_setPathAttr:function(_55){
if(_55.length){
return this.set("paths",[_55]);
}else{
return this.set("paths",[]);
}
},_setPathsAttr:function(_56){
var _57=this;
return new _6(_1.map(_56,function(_58){
var d=new _5();
_58=_1.map(_58,function(_59){
return _f.isString(_59)?_59:_57.model.getIdentity(_59);
});
if(_58.length){
_57._loadDeferred.addCallback(function(){
_5a(_58,[_57.rootNode],d);
});
}else{
d.errback("Empty path");
}
return d;
})).addCallback(_5b);
function _5a(_5c,_5d,def){
var _5e=_5c.shift();
var _5f=_1.filter(_5d,function(_60){
return _60.getIdentity()==_5e;
})[0];
if(!!_5f){
if(_5c.length){
_57._expandNode(_5f).addCallback(function(){
_5a(_5c,_5f.getChildren(),def);
});
}else{
def.callback(_5f);
}
}else{
def.errback("Could not expand path at "+_5e);
}
};
function _5b(_61){
_57.set("selectedNodes",_1.map(_1.filter(_61,function(x){
return x[0];
}),function(x){
return x[1];
}));
};
},_setSelectedNodeAttr:function(_62){
this.set("selectedNodes",[_62]);
},_setSelectedNodesAttr:function(_63){
this._loadDeferred.addCallback(_f.hitch(this,function(){
this.dndController.setSelection(_63);
}));
},mayHaveChildren:function(){
},getItemChildren:function(){
},getLabel:function(_64){
return this.model.getLabel(_64);
},getIconClass:function(_65,_66){
return (!_65||this.model.mayHaveChildren(_65))?(_66?"dijitFolderOpened":"dijitFolderClosed"):"dijitLeaf";
},getLabelClass:function(){
},getRowClass:function(){
},getIconStyle:function(){
},getLabelStyle:function(){
},getRowStyle:function(){
},getTooltip:function(){
return "";
},_onKeyPress:function(_67,e){
if(e.charCode<=32){
return;
}
if(!e.altKey&&!e.ctrlKey&&!e.shiftKey&&!e.metaKey){
var c=String.fromCharCode(e.charCode);
this._onLetterKeyNav({node:_67,key:c.toLowerCase()});
_b.stop(e);
}
},_onKeyDown:function(_68,e){
var key=e.keyCode;
var map=this._keyHandlerMap;
if(!map){
map={};
map[_e.ENTER]="_onEnterKey";
map[_e.SPACE]=map[" "]="_onEnterKey";
map[this.isLeftToRight()?_e.LEFT_ARROW:_e.RIGHT_ARROW]="_onLeftArrow";
map[this.isLeftToRight()?_e.RIGHT_ARROW:_e.LEFT_ARROW]="_onRightArrow";
map[_e.UP_ARROW]="_onUpArrow";
map[_e.DOWN_ARROW]="_onDownArrow";
map[_e.HOME]="_onHomeKey";
map[_e.END]="_onEndKey";
this._keyHandlerMap=map;
}
if(this._keyHandlerMap[key]){
if(this._curSearch){
clearTimeout(this._curSearch.timer);
delete this._curSearch;
}
this[this._keyHandlerMap[key]]({node:_68,item:_68.item,evt:e});
_b.stop(e);
}
},_onEnterKey:function(_69){
this._publish("execute",{item:_69.item,node:_69.node});
this.dndController.userSelect(_69.node,_2.isCopyKey(_69.evt),_69.evt.shiftKey);
this.onClick(_69.item,_69.node,_69.evt);
},_onDownArrow:function(_6a){
var _6b=this._getNextNode(_6a.node);
if(_6b&&_6b.isTreeNode){
this.focusNode(_6b);
}
},_onUpArrow:function(_6c){
var _6d=_6c.node;
var _6e=_6d.getPreviousSibling();
if(_6e){
_6d=_6e;
while(_6d.isExpandable&&_6d.isExpanded&&_6d.hasChildren()){
var _6f=_6d.getChildren();
_6d=_6f[_6f.length-1];
}
}else{
var _70=_6d.getParent();
if(!(!this.showRoot&&_70===this.rootNode)){
_6d=_70;
}
}
if(_6d&&_6d.isTreeNode){
this.focusNode(_6d);
}
},_onRightArrow:function(_71){
var _72=_71.node;
if(_72.isExpandable&&!_72.isExpanded){
this._expandNode(_72);
}else{
if(_72.hasChildren()){
_72=_72.getChildren()[0];
if(_72&&_72.isTreeNode){
this.focusNode(_72);
}
}
}
},_onLeftArrow:function(_73){
var _74=_73.node;
if(_74.isExpandable&&_74.isExpanded){
this._collapseNode(_74);
}else{
var _75=_74.getParent();
if(_75&&_75.isTreeNode&&!(!this.showRoot&&_75===this.rootNode)){
this.focusNode(_75);
}
}
},_onHomeKey:function(){
var _76=this._getRootOrFirstNode();
if(_76){
this.focusNode(_76);
}
},_onEndKey:function(){
var _77=this.rootNode;
while(_77.isExpanded){
var c=_77.getChildren();
_77=c[c.length-1];
}
if(_77&&_77.isTreeNode){
this.focusNode(_77);
}
},multiCharSearchDuration:250,_onLetterKeyNav:function(_78){
var cs=this._curSearch;
if(cs){
cs.pattern=cs.pattern+_78.key;
clearTimeout(cs.timer);
}else{
cs=this._curSearch={pattern:_78.key,startNode:_78.node};
}
var _79=this;
cs.timer=setTimeout(function(){
delete _79._curSearch;
},this.multiCharSearchDuration);
var _7a=cs.startNode;
do{
_7a=this._getNextNode(_7a);
if(!_7a){
_7a=this._getRootOrFirstNode();
}
}while(_7a!==cs.startNode&&(_7a.label.toLowerCase().substr(0,cs.pattern.length)!=cs.pattern));
if(_7a&&_7a.isTreeNode){
if(_7a!==cs.startNode){
this.focusNode(_7a);
}
}
},isExpandoNode:function(_7b,_7c){
return _7.isDescendant(_7b,_7c.expandoNode);
},_onClick:function(_7d,e){
var _7e=e.target,_7f=this.isExpandoNode(_7e,_7d);
if((this.openOnClick&&_7d.isExpandable)||_7f){
if(_7d.isExpandable){
this._onExpandoClick({node:_7d});
}
}else{
this._publish("execute",{item:_7d.item,node:_7d,evt:e});
this.onClick(_7d.item,_7d,e);
this.focusNode(_7d);
}
_b.stop(e);
},_onDblClick:function(_80,e){
var _81=e.target,_82=(_81==_80.expandoNode||_81==_80.expandoNodeText);
if((this.openOnDblClick&&_80.isExpandable)||_82){
if(_80.isExpandable){
this._onExpandoClick({node:_80});
}
}else{
this._publish("execute",{item:_80.item,node:_80,evt:e});
this.onDblClick(_80.item,_80,e);
this.focusNode(_80);
}
_b.stop(e);
},_onExpandoClick:function(_83){
var _84=_83.node;
this.focusNode(_84);
if(_84.isExpanded){
this._collapseNode(_84);
}else{
this._expandNode(_84);
}
},onClick:function(){
},onDblClick:function(){
},onOpen:function(){
},onClose:function(){
},_getNextNode:function(_85){
if(_85.isExpandable&&_85.isExpanded&&_85.hasChildren()){
return _85.getChildren()[0];
}else{
while(_85&&_85.isTreeNode){
var _86=_85.getNextSibling();
if(_86){
return _86;
}
_85=_85.getParent();
}
return null;
}
},_getRootOrFirstNode:function(){
return this.showRoot?this.rootNode:this.rootNode.getChildren()[0];
},_collapseNode:function(_87){
if(_87._expandNodeDeferred){
delete _87._expandNodeDeferred;
}
if(_87.isExpandable){
if(_87.state=="LOADING"){
return;
}
_87.collapse();
this.onClose(_87.item,_87);
this._state(_87,false);
}
},_expandNode:function(_88,_89){
if(_88._expandNodeDeferred&&!_89){
return _88._expandNodeDeferred;
}
var _8a=this.model,_8b=_88.item,_8c=this;
switch(_88.state){
case "UNCHECKED":
_88.markProcessing();
var def=(_88._expandNodeDeferred=new _5());
_8a.getChildren(_8b,function(_8d){
_88.unmarkProcessing();
var _8e=_88.setChildItems(_8d);
var ed=_8c._expandNode(_88,true);
_8e.addCallback(function(){
ed.addCallback(function(){
def.callback();
});
});
},function(err){
console.error(_8c,": error loading root children: ",err);
});
break;
default:
def=(_88._expandNodeDeferred=_88.expand());
this.onOpen(_88.item,_88);
this._state(_88,true);
}
return def;
},focusNode:function(_8f){
_11.focus(_8f.labelNode);
},_onNodeFocus:function(_90){
if(_90&&_90!=this.lastFocused){
if(this.lastFocused&&!this.lastFocused._destroyed){
this.lastFocused.setFocusable(false);
}
_90.setFocusable(true);
this.lastFocused=_90;
}
},_onNodeMouseEnter:function(){
},_onNodeMouseLeave:function(){
},_onItemChange:function(_91){
var _92=this.model,_93=_92.getIdentity(_91),_94=this._itemNodesMap[_93];
if(_94){
var _95=this.getLabel(_91),_96=this.getTooltip(_91);
_1.forEach(_94,function(_97){
_97.set({item:_91,label:_95,tooltip:_96});
_97._updateItemClasses(_91);
});
}
},_onItemChildrenChange:function(_98,_99){
var _9a=this.model,_9b=_9a.getIdentity(_98),_9c=this._itemNodesMap[_9b];
if(_9c){
_1.forEach(_9c,function(_9d){
_9d.setChildItems(_99);
});
}
},_onItemDelete:function(_9e){
var _9f=this.model,_a0=_9f.getIdentity(_9e),_a1=this._itemNodesMap[_a0];
if(_a1){
_1.forEach(_a1,function(_a2){
this.dndController.removeTreeNode(_a2);
var _a3=_a2.getParent();
if(_a3){
_a3.removeChild(_a2);
}
_a2.destroyRecursive();
},this);
delete this._itemNodesMap[_a0];
}
},_initState:function(){
this._openedNodes={};
if(this.persist&&this.cookieName){
var _a4=_3(this.cookieName);
if(_a4){
_1.forEach(_a4.split(","),function(_a5){
this._openedNodes[_a5]=true;
},this);
}
}
},_state:function(_a6,_a7){
if(!this.persist){
return false;
}
var _a8=_1.map(_a6.getTreePath(),function(_a9){
return this.model.getIdentity(_a9);
},this).join("/");
if(arguments.length===1){
return this._openedNodes[_a8];
}else{
if(_a7){
this._openedNodes[_a8]=true;
}else{
delete this._openedNodes[_a8];
}
var ary=[];
for(var id in this._openedNodes){
ary.push(id);
}
_3(this.cookieName,ary.join(","),{expires:365});
}
},destroy:function(){
if(this._curSearch){
clearTimeout(this._curSearch.timer);
delete this._curSearch;
}
if(this.rootNode){
this.rootNode.destroyRecursive();
}
if(this.dndController&&!_f.isString(this.dndController)){
this.dndController.destroy();
}
this.rootNode=null;
this.inherited(arguments);
},destroyRecursive:function(){
this.destroy();
},resize:function(_aa){
if(_aa){
_9.setMarginBox(this.domNode,_aa);
}
this._nodePixelIndent=_9.position(this.tree.indentDetector).w;
if(this.tree.rootNode){
this.tree.rootNode.set("indent",this.showRoot?0:-1);
}
},_createTreeNode:function(_ab){
return new _1e(_ab);
},_setTextDirAttr:function(_ac){
if(_ac&&this.textDir!=_ac){
this._set("textDir",_ac);
this.rootNode.set("textDir",_ac);
}
}});
_42._TreeNode=_1e;
return _42;
});
