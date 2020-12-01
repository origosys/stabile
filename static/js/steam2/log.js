dojo.provide('steam2.log');

steam2.DEBUG = true;
steam2.log = function(){
  if(steam2.DEBUG && typeof console != 'undefined'){
    console.log([].slice.call(arguments));
  }
};
