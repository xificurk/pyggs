# -*- coding: utf-8 -*-
"""
    plugins/gcczMyRatings.py - Downloads user's ratings from geocaching.cz.
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
import time
import urllib

from .base import base
from pyggs import Storage


class gcczMyRatings(base):
    def __init__(self, master):
        base.__init__(self, master)
        self.dependencies = ["gccz"]
        self.about = _("Storage for user's ratings of caches from geocaching.cz.")


    def setup(self):
        config = self.master.config

        config.assertSection(self.NS)
        config.defaults[self.NS] = {}
        config.defaults[self.NS]["timeout"] = "24"
        config.update(self.NS, "timeout", _("Timeout for user's stored geocaching.cz ratings in hours"))


    def prepare(self):
        base.prepare(self)
        self.storage = gcczMyRatingsDatabase(self, self.master.profileStorage)



class gcczMyRatingsDatabase(Storage):
    def __init__(self, plugin, database):
        self.NS = plugin.NS + ".db"
        self.log = logging.getLogger("Pyggs." + self.NS)
        self.plugin = plugin
        self.filename = database.filename

        self.valid = None

        self.createTables()


    def createTables(self):
        """If gcczMyRatings table doesn't exist, create it"""
        db = self.getDb()
        db.execute("""CREATE TABLE IF NOT EXISTS gcczMyRatings (
                waypoint varchar(9) NOT NULL,
                myrating int(3) NOT NULL,
                PRIMARY KEY (waypoint))""")
        db.close()


    def checkValidity(self):
        """Checks, if the database data are not out of date"""
        if self.valid is not None:
            return self.valid

        lastCheck = self.getEnv(self.NS + ".lastcheck")
        timeout = int(self.plugin.master.config.get(self.plugin.NS, "timeout"))*3600
        if lastCheck is not None and float(lastCheck)+timeout >= time.time():
            self.valid = True
        else:
            self.log.info("Geocaching.cz MyRatings database out of date, initiating refresh.")
            self.refresh()

        return self.valid


    def refresh(self):
        """Re-download ragings data"""
        config = self.plugin.master.config
        data = {"a":"ctivlastnihodnoceni","v":"1","u":config.get(self.plugin.gccz.NS, "username"),"p":config.get(self.plugin.gccz.NS, "password")}
        result = urllib.request.urlopen("http://www.geocaching.cz/api.php", urllib.parse.urlencode(data))
        result = result.read().decode("utf-8","replace").splitlines()

        succ = False
        for row in result:
            row = row.split(":")
            if row[0] == "info" and row[1] == "ok":
                succ = True
                break

        db = self.getDb()
        cur = db.cursor()
        if succ is False:
            self.log.error("Unable to load Geocaching.cz MyRatings, extending validity of current data.")
            self.log.debug("Response: {0}".format(result))
        else:
            cur.execute("DELETE FROM gcczMyRatings")
            result = result[2].split(":",1)[-1]
            for row in result.split("|"):
                row = row.split(";")
                if len(row) >= 2:
                    cur.execute("INSERT INTO gcczMyRatings(waypoint, myrating) VALUES(?,?)", (row[0], row[1]))
            self.log.info("Geocaching.cz MyRatings database successfully updated.")

        db.commit()
        db.close()
        self.setEnv(self.NS + ".lastcheck", time.time())


    def select(self, waypoints):
        """Selects data from database, performs update if neccessary"""
        self.checkValidity()
        result = []
        db = self.getDb()
        cur = db.cursor()
        for wpt in waypoints:
            row = cur.execute("SELECT * FROM gcczMyRatings WHERE waypoint = ?", (wpt,)).fetchone()
            if row is not None:
                row = dict(row)
                result.append(row)
        db.close()

        return result
