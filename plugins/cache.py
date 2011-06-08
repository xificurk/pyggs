# -*- coding: utf-8 -*-
"""
    plugins/cache.py - handles global database of cache details.
    Copyright (C) 2009-2011 Petr Morávek

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

__version__ = "0.2.19"


import logging
import math
import time

from . import base
from versioning import VersionInfo


class Plugin(base.Plugin):
    _elevation_retry = 3
    _elevation_wait = 5

    def __init__(self, master):
        base.Plugin.__init__(self, master)
        self.version = VersionInfo(__version__)
        self.about = _("Global storage for detailed info about caches.")


    def setup(self):
        config = self.master.config

        config.assertSection(self.NS)
        config.defaults[self.NS] = {}
        config.defaults[self.NS]["timeout"] = "14"
        config.update(self.NS, "timeout", _("Cache details data timeout in days:"), validate=lambda val: None if val.isdigit() else _("Use only digits, please."))


    def onPyggsUpgrade(self, oldVersion):
        if oldVersion < "0.2.5":
            # fix cache types Uknown -> Mystery/Puzzle
            storage = self.master.globalStorage
            self.log.warn(_("Fixing change of cache type name Unknown - Mystery/Puzzle."))
            storage.query("UPDATE [cache] SET [type] = 'Mystery/Puzzle Cache' WHERE [type] = 'Unknown Cache'")
        if oldVersion < "0.2.10":
            # fix missing guid
            storage = self.master.globalStorage
            self.log.warn(_("Deleting data for caches with missing guid."))
            storage.query("DELETE FROM [cache] WHERE [guid] = '' OR [guid] IS NULL")
        if oldVersion < "0.2.16":
            # fix floating timeouts
            storage = self.master.globalStorage
            db = storage.getDb()
            cur = db.cursor()
            for cache in cur.execute("SELECT guid, lastCheck FROM cache").fetchall():
                cur.execute("UPDATE cache SET lastCheck = ? WHERE guid = ?", (int(float(cache["lastCheck"])), cache["guid"]))
            db.commit()
            db.close()
        return True


    def onPluginUpgrade(self, oldVersion):
        if oldVersion < "0.2":
            if self.storage.query("SELECT COUNT(*) AS [exists] FROM [sqlite_master] WHERE [type] = 'table' AND [name] = 'cache'")[0]["exists"] > 0:
                exists = False
                for row in self.storage.query("PRAGMA TABLE_INFO([cache])"):
                    if row["name"] == "elevation":
                        exists = True
                        break
                if not exists:
                    self.log.info(_("Creating column for elevation in cache database."))
                    self.storage.query("ALTER TABLE [cache] ADD COLUMN [elevation] int(5) NOT NULL DEFAULT -9999")
                self.log.warn(_("Updating cache database with elevation data... this may take a while."))
                for cache in self.storage.query("SELECT guid, lat, lon FROM [cache] WHERE [elevation] = -9999"):
                    elevation = self.getElevation(cache["lat"], cache["lon"])
                    if elevation is not None:
                        self.storage.query("UPDATE [cache] SET [elevation] = ? WHERE [guid] = ?", (elevation, cache["guid"]))
        elif oldVersion < "0.2.3":
            self.storage.query("UPDATE cache SET elevation = -9999 WHERE elevation <= -1000")
        return True


    def getElevation(self, lat, lon):
        elevation = None
        for i in range(self._elevation_retry):
            if i > 0:
                self.log.warn(_("Elevation data download failed, re-trying in {0} seconds...").format(self._elevation_wait))
                time.sleep(self._elevation_wait)
            data = self.master.fetch("http://ws.geonames.org/astergdem?lat={0}&lng={1}".format(lat, lon))
            if data is not None:
                data = data.strip()
                if data.isdigit() and int(data) > -1000:
                    elevation = int(data)
                    return elevation
        self.log.error(_("Elevation data download failed."))


    def prepare(self):
        self.storage = Storage(self.master.globalStorage.filename, self)
        base.Plugin.prepare(self)
        self.config["timeout"] = int(self.config["timeout"])

        self.homecoord = {}
        self.homecoord["lat"] = float(self.master.config.get("general", "homelat"))
        self.homecoord["lon"] = float(self.master.config.get("general", "homelon"))

        self.master.registerHandler("cache", self.parseCache)


    def parseCache(self, cache):
        """Update Cache database"""
        details = dict(cache)
        if "lat" in details and "lon" in details:
            elevation = self.getElevation(details["lat"], details["lon"])
            if elevation is not None:
                details["elevation"] = elevation
        self.log.info(_("Updating Cache database for {0}: {1}.").format(details.get("waypoint"), details.get("name")))
        self.storage.update(details)


    def distance(self, lat1, lon1, lat2=None, lon2=None):
        """Calculate distance from home coordinates"""
        if lat2 is None:
            lat2 = self.homecoord["lat"]
        if lon2 is None:
            lon2 = self.homecoord["lon"]

        lon1 = math.radians(lon1)
        lat1 = math.radians(lat1)
        lon2 = math.radians(lon2)
        lat2 = math.radians(lat2)
        d_lon = lon1 - lon2
        dist = math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(lat2) * math.cos(d_lon)
        dist = math.acos(dist) * 6371
        return dist



class Storage(base.Storage):
    def createTables(self):
        """Create necessary tables"""
        base.Storage.createTables(self)
        self.query("""CREATE TABLE IF NOT EXISTS cache (
                guid varchar(36) NOT NULL,
                waypoint varchar(9) NOT NULL,
                name varchar(255) NOT NULL,
                owner varchar(100) NOT NULL,
                owner_id varchar(36) NOT NULL,
                hidden date NOT NULL,
                type varchar(30) NOT NULL,
                country varchar(100) NOT NULL,
                province varchar(100) NOT NULL,
                lat decimal(9,6) NOT NULL,
                lon decimal(9,6) NOT NULL,
                difficulty decimal(2,1) NOT NULL,
                terrain decimal(2,1) NOT NULL,
                elevation int(5) NOT NULL DEFAULT -9999,
                size varchar(15) NOT NULL,
                disabled int(1) NOT NULL,
                archived int(1) NOT NULL,
                hint text,
                attributes text,
                lastCheck date NOT NULL,
                PRIMARY KEY (guid),
                UNIQUE (waypoint))""")
        self.query("""CREATE TABLE IF NOT EXISTS cache_visits (
                guid varchar(36) NOT NULL,
                type varchar(30) NOT NULL,
                count int(4),
                PRIMARY KEY (guid,type))""")
        self.query("""CREATE TABLE IF NOT EXISTS cache_inventory (
                guid varchar(36) NOT NULL,
                tbid varchar(36) NOT NULL,
                name varchar(100) NOT NULL,
                PRIMARY KEY (guid,tbid))""")


    def update(self, data):
        """Update Cache database by data"""
        if "guid" not in data:
            self.log.error(_("No guid passed, not updating."))
            return

        db = self.getDb()
        cur = db.cursor()

        cur.execute("DELETE FROM cache_inventory WHERE guid = ?", (data["guid"],))
        for tbid in data.get("inventory", {}):
            cur.execute("INSERT INTO cache_inventory(guid, tbid, name) VALUES(?,?,?)", (data["guid"], tbid, data["inventory"][tbid]))

        if len(data.get("visits", [])) > 0:
            cur.execute("DELETE FROM cache_visits WHERE guid = ?", (data["guid"],))
            for logtype in data["visits"]:
                cur.execute("INSERT INTO cache_visits(guid, type, count) VALUES(?,?,?)", (data["guid"], logtype, data["visits"][logtype]))

        old = cur.execute("SELECT * FROM cache WHERE guid=?", (data["guid"],)).fetchone()
        if old is None:
            sql = "INSERT INTO cache(guid, waypoint, name, owner, owner_id, hidden, type, country, province, lat, lon, difficulty, terrain, size, disabled, archived, hint, attributes, lastCheck, elevation) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
            sql_data = (data["guid"], data.get("waypoint", "GC"), data.get("name", ""), data.get("owner", ""), data.get("owner_id", ""), data.get("hidden", ""), data.get("type", ""), data.get("country", ""), data.get("province", ""), data.get("lat", ""), data.get("lon", ""), data.get("difficulty", ""), data.get("terrain", ""), data.get("size", ""), data.get("disabled", ""), data.get("archived", ""), data.get("hint", ""), data.get("attributes", ""), int(time.time()), data.get("elevation", -9999))
        else:
            update = {"lastCheck": int(time.time())}
            for k in ("waypoint", "name", "owner", "owner_id", "hidden", "type", "country", "province", "lat", "lon", "difficulty", "terrain", "size", "disabled", "archived", "hint", "attributes", "elevation"):
                if k in data:
                    update[k] = data[k]
                else:
                    self.log.debug("{0} not found in downloaded cache details.".format(k))
            sql = "UPDATE cache SET {0} = ? WHERE guid = ?".format(" = ?, ".join(update.keys()))
            sql_data = tuple(list(update.values()) + [data["guid"]])
        self.log.debug(sql)
        cur.execute(sql, sql_data)
        db.commit()
        db.close()


    def getDetails(self, guids):
        """Selects data from database, performs update if neccessary"""
        timeout = self.plugin.config["timeout"]*24*3600
        result = []
        db = self.getDb()
        cur = db.cursor()
        for guid in guids:
            row = cur.execute("SELECT * FROM cache WHERE guid = ?", (guid,)).fetchone()
            if row is None or (timeout + int(row["lastCheck"])) <= int(time.time()):
                self.log.debug("Data about cache guid {0} out of date, initiating refresh.".format(guid))
                self.plugin.master.parse("cache", guid)
                row = cur.execute("SELECT * FROM cache WHERE guid = ?", (guid,)).fetchone()
            row = dict(row)
            row["inventory"] = {}
            for inv in cur.execute("SELECT tbid, name FROM cache_inventory WHERE guid = ?", (guid,)).fetchall():
                row["inventory"][inv["tbid"]] = inv["name"]
            row["visits"] = {}
            for vis in cur.execute("SELECT type, count FROM cache_visits WHERE guid = ?", (guid,)).fetchall():
                row["visits"][vis["type"]] = int(vis["count"])
            result.append(row)
        db.close()

        return result
