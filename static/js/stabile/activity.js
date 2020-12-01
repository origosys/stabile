define([
'dojo/_base/html',
'dojo/parser',
'steam2/user',
'dojo/on',
'dijit/form/Button',
'dijit/TitlePane',
'stabile/log'
],function(html, parser, user, on){

function Activity(args, node){

    if(user.is_admin){
        var fragment = [
            '<div dojoType="dijit.TitlePane" id="activityPane" title="Activity" open="false">',
            '<div id="logContainer"',
            'style="height:80px; overflow:auto; margin:0px; padding:2px; border-bottom:1px solid; border-color: #CCCCCC"></div>',
		    '<button dojoType="dijit.form.Button" id="refreshLog" onClick="getLog()">Refresh</button>',
            '<button dojoType="dijit.form.Button" id="clearLog" onClick="clearLog()">Clear</button>',
	        '</div>'].join('');
        html.place(fragment, node);
        parser.parse(node);
    }
}

var activity = new Activity({}, "activity-pane");

if(user.is_admin){
    on(dijit.byId('activityPane'), 'click', function(evt) {
        if ((!evt.explicitOriginalTarget || (evt.explicitOriginalTarget && evt.explicitOriginalTarget.id === '')) && dijit.byId('activityPane').open) {
            getLog(true);
        }
    });
}
return activity;

});
