# -*- coding: utf-8 -*-
"""
    plugins/base.py - Parent plugin for all others.
    Copyright (C) 2009-2010 Petr Morávek

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

from collections import OrderedDict
import logging
import sqlite3

from libs.versioning import VersionInfo


class Plugin(object):
    def __init__(self, master):
        self.NS = "plug." + self.__class__.__module__.split(".")[-1]
        self.log = logging.getLogger("Pyggs." + self.NS)
        self.master = master
        self.about = ""
        self.dependencies = []
        self.version = VersionInfo("0")


    def prepare(self):
        # Do we need to run upgrade script?
        pyggsVersion = self.master.profileStorage.getVersion("pyggs", self)
        if self.master.version > pyggsVersion:
            upgraded = True
            if hasattr(self, "onPyggsUpgrade"):
                self.log.info(_("Upgrading plugin data from Pyggs version {0} to {1}.").format(pyggsVersion, self.master.version))
                upgraded = self.onPyggsUpgrade(pyggsVersion)
            if not upgraded:
                self.log.critical(_("Upgrade script failed."))
            else:
                self.master.profileStorage.setVersion("pyggs", self.master.version, self)
        pluginVersion = self.master.profileStorage.getVersion("plugin", self)
        if self.version > pluginVersion:
            upgraded = True
            if hasattr(self, "onPluginUpgrade"):
                self.log.info(_("Upgrading plugin data from plugin version {0} to {1}.").format(pluginVersion, self.version))
                upgraded = self.onPluginUpgrade(pluginVersion)
            if not upgraded:
                self.log.critical(_("Upgrade script failed."))
            else:
                self.master.profileStorage.setVersion("plugin", self.version, self)

        # Map the dependencies
        for plugin in self.dependencies:
            self.__dict__[plugin] = self.master.plugins[plugin]

        # Load config
        self.config = {}
        if self.master.config.has_section(self.NS):
            for option in self.master.config.options(self.NS):
                self.config[option] = self.master.config.get(self.NS, option)


class Storage(object):
    def __init__(self, filename, plugin=None):
        if plugin is None:
            self.log = logging.getLogger("Pyggs.db")
            self.NS = ""
        else:
            self.plugin = plugin
            self.log = logging.getLogger("Pyggs." + plugin.NS + ".db")
            self.NS = plugin.NS + "."
        self.filename = filename
        self.createTables()


    def getDb(self):
        """ Return a new DB connection.
        """
        con = sqlite3.connect(self.filename)
        con.row_factory = sqlite3.Row
        return con


    def fetchAssoc(self, result, format="#"):
        """ Fetch result to a dictionary.
        """
        if format == "":
            format = "#"
        format = format.split(",")

        if len(result) == 0:
            if format[0] == "#":
                return []
            else:
                return OrderedDict()

        for field in format:
            if field != "#" and field not in result[0].keys():
                self.log.error("There is no field '{0}' in the result set.".format(field))
                return []

        # make associative tree
        data = OrderedDict()
        data["result"] = None
        for row in result:
            x = data
            i = "result"
            for field in format:
                if field == "#":
                    if x[i] is None:
                        x[i] = []
                    x[i].append(None)
                    x = x[i]
                    i = len(x)-1
                else:
                    if x[i] is None:
                        x[i] = OrderedDict()
                    if x[i].get(row[field]) is None:
                        x[i][row[field]] = None
                    x = x[i]
                    i = row[field]
            x[i] = dict(row)

        return data["result"]


    def query(self, query, values=()):
        """ Perform query in current database.
        """
        db = self.getDb()
        result = db.cursor().execute(query, values).fetchall()
        db.commit()
        db.close()
        return result


    def createTables(self):
        """ If Environment table doesn't exist, create it.
        """
        self.query("CREATE TABLE IF NOT EXISTS environment (variable VARCHAR(256) PRIMARY KEY, value VARCHAR(256))")


    def setEnv(self, variable, value):
        """ Insert or update environment variale.
        """
        variable = self.NS + variable
        self.query("INSERT OR REPLACE INTO environment(variable, value) VALUES(?, ?)", (variable, value))


    def getEnv(self, variable):
        """ Get environment variable.
        """
        variable = self.NS + variable
        value = self.query("SELECT value FROM environment WHERE variable=? LIMIT 1", (variable,))
        if len(value) > 0:
            value = value[0]["value"]
        else:
            value = None
        return value


    def delEnv(self, variable):
        """ Delete environment variable.
        """
        variable = self.NS + variable
        self.query("DELETE FROM environment WHERE variable=?", (variable,))


    def getVersion(self, type, plugin=None):
        """ Get stored version of pyggs, or plugin from plugin's namespace.
        """
        if plugin is not None:
            namespace = plugin.NS + "."
        else:
            namespace = ""

        version = self.getEnv("{0}version.{1}".format(namespace, type.lower()))
        if version is None:
            version = "0"
        return VersionInfo(version)


    def setVersion(self, type, version, plugin=None):
        """ Store version of pyggs, or plugin to plugin's namespace.
        """
        if plugin is not None:
            namespace = plugin.NS + "."
        else:
            namespace = ""

        self.setEnv("{0}version.{1}".format(namespace, type.lower()), str(version))
