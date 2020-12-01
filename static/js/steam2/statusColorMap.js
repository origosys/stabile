define([],function(){

    var statusColorMap = {
         
        codes:{
            ok: 'green',
            fail: 'red',
            enabled: 'blue',
            disabled: 'grey',
            active: 'green',
            booting: 'orange',
            down: 'red',
            inactive: 'grey',
            nostate: 'grey',
            moving: 'orange',
            joining: 'orange',
            unjoin: 'orange',
            unjoining: 'orange',
            nat: 'orange',
            running: 'green',
            sleeping: 'orange',
            asleep: 'orange',
            shutdown: 'red',
            shutoff: 'red',
            starting: 'orange',
            shuttingdown: 'orange',
            destroying: 'orange',
            deleting: 'orange',
            unused: 'grey',
            used: 'blue',
            up: 'green',
            creating: 'orange',
            cloning: 'orange',
            snapshotting: 'orange',
            unsnapping: 'orange',
            mastering: 'orange',
            unmastering: 'orange',
            rebasing: 'orange',
            backingup: 'orange',
            restoring: 'orange',
            copying: 'orange'
        },
             
        get: function(code){
            return this.codes[code] || 'black';
        }
    };
    
    return statusColorMap;

});
