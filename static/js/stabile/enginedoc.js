/*global
dojo:false
*/
var ed = {};

ed.form = function(args) {
  
  var button = dojo.byId("formButton");
  var id = args.domId;
  var clearOnSuccess = args.clearOnSuccess;

  dojo.connect(button, "onclick", function(event) {
    event.preventDefault();
    event.stopPropagation();

    var xhrArgs = {
      form: dojo.byId(id),
      handleAs: "json",
      load: function(data) {
        IRIGO.toaster([{
            message: data.message,
            type: "message",
            duration: 2000
        }]);
        if(data.action){
          // the action reflects the category and title
          dojo.byId(id).action = data.action;                       
        }
        if(clearOnSuccess){
          var nodes = dojo.query('#' + id + ' input, #' + id + ' textarea');
          var clear = function(node){
            node.value = "";
          };
          dojo.forEach(nodes, clear);
        }
      },
      error: function(error) {
        IRIGO.toaster([
            {
              message: error.responseText,
              type: "error",
              duration: 5000
            }]);
      }
    };

    IRIGO.toaster([{
        message: "Processing ...",
        type: "message",
        duration: 500
    }]);

    var deferred = dojo.xhrPost(xhrArgs);

    });
};
