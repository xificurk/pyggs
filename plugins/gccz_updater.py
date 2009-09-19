# -*- coding: utf-8 -*-
"""
    plugins/gccz_updater.py - Updates MyFinds database at geocaching.cz.
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

from hashlib import md5
import urllib

from . import base


class Plugin(base.Plugin):
    def __init__(self, master):
        base.Plugin.__init__(self, master)
        self.dependencies = ["myfinds", "cache", "gccz"]
        self.about = _("Updates user's finds in geocaching.cz database.")


    def setup(self):
        config = self.master.config

        config.assertSection(self.NS)
        config.defaults[self.NS] = {}
        config.defaults[self.NS]["force"] = "n"
        config.update(self.NS, "force", _("Force my finds update on every run"), validate=["y","n"])


    def finish(self):
        finds = ""
        for row in self.myfinds.storage.select("SELECT date, guid FROM myFinds"):
            if len(finds) > 0:
                finds = finds + "|"
            details = self.cache.storage.select([row["guid"]])[0]
            finds = finds + "{1};{2};{3};{4}".format(details["waypoint"], row["date"], details["lat"], details["lon"])
        config = self.master.config

        hash = str(finds)
        hash = md5(hash.encode("utf-8")).hexdigest()
        if config.get(self.NS, "force") != "y":
            hash_old = self.master.profileStorage.getEnv(self.NS + ".hash")
            if hash == hash_old:
                self.log.info("Geocaching.cz database seems already up to date, skipping update.")
                return

        data = {"a":"nalezy","u":config.get(self.gccz.NS, "username"),"p":config.get(self.gccz.NS, "password"),"d":finds}
        result = urllib.request.urlopen("http://www.geocaching.cz/api.php", urllib.parse.urlencode(data))
        result = result.read().decode().splitlines()

        succ = False
        for row in result:
            row = row.split(":")
            if row[0] == "info" and row[1] == "ok":
                succ = True
                break

        if succ is False:
            self.log.error("Unable to update Geocaching.cz database.")
            self.log.debug("Response: {0}".format(result))
        else:
            self.master.profileStorage.setEnv(self.NS + ".hash", hash)
            self.log.info("Geocaching.cz database successfully updated.")
