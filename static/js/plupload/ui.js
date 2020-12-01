define([
    "dojo/query",
    "dojo/NodeList-html", // NodeList::html()
    "dojo/NodeList-traverse", // NodeList::children()
    "dojo/NodeList-manipulate" // NodeList::val()
],function(query){

    var d = dojo;
    var $ = query;

    var uploaders = {};

    function _(str) {
        return plupload.translate(str) || str;
    }

    function pluploadQueue(target, settings){

        var uploader = window.uploader;
        var id = d.attr(target, 'id');
        //if(settings.loader_url){
        //    target.innerHTML = '<div style="width:100%;text-align:center"><img src="' + settings.loader_url + '" /></div>';
        //}

        if(!id){
            id = plupload.guid();
            d.attr(target, 'id', id);
        }

        /*    uploader = new plupload.Uploader(plupload.extend({
         dragdrop : true,
         container : id
         }, settings)); */

        // renderUI(id, target);

        // window.uploader = uploader;

        // Call preinit function
        if (settings.preinit) {
            settings.preinit(uploader);
        }

        uploaders[id] = uploader;

        function handleStatus(file) {
            var actionClass, title;

            if (file.status == plupload.DONE) {
                actionClass = 'plupload_done';
                title = "done";
            }

            if (file.status == plupload.FAILED) {
                actionClass = 'plupload_failed';
                title = "failed: " + file.error_message;
            }

            if (file.status == plupload.QUEUED) {
                actionClass = 'plupload_delete';
                title = "queued";
            }

            if (file.status == plupload.UPLOADING) {
                actionClass = 'plupload_uploading';
                title = "uploading";
            }
            var status_elms = $('#' + file.id).attr('class', actionClass);
            status_elms.query('a').style('display', 'block').attr('title', title);
        }

        function updateTotalProgress() {
            // removed target here
            $('div.plupload_progress').style('display', 'block');
            $('span.plupload_total_status').html(uploader.total.percent + '%');
            $('div.plupload_progress_bar').style('width', uploader.total.percent + '%');
            $('span.plupload_upload_status').html('Uploaded ' + uploader.total.uploaded + '/' + uploader.files.length + ' files');

            // All files are uploaded
            if (uploader.total.uploaded == uploader.files.length) {
                uploader.stop();
            }
        }

        function updateList() {
            var fileList = $('ul.plupload_filelist', target),
                inputCount = 0,
                inputHTML,
                hasQueuedFiles = false;

            fileList.html('');

            plupload.each(uploader.files, function(file) {
                inputHTML = '';

                if (file.status == plupload.DONE) {
                    if (file.target_name) {
                        inputHTML += '<input type="hidden" name="' + id + '_' + inputCount + '_tmpname" value="' + plupload.xmlEncode(file.target_name) + '" />';
                    }
                    inputHTML += '<input type="hidden" name="' + id + '_' + inputCount + '_name" value="' + plupload.xmlEncode(file.name) + '" />';
                    inputHTML += '<input type="hidden" name="' + id + '_' + inputCount + '_status" value="' + (file.status == plupload.DONE ? 'done' : 'failed') + '" />';
                    inputCount++;
                    $('#' + id + '_count').val(inputCount);
                } else if(file.status == plupload.QUEUED){
                    hasQueuedFiles = true;
                }

                fileList.addContent(
                    '<li id="' + file.id + '">' +
                        '<div class="plupload_file_name"><span>' + file.name + '</span></div>' +
                        '<div class="plupload_file_action"><a href="#images"></a></div>' +
                        '<div class="plupload_file_status">' + file.percent + '%</div>' +
                        '<div class="plupload_file_size">' + plupload.formatSize(file.size) + '</div>' +
                        '<div class="plupload_clearer">&nbsp;</div>' +
                        inputHTML +
                        '</li>');

                handleStatus(file);

                $('#' + file.id + '.plupload_delete a').onclick(function(e) {
                    $('#' + file.id).empty();
                    uploader.removeFile(file);
                    e.preventDefault();
                });
            });

            $('a.plupload_start', target).toggleClass('disabled', !hasQueuedFiles || uploader.state === plupload.STARTED);
            $('span.plupload_total_file_size', target).html(plupload.formatSize(uploader.total.size));

            // What plupload_add_text?
            // if (uploader.total.queued === 0) {
            //  $('span.plupload_add_text', target).text(_('Add files.'));
            // } else {
            //  $('span.plupload_add_text', target).text(uploader.total.queued + ' files queued.');
            // }

            // Scroll to end of file list
            fileList[0].scrollTop = fileList[0].scrollHeight;

            updateTotalProgress();

            // Re-add drag message if there is no files
            if (!uploader.files.length && uploader.features.dragdrop && uploader.settings.dragdrop) {
                d.place('<li class="plupload_droptext" ondrop="uploader.drop(event)" ondragover="uploader.dragover(event);" ondragleave="uploader.dragleave(event);">' + _("Drag image file here.") + '</li>', id + '_filelist', 'last');
            }
        }//updateList

        // Drag and drop not possible with Java due to JS security. Below just for fun...
        uploader.dragover = function(ev) {
            ev.preventDefault();
            $("#uploadDialogDiv_filelist").addClass("dragdrop_active");
        }
        uploader.dragleave = function(ev) {
            ev.preventDefault();
            $("#uploadDialogDiv_filelist").removeClass("dragdrop_active");
        }
        uploader.drop = function(ev) {
            ev.preventDefault();
            console.log("dropped", ev, ev.dataTransfer.files);
        }


        uploader.myInit = function(up, res) {

            //   renderUI(id, target);

            $('a.plupload_add', target).attr('id', id + '_browse');

            up.settings.browse_button = id + '_browse';

            // Enable drag/drop
            if (up.features.dragdrop && up.settings.dragdrop) {
                console.log('drag drop');
                up.settings.drop_element = id + '_filelist';
                d.place('<li class="plupload_droptext">' + _("Drag image file here.") + '</li>', id + '_filelist', 'last');
            }
            //$('#' + id + '_container').attr('title', 'Using runtime: ' + res.runtime);

            $('a.plupload_add', target).onclick(function(e){
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
                //uploader.trigger('SelectFiles');
                //e.preventDefault();
            });
            $('#urlupload', target).onfocus(function(e){
                // Commented out to allow upload without Java
                //if (uploader.initialized) {
                jQuery('a.plupload_add_url').show();
                jQuery('a.plupload_add').hide();
                //}
            });
            $('#urlupload', target).onblur(function(e){
//            if (uploader.initialized && !$("#urlupload").val()) {
                if (!$("#urlupload").val()) {
                    jQuery('a.plupload_add_url').hide();
                    jQuery('a.plupload_add').show();
                }
            });
            $('a.plupload_add_url', target).onclick(function(e){
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
                                        uploader.files.push({id: 'url_' + Date.now(), name: data.name, size: data.size, status:1, loaded:0, percent:0, url: urlfile, path: data.path});
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

            $('a.plupload_start', target).onclick(function(e) {
                if (!d.hasClass(target, 'disabled')) {
                    uploader.start();
                    $('a.plupload_start', target).toggleClass('disabled', true);
                }
                e.preventDefault();
            });

            $('a.plupload_stop', target).onclick(function(e) {
                var finished = true;
                uploader.stop();
                $('a.plupload_start', target).toggleClass('disabled', !finished);
                e.preventDefault();
            });

            // Initially start button is disabled.
            $('a.plupload_start', target).addClass('disabled');

        }

        uploader.myInit(uploader);

        // Event handlers
        //uploader.bind('Init', uploader.myInit);// end uploader.bind('Init',...
        uploader.bind('Init', function(){
            if (!$("#urlupload").val()) {
                jQuery('a.plupload_add_url').hide();
                jQuery('a.plupload_add').show();
            }
            updateList();
        });

        uploader.bind('StateChanged', function() {
            if (uploader.state === plupload.STARTED) {
                // $('li.plupload_delete a,div.plupload_buttons', target).style('display', 'none');
                // removed target so we can have the progressbar several place
                $('span.plupload_upload_status,div.plupload_progress,a.plupload_stop', target).style('display', 'block');
                $('span.plupload_upload_status', target).html('Uploaded 0/' + uploader.files.length + ' files');
            }
            else {
                $('a.plupload_stop,div.plupload_progress', target).style('display', 'none');
                $('a.plupload_delete', target).style('display', 'block');
            }
        });

        uploader.bind('QueueChanged', updateList);

        uploader.bind('StateChanged', function(up) {
            if (up.state == plupload.STOPPED) {
                updateList();
            }
        });

        uploader.bind('FileUploaded', function(up, file) {
            handleStatus(file);
        });

        uploader.bind("UploadProgress", function(up, file) {
            // Set file specific progress
            $('#' + file.id + ' div.plupload_file_status', target).html(file.percent + '%');

            handleStatus(file);
            updateTotalProgress();
        });

        uploader.bind('FileUploaded',
            function(up, file){
                dojo.publish(upload.FILE_UPLOADED);
            });

        uploader.bind("UploadFile", function(up, file) {
            console.log('UploadFile...', up, file);
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
                console.log("uploading file", up, file);
            }
        });



    }//pluploadQueue

    dojo.extend(dojo.NodeList, {
        pluploadQueue: dojo.NodeList._adaptAsForEach(pluploadQueue)
    });

});


