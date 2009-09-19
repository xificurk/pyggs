# -*- coding: utf-8 -*-
"""
    plugins/dtmatrix.py - difficulty-terrain matrix.
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
        base.Plugin.__init__(self, master)
        self.dependencies = ["stats", "cache", "myfinds"]
        self.about = _("Difficulty / Terrain matrix of found caches.")


    def run(self):
        myFinds = self.myfinds.storage.getList()
        caches = self.cache.storage.select(myFinds)
        templateData = self.getMatrix(caches)
        self.stats.registerTemplate(":stats.dtmatrix", templateData)


    def getMatrix(self, caches):
        totalfinds = len(caches)
        caches = self.cache.storage.fetchAssoc(caches, "terrain,difficulty,#")

        top = {"matrix":0, "sum":0}
        terrain = {}
        difficulty = {}
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
                except KeyError:
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

        result = {}
        result["matrix"] = dt
        result["difficulty"] = difficulty
        result["terrain"] = terrain
        result["top"] = top
        result["mean"] = mean
        return result
