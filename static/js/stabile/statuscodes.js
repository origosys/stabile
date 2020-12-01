dojo.provide('stabile.statuscodes');

dojo.ready(function(){

var statuscodes = {

    codes:{
        active: 'green',
        booting: 'orange',
        down: 'red',
        inactive: 'grey',
        nostate: 'grey',
        moving: 'yellow',
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
        copying: 'orange',
        enabled: 'blue',
        disabled: 'grey'
    },

    getColor: function(code){
        return this.codes[code] || 'black';
    }
};
window.statuscodes = statuscodes;
});