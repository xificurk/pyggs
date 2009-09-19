# -*- coding: utf-8 -*-
"""
    plugins/mapCR.py - Map of caches found in Czech Republic.
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


class mapCR(base):
    def __init__(self, master):
        base.__init__(self, master)
        self.dependencies = ["stats", "myFinds", "cache", "gccz"]
        self.about = _("Maps of Czech Republic from geocaching.cz.")


    def run(self):
        myFinds = self.myFinds.storage.getList()
        caches = self.cache.storage.select(myFinds)
        caches = self.master.globalStorage.fetchAssoc(caches, "country,province,#")
        caches = caches.get("Czech Republic")
        if caches is not None:
            provincesAbbr = {}
            provincesAbbr["Hlavni mesto Praha"] = "AA"
            provincesAbbr["Jihocesky kraj"] = "CC"
            provincesAbbr["Jihomoravsky kraj"] = "BB"
            provincesAbbr["Karlovarsky kraj"] = "KK"
            provincesAbbr["Kralovehradecky kraj"] = "HH"
            provincesAbbr["Liberecky kraj"] = "LL"
            provincesAbbr["Moravskoslezsky kraj"] = "TT"
            provincesAbbr["Olomoucky kraj"] = "MM"
            provincesAbbr["Pardubicky kraj"] = "EE"
            provincesAbbr["Plzensky kraj"] = "PP"
            provincesAbbr["Stredocesky kraj"] = "SS"
            provincesAbbr["Ustecky kraj"] = "UU"
            provincesAbbr["Vysocina"] = "JJ"
            provincesAbbr["Zlinsky kraj"] = "ZZ"
            total = {"country":0, "province":0}
            tot = 0
            provinces = {}
            for province in caches:
                total["country"] = total["country"]+len(caches[province])
                if len(province) > 0:
                    provinces[provincesAbbr[province]] = len(caches[province])
                    tot = tot+len(caches[province])
            total["province"] = len(provinces)

            prsorted = list(provinces.keys())
            prsorted.sort()
            tmp1 = ""
            tmp2 = ""
            for province in prsorted:
                if len(tmp1) > 0 or len(tmp2) > 0:
                    tmp1 = tmp1 + ","
                    tmp2 = tmp2 + ","
                tmp1 = tmp1 + provinces[province]
                tmp2 = "{0}{1}".format(tmp2, round(100*provinces[province]/tot))

            templateData = {}
            templateData["map"] = {}
            templateData["map"]["chld"] = "".join(prsorted)
            templateData["map"]["chd"] = tmp1 + "|" + tmp2
            templateData["total"] = total
            templateData["uid"] = self.master.config.get(self.gccz.NS, "uid")
            self.stats.registerTemplate(":stats.mapCR", templateData)
