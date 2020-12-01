define([
"steam2/user",
"steam2/statusColorMap",
"steam2/models/Image"
], function(user, statusColorMap, Image){

   var formatters = {
       action:function(val, rowIdx, cell) {
           var server = this.grid.getItem(rowIdx);
           return server.getActionButtons(server);
       },
       image: function(val, rowIdx){
           var server = this.grid.getItem(rowIdx);
           return server.getEditImageLink({colorize:true});
       },
       viewer: function(val, rowIdx){
           var server = this.grid.getItem(rowIdx);
           return server.getViewerButton();
       },
       viewerName: function(val, rowIdx){
           var viewer = "";
           if (val.issystem) {
               viewer = '<button title="System" class="plain_button system_icon" type="button"><span>System</span></button>';
           } else if (user.is_readonly) {
               ;
           } else if (val.macip && val.macip != "--") {
               viewer = val.getViewerButton();
           }
           return viewer + " " + val.name;
       },
       name : function(val, rowIdx){
           var server = this.grid.getItem(rowIdx);
           return server.getEditLink({colorize:true});
       },
       network: function(val, rowIdx){
           var server = this.grid.getItem(rowIdx);
           return server.getEditNetworkLink({colorize:true});
       },
       status: function(status, rowIdx){
//           if(status != "inactive" && status != "shutoff" && user.is_admin){
           if(user.is_admin){
               var server = this.grid.getItem(rowIdx);
               if (server.macname && server.macname != "--") {
                   status += " on " + server.macname;
               }
           }
           return status;
       },
       stats: function(val, rowIdx){
           var server = this.grid.getItem(rowIdx);
           return server.getActionButton('show_stats');   
       }
   };
   return formatters;
});