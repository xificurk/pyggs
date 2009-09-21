# -*- coding: utf-8 -*-
"""
    plugins/base.py - Parent plugin for all others.
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

from collections import OrderedDict
import logging
import sqlite3


class Plugin(object):
    def __init__(self, master):
        self.NS = "plug." + self.__class__.__module__.split(".")[-1]
        self.log = logging.getLogger("Pyggs." + self.NS)
        self.master = master
        self.about = ""
        self.dependencies = []


    def prepare(self):
        for plugin in self.dependencies:
            self.__dict__[plugin] = self.master.plugins[plugin]
        self.config = {}
        if self.master.config.has_section(self.NS):
            for option in self.master.config.options(self.NS):
                self.config[option] = self.master.config.get(self.NS, option)


class Storage(object):
    def __init__(self, filename, plugin=None):
        if plugin is None:
            self.NS = "Storage"
        else:
            self.plugin = plugin
            self.NS = plugin.NS + ".db"
        self.log = logging.getLogger("Pyggs." + self.NS)
        self.filename = filename
        self.createTables()


    def getDb(self):
        """Return a new DB connection"""
        con = sqlite3.connect(self.filename)
        con.row_factory = sqlite3.Row
        return con


    def fetchAssoc(self, result, format="#"):
        """Fetch result to a dictionary"""
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
        """Perform query in current database"""
        db = self.getDb()
        result = db.cursor().execute(query, values).fetchall()
        db.commit()
        db.close()
        return result


    def createTables(self):
        """If Environment table doesn't exist, create it"""
        self.query("CREATE TABLE IF NOT EXISTS environment (variable VARCHAR(256) PRIMARY KEY, value VARCHAR(256))")


    def setEnv(self, variable, value):
        """insert or update env variale"""
        variable = self.NS + "." + variable
        db = self.getDb()
        cur = db.cursor()
        cur.execute("SELECT * FROM environment WHERE variable=?", (variable,))
        if (len(cur.fetchall()) > 0):
            cur.execute("UPDATE environment SET value=? WHERE variable=?", (value, variable))
        else:
            cur.execute("INSERT INTO environment(variable, value) VALUES(?, ?)", (variable, value))
        db.commit()
        db.close()


    def getEnv(self, variable):
        """get env variable"""
        variable = self.NS + "." + variable
        db = self.getDb()
        cur = db.cursor()
        cur.execute("SELECT value FROM environment WHERE variable=? LIMIT 1", (variable,))
        value = cur.fetchone()
        db.close()
        if value is not None:
            value = value[0]
        return value


    def delEnv(self, variable):
        """delete env variale"""
        variable = self.NS + "." + variable
        db = self.getDb()
        cur = db.cursor()
        cur.execute("DELETE FROM environment WHERE variable=? LIMIT 1", (variable,))
        db.commit()
        db.close()
