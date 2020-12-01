define([
"dojox/charting/themes/PlotKit/blue"
], function(){

    steam2.StatsChartThemes = {};
    var th = dojo.clone(dojox.charting.themes.PlotKit.blue);

    th.axis.tick = {
        color:     "#474747",
        position:  "center",
		font: "normal normal normal 8pt Helvetica, Arial, sans-serif", 
        fontColor: "#474747"
    };

    th.marker = {
		stroke:  {width: 0.5, color: "#eaf2cb"},
		outline: {width: 0, color: "#eaf2cb"},
		font: "normal normal normal 8pt Helvetica, Arial, sans-serif"
	};

	th.next = function(elementType, mixin, doPost){
        // bypass reset of marker stroke and color in plotkit
		return dojox.charting.Theme.prototype.next.apply(this, arguments);
	};

    th.chart.fill = '#FFF';
    steam2.StatsChartThemes.blue = th;

});


