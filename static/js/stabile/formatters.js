define([
'dojo/date/locale'
], function(locale){

    function bytes2mbs(size, rowIds, cell){
      return Math.round(Number(size)/(1024*1024));
    };
    
    function bytes2gbs(size, rowIds, cell){
      return Math.round(Number(size)/(1024*1024*1024));
    };
    
    function kbytes2mbs(size, rowIds, cell){
      return Math.round(Number(size)/1024);
    };
    
    function datetime(/*String*/ timestamp){
      return locale.format(new Date(timestamp), this.constraint);
    };

    /**
     * Converts a long string of bytes into a readable format e.g KB, MB, GB, TB, YB
     *
     * @param {Int} num The number of bytes.
     */
    function readableBytes(bytes) {
        var i = Math.floor(Math.log(bytes) / Math.log(1024)),
            sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

        return (bytes / Math.pow(1024, i)).toFixed(2) * 1 + ' ' + sizes[i];
    };
    function readableMBytes(mbytes) {
        var bytes = mbytes *1024*1024;
        var i = Math.floor(Math.log(bytes) / Math.log(1024)),
            sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

        return (bytes / Math.pow(1024, i)).toFixed(2) * 1 + ' ' + sizes[i];
    }

    return {
      bytes2mbs: bytes2mbs,
      bytes2gbs: bytes2gbs,
      kbytes2mbs: kbytes2mbs,
      readableBytes: readableBytes,
      readableMBytes: readableMBytes,
      datetime:datetime
    };
})
