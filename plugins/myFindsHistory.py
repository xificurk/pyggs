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

import logging, datetime

class myFindsHistory(object):
    def __init__(self, master):
        self.NS  = "plugin.myFindsHistory"
        self.log = logging.getLogger("Pyggs.%s" % self.NS)
        self.master = master

        self.dependencies = ["myFindsAverages", "stats"]
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

        myFinds  = self.master.plugins["myFinds"].storage.select("""SELECT
                COUNT(DISTINCT date) AS gcdays,
                COUNT(guid) AS finds,
                STRFTIME('%Y', date) AS year,
                STRFTIME('%m', date) AS month,
                STRFTIME('%Y%m', date) AS ym
            FROM myFinds
            GROUP BY ym
            ORDER BY ym ASC
            """)
        myFinds = self.master.plugins["myFinds"].storage.database.fetchAssoc(myFinds, "year,month")

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
                    "averages":self.master.plugins["myFindsAverages"].getAverages("STRFTIME('%%Y', date) = '%d'" % int(year), int(datetime.date(int(year), 12, 31).strftime("%j")))}


        self.templateData["history"] = myFinds
        self.templateData["top"]     = top
        self.master.plugins["stats"].registerTemplate(":stats.myFindsHistory", self.templateData)
