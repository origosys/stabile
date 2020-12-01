define([
"dojo/_base/declare"
], function(declare){
    return declare('steam2.StatsChartLoader', null, {

    loaderURL: '/stabile/static/img/loader.gif',

    constructor: function(chart){
        var node = this.node = chart.node;

        this.loader = dojo.create('div', {
            className: 'loading', 
            innerHTML:dojo.replace('<img alt="..." src="{loader}" style="vertical-align:middle;position:relative;left:{left}px;top:{top}px" height="20px" />', {
                left: node.clientWidth / 2,
                top: node.clientHeight / 2,
                loader: this.loaderURL}),
            style: dojo.replace('display:none;height:{height};width:{width}', {
                height: node.style.height, 
                width: node.style.width })
        }, node, 'before');

        this.noDataNotifier = dojo.create('div', {
            innerHTML: '<div style="padding-top:' + node.clientHeight / 2 + 'px;text-align:center;">no data!</div>',
            style: dojo.replace('display:none;height:{height};width:{width}', {
                height: node.style.height, 
                width: node.style.width })
        }, node, 'before');


        dojo.connect(chart, 'loading', this, this.show);
        dojo.connect(chart, 'render' , this, this.hide);
        dojo.connect(chart, 'noData', this, this.noData);
    },

    show: function(){
        this.node.style.display = 'none';
        this.noDataNotifier.style.display = 'none';
        this.loader.style.display = '';
    },
                 
    hide: function(){
        this.loader.style.display = 'none';
        this.noDataNotifier.style.display = 'none';
        this.node.style.display = '';
    },

    noData: function(){
        this.loader.style.display = 'none';
        this.noDataNotifier.style.display = '';
    }
                 
});

});

