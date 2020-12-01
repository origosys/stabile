define([
"dojo/_base/declare",
"dijit/form/FilteringSelect",
"dojo/text!./resources/DropDownBox.html"
], function(declare, FilteringSelect, template){

    return declare("steam2.FilteringSelectWithDeselect", [FilteringSelect], {

        templateString: template,

        postCreate: function(){
            this.inherited(arguments);
            this.connect(this.deselectNode, "onclick", "_onDeselectClick");
            this.toggleDeselectButton();
        },

        toggleDeselectButton: function(){
            if(this.value && !this.disabled){
                this.deselectNode.style.display = '';
            }
            else{
                this.deselectNode.style.display = 'none';
            }
        },

        _onDeselectClick: function(/* Event */ e){
            this.set('value', '');
        },

        _setValueAttr: function(val){
            this.inherited(arguments);
            this.toggleDeselectButton();
        },

        _setDisabledAttr: function(val){
            this.inherited(arguments);
            this.toggleDeselectButton();
        }
    });
});