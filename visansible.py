#!/usr/bin/python3
#
# ansible -i inventory.cfg all -m setup --tree facts
#

import json
import os
import time
from datetime import datetime
import glob
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import xml.etree.ElementTree as ET

import subprocess
from HtmlPage import *
from VisGraph import *
from bs import *

inventory = {}
ipv4_ips = {}


def facts2rows(facts, options = "", offset = "", units = "", align = "left"):
	global hprefix
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
		if type(facts) is dict and option in facts:
			value = str(facts[option])
			html += hprefix + "<tr><td>" + offset + title + ": </td><td align='" + align + "'>"
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

	def show_graph(self, mode = "group", stamp = "0"):
		if mode == "":
			mode = group
		links = self.show_history(stamp)
		if stamp == "0":
			html = HtmlPage("Visansible <small>(" + str(len(inventory["hosts"])) + " hosts)</small>", "Graph (" + mode + ")", "latest info", links);
		else:
			html = HtmlPage("Visansible <small>(" + str(len(inventory["hosts"])) + " hosts)</small>", "Graph (" + mode + ")", datetime.fromtimestamp(int(stamp)).strftime("%a %d. %b %Y %H:%M:%S"), links);
		graph = VisGraph("visgraph", "800px")
		self.color_n = 0
		for host in inventory["hosts"]:
			if "0" in inventory["hosts"][host] and "ansible_facts" in inventory["hosts"][host]["0"]:
				if mode == "network":
					self.show_host_graph_network_pre(graph, inventory["hosts"][host]["0"]["ansible_facts"], "host_" + host, stamp)
		for host in inventory["hosts"]:
			for group in inventory["hosts"][host]["groups"]:
				if mode == "group":
					graph.node_add("all", "all", "cloud")
					graph.node_add("group_" + group, group, "table")
					graph.edge_add("all", "group_" + group)
				if stamp == "0" or int(stamp) >= int(inventory["hosts"][host]["first"]):
					if mode == "group":
						graph.edge_add("group_" + group, "host_" + host)
					if "0" in inventory["hosts"][host] and "ansible_facts" in inventory["hosts"][host]["0"]:
						fqdn = inventory["hosts"][host]["0"]["ansible_facts"]["ansible_fqdn"]
						osfamily = inventory["hosts"][host]["0"]["ansible_facts"]["ansible_os_family"]
						distribution = inventory["hosts"][host]["0"]["ansible_facts"]["ansible_distribution"]
						productname = ""
						if "ansible_product_name" in inventory["hosts"][host]["0"]["ansible_facts"]:
							productname = inventory["hosts"][host]["0"]["ansible_facts"]["ansible_product_name"]
						architecture = inventory["hosts"][host]["0"]["ansible_facts"]["ansible_architecture"]
						graph.node_add("host_" + host, host + "\\n" + fqdn + "\\n" + osfamily + "\\n" + productname + "\\n" + architecture, osicons_get(osfamily, distribution), "font: {color: '#0000FF'}")
						if mode == "network":
							self.show_host_graph_network(graph, inventory["hosts"][host]["0"]["ansible_facts"], "host_" + host, stamp, True)
					elif "0" in inventory["hosts"][host] and "msg" in inventory["hosts"][host]["0"]:
						graph.node_add("host_" + host, host + "\\n" + inventory["hosts"][host]["0"]["msg"].strip().replace(":", "\\n"), "monitor", "font: {color: '#FF0000'}")
					else:
						if stamp == "0":
							graph.node_add("host_" + host, host + "\\nNO SCANS FOUND", "monitor", "font: {color: '#FF0000'}")
						print(json.dumps(inventory["hosts"][host], indent=4, sort_keys=True));
		html.add(graph.end())
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write(bytes(html.end(), "utf8"))
		return


	def show_host_graph_network_pre(self, graph, facts, parentnode, stamp = "0"):
		for part in facts:
			if part != "ansible_default_ipv4" and type(facts[part]) is dict and "device" in facts[part]:
				device = facts[part]["device"]
				if ("active" in facts[part] and facts[part]["active"] == False) or device == "lo" or device == "lo0":
					continue
				if "ipv4" in facts[part]:
					if type(facts[part]["ipv4"]) == list:
						for ipv4 in facts[part]["ipv4"]:
							address = ipv4["address"]
							ipv4_ips[address] = parentnode + "_ipv4_" + address
							self.color_n = self.color_n + 1
							if self.color_n >= len(self.colors):
								self.color_n = 0; 
					else:
						address = facts[part]["ipv4"]["address"]
						ipv4_ips[address] = parentnode + "_ipv4_" + address


	def show_host_graph_network(self, graph, facts, parentnode, stamp = "0", simple = False):
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
											graph.edge_add(parentnode + "_ipv4_" + address, "network_" + network, "color: { color: '" + ipv4_ips[gateway_address] + "'}, arrows: {to: true}, label: 'gw:." + gateway_address.split(".")[-1] + "'")
										else:
											graph.edge_add(parentnode + "_ipv4_" + address, "network_" + network, "color: { color: '" + self.colors[self.color_n] + "'}, arrows: {to: true}, label: 'gw:." + gateway_address.split(".")[-1] + "'")
											self.color_n = self.color_n + 1
											if self.color_n >= len(self.colors):
												self.color_n = 0; 
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
											graph.edge_add("network_" + network, ipv4_ips[gateway_address], "color: { color: '" + ipv4_ips[gateway_address] + "'}, arrows: {to: true}, label: 'gw:." + gateway_address.split(".")[-1] + "'")
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
										graph.edge_add(parentnode + "_ipv4_" + address, "network_" + network, "color: { color: '" + ipv4_ips[gateway_address] + "'}, arrows: {to: true}, label: 'gw:." + gateway_address.split(".")[-1] + "'")
									else:
										graph.edge_add(parentnode + "_ipv4_" + address, "network_" + network, "color: { color: '" + self.colors[self.color_n] + "'}, arrows: {to: true}, label: 'gw:." + gateway_address.split(".")[-1] + "'")
										self.color_n = self.color_n + 1
										if self.color_n >= len(self.colors):
											self.color_n = 0; 
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
										graph.edge_add("network_" + network, ipv4_ips[gateway_address], "color: { color: '" + ipv4_ips[gateway_address] + "'}, arrows: {to: true}, label: 'gw:." + gateway_address.split(".")[-1] + "'")
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

		## Windows ##
		if "ansible_interfaces" in facts and type(facts["ansible_interfaces"]) is list:
			## default_gateway
			for iface in facts["ansible_interfaces"]:
				if type(iface) is dict:
					if "interface_name" in iface:
						device = iface["interface_name"]
						if "macaddress" in iface:
							macaddress = iface["macaddress"]
						else:
							macaddress = ""
						if simple == False:
							graph.node_add(parentnode + "_iface_" + device, device + "\\n" + macaddress, "port")
							graph.edge_add(parentnode, parentnode + "_iface_" + device)
		if "ansible_ip_addresses" in facts:
			for address in facts["ansible_ip_addresses"]:
				if ":" in address:
					if simple == False:
						graph.node_add(parentnode + "_ipv6_" + address, address, "ipv6")
						graph.edge_add(parentnode, parentnode + "_ipv6_" + address)
				else:
					graph.node_add(parentnode + "_ipv4_" + address, address, "ipv4")
					graph.edge_add(parentnode, parentnode + "_ipv4_" + address)

					network = ".".join(address.split(".")[:3]) + ".0"
					graph.node_add("network_" + network, network, "net");
					graph.edge_add(parentnode + "_ipv4_" + address, "network_" + network)



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
								if facts["ansible_devices"][device]["partitions"][partition]["uuid"] != None and facts["ansible_devices"][device]["partitions"][partition]["uuid"] != "N/A" and mount["uuid"] != "N/A" and mount["uuid"] != None:
									if mount["uuid"] == facts["ansible_devices"][device]["partitions"][partition]["uuid"]:
										graph.node_add(parentnode + "_mount_" + mount["mount"], mount["mount"] + "\\n" + mount["fstype"] + "\\n" + mount["device"], "folder-open")
										graph.edge_add(parentnode + "_partition_" + partition, parentnode + "_mount_" + mount["mount"])
								else:
									if mount["device"] == "/dev/" + partition:
										graph.node_add(parentnode + "_mount_" + mount["mount"], mount["mount"] + "\\n" + mount["fstype"] + "\\n" + mount["device"], "folder-open")
										graph.edge_add(parentnode + "_partition_" + partition, parentnode + "_mount_" + mount["mount"])
						## show disk-mounts ##
						for mount in facts["ansible_mounts"]:
							if "links" in facts["ansible_devices"][device] and "uuids" in facts["ansible_devices"][device]["links"]:
								for disk_uuid in facts["ansible_devices"][device]["links"]["uuids"]:
									if mount["uuid"] == disk_uuid:
										graph.node_add(parentnode + "_mount_" + mount["mount"], mount["mount"] + "\\n" + mount["fstype"] + "\\n" + mount["device"], "folder-open")
										graph.edge_add(parentnode + "_disk_" + device, parentnode + "_mount_" + mount["mount"])


	def show_host_table_ifaces(self, facts):
		html = ""
		if "ansible_default_ipv4" in facts:
			if "gateway" in facts["ansible_default_ipv4"]:
				gateway_address = facts["ansible_default_ipv4"]["gateway"]
				gateway_interface = facts["ansible_default_ipv4"]["interface"]
		for part in facts:
			if part != "ansible_default_ipv4" and type(facts[part]) is dict and "device" in facts[part]:
				html += bs_col_begin("6")
				html += bs_card_begin("Network-Interface: " + facts[part]["device"], "port")
				html += bs_row_begin()
				html += bs_col_begin("6")
				html += bs_add("<b>Interface:</b>")
				html += bs_table_begin()
				html += facts2rows(facts[part], ["device", "model", "macaddress", "mtu", "promisc", "type", "active"])
				html += bs_table_end()
				html += bs_col_end()
				html += bs_col_begin("6")
				if "ipv4" in facts[part]:
					if type(facts[part]["ipv4"]) == list:
						for ipv4 in facts[part]["ipv4"]:
							fact = ipv4
							html += bs_add("<b>IPv4:</b>")
							html += bs_table_begin()
							html += facts2rows(ipv4, ["address", "netmask", "broadcast", "network"])
							html += bs_table_end()
							bs_add("<br />")
					else:
						html += bs_add("<b>IPv4:</b>")
						html += bs_table_begin()
						html += facts2rows(facts[part]["ipv4"], ["address", "netmask", "broadcast", "network"])
						html += bs_table_end()
						bs_add("<br />")
				if "ipv6" in facts[part]:
					for ipv6 in facts[part]["ipv6"]:
						html += bs_add("<b>IPv6:</b>")
						html += bs_table_begin()
						html += facts2rows(ipv6, ["address", "prefix", "scope"])
						html += bs_table_end()
						bs_add("<br />")
				html += bs_col_end()
				html += bs_row_end()
				html += bs_card_end()
				html += bs_col_end()
		## Windows ##
		if "ansible_interfaces" in facts and type(facts["ansible_interfaces"]) is list:
			for iface in facts["ansible_interfaces"]:
				if type(iface) is dict:
					html += bs_col_begin("6")
					html += bs_card_begin("Network-Interface: ", "port")
					html += bs_row_begin()
					html += bs_col_begin("6")
					html += bs_add("<b>Interface:</b>")
					html += bs_table_begin()
					html += facts2rows(iface)
					html += bs_table_end()
					html += bs_col_end()
					html += bs_col_begin("6")
					html += "----"
					html += bs_col_end()
					html += bs_row_end()
					html += bs_card_end()
					html += bs_col_end()
		if "ansible_ip_addresses" in facts:
			html += bs_col_begin("6")
			html += bs_card_begin("IP-Addresses: ", "port")
			for address in facts["ansible_ip_addresses"]:
				html += address + "<br />"
			html += bs_card_end()
			html += bs_col_end()
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
				html += bs_col_begin("6")
				html += bs_card_begin("Disk: " + device, "harddisk")
				html += bs_row_begin()
				## show disk ##
				html += bs_col_begin("6")
				html += bs_add("<b>Disk: " + device + "</b>")
				html += bs_table_begin()
				for mount in facts["ansible_mounts"]:
					if mount["device"] == "/dev/" + device:
						html += facts2rows(mount, ["mount", "fstype", "device", "size_available", "options", "uuid"])
						html += bs_add("<tr><td>&nbsp;</td><td>&nbsp;</td></tr>")
				html += bs_table_end()
				html += bs_col_end()
				## show partitions ##
				html += bs_col_begin("6")
				for partition in facts["ansible_devices"][device]:
					html += bs_add("<b>Partition: " + partition + "</b>")
					html += bs_table_begin()
					## show mounts ##
					for mount in facts["ansible_mounts"]:
						if mount["device"] == "/dev/" + partition:
							html += facts2rows(mount, ["mount", "fstype", "device", "size_available", "options", "uuid"])
							html += bs_add("<tr><td>&nbsp;</td><td>&nbsp;</td></tr>")
					html += bs_table_end()
					bs_add("<br />")
				html += bs_col_end()
				html += bs_row_end()
				html += bs_card_end()
				html += bs_col_end()
			if "partitions" in facts["ansible_devices"][device]:
				if facts["ansible_devices"][device]["size"] != "0.00 Bytes" and (len(dms) == 0 or not device.startswith("dm-") ):
					html += bs_col_begin("6")
					if "model" in facts["ansible_devices"][device] and ("DVD" in str(facts["ansible_devices"][device]["model"]) or "CD" in str(facts["ansible_devices"][device]["model"])):
						html += bs_card_begin("Disk: " + device, "disk-player")
					else:
						html += bs_card_begin("Disk: " + device, "harddisk")
					html += bs_row_begin()
					## show disk ##
					html += bs_col_begin("6")
					html += bs_add("<b>Disk:</b>")
					html += bs_table_begin()
					html += facts2rows(facts["ansible_devices"][device], ["host", "vendor", "model", "serial", "size"])
					## show disk-mounts ##
					for mount in facts["ansible_mounts"]:
						if "links" in facts["ansible_devices"][device] and "uuids" in facts["ansible_devices"][device]["links"]:
							for disk_uuid in facts["ansible_devices"][device]["links"]["uuids"]:
								if mount["uuid"] == disk_uuid:
									html += facts2rows(mount, ["mount", "fstype", "device", "size_available", "options", "uuid"])
									html += bs_add("<tr><td>&nbsp;</td><td>&nbsp;</td></tr>")

					## check if device is slave of another disk ##
					for device2 in facts["ansible_devices"]:
						if "links" in facts["ansible_devices"][device2] and "masters" in facts["ansible_devices"][device2]["links"]:
							for master in facts["ansible_devices"][device2]["links"]["masters"]:
								if device == master:
									html += bs_add("<tr>")
									html += bs_add(" <td>Master: </td>")
									html += bs_add(" <td>" + device2 + "</td>")
									html += bs_add("</tr>")

					## check if device is slave of another partition ##
					for device2 in facts["ansible_devices"]:
						if "partitions" in facts["ansible_devices"][device2]:
							for partition2 in facts["ansible_devices"][device2]["partitions"]:
								if "links" in facts["ansible_devices"][device2]["partitions"][partition2] and "masters" in facts["ansible_devices"][device2]["partitions"][partition2]["links"]:
									for master in facts["ansible_devices"][device2]["partitions"][partition2]["links"]["masters"]:
										if device == master:
											html += bs_add("<tr>")
											html += bs_add(" <td>Master: </td>")
											html += bs_add(" <td>" + partition2 + "</td>")
											html += bs_add("</tr>")
					## show disk slaves ##
					if "links" in facts["ansible_devices"][device] and "masters" in facts["ansible_devices"][device]["links"]:
						for master in facts["ansible_devices"][device]["links"]["masters"]:
							html += bs_add("<tr>")
							html += bs_add(" <td>Slave-Device: </td>")
							html += bs_add(" <td>" + master + "</td>")
							html += bs_add("</tr>")
					html += bs_table_end()
					html += bs_col_end()
					## show partitions ##
					html += bs_col_begin("6")
					for partition in facts["ansible_devices"][device]["partitions"]:
						html += bs_add("<b>Partition: " + partition + "</b>")
						html += bs_table_begin()
						## show partition ##
						html += facts2rows(facts["ansible_devices"][device]["partitions"][partition], ["uuid", "size", "start", "sectors", "sectorsize"])
						## show partition slaves ##
						if "links" in facts["ansible_devices"][device]["partitions"][partition] and "masters" in facts["ansible_devices"][device]["partitions"][partition]["links"]:
							for master in facts["ansible_devices"][device]["partitions"][partition]["links"]["masters"]:
								html += bs_add("<tr>")
								html += bs_add(" <td>Slave-Device: </td>")
								html += bs_add(" <td>" + master + "</td>")
								html += bs_add("</tr>")
						## show mounts ##
						for mount in facts["ansible_mounts"]:
							if facts["ansible_devices"][device]["partitions"][partition]["uuid"] != None and facts["ansible_devices"][device]["partitions"][partition]["uuid"] != "N/A" and mount["uuid"] != "N/A" and mount["uuid"] != None:
								if mount["uuid"] == facts["ansible_devices"][device]["partitions"][partition]["uuid"]:
									html += facts2rows(mount, ["mount", "fstype", "device", "size_available", "options", "uuid"], "&nbsp;&nbsp;&nbsp;")
									html += bs_add("<tr><td>&nbsp;</td><td>&nbsp;</td></tr>")
							else:
								if mount["device"] == "/dev/" + partition:
									html += facts2rows(mount, ["mount", "fstype", "device", "size_available", "options", "uuid"], "&nbsp;&nbsp;&nbsp;")
									html += bs_add("<tr><td>&nbsp;</td><td>&nbsp;</td></tr>")
						html += bs_table_end()
						bs_add("<br />")
					html += bs_col_end()
					html += bs_row_end()
					html += bs_card_end()
					html += bs_col_end()
		if "ansible_lvm" in facts:
			if "vgs" in facts["ansible_lvm"]:
				for vg in facts["ansible_lvm"]["vgs"]:
					vg_pv = facts["ansible_lvm"]["vgs"][vg]
					html += bs_col_begin("6")
					html += bs_card_begin("LVM_VG: " + vg, "harddisk")
					html += bs_row_begin()
					html += bs_col_begin("6")
					html += bs_add("<b>VG:</b>")
					html += bs_table_begin()
					html += facts2rows(facts["ansible_lvm"]["vgs"][vg], ["size_g", "free_g", "num_lvs", "num_pvs"])
					if "pvs" in facts["ansible_lvm"]:
						for pv in facts["ansible_lvm"]["pvs"]:
							pv_vg = facts["ansible_lvm"]["pvs"][pv]["vg"]
							if pv_vg == vg:
								html += bs_add("<tr>")
								html += bs_add(" <td>&nbsp;&nbsp;&nbsp;PV: </td>")
								html += bs_add(" <td>" + pv + "</td>")
								html += bs_add("</tr>")
								html += facts2rows(facts["ansible_lvm"]["pvs"][pv], ["size_g", "free_g"], "&nbsp;&nbsp;&nbsp;")
								html += bs_add("<tr><td>&nbsp;</td><td>&nbsp;</td></tr>")
					html += bs_table_end()
					html += bs_col_end()
					html += bs_col_begin("6")
					if "lvs" in facts["ansible_lvm"]:
						for lv in facts["ansible_lvm"]["lvs"]:
							lv_vg = facts["ansible_lvm"]["lvs"][lv]["vg"]
							if lv_vg == vg:
								lv_device = "/dev/mapper/" + vg + "-" + lv
								html += bs_add("<b>LV: " + lv + "</b>")
								html += bs_table_begin()
								html += facts2rows(facts["ansible_lvm"]["lvs"][lv], ["size_g"])
								## show mounts ##
								for mount in facts["ansible_mounts"]:
									if mount["device"] == lv_device:
										html += facts2rows(mount, ["mount", "fstype", "device", "size_available", "options", "uuid"], "&nbsp;&nbsp;&nbsp;")
										html += bs_add("<tr><td>&nbsp;</td><td>&nbsp;</td></tr>")
								html += bs_table_end()
								bs_add("<br />")
					html += bs_col_end()
					html += bs_row_end()
					html += bs_card_end()
					html += bs_col_end()
		return html


	def show_host_table_general(self, facts):
		osfamily = facts["ansible_os_family"]
		distribution = facts["ansible_distribution"]
		html = ""
		html += bs_col_begin("6")
		html += bs_card_begin("General", osicons_get(osfamily, distribution))
		html += bs_row_begin()
		html += bs_col_begin("6")
		html += bs_table_begin()
		html += facts2rows(facts, ["ansible_fqdn", "ansible_system_vendor", "ansible_product_name", "ansible_product_serial", "ansible_architecture", "ansible_memtotal_mb", "ansible_virtualization_role", "ansible_virtualization_type"])
		html += bs_table_end()
		html += bs_col_end()
		html += bs_col_begin("6")
		html += bs_table_begin()
		html += facts2rows(facts, ["ansible_distribution", "ansible_distribution_major_version", "ansible_distribution_release", "ansible_distribution_version", "ansible_distribution_file_variety", "ansible_userspace_architecture", "ansible_kernel", "ansible_pkg_mgr"])
		html += bs_table_end()
		html += bs_col_end()
		html += bs_row_end()
		html += bs_row_begin()
		html += bs_col_begin("12")
		html += bs_add("<hr />")
		html += bs_col_end()
		html += bs_row_end()
		html += bs_row_begin()
		html += bs_col_begin("6")
		html += bs_add("<b>CPUs/Cores/Threads:</b><br />")
		html += bs_table_begin()
		html += facts2rows(facts, ["ansible_processor_count", "ansible_processor_cores", "ansible_processor_threads_per_core", "ansible_processor_vcpus"], "", "", "right")
		html += bs_table_end()
		html += bs_col_end()
		html += bs_col_begin("6")
		html += bs_add("<b>Types:</b><br />")
		html += bs_table_begin()
		if "ansible_processor" in facts:
			processor_n = 0
			for part in facts["ansible_processor"]:
				if part.isdigit():
					processor_n += 1
					if processor_n != 1:
						html += bs_add("</td>")
						html += bs_add("</tr>")
					html += bs_add("<tr>")
					html += bs_add(" <td>#" + str(processor_n) + ": </td>")
					html += bs_add(" <td>")
				else:
					html += part + " "
			html += bs_add("</td>")
			html += bs_add("</tr>")
		html += bs_table_end()
		html += bs_col_end()
		html += bs_row_end()
		html += bs_card_end()
		html += bs_col_end()
		return html


	def show_host_table_memory_hist(self, facts, stamp, hostname):
		html = ""
		if "ansible_memory_mb" in facts:
			html += bs_add("<canvas id='lcmemory' width='100%' height='20'></canvas>");
			stamps = []
			for host in inventory["hosts"]:
				for timestamp in inventory["hosts"][host]:
					if timestamp.isdigit() and timestamp != "0":
						stamps.append(timestamp)
			labels = []
			datas = []
			trange = (3600 * 12)
			tsteps = 300
			laststamp = int(stamp)
			for timestamp in sorted(set(stamps)):
				if stamp == "0" or int(timestamp) <= int(stamp):
					labels.append("")
			for section in ["nocache", "real", "swap"]:
				last = 0
				data = []
				for timestamp in sorted(set(stamps)):
					if hostname in inventory["hosts"] and timestamp in inventory["hosts"][hostname]:
						if "ansible_facts" in inventory["hosts"][hostname][timestamp]:
							if "ansible_memory_mb" in inventory["hosts"][hostname][timestamp]["ansible_facts"]:
								if section in inventory["hosts"][hostname][timestamp]["ansible_facts"]["ansible_memory_mb"]:
									if "used" in inventory["hosts"][hostname][timestamp]["ansible_facts"]["ansible_memory_mb"][section]:
										last = int(inventory["hosts"][hostname][timestamp]["ansible_facts"]["ansible_memory_mb"][section]["used"])
					data.append(last)
				datas.append(data)
			html += self.show_chart("lcmemory", labels, datas, ["nocache", "real", "swap"])
		return html


	def show_host_table_memory(self, facts, stamp, hostname):
		html = ""
		if "ansible_memory_mb" in facts:
			html += bs_col_begin("6")
			html += bs_card_begin("Memory", "memory")
			html += bs_row_begin()
			for section in ["nocache", "real", "swap"]:
				if section in facts["ansible_memory_mb"]:
					html += bs_col_begin("4")
					html += bs_add("<b>" + section.capitalize() + ":</b><br />")
					html += bs_table_begin()
					html += facts2rows(facts["ansible_memory_mb"][section], "", "", "MB", "right")
					html += bs_table_end()
					html += bs_col_end()
			html += bs_row_end()
			html += bs_card_end()
			html += bs_col_end()
		return html


	def show_host_table_mounts(self, facts, stamp, hostname):
		html = ""
		if "ansible_mounts" not in facts:
			return html
		html += bs_col_begin("6")
		html += bs_card_begin("Mounts", "folder-open")
		html += bs_row_begin()
		for mount in facts["ansible_mounts"]:
			html += bs_col_begin("6")
			html += bs_add("<b>Mount:</b><br />")
			html += bs_table_begin()
			html += facts2rows(mount, ["mount", "fstype", "device", "size_available", "options", "uuid"])
			html += bs_table_end()
			bs_add("<br />")
			html += bs_col_end()
		html += bs_row_end()
		html += bs_card_end()
		html += bs_col_end()
		return html


	def show_host_table_mounts_hist(self, facts, stamp, hostname):
		html = ""
		if "ansible_mounts" not in facts:
			return html
		html += bs_add("<canvas id='lcmounts' width='100%' height='20'></canvas>");
		stamps = []
		for host in inventory["hosts"]:
			for timestamp in inventory["hosts"][host]:
				if timestamp.isdigit() and timestamp != "0":
					stamps.append(timestamp)
		labels = []
		datas = []
		units = []
		trange = (3600 * 12)
		tsteps = 300
		laststamp = int(stamp)
		for timestamp in sorted(set(stamps)):
			if stamp == "0" or int(timestamp) <= int(stamp):
				labels.append("")
		mount_n = 0
		for mount in facts["ansible_mounts"]:
			units.append(mount["mount"])
			last = 0
			data = []
			for timestamp in sorted(set(stamps)):
				if hostname in inventory["hosts"] and timestamp in inventory["hosts"][hostname]:
					if "ansible_facts" in inventory["hosts"][hostname][timestamp]:
						if "ansible_mounts" in inventory["hosts"][hostname][timestamp]["ansible_facts"]:
							if mount_n < len(inventory["hosts"][hostname][timestamp]["ansible_facts"]["ansible_mounts"]):
								if "size_available" in inventory["hosts"][hostname][timestamp]["ansible_facts"]["ansible_mounts"][mount_n]:
									value = int(inventory["hosts"][hostname][timestamp]["ansible_facts"]["ansible_mounts"][mount_n]["size_available"]) * 100 / int(inventory["hosts"][hostname][timestamp]["ansible_facts"]["ansible_mounts"][mount_n]["size_total"])
									last = 100 - value
				data.append(last)
			datas.append(data)
			mount_n += 1
		html += self.show_chart("lcmounts", labels, datas, units)
		return html


	def show_host_table_network(self, facts):
		html = ""
		html += bs_col_begin("6")
		html += bs_card_begin("Network", "net")
		html += bs_row_begin()
		html += bs_col_begin("6")
		html += bs_add("<b>Hostname & Domain:</b><br />")
		html += bs_table_begin()
		html += facts2rows(facts, ["ansible_hostname", "ansible_domain", "ansible_fqdn"])
		html += bs_table_end()
		html += bs_col_end()
		html += bs_col_begin("6")
		html += bs_add("<b>DNS-Server:</b><br />")
		html += bs_table_begin()
		if "ansible_dns" in facts:
			if "nameservers" in facts["ansible_dns"]:
				for nameserver in facts["ansible_dns"]["nameservers"]:
					html += bs_add("<tr>")
					html += bs_add(" <td>DNS-Server: </td>")
					html += bs_add(" <td>" + nameserver + "</td>")
					html += bs_add("</tr>")
			if "search" in facts["ansible_dns"]:
				for search in facts["ansible_dns"]["search"]:
					html += bs_add("<tr>")
					html += bs_add(" <td>DNS-Search: </td>")
					html += bs_add(" <td>" + search + "</td>")
					html += bs_add("</tr>")
		html += bs_table_end()
		bs_add("<br />")
		html += bs_add("<b>Default-Gateway:</b><br />")
		html += bs_table_begin()
		if "ansible_default_ipv4" in facts:
			html += facts2rows(facts["ansible_default_ipv4"], ["gateway", "interface"])
		html += bs_table_end()
		html += bs_col_end()
		html += bs_row_end()
		html += bs_card_end()
		html += bs_col_end()
		return html


	def show_history(self, stamp = "0",  hostname = ""):
		links = ""
		links = bs_add("<br /><canvas id='myAreaChart' width='100%' height='30'></canvas>")
		stamps = []
		for host in inventory["hosts"]:
			for timestamp in inventory["hosts"][host]:
				if timestamp.isdigit() and timestamp != "0":
					stamps.append(timestamp)
		labels = []
		data = []
		data2 = []
		datas = []
		trange = (3600 * 12)
		tsteps = 600
		laststamp = int(stamp)
		if stamp == "0":
			laststamp = int(time.time())
		for timestamp in range(laststamp - trange, laststamp + tsteps, tsteps):
			labels.append("")
		if hostname != "":
			if inventory["hosts"][hostname]["first"] != "0":
				last = 0
				for timestamp in range(int(inventory["hosts"][hostname]["first"]), laststamp):
					if str(timestamp) in inventory["hosts"][hostname]:
						if "ansible_facts" in inventory["hosts"][hostname][str(timestamp)]:
							last = 1
						else:
							last = 0
					if timestamp >= int(inventory["hosts"][hostname]["first"]) and timestamp % tsteps == 0:
						data.append(last)
				datas.append(data)
				links += self.show_chart("myAreaChart", labels, datas)
			links += bs_table_begin()
			links += bs_add("<tr><td><a href='?host=" + hostname + "&stamp=0'>latest info</a></td></tr>")
			for tstamp in inventory["hosts"][hostname]:
				if tstamp.isdigit() and tstamp != "0":

					if "ansible_facts" in inventory["hosts"][hostname][tstamp]:
						stat = "OK"
					else:
						stat = "ERR"
					sstamp = ""
					if stamp == tstamp:
						sstamp += "&lt;"
					links += bs_add("<tr><td><a href='?host=" + hostname + "&stamp=" + tstamp + "'>" + datetime.fromtimestamp(int(tstamp)).strftime("%a %d. %b %Y %H:%M:%S") + "</a></td><td>" + stat + "</td><td>" + sstamp + "</td></tr>")
			links += bs_table_end()
			return links
		else:
			for timestamp in range(laststamp - trange, laststamp + tsteps, tsteps):
				n = 0
				n2 = 0
				for host in inventory["hosts"]:
					last = 0
					last2 = 0
					for hstamp in sorted(inventory["hosts"][host]):
						if hstamp != "0" and hstamp.isdigit():
							if int(timestamp) >= int(hstamp):
								if "ansible_facts" in inventory["hosts"][host][hstamp]:
									last = 1
									last2 = 1
								else:
									last = 0
					n += last
					n2 += last2
				data.append(n)
				data2.append(n2)
			datas.append(data)
			datas.append(data2)
			links += self.show_chart("myAreaChart", labels, datas)
			links += bs_table_begin()
			links += bs_add("<tr><td><a href='?stamp=0'>latest info</a></td></tr>")
			for tstamp in sorted(set(stamps), reverse=True):
				if stamp == tstamp:
					links += bs_add("<tr><td><a href='?stamp=" + tstamp + "'>" + datetime.fromtimestamp(int(tstamp)).strftime("%a %d. %b %Y %H:%M:%S") + "</a>&lt;</td></tr>")
				else:
					links += bs_add("<tr><td><a href='?stamp=" + tstamp + "'>" + datetime.fromtimestamp(int(tstamp)).strftime("%a %d. %b %Y %H:%M:%S") + "</a></td></tr>")
			links += bs_table_end()
			return links


	def show_hostdata(self, host, stamp = "0"):
		links = self.show_history(stamp, host)
		groups = " Groups: "
		for group in inventory["hosts"][host]["groups"]:
			groups += "<a href='/hosts?group=" + group + "'>" + group + "</a> "
		if stamp == "0":
			html = HtmlPage("Visansible <small>(" + str(len(inventory["hosts"])) + " hosts)</small>", "Host (" + host + ") <a href='/rescan?host=" + host + "'>[RESCAN]</a>" + groups, "latest info", links);
		else:
			html = HtmlPage("Visansible <small>(" + str(len(inventory["hosts"])) + " hosts)</small>", "Host (" + host + ") <a href='/rescan?host=" + host + "'>[RESCAN]</a>" + groups, datetime.fromtimestamp(int(stamp)).strftime("%a %d. %b %Y %H:%M:%S") + "", links);
		if "0" in inventory["hosts"][host] and "ansible_facts" in inventory["hosts"][host][stamp]:
			osfamily = inventory["hosts"][host][stamp]["ansible_facts"]["ansible_os_family"]
			distribution = inventory["hosts"][host][stamp]["ansible_facts"]["ansible_distribution"]
			icon = osicons_get(osfamily, distribution)
			## System ##
			html.add(bs_row_begin())
			html.add(self.show_host_table_general(inventory["hosts"][host][stamp]["ansible_facts"]))
			html.add(bs_col_begin("6"))
			html.add(bs_card_begin("History", "clock"))
			html.add(bs_add("<b>Memory-Usage:</b>"))
			html.add(self.show_host_table_memory_hist(inventory["hosts"][host][stamp]["ansible_facts"], stamp, host))
			html.add(bs_add("<hr />"))
			html.add(bs_add("<b>Disk-Usage:</b>"))
			html.add(self.show_host_table_mounts_hist(inventory["hosts"][host][stamp]["ansible_facts"], stamp, host))
			html.add(bs_card_end())
			html.add(bs_col_end())
			html.add(self.show_host_table_memory(inventory["hosts"][host][stamp]["ansible_facts"], stamp, host))
			html.add(self.show_host_table_network(inventory["hosts"][host][stamp]["ansible_facts"]))
			html.add(bs_row_end())
			## Network ##
			html.add(bs_row_begin())
			html.add(self.show_host_table_ifaces(inventory["hosts"][host][stamp]["ansible_facts"]))
			html.add(bs_row_end())
			html.add(bs_row_begin())
			html.add(bs_col_begin("12"))
			html.add(bs_card_begin("Network-Graph", "net"))
			graph = VisGraph("vis_network")
			graph.node_add("host_" + host, host, icon)
			self.show_host_graph_network(graph, inventory["hosts"][host][stamp]["ansible_facts"], "host_" + host)
			html.add(graph.end(direction = "UD"))
			html.add(bs_card_end())
			html.add(bs_col_end())
			html.add(bs_row_end())
			## Disks ##
			html.add(bs_row_begin())
			html.add(self.show_host_table_disks(inventory["hosts"][host][stamp]["ansible_facts"]))
			html.add(self.show_host_table_mounts(inventory["hosts"][host][stamp]["ansible_facts"], stamp, host))
			html.add(bs_col_begin("12"))
			html.add(bs_card_begin("Disks-Graph", "harddisk"))
			graph = VisGraph("vis_disks")
			graph.node_add("host_" + host, host, icon)
			self.show_host_graph_disks(graph, inventory["hosts"][host][stamp]["ansible_facts"], "host_" + host)
			html.add(graph.end(direction = "UD"))
			html.add(bs_card_end())
			html.add(bs_col_end())
			html.add(bs_row_end())
		else:
			if "0" in inventory["hosts"][host] and "msg" in inventory["hosts"][host][stamp]:
				html.add("<b>" + inventory["hosts"][host][stamp]["msg"].strip() + "</b>\n")
			else:
				html.add("<b>NO SCANS FOUND</b>\n")
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write(bytes(html.end(), "utf8"))
		return


	def show_hosts(self, stamp = "0", sgroup = "all", search = ""):
		if search != "":
			search = search.replace("%20", " ")
		options = ["ansible_fqdn", "ansible_distribution", "ansible_architecture", "ansible_product_name", "ansible_product_serial"]
		if stamp == "0":
			html = HtmlPage("Visansible <small>(" + str(len(inventory["hosts"])) + " hosts)</small>", "Hosts (" + sgroup + ")", "latest info", self.show_history(stamp));
		else:
			html = HtmlPage("Visansible <small>(" + str(len(inventory["hosts"])) + " hosts)</small>", "Hosts (" + sgroup + ")", datetime.fromtimestamp(int(stamp)).strftime("%a %d. %b %Y %H:%M:%S"), self.show_history(stamp));
		stamps = []
		html.add("\n")
		html.add(bs_add("<input id='search' type='text' name='search' value='' /><br />"))
		html.add("<script>\n")
		html.add("document.getElementById('search').onkeypress = function(event){\n")
		html.add(" if (event.keyCode == 13 || event.which == 13){\n")
		html.add("  location.href = '/hosts?search=' + document.getElementById('search').value;\n")
		html.add(" }\n")
		html.add("};\n")
		html.add("$('#search').focus();\n")
		html.add("$('#search').val('" + search + "');\n")
		html.add("$('#search').focus();\n")
		html.add("</script>\n")
		html.add("\n")
		for host in inventory["hosts"]:
			for timestamp in inventory["hosts"][host]:
				if timestamp.isdigit() and timestamp != "0":
					stamps.append(timestamp)
		html.add(bs_row_begin())
		html.add(bs_col_begin("12"))
		html.add(bs_add("<table class='table table-hover' width='90%'>"))
		if search != "":
			html.add("<tr>\n")
			html.add(" <th>Stamp</th>\n")
			html.add(" <th>Host</th>\n")
			for option in options:
				title = option.replace("ansible_", "").capitalize()
				html.add(" <th>" + title + "</th>\n")
			html.add(" <th width='10%'>Options</th>\n")
			html.add(" <th width='10%'>Status</th>\n")
			html.add("</tr>\n")
		for group in inventory["groups"]:
			if sgroup == "all" or sgroup == group:
				if search == "":
					if sgroup == group:
						html.add("<tr onClick=\"location.href = 'hosts?group=all';\">\n")
					else:
						html.add("<tr onClick=\"location.href = 'hosts?group=" + group + "';\">\n")
					html.add(" <td colspan='" + str(len(options) + 4) + "'>\n")
					html.add("  <h2>Group: " + group + " </h2>\n")
					html.add("  <a href='/rescan?host=" + group + "'>[RESCAN]<a/>\n")
					for section in inventory["groups"][group]["options"]:
						for var in inventory["groups"][group]["options"][section]:
							html.add("<small>" + var + "=" + inventory["groups"][group]["options"][section][var] + " </small>")
					html.add(" </td>\n")
					html.add("</tr>\n")
					html.add("<tr>\n")
					html.add(" <th>Stamp</th>\n")
					html.add(" <th>Host</th>\n")
					for option in options:
						title = option.replace("ansible_", "").capitalize()
						html.add(" <th>" + title + "</th>\n")
					html.add(" <th width='10%'>Options</th>\n")
					html.add(" <th width='10%'>Status</th>\n")
					html.add("</tr>\n")
				for host in inventory["hosts"]:
					hoststamp = "0"
					searchinfo = ""
					if group not in inventory["hosts"][host]["groups"]:
						continue
					if search != "":
						match = False
						if "0" in inventory["hosts"][host] and "ansible_facts" in inventory["hosts"][host]["0"]:
							facts = inventory["hosts"][host]["0"]["ansible_facts"]
							match = True
							for psearch in search.split(" "):
								matches = {}
								res, matches = self.search_element(facts, psearch, "", matches)
								if res == False:
									match = False
								else:
									rank = 0
									rank2 = 0
									searchinfo += psearch + ":("
									for path in matches:
										searchinfo += path.lstrip("/") + "(" + str(matches[path][0]) + ")=" + self.matchmark(matches[path][1], psearch, "#FFABAB") + ", "
										if rank < matches[path][0]:
											rank = matches[path][0]
										rank2 += 1
									searchinfo += ") " + str(rank + rank2) + " <br />"
						if match == False:
							continue
					if stamp != "0":
						for timestamp in sorted(set(stamps)):
							if int(stamp) >= int(timestamp) and timestamp in inventory["hosts"][host]:
								hoststamp = timestamp
					if stamp == "0" or int(stamp) >= int(inventory["hosts"][host]["first"]):
						html.add("<tr onClick=\"location.href = 'host?host=" + host + "';\">\n")
						if stamp != "0":
							html.add(" <td>" + datetime.fromtimestamp(int(hoststamp)).strftime("%a %d. %b %Y %H:%M:%S") + "</td>\n")
						else:
							html.add(" <td>" + datetime.fromtimestamp(int(inventory["hosts"][host]["stamp"])).strftime("%a %d. %b %Y %H:%M:%S") + "</td>\n")
						html.add(" <td width='10%'>" + host + "</td>\n")
						if hoststamp in inventory["hosts"][host] and "ansible_facts" in inventory["hosts"][host][hoststamp]:
							for option in options:
								if "ansible_facts" in inventory["hosts"][host][hoststamp] and option in inventory["hosts"][host][hoststamp]["ansible_facts"]:
									value = str(inventory["hosts"][host][hoststamp]["ansible_facts"][option])
									if option == "ansible_distribution":
										html.add("<td width='10%'>")
										osfamily = inventory["hosts"][host][hoststamp]["ansible_facts"]["ansible_os_family"]
										distribution = inventory["hosts"][host][hoststamp]["ansible_facts"]["ansible_distribution"]
										html.add("<img src='assets/MaterialDesignIcons/" + osicons_get(osfamily, distribution) + ".svg' />\n")
									else:
										html.add("<td>")
									html.add(value)
									html.add("</td>\n")
								else:
									html.add(" <td>---</td>\n")
							if "options" in inventory["hosts"][host]:
								html.add(" <td>" + ", ".join(inventory["hosts"][host]["options"]) + "</td>\n")
							else:
								html.add(" <td>---</td>\n")
							if stamp != "0":
								html.add(" <td colspan='6' style='color: #00FF00;'>OK <a href='/rescan?host=" + host + "'>[RESCAN]<a/></td>\n")
						else:
							if hoststamp in inventory["hosts"][host] and "msg" in inventory["hosts"][host][hoststamp]:
								html.add(" <td colspan='6' style='color: #FF0000;'>" + inventory["hosts"][host][hoststamp]["msg"].strip() + "</td>\n")
							else:
								html.add(" <td colspan='6' style='color: #FF0000;'>NO SCANS FOUND</td>\n")
							if stamp != "0":
								html.add(" <td colspan='6' style='color: #FF0000;'>ERR <a href='/rescan?host=" + host + "'>[RESCAN]<a/></td>\n")
						if stamp == "0":
							html.add(" <td>" + inventory["hosts"][host]["status"] + " " + datetime.fromtimestamp(int(inventory["hosts"][host]["last"])).strftime("%a %d. %b %Y %H:%M:%S") + " <a href='/rescan?host=" + host + "'>[RESCAN]<a/></td>\n")
						html.add("</tr>\n")
						if searchinfo != "":
							html.add("<tr><td colspan='9' style='color: #999999;'>")
							html.add(searchinfo)
							html.add("</td></tr>\n")

	
		html.add(bs_table_end())
		html.add("<br />\n")
		html.add(bs_col_end())
		html.add(bs_row_end())
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write(bytes(html.end(), "utf8"))
		return


	def load_ovs(self):
		bridges = {}
		alltags = []
		bridge = ""
		port = ""
		ovsshow = os.popen("ovs-vsctl show").read()
		for line in ovsshow.split("\n"):
			if line.strip().startswith("Bridge"):
				bridge = line.split()[1].strip("\"")
				port = ""
				bridges[bridge] = {}
			elif line.strip().startswith("Port"):
				port = line.split()[1].strip("\"")
				bridges[bridge][port] = {}
				bridges[bridge][port]["tag"] = ""
				bridges[bridge][port]["trunks"] = []
				bridges[bridge][port]["vlan_mode"] = ilink = os.popen("ovs-vsctl --columns=vlan_mode list port " + port).read().split()[2].replace("[]", "access/trunk")
			elif line.strip().startswith("Interface"):
				interface = line.split()[1].strip("\"")
				bridges[bridge][port]["interface"] = interface
				ilink = os.popen("ovs-vsctl --columns=external_ids find interface name=" + interface).read()
				for part in ilink.split(":", 1)[1].strip().strip("{}").split(","):
					if "=" in part:
						name = part.strip().split("=")[0].strip().strip("\"")
						value = part.strip().split("=")[1].strip().strip("\"")
						bridges[bridge][port][name] = value
				if "vm-id" in bridges[bridge][port] and "iface-id" in bridges[bridge][port]:
					bridges[bridge][port]["vm-name"] = os.popen("virsh dominfo " + bridges[bridge][port]["vm-id"] + " | grep '^Name:'").read().split()[1]
			elif line.strip().startswith("type:"):
				itype = line.split()[1].strip("\"")
				bridges[bridge][port]["type"] = itype
				bridges[bridge][port]["mac"] = "-----"
				ifconfig = os.popen("ifconfig " + interface).read()
				for iline in ifconfig.split("\n"):
					if iline.strip().startswith("inet "):
						bridges[bridge][port]["ip"] = iline.strip().split()[1]
					elif iline.strip().startswith("ether "):
						bridges[bridge][port]["mac"] = iline.strip().split()[1]
			elif line.strip().startswith("tag:"):
				itag = line.split()[1].strip("\"")
				bridges[bridge][port]["tag"] = itag
			elif line.strip().startswith("trunks:"):
				trunks = line.split(":", 1)[1].strip().strip("[]").split(",")
				for trunk in trunks:
					bridges[bridge][port]["trunks"].append(trunk.strip())
		for bridge in bridges:
			for port in bridges[bridge]:
				if bridges[bridge][port]["tag"] != "":
					alltags.append(int(bridges[bridge][port]["tag"]))
				for trunk in bridges[bridge][port]["trunks"]:
					alltags.append(int(trunk))
		alltags = set(alltags)
		return bridges, alltags


	def show_ovs(self, setport = "", settag = "", settrunk = "", vmod = ""):
		html = HtmlPage("vNetwork", "OVS-Overview", "");
		html.add("<div class='modal fade' id='vlanModal' tabindex='-1' role='dialog' aria-labelledby='vlanModalLabel' aria-hidden='true'>\n")
		html.add("  <div class='modal-dialog' role='document'>\n")
		html.add("    <div class='modal-content'>\n")
		html.add("      <div class='modal-header'>\n")
		html.add("        <h5 class='modal-title' id='vlanModalLabel'>Select Tag-Mode: <input id='vlanModalTag' type='text'> -&gt; <b id='vlanModalPort'>-1</b></h5>\n")
		html.add("        <button type='button' class='close' data-dismiss='modal' aria-label='Close'><span aria-hidden='true'>&times;</span></button>\n")
		html.add("      </div>\n")
		html.add("      <div class='modal-footer'>\n")
		html.add("        <button onClick=\"location.href='?port=' + $('#vlanModalPort').html() + '&trunk=' + $('#vlanModalTag').val() + '';\" type='button' class='btn btn-primary' data-dismiss='modal'>Tagged</button>\n")
		html.add("        <button onClick=\"location.href='?port=' + $('#vlanModalPort').html() + '&tag=' + $('#vlanModalTag').val() + '';\" type='button' class='btn btn-primary' data-dismiss='modal'>Untagged</button>\n")
		html.add("      </div>\n")
		html.add("    </div>\n")
		html.add("  </div>\n")
		html.add("</div>\n")
		html.add("<div class='modal fade' id='vlanModeModal' tabindex='-1' role='dialog' aria-labelledby='vlanModeModalLabel' aria-hidden='true'>\n")
		html.add("  <div class='modal-dialog' role='document'>\n")
		html.add("    <div class='modal-content'>\n")
		html.add("      <div class='modal-header'>\n")
		html.add("        <h5 class='modal-title' id='vlanModeModalLabel'>Select VLAN-Mode: <b id='vlanModeModalPort'>-1</b></h5>\n")
		html.add("        <button type='button' class='close' data-dismiss='modal' aria-label='Close'><span aria-hidden='true'>&times;</span></button>\n")
		html.add("      </div>\n")
		html.add("      <div class='modal-footer'>\n")
		html.add("        <button onClick=\"location.href='?port=' + $('#vlanModeModalPort').html() + '&vmode=access';\" type='button' class='btn btn-primary' data-dismiss='modal'>Access</button>\n")
		html.add("        <button onClick=\"location.href='?port=' + $('#vlanModeModalPort').html() + '&vmode=dot1q-tunnel';\" type='button' class='btn btn-primary' data-dismiss='modal'>Dot1q-Tunnel</button>\n")
		html.add("        <button onClick=\"location.href='?port=' + $('#vlanModeModalPort').html() + '&vmode=native-tagged';\" type='button' class='btn btn-primary' data-dismiss='modal'>Native-Tagged</button>\n")
		html.add("        <button onClick=\"location.href='?port=' + $('#vlanModeModalPort').html() + '&vmode=native-untagged';\" type='button' class='btn btn-primary' data-dismiss='modal'>native-untagged</button>\n")
		html.add("        <button onClick=\"location.href='?port=' + $('#vlanModeModalPort').html() + '&vmode=trunk';\" type='button' class='btn btn-primary' data-dismiss='modal'>Trunk</button>\n")
		html.add("        <button onClick=\"location.href='?port=' + $('#vlanModeModalPort').html() + '&vmode=[]';\" type='button' class='btn btn-primary' data-dismiss='modal'>access/trunk</button>\n")
		html.add("      </div>\n")
		html.add("    </div>\n")
		html.add("  </div>\n")
		html.add("</div>\n")
		graph = VisGraph("visgraph", "800px")
		bridges, alltags = self.load_ovs()
		if setport != "" and (settag != "" or settrunk != "" or vmod != ""):
			if settag != "":
				for bridge in bridges:
					if setport in bridges[bridge]:
						if str(settag) == str(bridges[bridge][setport]["tag"]):
							os.system("ovs-vsctl remove port " + setport + " tag " + settag)
						else:
							os.system("ovs-vsctl set port " + setport + " tag=" + settag)
			elif settrunk != "":
				new_trunks = []
				for bridge in bridges:
					if setport in bridges[bridge]:
						if settrunk in bridges[bridge][setport]["trunks"]:
							os.system("ovs-vsctl remove port " + setport + " trunk " + settrunk)
						else:
							bridges[bridge][setport]["trunks"].append(settrunk)
							os.system("ovs-vsctl set port " + setport + " trunk=" + ",".join(bridges[bridge][setport]["trunks"]))
			elif vmod != "":
				os.system("ovs-vsctl set port " + setport + " vlan_mode=" + vmod)
			bridges, alltags = self.load_ovs()
		html.add(bs_row_begin())
		for bridge in bridges:
			html.add(bs_col_begin("12"))
			html.add(bs_card_begin("Bridge: " + bridge, "net"))
			html.add(bs_row_begin())
			html.add(bs_col_begin("12"))
			html.add("<table class='table-striped' width='100%' border='0'>\n")
			html.add("<tr>\n")
			html.add(" <th colspan='3'>Switch</th>\n")
			html.add(" <th colspan='5'>Target</th>\n")
			html.add(" <th colspan='" + str(len(alltags) + 2) + "'>VLANs</th>\n")
			html.add(" <th></th>\n")
			html.add(" </tr>\n")
			html.add("<tr>\n")
			html.add(" <th width='160px'>Port</th>\n")
			html.add(" <th width='120px'>VlanMode</th>\n")
			html.add(" <th width='70px'>Tag</th>\n")
			html.add(" <th width='90px'>Trunks</th>\n")
			html.add(" <th width='100px'>Type</th>\n")
			html.add(" <th width='120px'>Host</th>\n")
			html.add(" <th width='70px'>Iface</th>\n")
			html.add(" <th width='160px'>MAC</th>\n")
			for tag in sorted(alltags):
				html.add(" <th width='50px'>&nbsp;&nbsp;" + str(tag) + "</th>\n")
			html.add(" <th width='50px'>&nbsp;&nbsp;NEW</th>\n")
			html.add(" <th></th>\n")
			html.add(" <th></th>\n")
			html.add(" </tr>\n")
			for port in bridges[bridge]:
				html.add("<tr>\n")
				html.add(" <td width='150px'>\n")
				html.add("<img src='assets/MaterialDesignIcons/port.svg' />")
				html.add(port)
				html.add(" </td>\n")
				html.add(" <td onClick=\"$('#vlanModeModalPort').html('" + str(port) + "')\" data-toggle='modal' data-target='#vlanModeModal'>" + bridges[bridge][port]["vlan_mode"] + "</td>")
				html.add(" <td>" + bridges[bridge][port]["tag"] + "</td>")
				html.add(" <td>" + ",".join(bridges[bridge][port]["trunks"]) + "</td>")
				html.add(" <td>\n")
				if "vm-id" in bridges[bridge][port] and "iface-id" in bridges[bridge][port]:
					html.add("<img src='assets/MaterialDesignIcons/monitor.svg' />&nbsp;libvirt")
				elif "container_id" in bridges[bridge][port] and "container_iface" in bridges[bridge][port]:
					html.add("<img src='assets/MaterialDesignIcons/docker.svg' />&nbsp;docker")
				elif "type" in bridges[bridge][port] and bridges[bridge][port]["type"] == "internal":
					html.add("<img src='assets/MaterialDesignIcons/desktop-tower-monitor.svg' />&nbsp;internal")
				html.add(" </td>\n")
				if "vm-id" in bridges[bridge][port] and "iface-id" in bridges[bridge][port]:
					html.add(" <td><a href='/vhost?host=" + bridges[bridge][port]["vm-name"] + "'>" + bridges[bridge][port]["vm-name"] + "</a></td>")
					html.add(" <td></td>")
					html.add(" <td>" + bridges[bridge][port]["attached-mac"] + "</td>")
				elif "container_id" in bridges[bridge][port] and "container_iface" in bridges[bridge][port]:
					html.add(" <td><a href='/vhost?host=" + bridges[bridge][port]["container_id"] + "'>" + bridges[bridge][port]["container_id"] + "</a></td>")
					html.add(" <td>" + bridges[bridge][port]["container_iface"] + "</td>")
					html.add(" <td></td>")
				elif "type" in bridges[bridge][port] and bridges[bridge][port]["type"] == "internal":
					html.add(" <td>LOCALHOST</td>")
					html.add(" <td>" + bridges[bridge][port]["interface"] + "</td>")
					if "mac" in bridges[bridge][port]:
						html.add(" <td>" + bridges[bridge][port]["mac"] + "</td>")
					else:
						html.add(" <td></td>")
				else:
					html.add(" <td></td>")
					html.add(" <td></td>")
					html.add(" <td></td>")
				for tag in sorted(alltags):
					html.add(" <td>\n")
					if str(tag) == bridges[bridge][port]["tag"] and str(tag) in bridges[bridge][port]["trunks"]:
						html.add("<img onClick=\"$('#vlanModalTag').val('" + str(tag) + "'); $('#vlanModalPort').html('" + str(port) + "')\" data-toggle='modal' data-target='#vlanModal' src='assets/MaterialDesignIcons/vline-con3.svg' />M")
					elif str(tag) in bridges[bridge][port]["trunks"]:
						html.add("<img onClick=\"$('#vlanModalTag').val('" + str(tag) + "'); $('#vlanModalPort').html('" + str(port) + "')\" data-toggle='modal' data-target='#vlanModal' src='assets/MaterialDesignIcons/vline-con2.svg' />T")
					elif str(tag) == bridges[bridge][port]["tag"]:
						html.add("<img onClick=\"$('#vlanModalTag').val('" + str(tag) + "'); $('#vlanModalPort').html('" + str(port) + "')\" data-toggle='modal' data-target='#vlanModal' src='assets/MaterialDesignIcons/vline-con1.svg' />U")
					else:
						html.add("<img onClick=\"$('#vlanModalTag').val('" + str(tag) + "'); $('#vlanModalPort').html('" + str(port) + "')\" data-toggle='modal' data-target='#vlanModal' src='assets/MaterialDesignIcons/vline.svg' />")
					html.add(" </td>\n")

				html.add(" <td>")
				html.add("<img onClick=\"$('#vlanModalTag').val(100); $('#vlanModalPort').html('" + str(port) + "')\" data-toggle='modal' data-target='#vlanModal' src='assets/MaterialDesignIcons/vline.svg' />")
				html.add(" <td>\n")

				html.add(" <td></td>")
				html.add(" </tr>\n")
			html.add("</table>\n")
			html.add(bs_col_end())
			html.add(bs_row_end())
			html.add(bs_card_end())
			html.add(bs_col_end())
		html.add(bs_col_begin("12"))
		html.add(bs_card_begin("vCables", "net"))
		html.add(bs_row_begin())
		html.add(bs_col_begin("12"))
		for bridge in bridges:
			graph.node_add("bridge_" + bridge, bridge, "net")
			for port in bridges[bridge]:
				if "vm-id" in bridges[bridge][port] and "iface-id" in bridges[bridge][port]:
					host = bridges[bridge][port]["vm-name"]
					graph.node_add("host_" + host, host, "monitor")
					graph.edge_add("host_" + host + "_port_" + port, "host_" + host)
				elif "container_id" in bridges[bridge][port] and "container_iface" in bridges[bridge][port]:
					host = bridges[bridge][port]["container_id"]
					iface = bridges[bridge][port]["container_iface"]
					graph.node_add("host_" + host, host, "docker")
					graph.edge_add("host_" + host + "_port_" + port, "host_" + host)
				elif "type" in bridges[bridge][port] and bridges[bridge][port]["type"] == "internal":
					host = "LOCALHOST"
					graph.node_add("host_" + host, host, "desktop-tower-monitor")
					graph.edge_add("host_" + host + "_port_" + port, "host_" + host)
				tag = bridges[bridge][port]["tag"]
				trunks = ",".join(bridges[bridge][port]["trunks"])
				graph.node_add("host_" + host + "_port_" + port, port + "\\n" + tag + "\\nTrunks:" + trunks, "port")
				graph.edge_add("bridge_" + bridge, "host_" + host + "_port_" + port)
		html.add(graph.end())
		html.add(bs_col_end())
		html.add(bs_row_end())
		html.add(bs_card_end())
		html.add(bs_col_end())
		html.add(bs_row_end())
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write(bytes(html.end(), "utf8"))
		return


	def show_vhost(self, host = ""):
		html = HtmlPage("vNetwork", "vHost-Setup: " + host, "");

		hosts = {}
		hostfiles = {}
		for hostfile in glob.glob("/usr/src/testnetz/hosts/*.json"):
			with open(hostfile) as json_file:
				hostdata = json.load(json_file)
				hosts[hostdata["hostname"]] = hostdata
				hostfiles[hostdata["hostname"]] = hostfile

		html.add(bs_row_begin())

		html.add(bs_col_begin("6"))
		html.add(bs_card_begin("Host: " + hosts[host]["hostname"] + "." + hosts[host]["domainname"] + ""))
		html.add(bs_row_begin())
		html.add(bs_col_begin("6"))
		html.add("<table>")
		for option in ["hostname", "domainname", "os", "target", "memory", "vcpu", "iso", "dockerfile", "image"]:
			value = ""
			if option in hosts[host]:
				value = str(hosts[host][option])
			html.add("<tr><td>" + option.capitalize() + ": </td><td><input id='inp_" + option + "' type='text' value='" + value + "'></td></tr>")
		html.add("</table>")
		html.add("<br />")
		html.add(bs_col_end())

		html.add(bs_col_begin("6"))
		html.add("<table>")
		html.add("<tr>")
		html.add(" <td>Nameservers: </td><td><input id='inp_nameservers' type='text' value='" + ", ".join(hosts[host]["network"]["nameservers"]) + "'></td>")
		html.add("</tr>")
		html.add("<tr>")
		html.add(" <td>Default-Gateway: </td><td><input id='inp_gateway' type='text' value='" + hosts[host]["network"]["gateway"] + "'></td>")
		html.add("</tr>")
		html.add("</table>")
		html.add("<br />")
		html.add(bs_col_end())

		html.add(bs_row_end())
		html.add(bs_card_end())
		html.add(bs_col_end())

		html.add(bs_col_begin("6"))
		html.add(bs_card_begin("Guest-Info"))
		html.add(bs_row_begin())
		html.add(bs_col_begin("6"))
		status = os.popen("cd /usr/src/testnetz ; python3 init.py -i " + hostfiles[host]).read()
		for line in status.split("\n"):
			if line.startswith("State:") or "Up" in line:
				html.add("<b>" + line + "</b><br />")
			elif line.startswith("UUID") or line.startswith("OS Type") or line.startswith("CPU") or line.startswith("Used memory"):
				html.add(line + "<br />")
		html.add(bs_col_end())
		html.add(bs_row_end())
		html.add(bs_card_end())
		html.add(bs_col_end())




		for interface in hosts[host]["network"]["interfaces"]:
			html.add(bs_col_begin("6"))
			html.add(bs_card_begin("Network-Interface: " + interface))
			html.add(bs_row_begin())
			html.add(bs_col_begin("6"))
			html.add(bs_add("<b>Interface:</b>"))
			html.add(bs_table_begin())
			html.add("<tr>")
			html.add(" <td>Bridge: </td><td><input id='inp_iface_" + interface + "_bridge' type='text' value='" + hosts[host]["network"]["interfaces"][interface]["bridge"] + "'></td>")
			html.add("</tr>")
			html.add("<tr>")
			html.add(" <td>HWaddress: </td><td><input id='inp_iface_" + interface + "_hwaddr' type='text' value='" + hosts[host]["network"]["interfaces"][interface]["hwaddr"] + "'></td>")
			html.add("</tr>")
			html.add(bs_table_end())
			html.add(bs_col_end())
			html.add(bs_col_begin("6"))
			ipv4_n = 0
			for ipv4 in hosts[host]["network"]["interfaces"][interface]["ipv4"]:
				html.add(bs_add("<b>IPv4:</b>"))
				html.add(bs_table_begin())
				html.add("<tr>")
				html.add(" <td>Address: </td><td><input id='inp_iface_" + interface + "_ipv4_" + str(ipv4_n) + "_address' type='text' value='" + ipv4["address"] + "'></td>")
				html.add("</tr>")
				html.add("<tr>")
				html.add(" <td>Netmask: </td><td><input id='inp_iface_" + interface + "_ipv4_" + str(ipv4_n) + "_netmask' type='text' value='" + ipv4["netmask"] + "'></td>")
				html.add("</tr>")
				html.add(bs_table_end())
				html.add("<br />")
				ipv4_n += 1
			html.add(bs_col_end())
			html.add(bs_row_end())
			html.add(bs_card_end())
			html.add(bs_col_end())




		for disk in hosts[host]["disks"]:
			html.add(bs_col_begin("6"))
			html.add(bs_card_begin("Disk: " + disk))
			html.add(bs_row_begin())
			html.add(bs_col_begin("6"))
			html.add(bs_add("<b>Disk:</b>"))
			html.add(bs_table_begin())
			if "image" not in hosts[host]["disks"][disk]:
				hosts[host]["disks"][disk]["image"] = ""
			html.add("<tr>")
			html.add(" <td>Size: </td><td><input id='inp_disk_" + disk + "_size' type='text' value='" + hosts[host]["disks"][disk]["size"] + "'></td>")
			html.add("</tr>")
			html.add("<tr>")
			html.add(" <td>Image: </td><td><input id='inp_disk_" + disk + "_image' type='text' value='" + hosts[host]["disks"][disk]["image"] + "'></td>")
			html.add("</tr>")
			html.add(bs_table_end())
			html.add(bs_col_end())
			html.add(bs_col_begin("6"))
