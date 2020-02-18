#!/usr/bin/py.test-3
#
#

import pytest
from http.server import BaseHTTPRequestHandler, HTTPServer
from inventory import *
from RenderFacts import *

inventory = Inventory().inventory_read()
rf = RenderFacts(inventory)


def test_show_hostdata():
	for host in inventory["hosts"]:
		ret = rf.show_hostdata(host)

def test_show_graph():
	ret = rf.show_graph()

def test_show_csv():
	ret = rf.show_csv()

def test_show_hosts():
	ret = rf.show_hosts()

def test_show_inventory():
	ret = rf.show_inventory()

def test_show_stats():
	ret = rf.show_stats()


