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

from .base import base

class gcczMyRatingsTop10(base):
    def __init__(self, master):
        base.__init__(self, master)
        self.dependencies = ["stats", "myFinds", "gcczRatings", "gcczMyRatings", "cache"]
        self.about        = _("List of top 10 user rated caches.")


    def run(self):
        templateData = {"top10":self.getMyRatingsTop()}
        if len(templateData["top10"]):
            self.stats.registerTemplate(":stats.gcczMyRatingsTop10", templateData)


    def getMyRatingsTop(self):
        fetchAssoc = self.master.globalStorage.fetchAssoc

        myFinds = self.myFinds.storage.select("SELECT * FROM myFinds")
        myFinds = fetchAssoc(myFinds, "guid")

        caches  = self.cache.storage.select(myFinds.keys())
        for cache in caches:
            cache.update(myFinds[cache["guid"]])
        caches  = fetchAssoc(caches, "waypoint")

        ratings = self.gcczRatings.storage.select(caches.keys())
        ratings = fetchAssoc(ratings, "waypoint")

        myratings = self.gcczMyRatings.storage.select(caches.keys())
        myratings = fetchAssoc(myratings, "waypoint")

        for wpt in list(caches.keys()):
            try:
                caches[wpt].update(ratings[wpt])
            except:
                caches[wpt].update({"rating":0,"count":0})
            try:
                caches[wpt].update(myratings[wpt])
            except:
                del(caches[wpt])

        caches = list(caches.values())
        caches.sort(key=lambda x: int(x["myrating"]) + int(x["rating"])/1000 + int(x["count"])/10000000)
        caches.reverse()
        return caches
