#!/usr/bin/python3
#
# ansible -i inventory.cfg all -m setup --tree facts
#

import time


import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from modules.inventory import *
from modules.RenderFacts import *
import modules.spice



class HTTPServer_RequestHandler(BaseHTTPRequestHandler):

	inv = Inventory()
	inventory = inv.inventory_read()
	rf = RenderFacts(inventory)


	def write_data(self, data, contentType="text/html", response=200):
		self.send_response(response)
		self.send_header("Content-type", contentType)
		self.end_headers()
		self.wfile.write(bytes(data, "utf8"))
		return


	def show_spice(self, host):
		vmname = self.libvirt_get_name(host)
		html = HtmlPage("Visansible <small>Spice-Console</small>", "", "", "");
		if vmname != "":
			html.add(bs_row_begin())
			html.add(bs_col_begin("12"))
			html.add(bs_card_begin("Spice", "monitor"))
			Spice = spice.Spice(vmname)
			html.add(Spice.show())
			html.add(bs_card_end())
			html.add(bs_col_end())
			html.add(bs_row_end())
		else:
			html.add("<h3>ERROR: host not found in libvirt</h3>")
		return html.end()


	def do_GET(self):
		opts = {}
		opts["stamp"] = "0"
		if "?" in self.path:
			for opt in urllib.parse.unquote(self.path).split("?")[1].split("&"):
				name = opt.split("=")[0]
				value = opt.split("=")[1]
				opts[name] = value

		if self.path.startswith("/visansible"):
			self.path = "/" + self.path.split("/", 2)[2]
		if self.path == "":
			self.path = "/"

		if self.path.startswith("/rescan"):
			if "host" not in opts or opts["host"] == "":
				opts["host"] = "all"
			timestamp = int(time.time())
			if not os.path.exists("facts"):
				os.mkdir("facts")
			if not os.path.exists("facts/hist_" + str(timestamp)):
				os.mkdir("facts/hist_" + str(timestamp))
			command = ['ansible', '-i', self.rf.inventory["file"], opts["host"], '-m', 'setup', '--tree', 'facts/hist_' + str(timestamp)]
			result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			html = HtmlPage("Visansible", "Rescan", "");
			html.add("<b>command:</b>")
			html.add("<pre>")
			html.add(" ".join(command))
			html.add("</pre>")
			self.inventory = self.inv.inventory_read(timestamp)
			errors = 0
			for host in self.inventory["hosts"]:
				invHost = self.inventory["hosts"][host]
				if "0" in invHost and "msg" in invHost["0"]:
					html.add("<b>error-msg:</b>")
					html.add("<pre style='color: #FF0000;'>")
					html.add(invHost["0"]["msg"])
					html.add("</pre>")
					errors = 2
				os.system("cp -a facts/hist_" + str(timestamp) + "/" + host + " facts/" + host)
			self.inventory = self.inv.inventory_read()
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
				if opts["host"] in self.inventory["hosts"]:
					html.add(" setTimeout(function() {location.href = '/host?host=" + opts["host"] + "'}, 2000);\n")
				elif opts["host"] in self.inventory["groups"]:
					html.add(" setTimeout(function() {location.href = '/hosts?group=" + opts["host"] + "'}, 2000);\n")
				else:
					html.add(" setTimeout(function() {location.href = '/hosts'}, 2000);\n")
				html.add("</script>\n")
			self.send_response(200)
			self.send_header("Content-type", "text/html")
			self.end_headers()
			self.wfile.write(bytes(html.end(), "utf8"))
			return
		elif self.path.startswith("/mantisbt_add"):
			self.write_data(self.rf.mantisbt_issues_post(opts))
			return
		elif self.path.startswith("/hosts"):
			if "group" not in opts:
				opts["group"] = "all"
			if "search" not in opts:
				opts["search"] = ""
			self.write_data(self.rf.show_hosts(opts["stamp"], opts["group"], opts["search"]))
			return
		elif self.path.startswith("/export_csv"):
			self.write_data(self.rf.show_csv(), "text/plain")
			return
		elif self.path.startswith("/stats"):
			self.write_data(self.rf.show_stats(opts["stamp"]))
			return
		elif self.path.startswith("/inventory"):
			self.write_data(self.rf.show_inventory())
			return
		elif self.path.startswith("/export_cfg"):
			self.write_data(self.inv.build_cfg(), "text/plain")
			return
		elif self.path.startswith("/export_yaml"):
			self.write_data(self.inv.build_yaml(), "text/plain")
			return
		elif self.path.startswith("/network"):
			self.write_data(self.rf.show_graph("network", opts["stamp"]))
			return
		elif self.path.startswith("/groups"):
			self.write_data(self.rf.show_graph("group", opts["stamp"]))
			return
		elif self.path.startswith("/libvirt"):
			if "host" in opts and "action" in opts:
				self.write_data(self.rf.libvirt_action(opts["host"], opts["action"]))
			return
		elif self.path.startswith("/spice"):
			if "host" in opts:
				self.write_data(self.show_spice(opts["host"]))
			return
		elif self.path.startswith("/host"):
			if "host" in opts:
				self.write_data(self.rf.show_hostdata(opts["host"], opts["stamp"]))
			else:
				self.write_data(self.rf.show_hosts())
			return
		elif self.path.startswith("/tree"):
			self.write_data(self.rf.show_tree())

		elif self.path.startswith("/playbook"):
			self.write_data(self.rf.show_playbook())

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
			self.write_data(self.rf.show_hosts())
		return





def run():
	vasetup = {}
	vasetup["ip"] = "127.0.0.1"
	vasetup["port"] = 8081
	if os.path.isfile("setup.json"):
		with open("setup.json") as json_file:
			vasetup = json.load(json_file)
	print("starting server (http://" + vasetup["ip"] + ":" + str(vasetup["port"]) + ")...")
	server_address = (vasetup["ip"], vasetup["port"])
	httpd = HTTPServer(server_address, HTTPServer_RequestHandler)
	print('running server...')
	httpd.serve_forever()





#print(json.dumps(inventory, indent=4))
run()


