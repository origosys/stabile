define([
"dojo/_base/Deferred",
"dojo/_base/xhr",
"dojo/store/util/SimpleQueryEngine",
"dojo/store/util/QueryResults",
"dojo/data/util/filter",
"dojox/json/query",
"dojox/data/util/JsonQuery"
], function(Deffered, xhr, QueryEngine, QueryResults, filterUtil, query, JsonQuery){

// Service to be used with the JsonRestStore.
// The service is to work around the backend format
 
return function(path, serviceImpl, schema){

    var queryEngine = QueryEngine;

    var service = function(id, args) {

        function processResults(results){
            var items = results.items;
	        var regexpList = {};
            var value,
	   	        ignoreCase = true;
            
            // convert regular queries to json query
            var queryOptions = args['queryOptions'];
            if(!queryOptions || !queryOptions['jsonQuery']){
                args.query = new JsonQuery()._toJsonQuery(args.query);
            }
            var result = query(args['query'] || '', items);
            return result;
        }

        var serviceArgs = {
            url : path, 
            handleAs : "json"
        };
        
        var deferred;
        deferred = xhr.get(serviceArgs);
        deferred.addCallback(processResults);
        return deferred;
    };

    service.put = function(id, value){
        
    };

    service.post = function(id, value){
        
    };

    service.delete = function(id){
        
    };
    
    service.servicePath = path;
    service._schema = schema;

    return service;
};     

});
