import yaml
import os
import re
import glob
import json
from datetime import datetime


class Inventory:
    def __init__(self):
        self.inventory = {}

    def build_cfg(self):
        data = ""
        for group in self.inventory["groups"]:
            if group != "all":
                data += "[" + group + "]\n"
                for host in self.inventory["hosts"]:
                    if group in self.inventory["hosts"][host]["groups"]:
                        hline = host
                        for option in self.inventory["hosts"][host]["options"]:
                            hline += (
                                " "
                                + option
                                + "="
                                + str(self.inventory["hosts"][host]["options"][option])
                            )
                        data += hline + "\n"
                data += "\n"
        return data

    def build_yaml(self, group="all", prefix=""):
        data = ""
        if group == "all":
            data += "---\n"
        if group in self.inventory["groups"]:
            data += prefix + group + ":\n"
            if len(self.inventory["groups"][group]["options"]) > 0:
                data += prefix + "    vars:\n"
                for option in self.inventory["groups"][group]["options"]:
                    data += (
                        prefix
                        + "        "
                        + option
                        + ": "
                        + str(self.inventory["groups"][group]["options"][option])
                        + "\n"
                    )
            if "children" in self.inventory["groups"][group]:
                hosts = []
                for host in self.inventory["hosts"]:
                    if self.inventory["hosts"][host]["path"].endswith("/" + group):
                        hosts.append(host)
                if len(hosts) > 0:
                    data += prefix + "    hosts:\n"
                    for host in hosts:
                        data += prefix + "        " + host + ":\n"
                        for option in self.inventory["hosts"][host]["options"]:
                            data += (
                                prefix
                                + "            "
                                + option
                                + ": "
                                + str(self.inventory["hosts"][host]["options"][option])
                                + "\n"
                            )
                if len(self.inventory["groups"][group]["children"]) > 0:
                    data += prefix + "    children:\n"
                    for children in self.inventory["groups"][group]["children"]:
                        if self.inventory["groups"][children]["path"].endswith(
                            "/" + group
                        ):
                            data += self.build_yaml(children, prefix + "        ")
        return data

    def calcHostnames(self, hostnames):
        if isinstance(hostnames, str):
            hostnames = [hostnames]
        for hostString in hostnames[:]:
            hostnames.remove(hostString)
            if "[" in hostString:
                ret = re.findall("\[(.*?)\]", hostString)
                if len(ret) > 0:
                    item = ret[0]
                    seqFrom = item.split(":")[0]
                    seqTo = item.split(":")[1]
                    size = len(seqFrom)
                    if seqFrom.isdigit():
                        seq = range(int(seqFrom), int(seqTo) + 1)
                        for n in seq:
                            ns = str(n)
                            if seqFrom.startswith("0"):
                                fmt = "{:0" + str(size) + "d}"
                                ns = fmt.format(n)
                            newhostString = hostString.replace("[" + item + "]", ns)
                            hostnames.append(newhostString)
                    else:
                        seq = range(ord(seqFrom), ord(seqTo) + 1)
                        for n in seq:
                            newhostString = hostString.replace("[" + item + "]", chr(n))
                            hostnames.append(newhostString)
            else:
                hostnames.append(hostString)
                return hostnames
        return self.calcHostnames(hostnames)

    def yamlInventory(self, data, parent="", path="", isHost=False):
        if isinstance(data, (dict)):
            for part in data:
                if parent == "host":
                    host = path.split("/")[-1]
                    hostnames = self.calcHostnames(host)
                    for hostname in hostnames:
                        self.inventory["hosts"][hostname]["options"][part] = data[part]
                elif parent == "hosts":
                    if part not in self.inventory["hosts"]:
                        hostnames = self.calcHostnames(part)
                        for hostname in hostnames:
                            self.inventory["hosts"][hostname] = {}
                            self.inventory["hosts"][hostname]["rawname"] = part
                            self.inventory["hosts"][hostname]["options"] = {}
                            self.inventory["hosts"][hostname]["info"] = ""
                            self.inventory["hosts"][hostname]["stamp"] = "0"
                            self.inventory["hosts"][hostname]["last"] = "0"
                            self.inventory["hosts"][hostname]["first"] = "0"
                            self.inventory["hosts"][hostname]["status"] = "ERR"
                            self.inventory["hosts"][hostname]["groups"] = []
                            self.inventory["hosts"][hostname]["path"] = path
                            self.inventory["hosts"][hostname]["maingroup"] = path.split(
                                "/"
                            )[-1]
                            for group in path.split("/"):
                                if group != "":
                                    self.inventory["hosts"][hostname]["groups"].append(
                                        group
                                    )
                elif parent == "vars":
                    group = path.split("/")[-1]
                    self.inventory["groups"][group]["options"][part] = data[part]
                elif part not in ["hosts", "children", "vars"]:
                    if part not in self.inventory["groups"]:
                        self.inventory["groups"][part] = {}
                        self.inventory["groups"][part]["options"] = {}
                        self.inventory["groups"][part]["path"] = path
                        self.inventory["groups"][part]["children"] = []
                    for group in path.split("/"):
                        if group != "":
                            if group not in self.inventory["groups"][part]["children"]:
                                self.inventory["groups"][group]["children"].append(part)

                if part not in ["hosts", "children", "vars"]:
                    newPath = path + "/" + part
                else:
                    newPath = path
                if parent == "hosts":
                    newParent = "host"
                else:
                    newParent = part
                self.yamlInventory(data[part], newParent, newPath, isHost)

    def inventory_read(self, timestamp=0):
        group = "NONE"
        groups = {}
        self.inventory = {}
        self.inventory["groups"] = {}
        self.inventory["hosts"] = {}
        section = ""
        misc = False
        if os.path.exists("inventory.yml"):
            with open("inventory.yml") as file:
                data = yaml.load(file)
                self.yamlInventory(data)
                self.inventory["file"] = "inventory.yml"

        else:
            hostslist = open("inventory.cfg", "r").read()
            self.inventory["file"] = "inventory.cfg"
            for line in hostslist.split("\n"):
                if line.startswith("#"):
                    print("COMMENTLINE: " + line)
                elif line.startswith("[") and ":" in line:
                    group = line.strip("[]").split(":")[0]
                    section = line.strip("[]").split(":")[1]
                    if group not in self.inventory["groups"]:
                        self.inventory["groups"][group] = {}
                        self.inventory["groups"][group]["options"] = {}
                    misc = True
                elif line.startswith("["):
                    group = line.strip("[]")
                    section = ""
                    if group not in self.inventory["groups"]:
                        self.inventory["groups"][group] = {}
                        self.inventory["groups"][group]["options"] = {}
                        self.inventory["groups"][group]["path"] = "/all"
                        self.inventory["groups"][group]["children"] = []
                    misc = False
                elif misc == True and line.strip() != "":
                    if "=" in line:
                        name = line.split("=")[0].strip()
                        value = line.split("=")[1].strip()
                        if section not in self.inventory["groups"][group]["options"]:
                            self.inventory["groups"][group]["options"][section] = {}
                        self.inventory["groups"][group]["options"][section][
                            name
                        ] = value
                    else:
                        if section not in self.inventory["groups"][group]["options"]:
                            self.inventory["groups"][group]["options"][section] = []
                        self.inventory["groups"][group]["options"][section].append(
                            line.strip()
                        )
                elif misc == False and line.strip() != "":
                    host = line.split(" ")[0]
                    host_options = line.split(" ")[1:]
                    if host not in self.inventory["hosts"]:
                        self.inventory["hosts"][host] = {}
                    invHost = self.inventory["hosts"][host]
                    invHost["options"] = host_options
                    if "groups" not in invHost:
                        invHost["groups"] = []
                    if group not in invHost["groups"]:
                        invHost["groups"].append(group)
                    invHost["maingroup"] = group
                    invHost["path"] = "/all/" + group
                    invHost["info"] = ""
                    invHost["stamp"] = "0"
                    invHost["last"] = "0"
                    invHost["first"] = "0"
                    invHost["status"] = "ERR"

        hists = sorted(glob.glob("./facts/hist_*"), reverse=True)
        for host in self.inventory["hosts"]:
            if timestamp > 0:
                if os.path.isfile("./facts/hist_" + str(timestamp) + "/" + host):
                    with open(
                        "./facts/hist_" + str(timestamp) + "/" + host
                    ) as json_file:
                        hostdata = json.load(json_file)
                        self.inventory["hosts"][host]["0"] = hostdata
            else:
                for filename in hists:
                    stamp = filename.split("_")[1]
                    if os.path.isfile("./facts/hist_" + str(stamp) + "/" + host):
                        with open(
                            "./facts/hist_" + str(stamp) + "/" + host
                        ) as json_file:
                            hostdata = json.load(json_file)
                            self.inventory["hosts"][host][str(stamp)] = hostdata
                            if self.inventory["hosts"][host]["last"] == "0":
                                self.inventory["hosts"][host]["last"] = str(stamp)
                            self.inventory["hosts"][host]["first"] = str(stamp)
                            if "0" not in self.inventory["hosts"][host]:
                                if "ansible_facts" in hostdata:
                                    self.inventory["hosts"][host]["0"] = hostdata
                                    self.inventory["hosts"][host]["stamp"] = str(stamp)
                                    self.inventory["hosts"][host]["info"] += "&lt;"
                            if "ansible_facts" in hostdata:
                                self.inventory["hosts"][host]["info"] += (
                                    "OK:"
                                    + datetime.fromtimestamp(int(stamp)).strftime(
                                        "%H:%M:%S"
                                    )
                                    + " "
                                )
                            else:
                                self.inventory["hosts"][host]["info"] += (
                                    "ERR:"
                                    + datetime.fromtimestamp(int(stamp)).strftime(
                                        "%H:%M:%S"
                                    )
                                    + " "
                                )
                if os.path.isfile("./facts/" + host):
                    with open("./facts/" + host) as json_file:
                        hostdata = json.load(json_file)
                        if "0" not in self.inventory["hosts"][host]:
                            self.inventory["hosts"][host]["0"] = hostdata
                        if "ansible_facts" in hostdata:
                            self.inventory["hosts"][host]["status"] = "OK"
        return self.inventory
