# -*- coding: utf-8 -*-
"""
    Configurator.py - Configuration storage.
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

import sys, os, logging, configparser

class BaseConfig(configparser.RawConfigParser):
    def __init__(self, configFile):
        self.log = logging.getLogger("Pyggs.Config")
        configparser.RawConfigParser.__init__(self)

        self.defaults = {}

        self.configFile = configFile
        if os.path.isfile(configFile):
            self.read(configFile)

    def save(self):
        """Save config to a file"""
        with open(self.configFile, "w") as cfp:
            self.write(cfp)

    def get(self, section, option):
        """Get section->option, from config, or self.defaults"""
        try:
            value = configparser.RawConfigParser.get(self, section, option)
        except:
            try:
                value = self.defaults[section][option]
            except:
                value = ""
        return value

    def assertSection(self, section):
        """Add section, if not present"""
        try:
            self.add_section(section)
        except:
            pass

    def update(self, section, option, prompt, validate = None):
        """Update option via user input"""
        default = self.get(section, option)
        value = input("    %s [%s]: " % (prompt, default))
        if len(value) == 0:
            value = default

        if type(validate) is list and value not in validate:
            print(_("ERROR: You have to input a value from %s.") % validate)
            self.update(section, option, prompt, validate)
        elif validate is not None and len(value) == 0:
            print(_("ERROR: You have to input a non-empty string."))
            self.update(section, option, prompt, validate)
        else:
            self.set(section, option, value)

        return self.get(section, option)



class Profile(BaseConfig):
    def __init__(self, configFile):
        BaseConfig.__init__(self, configFile)

        # set default values
        self.defaults["global"] = {}
        self.defaults["global"]["language"] = "en"
        self.defaults["plugins"] = {}
        self.defaults["plugins"]["base"] = "y"



class Global(BaseConfig):
    def __init__(self, configFile):
        BaseConfig.__init__(self, configFile)
        # set default values
        self.defaults["plugins"] = {}
        self.defaults["plugins"]["list"] = "base"


    def getPlugins(self):
        """Returns stripped list of plugins"""
        plugins = []
        for plugin in self.get("plugins", "list").split(","):
            plugins.append(plugin.strip())
        return plugins