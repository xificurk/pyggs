# -*- coding: utf-8 -*-
"""
    plugins/myFindsHistory.py - Show year after year myFinds history data.
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
import datetime

class myFindsHistory(base):
    def __init__(self, master):
        base.__init__(self, master)
        self.dependencies = ["myFinds", "myFindsAverages", "stats"]
        self.about        = _("Adds graph and average find values for every user's caching year.")


    def run(self):
        myFinds  = self.myFinds.storage.select("""SELECT
                COUNT(DISTINCT date) AS gcdays,
                COUNT(guid) AS finds,
                STRFTIME('%Y', date) AS year,
                STRFTIME('%m', date) AS month,
                STRFTIME('%Y%m', date) AS ym
            FROM myFinds
            GROUP BY ym
            ORDER BY ym ASC
            """)
        myFinds = self.myFinds.storage.fetchAssoc(myFinds, "year,month")

        top = 0
        for year in myFinds:
            yearstop = 0
            for month in myFinds[year]:
                if myFinds[year][month]["finds"] > yearstop:
                    yearstop = myFinds[year][month]["finds"]
                if myFinds[year][month]["finds"] > top:
                    top = myFinds[year][month]["finds"]
            myFinds[year] = {
                    "top":yearstop,
                    "data":myFinds[year],
                    "averages":self.myFindsAverages.getAverages("STRFTIME('%%Y', date) = '%d'" % int(year), int(datetime.date(int(year), 12, 31).strftime("%j")))}

        templateData            = {}
        templateData["history"] = myFinds
        templateData["top"]     = top
        self.stats.registerTemplate(":stats.myFindsHistory", templateData)
