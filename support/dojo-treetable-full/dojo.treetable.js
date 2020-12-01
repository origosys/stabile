dojo.require("dojo.dnd.Source");


/**
 * dojo TreeTable
 */
var TreeTable = function(config) {
    this.config = config;
    this.id = config.renderTo + '_TreeTable';
    this.nodes = {};
    this._nodes = {};
    
    if (this.config.nodes) {
        for (var i in this.config.nodes) {
            this.addNode(this.config.nodes[i]);
        }
    }
}

TreeTable.prototype.bodyEl = function() {
    return this.tbodyEl;
}

TreeTable.prototype.addNode = function(node) {
    if (typeof this.nodes[node.pid] == 'undefined') {
        this.nodes[node.pid] = [];
    }
    // if dataObject was received
    if (!(node instanceof TreeNode)) {
        node = new TreeNode(node, this);
    }
    this.nodes[node.pid].push(node);
    this._nodes[node.id] = node;
}

TreeTable.prototype.createSibling = function() {
    dojo.query('#' + this.id + ' .node-sibling').orphan();
    var el = dojo.doc.createElement("tr");
    el.className = 'node-hidden node-sibling';
    el.innerHTML = '<td></td><td></td><td></td>';
    return el;
}

TreeTable.prototype.siblingFix = function() {
    var el = this.createSibling();
    this.bodyEl().appendChild(el);
}



TreeTable.prototype.render = function() {
    var to = dojo.byId(this.config.renderTo);
    
    var tableEl = dojo.doc.createElement('table');
    tableEl.id = this.id;
    tableEl.className = 'dojo-treetable';
    if (this.config.width)
        tableEl.style.width = this.config.width
    
    var theadEl = dojo.doc.createElement('thead');
    tableEl.appendChild(theadEl);
    
    var trEl = dojo.doc.createElement('tr');
    theadEl.appendChild(trEl);
    
    for (var i in this.config.cm) {
        var thEl = dojo.doc.createElement('th');
        thEl.innerHTML = this.config.cm[i].text;
        if (this.config.cm[i].width) {
            thEl.style.width = this.config.cm[i].width;
        }
        trEl.appendChild(thEl);
    }
    var tbodyEl = dojo.doc.createElement('tbody');
    tbodyEl.id = this.id + '_tbody';
    tableEl.appendChild(tbodyEl);
    this.tbodyEl = tbodyEl;
    
    if (!this.nodes[0])
        return;
    for (var i in this.nodes[0]) {
        node = this.nodes[0][i];
        node.render();
    }
    to.appendChild(tableEl);
    // fix for nextSibling
    this.siblingFix();
}

TreeTable.prototype.node = function(id) {
    return this._nodes[id];
}

TreeTable.prototype.colorize = function() {
    dojo.query('#' + this.id + '_tbody .dojoxGridRowOdd').removeClass('dojoxGridRowOdd');
    
    var nodes = dojo.query('#' + this.id + '_tbody tr.node-visible');
    for (var i = 0, n = nodes.length; i < n; i++) {
        if (i % 2) {
            dojo.addClass(nodes[i], 'dojoxGridRowOdd');
        }
    }
}

/** 
 * TreeNode
 */
var TreeNode = function(config, tree) {
    this.config = config;
    this.id = config.id;
    this.elId = 'node_' + this.id;
    this.pid = config.pid;
    this.tree = tree;
    this.expanded = false;
    this._visibleChilds = [];
}

TreeNode.prototype.el = function() {
    return this.nodeEl;
}

TreeNode.prototype.hasChilds = function() {
    return (typeof this.tree.nodes[this.id]) != 'undefined' && this.tree.nodes[this.id].length > 0;
}

TreeNode.prototype.lastRenderedChild = function() {
    if (this.hasChilds()) {
        var nodes = this.tree.nodes[this.id];
        var last = nodes[nodes.length - 1];
        var all = [last].concat(last.childsAll());
        var last;
        for (var i in all) {
            if (all[i].rendered)
                last = all[i];
        }
        return last;
    } else
        return false;
}

