# -*- coding: utf-8 -*-
"""
    plugins/base.py - standard set of stats.
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

class base(object):
    def __init__(self, master):
        self.log = logging.getLogger("Pyggs.plugin.base")
        self.master = master

        self.dependencies = []
        self.templateData = {}


    def setup(self):
        """Setup script"""
        config = self.master.config
        NS = "plugin_base"

        config.assertSection(NS)

        config.defaults[NS] = {}
        config.defaults[NS]["myFinds_TO"] = "24"
        config.update(NS, "myFinds_TO", _("'My Finds' data timeout in hours"))

    def prepare(self):
        """Setup everything needed before actual run"""
        self.log.info("Preparing plugin '%s'." % self.__class__.__name__)

        self.master.registerHandler("myFinds", self.parseMyFinds)
        self.master.registerHandler("cache", self.parseCache)

        self.storage = {}
        self.storage["myFinds"] = myFindsDatabase(self, self.master.profileStorage)
        self.storage["cache"]   = cacheDatabase(self, self.master.globalStorage)


    def run(self):
        """Run the plugin's code"""
        self.log.info("Running plugin '%s'." % self.__class__.__name__)
        self.templateData['overall']    = self.storage["myFinds"].getAverages()


    def parseMyFinds(self, myFinds):
        """Update MyFinds database"""
        self.log.debug("Updating MyFinds database.")
        myFinds = myFinds.getList()
        #TODO: user corrections
        self.storage["myFinds"].update(myFinds)


    def parseCache(self, cache):
        """Update Cache database"""
        self.log.debug("Updating Cache database.")



class myFindsDatabase(object):
    def __init__(self, plugin, database):
        self.log = logging.getLogger("Pyggs.plugin.base.MF")
        self.database = database
        self.plugin   = plugin
        self.valid    = None

        self.createTables()


    def createTables(self):
        """If Environment table doesn't exist, create it"""
        db = self.database.getDb()
        db.execute("""CREATE TABLE IF NOT EXISTS base_myFinds (
                guid varchar(36) NOT NULL,
                sequence int(4) NOT NULL,
                date date NOT NULL,
                PRIMARY KEY (guid,sequence))""")
        db.close()


    def checkValidity(self):
        """Checks, if the database data are not out of date"""
        if self.valid is not None:
            return self.valid

        lastCheck = self.database.getE("base_myFinds_lastcheck")
        timeout   = int(self.plugin.master.config.get("plugin_base", "myFinds_TO"))*3600
        if lastCheck is not None and float(lastCheck)+timeout >= time.time():
            self.valid = True
        else:
            self.log.info("MyFinds database out of date, initiating refresh.")
            self.plugin.master.parse("myFinds")

        return self.valid

    def update(self, data):
        """Update MyFinds database by data"""
        db = self.database.getDb()
        cur = db.cursor()
        cur.execute("DELETE FROM base_myFinds")
        for find in data:
            print(find)
            cur.execute("INSERT INTO base_myFinds(guid, sequence, date) VALUES(?,?,?)", (find["guid"], find["sequence"], find["f_date"]))
        db.commit()
        db.close()
        self.database.setE("base_myFinds_lastcheck", time.time())


    def getAverages(self, where = "1", period = None):
        """return averages stats"""
        self.checkValidity()

        db = self.database.getDb()
        cur = db.cursor()
        result = cur.execute("SELECT * FROM base_myFinds WHERE %s ORDER BY date ASC, sequence ASC" % where)
        all    = self.database.fetchAssoc(result)
        result = cur.execute("SELECT * FROM base_myFinds WHERE %s ORDER BY date ASC, sequence ASC" % where)
        days   = self.database.fetchAssoc(result, "date")
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



class cacheDatabase(object):
    def __init__(self, plugin, database):
        self.log = logging.getLogger("Pyggs.plugin.base.C")
        self.database = database
        self.plugin   = plugin

        self.createTables()


    def createTables(self):
        """If Environment table doesn't exist, create it"""
        db = self.database.getDb()
        db.execute("""CREATE TABLE IF NOT EXISTS base_cache (
                waypoint varchar(9) NOT NULL,
                gid varchar(36) NOT NULL,
                name varchar(255) NOT NULL,
                author varchar(100) NOT NULL,
                placed date NOT NULL,
                type varchar(30) NOT NULL,
                country varchar(100) NOT NULL,
                province varchar(100) NOT NULL,
                lat decimal(9,6) NOT NULL,
                lon decimal(9,6) NOT NULL,
                difficulty decimal(2,1) NOT NULL,
                terrain decimal(2,1) NOT NULL,
                size varchar(15) NOT NULL,
                archived int(1) NOT NULL,
                rating int(3) default NULL,
                count int(4) default NULL,
                PRIMARY KEY (waypoint),
                UNIQUE (gid))""")
        db.close()
