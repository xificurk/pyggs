# -*- coding: utf-8 -*-
"""
    plugins/cacheDistrib.py - Tables with distribution of finds by type,
      container and country.
    Copyright (C) 2009 Petr Morávek

    This file is part of Pyggs.

    Pyggs is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    Pyggs is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

import logging
from collections import OrderedDict

class cacheDistrib(object):
    def __init__(self, master):
        self.NS  = "plugin.cacheDistrib"
        self.log = logging.getLogger("Pyggs.%s" % self.NS)
        self.master = master

        self.dependencies = ["base", "myFinds", "cache"]
        self.templateData = {}


    def setup(self):
        """Setup script"""
        pass


    def prepare(self):
        """Setup everything needed before actual run"""
        self.log.debug("Preparing...")


    def run(self):
        """Run the plugin's code"""
        self.log.info("Running...")

        myFinds = self.master.plugins["myFinds"].storage.getList()
        caches  = self.master.plugins["cache"].storage.select(myFinds)

        self.templateData["total"] = len(myFinds)

        fetchAssoc = self.master.plugins["cache"].storage.database.fetchAssoc

        result = fetchAssoc(caches, "country,#")
        tmp = []
        for country in result:
            tmp.append({"country":country, "count":len(result[country])})
        tmp.sort(key=lambda x: x["count"])
        tmp.reverse()
        countries = OrderedDict()
        for row in tmp:
            countries[row["country"]] = row["count"]
        self.templateData["countries"] = countries

        result = fetchAssoc(caches, "type,#")
        tmp = []
        for type in result:
            tmp.append({"type":type, "count":len(result[type])})
        tmp.sort(key=lambda x: x["count"])
        tmp.reverse()
        types = OrderedDict()
        for row in tmp:
            types[row["type"]] = row["count"]
        self.templateData["types"] = types

        result = fetchAssoc(caches, "size,#")
        tmp = []
        for size in result:
            tmp.append({"size":size, "count":len(result[size])})
        tmp.sort(key=lambda x: x["count"])
        tmp.reverse()
        sizes = OrderedDict()
        for row in tmp:
            sizes[row["size"]] = row["count"]

        self.templateData["sizes"] = sizes

        self.master.plugins["base"].registerTemplate(":cacheDistrib", self.templateData)
