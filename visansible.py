#!/usr/bin/python3
#
# ansible -i inventory.cfg all -m setup --tree facts
#


import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess

from HtmlPage import *
from VisGraph import *



groups = {}
ipv4_ips = {}

osicons = {
	"Debian": "debian",
	"RedHat": "hat-fedora",
	"FreeBSD": "freebsd",
	"Suse": "opensuse",
	"LibreELEC": "youtube-tv",
}


def osicons_get(osfamily, distribution = ""):
	if osfamily in osicons:
		return osicons[osfamily]
	elif distribution in osicons:
		return osicons[distribution]
	else:
		return "monitor"


def facts2rows(facts, options = "", offset = "", units = "", align = "left"):
	html = ""
	if options == "":
		options = []
		for option in facts:
			options.append(option)
	if type(units) is str:
		unit = units
		units = []
		for option in options:
			units.append(unit)
	un = 0
	for option in options:
		if option.endswith("_mb"):
			title = option.replace("ansible_", "").replace("_mb", "").replace("_", " ").capitalize()
		elif option.endswith("_g"):
			title = option.replace("ansible_", "").replace("_g", "").replace("_", " ").capitalize()
		else:
			title = option.replace("ansible_", "").replace("_", " ").capitalize()
		if option in facts:
			value = str(facts[option])
			html += "<tr><td>" + offset + title + ": </td><td align='" + align + "'>"
			if option.endswith("_mb"):
				html += value + " MB"
			elif option.endswith("_g"):
				html += value + " GB"
			else:
				html += value + " " + units[un]
			html += "</td></tr>\n"
		un += 1
	return html
	


