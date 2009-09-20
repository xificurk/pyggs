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

from . import base


class Plugin(base.Plugin):
    def __init__(self, master):
        # Run base.__init__
        base.Plugin.__init__(self, master)

        # Define list of all plugin names that we need to run this one.
        self.dependencies = ["stats", "myfinds"]

        # Brief info about plugin's function
        self.about = _("This plugin is just simple example.")


    def setup(self):
        """Setup script"""
        # This part will be called from setup.py script, you can interact with
        #   user and set up all neccessary options needed in run time.

        # Get config
        config = self.master.config

        # You should use only your plugin's namespace section.
        config.assertSection(self.NS)

        # Setup default values of some options.
        config.defaults[self.NS] = {}
        config.defaults[self.NS]["optionName"] = "value"

        # Now interact with user, and update values of some options.
        # You can add validate argument - if it is a list, value has to be from
        #   that list; if it is anything else then None, value has to be
        #   non-empty string
        config.update(self.NS, "optionName", "Text shown to user:")


    def prepare(self):
        """Setup everything needed before actual run"""
        # Run base.prepare
        base.Plugin.prepare(self)

        # Register custom parsers
        self.master.registerParser("myParserName", MyParserClass)

        # Register handlers for all kinds of parsers, e.g.
        self.master.registerHandler("myFinds", self.parseMyFinds)
        self.master.registerHandler("myParserName", self.parseMyParserName)

        # If your plugin needs some special storage facility, initialize it here
        self.storage = MyStorage()

        # Register pages you want to render to output directory
        self.master.registerPage("page.html", ":page_template", ":page_menu_template", self.templateData, layout=False):

        # You can also interact with dependency plugins via self.pluginName


    def run(self):
        """Run the plugin's code"""
        # Do whatever you need to prepare data for rendering
        # You can also interact with dependency plugins via self.pluginName
