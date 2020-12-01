require([
//    'dojo/ready',
    'dojo/_base/event',
    'dojo/_base/html',
    'dojo/_base/lang',
    'dojo/_base/window',
    'dojo/dom',
    'dojo/dom-class',
    'dojo/dom-construct',
    'dojo/io/script',
    'dojo/query',
//    'dijit/Dialog',
    'dijit/TooltipDialog',
    'dijit/form/DropDownButton',
    'dojo/NodeList-dom'
], function(
        /*ready,*/
        event,
        html,
        lang,
        win,
        dom,
        domClass,
        domConstruct,
        ioScript,
        query,
        /*Dialog,*/
        TooltipDialog,
        DropDownButton
    ){

    var hasTundra = domClass.contains(win.body(), 'tundra');

    function addStyle(){
        if(!hasTundra){
            domClass.add(win.body(), 'tundra');
        }
    }

    function removeStyle(){
        if(!hasTundra){
            domClass.remove(win.body(), 'tundra');
        }
    }

    function loadStylesheet(){
        var head = win.doc.getElementsByTagName("head")[0];

        var embedCss = domConstruct.create("link", {
            type: "text/css",
            rel: "stylesheet",
            //href: "//docs.irigo.com/static/css/embed.css"
            href: "/stabile/static/docs/style.css"
        });
        // add tundra css if not there!
        // FIXME: copy paste the relevant parts from that stylesheet into embed.css
        // and rename tundra.
        if(!hasTundra){
            var tundraCss = domConstruct.create("link", {
                type: "text/css",
                rel: "stylesheet",
                href: "//ajax.googleapis.com/ajax/libs/dojo/1.7.2/dijit/themes/tundra/tundra.css"
            });
            head.appendChild(tundraCss);
        }
        head.appendChild(embedCss);
    }

    function getTopic(url){
        if (url.indexOf('docs.irigo')!=-1) url += '/jsonp';
        else if (url.indexOf('get_engines')!=-1) ;
        else if (url.indexOf('https://www.origo.io')!=-1) url += '/?feed=json';
        var args = {
//            url: url + (url.indexOf('docs.irigo')!=-1?'/jsonp':'/?feed=json'),
            url: url,
            callbackParamName: 'callback'
        };
        return ioScript.get(args);
    }

    function tooltip(node, args){
        node = dom.byId(node);
        var topic_url = node.href;

        var dialog = new TooltipDialog({
            style:"width:300px;"
        });

        var button = new DropDownButton({
            dropDown: dialog,
            baseClass:"irigo-tooltip-base",
            iconClass:"irigo-tooltip-base-icon",
            onOpen: function(){
                addStyle();
            },
            onClose: function(){
                removeStyle();
            },
            onClick: function(e){
                if(dialog.get('content') == ''){
                    var dfd = getTopic(topic_url);
                    dfd.then(function(js){
                        //console.log(js.excerpt instanceof Array);
                        //dialog.set('content', '<p>' + js.excerpt + ' (<a href="' + topic_url + '" target="_blank">more</a>)</p>');
                        var ihtml = '<p>' + (js instanceof Array?js[0].excerpt:js.excerpt) + ' (<a href="' + topic_url + '" target="_blank">more</a>)</p>';
                        dialog.set('content', ihtml);
                    });
                }
                // else, we've already loaded the content.
                event.stop(e);
                return false;
            }
        });
        // replacing the a tag!
        html.place(button.domNode, node, 'replace');
    }

    function text(node, args){
        node = dom.byId(node);

        var topic_url = node.href;

        var dfd = getTopic(topic_url);
        dfd.then(function(js){
            var ihtml = '<!-- h3>' + (js instanceof Array?js[0].title:js.title) + '</h3 -->' + '<p>' + (js instanceof Array?js[0].excerpt:js.excerpt) + '</p>';
            var wrapper = domConstruct.create('div', {
                innerHTML: ihtml
            });
            // replacing the a tag!
            html.place(wrapper, node, 'replace');
        });
    }

    function loadSystem(node, args){
        if (args) {
//        var topic_url = "https://irigo.com/store/apps/" + args +
//                "/?json=1&include=title,excerpt,custom_fields&custom_fields=master,vcpu,bschedule,start,instances,monitors,memory,networktype1,name,storagepool";
            var topic_url = "https://irigo.com/app?p=" + args +
                    "&json=1&include=title,excerpt,custom_fields&custom_fields=master,vcpu,bschedule,start,instances,monitors,memory,networktype1,name,storagepool";

            var topicargs = {
                //url: url + '/jsonp',
                url: topic_url,
                callbackParamName: 'callback'
            };
            var dfd = ioScript.get(topicargs);

            //var dfd = getTopic(topic_url);

            dfd.then(function(js){
                if (js && js.page && js.page.custom_fields) {
                    var sys = js.page.custom_fields;
                    sys.excerpt = js.page.excerpt;
                    sys.title = js.page.title;
                    systembuilder.system.loadSystem(sys);
                } else {
                    systembuilder.system.loadSystem();
                }
            });
        } else {
            systembuilder.system.loadSystem();
        }
    }

    loadStylesheet();

    lang.extend(query.NodeList, {
        irigoTooltip: query.NodeList._adaptAsForEach(tooltip),
        irigoText: query.NodeList._adaptAsForEach(text),
        irigoLoadSystem: query.NodeList._adaptAsForEach(loadSystem)
    });

    if (typeof IRIGO === 'undefined') IRIGO = [];
//    IRIGO = {getTopic: getTopic};
    IRIGO.getTopic = getTopic;
});

