define([
], function(){

    function getLog(scroll) {
        //Look up the node we'll stick the text under.
        var targetNode = dojo.byId("logContainer");
        if (!dijit.byId("activityPane") || !dijit.byId("activityPane").open) {
            return;
        }
        dojo.byId("activityPane_pane").style.padding = "0";
        var xhrArgs = {
            url: "/stabile/nodes?action=listlog",
            handleAs: "text",
            preventCache: "true",
            load: function(data) {
                //Replace newlines with nice HTML tags.
                data = data.replace(/\n/g, "<br>");
                //Replace tabs with spacess.
                data = data.replace(/\t/g, "&nbsp;&nbsp;&nbsp;");
                var s = targetNode.style.height;
                var l = s.indexOf("px");
                var n = targetNode.scrollHeight - parseInt(s.substring(0,l), 10) - 4;
                var atbottom = (targetNode.scrollTop >= n);
                targetNode.innerHTML = data;
                if (atbottom || scroll) {
                    console.log("scrolling log");
                    targetNode.scrollTop = targetNode.scrollHeight;
                }
            },
            error: function(error) {
                targetNode.innerHTML = "--";
            }
        };
        var deferred = dojo.xhrGet(xhrArgs);
    };

    function clearLog() {
        var targetNode = dojo.byId("logContainer");
        var xhrArgs = {
            url: "/stabile/nodes?action=clearlog",
            handleAs: "text",
            preventCache: "true",
            load: function(data) {
                targetNode.innerHTML = "--";
            },
            error: function(error) {
                targetNode.innerHTML = "An unexpected error occurred: " + error;
            }
        };
        targetNode.innerHTML = "--";
        var deferred = dojo.xhrGet(xhrArgs);
    };

    window.getLog = getLog;
    window.clearLog = clearLog;

});

