# -*- coding: utf-8 -*-
"""
    plugins/myFindsTopPeriods.py - Add top periods of geocacher
      to general statistics.
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

class myFindsTopPeriods(object):
    def __init__(self, master):
        self.NS  = "plugin.myFindsTopPeriods"
        self.log = logging.getLogger("Pyggs.%s" % self.NS)
        self.master = master

        self.dependencies = ["general", "myFinds"]
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
        self.templateData = self.getTopPeriods()
        self.master.plugins["general"].registerTemplate(":statistics.general.myFindsTopPeriods", self.templateData)


    def getTopPeriods(self):
        """return top periods stats"""
        myFindsDB = self.master.plugins["myFinds"].storage
        result = myFindsDB.select("""SELECT
                date,
                (STRFTIME('%w', date) = "0" OR STRFTIME('%w', date) = "6") AS weekend,
                DATE(date, "weekday 0") AS sunday,
                STRFTIME('%Y-%m', date) AS month,
                STRFTIME('%Y', date) AS year
            FROM myFinds
            ORDER BY date ASC""")

        ret = {}
        ret["day"] = {"date":"", "count":0}
        days = myFindsDB.database.fetchAssoc(result, "date,#")
        for day in days:
            if len(days[day]) > ret["day"]["count"]:
                ret["day"]["count"] = len(days[day])
                ret["day"]["date"]  = day

        ret["weekend"] = {"date":"", "count":0}
        weekends = myFindsDB.database.fetchAssoc(result, "weekend,sunday,#")[1]
        for weekend in weekends:
            if len(weekends[weekend]) > ret["weekend"]["count"]:
                ret["weekend"]["count"] = len(weekends[weekend])
                ret["weekend"]["date"]  = weekend

        ret["week"] = {"date":"", "count":0}
        weeks = myFindsDB.database.fetchAssoc(result, "sunday,#")
        for week in weeks:
            if len(weeks[week]) > ret["week"]["count"]:
                ret["week"]["count"] = len(weeks[week])
                ret["week"]["date"]  = week

        ret["month"] = {"date":"", "count":0}
        months = myFindsDB.database.fetchAssoc(result, "month,#")
        for month in months:
            if len(months[month]) > ret["month"]["count"]:
                ret["month"]["count"] = len(months[month])
                ret["month"]["date"]  = months[month][0]["date"]

        ret["year"] = {"date":"", "count":0}
        years = myFindsDB.database.fetchAssoc(result, "year,#")
        for year in years:
            if len(years[year]) > ret["year"]["count"]:
                ret["year"]["count"] = len(years[year])
                ret["year"]["date"]  = years[year][0]["date"]

        gcperiod = {"count":0, "start":"NA", "end":"NA"}
        ended = True
        for day in days:
            if ended:
                gcperiod_tmp = {"count":1, "start":day}
                ended = False

            next_day = datetime.datetime.strptime(day, "%Y-%m-%d") + datetime.timedelta(1)
            next_day = next_day.strftime("%Y-%m-%d")

            if next_day in days:
                gcperiod_tmp["count"] = gcperiod_tmp["count"]+1
            else:
                gcperiod_tmp["end"] = day
                if gcperiod_tmp["count"] > gcperiod["count"]:
                    gcperiod = gcperiod_tmp
                ended = True
        ret["gcperiod"] = gcperiod

        nongcperiod = {"count":0, "start":"NA", "end":"NA"}
        (last,foo) = days.popitem()
        last    = datetime.datetime.strptime(last, "%Y-%m-%d")
        while len(days):
            (first,foo) = days.popitem()
            first    = datetime.datetime.strptime(first, "%Y-%m-%d")
            period = (last-first).days - 1
            if period > nongcperiod["count"]:
                nongcperiod["count"] = period
                nongcperiod["start"] = first + datetime.timedelta(1)
                nongcperiod["end"]   = last - datetime.timedelta(1)
            last = first
        ret["nongcperiod"] = nongcperiod

        return ret
