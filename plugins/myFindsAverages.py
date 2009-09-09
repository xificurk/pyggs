# -*- coding: utf-8 -*-
"""
    plugins/myFindsAverages.py - Add average values to general statistics.
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
import time, math

class myFindsAverages(base):
    def __init__(self, master):
        base.__init__(self, master)
        self.dependencies = ["general", "myFinds"]
        self.about        = _("Adds rows about average finds (overall, in last 365 days) into General statistics section.")


    def run(self):
        templateData            = {}
        templateData["overall"] = self.getAverages()
        templateData["last365"] = self.getAverages("date > DATE('now', '-365 days')", 365);
        self.general.registerTemplate(":stats.general.myFindsAverages", templateData)


    def getAverages(self, where = "1", period = None):
        """return averages stats"""
        result = self.myFinds.storage.select("SELECT * FROM myFinds WHERE %s ORDER BY date ASC, sequence ASC" % where)
        all    = self.myFinds.storage.fetchAssoc(result)
        days   = self.myFinds.storage.fetchAssoc(result, "date")

        ret           = {}
        ret["finds"]  = len(all);
        ret["gcdays"] = len(days);

        if period is None:
            start  = days.pop(list(days.keys())[0])
            start  = start["date"]
            period = int(math.ceil((time.time()-time.mktime(time.strptime(start, "%Y-%m-%d")))/24/3600+1))

        ret["days"]        = period;
        ret["gcdays/week"] = ret["gcdays"]/period*7
        ret["finds/gcday"] = ret["finds"]/max(ret["gcdays"],1)
        ret["finds/day"]   = ret["finds"]/period
        ret["finds/week"]  = ret["finds"]/period*7
        ret["finds/month"] = ret["finds"]/period*365.25/12

        return ret
