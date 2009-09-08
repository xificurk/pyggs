# -*- coding: utf-8 -*-
"""
    plugins/topGcczRatings.py - Add best/worst found cache to general
      statistics.
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

class topGcczRatings(object):
    def __init__(self, master):
        self.NS  = "plugin.topGcczRatings"
        self.log = logging.getLogger("Pyggs.%s" % self.NS)
        self.master = master

        self.dependencies = ["general", "myFinds", "gcczRatings", "cache"]
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
        myFinds = self.master.plugins["myFinds"].storage.select("SELECT * FROM myFinds")
        myFinds = self.master.profileStorage.fetchAssoc(myFinds, "guid")
        caches  = self.master.plugins["cache"].storage.select(myFinds.keys())
        for cache in caches:
            cache.update(myFinds[cache["guid"]])
        caches  = self.master.globalStorage.fetchAssoc(caches, "waypoint")
        ratings = self.master.plugins["gcczRatings"].storage.select(caches.keys(), min=3)
        ratings = self.master.globalStorage.fetchAssoc(ratings, "waypoint")
        for wpt in caches:
            try:
                caches[wpt].update(ratings[wpt])
            except:
                pass

        if len(ratings):
            result = {}
            result["best"] = {"rating":-1,"count":0}
            result["worst"] = {"rating":101,"count":0}
            for wpt in ratings:
                if caches[wpt]["rating"] > result["best"]["rating"] or (caches[wpt]["rating"] == result["best"]["rating"] and caches[wpt]["count"] > result["best"]["count"]):
                    result["best"] = caches[wpt]
                if caches[wpt]["rating"] < result["worst"]["rating"] or (caches[wpt]["rating"] == result["worst"]["rating"] and caches[wpt]["count"] > result["worst"]["count"]):
                    result["worst"] = caches[wpt]

            self.templateData = result
            self.master.plugins["general"].registerTemplate(":topGcczRatings", self.templateData)
