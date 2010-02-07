# -*- coding: utf-8 -*-
"""
    plugins/elevations.py - Show distribution of found caches by elevation.
    Copyright (C) 2010 Petr Morávek

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

import math

from . import base


class Plugin(base.Plugin):
    def __init__(self, master):
        base.Plugin.__init__(self, master)
        self.dependencies = ["myfinds", "cache", "stats"]
        self.about = _("Adds graph and average value of finds by elevation.")


    def run(self):
        myFinds = self.myfinds.storage.select()
        myFinds = self.myfinds.storage.fetchAssoc(myFinds, "guid")
        caches = self.cache.storage.select(myFinds.keys())
        for cache in caches:
            cache["elevation"] = int(cache["elevation"])
            if cache["elevation"] == -9999:
                caches.pop(cache)
            else:
                cache.update(myFinds[cache["guid"]])

        totals = None
        for cache in caches:
            if totals is None:
                totals = {"min":cache["elevation"], "max":cache["elevation"], "sum":cache["elevation"], "count":1}
                continue
            if cache["elevation"] > totals["max"]:
                totals["max"] = cache["elevation"]
            if cache["elevation"] < totals["min"]:
                totals["min"] = cache["elevation"]
            totals["sum"] = totals["sum"] + cache["elevation"]
            totals["count"] = totals["count"] + 1
        if totals is None:
            return
        average = round(totals["sum"]/totals["count"])
        step = math.ceil((totals["max"] - totals["min"])/20/25)*25

        elevations = []
        top = 0
        for lower in range(math.floor(totals["min"]/step)*step, (math.floor(totals["max"]/step)+1)*step, step):
            data = {"label":lower, "count":0}
            for cache in caches:
                if cache["elevation"] >= lower and cache["elevation"] < lower+step:
                    caches.remove(cache)
                    data["count"] = data["count"] + 1
            elevations.append(data)
            top = max(top, data["count"])

        templateData = {}
        templateData["average"] = average
        templateData["top"] = top
        templateData["elevations"] = elevations
        self.stats.registerTemplate(":stats.elevations", templateData)
