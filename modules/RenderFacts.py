import os
import io
import re
import cgi
import yaml
import time
import json
import socket
import requests
import urllib.parse
from datetime import datetime
from modules.VisGraph import *
from modules.HtmlPage import *
from modules.bs import *


def str_format(string):
    return cgi.escape(str(string)).replace("'", "")


def str_short(string, slen=100):
    string = str_format(string)
    if len(string) > slen:
        string = string[: (slen - 3)] + " ..."
    return string


def vars_replace(rvars, data):
    for n in (1, 2, 3, 4, 5, 6):
        if isinstance(data, (dict)):
            for part in data:
                ret = re.findall("\{\{(.*?)\}\}", str(data[part]))
                if len(ret) > 0:
                    for var in ret:
                        var_strippted = var.strip()
                        if var_strippted in rvars:
                            data[part] = str(data[part]).replace(
                                "{{%s}}" % (var), str(rvars[var_strippted])
                            )
        elif isinstance(data, (list, tuple)):
            new_data = []
            for part in data:
                ret = re.findall("\{\{(.*?)\}\}", str(part))
                if len(ret) > 0:
                    for var in ret:
                        var_strippted = var.strip()
                        if var_strippted in rvars:
                            new_data.append(
                                str(part).replace(
                                    "{{%s}}" % (var), str(rvars[var_strippted])
                                )
                            )
                        else:
                            new_data.append(part)
                else:
                    new_data.append(part)
            data = new_data
        else:
            data = str(data)
            ret = re.findall("\{\{(.*?)\}\}", data)
            if len(ret) > 0:
                for var in ret:
                    var_strippted = var.strip()
                    if var_strippted in rvars:
                        data = data.replace("{{%s}}" % (var), str(rvars[var_strippted]))

    return data


def defaults_load(defaultsfile, html, defaults=None):
    if defaults == None:
        defaults = {}
    if os.path.isfile(defaultsfile):
        html.add("<table class='table table-hover' width='100%'>")
        with open(defaultsfile, "r") as stream:
            new_defaults = yaml.safe_load(stream)
            for item in new_defaults:
                defaults[item] = vars_replace(defaults, new_defaults[item])
                html.add(
                    "<tr><td>"
                    + str(item)
                    + "</td><td data-toggle='tooltip' title='"
                    + str_format(defaults[item])
                    + "'>"
                    + str_short(new_defaults[item])
                    + "</td></tr>"
                )
        html.add("</table>")
    else:
        html.add("<h2>FILE NOT FOUND</h2>")
    return defaults


def task_show(tasksdir, tasks, rvars, html="", parent="", prefix=""):

    if os.path.isfile("%s/defaults/main.yml" % (tasksdir)):
        html.add(bs_col_begin("2"))
        html.add(
            bs_card_begin(
                "defaults:" + "%s/defaults/main.yml" % (tasksdir), "file", collapse=True
            )
        )
        html.add(bs_row_begin())
        rvars = defaults_load("%s/defaults/main.yml" % (tasksdir), html, rvars)
        html.add(bs_row_end())
        html.add(bs_card_end())
        html.add(bs_col_end())

    for item in tasks:
        ritems = []
        if "include" in item:
            include = item.get("include", "")

            html.add(bs_col_begin("12"))
            html.add(bs_card_begin("include:" + include, "file", collapse=True))
            html.add(bs_row_begin())

            print("%sinclude: %s" % (prefix, include))
            includefile = "%s/%s" % (tasksdir, include)
            with open(includefile, "r") as stream:
                data = yaml.safe_load(stream)
            task_show(tasksdir, data, rvars, html, parent, "%s  " % (prefix))

            html.add(bs_row_end())
            html.add(bs_card_end())
            html.add(bs_col_end())

        elif "name" in item:
            taskname = item.get("name", "")
            print("%staskname: %s" % (prefix, taskname))

            icon = "script"

            if "include_tasks" in item:
                include_tasks = item.get("include_tasks", "")

                html.add(bs_col_begin("12"))
                html.add(
                    bs_card_begin("include_tasks:" + taskname, "file", collapse=True)
                )
                html.add(bs_row_begin())

                html.add(bs_col_begin("3"))
                html.add("<table class='table table-hover' width='100%'>")
                for part in item:
                    if part != "name":
                        html.add(
                            "<tr><td>"
                            + str(part)
                            + "</td><td>"
                            + str_short(item[part])
                            + "</td></tr>"
                        )
                html.add("</table>")
                html.add(bs_col_end())

                if isinstance(include_tasks, (list)):
                    for include_task in include_tasks:
                        print("###%sinclude_task: %s" % (prefix, include_task))
                # 						includefile = "%s/%s" % (tasksdir, include_task)
                # 						with open(includefile, 'r') as stream:
                # 							data = yaml.safe_load(stream)
                # 						task_show(tasksdir, data, rvars, html, parent, "%s  " % (prefix))
                if isinstance(include_tasks, (str)):
                    print("##%sinclude_task: %s" % (prefix, include_tasks))
                    includefile = "%s/%s" % (tasksdir, include_tasks)
                    with open(includefile, "r") as stream:
                        data = yaml.safe_load(stream)
                    task_show(tasksdir, data, rvars, html, parent, "%s  " % (prefix))

                html.add(bs_row_end())
                html.add(bs_card_end())
                html.add(bs_col_end())
                continue

            if "set_fact" in item:
                set_fact = item.get("set_fact", "")
                if isinstance(set_fact, (dict)):
                    for set_factitem in set_fact:
                        rvars[set_factitem] = vars_replace(
                            rvars, str(set_fact[set_factitem])
                        )

            if "debug" in item:
                icon = "information"
                tags = item.get("debug", "")
                msg = vars_replace(rvars, str(tags["msg"]))
                print("%s  debug: %s" % (prefix, str(msg)))

            if "tags" in item:
                icon = "tag"
                tags = item.get("tags", "")
                if isinstance(tags, (list, tuple)):
                    print("%s  tags: %s" % (prefix, ", ".join(tags)))
                else:
                    print("%s  tags: %s" % (prefix, str(tags)))

            if "when" in item:
                # icon = "comment-question"
                when = item.get("when", [])
                if isinstance(when, (list, tuple)):
                    for whenitem in when:
                        print("%s  when: %s" % (prefix, str(whenitem)))
                else:
                    print("%s  when: %s" % (prefix, str(when)))

            if "notify" in item:
                # icon = "information"
                notify = item.get("notify", [])
                if isinstance(notify, (list, tuple)):
                    for notifyitem in notify:
                        print("%s  notify: %s" % (prefix, str(notifyitem)))
                else:
                    print("%s  notify: %s" % (prefix, str(notify)))

            if "with_items" in item:
                with_items = item.get("with_items", [])
                if isinstance(with_items, (list, tuple)):
                    for with_itemsitem in with_items:
                        print("%s  with_items: %s" % (prefix, str(with_itemsitem)))
                        ritems.append({"raw": vars_replace(rvars, str(with_itemsitem))})
                else:
                    print("%s  with_items: %s" % (prefix, str(with_items)))
                    ritems.append({"raw": vars_replace(rvars, str(with_items))})

            if "with_filetree" in item:
                # icon = "tree"
                with_filetree = item.get("with_filetree", [])
                if isinstance(with_filetree, (list, tuple)):
                    for with_filetreeitem in with_filetree:
                        print(
                            "%s  with_filetree#2: %s" % (prefix, str(with_filetreeitem))
                        )
                        ritems.append(
                            {"raw": vars_replace(rvars, str(with_filetreeitem))}
                        )
                else:
                    print("%s  with_filetree#1: %s" % (prefix, str(with_filetree)))
                    for r, d, f in os.walk(tasksdir + "/" + str(with_filetree)):
                        for fi in f:
                            ssrc = "%s/%s" % (r, fi)
                            spath = "%s/%s" % (
                                r.replace(tasksdir + "/" + str(with_filetree), ""),
                                fi,
                            )
                            ritems.append(
                                {
                                    "raw": vars_replace(rvars, "%s/%s" % (r, fi)),
                                    "src": ssrc.replace("//", "/"),
                                    "path": spath.lstrip("/"),
                                }
                            )

            if "with_sequence" in item:
                # icon = "format-list-numbered"
                with_sequence = item.get("with_sequence", [])
                with_sequence_options = ""
                if isinstance(with_sequence, (dict)):
                    for with_sequenceitem in with_sequence:
                        with_sequence_options += "%s=%s " % (
                            str(with_sequenceitem),
                            str(with_sequence[with_sequenceitem]),
                        )
                else:
                    with_sequence_options = str(with_sequence)

                with_sequence_options = vars_replace(rvars, with_sequence_options)
                print("%s  with_sequence: %s" % (prefix, with_sequence_options))
            # 				if with_sequence_options.startswith("count="):
            # 					num = with_sequence_options.split("=")[-1]
            # 					for n in range(0, int(num)):
            # 						ritems.append({'raw': str(n + 1)})

            if "template" in item:
                icon = "file"
                template = item.get("template", [])
                template_options = ""
                if isinstance(template, (dict)):
                    for templateitem in template:
                        template_options += "%s=%s " % (
                            str(templateitem),
                            str(template[templateitem]),
                        )
                else:
                    template_options = str(template)
                print("%s  template: %s" % (prefix, template_options))
                if len(ritems) > 0:
                    for ritem in ritems:
                        new_template_options = vars_replace(
                            {"item": ritem["raw"]}, template_options
                        )

                        if "src" in ritem:
                            new_template_options = vars_replace(
                                {"item.src": ritem["src"]}, new_template_options
                            )

                        if "path" in ritem:
                            new_template_options = vars_replace(
                                {"item.path": ritem["path"]}, new_template_options
                            )

                        new_template_options = vars_replace(rvars, new_template_options)
                        print("%s  >>>>>template: %s" % (prefix, new_template_options))
                else:
                    template_options = vars_replace(rvars, template_options)
                    print("%s  >>>>>template: %s" % (prefix, template_options))

            icons = {
                "user": "person-plus",
                "unarchive": "archive",
                "blockinfile": "pencil",
                "lineinfile": "pencil",
                "apache2_module": "web",
                "package": "package",
                "apt": "package",
                "apt_key": "package",
                "apt_repository": "package",
                "debconf": "package",
                "file": "file",
                "copy": "file-send",
                "systemd": "restart",
                "service": "restart",
                "shell": "powershell",
            }

            for part in item:
                if part in icons:
                    icon = icons[part]
                elif part.startswith("apt"):
                    icon = "package"
                elif part.startswith("deb"):
                    icon = "package"
                elif part.startswith("rpm"):
                    icon = "package"
                elif part.startswith("apache2"):
                    icon = "package"
                elif part.startswith("vmware_"):
                    icon = "virtual-reality"
                elif part.startswith("cloud"):
                    icon = "cloud"
                elif part.startswith("aws_"):
                    icon = "cloud"
                elif part.startswith("azure_"):
                    icon = "cloud"
                elif part.startswith("ec2_"):
                    icon = "cloud"
                elif part.startswith("docker_"):
                    icon = "docker"

            html.add(bs_col_begin("3"))
            html.add(bs_card_begin("task:" + taskname, icon))
            html.add("<table class='table table-hover' width='100%'>")
            for part in item:
                if part != "name":
                    html.add("<tr><td>" + str(part) + "</td><td>")
                    if isinstance(item[part], (dict)):
                        for npart in item[part]:
                            html.add(
                                "<font data-html='true' data-toggle='tooltip' title='"
                                + str_format(
                                    vars_replace(rvars, str_format(item[part][npart]))
                                )
                                + "'>"
                                + str_short(str_format(npart), 20)
                                + "="
                                + str_format(item[part][npart])
                                + "</font><br />"
                            )
                    elif isinstance(item[part], (list, tuple)):
                        for npart in item[part]:
                            html.add(
                                "<font data-html='true' data-toggle='tooltip' title='"
                                + str_format(vars_replace(rvars, str_format(npart)))
                                + "'>"
                                + str_short(str_format(npart), 30)
                                + "</font><br />"
                            )
                    else:
                        html.add(
                            "<font data-html='true' data-toggle='tooltip' title='"
                            + str_format(vars_replace(rvars, str_format(item[part])))
                            + "'>"
                            + str_short(str_format(item[part]))
                            + "</font><br />"
                        )
                    html.add("</td></tr>")
            html.add("</table>")
            html.add(bs_card_end())
            html.add(bs_col_end())


