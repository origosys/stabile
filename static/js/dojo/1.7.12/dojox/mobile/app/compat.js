/*
	Copyright (c) 2004-2011, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/

/*
	This is an optimized version of Dojo, built for deployment and not for
	development. To get sources and documentation, please visit:

		http://dojotoolkit.org
*/

//>>built
require({cache:{"dijit/main":function(){define("dijit/main",["dojo/_base/kernel"],function(_1){return _1.dijit;});},"dojox/main":function(){define("dojox/main",["dojo/_base/kernel"],function(_2){return _2.dojox;});},"dojox/mobile/compat":function(){define("dojox/mobile/compat",["dojo/_base/lang","dojo/_base/sniff"],function(_3,_4){var dm=_3.getObject("dojox.mobile",true);if(!_4("webkit")){var s="dojox/mobile/_compat";require([s]);}return dm;});}}});define("dojox/mobile/app/compat",["dojo","dijit","dojox","dojo/require!dojox/mobile/compat"],function(_5,_6,_7){_5.provide("dojox.mobile.app.compat");_5.require("dojox.mobile.compat");_5.extend(_7.mobile.app.AlertDialog,{_doTransition:function(_8){var h=_5.marginBox(this.domNode.firstChild).h;var _9=this.controller.getWindowSize().h;var _a=_9-h;var _b=_9;var _c=_5.fx.slideTo({node:this.domNode,duration:400,top:{start:_8<0?_a:_b,end:_8<0?_b:_a}});var _d=_5[_8<0?"fadeOut":"fadeIn"]({node:this.mask,duration:400});var _e=_5.fx.combine([_c,_d]);var _f=this;_5.connect(_e,"onEnd",this,function(){if(_8<0){_f.domNode.style.display="none";_5.destroy(_f.domNode);_5.destroy(_f.mask);}});_e.play();}});_5.extend(_7.mobile.app.List,{deleteRow:function(){var row=this._selectedRow;_5.style(row,{visibility:"hidden",minHeight:"0px"});_5.removeClass(row,"hold");var _10=_5.contentBox(row).h;_5.animateProperty({node:row,duration:800,properties:{height:{start:_10,end:1},paddingTop:{end:0},paddingBottom:{end:0}},onEnd:this._postDeleteAnim}).play();}});if(_7.mobile.app.ImageView&&!_5.create("canvas").getContext){_5.extend(_7.mobile.app.ImageView,{buildRendering:function(){this.domNode.innerHTML="ImageView widget is not supported on this browser."+"Please try again with a modern browser, e.g. "+"Safari, Chrome or Firefox";this.canvas={};},postCreate:function(){}});}if(_7.mobile.app.ImageThumbView){_5.extend(_7.mobile.app.ImageThumbView,{place:function(_11,x,y){_5.style(_11,{top:y+"px",left:x+"px",visibility:"visible"});}});}});