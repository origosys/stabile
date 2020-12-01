define([
"dojo/_base/declare",
"dojox/charting/action2d/Highlight",
"dojox/charting/action2d/Magnify",
"dojox/charting/action2d/Shake",
"dojox/charting/action2d/Tooltip",
"dojox/charting/Chart2D",
"dojox/charting/widget/Legend",
"dijit/form/HorizontalSlider",
"dijit/form/HorizontalRuleLabels",
"dijit/form/TextBox",
'dojox/charting/Chart',
"dojox/charting/widget/Legend",
'dojox/charting/themes/Tom',
"dojo/date/locale",
'steam2/StatsChartLoader',
'steam2/StatsChartThemes'
], function(declare){

var StatsChart = declare('steam2.StatsChart', dojox.charting.Chart, {

	_yaxis: {
		vertical: true,
        majorTicks: 4,
		min: 0,
		max: 1 //24*1024*100
	}, 

    _xaxis: {
        majorTicks: 3
    },

    markers: true,

//    statsURL: '/stabile/stats',
    statsURL: '/stabile/systems?action=metrics',

    constructor: function(/* DOMNode */node, /* dojox.charting.__ChartCtorArgs? */kwArgs){
		dojo.mixin(this, kwArgs);
        this.yaxis = dojo.mixin(dojo.mixin({}, this._yaxis), kwArgs.yaxis);
        this.xaxis = dojo.mixin(dojo.mixin({}, this._xaxis), kwArgs.xaxis);
		this.addAxis('y', this.yaxis);
        
        // add default plot
		this.addPlot('default', {
		    markers: this.markers,
		    notension: 'S',
		    lines: true,
		    nolabelOffset: -30
		});

        this.addPlot('grid', {type: 'Grid', hMinorLines: false});

        // then we can add dynamic stuff to the default plot
		new dojox.charting.action2d.Tooltip(this, 'default', {
            notext: function(o){
                //for (var prop in o.plot._eventSeries)
                //    console.log(o, prop);

                //console.log(o);
                var value = o.y;
                //var dt = new Date(o.x);
                //if(typeof value === 'number'){
                //    value = value.toFixed(2);
                //}
                //return dojo.date.locale.format(dt, {datePattern: 'EEE, dd MMM', timePattern: 'HH:mm'}) +
                 //   '<br /><span style="font-weight:bold">' + value + '</span>';
                return value;
            }
        });

        // on hover increase marker size.
        new dojox.charting.action2d.Magnify(this, 'default', {scale: 1.5});
        new steam2.StatsChartLoader(this);

        if(this.legend){
            var legendNodeWrapper = dojo.create('div', {className: 'legendNodeWrapper'}, node, 'after');
            var legendNode = dojo.create('div', null, legendNodeWrapper);
		    var legend = new dojox.charting.widget.Legend({
		        chart:this
		    }, legendNode);
            
            dojo.connect(this, 'render', function(){
                legend.refresh();
            });
        }

        this._setTheme();
    },

    humanSize: function(size, unitOnly){
        if (size==null) return null;
        var unit;
        if(size <= steam2.StatsChart.KB){
            unit = 'B/s';
        }
        else if(size <= steam2.StatsChart.MB){
            size = size / steam2.StatsChart.KB;
            unit = 'KB/s';
        }
        else if(size <= steam2.StatsChart.GB){
            size = size / steam2.StatsChart.MB; //Math.pow(2,20);
            unit = 'MB/s';
        }
        else{
            size = size / steam2.StatsChart.GB;
            unit = 'GB/s';
        }
        if(unitOnly){
            return unit;
        }
        return size.toFixed(0) + ' ' + unit;
    },

    getTimeLabel: function(timestamp){
       if ((new Date()).getDate() > (new Date(timestamp)).getDate()) { // Not today
           return dojo.date.locale.format(
                   new Date(timestamp), {
                       //selector: "date",
                       datePattern: 'd/M',
                       //timePattern: 'HH:mm:ss'
                       timePattern: 'HH:mm'
           });
       } else {
           return dojo.date.locale.format(
                   new Date(timestamp), {
                       selector: "time",
                       //datePattern: 'd/M',
                       timePattern: 'HH:mm:ss'
                       //timePattern: 'HH:mm'
           });
       }
    },

    getYLabel: function(value){
        if(this.type === 'data'){
            return {
                value: value,
                text: this.humanSize(value)
            };
        };            
        return value;
    },

    loading: function(){
    },

    noData: function(){        
    },

    show: function(uuid, statfield, name, kwArgs){
        this.loading();

        var self = this,
            from = parseInt(kwArgs.from.getTime() * 0.001, 10),
            to = parseInt(kwArgs.to.getTime() * 0.001, 10),
            query = {
                uuid: uuid,
                from: from,  
                to: to
            };
 
        query[statfield] = true;
        
        // when several series are present save the max
        this.yaxis.max = null;

        function success(dataArray){
            for (var i = 0; i < dataArray.length; i++) {
                data = dataArray[i];
                if(!data || data.timestamps === null){
                    self.noData();
                    console.log("No stats data to render");
                    return;
                }
                console.log("preparing", data.uuid);
                var d = self.prepare(data, statfield, name);
                self.addSeries(uuid+name, d.data, {stroke: {width: 1}});
                if(self.type === 'data'){
                    self.addBytesAxis(d.max);
                }
                else if(self.type === 'ratio'){
                    self.addRatioAxis(d.max);
                };
                //console.log(kwArgs.from.getTime()-d.xmin, kwArgs.to.getTime()-d.xmax);
                self.addAxis('x', {
                    minorTicks: false,
                    //from: kwArgs.from.getTime(),
                    from:d.xmin,
                    //to: kwArgs.to.getTime(),
                    to:d.xmax,
                    labelFunc: function(def, ts, precision){
                        return self.getTimeLabel(ts);
                    },
                    //majorTickStep: (d.data[d.data.length-1].x - d.data[0].x) / self.xaxis.majorTicks
                    majorTickStep: (to-from)*1000/6
                    //majorTickStep: (d.xmax-d.xmin)/6
                });
            }
            self.render();
        }

        function error(err){
            if(err.responseText){
                self.noData(err.responseText);                
            }
            else if(err.status === 401){
                self.noData("You are not logged in!");
            }
            else{
                self.noData("Couldn't get data from server");
            }
        }

        var def = this.fetch(query);
        def.then(success, error);
    },

    addRatioAxis: function(pmax){
        var max = pmax;
        var step = null;
        if(max > 1){
            step = .5;
            max = 2;
        }
        else{
            step = .5;
            max = 1.05;
        }
        this.yaxis.majorTickStep = step;
        this.yaxis.min = -0.05;
        this.yaxis.max = max;
        this.yaxis.leftBottom = false;
        this.yaxis.vertical = true;
        this.addAxis('y', this.yaxis);
    },

    addBytesAxis: function(pmax){
        var max = pmax * 1.1;

        if(!this.yaxis.max || this.yaxis.max < max){
            this.yaxis.max = max;
            this.yaxis.leftBottom = false;
            //this.yaxis.majorTickStep = max / 4;
            this.yaxis.majorTickStep = Math.round(max / 2);
            // go a little bit below 0 so we can see y=0 values
            this.yaxis.min = -this.yaxis.majorTickStep * 0.1;
            this.yaxis.vertical = true;

            var self = this;
            this.yaxis.labelFunc = function(def, y, precision){
                return self.humanSize(y);
            };
            this.addAxis('y', this.yaxis);
        }
    },

    fetch: function(query){
        return dojo.xhrGet({
           content: query,
           url: this.statsURL,
           handleAs: 'json'
        });
    },

    prepare: function(data, statfield, name){
        var prepared = {
            min:0,
            max:0,
            xmax:0,
            xmin:0,
            data:[]
        };
        for(var i = 0; i < data.timestamps.length; i++){
            var value = data[statfield][i];
            if (value || value==0) {
                prepared.data.push({
                    x: data.timestamps[i] * 1000, /* s -> ms */
                    y: value,
                    tooltip: name
                });
                if(value > prepared.max){
                    prepared.max = value;
                }
            }
            if(data.timestamps[i]*1000 > prepared.xmax || prepared.xmax==0){
                prepared.xmax = data.timestamps[i]*1000;
            }
            if(data.timestamps[i]*1000 < prepared.xmin || prepared.xmin==0){
                prepared.xmin = data.timestamps[i]*1000;
            }
        }
        return prepared;
    },

    _setTheme: function(){
        this.setTheme(steam2.StatsChartThemes.blue);
        //this.setTheme(dojox.charting.themes.Tom);
    }


});

StatsChart.KB = Math.pow(2,10);
StatsChart.MB = Math.pow(2,20);
StatsChart.GB = Math.pow(2,30);
StatsChart.TB = Math.pow(2,40);

});

