define([
"dojo/aspect",
"dojo/topic",
"dojo/_base/xhr"
], function(aspect, topic, xhr){

    var logoutInProgress = false;
    var loginUrl = '/stabile/login';

    aspect.around(dojo, "xhr", function(originalXhr){
        return function(method, args){
            var dfd = originalXhr(method, args);
            var errHandler = function(error){
                if(logoutInProgress){
                    return error;
                }
                if(error.status === 401 || error.status === 403){
                    logoutInProgress = true;
                    topic.publish("message", {
                        message: "Your session has timed out",
                        duration: 2000,
                        type:"warning"
                    });
                    var to_login_page = function(){
                        window.location.href = loginUrl;
                    };
                    // show message for 2 sec 
                    setTimeout(to_login_page, 2000);
                };
                return error;
            };
            var emptyHandler = function(){};
            dfd.then(emptyHandler, errHandler);
            return dfd;
        };
    });
});