class HTTPServer_RequestHandler(BaseHTTPRequestHandler):
	color_n = 0
	colors = ["#008080", "#0000FF", "#FF0000", "#800000", "#FFFF00", "#808000", "#00FF00", "#008000", "#00FFFF", "#000080", "#FF00FF", "#800080"]

	def show_graph(self, mode = "group"):
		if mode == "":
			mode = group
		html = HtmlPage("Visansible", "Graph (" + mode + ")");
		graph = VisGraph("visgraph", "800px")
		self.color_n = 0
		for group in groups:
			for host in groups[group]["hosts"]:
				if "ansible_facts" in groups[group]["hosts"][host]:
					if mode == "network":
						self.show_host_graph_network_pre(graph, groups[group]["hosts"][host]["ansible_facts"], "host_" + host)
		for group in groups:
			if mode == "group":
				graph.node_add("all", "all", "cloud")
				graph.node_add("group_" + group, group, "table")
				graph.edge_add("all", "group_" + group)
			for host in groups[group]["hosts"]:
				if mode == "group":
					graph.edge_add("group_" + group, "host_" + host)
				if "ansible_facts" in groups[group]["hosts"][host]:
					fqdn = groups[group]["hosts"][host]["ansible_facts"]["ansible_fqdn"]
					osfamily = groups[group]["hosts"][host]["ansible_facts"]["ansible_os_family"]
					distribution = groups[group]["hosts"][host]["ansible_facts"]["ansible_distribution"]
					productname = groups[group]["hosts"][host]["ansible_facts"]["ansible_product_name"]
					architecture = groups[group]["hosts"][host]["ansible_facts"]["ansible_architecture"]
					graph.node_add("host_" + host, host + "\\n" + fqdn + "\\n" + osfamily + "\\n" + productname + "\\n" + architecture, osicons_get(osfamily, distribution), "font: {color: '#0000FF'}")
					if mode == "network":
						self.show_host_graph_network(graph, groups[group]["hosts"][host]["ansible_facts"], "host_" + host, True)
				elif "msg" in groups[group]["hosts"][host]:
					graph.node_add("host_" + host, host + "\\n" + groups[group]["hosts"][host]["msg"].strip().replace(":", "\\n"), "monitor", "font: {color: '#FF0000'}")
				else:
					graph.node_add("host_" + host, host + "\\nUnknown-Error", "monitor", "font: {color: '#FF0000'}")
					print(json.dumps(groups[group]["hosts"][host], indent=4, sort_keys=True));
		html.add(graph.end())
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write(bytes(html.end(), "utf8"))
		return


	def show_host_graph_network_pre(self, graph, facts, parentnode):
		for part in facts:
			if part != "ansible_default_ipv4" and type(facts[part]) is dict and "device" in facts[part]:
				device = facts[part]["device"]
				if ("active" in facts[part] and facts[part]["active"] == False) or device == "lo" or device == "lo0":
					continue
				if "ipv4" in facts[part]:
					if type(facts[part]["ipv4"]) == list:
						for ipv4 in facts[part]["ipv4"]:
							address = ipv4["address"]
							ipv4_ips[address] = [parentnode + "_ipv4_" + address, self.colors[self.color_n]]
							self.color_n = self.color_n + 1
					else:
						address = facts[part]["ipv4"]["address"]
						ipv4_ips[address] = [parentnode + "_ipv4_" + address, self.colors[self.color_n]]
						self.color_n = self.color_n + 1


	def show_host_graph_network(self, graph, facts, parentnode, simple = False):
		gateway = ""
		gateway_interface = ""
		if "ansible_default_ipv4" in facts:
			if "gateway" in facts["ansible_default_ipv4"]:
				gateway_address = facts["ansible_default_ipv4"]["gateway"]
				gateway_interface = facts["ansible_default_ipv4"]["interface"]
		for part in facts:
			if part != "ansible_default_ipv4" and type(facts[part]) is dict and "device" in facts[part]:
				device = facts[part]["device"]
				if "active" in facts[part] and facts[part]["active"] == False or device == "lo" or device == "lo0":
					continue
				if "macaddress" in facts[part]:
					macaddress = facts[part]["macaddress"]
				else:
					macaddress = ""
				if simple == False:
					graph.node_add(parentnode + "_iface_" + device, device + "\\n" + macaddress, "port")
				if "ipv4" in facts[part]:
					if type(facts[part]["ipv4"]) == list:
						for ipv4 in facts[part]["ipv4"]:
							address = ipv4["address"]
							netmask = ipv4["netmask"]
							network = ipv4["network"]
							if address != "127.0.0.1":
								if simple == False:
									## show ipv4 ##
									graph.node_add(parentnode + "_ipv4_" + address, address + "\\n" + netmask, "ipv4")
									graph.edge_add(parentnode + "_iface_" + device, parentnode + "_ipv4_" + address)
									## show ipv4-network ##
									graph.node_add("network_" + network, network, "net");
									graph.edge_add(parentnode + "_ipv4_" + address, "network_" + network)
									## show ipv4-gateway ##
									if gateway_interface == device:
										graph.node_add("gateway_" + gateway_address, gateway_address, "router")
										graph.edge_add("network_" + network, "gateway_" + gateway_address)
										graph.node_add("cloud", "0.0.0.0", "weather-cloudy")
										graph.edge_add("gateway_" + gateway_address, "cloud")
								else:
									## show ipv4 ##
									graph.node_add(parentnode + "_ipv4_" + address, address + "\\n" + netmask, "ipv4")
									graph.edge_add(parentnode, parentnode + "_ipv4_" + address)
									## show ipv4-network ##
									graph.node_add("network_" + network, network, "net");
									## default route ##
									if gateway_interface == device:
										if gateway_address in ipv4_ips:
											graph.edge_add(parentnode + "_ipv4_" + address, "network_" + network, "color: { color: '" + ipv4_ips[gateway_address][0] + "'}, arrows: {to: true}, label: 'gw:." + gateway_address.split(".")[-1] + "'")
										else:
											graph.edge_add(parentnode + "_ipv4_" + address, "network_" + network, "color: { color: '" + self.colors[self.color_n] + "'}, arrows: {to: true}, label: 'gw:." + gateway_address.split(".")[-1] + "'")
											self.color_n = self.color_n + 1
									else:
										graph.edge_add(parentnode + "_ipv4_" + address, "network_" + network)
									## show ipv4-gateway ##
									if gateway_interface == device:
										if gateway_address not in ipv4_ips:
											graph.node_add("gateway_" + gateway_address, gateway_address, "router")
											graph.edge_add("network_" + network, "gateway_" + gateway_address)
											graph.node_add("cloud", "0.0.0.0", "weather-cloudy")
											graph.edge_add("gateway_" + gateway_address, "cloud")
										else:
											graph.edge_add("network_" + network, ipv4_ips[gateway_address][0], "color: { color: '" + ipv4_ips[gateway_address][0] + "'}, arrows: {to: true}, label: 'gw:." + gateway_address.split(".")[-1] + "'")
					else:
						address = facts[part]["ipv4"]["address"]
						netmask = facts[part]["ipv4"]["netmask"]
						network = facts[part]["ipv4"]["network"]
						if address != "127.0.0.1":
							if simple == False:
								## show ipv4 ##
								graph.node_add(parentnode + "_ipv4_" + address, address + "\\n" + netmask, "ipv4")
								graph.edge_add(parentnode + "_iface_" + device, parentnode + "_ipv4_" + address)
								## show ipv4-network ##
								graph.node_add("network_" + network, network, "net");
								graph.edge_add(parentnode + "_ipv4_" + address, "network_" + network)
								## show ipv4-gateway ##
								if gateway_interface == device:
									graph.node_add("gateway_" + gateway_address, gateway_address, "router")
									graph.edge_add("network_" + network, "gateway_" + gateway_address)
									graph.node_add("cloud", "0.0.0.0", "weather-cloudy")
									graph.edge_add("gateway_" + gateway_address, "cloud")
							else:
								## show ipv4 ##
								graph.node_add(parentnode + "_ipv4_" + address, address + "\\n" + netmask, "ipv4")
								graph.edge_add(parentnode, parentnode + "_ipv4_" + address)
								## show ipv4-network ##
								graph.node_add("network_" + network, network, "net");

								## default route ##
								if gateway_interface == device:
									if gateway_address in ipv4_ips:
										graph.edge_add(parentnode + "_ipv4_" + address, "network_" + network, "color: { color: '" + ipv4_ips[gateway_address][0] + "'}, arrows: {to: true}, label: 'gw:." + gateway_address.split(".")[-1] + "'")
									else:
										graph.edge_add(parentnode + "_ipv4_" + address, "network_" + network, "color: { color: '" + self.colors[self.color_n] + "'}, arrows: {to: true}, label: 'gw:." + gateway_address.split(".")[-1] + "'")
										self.color_n = self.color_n + 1
								else:
									graph.edge_add(parentnode + "_ipv4_" + address, "network_" + network)
								## show ipv4-gateway ##
								if gateway_interface == device:
									if gateway_address not in ipv4_ips:
										graph.node_add("gateway_" + gateway_address, gateway_address, "router")
										graph.edge_add("network_" + network, "gateway_" + gateway_address)
										graph.node_add("cloud", "0.0.0.0", "weather-cloudy")
										graph.edge_add("gateway_" + gateway_address, "cloud")
									else:
										graph.edge_add("network_" + network, ipv4_ips[gateway_address][0], "color: { color: '" + ipv4_ips[gateway_address][0] + "'}, arrows: {to: true}, label: 'gw:." + gateway_address.split(".")[-1] + "'")
				if simple == False:
					if "ipv6" in facts[part]:
						for ipv6 in facts[part]["ipv6"]:
							address = ipv6["address"]
							prefix = ipv6["prefix"]
							if "scope" in ipv6:
								scope = ipv6["scope"]
							else:
								scope = ""
							if address != "127.0.0.1":
								## show ipv6 ##
								graph.node_add(parentnode + "_ipv6_" + address, address + "\\n" + prefix + "\\n" + scope, "ipv6")
								graph.edge_add(parentnode + "_iface_" + device, parentnode + "_ipv6_" + address)
				if simple == False:
					if "interfaces" in facts[part] and len(facts[part]["interfaces"]) > 0:
						for interface in facts[part]["interfaces"]:
							graph.edge_add(parentnode + "_iface_" + interface, parentnode + "_iface_" + device)
					else:
						graph.edge_add(parentnode, parentnode + "_iface_" + device)


	def show_host_graph_disks(self, graph, facts, parentnode):
		if "ansible_devices" not in facts:
			return
		vg2pv = {}
		if "ansible_lvm" in facts:
			if "pvs" in facts["ansible_lvm"]:
				for pv in facts["ansible_lvm"]["pvs"]:
					vg = facts["ansible_lvm"]["pvs"][pv]["vg"]
					vg2pv[vg] = pv
					graph.node_add(parentnode + "_pvs_" + pv, "LVM-PV\\n" + pv, "harddisk")
					graph.edge_add(parentnode + "_partition_" + pv.replace("/dev/", ""), parentnode + "_pvs_" + pv)
			if "vgs" in facts["ansible_lvm"]:
				for vg in facts["ansible_lvm"]["vgs"]:
					graph.node_add(parentnode + "_vgs_" + vg, "LVM-VG\\n" + vg, "group")
					if vg in vg2pv:
						pv = vg2pv[vg]
						graph.edge_add(parentnode + "_pvs_" + pv, parentnode + "_vgs_" + vg)
			if "lvs" in facts["ansible_lvm"]:
				for lv in facts["ansible_lvm"]["lvs"]:
					print(lv)
					vg = facts["ansible_lvm"]["pvs"][pv]["vg"]
					lv_device = "/dev/mapper/" + vg + "-" + lv
					graph.node_add(parentnode + "_lvs_" + lv, "LVM-LV\\n" + lv, "partition")
					graph.edge_add(parentnode + "_vgs_" + vg, parentnode + "_lvs_" + lv)
					## show disk-mounts ##
					for mount in facts["ansible_mounts"]:
						if mount["device"] == lv_device:
							graph.node_add(parentnode + "_mount_" + mount["mount"], mount["mount"] + "\\n" + mount["fstype"] + "\\n" + mount["device"], "folder-open")
							graph.edge_add(parentnode + "_lvs_" + lv, parentnode + "_mount_" + mount["mount"])
		if type(facts["ansible_devices"]) is list:
			return
		for device in facts["ansible_devices"]:
			if type(facts["ansible_devices"][device]) is list:
				if device.startswith("cd"):
					graph.node_add(parentnode + "_disk_" + device, device, "disk-player")
				else:
					graph.node_add(parentnode + "_disk_" + device, device, "harddisk")
				graph.edge_add(parentnode, parentnode + "_disk_" + device)
				for partition in facts["ansible_devices"][device]:
					graph.node_add(parentnode + "_partition_" + str(partition), str(partition), "partition")
					graph.edge_add(parentnode + "_disk_" + device, parentnode + "_partition_" + partition)
					## show partition-mounts ##
					for mount in facts["ansible_mounts"]:
						if mount["device"] == "/dev/" + partition:
							graph.node_add(parentnode + "_mount_" + mount["mount"], mount["mount"] + "\\n" + mount["fstype"] + "\\n" + mount["device"], "folder-open")
							graph.edge_add(parentnode + "_partition_" + partition, parentnode + "_mount_" + mount["mount"])
				## show disk-mounts ##
				for mount in facts["ansible_mounts"]:
					if mount["device"] == "/dev/" + device:
						graph.node_add(parentnode + "_mount_" + mount["mount"], mount["mount"] + "\\n" + mount["fstype"] + "\\n" + mount["device"], "folder-open")
						graph.edge_add(parentnode + "_disk_" + device, parentnode + "_mount_" + mount["mount"])
			if "partitions" in facts["ansible_devices"][device]:
				if not device.startswith("loops") and (len(vg2pv) == 0 or not device.startswith("dm-") ):
					## show host controller ##
					hostctrl = str(facts["ansible_devices"][device]["host"])
					if hostctrl == "":
						hostctrl = "software"
					graph.node_add(parentnode + "_hostctrl_" + hostctrl, hostctrl.replace(":", "\\n"), "scsi")
					graph.edge_add(parentnode, parentnode + "_hostctrl_" + hostctrl)
					## show disk ##
					vendor = str(facts["ansible_devices"][device]["vendor"])
					model = str(facts["ansible_devices"][device]["model"])
					size = facts["ansible_devices"][device]["size"]
					if size != "0.00 Bytes":
						if "model" in facts["ansible_devices"][device] and ("DVD" in str(facts["ansible_devices"][device]["model"]) or "CD" in str(facts["ansible_devices"][device]["model"])):
							graph.node_add(parentnode + "_disk_" + device, device + "\\n" + vendor + "\\n" + model + "\\n" + size, "disk-player")
						else:
							graph.node_add(parentnode + "_disk_" + device, device + "\\n" + vendor + "\\n" + model + "\\n" + size, "harddisk")
						## check if device is slave of another disk ##
						is_slave = False
						for device2 in facts["ansible_devices"]:
							if "links" in facts["ansible_devices"][device2] and "masters" in facts["ansible_devices"][device2]["links"]:
								for master in facts["ansible_devices"][device2]["links"]["masters"]:
									if device == master:
										graph.edge_add(parentnode + "_disk_" + device2, parentnode + "_disk_" + device)
										is_slave = True
						## check if device is slave of another partition ##
						if is_slave == False:
							for device2 in facts["ansible_devices"]:
								if "partitions" in facts["ansible_devices"][device2]:
									for partition2 in facts["ansible_devices"][device2]["partitions"]:
										if "links" in facts["ansible_devices"][device2]["partitions"][partition2] and "masters" in facts["ansible_devices"][device2]["partitions"][partition2]["links"]:
											for master in facts["ansible_devices"][device2]["partitions"][partition2]["links"]["masters"]:
												if device == master:
													graph.edge_add(parentnode + "_partition_" + str(partition2), parentnode + "_disk_" + device)
													is_slave = True
						## link to the controller ##
						if is_slave == False:
							graph.edge_add(parentnode + "_hostctrl_" + hostctrl, parentnode + "_disk_" + device)
						## show partitions ##
						for partition in facts["ansible_devices"][device]["partitions"]:
							uuid = facts["ansible_devices"][device]["partitions"][partition]["uuid"]
							size = facts["ansible_devices"][device]["partitions"][partition]["size"]
							graph.node_add(parentnode + "_partition_" + str(partition), str(partition) + "\\n" + str(uuid) + "\\n" + str(size), "partition")
							graph.edge_add(parentnode + "_disk_" + device, parentnode + "_partition_" + partition)
							## show partition-mounts ##
							for mount in facts["ansible_mounts"]:
								if mount["uuid"] == uuid:
									graph.node_add(parentnode + "_mount_" + mount["mount"], mount["mount"] + "\\n" + mount["fstype"] + "\\n" + mount["device"], "folder-open")
									graph.edge_add(parentnode + "_partition_" + partition, parentnode + "_mount_" + mount["mount"])
						## show disk-mounts ##
						for mount in facts["ansible_mounts"]:
							if "links" in facts["ansible_devices"][device] and "uuids" in facts["ansible_devices"][device]["links"]:
								for disk_uuid in facts["ansible_devices"][device]["links"]["uuids"]:
									if mount["uuid"] == disk_uuid:
										graph.node_add(parentnode + "_mount_" + mount["mount"], mount["mount"] + "\\n" + mount["fstype"] + "\\n" + mount["device"], "folder-open")
										graph.edge_add(parentnode + "_disk_" + device, parentnode + "_mount_" + mount["mount"])


	def show_hostgraph(self, hostname, mode = "network"):
		html = HtmlPage("Visansible", "Hostgraph");
		graph = VisGraph()
		for group in groups:
			for host in groups[group]["hosts"]:
				if "ansible_facts" in groups[group]["hosts"][host] and hostname == host:
					facts = groups[group]["hosts"][host]["ansible_facts"]
					fqdn = facts["ansible_fqdn"]
					osfamily = facts["ansible_os_family"]
					productname = facts["ansible_product_name"]
					architecture = facts["ansible_architecture"]
					graph.node_add("host_" + host, host + "\\n" + fqdn + "\\n" + osfamily + "\\n" + productname + "\\n" + architecture, "monitor")
					if mode == "network":
						self.show_host_graph_network(graph, facts, "host_" + host)
					elif mode == "disks":
						self.show_host_graph_disks(graph, facts, "host_" + host)
					elif mode == "all":
						self.show_host_graph_disks(graph, facts, "host_" + host)
						self.show_host_graph_network(graph, facts, "host_" + host)
		html.add(graph.end())
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write(bytes(html.end(), "utf8"))
		return


	def show_host_table_ifaces(self, facts):
		html = ""
		if "ansible_default_ipv4" in facts:
			if "gateway" in facts["ansible_default_ipv4"]:
				gateway_address = facts["ansible_default_ipv4"]["gateway"]
				gateway_interface = facts["ansible_default_ipv4"]["interface"]
		for part in facts:
			if part != "ansible_default_ipv4" and type(facts[part]) is dict and "device" in facts[part]:
				html += "<div class='col-6'>\n"
				html += "<div class='card'>\n"
				html += "<div class='card-header'>Network-Interface: " + facts[part]["device"] + "<img class='float-right' src='assets/MaterialDesignIcons/port.svg'></div>\n"
				html += "<div class='card-body'>\n"
				html += "<div class='row'>\n"
				html += "<div class='col-6'>\n"
				html += "<b>Interface:</b>\n"
				html += "<table>\n"
				html += facts2rows(facts[part], ["device", "model", "macaddress", "mtu", "promisc", "type", "active"])
				html += "</table>\n"
				html += "</div>\n"
				html += "<div class='col-6'>\n"
				if "ipv4" in facts[part]:
					if type(facts[part]["ipv4"]) == list:
						for ipv4 in facts[part]["ipv4"]:
							fact = ipv4
							html += "<b>IPv4:</b>\n"
							html += "<table>\n"
							html += facts2rows(ipv4, ["address", "netmask", "broadcast", "network"])
							html += "</table>\n"
							html += "<br />\n"
					else:
						html += "<b>IPv4:</b>\n"
						html += "<table>\n"
						html += facts2rows(facts[part]["ipv4"], ["address", "netmask", "broadcast", "network"])
						html += "</table>\n"
						html += "<br />\n"
				if "ipv6" in facts[part]:
					for ipv6 in facts[part]["ipv6"]:
						html += "<b>IPv6:</b>\n"
						html += "<table>\n"
						html += facts2rows(ipv6, ["address", "prefix", "scope"])
						html += "</table>\n"
						html += "<br />\n"
				html += "</div>\n"
				html += "</div>\n"
				html += "</div>\n"
				html += "</div>\n"
				html += "</div>\n"
		return html


	def show_host_table_disks(self, facts):
		html = ""
		if "ansible_devices" not in facts:
			return html
		dms = {}
		if "ansible_lvm" in facts:
			if "vgs" in facts["ansible_lvm"]:
				for vg in facts["ansible_lvm"]["vgs"]:
					dms[0] = 0
		if type(facts["ansible_devices"]) is list:
			return html
		for device in facts["ansible_devices"]:
			if type(facts["ansible_devices"][device]) is list:
				html += "<div class='col-6'>\n"
				html += "<div class='card'>\n"
				html += "<div class='card-header'>Disk: " + device + "<img class='float-right' src='assets/MaterialDesignIcons/harddisk.svg'></div>\n"
				html += "<div class='card-body'>\n"
				html += "<div class='row'>\n"
				## show disk ##
				html += "<div class='col-6'>\n"
				html += "<b>Disk: " + device + "</b>\n"
				html += "<table>\n"
				## show disk-mounts ##
				for mount in facts["ansible_mounts"]:
					if mount["device"] == "/dev/" + device:
						html += facts2rows(mount, ["mount", "fstype", "device", "size_available", "uuid"])
						html += "<tr><td>&nbsp;</td><td>&nbsp;</td></tr>\n"
				html += "</table>\n"
				html += "</div>\n"
				## show partitions ##
				html += "<div class='col-6'>\n"
				for partition in facts["ansible_devices"][device]:
					html += "<b>Partition: " + partition + "</b>\n"
					html += "<table>\n"
					## show mounts ##
					for mount in facts["ansible_mounts"]:
						if mount["device"] == "/dev/" + partition:
							html += facts2rows(mount, ["mount", "fstype", "device", "size_available", "uuid"])
							html += "<tr><td>&nbsp;</td><td>&nbsp;</td></tr>\n"
					html += "</table>\n"
					html += "<br />\n"
				html += "</div>\n"
				html += "</div>\n"
				html += "</div>\n"
				html += "</div>\n"
				html += "</div>\n"
			if "partitions" in facts["ansible_devices"][device]:
				if facts["ansible_devices"][device]["size"] != "0.00 Bytes" and (len(dms) == 0 or not device.startswith("dm-") ):
					html += "<div class='col-6'>\n"
					html += "<div class='card'>\n"
					if "model" in facts["ansible_devices"][device] and ("DVD" in str(facts["ansible_devices"][device]["model"]) or "CD" in str(facts["ansible_devices"][device]["model"])):
						html += "<div class='card-header'>Disk: " + device + "<img class='float-right' src='assets/MaterialDesignIcons/disk-player.svg'></div>\n"
					else:
						html += "<div class='card-header'>Disk: " + device + "<img class='float-right' src='assets/MaterialDesignIcons/harddisk.svg'></div>\n"
					html += "<div class='card-body'>\n"
					html += "<div class='row'>\n"
					## show disk ##
					html += "<div class='col-6'>\n"
					html += "<b>Disk:</b>\n"
					html += "<table>\n"
					html += facts2rows(facts["ansible_devices"][device], ["host", "vendor", "model", "serial", "size"])
					## show disk-mounts ##
					for mount in facts["ansible_mounts"]:
						if "links" in facts["ansible_devices"][device] and "uuids" in facts["ansible_devices"][device]["links"]:
							for disk_uuid in facts["ansible_devices"][device]["links"]["uuids"]:
								if mount["uuid"] == disk_uuid:
									html += facts2rows(mount, ["mount", "fstype", "device", "size_available", "uuid"])
									html += "<tr><td>&nbsp;</td><td>&nbsp;</td></tr>\n"

					## check if device is slave of another disk ##
					for device2 in facts["ansible_devices"]:
						if "links" in facts["ansible_devices"][device2] and "masters" in facts["ansible_devices"][device2]["links"]:
							for master in facts["ansible_devices"][device2]["links"]["masters"]:
								if device == master:
									html += "<tr>\n"
									html += " <td>Master: </td>\n"
									html += " <td>" + device2 + "</td>\n"
									html += "</tr>\n"

					## check if device is slave of another partition ##
					for device2 in facts["ansible_devices"]:
						if "partitions" in facts["ansible_devices"][device2]:
							for partition2 in facts["ansible_devices"][device2]["partitions"]:
								if "links" in facts["ansible_devices"][device2]["partitions"][partition2] and "masters" in facts["ansible_devices"][device2]["partitions"][partition2]["links"]:
									for master in facts["ansible_devices"][device2]["partitions"][partition2]["links"]["masters"]:
										if device == master:
											html += "<tr>\n"
											html += " <td>Master: </td>\n"
											html += " <td>" + partition2 + "</td>\n"
											html += "</tr>\n"
					## show disk slaves ##
					if "links" in facts["ansible_devices"][device] and "masters" in facts["ansible_devices"][device]["links"]:
						for master in facts["ansible_devices"][device]["links"]["masters"]:
							html += "<tr>\n"
							html += " <td>Slave-Device: </td>\n"
							html += " <td>" + master + "</td>\n"
							html += "</tr>\n"
					html += "</table>\n"
					html += "</div>\n"
					## show partitions ##
					html += "<div class='col-6'>\n"
					for partition in facts["ansible_devices"][device]["partitions"]:
						html += "<b>Partition: " + partition + "</b>\n"
						html += "<table>\n"
						## show partition ##
						html += facts2rows(facts["ansible_devices"][device]["partitions"][partition], ["uuid", "size", "start", "sectors", "sectorsize"])
						## show partition slaves ##
						if "links" in facts["ansible_devices"][device]["partitions"][partition] and "masters" in facts["ansible_devices"][device]["partitions"][partition]["links"]:
							for master in facts["ansible_devices"][device]["partitions"][partition]["links"]["masters"]:
								html += "<tr>\n"
								html += " <td>Slave-Device: </td>\n"
								html += " <td>" + master + "</td>\n"
								html += "</tr>\n"
						## show mounts ##
						for mount in facts["ansible_mounts"]:
							if mount["uuid"] == facts["ansible_devices"][device]["partitions"][partition]["uuid"]:
								html += facts2rows(mount, ["mount", "fstype", "device", "size_available", "uuid"], "&nbsp;&nbsp;&nbsp;")
								html += "<tr><td>&nbsp;</td><td>&nbsp;</td></tr>\n"
						html += "</table>\n"
						html += "<br />\n"
					html += "</div>\n"
					html += "</div>\n"
					html += "</div>\n"
					html += "</div>\n"
					html += "</div>\n"
		if "ansible_lvm" in facts:
			if "vgs" in facts["ansible_lvm"]:
				for vg in facts["ansible_lvm"]["vgs"]:
					vg_pv = facts["ansible_lvm"]["vgs"][vg]
					html += "<div class='col-6'>\n"
					html += "<div class='card'>\n"
					html += "<div class='card-header'>LVM_VG: " + vg + "<img class='float-right' src='assets/MaterialDesignIcons/harddisk.svg'></div>\n"
					html += "<div class='card-body'>\n"
					html += "<div class='row'>\n"
					html += "<div class='col-6'>\n"
					html += "<b>VG:</b>\n"
					html += "<table>\n"
					html += facts2rows(facts["ansible_lvm"]["vgs"][vg], ["size_g", "free_g", "num_lvs", "num_pvs"])
					if "pvs" in facts["ansible_lvm"]:
						for pv in facts["ansible_lvm"]["pvs"]:
							pv_vg = facts["ansible_lvm"]["pvs"][pv]["vg"]
							if pv_vg == vg:
								html += "<tr>\n"
								html += " <td>&nbsp;&nbsp;&nbsp;PV: </td>\n"
								html += " <td>" + pv + "</td>\n"
								html += "</tr>\n"
								html += facts2rows(facts["ansible_lvm"]["pvs"][pv], ["size_g", "free_g"], "&nbsp;&nbsp;&nbsp;")
								html += "<tr><td>&nbsp;</td><td>&nbsp;</td></tr>\n"
					html += "</table>\n"
					html += "</div>\n"
					html += "<div class='col-6'>\n"
					if "lvs" in facts["ansible_lvm"]:
						for lv in facts["ansible_lvm"]["lvs"]:
							lv_vg = facts["ansible_lvm"]["lvs"][lv]["vg"]
							if lv_vg == vg:
								lv_device = "/dev/mapper/" + vg + "-" + lv
								html += "<b>LV: " + lv + "</b>\n"
								html += "<table>\n"
								html += facts2rows(facts["ansible_lvm"]["lvs"][lv], ["size_g"])
								## show mounts ##
								for mount in facts["ansible_mounts"]:
									if mount["device"] == lv_device:
										html += facts2rows(mount, ["mount", "fstype", "device", "size_available", "uuid"], "&nbsp;&nbsp;&nbsp;")
										html += "<tr><td>&nbsp;</td><td>&nbsp;</td></tr>\n"
								html += "</table>\n"
								html += "<br />\n"
					html += "</div>\n"
					html += "</div>\n"
					html += "</div>\n"
					html += "</div>\n"
					html += "</div>\n"
		return html


	def show_host_table_general(self, facts):
		html = ""
		html += "<div class='col-6'>\n"
		html += "<div class='card'>\n"
		osfamily = facts["ansible_os_family"]
		distribution = facts["ansible_distribution"]
		html += "<div class='card-header'>General<img class='float-right' src='assets/MaterialDesignIcons/" + osicons_get(osfamily, distribution) + ".svg'></div>\n"
		html += "<div class='card-body'>\n"
		html += "<div class='row'>\n"
		html += "<div class='col-6'>\n"
		html += "<table>\n"
		html += facts2rows(facts, ["ansible_fqdn", "ansible_system_vendor", "ansible_product_name", "ansible_product_serial", "ansible_architecture", "ansible_memtotal_mb", "ansible_virtualization_role", "ansible_virtualization_type"])
		html += "</table>\n"
		html += "</div>\n"
		html += "<div class='col-6'>\n"
		html += "<table>\n"
		html += facts2rows(facts, ["ansible_distribution", "ansible_distribution_major_version", "ansible_distribution_release", "ansible_distribution_version", "ansible_distribution_file_variety", "ansible_userspace_architecture", "ansible_kernel", "ansible_pkg_mgr"])
		html += "</table>\n"
		html += "</div>\n"
		html += "</div>\n"
		html += "</div>\n"
		html += "</div>\n"
		html += "</div>\n"
		return html


	def show_host_table_memory(self, facts):
		html = ""
		if "ansible_memory_mb" in facts:
			html += "<div class='col-6'>\n"
			html += "<div class='card'>\n"
			html += "<div class='card-header'>Memory<img class='float-right' src='assets/MaterialDesignIcons/memory.svg'></div>\n"
			html += "<div class='card-body'>\n"
			html += "<div class='row'>\n"
			for section in ["nocache", "real", "swap"]:
				if section in facts["ansible_memory_mb"]:
					html += "<div class='col-4'>\n"
					html += "<b>" + section.capitalize() + ":</b><br />\n"
					html += "<table>\n"
					html += facts2rows(facts["ansible_memory_mb"][section], "", "", "MB", "right")
					html += "</table>\n"
					html += "</div>\n"
			html += "</div>\n"
			html += "</div>\n"
			html += "</div>\n"
			html += "</div>\n"
		return html


	def show_host_table_network(self, facts):
		html = ""
		html += "<div class='col-6'>\n"
		html += "<div class='card'>\n"
		html += "<div class='card-header'>Network<img class='float-right' src='assets/MaterialDesignIcons/net.svg'></div>\n"
		html += "<div class='card-body'>\n"
		html += "<div class='row'>\n"
		html += "<div class='col-6'>\n"
		html += "<b>Hostname & Domain:</b><br />\n"
		html += "<table>\n"
		html += facts2rows(facts, ["ansible_hostname", "ansible_domain", "ansible_fqdn"])
		html += "</table>\n"
		html += "</div>\n"
		html += "<div class='col-6'>\n"
		html += "<b>DNS-Server:</b><br />\n"
		html += "<table>\n"
		if "nameservers" in facts["ansible_dns"]:
			for nameserver in facts["ansible_dns"]["nameservers"]:
				html += "<tr>\n"
				html += " <td>DNS-Server: </td>\n"
				html += " <td>" + nameserver + "</td>\n"
				html += "</tr>\n"
		if "search" in facts["ansible_dns"]:
			for search in facts["ansible_dns"]["search"]:
				html += "<tr>\n"
				html += " <td>DNS-Search: </td>\n"
				html += " <td>" + search + "</td>\n"
				html += "</tr>\n"
		html += "</table>\n"
		html += "<br />\n"
		html += "<b>Default-Gateway:</b><br />\n"
		html += "<table>\n"
		if "ansible_default_ipv4" in facts:
			html += facts2rows(facts["ansible_default_ipv4"], ["gateway", "interface"])
		html += "</table>\n"
		html += "</div>\n"
		html += "</div>\n"
		html += "</div>\n"
		html += "</div>\n"
		html += "</div>\n"
		return html


	def show_host_table_processors(self, facts):
		html = ""
		html += "<div class='col-6'>\n"
		html += "<div class='card'>\n"
		osfamily = facts["ansible_os_family"]
		html += "<div class='card-header'>Processors<img class='float-right' src='assets/MaterialDesignIcons/chip.svg'></div>\n"
		html += "<div class='card-body'>\n"
		html += "<div class='row'>\n"
		html += "<div class='col-6'>\n"
		html += "<b>CPUs/Cores/Threads:</b><br />\n"
		html += "<table>\n"
		html += facts2rows(facts, ["ansible_processor_count", "ansible_processor_cores", "ansible_processor_threads_per_core", "ansible_processor_vcpus"], "", "", "right")
		html += "</table>\n"
		html += "</div>\n"
		html += "<div class='col-6'>\n"
		html += "<b>Types:</b><br />\n"
		html += "<table>\n"
		if "ansible_processor" in facts:
			processor_n = 0
			for part in facts["ansible_processor"]:
				if part.isdigit():
					processor_n += 1
					if processor_n != 1:
						html += "</td>\n"
						html += "</tr>\n"
					html += "<tr>\n"
					html += " <td>#" + str(processor_n) + ": </td>\n"
					html += " <td>"
				else:
					html += part + " "
			html += "</td>\n"
			html += "</tr>\n"
		html += "</table>\n"
		html += "</div>\n"
		html += "</div>\n"
		html += "</div>\n"
		html += "</div>\n"
		html += "</div>\n"
		return html


	def show_hostdata(self, hostname):
		html = HtmlPage("Visansible", "Hostdata (" + hostname + ")");
		for group in groups:
			for host in groups[group]["hosts"]:
				if hostname == host:
					if "ansible_facts" in groups[group]["hosts"][host]:
						osfamily = groups[group]["hosts"][host]["ansible_facts"]["ansible_os_family"]
						distribution = groups[group]["hosts"][host]["ansible_facts"]["ansible_distribution"]
						icon = osicons_get(osfamily, distribution)
						html.add(" <div class='row'>\n")
						html.add(self.show_host_table_general(groups[group]["hosts"][host]["ansible_facts"]))
						html.add(self.show_host_table_processors(groups[group]["hosts"][host]["ansible_facts"]))
						html.add(self.show_host_table_memory(groups[group]["hosts"][host]["ansible_facts"]))
						html.add(self.show_host_table_network(groups[group]["hosts"][host]["ansible_facts"]))
						html.add(" </div>\n")
						html.add(" <div class='row'>\n")
						html.add(self.show_host_table_ifaces(groups[group]["hosts"][host]["ansible_facts"]))
						html.add("  <div class='col-12'>\n")
						html.add("  <div class='card'>\n")
						html.add("   <div class='card-header'>Network-Graph<img class='float-right' src='assets/MaterialDesignIcons/net.svg'></div>\n")
						html.add("   <div class='card-body'>\n")
						graph = VisGraph("vis_network")
						graph.node_add("host_" + host, host, icon)
						self.show_host_graph_network(graph, groups[group]["hosts"][host]["ansible_facts"], "host_" + host)
						html.add(graph.end(direction = "LR"))
						html.add("   </div>\n")
						html.add("   </div>\n")
						html.add("  </div>\n")
						html.add(" </div>\n")
						html.add(" <div class='row'>\n")
						html.add(self.show_host_table_disks(groups[group]["hosts"][host]["ansible_facts"]))
						html.add("  <div class='col-12'>\n")
						html.add("  <div class='card'>\n")
						html.add("   <div class='card-header'>Disks-Graph<img class='float-right' src='assets/MaterialDesignIcons/harddisk.svg'></div>\n")
						html.add("   <div class='card-body'>\n")
						graph = VisGraph("vis_disks")
						graph.node_add("host_" + host, host, icon)
						self.show_host_graph_disks(graph, groups[group]["hosts"][host]["ansible_facts"], "host_" + host)
						html.add(graph.end(direction = "UD"))
						html.add("   </div>\n")
						html.add("  </div>\n")
						html.add("  </div>\n")
						html.add(" </div>\n")
					else:
						if "msg" in groups[group]["hosts"][host]:
							html.add(" <b>" + groups[group]["hosts"][host]["msg"].strip() + "</b>\n")
						else:
							html.add(" <b>UNKNOWN-ERROR</b>\n")
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write(bytes(html.end(), "utf8"))
		return


	def show_hosts(self):
		options = ["ansible_fqdn", "ansible_os_family", "ansible_architecture", "ansible_product_name", "ansible_product_serial"]
		html = HtmlPage("Visansible", "Hosts");
		html.add(" <div class='row'>\n")
		html.add("  <div class='col-12'>\n")
		html.add("<table class='table table-hover' width='90%'>\n")
		for group in groups:
			html.add("<tr>\n")
			html.add(" <td colspan='" + str(len(options) + 3) + "'><h2>Group: " + group + "</h2></td>\n")
			html.add("</tr>\n")
			html.add("<tr>\n")
			html.add(" <th>Host</th>\n")
			for option in options:
				title = option.replace("ansible_", "").capitalize()
				html.add(" <th>" + title + "</th>\n")
			html.add(" <th width='10%'>Options</th>\n")
			html.add(" <th width='10%'>Status</th>\n")
			html.add("</tr>\n")
			for host in groups[group]["hosts"]:
				html.add("<tr>\n")
				html.add(" <td width='10%'><a href='/?host=" + host + "'>" + host + "</a></td>\n")
				for option in options:
					if "ansible_facts" in groups[group]["hosts"][host] and option in groups[group]["hosts"][host]["ansible_facts"]:
						value = str(groups[group]["hosts"][host]["ansible_facts"][option])
						if option == "ansible_os_family":
							html.add("<td width='10%'>")
							osfamily = groups[group]["hosts"][host]["ansible_facts"]["ansible_os_family"]
							distribution = groups[group]["hosts"][host]["ansible_facts"]["ansible_distribution"]
							html.add("<img src='assets/MaterialDesignIcons/" + osicons_get(osfamily, distribution) + ".svg' />\n")
						else:
							html.add("<td>")
						html.add(value)
						html.add("</td>\n")
					else:
						html.add(" <td>---</td>\n")
				if "options" in groups[group]["hosts"][host]:
					html.add(" <td>" + ", ".join(groups[group]["hosts"][host]["options"]) + "</td>\n")
				else:
					html.add(" <td>---</td>\n")
				if "msg" in groups[group]["hosts"][host]:
					html.add(" <td>" + groups[group]["hosts"][host]["msg"].strip() + "</td>\n")
				elif "ansible_facts" in groups[group]["hosts"][host]:
					html.add(" <td>OK</td>\n")
				else:
					html.add(" <td>UNKNOWN-ERROR</td>\n")
				html.add("</tr>\n")
		html.add("</table>\n")
		html.add("<br />\n")
		html.add("  </div>\n")
		html.add(" </div>\n")
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write(bytes(html.end(), "utf8"))
		return


	def show_inventory(self):
		html = HtmlPage("Visansible", "Inventory-File");
		html.add("<div class='row'>\n")
		html.add("<div class='col-12'>\n")
		inventory = open("inventory.cfg", "r").read()
		html.add("<pre>" + inventory + "</pre>\n")
		html.add("</div>\n")
		html.add("</div>\n")
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write(bytes(html.end(), "utf8"))
		return


	def show_stats(self):
		colors = ["#cb2121", "#830909", "#923e99", "#ae83d5", "#111111", "#050505", "#646464", "#747474", "#333333", "#444444", "#555555", "#666666", "#777777", "#888888", "#999999", "#008080", "#0000FF", "#FF0000", "#800000", "#FFFF00", "#808000", "#00FF00", "#008000", "#00FFFF", "#000080", "#FF00FF", "#800080"]
		options = ["ansible_os_family", "ansible_architecture", "ansible_product_name", "ansible_distribution", "ansible_kernel", "ansible_processor_count", "ansible_distribution_release", "ansible_virtualization_role", "ansible_virtualization_type", "ansible_pkg_mgr"]
		html = HtmlPage("Visansible", "Stats");
		stats = {}
		for option in options:
			stats[option] = {}
		for group in groups:
			for host in groups[group]["hosts"]:
				for option in options:
					value = groups[group]["hosts"][host]["ansible_facts"][option];
					if value not in stats[option]:
						stats[option][value] = 0
					stats[option][value] += 1
		html.add("<div class='row'>\n")
		for option in options:
			html.add("<div class='col-4'>\n")
			html.add("<div id='pieChart_" + option + "'></div>\n")
			html.add("</div>\n")
		html.add("</div>\n")
		for option in options:
			html.add("<script>\n")
			html.add("var pie = new d3pie('pieChart_" + option + "', {\n")
			html.add("	'header': {\n")
			html.add("		'title': {\n")
			html.add("			'text': '" + option.replace("ansible_", "").capitalize() + "',\n")
			html.add("			'fontSize': 14,\n")
			html.add("			'font': 'courier'\n")
			html.add("		},\n")
			html.add("		'subtitle': {\n")
			html.add("			'text': '" + option + "',\n")
			html.add("			'color': '#999999',\n")
			html.add("			'fontSize': 10,\n")
			html.add("			'font': 'courier'\n")
			html.add("		},\n")
			html.add("		'location': 'pie-center',\n")
			html.add("		'titleSubtitlePadding': 10\n")
			html.add("	},\n")
			html.add("	'size': {\n")
			html.add("		'canvasWidth': 390,\n")
			html.add("		'canvasHeight': 360,\n")
			html.add("		'pieInnerRadius': '90%',\n")
			html.add("		'pieOuterRadius': '50%'\n")
			html.add("	},\n")
			html.add("	'data': {\n")
			html.add("		'sortOrder': 'label-desc',\n")
			html.add("		'content': [\n")
			color_n = 0
			for label in stats[option]:
				html.add("{\n")
				html.add(" 'label': '" + str(stats[option][label]) + "x " + str(label) + "',\n")
				html.add(" 'color': '" + colors[color_n] + "',\n")
				html.add(" 'value': " + str(stats[option][label]) + ",\n")
				html.add("},\n")
				color_n += 1
			html.add("		]\n")
			html.add("	},\n")
			html.add("	'labels': {\n")
			html.add("		'outer': {\n")
			html.add("			'format': 'label-percentage1',\n")
			html.add("			'pieDistance': 20\n")
			html.add("		},\n")
			html.add("		'inner': {\n")
			html.add("			'format': 'none'\n")
			html.add("		},\n")
			html.add("		'mainLabel': {\n")
			html.add("			'fontSize': 11\n")
			html.add("		},\n")
			html.add("		'percentage': {\n")
			html.add("			'color': '#999999',\n")
			html.add("			'fontSize': 11,\n")
			html.add("			'decimalPlaces': 0\n")
			html.add("		},\n")
			html.add("		'value': {\n")
			html.add("			'color': '#cccc43',\n")
			html.add("			'fontSize': 11\n")
			html.add("		},\n")
			html.add("		'lines': {\n")
			html.add("			'enabled': true,\n")
			html.add("			'color': '#777777'\n")
			html.add("		},\n")
			html.add("		'truncation': {\n")
			html.add("			'enabled': true\n")
			html.add("		}\n")
			html.add("	},\n")
			html.add("	'effects': {\n")
			html.add("		'pullOutSegmentOnClick': {\n")
			html.add("			'effect': 'linear',\n")
			html.add("			'speed': 400,\n")
			html.add("			'size': 8\n")
			html.add("		}\n")
			html.add("	},\n")
			html.add("	'misc': {\n")
			html.add("		'colors': {\n")
			html.add("			'segmentStroke': '#000000'\n")
			html.add("		}\n")
			html.add("	}\n")
			html.add("});\n")
			html.add("</script>\n")
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write(bytes(html.end(), "utf8"))
		return


	def do_GET(self):
		print(self.path)
		if self.path.startswith("/rescan"):
			command = ['ansible', '-i', 'inventory.cfg', 'all', '-m', 'setup', '--tree', 'facts']
			result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			html = HtmlPage("Visansible", "Rescan");
			html.add("<b>command:</b>")
			html.add("<pre>")
			html.add(" ".join(command))
			html.add("</pre>")
			if result.stderr.decode('utf-8') != "":
				html.add("<b>stderr:</b>")
				html.add("<pre>")
				html.add(result.stderr.decode('utf-8'))
				html.add("</pre>")
			if result.stdout.decode('utf-8') != "":
				html.add("<b>stdout:</b>")
				html.add("<pre>")
				html.add(result.stdout.decode('utf-8'))
				html.add("</pre>")
			inventory_read()
			self.send_response(200)
			self.send_header("Content-type", "text/html")
			self.end_headers()
			self.wfile.write(bytes(html.end(), "utf8"))
			return
		elif self.path.startswith("/assets/"):
			if ".." in self.path:
				self.send_response(404)
				self.send_header("Content-type", "text/plain")
				self.end_headers()
				self.wfile.write(bytes("file not found: " + self.path, "utf8"))
			else:
				if os.path.isfile("." + self.path):
					statinfo = os.stat("." + self.path)
					size = statinfo.st_size
					self.send_response(200)
					self.send_header("Content-length", size)
					if self.path.endswith(".js"):
						self.send_header("Content-type", "application/javascript")
					elif self.path.endswith(".css"):
						self.send_header("Content-type", "text/css")
					elif self.path.endswith(".png"):
						self.send_header("Content-type", "image/png")
					elif self.path.endswith(".svg"):
						self.send_header("Content-type", "image/svg+xml")
					else:
						self.send_header("Content-type", "text/plain")
					self.end_headers()
					data = open("." + self.path, "rb").read()
					self.wfile.write(data)
				else:
					self.send_response(404)
					self.send_header("Content-type", "text/plain")
					self.end_headers()
					self.wfile.write(bytes("file not found: " + self.path, "utf8"))
		elif self.path.startswith("/?host="):
			opts = {}
			opts["mode"] = "network"
			for opt in self.path.split("?")[1].split("&"):
				name = opt.split("=")[0]
				value = opt.split("=")[1]
				opts[name] = value
