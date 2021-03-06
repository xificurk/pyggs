# -*- coding: utf-8 -*-
"""
    plugins/cache_topfeatures.py - Add top features of found caches (most distant
      cache, most southern cache, etc.) to general statistics.
    Copyright (C) 2009-2010 Petr Morávek

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

from . import base


class Plugin(base.Plugin):
    def __init__(self, master):
        base.Plugin.__init__(self, master)
        self.dependencies = ["general", "cache", "myfinds"]
        self.about = _("Adds rows about most distant, most southern, oldest etc. caches found into General statistics section.")


    def run(self):
        myFinds = self.myfinds.storage.select()
        myFinds = self.myfinds.storage.fetchAssoc(myFinds, "guid")
        caches = self.cache.storage.getDetails(myFinds.keys())
        for cache in caches:
            cache.update(myFinds[cache["guid"]])

        templateData = {}
        templateData["distances"] = self.getTopDistances(caches)
        templateData["directions"] = self.getTopDirections(caches)
        templateData["elevations"] = self.getTopElevations(caches)
        templateData["age"] = self.getTopAge(caches)
        templateData["archived"] = self.getArchived(caches)
        self.general.registerTemplate(":stats.general.cache_topfeatures", templateData)


    def getTopDistances(self, caches):
        distances = None
        for cache in caches:
            if isinstance(cache["lat"], str) or isinstance(cache["lon"], str):
                continue
            cache["distance"] = self.cache.distance(cache["lat"], cache["lon"])
            if distances is None:
                distances = {"min":cache, "max":cache}
                continue
            if cache["distance"] > distances["max"]["distance"] or (cache["distance"] == distances["max"]["distance"] and cache["date"] < distances["max"]["date"]):
                distances["max"] = cache
            if cache["distance"] < distances["min"]["distance"] or (cache["distance"] == distances["min"]["distance"] and cache["date"] < distances["min"]["date"]):
                distances["min"] = cache

        return distances


    def getTopDirections(self, caches):
        directions = None
        for cache in caches:
            if isinstance(cache["lat"], str) or isinstance(cache["lon"], str):
                continue
            if directions is None:
                directions = {"north":cache, "south":cache,"east":cache, "west":cache}
                continue
            if cache["lat"] > directions["north"]["lat"] or (cache["lat"] == directions["north"]["lat"] and cache["date"] < directions["north"]["date"]):
                directions["north"] = cache
            if cache["lat"] < directions["south"]["lat"] or (cache["lat"] == directions["south"]["lat"] and cache["date"] < directions["south"]["date"]):
                directions["south"] = cache
            if cache["lon"] > directions["east"]["lon"] or (cache["lon"] == directions["east"]["lon"] and cache["date"] < directions["east"]["date"]):
                directions["east"] = cache
            if cache["lon"] < directions["west"]["lon"] or (cache["lon"] == directions["west"]["lon"] and cache["date"] < directions["west"]["date"]):
                directions["west"] = cache

        return directions


    def getTopElevations(self, caches):
        elevation = None
        for cache in caches:
            if cache["elevation"] == -9999:
                continue
            if elevation is None:
                elevation = {"min":cache, "max":cache}
                continue
            if cache["elevation"] > elevation["max"]["elevation"] or (cache["elevation"] == elevation["max"]["elevation"] and cache["date"] < elevation["max"]["date"]):
                elevation["max"] = cache
            if cache["elevation"] < elevation["min"]["elevation"] or (cache["elevation"] == elevation["min"]["elevation"] and cache["date"] < elevation["min"]["date"]):
                elevation["min"] = cache

        return elevation


    def getTopAge(self, caches):
        age = None
        for cache in caches:
            if cache["hidden"] == "":
                continue
            if age is None:
                age = {"min":cache, "max":cache}
                continue
            if cache["hidden"] > age["max"]["hidden"] or (cache["hidden"] == age["max"]["hidden"] and cache["date"] < age["max"]["date"]):
                age["max"] = cache
            if cache["hidden"] < age["min"]["hidden"] or (cache["hidden"] == age["min"]["hidden"] and cache["date"] < age["min"]["date"]):
                age["min"] = cache

        return age


    def getArchived(self, caches):
        archived = {"absolute":0, "relative":0}
        for cache in caches:
            if isinstance(cache["archived"], str):
                continue
            if cache["archived"] > 0:
                archived["absolute"] = archived["absolute"]+1

        archived["relative"] = archived["absolute"]/len(caches)
        return archived
