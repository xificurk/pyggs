# -*- coding: utf-8 -*-
"""
    plugins/gccom_updater.py - Updates generated profile at geocaching.com.
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
import os.path

from . import base


class Plugin(base.Plugin):
    def __init__(self, master):
        base.Plugin.__init__(self, master)
        self.dependencies = ["stats"]
        self.about = _("Updates geocaching.com profile with generated statistics.")


    def setup(self):
        config = self.master.config

        config.assertSection(self.NS)
        config.defaults[self.NS] = {}
        config.defaults[self.NS]["force"] = "n"
        config.update(self.NS, "force", _("Force geocaching.com profile update on every run ({CHOICES})?"), validate=["y", "n"])


    def prepare(self):
        base.Plugin.prepare(self)
        if self.config["force"] == "y":
            self.config["force"] = True
        else:
            self.config["force"] = False


    def finish(self):
        file = os.path.join(self.master.outDir, "export.html")
        if not os.path.isfile(file):
            self.log.error(_("Export file not found."))
            return

        with open(file, "r", encoding="utf-8") as fp:
            data = fp.read()

        hash = data.splitlines()
        for line in hash:
            if line.find("<!-- pyggs[hashRemove] -->") != -1:
                hash.remove(line)
        hash = "\n".join(hash)
        hash = md5(hash.encode("utf-8")).hexdigest()
        if not self.config["force"]:
            hashOld = self.master.profileStorage.getEnv(self.NS + ".hash")
            if hash == hashOld:
                self.log.info(_("Geocaching.com profile seems already up to date, skipping update."))
                return

        data = data.replace("<!-- pyggs[hashRemove] -->", "")

        self.master.registerHandler("editProfile", self.update)
        self.master.parse("editProfile", data)
        self.master.profileStorage.setEnv(self.NS + ".hash", hash)


    def update(self, parser):
        """Updates profile data"""
        self.log.debug("Saving...")
        parser.save()