#			self.show_hostgraph(opts["host"], "all")
			self.show_hostdata(opts["host"])
		elif self.path.startswith("/?mode="):
			opts = {}
			for opt in self.path.split("?")[1].split("&"):
				name = opt.split("=")[0]
				value = opt.split("=")[1]
				opts[name] = value
			if opts["mode"] == "hosts":
				self.show_hosts()
			elif opts["mode"] == "stats":
				self.show_stats()
			elif opts["mode"] == "inventory":
				self.show_inventory()
			else:
				self.show_graph(opts["mode"])
		else:
			self.show_graph()
		return


	def show_element(self, element, prefix = ""):
		html = ""
		if type(element) is str:
			html += prefix + str(element) + "<br />\n"
		elif type(element) is int:
			html += prefix + str(element) + "<br />\n"
		elif type(element) is list:
			for part in element:
				if type(part) is str:
					html += prefix + str(part) + "<br />\n"
				elif type(part) is int:
					html += prefix + str(part) + "<br />\n"
			for part in element:
				if type(part) is dict:
					html += "<br />\n"
					html += self.show_element(part, prefix + "&nbsp;&nbsp;&nbsp;")
				elif type(part) is list:
					html += "<br />\n"
					html += self.show_element(part, prefix + "&nbsp;&nbsp;&nbsp;")
		else:
			for part in element:
				if type(element[part]) is str:
					html += prefix + str(part) + " = " + str(element[part]) + "<br />\n"
				elif type(element[part]) is int:
					html += prefix + str(part) + " = " + str(element[part]) + "<br />\n"
			for part in element:
				if type(element[part]) is dict:
					html += "<br />\n"
					html += prefix + "<b>" + part + ":</b><br />\n"
					html += self.show_element(element[part], prefix + "&nbsp;&nbsp;&nbsp;")
				elif type(element[part]) is list:
					html += "<br />\n"
					html += prefix + "<b>" + part + ":</b><br />\n"
					html += self.show_element(element[part], prefix + "&nbsp;&nbsp;&nbsp;")
		return html;



