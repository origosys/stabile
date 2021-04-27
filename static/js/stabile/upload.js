define([
"dojo/query",
//'java/applet',
//'plupload/java',
//    'plupload/moxie',
    'plupload/plupload',
//'plupload/ui',
'dijit/Dialog'
], function(query){

    var upload = {};
    // shows the upload dialog with plupload inside
    upload.showDialog = function() {
        if (!upload.inited) upload.init();
        upload.dialog.show();
    };
    upload.updateList = updateList;
    upload.files_uploaded = false;
    upload.inited = false;
    window.upload = upload;

    function handleStatus(file) {
        var actionClass, title;

        if (file.status == plupload.DONE) {
            actionClass = 'plupload_done';
            title = "done";
        }

        if (file.status == plupload.FAILED) {
            actionClass = 'plupload_failed';
            //title = "failed: " + file.error_message;
            if (file.error_message) title = file.error_message;
        }

        if (file.status == plupload.QUEUED) {
            actionClass = 'plupload_delete';
            title = "queued";
        }

        if (file.status == plupload.UPLOADING) {
            actionClass = 'plupload_uploading';
            title = "uploading";
        }
        $('#' + file.id).addClass(actionClass);
        $('#' + file.id).find('a').css('display', 'block').attr('title', title);
    }

    function updateTotalProgress() {
        // removed target here
        $('div.plupload_progress').css('display', 'block');
        $('span.plupload_total_status').html(uploader.total.percent + '%');
        $('div.plupload_progress_bar').css('width', uploader.total.percent + '%');
        $('span.plupload_upload_status').html('Uploaded ' + uploader.total.uploaded + '/' + uploader.files.length + ' files');

        // All files are uploaded
        if (uploader.total.uploaded == uploader.files.length) {
            uploader.stop();
        }
    }

    function updateList() {
        var fileList = $('ul.plupload_filelist'),
            hasQueuedFiles = false;

        fileList.html('');

        plupload.each(uploader.files, function(file) {
            if (file.status == plupload.DONE) {
            } else if(file.status == plupload.QUEUED){
                hasQueuedFiles = true;
            }

            fileList.append(
                '<li id="' + file.id + '">' +
                    '<div class="plupload_file_name"><span>' + file.name + '</span></div>' +
                    '<div class="plupload_file_action"><a href="#images"></a></div>' +
                    '<div class="plupload_file_status">' + file.percent + '%</div>' +
                    '<div class="plupload_file_size">' + plupload.formatSize(file.size) + '</div>' +
                    '<div class="plupload_clearer">&nbsp;</div>' +
                    '</li>');

            handleStatus(file);

            $('#' + file.id + '.plupload_delete a').click(function(e) {
                uploader.removeFile(file);
                $('#' + file.id).empty();
                e.preventDefault();
            });
        });

        $('a.plupload_start').toggleClass('disabled', !hasQueuedFiles || uploader.state === plupload.STARTED);
        $('span.plupload_total_file_size').html(plupload.formatSize(uploader.total.size));

        // Scroll to end of file list
        fileList[0].scrollTop = fileList[0].scrollHeight;

        updateTotalProgress();

        // Re-add drag message if there is no files
        if (!uploader.files.length && uploader.features.dragdrop && uploader.settings.dragdrop) {
            dojo.place('<li class="plupload_droptext" ondrop="uploader.drop(event)" ondragover="uploader.dragover(event);" ondragleave="uploader.dragleave(event);">' + ("Drag image file here.") + '</li>', id + '_filelist', 'last');
        }
    }//updateList

    function myInit() {
        $('a.plupload_add').click(function(e){
            var old_files = [];
            plupload.each(uploader.files, function(file){
                if(file.status == plupload.DONE || file.status == plupload.FAILED){
                    old_files.push(file);
                }
            });
            plupload.each(old_files, function(file){
                $('#' + file.id).empty();
                uploader.removeFile(file);
            });
        });
        $('#urlupload').focus(function(e){
            jQuery('a.plupload_add_url').show();
            jQuery('a.plupload_add').hide();
        });

        $('#urlupload').blur(function(e){
            if (!$("#urlupload").val()) {
                jQuery('a.plupload_add_url').hide();
                jQuery('a.plupload_add').show();
            }
        });
        $('a.plupload_add_url').click(function(e){
            var old_files = [];
            plupload.each(uploader.files, function(file){
                if(file.status == plupload.DONE || file.status == plupload.FAILED){
                    old_files.push(file);
                }
            });
            plupload.each(old_files, function(file){
                $('#' + file.id).empty();
                uploader.removeFile(file);
            });
            if ($("#urlupload").val()) {
                var urlfile = $("#urlupload").val();
                if(/^(http|https):\/\/[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(\/.*)?$/i.test(urlfile)) {
                    $(".plupload_add_url").toggleClass('disabled', true);
                    jQuery.get("/stabile/images?action=urlupload\&url=" + encodeURIComponent(urlfile) + "\&probe=1",
                        function(data) {
                            if (data.status == 'OK') {
                                var match = false;
                                jQuery.each(uploader.files, function(i, val) {if (val.name == data.name) match=true;});
                                if (match) {
                                    IRIGO.toast("You have already added a file with that name");
                                } else {
                                    var nfile = new plupload.File({name: data.name, size: data.size, destroy: function(){;}  });
                                    nfile.url = urlfile;
                                    nfile.path = data.path;
                                    //var nfile = {id: 'url_' + Date.now(), name: data.name, size: data.size, status:1, loaded:0, percent:0, url: urlfile, path: data.path, destroy: function(){;}, getSource: function(){return {size: data.size};}};
                                    uploader.files.push(nfile);
                                    updateList();
                                }
                                $("#urlupload").val('');
                            } else {
                                IRIGO.toast("The file could not be downloaded. " + data.message);
                            }
                            $(".plupload_add_url").toggleClass('disabled', false);
                            jQuery('a.plupload_add_url').hide();
                            jQuery('a.plupload_add').show();
                        });
                } else {
                    IRIGO.toast("That's not a valid URL. Please type in a http(s) URL which points to the image you want to upload.");
                }
            }
            e.preventDefault();
        });

        $('a.plupload_start').click(function(e) {
            if (!$('a.plupload_start').hasClass('disabled')) {
                uploader.start();
                $('a.plupload_start').toggleClass('disabled', true);
            }
            e.preventDefault();
        });

        $('a.plupload_stop').click(function(e) {
            var finished = true;
            uploader.stop();
            $('a.plupload_start').toggleClass('disabled', !finished);
            e.preventDefault();
        });

        // Initially start button is disabled.
        $('a.plupload_start').addClass('disabled');
    }

    upload.init = function() {
        plupload.Downloader = function(file) {
            var percent = 0;
            function progress() {
                if (percent<100) {
                    jQuery.get("/stabile/images?action=urlupload\&path=" + encodeURIComponent(file.path) + "\&getsize=1",
                        function(data) {
                            if (data.status == 'OK') {
                                percent = Math.round(100*data.size/file.size);
                                file.loaded = data.size;
                                file.percent = percent;
                                uploader.trigger('UploadProgress', file);
                                setTimeout(function() {
                                    progress();
                                }, 2000);
                            }
                        });
                } else {
                    file.status = plupload.DONE;
                    console.log("done downloading", file);
                    uploader.trigger('FileUploaded', file);
                }
            }

            plupload.extend(this, {
                start: function() {
                    jQuery.get("/stabile/images?action=urlupload\&url=" + encodeURIComponent(file.url)
                        + "\&path=" + encodeURIComponent(file.path)
                        + "\&name=" + encodeURIComponent(file.name)
                        + "\&size=" + file.size,
                        function(data) {
                            if (data.status == 'OK') {
                                progress();
                            }
                        }
                    )
                }
            });
        }
        if(!upload.dialog) {
            var ucontent =  '<div class="plupload_wrapper plupload_scroll">' +
            '<div id="uploadDialogDiv_container" class="plupload_container">' +
            '<div class="plupload">' +
            '<div class="plupload_header">' +
            '<div class="plupload_header_content">' +
            '<div class="plupload_header_text">Add files to the upload queue and click the start button.</div>' +
            '</div>' +
            '</div>' +

            '<div class="plupload_content" style="margin-bottom:10px;">' +
            '<div class="plupload_filelist_header">' +
            '<div class="plupload_file_name">Filename</div>' +
            '<div class="plupload_file_action">&nbsp;</div>' +
            '<div class="plupload_file_status"><span>Status</span></div>' +
            '<div class="plupload_file_size">Size</div>' +
            '<div class="plupload_clearer">&nbsp;</div>' +
            '</div>' +

            '<ul id="uploadDialogDiv_filelist" class="plupload_filelist"></ul>' +

            '<div class="plupload_filelist_footer">' +
            '<div class="plupload_file_name">' +
            '<span class="plupload_upload_status"></span>' +
            '</div>' +
            '<div class="plupload_file_action"></div>' +
            '<div class="plupload_file_status"><span class="plupload_total_status">0%</span></div>' +
            '<div class="plupload_file_size"><span class="plupload_total_file_size">0 b</span></div>' +
            '<div class="plupload_progress" style="display:none;">' +
            '<div class="plupload_progress_container">' +
            '<div class="plupload_progress_bar"></div>' +
            '</div>' +
            '</div>' +
            '<div class="plupload_clearer">&nbsp;</div>' +
            '</div>' +
            '</div>' +
            '<div id="uploadButtons">' +
            '<input style="width:250px; height: 30px; font-size:90%;" id="urlupload" placeholder="Add image file from URL" class="form-control pull-left input-small">' +
            '<span class="plupload_buttons">' +
            '<a href="#images" style="display:none;" class="plupload_button plupload_add_url btn btn-info btn-sm">Add from URL</a> ' +
            '<span id="plupload_container"><a href="#images" id="uploadDialogDiv_browse" class="plupload_button plupload_add btn btn-info btn-sm">Add local file</a></span> ' +
            '<a href="#images" class="plupload_button plupload_start btn btn-success btn-sm">Start upload</a>' +
            '</span>' +
            '</div>' +
            '</div>' +
            '</div>' +
            '<input type="hidden" id="uploadDialogDiv_count" name="uploadDialogDiv_count" value="0" />' +
            '</div>';

            var content = [
            '<div>',
            '    <div style="float:right; margin-right:10px;"><a href="https://www.origo.io/info/stabiledocs/web/images/upload" rel="help" target="_blank" id="irigo-upload-tooltip">help</a></div>',
            '    <div id="uploadDialogDiv" style="width: 450px; height: 360px; margin:10px;">' +
                ucontent +
            '</div>',
            '</div>'].join('\n');

            upload.dialog = new dijit.Dialog({ id: 'uploadDialog', onCancel: function() {if (upload.files_uploaded) {upload.files_uploaded=false;images.grid.refresh();}}});
            upload.dialog.set('title', 'Image Transfers');
            upload.dialog.set('content', content);
            var q = dojo.query('#irigo-upload-tooltip', upload.dialog.domNode);
            if(q.irigoTooltip){q.irigoTooltip();};

            var uploader = new plupload.Uploader({
                browse_button : document.getElementById('uploadDialogDiv_browse'),
                runtimes : 'html5',
                url: '/stabile/images?action=upload',
                chunk_size : '10mb',
                drop_element: ['uploadDialogDiv_filelist', 'uploadDialogDiv_browse'],
                java_applet_url: '/stabile/static/applet/plupload.java.jar',
                loader_url: '/stabile/static/img/loader.gif',
    //            dragdrop : true,
                container : document.getElementById("plupload_container"),
                filters : {
                    max_file_size : '200gb',
                    prevent_duplicates: true,
                    mime_types: [
                        {title : "Native image files", extensions : "qcow2"},
                        {title : "Foreign image files", extensions : "img,vdi,vmdk"},
                        {title : "CDs", extensions : "iso"}
                    ]
                },
                init: {
                    Init: function() {
                        if (!jQuery("#urlupload").val()) {
                            jQuery('a.plupload_add_url').hide();
                            jQuery('a.plupload_add').show();
                        }
                        myInit();
                        //updateList();

                    },
                    Error: function(up, err) {
                        var file = err.file, message;
                        if (file) {
                            message = err.message;
                            if (err.details) {
                                message += " (" + err.details + ")";
                                IRIGO.toast(("Error: ") + message);
                                console.log(message, err);
                            }
                            if (err.code == plupload.FILE_SIZE_ERROR) {
                                IRIGO.toast(("Error: File to large: ") + file.name);
                            }
                            else if (err.code == plupload.FILE_EXTENSION_ERROR) {
                                IRIGO.toast(("Error: Invalid file extension: ") + file.name);
                            }
                            else {
                                IRIGO.toast("Error #" + err.code + ": " + err.message);
                            }
                        }
                        //$('div.plupload_progress').css('display', 'none');
                    },
                    FilesAdded: function(up, files) {
                        updateList();
                    },
                    FileUploaded: function(up, file, res){
                        if (res && res.response && res.response.indexOf('Error')==0) {
                            file.status = plupload.FAILED;
                            file.error_message = res.response;
                            IRIGO.toast(res.response);
                        }
                        handleStatus(file);
                        dojo.publish('upload:file_uploaded');
                        upload.files_uploaded = true;
                        //$('div.plupload_progress').css('display', 'none');
                    },
                    QueueChanged: function() {
                        updateList();
                    },
                    StateChanged: function(up) {
                        if (uploader.state === plupload.STARTED) {
                            $('span.plupload_upload_status,div.plupload_progress,a.plupload_stop').css('display', 'block');
                            $('span.plupload_upload_status').html('Uploaded 0/' + uploader.files.length + ' files');
                        }
                        else {
                            $('a.plupload_stop,div.plupload_progress').css('display', 'none');
                            $('a.plupload_delete').css('display', 'block');
                        }
                        if (up.state == plupload.STOPPED) {
                            updateList();
                        }
                    },
                    UploadProgress: function(up, file) {
                        // Set file specific progress
                        $('#' + file.id + ' div.plupload_file_status').html(file.percent + '%');
                        handleStatus(file);
                        updateTotalProgress();
                    },
                    BeforeUpload: function(up, file) {
                    },
                    UploadFile: function(up, file) {
                        if(file.url) {
                            console.log("downloading file", up, file);
                            var download = new plupload.Downloader(file);
                            download.start();
                            return false;
                        } else {
                            console.log("uploading file", up, file);
                        }
                    }
                }
            });

            uploader.init();
            window.uploader = uploader;
            upload.inited = true;
        }
    }
    return upload;
});

