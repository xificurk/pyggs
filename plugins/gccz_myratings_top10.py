# -*- coding: utf-8 -*-
"""
    plugins/gccz_myratings_top10.py - Your Top10 rated caches.
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
        self.dependencies = ["stats", "myfinds", "gccz_ratings", "gccz_myratings", "cache"]
        self.about = _("List of top 10 user rated caches.")


    def run(self):
        templateData = {"top10":self.getMyRatingsTop()}
        if len(templateData["top10"]) > 0:
            self.stats.registerTemplate(":stats.gccz_myratings_top10", templateData)


    def getMyRatingsTop(self):
        fetchAssoc = self.master.globalStorage.fetchAssoc

        myFinds = self.myfinds.storage.select()
        myFinds = fetchAssoc(myFinds, "guid")

        caches = self.cache.storage.getDetails(myFinds.keys())
        for cache in caches:
            cache.update(myFinds[cache["guid"]])
        caches = fetchAssoc(caches, "waypoint")
        try:
            del(caches[""])
        except KeyError:
            pass

        ratings = self.gccz_ratings.storage.getRatings(caches.keys())
        ratings = fetchAssoc(ratings, "waypoint")

        myratings = self.gccz_myratings.storage.getRatings(caches.keys())
        myratings = fetchAssoc(myratings, "waypoint")

        for wpt in list(caches.keys()):
            try:
                caches[wpt].update(myratings[wpt])
            except KeyError:
                del(caches[wpt])
                continue
            try:
                caches[wpt].update(ratings[wpt])
            except KeyError:
                caches[wpt].update({"rating":0,"count":0,"deviation":100})

        caches = list(caches.values())
        caches.sort(key=lambda x: int(x["myrating"]) + (int(x["rating"]) - int(x["deviation"])/1000)/1000, reverse=True)
        return caches
