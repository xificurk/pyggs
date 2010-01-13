# -*- coding: utf-8 -*-
"""
    plugins/gccz_ratings_top.py - Add best/worst found cache to general
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

from . import base


class Plugin(base.Plugin):
    def __init__(self, master):
        base.Plugin.__init__(self, master)
        self.dependencies = ["general", "myfinds", "gccz_ratings", "cache"]
        self.about = _("Adds rows about worst/best rated cache found into General statistics section.")


    def run(self):
        templateData = self.getTopRated()
        if templateData is not None:
            self.general.registerTemplate(":stats.general.gccz_ratings_top", templateData)


    def getTopRated(self):
        fetchAssoc = self.master.globalStorage.fetchAssoc

        myFinds = self.myfinds.storage.select()
        myFinds = fetchAssoc(myFinds, "guid")

        caches = self.cache.storage.select(myFinds.keys())
        for cache in caches:
            cache.update(myFinds[cache["guid"]])
        caches = fetchAssoc(caches, "waypoint")
        try:
            del(caches[""])
        except KeyError:
            pass

        ratings = self.gccz_ratings.storage.select(caches.keys(), min=3)
        ratings = fetchAssoc(ratings, "waypoint")

        for wpt in caches:
            try:
                caches[wpt].update(ratings[wpt])
            except KeyError:
                pass

        if len(ratings) > 0:
            result = {}
            result["best"] = {"rating":-1,"count":0}
            result["worst"] = {"rating":101,"count":0}
            for wpt in ratings:
                if caches[wpt]["rating"] > result["best"]["rating"] or (caches[wpt]["rating"] == result["best"]["rating"] and caches[wpt]["count"] > result["best"]["count"]):
                    result["best"] = caches[wpt]
                if caches[wpt]["rating"] < result["worst"]["rating"] or (caches[wpt]["rating"] == result["worst"]["rating"] and caches[wpt]["count"] > result["worst"]["count"]):
                    result["worst"] = caches[wpt]
            return result
        else:
            return None
