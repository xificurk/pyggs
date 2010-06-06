# -*- coding: utf-8 -*-
"""
    plugins/general.py - Prepare place to put general statistics.
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
        self.dependencies = ["stats"]
        self.about = _("Container for General statistics table.")

        self.templateData = {"templates":{}}


    def run(self):
        self.stats.registerTemplate(":stats.general", self.templateData)


    def registerTemplate(self, template, context):
        """Register template for rendering in General stats section"""
        self.templateData["templates"][template] = context
