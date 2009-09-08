# -*- coding: utf-8 -*-
"""
    plugins/cacheTopFeatures.py - Add top features of found caches (most distant
      cache, most southern cache, etc.) to general statistics.
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

class cacheTopFeatures(object):
    def __init__(self, master):
        self.NS  = "plugin.cacheTopFeatures"
        self.log = logging.getLogger("Pyggs.%s" % self.NS)
        self.master = master

        self.dependencies = ["general", "cache", "myFinds"]
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

        self.templateData["distances"]  = self.getTopDistances(caches)
        self.templateData["directions"] = self.getTopDirections(caches)
        self.templateData["age"]        = self.getTopAge(caches)
        self.templateData["archived"]   = self.getArchived(caches)
        self.master.plugins["general"].registerTemplate(":cacheTopFeatures", self.templateData)


    def getTopDistances(self, caches):
        distances = {"min":caches[0], "max":caches[0]}
        for cache in caches:
            cache["distance"] = self.master.plugins["cache"].distance(cache["lat"], cache["lon"])
            if cache["distance"] > distances["max"]["distance"]:
                distances["max"] = cache
            if cache["distance"] < distances["min"]["distance"]:
                distances["min"] = cache

        return distances


    def getTopDirections(self, caches):
        directions = {"north":caches[0], "south":caches[0],"east":caches[0], "west":caches[0]}
        for cache in caches:
            if cache["lat"] > directions["north"]["lat"]:
                directions["north"] = cache
            if cache["lat"] < directions["south"]["lat"]:
                directions["south"] = cache
            if cache["lon"] > directions["east"]["lon"]:
                directions["east"] = cache
            if cache["lon"] < directions["west"]["lon"]:
                directions["west"] = cache

        return directions


    def getTopAge(self, caches):
        age = {"min":caches[0], "max":caches[0]}
        for cache in caches:
            if cache["hidden"] > age["max"]["hidden"]:
                age["max"] = cache
            if cache["hidden"] < age["min"]["hidden"]:
                age["min"] = cache

        return age


    def getArchived(self, caches):
        archived = {"absolute":0, "relative":0}
        for cache in caches:
            if cache["archived"] > 0:
                archived["absolute"] = archived["absolute"]+1

        archived["relative"] = archived["absolute"]/len(caches)
        return archived