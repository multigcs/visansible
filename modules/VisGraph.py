#!/usr/bin/python3
#
#

import os
import os.path

class VisGraph():

	def __init__(self, name = "visjsgraph", setup={}, height = "640px"):
		""" initialize a new graph

		Args:
			name (str): name of the graph
			height (str): height of the graph

		Returns:
			None

		"""
		self.type = setup.get("type", "vis.js")
		self.name = name
		self.edges = []

		self.html = "\n"
		self.html += "<!--netgraph-->\n"

		if self.type == "vis.js":
			self.html += "<div id='" + self.name + "' style='height: " + height + ";'></div>\n"
			self.html += "<script>\n"
			self.html += "  var nodes = new vis.DataSet([\n"
		else:
#			self.html += "<div id='" + self.name + "' ></div>\n"
			self.graph_name = name
			self.graph = open("/tmp/" + name + ".dot", "w")
			self.graph.write("digraph " + name + " {\n")
			self.graph.write(" truecolor = true;\n")
			self.graph.write(" overlap = false;\n")


	def end(self, direction = ""):
		""" builds the graph in gtml/javascript

		Args:
			direction (str): direction of the graph (UD/LR/...)

		Returns:
			html/javascript string

		"""
		if self.type == "vis.js":
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
				self.html += "       stabilization: {\n";
				self.html += "          iterations:100\n";
				self.html += "       },\n";
				self.html += "       timestep:1,\n";
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
			self.html += "  	if (nodeid.startsWith('host_') && ! nodeid.includes('_ipv4_')) {\n";
			self.html += "  	 window.location.href = 'host?host=' + name + '';\n";
			self.html += "  	} else if (nodeid.startsWith('group_')) {\n";
			self.html += "  	 window.location.href = 'hosts?group=' + name;\n";
			self.html += "  	} else if (nodeid.startsWith('all')) {\n";
			self.html += "  	 window.location.href = 'hosts';\n";
			self.html += "  	}\n";
			self.html += "  });\n";
			self.html += "</script>\n"
			self.html += "<!--/netgraph-->\n"
			self.html += "\n"
		else:
			for edge in self.edges:
				self.graph.write(" \"" + edge[0] + "\" -> \"" + edge[1] + "\" []\n")
			if direction != "":
				self.graph.write(" rankdir = UD;\n")
				self.graph.write("}\n")
				self.graph.close()
				ret = os.popen("dot -T svg \"/tmp/" + self.name + ".dot\"").read()
			else:
				self.graph.write("}\n")
				self.graph.close()
				ret = os.popen(self.type + " -T svg \"/tmp/" + self.name + ".dot\"").read()
#			self.html += "<script>\n"
#			self.html += "document.getElementById('" + self.name + "').innerHTML = '" + "<" + ret.split("<", 5)[-1].replace("\n", "").replace("width=", "_w=").replace("height=", "_h=") + "';\n"
#			self.html += "</script>\n"
			self.html += "<" + ret.split("<", 5)[-1].replace("\n", "").replace("width=", "_w=").replace("height=", "_h=")
		return self.html


	def node_add(self, nid, label, icon = "desktop-tower", options = ""):
		""" Adds a node to the graph

		Args:
			nid (str): id of the node
			label (str): label of the node
			icon (str): label of the node
			options (str): options of the node

		Returns:
			None

		"""
		if not "/" in icon:
			icon = "assets/MaterialDesignIcons/" + icon
		if self.type == "vis.js":
			if options != "":
				self.html += "    {id: '" + nid + "', label: '" + label + "', image:'" + icon + ".svg', shape:'image', " + options + "},\n"
			else:
				self.html += "    {id: '" + nid + "', label: '" + label + "', image:'" + icon + ".svg', shape:'image'},\n"
		else:
			icon += ".svg"
			if not os.path.isfile(icon + ".png"):
				ret = os.popen("convert -scale 32x " + icon + " " + icon + ".png").read()
			icon += ".png"
			link = ""
			if nid.startswith("host_"):
				link = "/host?host=" + nid.replace("host_", "")
			elif nid.startswith("group_"):
				link = "/hosts?group=" + nid.replace("group_", "")

			self.graph.write(" \"" + nid + "\" [shape=\"none\",tooltip=\"" + label + "\",label=<<table border='0' cellspacing='0'><tr><td width=\"100\" height=\"50\" fixedsize=\"true\"><IMG src='" + icon + "' /></td></tr><tr><td>" + label.replace("\\n", "<br />") + "</td></tr></table>>, URL=\"" + link + "\",]\n")


	def edge_add(self, source, target, options = ""):
		""" Adds an edge to the graph

		Args:
			source (str): id of the source node
			target (str): id of the target node
			options (str): edge options

		Returns:
			None

		"""
		if not [source, target, options] in self.edges:
			self.edges.append([source, target, options])


