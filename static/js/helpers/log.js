dojo.provide('util.log');

lg = function(){ window.console && window.console.log(Array.prototype.slice.call(arguments));};
er = function(){ window.console && window.console.error(Array.prototype.slice.call(arguments));};

if(typeof console == 'undefined'){

   console = {
       log: function(){},
       error: function(){}
   };
    
}
