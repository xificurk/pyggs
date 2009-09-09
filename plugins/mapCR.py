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

import logging

class mapCR(object):
    def __init__(self, master):
        self.NS  = "plugin.mapCR"
        self.log = logging.getLogger("Pyggs.%s" % self.NS)
        self.master = master

        self.dependencies = ["stats", "myFinds", "cache", "gccz"]
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
        caches  = self.master.globalStorage.fetchAssoc(caches, "country,province,#")
        caches  = caches.get("Czech Republic")
        if caches:
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
            tot   = 0
            provinces = {}
            for province in caches:
                total["country"] = total["country"]+len(caches[province])
                if len(province):
                    provinces[provincesAbbr[province]] = len(caches[province])
                    tot = tot+len(caches[province])
            total["province"] = len(provinces)
            self.templateData["total"] = total

            prsorted = list(provinces.keys())
            prsorted.sort()
            self.templateData["map"] = {}
            self.templateData["map"]["chld"] = "".join(prsorted)
            tmp1 = ""
            tmp2 = ""
            for province in prsorted:
                if len(tmp1) or len(tmp2):
                    tmp1 = "%s," % tmp1
                    tmp2 = "%s," % tmp2
                tmp1 = "%s%s" % (tmp1, provinces[province])
                tmp2 = "%s%d" % (tmp2, round(100*provinces[province]/tot))
            self.templateData["map"]["chd"] = "%s|%s" % (tmp1, tmp2)

            self.templateData["uid"] = self.master.config.get(self.master.plugins["gccz"].NS, "uid")
            self.master.plugins["stats"].registerTemplate(":stats.mapCR", self.templateData)
