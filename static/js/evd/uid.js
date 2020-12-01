dojo.provide('evd.uid');

(function($){

    function uid(){
        var uid = new Date().getTime().toString(32), i;
        for (i = 0; i < 5; i++) {
	    uid += Math.floor(Math.random() * 65535).toString(32);
        }
        return uid;
    }
    
    $.uid = uid;

})(window);
