# -*- coding: utf-8 -*-
"""
    plugins/myFinds.py - handles myFinds database for each profile.
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

import logging, time

class myFinds(object):
    def __init__(self, master):
        self.NS  = "plugin.myFinds"
        self.log = logging.getLogger("Pyggs.%s" % self.NS)
        self.master = master

        self.dependencies = []


    def setup(self):
        """Setup script"""
        config = self.master.config

        config.assertSection(self.NS)
        config.defaults[self.NS] = {}
        config.defaults[self.NS]["timeout"] = "24"
        config.update(self.NS, "timeout", _("'My Finds' data timeout in hours"))

    def prepare(self):
        """Setup everything needed before actual run"""
        self.log.debug("Preparing...")

        self.master.registerHandler("myFinds", self.parseMyFinds)
        self.storage = myFindsDatabase(self, self.master.profileStorage)


    def run(self):
        """Run the plugin's code"""
        self.log.info("Running...")


    def parseMyFinds(self, myFinds):
        """Update MyFinds database"""
        self.log.info("Updating MyFinds database.")
        myFinds = myFinds.getList()
        #TODO: user corrections
        self.storage.update(myFinds)



class myFindsDatabase(object):
    def __init__(self, plugin, database):
        self.NS       = "%s.MF" % plugin.NS
        self.log      = logging.getLogger("Pyggs.%s" % self.NS)
        self.database = database
        self.plugin   = plugin

        self.valid    = None

        self.createTables()


    def createTables(self):
        """If Environment table doesn't exist, create it"""
        db = self.database.getDb()
        db.execute("""CREATE TABLE IF NOT EXISTS myFinds (
                guid varchar(36) NOT NULL,
                sequence int(4) NOT NULL,
                date date NOT NULL,
                PRIMARY KEY (guid,sequence))""")
        db.close()


    def checkValidity(self):
        """Checks, if the database data are not out of date"""
        if self.valid is not None:
            return self.valid

        lastCheck = self.database.getE("%s.lastcheck" % self.NS)
        timeout   = int(self.plugin.master.config.get(self.plugin.NS, "timeout"))*3600
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
        cur.execute("DELETE FROM myFinds")
        for find in data:
            cur.execute("INSERT INTO myFinds(guid, sequence, date) VALUES(?,?,?)", (find["guid"], find["sequence"], find["f_date"]))
        db.commit()
        db.close()
        self.database.setE("%s.lastcheck" % self.NS, time.time())


    def select(self, query):
        """Selects data from database, performs update if neccessary"""
        self.checkValidity()
        db     = self.database.getDb()
        result = db.cursor().execute(query).fetchall()
        db.close()
        return result
