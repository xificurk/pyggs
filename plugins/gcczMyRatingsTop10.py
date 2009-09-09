# -*- coding: utf-8 -*-
"""
    plugins/gcczMyRatingsTop10.py - Your Top10 rated caches.
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

class gcczMyRatingsTop10(object):
    def __init__(self, master):
        self.NS  = "plugin.gcczMyRatingsTop10"
        self.log = logging.getLogger("Pyggs.%s" % self.NS)
        self.master = master

        self.dependencies = ["stats", "myFinds", "gcczRatings", "gcczMyRatings", "cache"]
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
        ratings = plugins["gcczRatings"].storage.select(caches.keys())
        ratings = fetchAssoc(ratings, "waypoint")
        myratings = plugins["gcczMyRatings"].storage.select(caches.keys())
        myratings = fetchAssoc(myratings, "waypoint")
        for wpt in caches:
            try:
                caches[wpt].update(ratings[wpt])
            except:
                caches[wpt].update({"rating":0,"count":0})
            try:
                caches[wpt].update(myratings[wpt])
            except:
                del(caches[wpt])

        if len(caches):
            caches = list(caches.values())
            caches.sort(key=lambda x: int(x["myrating"]) + int(x["rating"])/1000 + int(x["count"])/10000000)
            caches.reverse()

            self.templateData["top10"] = caches
            self.master.plugins["stats"].registerTemplate(":stats.gcczMyRatingsTop10", self.templateData)
