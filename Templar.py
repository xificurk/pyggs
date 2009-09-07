# -*- coding: utf-8 -*-
"""
    Templar.py - HTML&CSS templating engine above tenjin.
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

import logging, os.path, sys, re
from datetime import datetime

import Configurator

import tenjin
from tenjin.helpers import *

class Templar(tenjin.Engine):
    def __init__(self, master):
        self.log    = logging.getLogger("Pyggs.Templar")

        templateDir = None
        template = master.config.get("output", "template")
        if os.path.isdir("%s/pyggs/templates/%s" % (master.workDir, template)):
            templateDir = "%s/pyggs/templates/%s" % (master.workDir, template)
        elif os.path.isdir("%s/templates/%s" % (os.path.dirname(__file__), template)):
            templateDir = "%s/templates/%s" % (os.path.dirname(__file__), template)
        if templateDir is None:
            self.log.error(_("Template '%s' not found.") % template)
            master.die()

        tenjin.Engine.__init__(self, postfix = ".pyhtml", layout = ":@layout", path = [templateDir])
        self.theme  = Theme(master)
        self.outdir = os.path.expanduser(master.config.get("output", "directory"))
        if not os.path.isdir(self.outdir):
            self.log.error(_("Invalid output directory '%s'.") % self.outdir)
            master.die()


    def include(self, template_name, append_to_buf=True, context = None):
        """This allows to pass different context to the subtemplate"""
        frame = sys._getframe(1)
        locals  = frame.f_locals
        globals = frame.f_globals
        assert '_context' in locals
        if context is None:
            context = locals['_context']
        else:
            self.hook_context(context)
        # context and globals are passed to get_template() only for preprocessing.
        template = self.get_template(template_name, context, globals)
        if append_to_buf:  _buf = locals['_buf']
        else:              _buf = None
        return template.render(context, globals, _buf=_buf)


    def outputPages(self, pages):
        """Render and save all pages"""
        for output in pages:
            globals = {"escape":escape, "to_str":to_str, "echo":echo, "css_header":self.theme.cssHeader, "css":self.theme.css, "gradient":self.theme.cssGradient, "date":self.formatDate, "dateRange":self.dateRange}
            context = pages[output]["context"]
            context["pages"] = pages
            result = self.render(pages[output]["template"], context, globals = globals, layout = pages[output]["layout"])
            with open("%s/%s" % (self.outdir, output), "w") as fp:
                fp.write(result)
                fp.flush()


    def formatDate(self, value = None, format = "%(day)d.&nbsp;%(month)d.&nbsp;%(year)d"):
        """Return date in string fromat"""
        if type(value) is str:
            value = datetime.strptime(value, "%Y-%m-%d")
        elif type(value) is int:
            value = datetime.fromtimestamp(value)
        elif value is None:
            value = datetime.today()

        return format % {"year":value.year, "month":value.month, "day":value.day, "hour":value.hour, "minute":value.minute}


    def dateRange(self, start, end = None):
        """Returns date range in string format"""
        if type(start) is str:
            start = datetime.strptime(start, "%Y-%m-%d")
        elif type(start) is int:
            start = datetime.fromtimestamp(start)
        elif start is None:
            start = datetime.today()

        if end is None:
            return self.formatDate(start, "%(day)d.&nbsp;%(month)d.&nbsp;%(year)d")
        elif type(end) is str:
            end = datetime.strptime(end, "%Y-%m-%d")
        elif type(end) is int:
            end = datetime.fromtimestamp(end)

        if self.formatDate(start, "%(year)d-%(month)d") == self.formatDate(end, "%(year)d-%(month)d"):
            string = self.formatDate(start, "%(day)d.");
        elif self.formatDate(start, "%(year)d") == self.formatDate(end, "%(year)d"):
            string = self.formatDate(start, "%(day)d.&nbsp;%(month)d.")
        else:
            string = self.formatDate(start, "%(day)d.&nbsp;%(month)d.&nbsp;%(year)d")
        string = "%s&nbsp;– %s" % (string, self.formatDate(end, "%(day)d.&nbsp;%(month)d.&nbsp;%(year)d"))

        return string



class Theme(Configurator.Theme):
    def __init__(self, master):
        themeFile = None
        theme = master.config.get("output", "theme")
        if os.path.isfile("%s/pyggs/themes/%s.theme" % (master.workDir, theme)):
            themeFile = "%s/pyggs/themes/%s.theme" % (master.workDir, theme)
        elif os.path.isfile("%s/themes/%s.theme" % (os.path.dirname(__file__), theme)):
            themeFile = "%s/themes/%s.theme" % (os.path.dirname(__file__), theme)
        if themeFile is None:
            self.log.error(_("Theme '%s' not found.") % theme)
            master.die()

        Configurator.Theme.__init__(self, themeFile)


    def css(self, classes):
        """Merge definitions from classe and return them"""
        if type(classes) is str:
            classes = [classes]
        all = {}
        for cl in classes:
            tomerge = {}
            if type(cl) is dict:
                tomerge = cl
            else:
                for property in self.options(cl):
                    tomerge[property] = self.get(cl, property)
            for property in tomerge:
                if property in all.keys():
                    del(all[property])
                if tomerge[property] != "inherit":
                    all[property] = tomerge[property]

        ret = ""
        for property in all:
            ret = "%s%s:%s;" % (ret, property, all[property])

        if len(ret):
            return " style=\"%s\"" % ret 


    def cssHeader(self):
        """Render common styles in the header"""
        ret = ""
        for option in self.options("@screen"):
            ret = "%s\n%s {%s}" % (ret, option, self.get("@screen", option))
        return ret


    def cssGradient(self, color1, color2, share):
        """Return color between color1 and color2 according to share"""
        colors = self.options("@colors")
        if color1 in colors:
            color1 = self.get("@colors", color1)
        if color2 in colors:
            color2 = self.get("@colors", color2)

        match1 = re.search("rgb\(\s*([0-9]+)\s*,\s*([0-9]+)\s*,\s*([0-9]+)\s*\)", color1)
        match2 = re.search("rgb\(\s*([0-9]+)\s*,\s*([0-9]+)\s*,\s*([0-9]+)\s*\)", color2)

        if not match1:
            self.log.error("Cannost parse color '%s'." % color1)
            return "inherit"
        if not match2:
            self.log.error("Cannost parse color '%s'." % color2)
            return "inherit"

        share = max(0, min(float(share), 1))

        red   = (1-share)*float(match1.group(1)) + share*float(match2.group(1))
        green = (1-share)*float(match1.group(2)) + share*float(match2.group(2))
        blue  = (1-share)*float(match1.group(3)) + share*float(match2.group(3))

        return "rgb(%d, %d, %d)" % (red, green, blue)
