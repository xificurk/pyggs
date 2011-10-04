# -*- coding: utf-8 -*-
"""
    plugins/map_cr.py - Map of caches found in Czech Republic.
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
    abbr = {}
    abbr["Hlavni mesto Praha"] = "AA"
    abbr["Jihocesky kraj"] = "CC"
    abbr["Jihomoravsky kraj"] = "BB"
    abbr["Karlovarsky kraj"] = "KK"
    abbr["Kralovehradecky kraj"] = "HH"
    abbr["Liberecky kraj"] = "LL"
    abbr["Moravskoslezsky kraj"] = "TT"
    abbr["Olomoucky kraj"] = "MM"
    abbr["Pardubicky kraj"] = "EE"
    abbr["Plzensky kraj"] = "PP"
    abbr["Stredocesky kraj"] = "SS"
    abbr["Ustecky kraj"] = "UU"
    abbr["Kraj Vysocina"] = "JJ"
    abbr["Zlinsky kraj"] = "ZZ"

    def __init__(self, master):
        base.Plugin.__init__(self, master)
        self.dependencies = ["stats", "myfinds", "cache", "gccz"]
        self.about = _("Maps of Czech Republic from geocaching.cz.")


    def run(self):
        myFinds = self.myfinds.storage.getList()
        caches = self.cache.storage.getDetails(myFinds)
        caches = self.master.globalStorage.fetchAssoc(caches, "country,province,#")
        caches = caches.get("Czech Republic")
        if caches is None:
            return

        total = {"country":0, "province":0}
        tot = 0
        provinces = {}
        for province in caches:
            total["country"] += len(caches[province])
            if len(province) > 0 and province in self.abbr:
                provinces[self.abbr[province]] = len(caches[province])
                tot += len(caches[province])
        total["province"] = len(provinces)

        prsorted = list(provinces.keys())
        prsorted.sort()
        data_count = []
        data_percent = []
        for province in prsorted:
            data_count.append(str(provinces[province]))
            data_percent.append(str(round(100*provinces[province]/tot)))

        templateData = {}
        templateData["map"] = {}
        templateData["map"]["chld"] = "".join(prsorted)
        templateData["map"]["chd"] = ",".join(data_count) + "|" + ",".join(data_percent)
        templateData["total"] = total
        templateData["uid"] = self.gccz.config["uid"]
        self.stats.registerTemplate(":stats.map_cr", templateData)
