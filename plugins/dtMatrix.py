# -*- coding: utf-8 -*-
"""
    plugins/dtMatrix.py - difficulty-terrain matrix.
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

class dtMatrix(object):
    def __init__(self, master):
        self.NS  = "plugin.dtMatrix"
        self.log = logging.getLogger("Pyggs.%s" % self.NS)
        self.master = master

        self.dependencies = ["base", "cache", "myFinds"]
        self.templateData = {}


    def setup(self):
        """Setup script"""
        pass


    def prepare(self):
        """Setup everything needed before actual run"""
        self.log.debug("Preparing...")


    def run(self):
        """Run the plugin's code"""
        self.log.info("Running...")

        myFinds = self.master.plugins["myFinds"].storage.getList()
        caches  = self.master.plugins["cache"].storage.select(myFinds)
        totalfinds = len(myFinds)
        caches = self.master.plugins["cache"].storage.database.fetchAssoc(caches, "terrain,difficulty,#")

        top = {}
        top["matrix"] = 0
        top["sum"]    = 0
        terrain       = {}
        difficulty    = {}
        mean = {"terrain":0, "difficulty":0}
        dt = {}

        t = 0.5
        while t < 5:
            t = t+0.5
            terrain[t] = 0
            dt[t] = {}
            d = 0.5
            while d < 5:
                d = d+0.5
                try:
                    dt[t][d] = len(caches[t][d])
                except:
                    dt[t][d] = 0
                if dt[t][d] > top["matrix"]:
                    top["matrix"] = dt[t][d]
                terrain[t] = terrain[t] + dt[t][d]

            if terrain[t] > top["sum"]:
                top["sum"] = terrain[t]
            mean["terrain"] = mean["terrain"] + terrain[t]*t;
        mean["terrain"] = mean["terrain"]/totalfinds

        d = 0.5
        while d < 5:
            d = d+0.5
            difficulty[d] = 0
            t = 0.5
            while t < 5:
                t = t+0.5
                difficulty[d] = difficulty[d] + dt[t][d]
            if difficulty[d] > top["sum"]:
                top["sum"] = difficulty[d]
            mean["difficulty"] = mean["difficulty"] + difficulty[d]*d;
        mean["difficulty"] = mean["difficulty"]/totalfinds

        self.templateData["matrix"]     = dt
        self.templateData["difficulty"] = difficulty
        self.templateData["terrain"]    = terrain
        self.templateData["top"]        = top
        self.templateData["mean"]       = mean
        self.master.plugins["base"].registerTemplate(":dtMatrix", self.templateData)
