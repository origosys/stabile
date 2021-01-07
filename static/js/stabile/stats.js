define([
"dojox/data/ClientFilter",
"dojox/data/JsonRestStore",
"dojox/charting/Chart2D",
"dojox/charting/Theme"
], function(){

var stats = {
    span : 36,

    unit : "h",

    /** now in seconds since epoch. */
    now : function() {
        return parseInt(new Date().getTime() * 0.001, 10);
    }

};

stats.colors = {
    current: 0x18B0000,

    id2color: {},

    next: function(){
        this.current += 0x302010;
        return this.current;
    },

    get: function(id){
        var color = this.id2color[id];
        if(!color){
            color = this.next();
            this.id2color[id] = color;
        }
        return "#" + color.toString(16).substr(1,7);
    }
};

stats.theme = new dojox.charting.Theme({
    chart:{
        stroke:null,
        fill: "white"
    },
    plotarea:{
        stroke:null,
        fill: "#D4EDF1"
    },
    axis:{
        stroke:{ color:"#fff",width:2 },
        line:{ color:"#fff",width:1 },
        majorTick:{ color:"#fff", width:2, length:12 },
        minorTick:{ color:"#fff", width:1, length:8 },
        font:"normal normal normal 8pt Tahoma",
        fontColor:"#999"
    },
    series:{
        outline:{ width: 0.1, color:"#fff" },
        stroke:{ width: 1, color:"#666" },
        fill:new dojo.Color([0x66, 0x66, 0x66, 0.8]),
        font:"normal normal normal 7pt Tahoma",	//	label
        fontColor:"#000"
    },
    marker:{	//	any markers on a series.
        stroke:{ width:1 },
        fill:"#333",
        font:"normal normal normal 7pt Tahoma",	//	label
        fontColor:"#000"
    },
    colors:[]
});

stats.labels = {

    /**
     * Gets labels for a chart with the given specs.
     * Args:
     *   span {Number}:
     *   step {Number}:
     *   unit {String}:
     */
    get: function(args){
        var labels = [];
        for(var i = 0; i < args.span; i = i + args.step){
            labels.push({value: i, text: (i - args.span) + args.unit });
        }
        // the last label is "now"
        labels.push({value:args.span, text: "now"});
        return labels;
    }
};

stats.data = {

    secsPerStep: {
        min: 60,
        h: 3600,
        d: 86400,
        w: 604800,
        m: 2592000 // 30 days
    },

    /**
     * Converts unix timestamps (i.d., secs since epoch) to
     * values in [0;...] suitable for charting.
     */
    prepare: function(args) {
        var item = args.item,
                datasetprops = args.datasetprops || [],
                span = args.span || stats.span,
                unit = args.unit || stats.unit,
                maxTime = args.maxTime;

        // guard against null from the server
        item.timestamps = item.timestamps           || [];
        item.mem = item.mem                         || [];
        item.diskactivity = item.diskactivity       || [];
        item.cpuload = item.cpuload                 || [];
        item.networkactivity = item.networkactivity || [];

        var self = this;

        /* at x = 0 */
        var referenceTime = maxTime - (span * self.secsPerStep[unit]);

        function normalize(ts){
            var val = (ts - referenceTime) / self.secsPerStep[unit];
            return val;
        }

        for(var j = 0; j < datasetprops.length; j++){
            var normalized = [];
            var min = null, max = null;

            for(var i = 0; i < item.timestamps.length; i++){
                var val = item[datasetprops[j]][i];
                if(!min || val < min){
                    min = val;
                }
                if(!max || val > max){
                    max = val;
                }
                var x = normalize(item.timestamps[i]);
                normalized.push({x:x, y: val});
            }
            item[datasetprops[j] + "_normalized"] = normalized;
            item[datasetprops[j] + "_min"] = min || 0;
            item[datasetprops[j] + "_max"] = max || 0;
        }
    },

    load: function(item){
        if(!this.store){
//            this.store = new dojox.data.JsonRestStore({target:"/stabile/stats"});
            this.store = new dojox.data.JsonRestStore({target:"/stabile/systems?action=metrics"});
        }
        var self = this;
        var from = stats.now() - stats.span * stats.data.secsPerStep[stats.unit];

        // FIXME: why is the data wrapped in a new array by dojo?
        var query = {
            uuid: item.uuid,
            cpuload: true,
            diskactivity: true,
            networkactivity: true,
            mem: true,
            diskspace: true,
            from: from,
            to: stats.now() // now
        };
        var queryStr = "?" + dojo.objectToQuery(query);

        function loaded(response, request){
            if(!response.items){
                IRIGO.toaster([
                    {
                        message: "No statistics available for server: " + item.name,
                        type: "message",
                        duration: 5000
                    }]);
                return;
            }
            var server = response.items[0];


            function prune(prop){
                var divisor = 1;
                if (prop == "mem") {divisor = 1024;}
                else if (prop == "diskactivity") {divisor = 1024;}
                else if (prop == "networkactivity") {divisor = 1024;}
                else if (prop == "cpuload") {divisor = 1024*1024*100;}
                var values = server[prop] || []; // sometimes null
                var pruned = [];
                var i;
                var aber = 0;
                for(i = 0; i < values.length; i = i + 1){
                    if (values[i]==null) { // Ugly hack to correct aberrations...
                        if (aber<3 && pruned[i-1]!=null) {
                            pruned.push(pruned[i-1]);
                            aber++;
                        } else {
                            pruned.push(values[i]);
                        }
                    } else {
                        pruned.push(values[i] / divisor);
                        aber = 0;
                    }
                }
                if (pruned[i-2]==0) {pruned[i-2] = pruned[i-3];}
                if (pruned[i-1]==0) {pruned[i-1] = pruned[i-2];}
                server[prop] = pruned;
            }

            dojo.forEach(["mem", "cpuload", "diskactivity", "networkactivity"],
                    function(prop){
                        prune(prop);
                    });


            self.prepare(
            {
                maxTime: stats.now(),
                span: stats.span,
                unit: stats.unit,
                item:server,
                datasetprops: ["cpuload", "mem", "diskactivity", "networkactivity"]
            }
                    );
            self.onLoad(server);
        }

        self.store.fetch({
            query:query,
            onComplete: loaded,
            onError: function(){
                IRIGO.toaster([
                    {
                        message: "Error fetching data from server: " + item.name,
                        type: "message",
                        duration: 5000
                    }]);

            }
        });
    },

    // event to attach to
    onLoad: function(item){}
};

stats.chart = function(domId, args){
    domId = dojo.byId(domId);
    args = args || {};
    args.type = args.type || "";
    args.yAxisMax = args.yAxisMax || 100;

    var c = {
        tickStepXAxis: 4,
        chart: null,
        type: args.type,

        addXAxis: function(){
            this.chart.addAxis("x", {
                labels: stats.labels.get({span:stats.span, step:this.tickStepXAxis, unit: stats.unit}),
                min: 0,
                max: stats.span,
                includeZero: true,
                minorTicks: true,
                majorTickStep: this.tickStepXAxis
            });

        },

        addYAxis: function(){
            c.chart.addAxis("y", {
                min: 0,
                max: args.yAxisMax,
                vertical: true,
                includeZero: true,
                minorTicks: false,
                majorTickStep: args.yAxisMax / 4
            });
        },

        addBackgroundGrid: function(){
            this.chart.addPlot("grid", {type: "Grid", hMinorLines: true});
        },

        render: function(){
            this.refresh();
            this.chart.render();
        },

        refresh: function(){
            this.chart.removeAxis("y");
            this.addYAxis();
            this.chart.removeAxis("x");
            this.addXAxis();
        },

        add: function(item){

            var data = item[args.type + "_normalized"] || console.error("couldn't find prepared data");

            this.chart.addSeries(item.name, data, {
                // legend: item.name,
                stroke: {color:stats.colors.get(item.name), width: 1},
                line: {width:1}
            });

            // adjust yAxis
            args.yAxisMax = item[args.type + "_max"] * 1.1;
            var yMax = item[args.type + "_max"];
            if(yMax > args.yAxisMax){
                args.yAxisMax = yMax * 1.1;
            }

            var index = this.chart.runs[item.name];
            return this.chart.series[index];
        },

        remove: function(item){
            this.chart.removeSeries(item.name);
        },

        init: function(domId){
            this.chart = new dojox.charting.Chart2D(domId);
            this.chart.setTheme(stats.theme);
            this.addYAxis();
            this.addXAxis();
            //this.addBackgroundGrid();

            return this;

            // _legend = new dojox.charting.widget.Legend({chart: c.chart}, "chartLegend");
        }
    };

    var chart = c.init(domId);
    chart.refresh();
    return chart;
};

window.stats = stats;

});