TreeNode.prototype.childs = function() {
    return this.hasChilds() ? this.tree.nodes[this.id] : [];
}

TreeNode.prototype.childsAll = function() {
    var nodes = [];
    
    var _nodes = this.childs();
    for (var i in _nodes) {
        var node = _nodes[i];
        nodes = nodes.concat(node, node.childsAll());
    }
    return nodes;
}

TreeNode.prototype.hasNode = function(node) {
    var nodes = this.childsAll();
    for (var i in nodes) {
        if (nodes[i].id == node.id)
            return true;
    }
    return false;
}

TreeNode.prototype.icon = function() {
    return this.iconEl;
}

TreeNode.prototype.titleEl = function() {
    return dojo.query('#' + this.elId + ' .node-title')[0];
}

TreeNode.prototype.visibleChilds = function() {
    var nodes = [];
    if (!this.hasChilds())
        return nodes;
    
    var _nodes = this.childs();
    for (var i in _nodes) {
        var node = _nodes[i];
        if (node.nodeEl && dojo.hasClass(node.nodeEl, 'node-visible')) {
            nodes.push(node);
        } else 
            continue;
        
        nodes = nodes.concat(node.visibleChilds());
    }
    return nodes;
}

TreeNode.prototype.lvl = function() {
    if (this.pid == 0) {
        return 0;
    }
    
    return 1 + this.tree._nodes[this.pid].lvl();
}

TreeNode.prototype.updateLvl = function() {
    if (this.rendered)
        this.dndSourceEl.style.paddingLeft =  (this.lvl() * this.tree.config.indent) + 'px';
}

TreeNode.prototype.show = function() {
    dojo.removeClass(this.elId, 'node-hidden');
    dojo.addClass(this.elId, 'node-visible');
}

TreeNode.prototype.hide = function() {
    dojo.removeClass(this.elId, 'node-visible');
    dojo.addClass(this.elId, 'node-hidden');
}

TreeNode.prototype.iconUpdate = function() {
    var icon = this.icon();
    
    dojo.removeClass(icon, 'folder-expanded');
    dojo.removeClass(icon, 'folder-collapsed');
    dojo.removeClass(icon, 'doc');
    
    if (this.hasChilds()) {
        if (this.expanded)
            dojo.addClass(icon, 'folder-expanded');
        else
            dojo.addClass(icon, 'folder-collapsed');
    } else {
        dojo.addClass(icon, 'doc');
        this.expanded = false;
    }
}

TreeNode.prototype.expand = function() {
    if (!this.hasChilds()) {
        return;
    }
    var _nodes = this.tree.nodes[this.id].concat().reverse();
    for (var i in _nodes) {
        if (!_nodes[i].rendered) {
            _nodes[i].render();
        }
        _nodes[i].show();
    }
    this.expanded = true;
    
    this.iconUpdate();
    
    for (var i in this._visibleChilds) {
        this._visibleChilds[i].show();
    }
    this.tree.colorize();
}

TreeNode.prototype.collapse = function() {
    if (!this.hasChilds()) {
        return;
    }
    
    this._visibleChilds = this.visibleChilds();
    
    for (var i in this._visibleChilds) {
        this._visibleChilds[i].hide();
    }
    this.expanded = false;
    
    var icon = this.icon();
    dojo.addClass(icon, 'folder-collapsed');
    dojo.removeClass(icon, 'folder-expanded');
    
    this.tree.colorize();
}

TreeNode.prototype.toggle = function() {
    if (this.expanded)
        this.collapse();
    else
        this.expand();
}

TreeNode.prototype.onDrop = function(src, nodes, copy) {
    var toNode = this.ssnode;
    var srcNode = src.ssnode;
    srcNode.move(toNode);
    toNode.tree.colorize();
}

