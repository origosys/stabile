define([
"dojo/_base/declare",
"dojo/_base/array",
"dojo/_base/lang",
"dojo/_base/connect",
"dojo/cache",
"dojo/string",
"dojo/query",
"dojox/grid/DataGrid",
"dojox/lang/functional",
"dojox/lang/functional/fold",
"dijit/Dialog",
"dijit/form/CheckBox",
"dijit/form/TextBox",
"dijit/form/Button",
"steam2/user",
"steam2/statusColorMap"
], function(declare, arrayUtil, lang, connect, cache, string, query, DataGrid, funcUtil, _fold, Dialog, CheckBox, TextBox, Button, user, statusColorMap){

var ActionGrid = declare('steam2.ActionGrid', DataGrid, {

    store: null,
    model: null,

    queryOptions: {
        jsonQuery: true
    },

    gridId: null,

    widgetsInTemplate: true,

    // NOTE: watch out changing this to extended
    // since additional row clicks does not trigger onSelected!?!
    selectionMode: 'multiple',

    templateString: dojo.cache('steam2','resources/_Grid.html'),

    searchPlaceholder: 'Type to search',

    constructor: function(args){
        // enable reflective lookup of grids...
        ActionGrid.grids.push(this);
        this.gridId = ActionGrid.gridId;
        ActionGrid.gridId++;

        // on every fetch update the bulk info.
        connect.connect(this, '_onFetchComplete', this, function(){
            this.setBulkInfo();
        });

    },

    _onRevert: function(){
        this.selection.deselectAll();
        this._selectAllCheckBox.checked = false;

        // NOTE: when the running filter is selected
        // dojo tries to fetch those items by issuing a request at
        // servers.cgi/[?status~'running'][:25]
        // and that is not supported by the backend.

        // we remove the query, thereby fetching all items
        // and filtering them client side afterwards.

        // NOTE: the client side filtering is because the store
        // uses ClientFilter and caching.
        this.query = "";
        var h = connect.connect(this, "_onFetchComplete", this, function(){
            connect.disconnect(h);
            this.filter(this._toJsonQuery(), true);
        });
        this.inherited(arguments);
    },


    _getHeaderHeight: function(){
        // Overwritten method that adds the height of the search node.
        /* remember doesn't include the margins */
        var hh = this.inherited(arguments);
        var hs = this.searchNode.offsetHeight; 
        return hh + hs + /*one magic missing pixel*/1;
    },

    renderTooltip: function(){
        var q = dojo.query('.irigo-tooltip', this.domNode);
        if(q.irigoTooltip){q.irigoTooltip();}
    },

    render: function(){
        var searchQueryInput = new TextBox({
            placeholder: this.searchPlaceholder, 
            intermediateChanges:true,
            onInput: function(e){
                // NOTE: for some fu... reason spaces doesn't go through
                // when text box is inside the grid.
                // we set it ourself
                if(e.keyCode === 32){
                    this.set('value', this.get('value') + ' ');
                }
            }
        }, this.searchQueryInputNode);
        connect.connect(searchQueryInput, "onChange", this, this._onSearchQueryChange);



        // NOTE: the grid steals back the focus _onFetchComplete, see. FocusManager
        // this is triggered by a click on a header in the grid (sorting).
        this.focus._delayedHeaderFocus = function(){
            // summary: overwriting the focus on the headers since that removes 
            // focus from the query input.
        };

        this.inherited(arguments);
    },
                             
    postrender: function(){
        this.inherited(arguments);

        this._selectAllCheckBox = query('.gridSelectAllCheckbox', this.viewsHeaderNode)[0];
        connect.connect(this._selectAllCheckBox, "onchange", this, this._onSelectAllChange);

        this.views.views[0].onAfterRow = lang.hitch(this, this.onAfterRow);
        this.renderTooltip();
    },

    onAfterRow: function(rowIdx, cells, rowNode){
        // summary:
        //     render header tooltip when header is re-rendered
        // that happens when there are no items to show in the grid after filter
        if(rowIdx === -1){
            // maintain the help icon
            this.renderTooltip();

            // maintain the select all checkbox in the 
            // re-created checkbox
            var checked = this._selectAllCheckBox.checked;
            this._selectAllCheckBox = query('.gridSelectAllCheckbox', this.viewsHeaderNode)[0];
            this._selectAllCheckBox.checked = checked;
            connect.connect(this._selectAllCheckBox, "onchange", this, this._onSelectAllChange);
        }
    },

    getBulkActions: function(items){
        // FIXME: move helpers somewhere else!
        function intersect(o1,o2){
            var intersected = {}, k;
            for(k in o2){
                if(o1[k]){
                    intersected[k] = k;
                }
            }
            return intersected;
        }

        function set(array){
            var s = {};
            for(var i = 0; i < array.length; i++){
                s[array[i]] = true;
            }
            return s;
        }

        var action_sets = [];

        // get actions for each item
        arrayUtil.forEach(items, function(item){
            var actions = item.getActions();
            // actions may just be a string... namely the loader
            if(lang.isArray(actions)){
                action_sets.push(set(actions));
            }
            else{
                action_sets.push(actions);
            }
        });

        var intersected = funcUtil.reduce(action_sets, intersect);
        return intersected;
    },

    getBulkActionButtons: function(items){

        var self = this;
        var selected = items;
        var selectedCount = items.length;
        if(selectedCount === 0){
            return '';
        }
        else if(selectedCount == 1){
            var item = selected[0];
            return item.getActionButtons();
        }
        // Intersect the actions
        else{
            var intersected = this.getBulkActions(items);
            var action_buttons = [];
            for(var action in intersected){
                if(action === 'loading'){
                    return '';
                }
                var t = '<button type="button" class="action_button ${action}_icon" onclick="${onClickAction}"><span>${action}</span></button>';
                var args = {
                    onClickAction: string.substitute(
                        "steam2.ActionGrid.bulkActionHandler('${0}', '${1}');return false;", 
                        [
                            action,
                            this.gridId
                        ]),
                    action: action
                };
                action_buttons.push(string.substitute(t, args));
            }
            return action_buttons.join('');
        }

    },

    getSelectedItems: function(){
        // NOTE: some items in the selection are null after filtering!?!
        return arrayUtil.filter(this.selection.getSelected(), function(item){
            return item === null ? false : true;
        });
    },

    filter: function(query, reRender){
        if(this._selectAllCheckBox.checked){
            this._onFetchCompleteSelectAll();
        }
        this.inherited(arguments);
    },

    setBulkInfo: function(eventType){
        var selectedItems = this.getSelectedItems();
        var selectedCount = selectedItems.length;

        if(selectedCount === 0){
            this.bulkOperationsNode.style.display = 'none';
            return;
        }

        var actionButtons =  this.getBulkActionButtons(selectedItems);
        var text = "";

        if(!actionButtons){
            actionButtons = "<em>No actions in common</em>";
        }
        else{
            text = "Available bulk operations:";
        }

        var t = string.substitute(
            '${0} Selected. ${1} ${2}',
            [selectedCount, text, actionButtons]
        );

        this.bulkOperationsNode.style.display = '';
        this.bulkOperationsNode.innerHTML = t;
    },

    onSelected: function(inIndex){
        this.updateRow(inIndex);
        this.setBulkInfo('select');
    },

    onDeselected: function(inIndex){
        this._selectAllCheckBox.checked = false;
        this.updateRow(inIndex);
        this.setBulkInfo('deselect');
    },

    onStyleRow: function(row){
        this.inherited(arguments);
        var item = this.getItem(row.index);
        if(item){
            var status = item.status;
            var color = statusColorMap.get(status);
            // the old style is cached there for some reason
            // clear it
            row.node._style = '';
            row.customStyles = 'cursor:pointer;color:' + color + ';';
        }
    },

    _onSet: function(item, attribute, oldValue, newValue){
        this.inherited(arguments);
        // update the bulk icons when items are updated.
        if(attribute == 'status'){
            this.setBulkInfo();
        }
    },

    setQuery: function(query){
        if(!query){
            delete this.queries['name'];
            delete this.queries['status'];
        }
        else{
            this.queries['name'] = {prop: 'name', value:query, type:'or'};
            this.queries['status'] = {prop: 'status', value:query, type:'or'};
        }        
    },

    _onSearchQueryChangeTimeout: function(query){
        // if a request is pending the following requests are ignored by the DataGrid 
        // wait for finish and execute...
        if(this._pending_requests[0]){
            var h = connect.connect(this, '_onFetchComplete', this, function(){
                this._onSearchQueryChangeTimeout();
                connect.disconnect(h);
            });
            return;
        }
        this.setQuery(query);
        this.filter(this._toJsonQuery(), true);
    },

    _onSearchQueryChange: function(query){
        // summary:
        //     handle search query input.
        // we delay executing the queries on sequential inputs.
        if(this.__searchQueryTimeout){
            window.clearTimeout(this.__searchQueryTimeout);
        }
        var _onSearchQueryChangeTimout = lang.hitch(this, this._onSearchQueryChangeTimeout, query);
        this.__searchQueryTimeout = window.setTimeout(_onSearchQueryChangeTimout, 200);
    },

    _clearSelection: function(){
        var self = this;
        arrayUtil.forEach(this.selection.selected, function(item, idx){
            // We are not using selection.clear();
            // since that triggers setBulkInfo on each item.
            delete self.selection.selected[idx];
        });
    },

    selectAll: function(){
        this.selection.selectRange(0, this._by_idx.length-1);
    },

    _onFetchCompleteSelectAll: function(){
        this._clearSelection();
        // onFetchCompleteSelectAll
        var h = dojo.connect(this, '_onFetchComplete', this, function(){
            this.selectAll();
            dojo.disconnect(h);
        });
    },

    _onSelectAllChange: function(event){
        // summary:
        //     Handle clicks on the 'select all' checkbox
        // event: DOMEvent
        this._clearSelection();
        this.filter(this._toJsonQuery());
    },

    queries: {
    },

    _toJsonQuery: function(){
            // query += '[?status~"' + this.statusQuery + '"]'; 

        function match(query){
            // case insensitive match
            return query.prop + "~\"*" + query.value + "*\"";
        }
        var orQueries = [];
        var andQueries = [];
        var query = '';
        for(var key in this.queries){
            var q = this.queries[key];
            if(q.type === "or"){
                orQueries.push(match(q));                
            }
            else if(q.type === "and"){
                andQueries.push(match(q));                
            }
        }
        if(orQueries.length > 0){
            query = '[?' + orQueries.join('|') + ']';
        }
        arrayUtil.forEach(andQueries, function(q){
            query += '[?' + q + ']';
        });
        return query;
    }
});


//
// 'static' stuff
//

ActionGrid.gridId = 0;
ActionGrid.grids = [];

ActionGrid.bulkActionHandler = function(action, gridId){
    var grid = ActionGrid.grids[gridId];
    var store = grid.store;
    var selected = grid.selection.getSelected();

    grid.model.save(selected, action);
};

return ActionGrid;

});