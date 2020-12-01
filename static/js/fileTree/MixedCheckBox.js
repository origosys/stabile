define([
    'dojo/_base/declare', 
    'dijit/form/CheckBox'], 
function(declare, CheckBox){

    return declare('fileTree.MixedCheckBox', CheckBox, {
        // baseClass: [protected] String
    	//		Root CSS class of the widget (ex: mixedCheckBox), used to add CSS classes of widget
    	//		(ex: "mixedCheckBox mixedCheckBoxChecked mixedCheckBoxFocused mixedCheckBoxMixed")
    	//		See _setStateClass().
        baseClass: 'mixedCheckBox'
    });
});


