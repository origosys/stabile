require([
'dojo/ready',
'dojo/parser',
'dijit/form/Button',
'dijit/form/FilteringSelect',
'dijit/form/DateTextBox',
'dijit/form/HorizontalSlider',
'dijit/form/HorizontalRuleLabels',
'steam2/stores',
'steam2/StatsChart'
], function(ready, parser, Button, FilteringSelect, DateTextBox, HorizontalSlider, HorizontalRuleLabels, stores, StatsChart){

ready(function(){

 // keep our own that includes hours and secs which is stripped in the dijit widget
 var from = new Date();
 var to = new Date(from.getTime());

 function updateDate(d1,d2){
   d1.setDate(d2.getDate());
   d1.setMonth(d2.getMonth());
   d1.setFullYear(d2.getFullYear());
 }

 var id = null;
 var selected = null;
 var secs      = [1800,  3600, 2*3600, 12*3600, 24*3600, 2*86400, 14*86400, 28*86400, 2*2592000, 6*2592000, 12*2592000 ];
 var labels    = ['30mins', '60',   '2hrs',   '12',   '24',    '2days',    '14',    '28',      '2mths',      '6',       '12'];
 var timeout = 400;

 function doIt(){
     if(!selected){
         return;
     }
     if(id){
         window.clearTimeout(id);
     }
     id = window.setTimeout(function(){
         var args = getStatsQuery();
         chartCpuLoad.show(selected, 'cpuload','CPU load',  args);

         chartIO.show(selected, 'diskWrites', 'Disk Writes', args);
         chartIO.show(selected, 'diskReads', 'Disk Reads', args);

         chartNetworkActivity.show(selected, 'networkactivityrx', 'Network Reads', args);
         chartNetworkActivity.show(selected, 'networkactivitytx', 'Network Writes', args);
     }, timeout);
 }
      
 function getStatsQuery(){

      console.log('from', from.toString(), 'to', to.toString());

    return {
        from: from,
        to: to
    };
 }

 var slider = new HorizontalSlider({
     name: "slider",
     value: 0,
     minimum: 0,
     maximum: 10,
     discreteValues: 11,
     showButtons: false,
     intermediateChanges: true,
     style: {width: "100%"},
     onChange: function(value) {
       doIt();
     }
 }, "slider");

 var sliderLabels = new HorizontalRuleLabels({
     container:"bottomDecoration",
     labels: labels 
 }, "rules" );

 var chartCpuLoad = new StatsChart('chartCpuLoad', { 
     type: 'ratio'
 });

 chartCpuLoad.render();

 var chartIO = new StatsChart('chartIO', { 
    type: 'data',
    legend: true});
 chartIO.render();

 var chartNetworkActivity = new StatsChart('chartNetworkActivity', { 
     type: 'data',
     legend:true});
 chartNetworkActivity.render();

 var filteringSelect = new FilteringSelect({
     id: "serverSelect",
     placeHolder: 'Select server',
     store: stores.servers,
     searchAttr: "name"
 }, "serverSelect");

 dojo.connect(filteringSelect, 'onChange', function(uuid){
     selected = uuid;
     var query = getStatsQuery();

     chartCpuLoad.show(uuid, 'cpuload', 'CPU load', query);
     chartIO.show(selected, 'diskWrites', 'Disk Writes', query);
     chartIO.show(selected, 'diskReads', 'Disk Reads', query);

     chartNetworkActivity.show(selected, 'networkactivityrx', 'Network Reads', query);
     chartNetworkActivity.show(selected, 'networkactivitytx', 'Network Writes', query);
 });

 dojo.connect(slider, 'onChange', function(value){
    from = new Date(to.getTime() - 1000 * secs[value]);
    fromTextBox.set('value', from);
 });

 from = new Date(from.getTime() - 1000 * secs[slider.get('value')]);

 var fromTextBox = new DateTextBox({
   value: from,
   style: {width:'90px'},
   onChange: function(value){
       updateDate(from, value);
       if(from.getTime() > to.getTime()){
           to = new Date(from + 1000 * secs[slider.get('value')]);
           toTextBox.set('value', to);
       }
       doIt();
   }
 }, 'from');

 var toTextBox = new DateTextBox({
   value: to,
   style: {width:'90px'},
   onChange: function(value){
       updateDate(to, value);
       if(to.getTime() < from.getTime()){
           from = new Date(to - 1000 * secs[slider.get('value')]);
           fromTextBox.set('value', from);
       }
       doIt();
   }
 }, 'to');

 var queryParams = dojo.queryToObject(window.location.search.slice(1));
 if(queryParams['uuid']){
     filteringSelect.set('value', queryParams.uuid);
 }

});
});