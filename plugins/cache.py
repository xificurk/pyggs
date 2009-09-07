# -*- coding: utf-8 -*-
"""
    plugins/cache.py - handles global database of cache details.
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

class cache(object):
    def __init__(self, master):
        self.NS  = "plugin.cache"
        self.log = logging.getLogger("Pyggs.%s" % self.NS)
        self.master = master

        self.dependencies = []


    def setup(self):
        """Setup script"""
        pass


    def prepare(self):
        """Setup everything needed before actual run"""
        self.log.debug("Preparing...")

        self.master.registerHandler("cache", self.parseCache)
        self.storage = cacheDatabase(self, self.master.globalStorage)


    def run(self):
        """Run the plugin's code"""
        self.log.info("Running...")


    def parseCache(self, cache):
        """Update Cache database"""
        self.log.debug("Updating Cache database.")



class cacheDatabase(object):
    def __init__(self, plugin, database):
        self.NS       = "%s.C" % plugin.NS
        self.log      = logging.getLogger("Pyggs.%s" % self.NS)
        self.database = database
        self.plugin   = plugin

        self.createTables()


    def createTables(self):
        """If Environment table doesn't exist, create it"""
        db = self.database.getDb()
        db.execute("""CREATE TABLE IF NOT EXISTS cache (
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
