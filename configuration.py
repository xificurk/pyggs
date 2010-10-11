# -*- coding: utf-8 -*-
"""
    configuration.py - configuration tools.
    Copyright (C) 2010 Petr Morávek

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

import configparser
import logging
import os.path

import libs.console as console


class BaseConfig(configparser.RawConfigParser):
    def __init__(self, configFile):
        self.log = logging.getLogger("Pyggs.Config")
        configparser.RawConfigParser.__init__(self)

        # Let's make option names case-sensitive
        self.optionxform = str

        self.defaults = {}

        self.configFile = configFile
        if os.path.isfile(configFile):
            self.load(configFile)


    def save(self):
        """ Save config to a file.
        """
        with open(self.configFile, "w", encoding="utf-8") as cfp:
            self.write(cfp)


    def load(self, configFile):
        """ Load config from a file.
        """
        with open(configFile, encoding="utf-8") as cfp:
            self.readfp(cfp)


    def get(self, section, option):
        """ Get section->option from config, or self.defaults.
        """
        try:
            value = configparser.RawConfigParser.get(self, section, option)
        except (configparser.NoSectionError, configparser.NoOptionError):
            try:
                value = self.defaults[section][option]
            except KeyError:
                value = ""
        return value


    def assertSection(self, section):
        """ Add section if not present.
        """
        try:
            self.add_section(section)
        except configparser.DuplicateSectionError:
            pass


    def update(self, section, option, prompt, validate=None):
        """ Update option via user input.
        """
        default = self.get(section, option)
        value = console.prompt(prompt, padding=2, default=default, validate=validate)
        self.set(section, option, value)
        return self.get(section, option)



class ProfileConfig(BaseConfig):
    def __init__(self, configFile):
        BaseConfig.__init__(self, configFile)
        self.log = logging.getLogger("Pyggs.ProfileConfig")

        # set default values
        self.defaults["output"] = {}
        self.defaults["output"]["template"] = "default.en"
        self.defaults["output"]["theme"] = "default"
        self.defaults["plugins"] = {}
        self.defaults["plugins"]["stats"] = "y"
        self.defaults["plugins"]["general"] = "y"
        self.defaults["plugins"]["myfinds_averages"] = "y"