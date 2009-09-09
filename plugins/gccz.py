# -*- coding: utf-8 -*-
"""
    plugins/gccz.py - This plugin just stores credentials for geocaching.cz.
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

class gccz(object):
    def __init__(self, master):
        self.NS  = "plugin.gccz"
        self.log = logging.getLogger("Pyggs.%s" % self.NS)
        self.master = master

        self.dependencies = []
        self.templateData = {}


    def setup(self):
        """Setup script"""
        config = self.master.config

        config.assertSection(self.NS)
        config.update(self.NS, "username", _("Geocaching.cz username"), validate=True)
        config.update(self.NS, "password", _("Geocaching.cz password"), validate=True)
        config.update(self.NS, "uid", _("UID (for map generating)"), validate=True)


    def prepare(self):
        """Setup everything needed before actual run"""
        self.log.debug("Preparing...")


    def run(self):
        """Run the plugin's code"""
        self.log.info("Running...")
