// dojo.provide('evd.vnc');
// dojo.require('evd.uid');

// (function($, d){
        
//      function javatrigger(eventname, id, msg){
//          console.log('javatrigger', eventname, msg);
//          function f(){
//              console.log(eventname);
//              dojo.publish('vnc:' + eventname, [{id:id,msg:msg}]);
//          }
//          setTimeout(f, 0);
//      }

//      function start(node, args){
//          lg('vnc::start', node, args);
//          var id = uid();
//          dojo.publish(vnc.INJECT);

//          $.applet.inject(node, {
//                 archive: (args.archive || 'vnc.jar'),
//                 id: id,
//                 code: 'com.tigervnc.VncApplet',
//                 port: args.port,
//                 host: args.host,
//                 title: args.title,
//                 show_controls: 'no',
//                 new_window: "Yes",
//                 log_level: "error",
//                 callback: 'vnc.javatrigger'
//             });

//          return id;
//      }

//      // You can subscribe to events like this:
//      // dojo.subscribe(vnc.INIT, function(){});
//      // dojo.subscribe(vnc.DESTROY, function(){});
//      // dojo.subscribe(vnc.INJECT, function(){});

//      $.vnc = {
//          start:start,
//          javatrigger: javatrigger,

//          // EVENTS
//          CONNECTION_ERROR: 'vnc:connection_error',
//          INIT: 'vnc:init',
//          DESTROY: 'vnc:destroy',
//          INJECT: 'vnc:inject'
//      };

//     dojo.subscribe(vnc.DESTROY, function(obj){
//         dojo.destroy(obj.id);
//     });

// })(window, dojo);
