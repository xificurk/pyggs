# -*- coding: utf-8 -*-
"""
    plugins/cacheDistrib.py - Tables with distribution of finds by type,
      container and country.
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

from collections import OrderedDict

from .base import base


class cacheDistrib(base):
    def __init__(self, master):
        base.__init__(self, master)
        self.dependencies = ["stats", "myFinds", "cache"]
        self.about = _("Statistics of found caches by type, size and country.")


    def prepare(self):
        base.prepare(self)
        self.fetchAssoc = self.master.globalStorage.fetchAssoc


    def run(self):
        myFinds = self.myFinds.storage.getList()
        caches = self.cache.storage.select(myFinds)

        templateData = {}
        templateData["total"] = len(myFinds)
        templateData["countries"] = self.getCountries(caches)
        templateData["types"] = self.getTypes(caches)
        templateData["sizes"] = self.getSizes(caches)
        self.stats.registerTemplate(":stats.cacheDistrib", templateData)


    def getCountries(self, caches):
        result = self.fetchAssoc(caches, "country,#")
        tmp = []
        for country in result:
            tmp.append({"country":country, "count":len(result[country])})
        tmp.sort(key=lambda x: x["count"])
        tmp.reverse()
        countries = OrderedDict()
        for row in tmp:
            countries[row["country"]] = row["count"]
        return countries


    def getTypes(self, caches):
        result = self.fetchAssoc(caches, "type,#")
        tmp = []
        for type in result:
            tmp.append({"type":type, "count":len(result[type])})
        tmp.sort(key=lambda x: x["count"])
        tmp.reverse()
        types = OrderedDict()
        for row in tmp:
            types[row["type"]] = row["count"]
        return types


    def getSizes(self, caches):
        result = self.fetchAssoc(caches, "size,#")
        tmp = []
        for size in result:
            tmp.append({"size":size, "count":len(result[size])})
        tmp.sort(key=lambda x: x["count"])
        tmp.reverse()
        sizes = OrderedDict()
        for row in tmp:
            sizes[row["size"]] = row["count"]
        return sizes
