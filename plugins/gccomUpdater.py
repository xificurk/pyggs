# -*- coding: utf-8 -*-
"""
    plugins/gccomUpdater.py - Updates generated profile at geocaching.com.
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

import logging, os
from hashlib import md5

class gccomUpdater(object):
    def __init__(self, master):
        self.NS  = "plugin.gccomUpdater"
        self.log = logging.getLogger("Pyggs.%s" % self.NS)
        self.master = master

        self.dependencies = ["base"]
        self.templateData = {}


    def setup(self):
        """Setup script"""
        config = self.master.config

        config.assertSection(self.NS)
        config.defaults[self.NS] = {}
        config.defaults[self.NS]["force"] = "n"
        config.update(self.NS, "force", _("Force geocaching.com profile update on every run"), validate=["y","n"])


    def prepare(self):
        """Setup everything needed before actual run"""
        self.log.debug("Preparing...")

    def run(self):
        pass


    def finish(self):
        """Run the plugin's code after rendering"""
        self.log.debug("Finishing...")

        file = "%s/%s" % (self.master.templar.outdir, "export.html")
        if not os.path.isfile(file):
            self.log.error("Export file not found.")
            return

        with open(file, "r") as fp:
            data = fp.read()

        config = self.master.config

        hash = data.splitlines()
        for line in hash:
            if line.find("<!-- pyggs[hashRemove] -->") != -1:
                hash.remove(line)
        hash = "\n".join(hash)
        hash = md5(hash.encode()).hexdigest()
        if config.get(self.NS, "force") != "y":
            hash_old = self.master.profileStorage.getE("%s.hash" % self.NS)
            if hash == hash_old:
                self.log.info("Geocaching.com profile seems already up to date, skipping update.")
                return

        data = data.replace("<!-- pyggs[hashRemove] -->", "")

        self.master.registerHandler("editProfile", self.update)
        self.master.parse("editProfile", data)
        self.master.profileStorage.setE("%s.hash" % self.NS, hash)


    def update(self, parser):
        """Updates profile data"""
        self.log.debug("Saving...")
        parser.save()