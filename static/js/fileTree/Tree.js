define([
"dojo/_base/array",
"dojo/_base/connect",
"dojo/_base/lang",
"dojo/_base/declare",
"dojo/on",
"dijit/Tree",
"dijit/form/CheckBox",
"fileTree/MixedCheckBox"],
function(array, connect, lang, declare, on, Tree, CheckBox, MixedCheckBox){

var _TreeNode = declare("fileTree._TreeNode", dijit._TreeNode, {

    _checkbox: null,

    _createCheckbox: function() {
        this._checkbox = new MixedCheckBox();
        this._checkbox.placeAt(this.expandoNode, "after");
        this._mixed = false;
        on(this._checkbox, "change", lang.hitch(this, this._onChange));

        // check lazy-loaded children of checked nodes
        connect.connect(this, "setChildItems", this, this._updateChildren);
    },

    postCreate: function() {
        this._createCheckbox();
        this.inherited(arguments);
    },

    _onChange: function(value){
        this._checkbox.value = value;
        value ? this.tree.onNodeChecked(this.item, this) : this.tree.onNodeUnchecked(this.item, this);
        this._updateParents();
        this._updateChildren();
    },

    _updateChildren: function() {
        // summary:
        //    Updates all children to the same checked value as this node.
        array.forEach(this.getChildren(), dojo.hitch(this, function(child, idx){
            child._checkbox.set("value", this._checkbox.get("value"));
            child._updateChildren();
        }));
    },

    _updateParents: function(){
        // summary:
        //     Updates the parents. Parents are checked if all children are
        //     checked otherwise unchecked.
        var parent = this.getParent();

        // in dojo 1.7, getParent just walks up the tree.
        // therefore check if parent is a tree node and not
        // just the tree isself.
        if(parent && parent.isTreeNode){
            var hasChecked = false;
            var hasUnchecked = false;
            var hasMixed = false;

            array.forEach(parent.getChildren(), function(child, idx){
                switch(child.getState()){
                    case "mixed":
                        hasMixed = true;
                        break;
                    case "checked":
                        hasChecked = true;
                        break;
                    case "unchecked":
                       hasUnchecked = true;
                       break;
                }
                if(hasMixed || (hasChecked && hasUnchecked)){
                    return false; // skip checking the rest
                }
            });

            parent._mixed = hasMixed || (hasChecked && hasUnchecked);
            parent._checkbox.state = parent._mixed ? "Mixed" : null;

            // using _set to bypass _onChange
            parent._checkbox._set("checked", parent._mixed ? false : this._checkbox.get("checked"));
            parent._checkbox._setStateClass();
            parent._updateParents();
        }
    },

    getState: function(){
        // summary:
        //     Get the current state of this node
        // returns:
        //     The state, checked, unchecked, or mixed.
        if(this._mixed){
            return 'mixed';
        }
        else{
            return this._checkbox.checked ? 'checked' : 'unchecked';
        }
    }
});

return declare("fileTree.Tree", Tree, {

    _createTreeNode: function( args ) {
        return new _TreeNode(args);
    },

    getChecked: function(){

        function _getChecked(/*fileTree._TreeNode*/node, /*Array*/ret){
            var state = node.getState();

            if(state === 'mixed'){
                var childrenLen = node.item.children.length;
                for(var i = 0; i < childrenLen; i++){

                    var child = node.item.children[i];
                    var nodes = tree._itemNodesMap[tree.model.getIdentity(child)];
                    var nodesLen = nodes.length;
                    for(var j = 0; j < nodesLen; j++){
                        _getChecked(nodes[j], ret);
                    }
                }
            }
            else if(state === 'checked'){
                ret.push(tree.model.getIdentity(node.item));
            }
            else{}
        }

        var checked = [];
        var tree = this;
        _getChecked(tree.rootNode, checked);
        return checked;
    },

    onNodeChecked: function(/*dojo.data.Item*/ storeItem, /*treeNode*/ nodeWidget){
    },

    onNodeUnchecked: function(/*dojo.data.Item*/ storeItem, /* treeNode */ nodeWidget){
    }
});

});

