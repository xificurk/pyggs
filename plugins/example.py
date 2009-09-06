# -*- coding: utf-8 -*-
"""
    plugins/example.py - Example dummy plugin.
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

class base(object):
    def __init__(self, master):
        # Let's define logging facility in Pyggs way.
        self.log = logging.getLogger("Pyggs.plugin.%s" % self.__class__.__name__)

        # Save reference to the Pyggs object.
        self.master = master

        # Define list of all plugin names that we need to run this one.
        self.dependencies = []

        # Prepare place for template data
        self.templateData = {}

    def setup(self):
        """Setup script"""
        # This part will be called from setup.py script, you can interact with
        #   user and set up all neccessary options needed in run time.

        # Get config
        config = self.master.config

        # You should use only your plugin's namespace section.
        NS = "pluginNS"
        config.assertSection(NS)

        # Setup default values of some options.
        config.defaults[NS] = {}
        config.defaults[NS]["optionName"] = "value"

        # Now interact with user, and update values of some options.
        # You can add validate argument - if it is a list, value has to be from
        #   that list; if it is anything else then None, value has to be
        #   non-empty string
        config.update(NS, "optionName", "Text shown to user: ")

    def prepare(self):
        """Setup everything needed before actual run"""
        # Log this
        self.log.info(_("Preparing plugin '%s'.") % self.__class__.__name__)

        # Register custom parsers
        self.master.registerParser("myParserName", MyParserClass)

        # Register handlers for all kinds of parsers, e.g.
        self.master.registerHandler("myFinds", self.parserMyFinds)
        self.master.registerHandler("myParserName", self.parserMyParserName)

        # If your plugin needs some special storage facility, initialize it here
        self.storage = MyStorage()

        # You can also interact with other plugins via self.master.plugins[name]

    def run(self):
        """Run the plugin's code"""
        # Do whatever you need to prepare data for rendering
        # You can also interact with other plugins via self.master.plugins[name]
        pass