TreeNode.prototype.render = function() {
    var el = dojo.doc.createElement("tr");
    this.nodeEl = el;
    
    if (this.pid != 0) {
        dojo.addClass(el, 'node-hidden');
    } else {
        dojo.addClass(el, 'node-visible');
    }
    
    el.id = this.elId;
    
    // checkbox
    var cbEl = dojo.doc.createElement('td');
    cbEl.innerHTML = '<input type="checkbox">';
    el.appendChild(cbEl);
    
    // title
    this.type = this.hasChilds() ? 'folder' : 'doc';
    var cls = this.hasChilds() ? 'folder-collapsed' : 'doc';
    
    var titleEl = dojo.doc.createElement('td');
    titleEl.style.paddingLeft = (this.lvl() * this.tree.config.indent) + 'px';
    titleEl.style.paddingRight = '30px';
    titleEl.id = 'dnd_source_' + this.id;
    
    var aEl = dojo.doc.createElement('a');
    dojo.addClass(aEl, 'node-icon');
    dojo.addClass(aEl, cls);
    titleEl.appendChild(aEl);
    this.iconEl = aEl;
    
    var spanEl = dojo.doc.createElement('span');
    spanEl.innerHTML = this.config.title;
    spanEl.className = 'node-title';
    titleEl.appendChild(spanEl);
    
    el.appendChild(titleEl);
    // title end
    
    for (var i = 2, n = this.tree.config.cm.length; i < n; i++) {
        var cm = this.tree.config.cm[i];
        var oEl = dojo.doc.createElement('td');
        if (cm.renderer) {
            oEl.innerHTML = cm.renderer(this);
        } else {
            oEl.innerHTML = this.config[cm.data];
        }
        el.appendChild(oEl);
    }
    
    // insert element
    if (this.pid == 0)
        this.tree.tbodyEl.appendChild(el);
    else {
        var node = this.tree._nodes[this.pid].nodeEl;
        node.parentNode.insertBefore(el, node.nextSibling);
    }
    
    // add events
    dojo.connect(this.iconEl, 'onclick', this, 'toggle');
    
    // render all childs nodes
    /*if (this.hasChilds()) {
        var _nodes = this.tree.nodes[this.id].concat().reverse();
        for (var i in _nodes) {
            _nodes[i].render();
        }
    }*/
    
    // d'n'd
    this.dndSourceEl = titleEl;
    this.dndSource = new dojo.dnd.Source(this.dndSourceEl);
    this.dndSource.ssnode = this;
    this.dndSource.insertNodes(false, [spanEl]);
    this.dndSource.onDrop = this.onDrop;
    
    this.rendered = true;
}

TreeNode.prototype.move = function(toNode) {
    // update connection in the tree
    if (this.hasNode(toNode) || toNode.id == this.id) {
        return false;
    }
    if (!toNode.expanded) {
        toNode.expand();
    }
    
    var fromNode = this.tree._nodes[this.pid];
    
    /* Search afterEl */
    var afterEl, afterNode, lastNode;
    if (lastNode = toNode.lastRenderedChild()) {
        afterNode = lastNode;
    } else {
        afterNode = toNode;
    }
    
    if (toNode.hasNode(afterNode)) {
        afterEl = afterNode.el().nextSibling;
    } else
        afterEl = afterNode.el();
    
    /*
     * last element fix
     * insert sibling node & using it as afterEl
     * it will be removed at the end
     */
    var sibling = this.tree.createSibling();
    var afterEl = afterNode.el();
    afterEl.parentNode.insertBefore(sibling, afterEl.nextSibling);
    afterEl = sibling;
    
    /* move all */
    var nodes = [this].concat(this.childsAll()).reverse();
    for (var i in nodes) {
        if (!nodes[i].rendered) continue;
        afterEl.parentNode.insertBefore(nodes[i].el(), afterEl.nextSibling);
        nodes[i].updateLvl();
    }
    this.tree.siblingFix();
    
    // update tree joins
    var pid = this.pid;
    this.pid = toNode.id;
    for (var i in this.tree.nodes[pid]) {
        if (this.tree.nodes[pid][i].id == this.id) {
            this.tree.nodes[pid].splice(i, 1);
            break;
        }
    }
    this.tree.addNode(this);
    
    for (var i in nodes) {
        nodes[i].updateLvl();
    }
    
    // fix for empty nodes
    toNode.expanded = true;
    
    toNode.iconUpdate();
    if (fromNode)
        fromNode.iconUpdate();
}
