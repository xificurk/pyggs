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

import logging


class base(object):
    def __init__(self, master):
        self.NS = "plug." + self.__class__.__name__
        self.log = logging.getLogger("Pyggs." + self.NS)
        self.master = master
        self.about = ""
        self.dependencies = []


    def prepare(self):
        for plugin in self.dependencies:
            self.__dict__[plugin] = self.master.plugins[plugin]