#			for partition in hosts[host]["disks"][disk]["partitions"]:
#				html.add(bs_add("<b>IPv4:</b>"))
#				html.add(bs_table_begin())
#				html.add("<tr>")
#				html.add(" <td>Address: </td><td>" + ipv4["address"] + "</td>")
#				html.add("</tr>")
#				html.add("<tr>")
#				html.add(" <td>Netmask: </td><td>" + ipv4["netmask"] + "</td>")
#				html.add("</tr>")
#				html.add(bs_table_end())
#				html.add("<br />")
			html.add(bs_col_end())
			html.add(bs_row_end())
			html.add(bs_card_end())
			html.add(bs_col_end())


		for user in hosts[host]["users"]:
			html.add(bs_col_begin("6"))
			html.add(bs_card_begin("User: " + user))
			html.add(bs_row_begin())
			html.add(bs_col_begin("12"))
			html.add(bs_add("<b>User:</b>"))
			html.add(bs_table_begin())
			html.add("<tr>")
			if "password" not in hosts[host]["users"][user]:
				hosts[host]["users"][user]["password"] = ""
			if "sshpubkey" not in hosts[host]["users"][user]:
				hosts[host]["users"][user]["sshpubkey"] = ""
			html.add("<tr>")
			html.add(" <td>Password: </td><td><input id='inp_user_" + user + "_password' type='text' type='text' value='" + hosts[host]["users"][user]["password"] + "'></td>")
			html.add("</tr>")
			html.add("<tr>")
			html.add(" <td>SSH-Pubkey: </td><td><input id='inp_user_" + user + "_password' type='text' value='" + hosts[host]["users"][user]["sshpubkey"] + "'></td>")
			html.add("</tr>")
			html.add("</tr>")
			html.add(bs_table_end())
			html.add(bs_col_end())
			html.add(bs_row_end())
			html.add(bs_card_end())
			html.add(bs_col_end())
		html.add(bs_row_end())



		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write(bytes(html.end(), "utf8"))
		return


	def show_inventory(self):
		html = HtmlPage("Visansible <small>(" + str(len(inventory["hosts"])) + " hosts)</small>", "Inventory-File", "");
		html.add(bs_row_begin())
		html.add(bs_col_begin("12"))
		inventorycfg = open("inventory.cfg", "r").read()
		html.add("<pre>" + inventorycfg + "</pre>\n")
		html.add(bs_col_end())
		html.add(bs_row_end())
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write(bytes(html.end(), "utf8"))
		return


	def show_chart(self, name, labels, datas, units = ["","","","","","","","",""], colors = ["#cb2121", "#830909", "#923e99", "#ae83d5", "#111111", "#050505", "#646464", "#747474", "#333333", "#444444", "#555555", "#666666", "#777777", "#888888", "#999999", "#008080", "#0000FF", "#FF0000", "#800000", "#FFFF00", "#808000", "#00FF00", "#008000", "#00FFFF", "#000080", "#FF00FF", "#800080"]):
		html = "\n"
		html += "<!--chart-->\n"
		html += "<script>\n"
		html += "	Chart.defaults.global.defaultFontFamily = '-apple-system,system-ui,BlinkMacSystemFont,\"Segoe UI\",Roboto,\"Helvetica Neue\",Arial,sans-serif';\n"
		html += "	Chart.defaults.global.defaultFontColor = '#292b2c';\n"
		html += "	var ctx = document.getElementById('" + name + "');\n"
		html += "	var myLineChart = new Chart(ctx, {\n"
		html += "		type: 'line',\n"
		html += "		data: {labels: " + str(labels).replace(" ", "") + ",\n"
		html += "		datasets: [\n"
		dn = 0
		for data in datas:
			html += "			{type: 'line', pointRadius: 0, fill: false, lineTension: 0, borderWidth: 2, label: '" + units[dn] + "', BackgroundColor: '" + colors[dn] + "', borderColor: '" + colors[dn] + "', data: " + str(data).replace(" ", "") + "},\n"
			dn += 1
		html += "		],\n"
		html += "		},\n"
		html += "		options: {\n"
		html += "			tooltips: {intersect: false, mode: 'index', callbacks: {\n"
		html += "				label: function(tooltipItem, myData) {var label = myData.datasets[tooltipItem.datasetIndex].label || ''; if (label) {label += ': ';}; label += parseFloat(tooltipItem.value).toFixed(2); return label;}\n"
		html += "			}},\n"
		html += "			scales: {xAxes: [{distribution: 'series', ticks: {source: 'data', autoSkip: true}, gridLines: {lineWidth: 0}}], yAxes: [{ticks: {suggestedMin: 0}, scaleLabel: {display: false}, gridLines: {lineWidth: 1}}]},\n"
		html += "			legend: {"
		if units[0] == "":
			html += "display: false"
		else:
			html += "display: true"
		html += "}\n"
		html += "		}\n"
		html += "	});\n"
		html += "</script>\n"
		html += "<!--/chart-->\n"
		html += "\n"
		return html


	def show_stats(self, stamp = "0"):
		colors = ["#cb2121", "#830909", "#923e99", "#ae83d5", "#111111", "#050505", "#646464", "#747474", "#333333", "#444444", "#555555", "#666666", "#777777", "#888888", "#999999", "#008080", "#0000FF", "#FF0000", "#800000", "#FFFF00", "#808000", "#00FF00", "#008000", "#00FFFF", "#000080", "#FF00FF", "#800080"]
		options = ["ansible_os_family", "ansible_architecture", "ansible_product_name", "ansible_distribution", "ansible_kernel", "ansible_processor_count", "ansible_distribution_release", "ansible_virtualization_role", "ansible_virtualization_type", "ansible_pkg_mgr"]
		stamps = []
		for host in inventory["hosts"]:
			for timestamp in inventory["hosts"][host]:
				if timestamp.isdigit() and timestamp != "0":
					stamps.append(timestamp)
		stats = {}
		for option in options:
			stats[option] = {}
		for host in inventory["hosts"]:
			hoststamp = stamp
			if stamp != "0":
				for timestamp in sorted(set(stamps)):
					if int(stamp) >= int(timestamp) and timestamp in inventory["hosts"][host]:
						hoststamp = timestamp
			if stamp == "0" or int(stamp) >= int(inventory["hosts"][host]["first"]):
				for option in options:
					if "0" in inventory["hosts"][host] and "ansible_facts" in inventory["hosts"][host][hoststamp] and option in inventory["hosts"][host][hoststamp]["ansible_facts"]:
						value = inventory["hosts"][host][hoststamp]["ansible_facts"][option];
					else:
						value = "UNKNOWN"
					if value not in stats[option]:
						stats[option][value] = 0
					stats[option][value] += 1
		if stamp == "0":
			html = HtmlPage("Visansible <small>(" + str(len(inventory["hosts"])) + " hosts)</small>", "Stats", "latest info", self.show_history(stamp));
		else:
			html = HtmlPage("Visansible <small>(" + str(len(inventory["hosts"])) + " hosts)</small>", "Stats", datetime.fromtimestamp(int(stamp)).strftime("%a %d. %b %Y %H:%M:%S"), self.show_history(stamp));
		html.add(bs_row_begin())
		for option in options:
			html.add(bs_col_begin("4"))
			html.add(bs_add("<div id='pieChart_" + option + "'></div>"))
			html.add(bs_col_end())
		html.add(bs_row_end())
		for option in options:
			html.add("\n")
			html.add("<!--chart-->\n")
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
			html.add("<!--/chart-->\n")
			html.add("\n")
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write(bytes(html.end(), "utf8"))
		return


	def do_GET(self):
		print(self.path)
		opts = {}
		opts["stamp"] = "0"
		if "?" in self.path:
			for opt in self.path.split("?")[1].split("&"):
				name = opt.split("=")[0]
				value = opt.split("=")[1]
				opts[name] = value
		if self.path.startswith("/rescan"):
			if "host" not in opts or opts["host"] == "":
				opts["host"] = "all"
			timestamp = int(time.time())
			if not os.path.exists("facts"):
				os.mkdir("facts")
			if not os.path.exists("facts/hist_" + str(timestamp)):
				os.mkdir("facts//hist_" + str(timestamp))
			command = ['ansible', '-i', 'inventory.cfg', opts["host"], '-m', 'setup', '--tree', 'facts/hist_' + str(timestamp)]
			result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			html = HtmlPage("Visansible", "Rescan", "");
			html.add("<b>command:</b>")
			html.add("<pre>")
			html.add(" ".join(command))
			html.add("</pre>")
			inventory_read(timestamp)
			errors = 0
			for host in inventory["hosts"]:
				if "0" in inventory["hosts"][host] and "msg" in inventory["hosts"][host]["0"]:
					html.add("<b>error-msg:</b>")
					html.add("<pre style='color: #FF0000;'>")
					html.add(inventory["hosts"][host]["0"]["msg"])
					html.add("</pre>")
					errors = 2
				os.system("cp -a facts/hist_" + str(timestamp) + "/" + host + " facts/" + host)
			inventory_read()
			if result.stderr.decode('utf-8') != "":
				html.add("<b>stderr:</b>")
				if "WARNING" in result.stderr.decode('utf-8'):
					html.add("<pre style='color: #999900;'>")
					if errors < 1:
						errors = 1
				else:
					html.add("<pre style='color: #FF0000;'>")
					errors = 2
				html.add(result.stderr.decode('utf-8'))
				html.add("</pre>")
			if result.stdout.decode('utf-8') != "":
				html.add("<b>stdout:</b>")
				html.add("<pre>")
				html.add(result.stdout.decode('utf-8'))
				html.add("</pre>")
			if errors <= 1:
				html.add("<script>\n")
				if opts["host"] in inventory["hosts"]:
					html.add(" setTimeout(function() {location.href = '/host?host=" + opts["host"] + "'}, 2000);\n")
				elif opts["host"] in inventory["groups"]:
					html.add(" setTimeout(function() {location.href = '/hosts?group=" + opts["host"] + "'}, 2000);\n")
				else:
					html.add(" setTimeout(function() {location.href = '/hosts'}, 2000);\n")
				html.add("</script>\n")
			self.send_response(200)
			self.send_header("Content-type", "text/html")
			self.end_headers()
			self.wfile.write(bytes(html.end(), "utf8"))
			return
		elif self.path.startswith("/hosts"):
			if "group" not in opts:
				opts["group"] = "all"
			if "search" not in opts:
				opts["search"] = ""
			self.show_hosts(opts["stamp"], opts["group"], opts["search"])
			return
		elif self.path.startswith("/stats"):
			self.show_stats(opts["stamp"])
			return
		elif self.path.startswith("/inventory"):
			self.show_inventory()
			return
		elif self.path.startswith("/network"):
			self.show_graph("network", opts["stamp"])
			return
		elif self.path.startswith("/groups"):
			self.show_graph("group", opts["stamp"])
			return
		elif self.path.startswith("/host"):
			if "host" in opts:
				self.show_hostdata(opts["host"], opts["stamp"])
			else:
				self.show_hosts()
			return
		elif self.path.startswith("/ovs"):
			if "port" not in opts:
				opts["port"] = ""
			if "tag" not in opts:
				opts["tag"] = ""
			if "trunk" not in opts:
				opts["trunk"] = ""
			if "vmode" not in opts:
				opts["vmode"] = ""
			self.show_ovs(opts["port"], opts["tag"], opts["trunk"], opts["vmode"])
			return
		elif self.path.startswith("/vhost"):
			if "host" not in opts:
				opts["host"] = ""
			self.show_vhost(opts["host"])
			return
		elif self.path.startswith("/assets/"):
			if ".." in self.path:
				self.send_response(404)
				self.send_header("Content-type", "text/plain")
				self.end_headers()
				self.wfile.write(bytes("file NO SCANS FOUND: " + self.path, "utf8"))
			else:
				filepath = self.path.split("?")[0]
				if os.path.isfile("." + filepath):
					statinfo = os.stat("." + filepath)
					size = statinfo.st_size
					self.send_response(200)
					self.send_header("Content-length", size)
					if filepath.endswith(".js"):
						self.send_header("Content-type", "application/javascript")
					elif filepath.endswith(".html"):
						self.send_header("Content-type", "text/html")
					elif filepath.endswith(".css"):
						self.send_header("Content-type", "text/css")
					elif filepath.endswith(".png"):
						self.send_header("Content-type", "image/png")
					elif filepath.endswith(".svg"):
						self.send_header("Content-type", "image/svg+xml")
					else:
						self.send_header("Content-type", "text/plain")
					self.end_headers()
					data = open("." + filepath, "rb").read()
					self.wfile.write(data)
				else:
					self.send_response(404)
					self.send_header("Content-type", "text/plain")
					self.end_headers()
					self.wfile.write(bytes("file NO SCANS FOUND: " + self.path, "utf8"))
		else:
			self.show_hosts()
		return


	def show_element(self, element, prefix = ""):
		html = ""
		if type(element) is str:
			html += prefix + str(element) + "<br />\n"
		elif type(element) is int:
			html += prefix + str(element) + "<br />\n"
		elif type(element) is list:
			for part in element:
				bs_add("<br />")
				html += self.show_element(part, prefix + "&nbsp;&nbsp;&nbsp;")
		elif type(element) is dict:
			for part in element:
				bs_add("<br />")
				html += prefix + "<b>" + part + ":</b><br />\n"
				html += self.show_element(element[part], prefix + "&nbsp;&nbsp;&nbsp;")
		return html;


	def matchmark(self, text, old, color):
		index_l = text.lower().index(old.lower())
		return text[:index_l] + "<b style='color: " + color + ";'>" + text[index_l:][:len(old)] + "</b>" + text[index_l + len(old):] 


	def search_element(self, element, search, path = "", matches = {}):
		ret = False
		if type(element) is str:
			if search.lower() in str(element).lower():
				rank = 1
				if search == str(element):
					rank += 1
				if search.lower() == str(element).lower():
					rank += 1
				if str(element).startswith(search):
					rank += 1
				if str(element).lower().startswith(search.lower()):
					rank += 1
				if search in str(element):
					rank += 1
				matches[path] = [rank, str(element)]
				ret = True
		elif type(element) is int:
			if search.lower() in str(element).lower():
				matches[path] = str(element)
				ret = True
		elif type(element) is list:
			n = 0
			for part in element:
				res, matches = self.search_element(part, search, path + "/" + str(n), matches)
				if res == True:
					ret = True
				n += 1
		elif type(element) is dict:
			for part in element:
				res, matches = self.search_element(element[part], search, path + "/" + str(part).replace("ansible_", ""), matches)
				if res == True:
					ret = True
		return ret, matches


