# -*- coding: utf-8 -*-
"""
    plugins/gcczRatings.py - Downloads ratings from geocaching.cz.
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


class gcczRatings(base):
    def __init__(self, master):
        base.__init__(self, master)
        self.about = _("Global storage for ratings of caches from geocaching.cz.")


    def setup(self):
        config = self.master.config

        config.assertSection(self.NS)
        config.defaults[self.NS] = {}
        config.defaults[self.NS]["timeout"] = "7"
        config.update(self.NS, "timeout", _("Timeout for stored geocaching.cz ratings in days"))


    def prepare(self):
        base.prepare(self)
        self.storage = gcczRatingsDatabase(self, self.master.globalStorage)



class gcczRatingsDatabase(Storage):
    def __init__(self, plugin, database):
        self.NS = plugin.NS + ".db"
        self.log = logging.getLogger("Pyggs." + self.NS)
        self.plugin = plugin
        self.filename = database.filename

        self.valid = None

        self.createTables()


    def createTables(self):
        """If Ratings table doesn't exist, create it"""
        db = self.getDb()
        db.execute("""CREATE TABLE IF NOT EXISTS gcczRatings (
                waypoint varchar(9) NOT NULL,
                rating int(3) NOT NULL,
                count int(5) NOT NULL,
                PRIMARY KEY (waypoint))""")
        db.close()


    def checkValidity(self):
        """Checks, if the database data are not out of date"""
        if self.valid is not None:
            return self.valid

        lastCheck = self.getEnv(self.NS + ".lastcheck")
        timeout = int(self.plugin.master.config.get(self.plugin.NS, "timeout"))*3600*24
        if lastCheck is not None and float(lastCheck)+timeout >= time.time():
            self.valid = True
        else:
            self.log.info("Geocaching.cz Ratings database out of date, initiating refresh.")
            self.refresh()

        return self.valid


    def refresh(self):
        """Re-download ragings data"""
        data = {"a":"ctihodnoceni","v":"1"}
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
            self.log.error("Unable to load Geocaching.cz Ratings, extending validity of current data.")
            self.log.debug("Response: {0}".format(result))
        else:
            cur.execute("DELETE FROM gcczRatings")
            result = result[2].split(":",1)[-1]
            for row in result.split("|"):
                row = row.split(";")
                if len(row) >= 3:
                    cur.execute("INSERT INTO gcczRatings(waypoint, rating, count) VALUES(?,?,?)", (row[0], row[1], row[2]))
            self.log.info("Geocaching.cz Ratings database successfully updated.")

        db.commit()
        db.close()
        self.setEnv(self.NS + ".lastcheck", time.time())


    def select(self, waypoints, min=0):
        """Selects data from database, performs update if neccessary"""
        self.checkValidity()
        result = []
        db = self.getDb()
        cur = db.cursor()
        for wpt in waypoints:
            row = cur.execute("SELECT * FROM gcczRatings WHERE waypoint = ? AND count >= ?", (wpt,min)).fetchone()
            if row is not None:
                row = dict(row)
                result.append(row)
        db.close()

        return result
