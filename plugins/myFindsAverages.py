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

import logging, time, math

class myFindsAverages(object):
    def __init__(self, master):
        self.NS  = "plugin.myFindsAverages"
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
        self.templateData["overall"] = self.getAverages()
        self.templateData["last365"] = self.getAverages("date > DATE('now', '-365 days')", 365);
        self.master.plugins["general"].registerTemplate(":myFindsAverages", self.templateData)


    def getAverages(self, where = "1", period = None):
        """return averages stats"""
        myFindsDB = self.master.plugins["myFinds"].storage
        myFindsDB.checkValidity()

        db = myFindsDB.database.getDb()
        cur = db.cursor()
        result = cur.execute("SELECT * FROM myFinds WHERE %s ORDER BY date ASC, sequence ASC" % where).fetchall()
        all    = myFindsDB.database.fetchAssoc(result)
        days   = myFindsDB.database.fetchAssoc(result, "date")
        db.close()

        ret = {}
        ret["finds"] = len(all);
        ret["gcdays"] = len(days);

        if period is None:
            start  = days.pop(list(days.keys())[0])
            start  = start["date"]
            period = int(math.ceil((time.time()-time.mktime(time.strptime(start, "%Y-%m-%d")))/24/3600+1))

        ret["days"] = period;
        ret["gcdays/week"] = "%.2f" % (ret["gcdays"]/period*7)
        ret["finds/gcday"] = "%.2f" % (ret["finds"]/max(ret["gcdays"],1))
        ret["finds/day"]   = "%.2f" % (ret["finds"]/period)
        ret["finds/week"]  = "%.2f" % (ret["finds"]/period*7)
        ret["finds/month"] = "%.2f" % (ret["finds"]/period*365.12/12)

        return ret