def inventory_read(timestamp = 0):
	global inventory
	global groups
	hostslist = open("inventory.cfg", "r").read()
	group = "NONE"
	groups = {}
	inventory = {}
	inventory["groups"] = {}
	inventory["hosts"] = {}
	section = ""
	hists = sorted(glob.glob("./facts/hist_*"), reverse=True)
	misc = False
	for line in hostslist.split("\n"):
		if line.startswith("[") and ":" in line:
			group = line.strip("[]").split(":")[0]
			section = line.strip("[]").split(":")[1]
			if group not in inventory["groups"]:
				inventory["groups"][group] = {}
				inventory["groups"][group]["options"] = {}
			misc = True
		elif line.startswith("["):
			group = line.strip("[]")
			section = ""
			if group not in inventory["groups"]:
				inventory["groups"][group] = {}
				inventory["groups"][group]["options"] = {}
			misc = False
		elif misc == True and line.strip() != "":
			name = line.split("=")[0].strip()
			value = line.split("=")[1].strip()
			inventory["groups"][group]["options"][section] = {}
			inventory["groups"][group]["options"][section][name] = value
		elif misc == False and line.strip() != "":
			host = line.split(" ")[0]
			host_options = line.split(" ")[1:]
			if host not in inventory["hosts"]:
				inventory["hosts"][host] = {}
			inventory["hosts"][host]["options"] = host_options
			if "groups" not in inventory["hosts"][host]:
				inventory["hosts"][host]["groups"] = []
			if group not in inventory["hosts"][host]["groups"]:
				inventory["hosts"][host]["groups"].append(group)
			inventory["hosts"][host]["info"] = ""
			inventory["hosts"][host]["stamp"] = "0"
			inventory["hosts"][host]["last"] = "0"
			inventory["hosts"][host]["first"] = "0"
			inventory["hosts"][host]["status"] = "ERR"
			if timestamp > 0:
				if os.path.isfile("./facts/hist_" + str(timestamp) + "/" + host):
					with open("./facts/hist_" + str(timestamp) + "/" + host) as json_file:
						hostdata = json.load(json_file)
						inventory["hosts"][host]["0"] = hostdata
			else:
				for filename in hists:
					stamp = filename.split("_")[1]
					if os.path.isfile("./facts/hist_" + str(stamp) + "/" + host):
						with open("./facts/hist_" + str(stamp) + "/" + host) as json_file:
							hostdata = json.load(json_file)
							inventory["hosts"][host][str(stamp)] = hostdata
							if inventory["hosts"][host]["last"] == "0":
								inventory["hosts"][host]["last"] = str(stamp)
							inventory["hosts"][host]["first"] = str(stamp)
							if "0" not in inventory["hosts"][host]:
								if "ansible_facts" in hostdata:
									inventory["hosts"][host]["0"] = hostdata
									inventory["hosts"][host]["stamp"] = str(stamp)
									inventory["hosts"][host]["info"] += "&lt;"
							if "ansible_facts" in hostdata:
								inventory["hosts"][host]["info"] += "OK:" + datetime.fromtimestamp(int(stamp)).strftime("%H:%M:%S") + " "
							else:
								inventory["hosts"][host]["info"] += "ERR:" + datetime.fromtimestamp(int(stamp)).strftime("%H:%M:%S") + " "
				if os.path.isfile("./facts/" + host):
					with open("./facts/" + host) as json_file:
						hostdata = json.load(json_file)
						if "0" not in inventory["hosts"][host]:
							inventory["hosts"][host]["0"] = hostdata
						if "ansible_facts" in hostdata:
							inventory["hosts"][host]["status"] = "OK"


def run():
	print('starting server...')
	server_address = ('127.0.0.1', 8081)
	httpd = HTTPServer(server_address, HTTPServer_RequestHandler)
	print('running server...')
	httpd.serve_forever()


inventory_read()
#print(json.dumps(inventory, indent=4))
run()


