#!/usr/bin/python3
#
#

import os


class Spice:
    def __init__(self, host):
        self.host = host
        self.spice_port = os.popen("virsh domdisplay " + self.host + "").read().strip()

    def get_port(self):
        return self.spice_port

    def show(self):
        html = ""
        if ":" in self.spice_port:
            print(
                "websockify 1"
                + self.spice_port.split(":")[2]
                + " "
                + self.spice_port.split(":")[1].strip("/")
                + ":"
                + self.spice_port.split(":")[2]
                + " &"
            )
            os.system(
                "websockify 1"
                + self.spice_port.split(":")[2]
                + " "
                + self.spice_port.split(":")[1].strip("/")
                + ":"
                + self.spice_port.split(":")[2]
                + " &"
            )
            html = (
                """
	<div id="login">
		<input type='hidden' id='host' name='host' value='localhost'> <!-- localhost -->
		<input type='hidden' id='port' name='port' value='1"""
                + self.spice_port.split(":")[2]
                + """'>
		<input type='hidden' id='password' value=''>
		<!-- label for="show_console">Show console </label><input type="checkbox" id="show_console" value="1" -->
		<!-- button id="connectButton">Start</button -->
	</div>
	<div id="spice-area">
		<div id="spice-screen" class="spice-screen"></div>
	</div>
	<div id="message-div" class="spice-message"></div>
	<div id="debug-div">
	</div>
	<script type="module">
		window._spice_has_module_support = true;
	</script>
	<script>
		window.addEventListener("load", function() {
			if (window._spice_has_module_support) return;
			var loader = document.createElement("script");
			loader.src = "thirdparty/browser-es-module-loader/dist/" +
				"browser-es-module-loader.js";
			document.head.appendChild(loader);
		});
	</script>
	<script type="module" crossorigin="anonymous">
		import * as SpiceHtml5 from '/assets/spice-html5-master/src/main.js';
		var host = null, port = null;
		var sc;
		function spice_error(e) {
			disconnect();
		}
		function connect() {
			var host, port, password, scheme = "ws://", uri;
			host = document.getElementById("host").value;
			port = document.getElementById("port").value;
			password = document.getElementById("password").value;
			if ((!host) || (!port)) {
				console.log("must set host and port");
				return;
			}
			if (sc) {
				sc.stop();
			}
			uri = scheme + host + ":" + port;
			//document.getElementById('connectButton').innerHTML = "Stop";
			//document.getElementById('connectButton').onclick = disconnect;
			try {
				sc = new SpiceHtml5.SpiceMainConn({uri: uri, screen_id: "spice-screen", dump_id: "debug-div",
							message_id: "message-div", password: password, onerror: spice_error, onagent: agent_connected });
			}
			catch (e) {
				alert(e.toString());
				disconnect();
			}
		}
		function disconnect() {
			console.log(">> disconnect");
			if (sc) {
				sc.stop();
			}
			//document.getElementById('connectButton').innerHTML = "Start";
			//document.getElementById('connectButton').onclick = connect;
			if (window.File && window.FileReader && window.FileList && window.Blob) {
				var spice_xfer_area = document.getElementById('spice-xfer-area');
				if (spice_xfer_area != null) {
				  document.getElementById('spice-area').removeChild(spice_xfer_area);
				}
				document.getElementById('spice-area').removeEventListener('dragover', SpiceHtml5.handle_file_dragover, false);
				document.getElementById('spice-area').removeEventListener('drop', SpiceHtml5.handle_file_drop, false);
			}
			console.log("<< disconnect");
		}
		function agent_connected(sc) {
			window.addEventListener('resize', SpiceHtml5.handle_resize);
			window.spice_connection = this;
			SpiceHtml5.resize_helper(this);
			if (window.File && window.FileReader && window.FileList && window.Blob) {
				var spice_xfer_area = document.createElement("div");
				spice_xfer_area.setAttribute('id', 'spice-xfer-area');
				document.getElementById('spice-area').appendChild(spice_xfer_area);
				document.getElementById('spice-area').addEventListener('dragover', SpiceHtml5.handle_file_dragover, false);
				document.getElementById('spice-area').addEventListener('drop', SpiceHtml5.handle_file_drop, false);
			} else {
				console.log("File API is not supported");
			}
		}
		function toggle_console() {
			var checkbox = document.getElementById('show_console');
			var m = document.getElementById('message-div');
			if (checkbox.checked) {
				m.style.display = 'block';
			} else {
				m.style.display = 'none';
			}
			window.addEventListener('resize', SpiceHtml5.handle_resize);
			if (sc) {
				SpiceHtml5.resize_helper(sc);
			}
		}
		//document.getElementById('connectButton').onclick = connect;
		//document.getElementById('show_console').onchange = toggle_console;
		connect();
	</script>
		"""
            )
        return html