class RenderFacts:

    ipv4_ips = {}
    vasetup = {}

    color_n = 0
    colors = [
        "#008080",
        "#0000FF",
        "#FF0000",
        "#800000",
        "#FFFF00",
        "#808000",
        "#00FF00",
        "#008000",
        "#00FFFF",
        "#000080",
        "#FF00FF",
        "#800080",
    ]
    vasetup = {}
    if os.path.isfile("setup.json"):
        with open("setup.json") as json_file:
            vasetup = json.load(json_file)
    pnp4nagios = ""
    pnp4nagios_duration = 12
    livestatus = ""
    if (
        "checkmk" in vasetup
        and "enable" in vasetup["checkmk"]
        and vasetup["checkmk"]["enable"] == True
    ):
        if "baseurl" in vasetup["checkmk"]:
            pnp4nagios = vasetup["checkmk"]["baseurl"]
        if "duration" in vasetup["checkmk"]:
            pnp4nagios_duration = vasetup["checkmk"]["duration"]
        if "livestatus" in vasetup["checkmk"]:
            if (
                "ip" in vasetup["checkmk"]["livestatus"]
                and "port" in vasetup["checkmk"]["livestatus"]
            ):
                livestatus = (
                    vasetup["checkmk"]["livestatus"]["ip"],
                    vasetup["checkmk"]["livestatus"]["port"],
                )

    mantisbt = ""
    mantisbt_token = ""
    mantisbt_project = 1
    if (
        "mantisbt" in vasetup
        and "enable" in vasetup["mantisbt"]
        and vasetup["mantisbt"]["enable"] == True
    ):
        if "baseurl" in vasetup["mantisbt"]:
            mantisbt = vasetup["mantisbt"]["baseurl"]
        if "token" in vasetup["mantisbt"]:
            mantisbt_token = vasetup["mantisbt"]["token"]
        if "project" in vasetup["mantisbt"]:
            mantisbt_project = vasetup["mantisbt"]["project"]

    def __init__(self, inventory):
        self.inventory = inventory
        # print(self.inventory)

    def mantisbt_tickets(self, host=""):
        try:
            issues = json.loads(
                requests.get(
                    self.mantisbt
                    + "/api/rest/issues?project_id="
                    + str(self.mantisbt_project),
                    headers={"Authorization": self.mantisbt_token},
                ).text
            )
            for issue in issues["issues"]:
                if host == "":
                    issue["match"] = True
                else:
                    issue["match"] = False
                    issue["viewed"] = False
                    if "tags" in issue:
                        for tag in issue["tags"]:
                            if tag["name"] == "server:" + host:
                                issue["match"] = True
                            elif (
                                tag["name"]
                                == "server:"
                                + inventory["hosts"][host]["0"]["ansible_facts"][
                                    "ansible_fqdn"
                                ]
                            ):
                                issue["match"] = True
        except:
            print("ERROR: getting mantis ticket data")
            self.mantisbt = ""
            return {}
        return issues["issues"]

    def livestatus_services(self, host=""):
        lsdata = []
        try:
            columns = [
                "host_name",
                "description",
                "state",
                "plugin_output",
                "acknowledged",
            ]
            family = (
                socket.AF_INET if type(self.livestatus) == tuple else socket.AF_UNIX
            )
            sock = socket.socket(family, socket.SOCK_STREAM)
            sock.connect(self.livestatus)
            if host != "":
                get = (
                    "GET services\nFilter: host_name = "
                    + host
                    + "\nColumns: "
                    + " ".join(columns)
                    + "\nOutputFormat: json\n"
                )
            else:
                get = (
                    "GET services\nColumns: "
                    + " ".join(columns)
                    + "\nOutputFormat: json\n"
                )
            sock.sendall(get.encode("utf-8"))
            sock.shutdown(socket.SHUT_WR)
            chunk = sock.recv(1024)
            data = chunk
            while len(chunk) > 0:
                chunk = sock.recv(1024)
                data += chunk
            sock.close()
            for service in json.loads(data.decode()):
                newservice = {}
                n = 0
                for column in service:
                    newservice[columns[n]] = column
                    n += 1
                lsdata.append(newservice)
        except:
            print("ERROR: getting livestatus data")
            self.livestatus = ""
            return lsdata
        return lsdata

    def facts2rows(self, facts, options="", offset="", units="", align="left"):
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
                title = (
                    option.replace("ansible_", "")
                    .replace("_mb", "")
                    .replace("_", " ")
                    .capitalize()
                )
            elif option.endswith("_g"):
                title = (
                    option.replace("ansible_", "")
                    .replace("_g", "")
                    .replace("_", " ")
                    .capitalize()
                )
            else:
                title = option.replace("ansible_", "").replace("_", " ").capitalize()
            if type(facts) is dict and option in facts:
                value = str(facts[option])
                html += (
                    "<tr><td>" + offset + title + ": </td><td align='" + align + "'>"
                )
                if option.endswith("_mb"):
                    html += value + " MB"
                elif option.endswith("_g"):
                    html += value + " GB"
                else:
                    html += value + " " + units[un]
                html += "</td></tr>\n"
            un += 1
        return html

    def show_graph(self, mode="group", stamp="0"):
        if mode == "":
            mode = group
        links = self.show_history(stamp)
        if stamp == "0":
            html = HtmlPage(
                "Visansible <small>("
                + str(len(self.inventory["hosts"]))
                + " hosts)</small>",
                "Graph (" + mode + ")",
                "latest info",
                links,
            )
        else:
            html = HtmlPage(
                "Visansible <small>("
                + str(len(self.inventory["hosts"]))
                + " hosts)</small>",
                "Graph (" + mode + ")",
                datetime.fromtimestamp(int(stamp)).strftime("%a %d. %b %Y %H:%M:%S"),
                links,
            )

        graph = VisGraph("visgraph", self.vasetup.get("graph", {}), "800px")

        hosts = self.inventory["hosts"]

        self.color_n = 0
        n = 0
        for host in hosts:
            n += 1
            if n > 250:
                break
            invHost = hosts[host]
            if "0" in invHost and "ansible_facts" in invHost["0"]:
                invHostLatestFacts = invHost["0"]["ansible_facts"]
                if mode == "network":
                    self.show_host_graph_network_pre(
                        graph, invHostLatestFacts, "host_" + host, stamp
                    )
        n = 0
        for host in hosts:
            invHost = hosts[host]

            n += 1
            if n > 250:
                break

            if mode == "group":
                lastGroup = ""
                for group in invHost["path"].split("/"):
                    if group != "":
                        graph.node_add("group_" + group, group, "table")
                        if lastGroup != "":
                            graph.edge_add("group_" + lastGroup, "group_" + group)
                        lastGroup = group

            if stamp == "0" or int(stamp) >= int(invHost["first"]):
                if mode == "group":
                    if lastGroup != "":
                        graph.edge_add("group_" + lastGroup, "host_" + host)
                if "0" in invHost and "ansible_facts" in invHost["0"]:
                    invHostLatest = invHost["0"]
                    invHostLatestFacts = invHostLatest["ansible_facts"]
                    fqdn = invHostLatestFacts.get("ansible_fqdn", host)
                    osfamily = invHostLatestFacts.get("ansible_os_family", "")
                    distribution = invHostLatestFacts.get("ansible_distribution", "")
                    productname = invHostLatestFacts.get("ansible_product_name", "")
                    architecture = invHostLatestFacts.get("ansible_architecture", "")
                    # graph.node_add("host_" + host, host + "\\n" + fqdn + "\\n" + osfamily + "\\n" + productname + "\\n" + architecture, osicons_get(osfamily, distribution), "font: {color: '#0000FF'}")
                    graph.node_add(
                        "host_" + host,
                        host + "\\n" + osfamily,
                        osicons_get(osfamily, distribution),
                        "font: {color: '#0000FF'}",
                    )
                    if mode == "network":
                        self.show_host_graph_network(
                            graph, invHostLatestFacts, "host_" + host, stamp, True
                        )
                elif "0" in invHost and "msg" in invHostLatest:
                    graph.node_add(
                        "host_" + host,
                        host
                        + "\\n"
                        + invHostLatest["msg"]
                        .strip()
                        .replace(":", "\\n")
                        .replace("'", "'"),
                        "monitor",
                        "font: {color: '#FF0000'}",
                    )
                else:
                    if stamp == "0":
                        graph.node_add(
                            "host_" + host,
                            host + "\\nNO SCANS FOUND",
                            "monitor",
                            "font: {color: '#FF0000'}",
                        )
                    # print(json.dumps(invHost, indent=4, sort_keys=True));

        html.add(graph.end())
        return html.end()

    def show_host_graph_network_pre(self, graph, facts, parentnode, stamp="0"):
        for part in facts:
            if (
                part != "ansible_default_ipv4"
                and type(facts[part]) is dict
                and "device" in facts[part]
            ):
                device = facts[part]["device"]
                if (
                    ("active" in facts[part] and facts[part]["active"] == False)
                    or device == "lo"
                    or device == "lo0"
                ):
                    continue
                if "ipv4" in facts[part]:
                    if type(facts[part]["ipv4"]) == list:
                        for ipv4 in facts[part]["ipv4"]:
                            address = ipv4["address"]
                            self.ipv4_ips[address] = parentnode + "_ipv4_" + address
                            self.color_n = self.color_n + 1
                            if self.color_n >= len(self.colors):
                                self.color_n = 0
                    else:
                        address = facts[part]["ipv4"]["address"]
                        self.ipv4_ips[address] = parentnode + "_ipv4_" + address

    def show_host_graph_network(
        self, graph, facts, parentnode, stamp="0", simple=False
    ):
        gateway = ""
        gateway_interface = ""
        if "ansible_default_ipv4" in facts:
            if "gateway" in facts["ansible_default_ipv4"]:
                gateway_address = facts["ansible_default_ipv4"]["gateway"]
                gateway_interface = facts["ansible_default_ipv4"]["interface"]
        for part in facts:
            if (
                part != "ansible_default_ipv4"
                and type(facts[part]) is dict
                and "device" in facts[part]
            ):
                device = facts[part]["device"]
                if (
                    "active" in facts[part]
                    and facts[part]["active"] == False
                    or device == "lo"
                    or device == "lo0"
                ):
                    continue
                if "macaddress" in facts[part]:
                    macaddress = facts[part]["macaddress"]
                else:
                    macaddress = ""
                if simple == False:
                    graph.node_add(
                        parentnode + "_iface_" + device,
                        device + "\\n" + macaddress,
                        "port",
                    )
                if "ipv4" in facts[part]:
                    if type(facts[part]["ipv4"]) == list:
                        for ipv4 in facts[part]["ipv4"]:
                            address = ipv4["address"]
                            netmask = ipv4["netmask"]
                            network = ipv4["network"]
                            if address != "127.0.0.1":
                                if simple == False:
                                    ## show ipv4 ##
                                    graph.node_add(
                                        parentnode + "_ipv4_" + address,
                                        address + "\\n" + netmask,
                                        "ipv4",
                                    )
                                    graph.edge_add(
                                        parentnode + "_iface_" + device,
                                        parentnode + "_ipv4_" + address,
                                    )
                                    ## show ipv4-network ##
                                    graph.node_add("network_" + network, network, "net")
                                    graph.edge_add(
                                        parentnode + "_ipv4_" + address,
                                        "network_" + network,
                                    )
                                    ## show ipv4-gateway ##
                                    if gateway_interface == device:
                                        graph.node_add(
                                            "gateway_" + gateway_address,
                                            gateway_address,
                                            "router",
                                        )
                                        graph.edge_add(
                                            "network_" + network,
                                            "gateway_" + gateway_address,
                                        )
                                        graph.node_add(
                                            "cloud", "0.0.0.0", "weather-cloudy"
                                        )
                                        graph.edge_add(
                                            "gateway_" + gateway_address, "cloud"
                                        )
                                else:
                                    if False:
                                        ## show ipv4 ##
                                        graph.node_add(
                                            parentnode + "_ipv4_" + address,
                                            address + "\\n" + netmask,
                                            "ipv4",
                                        )
                                        graph.edge_add(
                                            parentnode, parentnode + "_ipv4_" + address
                                        )
                                        ## show ipv4-network ##
                                        graph.node_add(
                                            "network_" + network, network, "net"
                                        )
                                        ## default route ##
                                        if gateway_interface == device:
                                            if gateway_address in self.ipv4_ips:
                                                graph.edge_add(
                                                    parentnode + "_ipv4_" + address,
                                                    "network_" + network,
                                                    "color: { color: '"
                                                    + self.ipv4_ips[gateway_address]
                                                    + "'}, arrows: {to: true}, label: 'gw:."
                                                    + gateway_address.split(".")[-1]
                                                    + "'",
                                                )
                                            else:
                                                graph.edge_add(
                                                    parentnode + "_ipv4_" + address,
                                                    "network_" + network,
                                                    "color: { color: '"
                                                    + self.colors[self.color_n]
                                                    + "'}, arrows: {to: true}, label: 'gw:."
                                                    + gateway_address.split(".")[-1]
                                                    + "'",
                                                )
                                                self.color_n = self.color_n + 1
                                                if self.color_n >= len(self.colors):
                                                    self.color_n = 0
                                        else:
                                            graph.edge_add(
                                                parentnode + "_ipv4_" + address,
                                                "network_" + network,
                                            )
                                    else:
                                        graph.node_add(
                                            "network_" + network, network, "net"
                                        )
                                        graph.edge_add(parentnode, "network_" + network)
                                    ## show ipv4-gateway ##
                                    if gateway_interface == device:
                                        if gateway_address not in self.ipv4_ips:
                                            graph.node_add(
                                                "gateway_" + gateway_address,
                                                gateway_address,
                                                "router",
                                            )
                                            graph.edge_add(
                                                "network_" + network,
                                                "gateway_" + gateway_address,
                                            )
                                            graph.node_add(
                                                "cloud", "0.0.0.0", "weather-cloudy"
                                            )
                                            graph.edge_add(
                                                "gateway_" + gateway_address, "cloud"
                                            )
                                        else:
                                            graph.edge_add(
                                                "network_" + network,
                                                self.ipv4_ips[gateway_address],
                                                "color: { color: '"
                                                + self.ipv4_ips[gateway_address]
                                                + "'}, arrows: {to: true}, label: 'gw:."
                                                + gateway_address.split(".")[-1]
                                                + "'",
                                            )
                    else:
                        ipv4 = facts[part]["ipv4"]
                        address = ipv4["address"]
                        netmask = ipv4["netmask"]
                        network = ipv4["network"]
                        if address != "127.0.0.1":
                            if simple == False:
                                ## show ipv4 ##
                                graph.node_add(
                                    parentnode + "_ipv4_" + address,
                                    address + "\\n" + netmask,
                                    "ipv4",
                                )
                                graph.edge_add(
                                    parentnode + "_iface_" + device,
                                    parentnode + "_ipv4_" + address,
                                )
                                ## show ipv4-network ##
                                graph.node_add("network_" + network, network, "net")
                                graph.edge_add(
                                    parentnode + "_ipv4_" + address,
                                    "network_" + network,
                                )
                                ## show ipv4-gateway ##
                                if gateway_interface == device:
                                    graph.node_add(
                                        "gateway_" + gateway_address,
                                        gateway_address,
                                        "router",
                                    )
                                    graph.edge_add(
                                        "network_" + network,
                                        "gateway_" + gateway_address,
                                    )
                                    graph.node_add("cloud", "0.0.0.0", "weather-cloudy")
                                    graph.edge_add(
                                        "gateway_" + gateway_address, "cloud"
                                    )
                            else:
                                if False:
                                    ## show ipv4 ##
                                    graph.node_add(
                                        parentnode + "_ipv4_" + address,
                                        address + "\\n" + netmask,
                                        "ipv4",
                                    )
                                    # graph.node_add(parentnode + "_ipv4_" + address, address + "\\n" + netmask, self.pnp4nagios + "/pnp4nagios/testnetz/pnp4nagios/index.php/image?host=" + parentnode.replace("host_", "") + "&srv=Interface_1&theme=facelift&baseurl=%2Ftestnetz%2Fcheck_mk%2F&view=0&source=0&start=1576596319&end=1576610719&w=50&h=20")
                                    graph.edge_add(
                                        parentnode, parentnode + "_ipv4_" + address
                                    )
                                    ## show ipv4-network ##
                                    graph.node_add("network_" + network, network, "net")
                                    ## default route ##
                                    if gateway_interface == device:
                                        if gateway_address in self.ipv4_ips:
                                            graph.edge_add(
                                                parentnode + "_ipv4_" + address,
                                                "network_" + network,
                                                "color: { color: '"
                                                + self.ipv4_ips[gateway_address]
                                                + "'}, arrows: {to: true}, label: 'gw:."
                                                + gateway_address.split(".")[-1]
                                                + "'",
                                            )
                                        else:
                                            graph.edge_add(
                                                parentnode + "_ipv4_" + address,
                                                "network_" + network,
                                                "color: { color: '"
                                                + self.colors[self.color_n]
                                                + "'}, arrows: {to: true}, label: 'gw:."
                                                + gateway_address.split(".")[-1]
                                                + "'",
                                            )
                                            self.color_n = self.color_n + 1
                                            if self.color_n >= len(self.colors):
                                                self.color_n = 0
                                    else:
                                        graph.edge_add(
                                            parentnode + "_ipv4_" + address,
                                            "network_" + network,
                                        )
                                else:
                                    graph.node_add("network_" + network, network, "net")
                                    graph.edge_add(parentnode, "network_" + network)
                                ## show ipv4-gateway ##
                                if gateway_interface == device:
                                    if gateway_address not in self.ipv4_ips:
                                        graph.node_add(
                                            "gateway_" + gateway_address,
                                            gateway_address,
                                            "router",
                                        )
                                        graph.edge_add(
                                            "network_" + network,
                                            "gateway_" + gateway_address,
                                        )
                                        graph.node_add(
                                            "cloud", "0.0.0.0", "weather-cloudy"
                                        )
                                        graph.edge_add(
                                            "gateway_" + gateway_address, "cloud"
                                        )
                                    else:
                                        graph.edge_add(
                                            "network_" + network,
                                            self.ipv4_ips[gateway_address],
                                            "color: { color: '"
                                            + self.ipv4_ips[gateway_address]
                                            + "'}, arrows: {to: true}, label: 'gw:."
                                            + gateway_address.split(".")[-1]
                                            + "'",
                                        )
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
                                graph.node_add(
                                    parentnode + "_ipv6_" + address,
                                    address + "\\n" + prefix + "\\n" + scope,
                                    "ipv6",
                                )
                                graph.edge_add(
                                    parentnode + "_iface_" + device,
                                    parentnode + "_ipv6_" + address,
                                )
                if simple == False:
                    if (
                        "interfaces" in facts[part]
                        and len(facts[part]["interfaces"]) > 0
                    ):
                        for interface in facts[part]["interfaces"]:
                            graph.edge_add(
                                parentnode + "_iface_" + interface,
                                parentnode + "_iface_" + device,
                            )
                    else:
                        graph.edge_add(parentnode, parentnode + "_iface_" + device)
        ## Windows ##
        ips_show = False
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
                            graph.node_add(
                                parentnode + "_iface_" + device,
                                device + "\\n" + macaddress,
                                "port",
                            )
                            graph.edge_add(parentnode, parentnode + "_iface_" + device)
                        if (
                            "ipaddresses" in iface
                            and type(iface["ipaddresses"]) is list
                        ):
                            ips_show = True
                            for address in iface["ipaddresses"]:
                                if ":" not in address:
                                    graph.node_add(
                                        parentnode + "_ipv4_" + address, address, "ipv4"
                                    )
                                    graph.edge_add(
                                        parentnode + "_iface_" + device,
                                        parentnode + "_ipv4_" + address,
                                    )
                                    network = ".".join(address.split(".")[:3]) + ".0"
                                    graph.node_add("network_" + network, network, "net")
                                    graph.edge_add(
                                        parentnode + "_ipv4_" + address,
                                        "network_" + network,
                                    )
                                else:
                                    graph.node_add(
                                        parentnode + "_ipv4_" + address, address, "ipv4"
                                    )
                                    graph.edge_add(
                                        parentnode + "_iface_" + device,
                                        parentnode + "_ipv4_" + address,
                                    )
        if ips_show == False:
            if "ansible_ip_addresses" in facts:
                for address in facts["ansible_ip_addresses"]:
                    if ":" in address:
                        if simple == False:
                            graph.node_add(
                                parentnode + "_ipv6_" + address, address, "ipv6"
                            )
                            graph.edge_add(parentnode, parentnode + "_ipv6_" + address)
                    else:
                        graph.node_add(parentnode + "_ipv4_" + address, address, "ipv4")
                        graph.edge_add(parentnode, parentnode + "_ipv4_" + address)
                        network = ".".join(address.split(".")[:3]) + ".0"
                        graph.node_add("network_" + network, network, "net")
                        graph.edge_add(
                            parentnode + "_ipv4_" + address, "network_" + network
                        )

    def show_host_graph_disks(self, graph, facts, parentnode):
        test = False
        if "ansible_devices" in facts:
            if type(facts["ansible_devices"]) is dict:
                for device in facts["ansible_devices"]:
                    if type(facts["ansible_devices"][device]) is list:
                        for partition in facts["ansible_devices"][device]:
                            test = True
                    if "partitions" in facts["ansible_devices"][device]:
                        test = True
        if test == False:
            if "ansible_mounts" in facts:
                for aMount in facts["ansible_mounts"]:
                    mount = aMount["mount"]
                    graph.node_add(
                        parentnode + "_mount_" + mount,
                        mount + "\\n" + aMount["fstype"] + "\\n" + aMount["device"],
                        "folder-open",
                    )
                    if mount == "/":
                        graph.edge_add(parentnode, parentnode + "_mount_" + mount)
                    mparent = ""
                    for mount_parent in facts["ansible_mounts"]:
                        mtest = mount_parent["mount"]
                        if mtest != "/":
                            mtest = mount_parent["mount"] + "/"
                        if mtest in mount and mount != mount_parent["mount"]:
                            if len(mparent) < len(mount_parent["mount"]):
                                mparent = mount_parent["mount"]
                    if mparent != "":
                        graph.edge_add(
                            parentnode + "_mount_" + mparent,
                            parentnode + "_mount_" + mount,
                        )
            return
        vg2pv = {}
        if "ansible_lvm" in facts:
            facts_lvm = facts["ansible_lvm"]
            if "pvs" in facts_lvm:
                for pv in facts_lvm["pvs"]:
                    vg = facts_lvm["pvs"][pv]["vg"]
                    vg2pv[vg] = pv
                    graph.node_add(
                        parentnode + "_pvs_" + pv, "LVM-PV\\n" + pv, "harddisk"
                    )
                    graph.edge_add(
                        parentnode + "_partition_" + pv.replace("/dev/", ""),
                        parentnode + "_pvs_" + pv,
                    )
            if "vgs" in facts_lvm:
                for vg in facts_lvm["vgs"]:
                    graph.node_add(parentnode + "_vgs_" + vg, "LVM-VG\\n" + vg, "group")
                    if vg in vg2pv:
                        pv = vg2pv[vg]
                        graph.edge_add(
                            parentnode + "_pvs_" + pv, parentnode + "_vgs_" + vg
                        )
            if "lvs" in facts_lvm:
                for lv in facts_lvm["lvs"]:
                    # print(lv)
                    vg = facts_lvm["pvs"][pv]["vg"]
                    lv_device = "/dev/mapper/" + vg + "-" + lv
                    graph.node_add(
                        parentnode + "_lvs_" + lv, "LVM-LV\\n" + lv, "partition"
                    )
                    graph.edge_add(parentnode + "_vgs_" + vg, parentnode + "_lvs_" + lv)
                    ## show disk-mounts ##
                    if "ansible_mounts" in facts:
                        for mount in facts["ansible_mounts"]:
                            if mount["device"] == lv_device:
                                graph.node_add(
                                    parentnode + "_mount_" + mount["mount"],
                                    mount["mount"]
                                    + "\\n"
                                    + mount["fstype"]
                                    + "\\n"
                                    + mount["device"],
                                    "folder-open",
                                )
                                graph.edge_add(
                                    parentnode + "_lvs_" + lv,
                                    parentnode + "_mount_" + mount["mount"],
                                )
        for device in facts["ansible_devices"]:
            if type(facts["ansible_devices"][device]) is list:
                if device.startswith("cd"):
                    graph.node_add(
                        parentnode + "_disk_" + device, device, "disk-player"
                    )
                else:
                    graph.node_add(parentnode + "_disk_" + device, device, "harddisk")
                graph.edge_add(parentnode, parentnode + "_disk_" + device)
                for partition in facts["ansible_devices"][device]:
                    graph.node_add(
                        parentnode + "_partition_" + str(partition),
                        str(partition),
                        "partition",
                    )
                    graph.edge_add(
                        parentnode + "_disk_" + device,
                        parentnode + "_partition_" + partition,
                    )
                    ## show partition-mounts ##
                    if "ansible_mounts" in facts:
                        for mount in facts["ansible_mounts"]:
                            if mount["device"] == "/dev/" + partition:
                                graph.node_add(
                                    parentnode + "_mount_" + mount["mount"],
                                    mount["mount"]
                                    + "\\n"
                                    + mount["fstype"]
                                    + "\\n"
                                    + mount["device"],
                                    "folder-open",
                                )
                                graph.edge_add(
                                    parentnode + "_partition_" + partition,
                                    parentnode + "_mount_" + mount["mount"],
                                )
                ## show disk-mounts ##
                if "ansible_mounts" in facts:
                    for mount in facts["ansible_mounts"]:
                        if mount["device"] == "/dev/" + device:
                            graph.node_add(
                                parentnode + "_mount_" + mount["mount"],
                                mount["mount"]
                                + "\\n"
                                + mount["fstype"]
                                + "\\n"
                                + mount["device"],
                                "folder-open",
                            )
                            graph.edge_add(
                                parentnode + "_disk_" + device,
                                parentnode + "_mount_" + mount["mount"],
                            )
            if "partitions" in facts["ansible_devices"][device]:
                if not device.startswith("loops") and (
                    len(vg2pv) == 0 or not device.startswith("dm-")
                ):
                    ## show host controller ##
                    hostctrl = str(facts["ansible_devices"][device]["host"])
                    if hostctrl == "":
                        hostctrl = "software"
                    graph.node_add(
                        parentnode + "_hostctrl_" + hostctrl,
                        hostctrl.replace(":", "\\n"),
                        "scsi",
                    )
                    graph.edge_add(parentnode, parentnode + "_hostctrl_" + hostctrl)
                    ## show disk ##
                    vendor = ""
                    model = ""
                    if "vendor" in facts["ansible_devices"][device]:
                        vendor = str(facts["ansible_devices"][device]["vendor"])
                    if "model" in facts["ansible_devices"][device]:
                        model = str(facts["ansible_devices"][device]["model"])
                    size = facts["ansible_devices"][device]["size"]
                    if size != "0.00 Bytes":
                        if "model" in facts["ansible_devices"][device] and (
                            "DVD" in str(facts["ansible_devices"][device]["model"])
                            or "CD" in str(facts["ansible_devices"][device]["model"])
                        ):
                            graph.node_add(
                                parentnode + "_disk_" + device,
                                device + "\\n" + vendor + "\\n" + model + "\\n" + size,
                                "disk-player",
                            )
                        else:
                            graph.node_add(
                                parentnode + "_disk_" + device,
                                device + "\\n" + vendor + "\\n" + model + "\\n" + size,
                                "harddisk",
                            )
                        ## check if device is slave of another disk ##
                        is_slave = False
                        for device2 in facts["ansible_devices"]:
                            if (
                                "links" in facts["ansible_devices"][device2]
                                and "masters"
                                in facts["ansible_devices"][device2]["links"]
                            ):
                                for master in facts["ansible_devices"][device2][
                                    "links"
                                ]["masters"]:
                                    if device == master:
                                        graph.edge_add(
                                            parentnode + "_disk_" + device2,
                                            parentnode + "_disk_" + device,
                                        )
                                        is_slave = True
                        ## check if device is slave of another partition ##
                        if is_slave == False:
                            for device2 in facts["ansible_devices"]:
                                if "partitions" in facts["ansible_devices"][device2]:
                                    for partition2 in facts["ansible_devices"][device2][
                                        "partitions"
                                    ]:
                                        if (
                                            "links"
                                            in facts["ansible_devices"][device2][
                                                "partitions"
                                            ][partition2]
                                            and "masters"
                                            in facts["ansible_devices"][device2][
                                                "partitions"
                                            ][partition2]["links"]
                                        ):
                                            for master in facts["ansible_devices"][
                                                device2
                                            ]["partitions"][partition2]["links"][
                                                "masters"
                                            ]:
                                                if device == master:
                                                    graph.edge_add(
                                                        parentnode
                                                        + "_partition_"
                                                        + str(partition2),
                                                        parentnode + "_disk_" + device,
                                                    )
                                                    is_slave = True
                        ## link to the controller ##
                        if is_slave == False:
                            graph.edge_add(
                                parentnode + "_hostctrl_" + hostctrl,
                                parentnode + "_disk_" + device,
                            )
                        ## show partitions ##
                        for partition in facts["ansible_devices"][device]["partitions"]:
                            uuid = ""
                            if (
                                "uuid"
                                in facts["ansible_devices"][device]["partitions"][
                                    partition
                                ]
                            ):
                                uuid = facts["ansible_devices"][device]["partitions"][
                                    partition
                                ]["uuid"]
                            size = facts["ansible_devices"][device]["partitions"][
                                partition
                            ]["size"]
                            graph.node_add(
                                parentnode + "_partition_" + str(partition),
                                str(partition) + "\\n" + str(uuid) + "\\n" + str(size),
                                "partition",
                            )
                            graph.edge_add(
                                parentnode + "_disk_" + device,
                                parentnode + "_partition_" + partition,
                            )
                            if (
                                "drive_letter"
                                in facts["ansible_devices"][device]["partitions"][
                                    partition
                                ]
                                and facts["ansible_devices"][device]["partitions"][
                                    partition
                                ]["drive_letter"]
                                != None
                            ):
                                dletter = facts["ansible_devices"][device][
                                    "partitions"
                                ][partition]["drive_letter"]
                                fstype = facts["ansible_devices"][device]["partitions"][
                                    partition
                                ]["type"]
                                graph.node_add(
                                    parentnode + "_mount_" + dletter,
                                    dletter + "\\n" + fstype + "\\n" + "device",
                                    "folder-open",
                                )
                                graph.edge_add(
                                    parentnode + "_partition_" + partition,
                                    parentnode + "_mount_" + dletter,
                                )
                            ## show partition-mounts ##
                            if "ansible_mounts" in facts:
                                for mount in facts["ansible_mounts"]:
                                    if (
                                        "uuid"
                                        in facts["ansible_devices"][device][
                                            "partitions"
                                        ][partition]
                                        and facts["ansible_devices"][device][
                                            "partitions"
                                        ][partition]["uuid"]
                                        != None
                                        and facts["ansible_devices"][device][
                                            "partitions"
                                        ][partition]["uuid"]
                                        != "N/A"
                                        and mount["uuid"] != "N/A"
                                        and "uuid" in mount
                                        and mount["uuid"] != None
                                    ):
                                        if (
                                            mount["uuid"]
                                            == facts["ansible_devices"][device][
                                                "partitions"
                                            ][partition]["uuid"]
                                        ):
                                            graph.node_add(
                                                parentnode + "_mount_" + mount["mount"],
                                                mount["mount"]
                                                + "\\n"
                                                + mount["fstype"]
                                                + "\\n"
                                                + mount["device"],
                                                "folder-open",
                                            )
                                            graph.edge_add(
                                                parentnode + "_partition_" + partition,
                                                parentnode + "_mount_" + mount["mount"],
                                            )
                                    else:
                                        if mount["device"] == "/dev/" + partition:
                                            graph.node_add(
                                                parentnode + "_mount_" + mount["mount"],
                                                mount["mount"]
                                                + "\\n"
                                                + mount["fstype"]
                                                + "\\n"
                                                + mount["device"],
                                                "folder-open",
                                            )
                                            graph.edge_add(
                                                parentnode + "_partition_" + partition,
                                                parentnode + "_mount_" + mount["mount"],
                                            )
                        ## show disk-mounts ##
                        if "ansible_mounts" in facts:
                            for mount in facts["ansible_mounts"]:
                                if (
                                    "links" in facts["ansible_devices"][device]
                                    and "uuids"
                                    in facts["ansible_devices"][device]["links"]
                                ):
                                    for disk_uuid in facts["ansible_devices"][device][
                                        "links"
                                    ]["uuids"]:
                                        if mount["uuid"] == disk_uuid:
                                            graph.node_add(
                                                parentnode + "_mount_" + mount["mount"],
                                                mount["mount"]
                                                + "\\n"
                                                + mount["fstype"]
                                                + "\\n"
                                                + mount["device"],
                                                "folder-open",
                                            )
                                            graph.edge_add(
                                                parentnode + "_disk_" + device,
                                                parentnode + "_mount_" + mount["mount"],
                                            )

    def show_host_table_ifaces(self, facts):
        html = ""
        if "ansible_default_ipv4" in facts:
            if "gateway" in facts["ansible_default_ipv4"]:
                gateway_address = facts["ansible_default_ipv4"]["gateway"]
                gateway_interface = facts["ansible_default_ipv4"]["interface"]
        for part in facts:
            if (
                part != "ansible_default_ipv4"
                and type(facts[part]) is dict
                and "device" in facts[part]
            ):
                html += bs_col_begin("6")
                html += bs_card_begin(
                    "Network-Interface: " + facts[part]["device"], "port"
                )
                html += bs_row_begin()
                html += bs_col_begin("6")
                html += bs_add("<b>Interface:</b>")
                html += bs_table_begin()
                html += self.facts2rows(
                    facts[part],
                    [
                        "device",
                        "model",
                        "macaddress",
                        "mtu",
                        "promisc",
                        "type",
                        "active",
                    ],
                )
                html += bs_table_end()
                html += bs_col_end()
                html += bs_col_begin("6")
                if "ipv4" in facts[part]:
                    if type(facts[part]["ipv4"]) == list:
                        for ipv4 in facts[part]["ipv4"]:
                            fact = ipv4
                            html += bs_add("<b>IPv4:</b>")
                            html += bs_table_begin()
                            html += self.facts2rows(
                                ipv4, ["address", "netmask", "broadcast", "network"]
                            )
                            html += bs_table_end()
                            bs_add("<br />")
                    else:
                        html += bs_add("<b>IPv4:</b>")
                        html += bs_table_begin()
                        html += self.facts2rows(
                            facts[part]["ipv4"],
                            ["address", "netmask", "broadcast", "network"],
                        )
                        html += bs_table_end()
                        bs_add("<br />")
                if "ipv6" in facts[part]:
                    for ipv6 in facts[part]["ipv6"]:
                        html += bs_add("<b>IPv6:</b>")
                        html += bs_table_begin()
                        html += self.facts2rows(ipv6, ["address", "prefix", "scope"])
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
                    html += self.facts2rows(iface)
                    html += bs_table_end()
                    html += bs_col_end()
                    html += bs_col_begin("6")
                    if "ipaddresses" in iface and type(iface["ipaddresses"]) is list:
                        html += bs_add("<b>IPv4:</b>")
                        html += bs_add("<br />")
                        for address in iface["ipaddresses"]:
                            if ":" not in address:
                                html += bs_add(address)
                                html += bs_add("<br />")
                        html += bs_add("<br />")
                        html += bs_add("<b>IPv6:</b>")
                        html += bs_add("<br />")
                        for address in iface["ipaddresses"]:
                            if ":" in address:
                                html += bs_add(address)
                                html += bs_add("<br />")
                        html += bs_add("<br />")
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
            facts_lvm = facts["ansible_lvm"]
            if "vgs" in facts_lvm:
                for vg in facts_lvm["vgs"]:
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
                if "ansible_mounts" in facts:
                    html += bs_table_begin()
                    for mount in facts["ansible_mounts"]:
                        if mount["device"] == "/dev/" + device:
                            html += self.facts2rows(
                                mount,
                                [
                                    "mount",
                                    "fstype",
                                    "device",
                                    "size_available",
                                    "options",
                                    "uuid",
                                ],
                            )
                            html += bs_add("<tr><td>&nbsp;</td><td>&nbsp;</td></tr>")
                    html += bs_table_end()
                html += bs_col_end()
                ## show partitions ##
                html += bs_col_begin("6")
                for partition in facts["ansible_devices"][device]:
                    html += bs_add("<b>Partition: " + partition + "</b>")
                    if "ansible_mounts" in facts:
                        html += bs_table_begin()
                        ## show mounts ##
                        for mount in facts["ansible_mounts"]:
                            if mount["device"] == "/dev/" + partition:
                                html += self.facts2rows(
                                    mount,
                                    [
                                        "mount",
                                        "fstype",
                                        "device",
                                        "size_available",
                                        "options",
                                        "uuid",
                                    ],
                                )
                                html += bs_add(
                                    "<tr><td>&nbsp;</td><td>&nbsp;</td></tr>"
                                )
                        html += bs_table_end()
                    bs_add("<br />")
                html += bs_col_end()
                html += bs_row_end()
                html += bs_card_end()
                html += bs_col_end()
            if "partitions" in facts["ansible_devices"][device]:
                if facts["ansible_devices"][device]["size"] != "0.00 Bytes" and (
                    len(dms) == 0 or not device.startswith("dm-")
                ):
                    html += bs_col_begin("6")
                    if "model" in facts["ansible_devices"][device] and (
                        "DVD" in str(facts["ansible_devices"][device]["model"])
                        or "CD" in str(facts["ansible_devices"][device]["model"])
                    ):
                        html += bs_card_begin("Disk: " + device, "disk-player")
                    else:
                        html += bs_card_begin("Disk: " + device, "harddisk")
                    html += bs_row_begin()
                    ## show disk ##
                    html += bs_col_begin("6")
                    html += bs_add("<b>Disk:</b>")
                    html += bs_table_begin()
                    html += self.facts2rows(
                        facts["ansible_devices"][device],
                        ["host", "vendor", "model", "serial", "size"],
                    )
                    ## show disk-mounts ##
                    if "ansible_mounts" in facts:
                        for mount in facts["ansible_mounts"]:
                            if (
                                "links" in facts["ansible_devices"][device]
                                and "uuids" in facts["ansible_devices"][device]["links"]
                            ):
                                for disk_uuid in facts["ansible_devices"][device][
                                    "links"
                                ]["uuids"]:
                                    if mount["uuid"] == disk_uuid:
                                        html += self.facts2rows(
                                            mount,
                                            [
                                                "mount",
                                                "fstype",
                                                "device",
                                                "size_available",
                                                "options",
                                                "uuid",
                                            ],
                                        )
                                        html += bs_add(
                                            "<tr><td>&nbsp;</td><td>&nbsp;</td></tr>"
                                        )

                    ## check if device is slave of another disk ##
                    for device2 in facts["ansible_devices"]:
                        if (
                            "links" in facts["ansible_devices"][device2]
                            and "masters" in facts["ansible_devices"][device2]["links"]
                        ):
                            for master in facts["ansible_devices"][device2]["links"][
                                "masters"
                            ]:
                                if device == master:
                                    html += bs_add("<tr>")
                                    html += bs_add(" <td>Master: </td>")
                                    html += bs_add(" <td>" + device2 + "</td>")
                                    html += bs_add("</tr>")

                    ## check if device is slave of another partition ##
                    for device2 in facts["ansible_devices"]:
                        if "partitions" in facts["ansible_devices"][device2]:
                            for partition2 in facts["ansible_devices"][device2][
                                "partitions"
                            ]:
                                if (
                                    "links"
                                    in facts["ansible_devices"][device2]["partitions"][
                                        partition2
                                    ]
                                    and "masters"
                                    in facts["ansible_devices"][device2]["partitions"][
                                        partition2
                                    ]["links"]
                                ):
                                    for master in facts["ansible_devices"][device2][
                                        "partitions"
                                    ][partition2]["links"]["masters"]:
                                        if device == master:
                                            html += bs_add("<tr>")
                                            html += bs_add(" <td>Master: </td>")
                                            html += bs_add(
                                                " <td>" + partition2 + "</td>"
                                            )
                                            html += bs_add("</tr>")
                    ## show disk slaves ##
                    if (
                        "links" in facts["ansible_devices"][device]
                        and "masters" in facts["ansible_devices"][device]["links"]
                    ):
                        for master in facts["ansible_devices"][device]["links"][
                            "masters"
                        ]:
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
                        html += self.facts2rows(
                            facts["ansible_devices"][device]["partitions"][partition],
                            [
                                "uuid",
                                "size",
                                "start",
                                "sectors",
                                "sectorsize",
                                "drive_letter",
                            ],
                        )
                        ## show partition slaves ##
                        if (
                            "links"
                            in facts["ansible_devices"][device]["partitions"][partition]
                            and "masters"
                            in facts["ansible_devices"][device]["partitions"][
                                partition
                            ]["links"]
                        ):
                            for master in facts["ansible_devices"][device][
                                "partitions"
                            ][partition]["links"]["masters"]:
                                html += bs_add("<tr>")
                                html += bs_add(" <td>Slave-Device: </td>")
                                html += bs_add(" <td>" + master + "</td>")
                                html += bs_add("</tr>")
                        ## show mounts ##
                        if "ansible_mounts" in facts:
                            for mount in facts["ansible_mounts"]:
                                if (
                                    "uuid"
                                    in facts["ansible_devices"][device]["partitions"][
                                        partition
                                    ]
                                    and facts["ansible_devices"][device]["partitions"][
                                        partition
                                    ]["uuid"]
                                    != None
                                    and facts["ansible_devices"][device]["partitions"][
                                        partition
                                    ]["uuid"]
                                    != "N/A"
                                    and "uuid" in mount
                                    and mount["uuid"] != "N/A"
                                    and mount["uuid"] != None
                                ):
                                    if (
                                        mount["uuid"]
                                        == facts["ansible_devices"][device][
                                            "partitions"
                                        ][partition]["uuid"]
                                    ):
                                        html += self.facts2rows(
                                            mount,
                                            [
                                                "mount",
                                                "fstype",
                                                "device",
                                                "size_available",
                                                "options",
                                                "uuid",
                                            ],
                                            "&nbsp;&nbsp;&nbsp;",
                                        )
                                        html += bs_add(
                                            "<tr><td>&nbsp;</td><td>&nbsp;</td></tr>"
                                        )
                                else:
                                    if mount["device"] == "/dev/" + partition:
                                        html += self.facts2rows(
                                            mount,
                                            [
                                                "mount",
                                                "fstype",
                                                "device",
                                                "size_available",
                                                "options",
                                                "uuid",
                                            ],
                                            "&nbsp;&nbsp;&nbsp;",
                                        )
                                        html += bs_add(
                                            "<tr><td>&nbsp;</td><td>&nbsp;</td></tr>"
                                        )
                        html += bs_table_end()
                        bs_add("<br />")
                    html += bs_col_end()
                    html += bs_row_end()
                    html += bs_card_end()
                    html += bs_col_end()
        if "ansible_lvm" in facts:
            facts_lvm = facts["ansible_lvm"]
            if "vgs" in facts_lvm:
                for vg in facts_lvm["vgs"]:
                    vg_pv = facts_lvm["vgs"][vg]
                    html += bs_col_begin("6")
                    html += bs_card_begin("LVM_VG: " + vg, "harddisk")
                    html += bs_row_begin()
                    html += bs_col_begin("6")
                    html += bs_add("<b>VG:</b>")
                    html += bs_table_begin()
                    html += self.facts2rows(
                        facts_lvm["vgs"][vg], ["size_g", "free_g", "num_lvs", "num_pvs"]
                    )
                    if "pvs" in facts_lvm:
                        for pv in facts_lvm["pvs"]:
                            pv_vg = facts_lvm["pvs"][pv]["vg"]
                            if pv_vg == vg:
                                html += bs_add("<tr>")
                                html += bs_add(" <td>&nbsp;&nbsp;&nbsp;PV: </td>")
                                html += bs_add(" <td>" + pv + "</td>")
                                html += bs_add("</tr>")
                                html += self.facts2rows(
                                    facts_lvm["pvs"][pv],
                                    ["size_g", "free_g"],
                                    "&nbsp;&nbsp;&nbsp;",
                                )
                                html += bs_add(
                                    "<tr><td>&nbsp;</td><td>&nbsp;</td></tr>"
                                )
                    html += bs_table_end()
                    html += bs_col_end()
                    html += bs_col_begin("6")
                    if "lvs" in facts_lvm:
                        for lv in facts_lvm["lvs"]:
                            lv_vg = facts_lvm["lvs"][lv]["vg"]
                            if lv_vg == vg:
                                lv_device = "/dev/mapper/" + vg + "-" + lv
                                html += bs_add("<b>LV: " + lv + "</b>")
                                html += bs_table_begin()
                                html += self.facts2rows(
                                    facts_lvm["lvs"][lv], ["size_g"]
                                )
                                ## show mounts ##
                                if "ansible_mounts" in facts:
                                    for mount in facts["ansible_mounts"]:
                                        if mount["device"] == lv_device:
                                            html += self.facts2rows(
                                                mount,
                                                [
                                                    "mount",
                                                    "fstype",
                                                    "device",
                                                    "size_available",
                                                    "options",
                                                    "uuid",
                                                ],
                                                "&nbsp;&nbsp;&nbsp;",
                                            )
                                            html += bs_add(
                                                "<tr><td>&nbsp;</td><td>&nbsp;</td></tr>"
                                            )
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
        html += self.facts2rows(
            facts,
            [
                "ansible_fqdn",
                "ansible_system_vendor",
                "ansible_product_name",
                "ansible_product_serial",
                "ansible_architecture",
                "ansible_memtotal_mb",
                "ansible_virtualization_role",
                "ansible_virtualization_type",
            ],
        )
        html += bs_table_end()
        html += bs_col_end()
        html += bs_col_begin("6")
        html += bs_table_begin()
        html += self.facts2rows(
            facts,
            [
                "ansible_distribution",
                "ansible_distribution_major_version",
                "ansible_distribution_release",
                "ansible_distribution_version",
                "ansible_distribution_file_variety",
                "ansible_userspace_architecture",
                "ansible_kernel",
                "ansible_pkg_mgr",
            ],
        )
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
        html += self.facts2rows(
            facts,
            [
                "ansible_processor_count",
                "ansible_processor_cores",
                "ansible_processor_threads_per_core",
                "ansible_processor_vcpus",
            ],
            "",
            "",
            "right",
        )
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
        invHost = self.inventory["hosts"][hostname][stamp]
        html = ""
        if "ansible_memory_mb" in facts:
            html += bs_add("<canvas id='lcmemory' width='100%' height='20'></canvas>")
            stamps = []
            for host in self.inventory["hosts"]:
                for timestamp in self.inventory["hosts"][host]:
                    if timestamp.isdigit() and timestamp != "0":
                        stamps.append(timestamp)
            labels = []
            datas = []
            trange = 3600 * 12
            tsteps = 300
            laststamp = int(stamp)
            for timestamp in sorted(set(stamps)):
                if stamp == "0" or int(timestamp) <= int(stamp):
                    labels.append("")
            for section in ["nocache", "real", "swap"]:
                last = 0
                data = []
                for timestamp in sorted(set(stamps)):
                    if (
                        hostname in self.inventory["hosts"]
                        and timestamp in self.inventory["hosts"][hostname]
                    ):
                        if "ansible_facts" in invHost:
                            invHostFacts = invHost["ansible_facts"]
                            if "ansible_memory_mb" in invHostFacts:
                                if section in invHostFacts["ansible_memory_mb"]:
                                    if (
                                        "used"
                                        in invHostFacts["ansible_memory_mb"][section]
                                    ):
                                        last = int(
                                            invHostFacts["ansible_memory_mb"][section][
                                                "used"
                                            ]
                                        )
                    data.append(last)
                datas.append(data)
            html += self.show_chart(
                "lcmemory", labels, datas, ["nocache", "real", "swap"]
            )
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
                    html += self.facts2rows(
                        facts["ansible_memory_mb"][section], "", "", "MB", "right"
                    )
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
            html += self.facts2rows(
                mount,
                ["mount", "fstype", "device", "size_available", "options", "uuid"],
            )
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
        html += bs_add("<canvas id='lcmounts' width='100%' height='20'></canvas>")
        stamps = []
        for host in self.inventory["hosts"]:
            for timestamp in self.inventory["hosts"][host]:
                if timestamp.isdigit() and timestamp != "0":
                    stamps.append(timestamp)
        labels = []
        datas = []
        units = []
        trange = 3600 * 12
        tsteps = 300
        laststamp = int(stamp)
        for timestamp in sorted(set(stamps)):
            if stamp == "0" or int(timestamp) <= int(stamp):
                labels.append("")
        if "ansible_mounts" in facts:
            mount_n = 0
            for mount in facts["ansible_mounts"]:
                units.append(mount["mount"])
                last = 0
                data = []
                for timestamp in sorted(set(stamps)):
                    if (
                        hostname in self.inventory["hosts"]
                        and timestamp in self.inventory["hosts"][hostname]
                    ):
                        invHost = self.inventory["hosts"][hostname][timestamp]
                        if "ansible_facts" in invHost:
                            invHostFacts = invHost["ansible_facts"]
                            if "ansible_mounts" in invHostFacts:
                                if mount_n < len(invHostFacts["ansible_mounts"]):
                                    if (
                                        "size_available"
                                        in invHostFacts["ansible_mounts"][mount_n]
                                    ):
                                        if (
                                            int(
                                                invHostFacts["ansible_mounts"][mount_n][
                                                    "size_total"
                                                ]
                                            )
                                            > 0
                                        ):
                                            value = (
                                                int(
                                                    invHostFacts["ansible_mounts"][
                                                        mount_n
                                                    ]["size_available"]
                                                )
                                                * 100
                                                / int(
                                                    invHostFacts["ansible_mounts"][
                                                        mount_n
                                                    ]["size_total"]
                                                )
                                            )
                                        else:
                                            value = 0
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
        html += self.facts2rows(
            facts, ["ansible_hostname", "ansible_domain", "ansible_fqdn"]
        )
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
            html += self.facts2rows(
                facts["ansible_default_ipv4"], ["gateway", "interface"]
            )
        html += bs_table_end()
        html += bs_col_end()
        html += bs_row_end()
        html += bs_card_end()
        html += bs_col_end()
        return html

    def show_history(self, stamp="0", hostname=""):
        return ""
        links = ""
        links = bs_add(
            "<br /><canvas id='myAreaChart' width='100%' height='30'></canvas>"
        )
        stamps = []
        for host in self.inventory["hosts"]:
            for timestamp in self.inventory["hosts"][host]:
                if timestamp.isdigit() and timestamp != "0":
                    stamps.append(timestamp)
        labels = []
        data = []
        data2 = []
        datas = []
        trange = 3600 * 12
        tsteps = 600
        laststamp = int(stamp)
        if stamp == "0":
            laststamp = int(time.time())
        for timestamp in range(laststamp - trange, laststamp + tsteps, tsteps):
            labels.append("")
        if hostname != "":
            if self.inventory["hosts"][hostname]["first"] != "0":
                last = 0
                for timestamp in range(
                    int(self.inventory["hosts"][hostname]["first"]), laststamp
                ):
                    if str(timestamp) in self.inventory["hosts"][hostname]:
                        if (
                            "ansible_facts"
                            in self.inventory["hosts"][hostname][str(timestamp)]
                        ):
                            last = 1
                        else:
                            last = 0
                    if (
                        timestamp >= int(self.inventory["hosts"][hostname]["first"])
                        and timestamp % tsteps == 0
                    ):
                        data.append(last)
                datas.append(data)
                links += self.show_chart("myAreaChart", labels, datas)
            links += bs_table_begin()
            links += bs_add(
                "<tr><td><a href='?host="
                + hostname
                + "&stamp=0'>latest info</a></td></tr>"
            )
            for tstamp in self.inventory["hosts"][hostname]:
                if tstamp.isdigit() and tstamp != "0":
                    if "ansible_facts" in self.inventory["hosts"][hostname][tstamp]:
                        stat = "OK"
                    else:
                        stat = "ERR"
                    sstamp = ""
                    if stamp == tstamp:
                        sstamp += "&lt;"
                    links += bs_add(
                        "<tr><td><a href='?host="
                        + hostname
                        + "&stamp="
                        + tstamp
                        + "'>"
                        + datetime.fromtimestamp(int(tstamp)).strftime(
                            "%a %d. %b %Y %H:%M:%S"
                        )
                        + "</a></td><td>"
                        + stat
                        + "</td><td>"
                        + sstamp
                        + "</td></tr>"
                    )
            links += bs_table_end()
            return links
        else:
            for timestamp in range(laststamp - trange, laststamp + tsteps, tsteps):
                n = 0
                n2 = 0
                for host in self.inventory["hosts"]:
                    last = 0
                    last2 = 0
                    for hstamp in sorted(self.inventory["hosts"][host]):
                        if hstamp != "0" and hstamp.isdigit():
                            if int(timestamp) >= int(hstamp):
                                if (
                                    "ansible_facts"
                                    in self.inventory["hosts"][host][hstamp]
                                ):
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
                    links += bs_add(
                        "<tr><td><a href='?stamp="
                        + tstamp
                        + "'>"
                        + datetime.fromtimestamp(int(tstamp)).strftime(
                            "%a %d. %b %Y %H:%M:%S"
                        )
                        + "</a>&lt;</td></tr>"
                    )
                else:
                    links += bs_add(
                        "<tr><td><a href='?stamp="
                        + tstamp
                        + "'>"
                        + datetime.fromtimestamp(int(tstamp)).strftime(
                            "%a %d. %b %Y %H:%M:%S"
                        )
                        + "</a></td></tr>"
                    )
            links += bs_table_end()
            return links

    def libvirt_get_name(self, host):
        macs = []
        invHost = self.inventory["hosts"][host]
        if "libvirt" in self.vasetup and self.vasetup["libvirt"].get("enable", False):
            if "0" in invHost and "ansible_facts" in invHost["0"]:
                invHostLatestFacts = invHost["0"]["ansible_facts"]
                for part in invHostLatestFacts:
                    if (
                        part != "ansible_default_ipv4"
                        and type(invHostLatestFacts[part]) is dict
                        and "device" in invHostLatestFacts[part]
                    ):
                        if "macaddress" in invHostLatestFacts[part]:
                            macs.append(invHostLatestFacts[part]["macaddress"].lower())
            if len(macs) > 0:
                domlist = os.popen("virsh list --all 2>&1").read()
                ende = time.time()
                print("{:5.3f}s".format(ende - start))
                for line in domlist.split("\n"):
                    if " " in line and not line.strip().startswith("Id"):
                        name = line.split()[1]
                        domiflist = os.popen("virsh domiflist " + name + " 2>&1").read()
                        for ifline in domiflist.split("\n"):
                            if ":" in ifline:
                                if ifline.split()[4].lower() in macs:
                                    return name
        return ""

    def libvirt_action(self, host, action):
        vmname = self.libvirt_get_name(host)
        html = HtmlPage("Visansible <small>Spice-Console</small>", "", "", "")
        html.add('<meta http-equiv="refresh" content="1; url=/host?host=' + host + '">')
        if vmname != "":
            html.add("<h2>")
            html.add(vmname)
            html.add(" - ")
            html.add(action)
            html.add("</h2>")
            html.add("<br />")
            result = os.popen("virsh " + action + " " + vmname + " 2>&1").read()
            html.add("<b><p>" + result + "</p></b>")
        else:
            html.add("<h3>ERROR: host not found in libvirt</h3>")
        return html.end()

    def show_hostdata(self, host, stamp="0"):
        links = self.show_history(stamp, host)
        groups = " Groups: "
        for group in self.inventory["hosts"][host]["groups"]:
            groups += "<a href='hosts?group=" + group + "'>" + group + "</a> "
        groups += ", Path: " + self.inventory["hosts"][host]["path"] + " "
        if stamp == "0":
            html = HtmlPage(
                "Visansible <small>("
                + str(len(self.inventory["hosts"]))
                + " hosts)</small>",
                "Host ("
                + host
                + ") <a href='rescan?host="
                + host
                + "'>[RESCAN]</a>"
                + groups,
                "latest info",
                links,
            )
        else:
            html = HtmlPage(
                "Visansible <small>("
                + str(len(self.inventory["hosts"]))
                + " hosts)</small>",
                "Host ("
                + host
                + ") <a href='rescan?host="
                + host
                + "'>[RESCAN]</a>"
                + groups,
                datetime.fromtimestamp(int(stamp)).strftime("%a %d. %b %Y %H:%M:%S")
                + "",
                links,
            )
        if (
            stamp in self.inventory["hosts"][host]
            and "ansible_facts" in self.inventory["hosts"][host][stamp]
        ):
            invHostFacts = self.inventory["hosts"][host][stamp]["ansible_facts"]
            osfamily = invHostFacts["ansible_os_family"]
            distribution = invHostFacts["ansible_distribution"]
            icon = osicons_get(osfamily, distribution)
            ## VM-Control ##
            if "ansible_virtualization_type" in invHostFacts and (
                invHostFacts["ansible_virtualization_type"] == "kvm"
                or invHostFacts["ansible_virtualization_type"] == "xen"
            ):
                vmname = self.libvirt_get_name(host)
                if vmname != "":
                    dominfo = os.popen("virsh dominfo " + vmname + " 2>&1").read()
                    vmstate = ""
                    for line in dominfo.split("\n"):
                        if line.startswith("State:"):
                            vmstate = line.split(":", 1)[1].strip()
                    if vmstate != "":
                        html.add(bs_row_begin())
                        html.add(bs_col_begin("12"))
                        html.add(bs_card_begin("VM-Control: " + vmstate))
                        html.add(
                            "<a title='Show Screen' target='_blank' href='/spice?host="
                            + host
                            + "'><img src='assets/MaterialDesignIcons/monitor.svg'></a>&nbsp;&nbsp;&nbsp;"
                        )
                        html.add(
                            "<a title='Start VM' href='/libvirt?host="
                            + host
                            + "&action=start'><img src='assets/MaterialDesignIcons/play.svg'></a>&nbsp;&nbsp;&nbsp;"
                        )
                        if vmstate == "paused":
                            html.add(
                                "<a title='Resume VM' href='/libvirt?host="
                                + host
                                + "&action=resume'><img src='assets/MaterialDesignIcons/pause.svg'></a>&nbsp;&nbsp;&nbsp;"
                            )
                        else:
                            html.add(
                                "<a title='Suspend VM' href='/libvirt?host="
                                + host
                                + "&action=suspend'><img src='assets/MaterialDesignIcons/pause.svg'></a>&nbsp;&nbsp;&nbsp;"
                            )
                        html.add(
                            "<a title='Destroy VM (Stop)' href='/libvirt?host="
                            + host
                            + "&action=destroy'><img src='assets/MaterialDesignIcons/stop.svg'></a>&nbsp;&nbsp;&nbsp;"
                        )
                        for line in dominfo.split("\n"):
                            if ":" in line:
                                key = line.split(":", 1)[0].strip()
                                if key in [
                                    "Name",
                                    "State",
                                    "CPU(s)",
                                    "Used memory",
                                    "Autostart",
                                ]:
                                    value = line.split(":", 1)[1].strip()
                                    html.add(
                                        "<b>"
                                        + key
                                        + "</b>="
                                        + value
                                        + "&nbsp;&nbsp;&nbsp;&nbsp;"
                                    )
                        html.add(bs_card_end())
                        html.add(bs_col_end())
                        html.add(bs_row_end())
            ## System ##
            html.add(bs_row_begin())
            html.add(self.show_host_table_general(invHostFacts))
            html.add(bs_col_begin("6"))
            html.add(bs_card_begin("History", "clock"))
            html.add(bs_add("<b>Memory-Usage:</b>"))
            html.add(self.show_host_table_memory_hist(invHostFacts, stamp, host))
            html.add(bs_add("<hr />"))
            html.add(bs_add("<b>Disk-Usage:</b>"))
            html.add(self.show_host_table_mounts_hist(invHostFacts, stamp, host))
            html.add(bs_card_end())
            html.add(bs_col_end())
            html.add(bs_row_end())
            ## Tickets ##
            if self.mantisbt != "" or self.livestatus != "":
                html.add(bs_row_begin())
            if self.mantisbt != "":
                issues = self.mantisbt_tickets(host)
            if self.livestatus != "":
                lsdata = self.livestatus_services(host)
                srv_issues = {}
                if self.mantisbt != "":
                    for issue in issues:
                        if issue["match"] == True:
                            for tag in issue["tags"]:
                                if tag["name"].startswith("service:"):
                                    service = tag["name"].replace("service:", "")
                                    if not service in srv_issues:
                                        srv_issues[service] = []
                                    srv_issues[service].append(issue)

                html.add(bs_col_begin("6"))
                html.add(
                    bs_card_begin(
                        "<a target='_blank' href='"
                        + self.pnp4nagios
                        + "/check_mk/index.py?start_url=%2Ftestnetz%2Fcheck_mk%2Fview.py%3Fhost%3D"
                        + host
                        + "%26view_name%3Dhost'>Monitoring-Tickets</a>",
                        "magnify",
                    )
                )
                html.add(bs_row_begin())
                html.add("<table class='table' width='90%'>")
                html.add(
                    "<tr><th width='20px'>Status</th><th>Service</th><th>Output</th><th>Ticket</th></tr>\n"
                )
                for part in lsdata:
                    if part["description"] in srv_issues or (
                        part["state"] > 0 and part["acknowledged"] == 0
                    ):
                        html.add("<tr>\n")
                        if part["state"] == 0:
                            html.add("<td bgcolor='#abffab'>OK</td>\n")
                        elif part["state"] == 1:
                            html.add("<td bgcolor='#ffffab'>WARN</td>\n")
                        elif part["state"] == 2:
                            html.add("<td bgcolor='#ffabab'>CRIT</td>\n")
                        elif part["state"] == 3:
                            html.add("<td bgcolor='#ababab'>UNKN</td>\n")
                        else:
                            html.add("<td bgcolor='#abffff'>???</td>\n")
                        html.add(" <td>" + str(part["description"]) + "</td>\n")
                        html.add(" <td>" + str(part["plugin_output"]) + "</td>\n")
                        html.add(" <td>\n")
                        if part["description"] not in srv_issues:
                            html.add(
                                "<a href='/mantisbt_add?host="
                                + host
                                + "&service="
                                + part["description"]
                                + "&summary="
                                + part["plugin_output"]
                                + "&description="
                                + part["plugin_output"]
                                + "'>[ADD]</a>\n"
                            )
                        html.add(" </td>\n")
                        html.add("</tr>\n")
                        if part["description"] in srv_issues:
                            for issue in srv_issues[part["description"]]:
                                issue["viewed"] = True
                                html.add("<tr>\n")
                                html.add("<td></td>\n")
                                html.add(" <td colspan='3'>\n")
                                html.add(
                                    "  <a target='_blank' href='"
                                    + self.mantisbt
                                    + "/view.php?id="
                                    + str(issue["id"])
                                    + "'>ID:"
                                    + str(issue["id"])
                                    + "</a><br /> "
                                )
                                html.add(
                                    "  Priority: "
                                    + issue["priority"]["name"]
                                    + "<br />\n"
                                )
                                html.add(
                                    "  Status: " + issue["status"]["name"] + "<br />\n"
                                )
                                if "handler" in issue and "name" in issue["handler"]:
                                    html.add(
                                        "  Handler: "
                                        + issue["handler"]["name"]
                                        + "<br />\n"
                                    )
                                if "tags" in issue:
                                    html.add("  Tags: ")
                                    for tag in issue["tags"]:
                                        if tag["name"].startswith("server:"):
                                            html.add(
                                                "<a href='/host?host="
                                                + tag["name"].replace("server:", "")
                                                + "'>"
                                                + tag["name"]
                                                + "</a> "
                                            )
                                        else:
                                            html.add(tag["name"] + " ")
                                    html.add("<br />\n")
                                html.add(" </td>\n")
                                html.add("</tr>\n")
                html.add("</table>")
                html.add(bs_row_end())
                html.add(bs_card_end())
                html.add(bs_col_end())

            if self.mantisbt != "":
                html.add(bs_col_begin("6"))
                if self.livestatus != "":
                    html.add(
                        bs_card_begin(
                            "<a target='_blank' href='"
                            + self.mantisbt
                            + "'>Other-Tickets</a>",
                            "ticket",
                        )
                    )
                else:
                    html.add(
                        bs_card_begin(
                            "<a target='_blank' href='"
                            + self.mantisbt
                            + "'>Tickets</a>",
                            "ticket",
                        )
                    )
                html.add(bs_row_begin())
                html.add("<table class='table' width='90%'>")
                html.add(
                    "<tr><th width='20px'>Status</th><th>Summary</th><th>Priority</th><th>Handler</th><th>Tags</th><th>Ticket</th></tr>\n"
                )
                for issue in issues:
                    if issue["match"] == True and issue["viewed"] == False:
                        html.add("<tr>\n")
                        if issue["priority"]["name"] == "low":
                            html.add(
                                "<td bgcolor='#abffab'>"
                                + issue["priority"]["name"]
                                + "</td>\n"
                            )
                        elif issue["priority"]["name"] == "normal":
                            html.add(
                                "<td bgcolor='#ffffab'>"
                                + issue["priority"]["name"]
                                + "</td>\n"
                            )
                        elif issue["priority"]["name"] == "high":
                            html.add(
                                "<td bgcolor='#ffabab'>"
                                + issue["priority"]["name"]
                                + "</td>\n"
                            )
                        else:
                            html.add(
                                "<td bgcolor='#ababab'>"
                                + issue["priority"]["name"]
                                + "</td>\n"
                            )
                        html.add(" <td>" + issue["summary"] + "</td>\n")
                        html.add(" <td>" + issue["status"]["name"] + "</td>\n")
                        if "handler" in issue and "name" in issue["handler"]:
                            html.add(" <td>" + issue["handler"]["name"] + "</td>\n")
                        else:
                            html.add(" <td>---</td>\n")
                        html.add(" <td>")
                        if "tags" in issue:
                            for tag in issue["tags"]:
                                if tag["name"].startswith("server:"):
                                    html.add(
                                        "<a href='/host?host="
                                        + tag["name"].replace("server:", "")
                                        + "'>"
                                        + tag["name"]
                                        + "</a> "
                                    )
                                else:
                                    html.add(tag["name"] + " ")
                        html.add("</td>\n")
                        html.add(
                            " <td><a target='_blank' href='"
                            + self.mantisbt
                            + "/view.php?id="
                            + str(issue["id"])
                            + "'>ID:"
                            + str(issue["id"])
                            + "</a></td>\n"
                        )
                        html.add("</tr>\n")
                html.add("</table>")
                html.add("<hr />")
                html.add(bs_row_end())
                html.add(bs_card_end())
                html.add(bs_col_end())

            if self.mantisbt != "" or self.livestatus != "":
                html.add(bs_row_end())

            ## CheckMK-Graphs ##
            if self.pnp4nagios != "":
                end = int(time.time())
                start = end - self.pnp4nagios_duration * 3600
                html.add(bs_row_begin())
                html.add(bs_col_begin("12"))
                html.add(
                    bs_card_begin(
                        "<a target='_blank' href='"
                        + self.pnp4nagios
                        + "/check_mk/index.py?start_url=%2Ftestnetz%2Fcheck_mk%2Fview.py%3Fhost%3D"
                        + host
                        + "%26view_name%3Dhost'>CheckMK</a>",
                        "chart-line",
                    )
                )
                html.add(bs_row_begin())
                html.add(bs_col_begin("4"))
                html.add(
                    '<img width=100% src="'
                    + self.pnp4nagios
                    + "/pnp4nagios/testnetz/pnp4nagios/index.php/image?host="
                    + host
                    + "&srv=_HOST_&theme=facelift&baseurl=%2Ftestnetz%2Fcheck_mk%2F&view=0&source=0&start="
                    + str(start)
                    + "&end="
                    + str(end)
                    + '">\n'
                )
                html.add(bs_col_end())
                html.add(bs_col_begin("4"))
                html.add(
                    '<img width=100% src="'
                    + self.pnp4nagios
                    + "/pnp4nagios/testnetz/pnp4nagios/index.php/image?host="
                    + host
                    + "&srv=Check_MK&theme=facelift&baseurl=%2Ftestnetz%2Fcheck_mk%2F&view=0&source=0&start="
                    + str(start)
                    + "&end="
                    + str(end)
                    + '">\n'
                )
                html.add(bs_col_end())
                html.add(bs_col_begin("4"))
                html.add(
                    '<img width=100% src="'
                    + self.pnp4nagios
                    + "/pnp4nagios/testnetz/pnp4nagios/index.php/image?host="
                    + host
                    + "&srv=Memory&theme=facelift&baseurl=%2Ftestnetz%2Fcheck_mk%2F&view=0&source=0&start="
                    + str(start)
                    + "&end="
                    + str(end)
                    + '">\n'
                )
                html.add(bs_col_end())
                html.add(bs_row_end())
                html.add(bs_card_end())
                html.add(bs_col_end())
                html.add(bs_row_end())

            html.add(bs_row_begin())
            html.add(self.show_host_table_memory(invHostFacts, stamp, host))
            html.add(self.show_host_table_network(invHostFacts))
            html.add(bs_row_end())

            ## Network ##
            html.add(bs_row_begin())
            html.add(self.show_host_table_ifaces(invHostFacts))
            html.add(bs_row_end())
            html.add(bs_row_begin())
            html.add(bs_col_begin("12"))
            html.add(bs_card_begin("Network-Graph", "net"))
            graph = VisGraph("vis_network", self.vasetup.get("graph"))
            graph.node_add("host_" + host, host, icon)
            self.show_host_graph_network(graph, invHostFacts, "host_" + host)
            html.add(graph.end(direction="UD"))
            html.add(bs_card_end())
            html.add(bs_col_end())
            html.add(bs_row_end())

            ## Disks ##
            show = True
            if (
                "ansible_virtualization_type" in invHostFacts
                and invHostFacts["ansible_virtualization_type"] == "docker"
            ):
                show = False
            if show == True:
                html.add(bs_row_begin())
                html.add(self.show_host_table_disks(invHostFacts))
                html.add(self.show_host_table_mounts(invHostFacts, stamp, host))
                html.add(bs_col_begin("12"))
                html.add(bs_card_begin("Disks-Graph", "harddisk"))
                graph = VisGraph("vis_disks", self.vasetup.get("graph"))
                graph.node_add("host_" + host, host, icon)
                self.show_host_graph_disks(graph, invHostFacts, "host_" + host)
                html.add(graph.end(direction="UD"))
                html.add(bs_card_end())
                html.add(bs_col_end())
                html.add(bs_row_end())
        else:
            if (
                "0" in self.inventory["hosts"][host]
                and "msg" in self.inventory["hosts"][host]["0"]
            ):
                html.add(
                    "<b>" + self.inventory["hosts"][host]["0"]["msg"].strip() + "</b>\n"
                )
            else:
                html.add("<b>NO SCANS FOUND</b>\n")
        return html.end()

    def show_csv(self):
        csv = ""
        for host in self.inventory["hosts"]:
            invHost = self.inventory["hosts"][host]
            ipaddr = ""
            if (
                "0" in self.inventory["hosts"][host]
                and "ansible_facts" in self.inventory["hosts"][host]["0"]
            ):
                invHostLatest = invHost["0"]
                invHostLatestFacts = invHostLatest["ansible_facts"]
                for part in invHostLatestFacts:
                    if (
                        part != "ansible_default_ipv4"
                        and type(invHostLatestFacts[part]) is dict
                        and "device" in invHostLatestFacts[part]
                    ):
                        if "ipv4" in invHostLatestFacts[part]:
                            if type(invHostLatestFacts[part]["ipv4"]) == list:
                                for ipv4 in invHostLatestFacts[part]["ipv4"]:
                                    ipaddr = ipv4["address"]
                                    break
                            else:
                                ipaddr = invHostLatestFacts[part]["ipv4"]["address"]
                                break
            if ipaddr != "":
                csv += host + ";"
                csv += ipaddr + "\n"
            else:
                csv += host + ";"
                csv += "\n"
        return csv

    def show_tree(self):
        html = HtmlPage("Visansible")
        html.add("<pre>")
        html.add(self.build_tree())
        html.add("</pre>")
        return html.end()

    def show_playbook(self):
        html = HtmlPage("Visansible")
        html.add(bs_row_begin())

        playbook_file = "ansible-xml/xmlapi-playbook-dev.yml"
        if os.path.isfile(playbook_file):
            with open(playbook_file, "r") as stream:
                rvars = {}
                data = yaml.safe_load(stream)
                basedir = os.path.dirname(playbook_file)
                dirname = os.path.basename(basedir)
                if dirname == "":
                    dirname = "."
                if dirname == "tasks":
                    task_show(basedir, data, rvars, html, parent)
                    a = 1
                else:
                    lastid = "root"
                    for item in data:
                        if "hosts" in item:
                            print("hosts: %s" % (str(item["hosts"])))

                            rvars["inventory_hostname"] = str(item["hosts"])

                        if "vars_files" in item:
                            html.add(bs_col_begin("12"))
                            html.add(bs_card_begin("vars_files", "file", collapse=True))
                            html.add(bs_row_begin())
                            for varfile in item["vars_files"]:

                                html.add(bs_col_begin("3"))
                                html.add(bs_card_begin("vars_file:" + varfile, "file"))
                                html.add(bs_row_begin())

                                rvars = defaults_load(
                                    basedir + "/" + varfile, html, rvars
                                )

                                html.add(bs_row_end())
                                html.add(bs_card_end())
                                html.add(bs_col_end())

                            html.add(bs_row_end())
                            html.add(bs_card_end())
                            html.add(bs_col_end())

                        if "tasks" in item:
                            task_show(basedir, item["tasks"], rvars, html, parent, "  ")

                        if "roles" in item:
                            roles = item.get("roles", {})
                            for role in roles:
                                role_name = ""
                                if isinstance(role, (str)):
                                    role_name = role
                                    print("  role: %s" % (role_name))
                                else:
                                    role_name = role.get("role", "")
                                    print("  role: %s" % (role_name))
                                    for option in role:
                                        if option != "role":
                                            print(
                                                "	%s: %s" % (option, str(role[option]))
                                            )

                                html.add(bs_col_begin("12"))
                                html.add(
                                    bs_card_begin(
                                        "role:" + role_name, "group", collapse=True
                                    )
                                )
                                html.add(bs_row_begin())

                                role_dir = "%s/roles/%s" % (dirname, role_name)
                                if os.path.isdir(role_dir):
                                    role_tasks_main = "%s/roles/%s/tasks/main.yml" % (
                                        dirname,
                                        role_name,
                                    )
                                    if os.path.isfile(role_tasks_main):
                                        with open(role_tasks_main, "r") as stream:
                                            data = yaml.safe_load(stream)
                                        basedir = os.path.dirname(role_tasks_main)
                                        task_show(
                                            basedir, data, rvars, html, "", "    "
                                        )

                                html.add(bs_row_end())
                                html.add(bs_card_end())
                                html.add(bs_col_end())

                                print("")
                            print("")

        html.add(bs_row_end())

        return html.end()

    def build_tree(self, group="all", prefix=""):
        data = ""
        if group in self.inventory["groups"]:
            data += (
                prefix
                + '+-<a href="/hosts?group='
                + group
                + '"><img src="assets/MaterialDesignIcons/table.svg">'
                + group
                + "</a>\n"
            )
            # 			if len(self.inventory["groups"][group]["options"]) > 0:
            # 				data += prefix + " vars\n"
            # 				for option in self.inventory["groups"][group]["options"]:
            # 					data += prefix + "  " + option + ": " + str(self.inventory["groups"][group]["options"][option]) + "\n"
            if "children" in self.inventory["groups"][group]:
                hosts = []
                for host in self.inventory["hosts"]:
                    if self.inventory["hosts"][host]["path"].endswith("/" + group):
                        hosts.append(host)
                if len(hosts) > 0:
                    for host in hosts:

                        icon = "monitor"
                        invHost = self.inventory["hosts"][host]
                        if "0" in invHost and "ansible_facts" in invHost["0"]:
                            invHostLatest = invHost["0"]
                            invHostLatestFacts = invHostLatest["ansible_facts"]
                            osfamily = invHostLatestFacts.get("ansible_os_family", "")
                            distribution = invHostLatestFacts.get(
                                "ansible_distribution", ""
                            )
                            icon = osicons_get(osfamily, distribution)
                        data += (
                            prefix
                            + "|  "
                            + '+-<a href="/host?host='
                            + host
                            + '"><img src="assets/MaterialDesignIcons/'
                            + icon
                            + '.svg">'
                            + host
                            + "</a>\n"
                        )
                # 						for option in self.inventory["hosts"][host]["options"]:
                # 							data += prefix + "    " + option + ": " + str(self.inventory["hosts"][host]["options"][option]) + "\n"
                if len(self.inventory["groups"][group]["children"]) > 0:
                    for children in self.inventory["groups"][group]["children"]:
                        if self.inventory["groups"][children]["path"].endswith(
                            "/" + group
                        ):
                            data += self.build_tree(children, prefix + "|  ")
        return data

    def show_hosts(self, stamp="0", sgroup="all", search=""):
        if search != "":
            search = search.replace("%20", " ")
        options = [
            "ansible_fqdn",
            "ansible_distribution",
            "ansible_architecture",
            "ansible_product_name",
            "ansible_product_serial",
        ]
        if stamp == "0":
            html = HtmlPage(
                "Visansible <small>("
                + str(len(self.inventory["hosts"]))
                + " hosts)</small>",
                "Hosts (" + sgroup + ")",
                "latest info",
                self.show_history(stamp),
            )
        else:
            html = HtmlPage(
                "Visansible <small>("
                + str(len(self.inventory["hosts"]))
                + " hosts)</small>",
                "Hosts (" + sgroup + ")",
                datetime.fromtimestamp(int(stamp)).strftime("%a %d. %b %Y %H:%M:%S"),
                self.show_history(stamp),
            )
        stamps = []
        if self.livestatus != "":
            lsdata = self.livestatus_services()
        if self.mantisbt != "":
            issues = self.mantisbt_tickets()
        html.add("\n")
        html.add(
            bs_add("<input id='search' type='text' name='search' value='' /><br />")
        )
        html.add("<script>\n")
        html.add("document.getElementById('search').onkeypress = function(event){\n")
        html.add(" if (event.keyCode == 13 || event.which == 13){\n")
        html.add(
            "  location.href = '/hosts?search=' + document.getElementById('search').value;\n"
        )
        html.add(" }\n")
        html.add("};\n")
        html.add("$('#search').focus();\n")
        html.add("$('#search').val('" + search + "');\n")
        html.add("$('#search').focus();\n")
        html.add("</script>\n")
        html.add("\n")
        for host in self.inventory["hosts"]:
            for timestamp in self.inventory["hosts"][host]:
                if timestamp.isdigit() and timestamp != "0":
                    stamps.append(timestamp)
        html.add(bs_row_begin())
        html.add(bs_col_begin("12"))
        html.add(bs_add("<table class='table table-hover' width='90%'>"))
        if search != "":
            html.add("<tr>\n")
            if self.pnp4nagios != "":
                html.add(" <th>Graph</th>\n")
            html.add(" <th>Stamp</th>\n")
            html.add(" <th>Host</th>\n")
            for option in options:
                title = option.replace("ansible_", "").capitalize()
                html.add(" <th>" + title + "</th>\n")
            # html.add(" <th width='10%'>Options</th>\n")
            html.add(" <th width='10%'>Status</th>\n")
            if self.livestatus != "":
                html.add(" <th>Problems</th>\n")
                lsdata = self.livestatus_services()
            if self.mantisbt != "":
                html.add(" <th>Tickets</th>\n")
                issues = self.mantisbt_tickets()
            html.add("</tr>\n")
        for group in self.inventory["groups"]:
            if sgroup == "all" or sgroup == group:
                if search == "":
                    if sgroup == group:
                        html.add(
                            "<tr onClick=\"location.href = 'hosts?group=all';\">\n"
                        )
                    else:
                        html.add(
                            "<tr onClick=\"location.href = 'hosts?group="
                            + group
                            + "';\">\n"
                        )
                    colspan = 3
                    if self.pnp4nagios != "":
                        colspan += 1
                    if self.livestatus != "":
                        colspan += 1
                    if self.mantisbt != "":
                        colspan += 1
                    html.add(" <td colspan='" + str(len(options) + colspan) + "'>\n")
                    html.add("  <h2>Group: " + group + " </h2>\n")
                    html.add("  <a href='rescan?host=" + group + "'>[RESCAN]<a/>\n")

                    if self.inventory["groups"][group]["path"] != "":
                        html.add(" Path: ")
                        for part in self.inventory["groups"][group]["path"].split("/"):
                            if part != "":
                                html.add(
                                    '/<a href="hosts?group='
                                    + part
                                    + '">'
                                    + part
                                    + "</a>"
                                )

                    if len(self.inventory["groups"][group]["children"]) > 0:
                        html.add(" Children: ")
                        for children in self.inventory["groups"][group]["children"]:
                            html.add(
                                '<a href="hosts?group='
                                + children
                                + '">'
                                + children
                                + "</a> "
                            )

                    for section in self.inventory["groups"][group]["options"]:
                        html.add(" Vars: ")
                        if (
                            type(self.inventory["groups"][group]["options"][section])
                            == dict
                        ):
                            for var in self.inventory["groups"][group]["options"][
                                section
                            ]:
                                html.add(
                                    "<small>"
                                    + section
                                    + ":"
                                    + var
                                    + "="
                                    + self.inventory["groups"][group]["options"][
                                        section
                                    ][var]
                                    + " </small>"
                                )
                        elif (
                            type(self.inventory["groups"][group]["options"][section])
                            == str
                        ):
                            html.add(
                                "<small>"
                                + section
                                + ":"
                                + self.inventory["groups"][group]["options"][section]
                                + " </small>"
                            )
                        else:
                            for var in self.inventory["groups"][group]["options"][
                                section
                            ]:
                                html.add("<small>" + section + ":" + var + " </small>")

                    html.add(" </td>\n")
                    html.add("</tr>\n")
                    html.add("<tr>\n")

                    if self.pnp4nagios != "":
                        html.add(" <th>Graph</th>\n")

                    html.add(" <th>Stamp</th>\n")
                    html.add(" <th>Host</th>\n")
                    for option in options:
                        title = option.replace("ansible_", "").capitalize()
                        html.add(" <th>" + title + "</th>\n")
                    # html.add(" <th width='10%'>Options</th>\n")
                    html.add(" <th width='10%'>Status</th>\n")

                    if self.livestatus != "":
                        html.add(" <th>Problems</th>\n")
                        lsdata = self.livestatus_services()

                    if self.mantisbt != "":
                        html.add(" <th>Tickets</th>\n")
                        issues = self.mantisbt_tickets()

                    html.add("</tr>\n")
                for host in self.inventory["hosts"]:
                    invHost = self.inventory["hosts"][host]
                    hoststamp = "0"
                    searchinfo = ""

                    if sgroup == "all":
                        if group != invHost["maingroup"]:
                            continue
                    else:
                        if group not in invHost["groups"]:
                            continue

                    if search != "":
                        match = False
                        if "0" in invHost and "ansible_facts" in invHost["0"]:
                            invHostLatest = invHost["0"]
                            invHostLatestFacts = invHostLatest["ansible_facts"]
                            facts = invHostLatestFacts
                            match = True
                            for psearch in search.split(" "):
                                matches = {}
                                res, matches = self.search_element(
                                    facts, psearch, "", matches
                                )
                                if res == False:
                                    if psearch.lower() in host.lower():
                                        rank = 5
                                        match = True
                                        searchinfo += (
                                            psearch
                                            + ":(host("
                                            + str(rank)
                                            + ")="
                                            + self.matchmark(
                                                host.lower(), psearch, "#FFABAB"
                                            )
                                            + ") "
                                            + str(rank)
                                            + "<br />"
                                        )
                                    else:
                                        match = False
                                else:
                                    rank = 0
                                    rank2 = 0
                                    searchinfo += psearch + ":("
                                    for path in matches:
                                        searchinfo += (
                                            path.lstrip("/")
                                            + "("
                                            + str(matches[path][0])
                                            + ")="
                                            + self.matchmark(
                                                matches[path][1], psearch, "#FFABAB"
                                            )
                                            + ", "
                                        )
                                        if rank < matches[path][0]:
                                            rank = matches[path][0]
                                        rank2 += 1
                                    searchinfo += ") " + str(rank + rank2) + " <br />"
                        if match == False:
                            continue
                    if stamp != "0":
                        for timestamp in sorted(set(stamps)):
                            if int(stamp) >= int(timestamp) and timestamp in invHost:
                                hoststamp = timestamp
                    if stamp == "0" or int(stamp) >= int(invHost["first"]):
                        html.add(
                            "<tr onClick=\"location.href = 'host?host="
                            + host
                            + "';\">\n"
                        )
                        if self.pnp4nagios != "":
                            end = int(time.time())
                            start = end - self.pnp4nagios_duration * 3600
                            html.add(
                                ' <td><img src="'
                                + self.pnp4nagios
                                + "/pnp4nagios/testnetz/pnp4nagios/index.php/image?host="
                                + host
                                + "&srv=Check_MK&theme=facelift&baseurl=%2Ftestnetz%2Fcheck_mk%2F&view=0&source=0&start="
                                + str(start)
                                + "&end="
                                + str(end)
                                + '&w=100&h=40"></td>\n'
                            )
                        if stamp != "0":
                            html.add(
                                " <td>"
                                + datetime.fromtimestamp(int(hoststamp)).strftime(
                                    "%a %d. %b %Y %H:%M:%S"
                                )
                                + "</td>\n"
                            )
                        else:
                            html.add(
                                " <td>"
                                + datetime.fromtimestamp(
                                    int(invHost["stamp"])
                                ).strftime("%a %d. %b %Y %H:%M:%S")
                                + "</td>\n"
                            )
                        html.add(" <td width='10%'>" + host + "</td>\n")
                        if (
                            hoststamp in invHost
                            and "ansible_facts" in invHost[hoststamp]
                        ):
                            for option in options:
                                if (
                                    "ansible_facts" in invHost[hoststamp]
                                    and option in invHost[hoststamp]["ansible_facts"]
                                ):
                                    value = str(
                                        invHost[hoststamp]["ansible_facts"][option]
                                    )
                                    if option == "ansible_distribution":
                                        html.add("<td width='10%'>")
                                        osfamily = invHost[hoststamp]["ansible_facts"][
                                            "ansible_os_family"
                                        ]
                                        distribution = invHost[hoststamp][
                                            "ansible_facts"
                                        ]["ansible_distribution"]
                                        html.add(
                                            "<img src='assets/MaterialDesignIcons/"
                                            + osicons_get(osfamily, distribution)
                                            + ".svg' />\n"
                                        )
                                    else:
                                        html.add("<td>")
                                    html.add(value)
                                    html.add("</td>\n")
                                else:
                                    html.add(" <td>---</td>\n")
                            if stamp != "0":
                                html.add(
                                    " <td bgcolor='#abffab'>OK <a href='rescan?host="
                                    + host
                                    + "'>[RESCAN]<a/></td>\n"
                                )
                        else:
                            if hoststamp in invHost and "msg" in invHost[hoststamp]:
                                html.add(
                                    " <td colspan='5' bgcolor='#ffabab'>"
                                    + invHost[hoststamp]["msg"].strip()
                                    + "</td>\n"
                                )
                            else:
                                html.add(" <td bgcolor='#ffabab'>NO SCANS FOUND</td>\n")
                            if stamp != "0":
                                html.add(
                                    " <td bgcolor='#ffabab'>ERR <a href='rescan?host="
                                    + host
                                    + "'>[RESCAN]<a/></td>\n"
                                )
                        if stamp == "0":
                            if invHost["status"] != "OK":
                                html.add(
                                    " <td bgcolor='#ffffab'>"
                                    + invHost["status"]
                                    + " <a href='rescan?host="
                                    + host
                                    + "'>[RESCAN]<a/></td>\n"
                                )
                            else:
                                html.add(
                                    " <td bgcolor='#abffab'>"
                                    + invHost["status"]
                                    + " <a href='rescan?host="
                                    + host
                                    + "'>[RESCAN]<a/></td>\n"
                                )

                        if self.livestatus != "":
                            lstatus = -1
                            ln_c = 0
                            ln_w = 0
                            ln_u = 0
                            for part in lsdata:
                                if part["host_name"] == host:
                                    if part["acknowledged"] == 0:
                                        if part["state"] == 1:
                                            ln_w += 1
                                        elif part["state"] == 2:
                                            ln_c += 1
                                        elif part["state"] == 3:
                                            ln_u += 1
                                        if lstatus < part["state"]:
                                            lstatus = part["state"]
                            if lstatus == -1:
                                html.add("<td bgcolor='#ff0000'>MISS</td>\n")
                            elif lstatus == 0:
                                html.add("<td bgcolor='#abffab'>OK</td>\n")
                            elif lstatus == 1:
                                html.add(
                                    "<td bgcolor='#ffffab'>"
                                    + str(ln_w)
                                    + "/"
                                    + str(ln_c)
                                    + "/"
                                    + str(ln_u)
                                    + "</td>\n"
                                )
                            elif lstatus == 2:
                                html.add(
                                    "<td bgcolor='#ffabab'>"
                                    + str(ln_w)
                                    + "/"
                                    + str(ln_c)
                                    + "/"
                                    + str(ln_u)
                                    + "</td>\n"
                                )
                            elif lstatus == 3:
                                html.add(
                                    "<td bgcolor='#ababab'>"
                                    + str(ln_w)
                                    + "/"
                                    + str(ln_c)
                                    + "/"
                                    + str(ln_u)
                                    + "</td>\n"
                                )
                            else:
                                html.add(
                                    "<td bgcolor='#abffff'>"
                                    + str(ln_w)
                                    + "/"
                                    + str(ln_c)
                                    + "/"
                                    + str(ln_u)
                                    + "</td>\n"
                                )

                        if self.mantisbt != "":
                            tickets = 0
                            for issue in issues:
                                if "tags" in issue:
                                    for tag in issue["tags"]:
                                        if tag["name"] == "server:" + host:
                                            issue["match"] = True
                                            tickets += 1
                                        elif (
                                            "0" in invHost
                                            and "ansible_facts" in invHost["0"]
                                            and "ansible_fqdn"
                                            in invHost["0"]["ansible_facts"]
                                            and tag["name"]
                                            == "server:"
                                            + invHost["0"]["ansible_facts"][
                                                "ansible_fqdn"
                                            ]
                                        ):
                                            tickets += 1
                            if tickets > 0:
                                html.add(
                                    " <td bgcolor='#ababff'>" + str(tickets) + "</td>\n"
                                )
                            else:
                                html.add(
                                    " <td bgcolor='#abffab'>" + str(tickets) + "</td>\n"
                                )

                        html.add("</tr>\n")
                        if searchinfo != "":
                            colspan = 3
                            if self.pnp4nagios != "":
                                colspan += 1
                            if self.livestatus != "":
                                colspan += 1
                            if self.mantisbt != "":
                                colspan += 1
                            html.add(
                                "<tr><td colspan='"
                                + str(len(options) + colspan)
                                + "' style='color: #999999;'>"
                            )
                            html.add(searchinfo)
                            html.add("</td></tr>\n")
        html.add(bs_table_end())
        html.add("<br />\n")
        html.add(bs_col_end())
        html.add(bs_row_end())
        return html.end()

    def show_inventory(self):
        html = HtmlPage(
            "Visansible <small>("
            + str(len(self.inventory["hosts"]))
            + " hosts)</small>",
            "Inventory-File",
            "",
        )
        html.add(bs_row_begin())
        html.add(bs_col_begin("12"))
        inventorycfg = open(self.inventory["file"], "r").read()
        html.add("<pre>" + inventorycfg + "</pre>\n")
        html.add(bs_col_end())
        html.add(bs_row_end())
        return html.end()

    def show_chart(
        self,
        name,
        labels,
        datas,
        units=["", "", "", "", "", "", "", "", ""],
        colors=[
            "#cb2121",
            "#830909",
            "#923e99",
            "#ae83d5",
            "#111111",
            "#050505",
            "#646464",
            "#747474",
            "#333333",
            "#444444",
            "#555555",
            "#666666",
            "#777777",
            "#888888",
            "#999999",
            "#008080",
            "#0000FF",
            "#FF0000",
            "#800000",
            "#FFFF00",
            "#808000",
            "#00FF00",
            "#008000",
            "#00FFFF",
            "#000080",
            "#FF00FF",
            "#800080",
        ],
    ):
        html = "\n"
        html += "<!--chart-->\n"
        html += "<script>\n"
        html += '	Chart.defaults.global.defaultFontFamily = \'-apple-system,system-ui,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif\';\n'
        html += "	Chart.defaults.global.defaultFontColor = '#292b2c';\n"
        html += "	var ctx = document.getElementById('" + name + "');\n"
        html += "	var myLineChart = new Chart(ctx, {\n"
        html += "		type: 'line',\n"
        html += "		data: {labels: " + str(labels).replace(" ", "") + ",\n"
        html += "		datasets: [\n"
        dn = 0
        for data in datas:
            html += (
                "			{type: 'line', pointRadius: 0, fill: false, lineTension: 0, borderWidth: 2, label: '"
                + units[dn]
                + "', BackgroundColor: '"
                + colors[dn]
                + "', borderColor: '"
                + colors[dn]
                + "', data: "
                + str(data).replace(" ", "")
                + "},\n"
            )
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

    def show_stats(self, stamp="0"):
        colors = [
            "#cb2121",
            "#830909",
            "#923e99",
            "#ae83d5",
            "#111111",
            "#050505",
            "#646464",
            "#747474",
            "#333333",
            "#444444",
            "#555555",
            "#666666",
            "#777777",
            "#888888",
            "#999999",
            "#008080",
            "#0000FF",
            "#FF0000",
            "#800000",
            "#FFFF00",
            "#808000",
            "#00FF00",
            "#008000",
            "#00FFFF",
            "#000080",
            "#FF00FF",
            "#800080",
        ]
        options = [
            "ansible_os_family",
            "ansible_architecture",
            "ansible_product_name",
            "ansible_distribution",
            "ansible_kernel",
            "ansible_processor_count",
            "ansible_distribution_release",
            "ansible_virtualization_role",
            "ansible_virtualization_type",
            "ansible_pkg_mgr",
        ]
        stamps = []
        for host in self.inventory["hosts"]:
            invHost = self.inventory["hosts"][host]
            for timestamp in invHost:
                if timestamp.isdigit() and timestamp != "0":
                    stamps.append(timestamp)
        stats = {}
        for option in options:
            stats[option] = {}
        for host in self.inventory["hosts"]:
            invHost = self.inventory["hosts"][host]
            hoststamp = stamp
            if stamp != "0":
                for timestamp in sorted(set(stamps)):
                    if int(stamp) >= int(timestamp) and timestamp in invHost:
                        hoststamp = timestamp
            if stamp == "0" or int(stamp) >= int(invHost["first"]):
                for option in options:
                    if (
                        "0" in invHost
                        and "ansible_facts" in invHost[hoststamp]
                        and option in invHost[hoststamp]["ansible_facts"]
                    ):
                        value = invHost[hoststamp]["ansible_facts"][option]
                    else:
                        value = "UNKNOWN"
                    if value not in stats[option]:
                        stats[option][value] = 0
                    stats[option][value] += 1
        if stamp == "0":
            html = HtmlPage(
                "Visansible <small>("
                + str(len(self.inventory["hosts"]))
                + " hosts)</small>",
                "Stats",
                "latest info",
                self.show_history(stamp),
            )
        else:
            html = HtmlPage(
                "Visansible <small>("
                + str(len(self.inventory["hosts"]))
                + " hosts)</small>",
                "Stats",
                datetime.fromtimestamp(int(stamp)).strftime("%a %d. %b %Y %H:%M:%S"),
                self.show_history(stamp),
            )
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
            html.add(
                "			'text': '" + option.replace("ansible_", "").capitalize() + "',\n"
            )
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
                html.add(
                    " 'label': '"
                    + str(stats[option][label])
                    + "x "
                    + str(label)
                    + "',\n"
                )
                html.add(" 'color': '" + colors[color_n] + "',\n")
                html.add(" 'value': " + str(stats[option][label]) + ",\n")
                html.add("},\n")
                color_n += 1
                if color_n >= len(colors):
                    color_n = 0

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
        return html.end()

    def matchmark(self, text, old, color):
        try:
            index_l = text.lower().index(old.lower())
        except Exception:
            index_l = 0
        return (
            text[:index_l]
            + "<b style='color: "
            + color
            + ";'>"
            + text[index_l:][: len(old)]
            + "</b>"
            + text[index_l + len(old) :]
        )

    def search_element(self, element, search, path="", matches={}):
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
                res, matches = self.search_element(
                    part, search, path + "/" + str(n), matches
                )
                if res == True:
                    ret = True
                n += 1
        elif type(element) is dict:
            for part in element:
                res, matches = self.search_element(
                    element[part],
                    search,
                    path + "/" + str(part).replace("ansible_", ""),
                    matches,
                )
                if res == True:
                    ret = True
        return ret, matches