def inventory_read():
	## get hosts and goups
	hostslist = open("inventory.cfg", "r").read()
	group = "NONE"
	section = ""
	misc = False
	for line in hostslist.split("\n"):
		if line.startswith("[") and ":" in line:
			group = line.strip("[]").split(":")[0]
			section = line.strip("[]").split(":")[1]
			if group not in groups:
				groups[group] = {}
				groups[group]["hosts"] = {}
				groups[group]["options"] = {}
			misc = True
		elif line.startswith("["):
			group = line.strip("[]")
			section = ""
			if group not in groups:
				groups[group] = {}
				groups[group]["hosts"] = {}
				groups[group]["options"] = {}
			misc = False
		elif misc == True and line.strip() != "":
			name = line.split("=")[0].strip()
			value = line.split("=")[1].strip()
			groups[group]["options"][section] = {}
			groups[group]["options"][section][name] = value
		elif misc == False and line.strip() != "":
			host = line.split(" ")[0]
			groups[group]["hosts"][host] = {}
			host_options = line.split(" ")[1:]
			if os.path.isfile("./facts/" + host):
				with open("./facts/" + host) as json_file:
					hostdata = json.load(json_file)
					groups[group]["hosts"][host] = hostdata
			groups[group]["hosts"][host]["options"] = host_options


def run():
	print('starting server...')
	server_address = ('127.0.0.1', 8081)
	httpd = HTTPServer(server_address, HTTPServer_RequestHandler)
	print('running server...')
	httpd.serve_forever()


inventory_read()
print(json.dumps(groups, indent=4))
run()


