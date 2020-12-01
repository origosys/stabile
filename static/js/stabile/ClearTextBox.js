define([
'dojo/_base/declare',
'dijit/form/TextBox'
], function(declare, TextBox){

    var ClearTextBox = declare('stabile.ClearTextBox', TextBox, {

        // The "Delete" word
        deleteText: "",

        // Fire the change event for every text change
        intermediateChanges: true,

        // PostCreate method
        // Fires *after* nodes are created, before rendered to screen
        postCreate: function() {
            // Do what the previous does with this method
            this.inherited(arguments);

            // Add widget class to the domNode
            var domNode = this.domNode;
            dojo.addClass(domNode, "stabileClearBox");

            // Create the "X" link
            this.clearLink = dojo.create("a", {
                className: "stabileClear",
                innerHTML: this.deleteText
            }, domNode, "first");

            // Fix the width
            var startWidth = dojo.style(domNode, "width"),
                    pad = dojo.style(this.domNode,"paddingRight");
            dojo.style(domNode, "width", (startWidth - pad) + "px");

            // Add click event to focus node
            this.connect(this.clearLink, "onclick", function(){
                // Clear the value
                this.set("value", "");
                // Focus on the node, not the link
                this.textbox.blur();
            });

            // Add intermediate change for self so that "X" hides when no value
            this.connect(this, "onChange", "checkValue");

            // Check value right away, hide link if necessary
            this.checkValue();
        },

        checkValue: function(value) {
            dojo[(value != "" && value != undefined ? "remove" : "add") + "Class"](this.clearLink, "dijitHidden");
        }
    });

});
