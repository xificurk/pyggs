# -*- coding: utf-8 -*-
"""
    plugins/gccz_ratings.py - Downloads ratings from geocaching.cz.
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

from . import base


class Plugin(base.Plugin):
    def __init__(self, master):
        base.Plugin.__init__(self, master)
        self.about = _("Global storage for ratings of caches from geocaching.cz.")


    def setup(self):
        config = self.master.config

        config.assertSection(self.NS)
        config.defaults[self.NS] = {}
        config.defaults[self.NS]["timeout"] = "7"
        config.update(self.NS, "timeout", _("Timeout for stored geocaching.cz ratings in days:"), validate=lambda val: None if val.isdigit() else _("Use only digits, please."))


    def prepare(self):
        base.Plugin.prepare(self)
        self.config["timeout"] = int(self.config["timeout"])
        self.storage = Storage(self.master.globalStorage.filename, self)



class Storage(base.Storage):
    def __init__(self, filename, plugin):
        base.Storage.__init__(self, filename, plugin)
        self.valid = None


    def createTables(self):
        """Create necessary tables"""
        base.Storage.createTables(self)
        self.query("""CREATE TABLE IF NOT EXISTS gccz_ratings (
                waypoint varchar(9) NOT NULL,
                rating int(3) NOT NULL,
                count int(5) NOT NULL,
                PRIMARY KEY (waypoint))""")


    def checkValidity(self):
        """Checks, if the database data are not out of date"""
        if self.valid is not None:
            return self.valid

        lastCheck = self.getEnv("lastcheck")
        timeout = self.plugin.config["timeout"]*3600*24
        if lastCheck is not None and float(lastCheck)+timeout >= time.time():
            self.valid = True
        else:
            self.log.info(_("Geocaching.cz Ratings database out of date, initiating refresh."))
            self.update()

        return self.valid


    def update(self):
        """Re-download ragings data"""
        data = {"a":"ctihodnoceni","v":"1"}
        reuslt = self.plugin.master.fetch("http://www.geocaching.cz/api.php", data=data)
        if result is None:
            self.log.error(_("Unable to load Geocaching.cz Ratings, extending validity of current data."))
            return

        result = result.read().decode("utf-8","replace").splitlines()

        succ = False
        for row in result:
            row = row.split(":")
            if row[0] == "info" and row[1] == "ok":
                succ = True
                break

        if not succ:
            self.log.error(_("Unable to load Geocaching.cz Ratings, extending validity of current data."))
            self.log.debug("Response: {0}".format(result))
            return

        db = self.getDb()
        cur = db.cursor()
        cur.execute("DELETE FROM gccz_ratings")
        result = result[2].split(":",1)[-1]
        for row in result.split("|"):
            row = row.split(";")
            if len(row) >= 3:
                cur.execute("INSERT INTO gccz_ratings(waypoint, rating, count) VALUES(?,?,?)", (row[0], row[1], row[2]))
        self.log.info(_("Geocaching.cz Ratings database successfully updated."))
        db.commit()
        db.close()
        self.setEnv("lastcheck", time.time())
        self.valid = True


    def getRatings(self, waypoints, min=0):
        """Selects data from database, performs update if neccessary"""
        self.checkValidity()
        result = []
        db = self.getDb()
        cur = db.cursor()
        for wpt in waypoints:
            row = cur.execute("SELECT * FROM gccz_ratings WHERE waypoint = ? AND count >= ?", (wpt,min)).fetchone()
            if row is not None:
                row = dict(row)
                result.append(row)
        db.close()

        return result
