#!/usr/bin/python3
#
#


class VisGraph():

	def __init__(self, name = "visjsgraph", height = "640px"):
		self.name = name
		self.edges = []
		self.html = "\n"
		self.html += "<!--netgraph-->\n"
		self.html += "<div id='" + self.name + "' style='height: " + height + ";'></div>\n"
		self.html += "<script>\n"
		self.html += "  var nodes = new vis.DataSet([\n"

	def end(self, direction = ""):
		self.html += "  ]);\n"
		self.html += "  var edges = new vis.DataSet([\n"
		for edge in self.edges:
			if edge[2] != "":
				self.html += "    {from: '" + edge[0] + "', to: '" + edge[1] + "', " + edge[2] + "},\n"
			else:
				self.html += "    {from: '" + edge[0] + "', to: '" + edge[1] + "'},\n"

		self.html += "  ]);\n"
		self.html += "  var container = document.getElementById('" + self.name + "');\n"
		self.html += "  var data = {\n"
		self.html += "    nodes: nodes,\n"
		self.html += "    edges: edges\n"
		self.html += "  };\n"
		self.html += "  var options = {\n"
		if direction != "":
			self.html += "   layout: {\n"
			self.html += "     improvedLayout: true,\n"
			self.html += "     hierarchical: {\n"
			self.html += "       direction: '" + direction + "',\n"
			self.html += "       sortMethod: 'directed'\n"
			self.html += "     }\n"
			self.html += "   },\n"
			self.html += "   interaction: {\n"
			self.html += "     zoomView: false,\n"
			self.html += "     dragView: false,\n"
			self.html += "     dragNodes: false,\n"
			self.html += "   },\n";
			self.html += "   physics: {\n"
			self.html += "       enabled: true,\n"
			self.html += "       hierarchicalRepulsion: {\n"
			self.html += "           centralGravity: 0.0,\n"
			self.html += "           springLength: 200,\n"
			self.html += "           springConstant: 0.01,\n"
			self.html += "           nodeDistance: 120,\n"
			self.html += "           damping: 0.09\n"
			self.html += "       },\n";
			self.html += "       solver: 'hierarchicalRepulsion'\n";
			self.html += "   },\n";
		self.html += "  }\n";
		self.html += "  var network = new vis.Network(container, data, options);\n";
		self.html += "  network.on(\"click\", function(properties) {\n";
		self.html += "  	var ids = properties.nodes;\n";
		self.html += "  	var clickedNodes = nodes.get(ids);\n";
		self.html += "  	var nodeid = clickedNodes[0][\"id\"];\n";
		self.html += "  	var name = nodeid.split('_').slice(1).join('_');\n";
		self.html += "  	console.log(\"clicked nodes: \", nodeid);\n";
		self.html += "  	console.log(\"clicked name: \", name);\n";
		self.html += "  	if (nodeid.startsWith('host_')) {\n";
		self.html += "  	 window.location.href = '/?host=' + name +  '&mode=network';\n";
		self.html += "  	} else if (nodeid.startsWith('all')) {\n";
		self.html += "  	 window.location.href = '/?mode=network';\n";
		self.html += "  	}\n";
		self.html += "  });\n";
		self.html += "</script>\n"
		self.html += "<!--/netgraph-->\n"
		self.html += "\n"
		return self.html


	def node_add(self, nid, label, icon = "desktop-tower", options = ""):

		if options != "":
			self.html += "    {id: '" + nid + "', label: '" + label + "', image:'assets/MaterialDesignIcons/" + icon + ".svg', shape:'image', " + options + "},\n"
		else:
			self.html += "    {id: '" + nid + "', label: '" + label + "', image:'assets/MaterialDesignIcons/" + icon + ".svg', shape:'image'},\n"


	def edge_add(self, source, target, options = ""):
		if not [source, target, options] in self.edges:
			self.edges.append([source, target, options])


