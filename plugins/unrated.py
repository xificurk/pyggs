# -*- coding: utf-8 -*-
"""
    plugins/unrated.py - Generates list with found but unrated caches.
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

class unrated(object):
    def __init__(self, master):
        self.NS  = "plugin.unrated"
        self.log = logging.getLogger("Pyggs.%s" % self.NS)
        self.master = master

        self.dependencies = ["myFinds", "gcczMyRatings", "cache"]
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
        fetchAssoc = self.master.globalStorage.fetchAssoc
        plugins = self.master.plugins
        myFinds = plugins["myFinds"].storage.select("SELECT * FROM myFinds")
        myFinds = fetchAssoc(myFinds, "guid")
        caches  = plugins["cache"].storage.select(myFinds.keys())
        for cache in caches:
            cache.update(myFinds[cache["guid"]])
        caches  = fetchAssoc(caches, "waypoint")
        myratings = plugins["gcczMyRatings"].storage.select(caches.keys())
        myratings = list(fetchAssoc(myratings, "waypoint").keys())
        unrated = []
        for wpt in caches:
            if caches[wpt]["waypoint"] not in myratings:
                unrated.append(caches[wpt])
        self.templateData["unrated"] = unrated
        self.master.registerPage("unrated.html", ":unrated", ":menu.unrated", self.templateData)
