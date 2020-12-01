define([
"dojo/_base/lang",
"dojo/_base/declare",
"dojo/_base/connect",         
"dojo/dom-construct",
"dojo/string",
"dijit/form/Select",
"steam2/ActionGrid",
"steam2/ServersGridFormatters",
"steam2/stores",
"steam2/statusColorMap",
"steam2/models/Server",
"steam2/user"
], function(lang, declare, connect, domConstruct, string, Select, ActionGrid, formatters, stores, statusColorMap, Server, user){

return declare("steam2.ServersGrid", ActionGrid, {

    store: stores.servers,
    model: Server,
    
    // FIXME: removed when stores are converted to JsonRestStore
    postURL: '/stabile/servers',
                
    summaryTemplate: "Total VCPUs: ${vcpus} (Quota: ${vcpuQuota}) &nbsp;&nbsp;Total memory: ${memory} GB (Quota: ${memoryQuota} GB)",

    searchPlaceholder: user.is_admin ? 
                       'Find by name, status or node' : 
                       'Find by name or status',

    constructor: function(args){
        connect.connect(Server, 'onViewerStart', this, function(server){
            this.updateRow(this.getItemIndex(server));
        });
        connect.connect(Server, 'onViewerStop', this, function(server){
            this.updateRow(this.getItemIndex(server));
        });
        // on every fetch update the summary.
        connect.connect(this, '_onFetchComplete', this, function(){
            this.updateSummary();
        });
        connect.connect(this.store, 'onSet', this, function(){
            this.updateSummary();
        });

        this.inherited(arguments);
    },

    postrender: function(){
        this.inherited(arguments);
        
        var statusFilter = new Select({
            options: [
                { label: 'All', value: 'all', selected: true },
                { label: 'Running', value: 'running' },
                { label: 'Inactive', value: 'inactive' },
                { label: 'Shutoff', value: 'shutoff' }
            ]
        }, this.searchFilterNode);
        
        connect.connect(statusFilter, "onChange", this, function(status){
            if(status === "all"){
                delete this.queries['statusFilter'];
            }
            else{
                this.queries.statusFilter = {prop:"status", value:status, type:"and"};
            }
            if(this._selectAllCheckBox.checked){
                this._onFetchCompleteSelectAll();
            }
            this.filter(this._toJsonQuery(), /*rerender*/true);
        });
        this.updateSummary();
    },

    getBulkActions: function(){
        var actions = this.inherited(arguments);
        // always enable destroy
        if(!actions){
            actions = {};
        }
        actions.destroy = 'destroy';
        actions.start = 'start';
        return actions;
    },

    updateSummary: function(){

        function toGb(mb){
            return (Math.round(10*mb / 1024) / 10);
        }

        var templateArgs = {
            vcpus : 0,
            memory : 0,
            vcpuQuota : user.vcpuquota,
            memoryQuota : user.memoryquota
        };

        for(var i = 0; i < this.rowCount; i++){
            var server = this.getItem(i);
            if (server) {
                if (server.isPowered()){
                    templateArgs.vcpus += (parseInt(server.vcpu));
                    templateArgs.memory += parseInt(server.memory);
                }
            }
        }

        // convert to GB
        templateArgs.memory = toGb(templateArgs.memory);
        templateArgs.memoryQuota = toGb(templateArgs.memoryQuota);
        
        this.summaryNode.innerHTML = string.substitute(this.summaryTemplate, templateArgs);
    },

    structure: [
        {
            width:'20px',
            name: '<input type="checkbox" class="gridSelectAllCheckbox"></input>',
            formatter: function(val, rowIdx){
                if(this.grid.selection.isSelected(rowIdx)){
                    return '<input type="checkbox" checked="checked"></input>';
                }
                return '<input type="checkbox"></input>';
            },
            hidden: user.is_readonly
        },
        {
            width: '30px',
            name: '<a href="https://www.origo.io/info/support/help/origo-stabile/servers/console" rel="help" target="_blank" class="irigo-tooltip">help</a>',
            formatter: formatters.viewer
        },
        {
            field: 'name',
            width: '100%',
            formatter: formatters.name
        },
        {
            field: 'status',
            name: 'Status <a href="https://www.origo.io/info/support/help/origo-stabile/servers/status" rel="help" target="_blank" class="irigo-tooltip">help</a>',
            width: '100px',
            formatter: formatters.status
        },
        {
            field: 'vcpu',
            width: '40px',
            name: 'VCPUs',
            cellStyles: 'text-align:right;'
        },
        {
            field: 'memory',
            width: '70px'
        },
        {
            field: 'image',
            name: 'Image',
            width: '130px',
            formatter: formatters.image
        },
        {
            field: 'network',
            name:'Network',
            width:'100px',
            formatter: formatters.network
        },
        { 
            field: 'action',
            name: 'Action <a href="https://www.origo.io/info/support/help/origo-stabile/servers/actions" rel="help" target="_blank" class="irigo-tooltip">help</a>',
            width: '120px',
            formatter: formatters.action,
            hidden: user.is_readonly
        }
    ],

    canSort: function(index){
        if(index === 1 || index === 2 || index === 6){ 
            return false;
        }
        return true;
    },

    setQuery: function(query){
        this.inherited(arguments);
        if(user.is_admin){
            if(!query){
                delete this.queries['macname'];
            }
            else{
                this.queries['macname'] = {prop:'macname', value:query, type:'or'};
            }
        }

    }

    // onCellMouseOver: function(e){
    //     if(e.cellIndex === 0){
    //         var msg = 'Info ...';
    //         dijit.showTooltip(msg, e.cellNode);
    //     }
    // }
});

});
