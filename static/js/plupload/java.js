/*global plupload:false, escape:false, alert:false */
/*jslint evil: true */
define([
'plupload/plupload',
'java/applet'
], function(plupload, applet){

  var uploadInstances = {};
      
  plupload.applet = {

    pluploadjavatrigger : function(eventname, id, fileobjstring) {
      // FF / Safari mac breaks down if it's not detached here
      // can't do java -> js -> java
      setTimeout(function() {
          var uploader = uploadInstances[id], i, args;
          var file = fileobjstring ? eval('(' + fileobjstring + ')') : "";
          if (uploader) {
            uploader.trigger('applet:' + eventname, file);
          }
      }, 0);
    }
  };

  plupload.runtimes.Applet = plupload.addRuntime("java", {

    /**
     * Returns supported features for the Java runtime.
     * 
     * @return {Object} Name/value object with supported features.
     */                                                   

    getFeatures : function() {
      return {
        java: applet.hasVersion('1.5'),
        chunks: true,
        progress: true,
        dragdrop: false
      };
    },    

    initialized : false,
    init : function(uploader, callback) {

      var _applet,
          appletContainer, 
          appletVars, 
          lookup = {},
          initialized, 
          waitCount = 0, 
          container = document.body,
          features = this.getFeatures(),
          url = uploader.settings.java_applet_url;

  // Commented out to allow upload without Java
      //if(!features.java){
      //  callback({success : false});
      //  return;
      //}

      function getApplet() {
        if(!_applet){
          _applet = document.getElementById(uploader.id);
        }
        return _applet;
      }

      function waitForAppletToLoadIn5SecsErrorOtherwise() {
          // Wait for applet init in 5 secs.
          waitCount += 500;
          if (waitCount > 5000) {
              IRIGO.toaster([{
                  message: '\If direct upload (Java) is not starting, please click here ->\
                <object\
                classid="java:plupload.Plupload.class"\
                codebase="/stabile/static/applet/"\
                codetype="application/x-java-applet"\
                archive="plupload.java.jar"\
                standby="The Java applet is loading..."\
                callback=""\
                name="javatest"\
                height="30"\
                width="30"\
                style="vertical-align:middle;">\
                    Plupload\
                </object>',
                  type: "message",
                  duration: 20000
              }]);
          }
          if (waitCount > 60000) {
              callback({success : false});
              console.log("giving up on Java applet...");
              return;
          }

          // Commented out to allow upload without Java
//          if (!initialized) {
          if (!initialized && features.java) {
              setTimeout(waitForAppletToLoadIn5SecsErrorOtherwise, 500);
          }
      }
      
      uploadInstances[uploader.id] = uploader;
      appletContainer = document.createElement('div');
      appletContainer.id = uploader.id + '_applet_container';
      appletContainer.className = 'plupload applet';

      plupload.extend(appletContainer.style, {
        // move the 1x1 pixel out of the way. 
        position : 'absolute',
        left: '-9999px',
        zIndex : -1
      });

      uploader.bind("Applet:Init", function() {
        var filters;
        initialized = uploader.initialized = true;
        if(uploader.settings.filters){
          filters = [];
          for(var i = 0, len = uploader.settings.filters.length; i < len; i++){
            filters.push(uploader.settings.filters[i].extensions);
          }
          getApplet().setFileFilters(filters.join(","));
          console.log("Applet inited");
        }
        callback({success : true});
      });

      document.body.appendChild(appletContainer);

      applet.inject(appletContainer, {
        archive: url,
        id: escape(uploader.id),
        code: 'plupload.Plupload',
        callback: 'plupload.applet.pluploadjavatrigger'
      });

      uploader.bind("UploadFile", function(up, file) {
          console.log('UploadFile', up, file);
          var settings = up.settings,
              abs_url = location.protocol + '//' + location.host;

          if(settings.url.charAt(0) === "/"){
            abs_url += settings.url;
          }
          else if(settings.url.slice(0,4) === "http"){
            abs_url = settings.url;
          }
          else{
            // relative
            abs_url += location.pathname.slice(0, location.pathname.lastIndexOf('/')) + '/' + settings.url;
          }
          if(file.url) {
              var download = new plupload.Downloader(file);
              download.start();
          } else {
              // converted to string since number type conversion is buggy in MRJ runtime
              // In Firefox Mac (MRJ) runtime every number is a double
              getApplet().uploadFile(lookup[file.id] + "", abs_url, document.cookie, settings.chunk_size, (settings.retries || 3));
          }
      });
   
      uploader.bind("SelectFiles", function(up){
        getApplet().openFileDialog();
      });

      uploader.bind("Applet:UploadProcess", function(up, javaFile) {
        var file = up.getFile(lookup[javaFile.id]);
        var finished = javaFile.chunk === javaFile.chunks;

        if (file.status != plupload.FAILED) {
          file.loaded = javaFile.loaded;
          file.size = javaFile.size;
          up.trigger('UploadProgress', file);
        }
        else{
            IRIGO.toast("uploadProcess status failed");
        }

        if (finished) {
          file.status = plupload.DONE;
          up.trigger('FileUploaded', file, {
            response : "File uploaded"
          });
        }
      });

      uploader.bind("Applet:SelectFiles", function(up, file) {
        var i, files = [], id;
        id = plupload.guid();
        lookup[id] = file.id;
        lookup[file.id] = id;

        var match = false;
        jQuery.each(uploader.files, function(i, val) {if (val.name == file.name) match=true;});
        if (match) {
          IRIGO.toast("You have already added a file with that name");
        } else {
            files.push(new plupload.File(id, file.name, file.size));
            // Trigger FilesAdded event if we added any
            if (files.length) {
                uploader.trigger("FilesAdded", files);
            }
        }
      });
      
      uploader.bind("Applet:GenericError", function(up, err) {
        uploader.trigger('Error', {
          code : plupload.GENERIC_ERROR,
          message : 'Generic error.',
          details : err.message,
          file : uploader.getFile(lookup[err.id])
        });
      });

      uploader.bind("Applet:IOError", function(up, err) {
        uploader.trigger('Error', {
          code : plupload.IO_ERROR,
          message : 'IO error.',
          details : err.message,
          file : uploader.getFile(lookup[err.id])
        });
      });

      uploader.bind("FilesRemoved", function(up, files) {
        for (var i = 0, len = files.length; i < len; i++) {
          getApplet().removeFile(lookup[files[i].id]);
        }
      });

      waitForAppletToLoadIn5SecsErrorOtherwise();

    }// end object arg
  });// end add runtime


});




