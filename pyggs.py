#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    pyggs.py - base script for Pyggs.
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

import logging, os, sqlite3
from ColorConsole import ColorConsole
from optparse import OptionParser

from GCparser.GCparser import GCparser

from Templar import Templar
import Configurator
import plugins

import gettext
# Autodetect translations
localeDir = os.path.dirname(__file__) + "/translations"
langs = {}
for lang in os.listdir(localeDir):
    if os.path.isdir("%s/%s" % (localeDir, lang)):
        langs[lang] = gettext.translation("pyggs", localedir = localeDir, codeset="utf-8", languages = [lang])
gettext.install("pyggs", localedir = localeDir, codeset="utf-8")

class Pyggs(GCparser):
    def __init__(self):
        # Setup console output logging
        console = ColorConsole(fmt="%(levelname)-8s %(name)-30s %(message)s")
        rootlog = logging.getLogger("")
        rootlog.addHandler(console)
        rootlog.setLevel(logging.WARN)

        # Parse command line arguements
        optp = OptionParser()
        optp.add_option("-q","--quiet", help=_("set logging to ERROR"), action="store_const", dest="loglevel", const=logging.ERROR, default=logging.WARN)
        optp.add_option("-v","--verbose", help=_("set logging to INFO"), action="store_const", dest="loglevel", const=logging.INFO)
        optp.add_option("-d","--debug", help=_("set logging to DEBUG"), action="store_const", dest="loglevel", const=logging.DEBUG)
        optp.add_option("-D","--Debug", help=_("set logging to ALL"), action="store_const", dest="loglevel", const=0)
        optp.add_option("-w","--workdir", dest="workdir", default="~/.geocaching", help=_("set working directory, default is %s") % "~/.geocaching")
        optp.add_option("-p","--profile", dest="profile", help=_("choose profile"))
        self.opts,args = optp.parse_args()

        rootlog.setLevel(self.opts.loglevel)
        self.log = logging.getLogger("Pyggs")

        if self.opts.profile is None:
            self.log.error(_("You have to select a profile."))
            self.die()

        self.workDir = os.path.expanduser(self.opts.workdir)
        self.plugins = {}


    def setup(self):
        """Setup script"""
        # Setup working directory structure
        if not os.path.isdir(self.workDir):
            os.mkdir(self.workDir)
        if not os.path.isdir(self.workDir):
            self.log.critical(_("Unable to create working directory '%s'.") % self.workDir)
            self.die()

        parserDir = self.workDir + "/parser"
        if not os.path.isdir(parserDir):
            os.mkdir(parserDir)
        pyggsDir = self.workDir + "/pyggs"
        if not os.path.isdir(pyggsDir):
            os.mkdir(pyggsDir)
        if not os.path.isdir(parserDir) or not os.path.isdir(pyggsDir):
            self.log.critical(_("Unable to set up base directory structure in working directory '%s'.") % self.workDir)
            self.die()

        self.log.info("Working directory is '%s'." % self.workDir)

        profileDir = "%s/%s" %(pyggsDir, self.opts.profile)
        if not os.path.isdir(profileDir):
            os.mkdir(profileDir)
        if not os.path.isdir(profileDir):
            self.log.critical(_("Unable to create profile directory '%s'.") % profileDir)
            self.die()

        # Let's ask some questions and create config
        configFile = "%s/config.cfg" % profileDir
        self.config = config = Configurator.Profile(configFile)
        langs = globals()["langs"]
        lang = config.get("general", "language")
        if lang:
            langs[lang].install()

        print()
        print(_("Now, we're going to setup your profile named '%s'.") % self.opts.profile)

        config.assertSection("general")
        print()
        print("  %s:" % _("General options"))
        config.update("general", "language", _("Please, select user interface language"), validate = list(langs.keys()))
        langs[config.get("general", "language")].install()

        installedPlugins = []
        for plugin in os.listdir(os.path.dirname(__file__) + "/plugins"):
            if plugin[-3:] == ".py" and not plugin.startswith("__init__") and not plugin.startswith("example"):
                installedPlugins.append(plugin[:-3])

        config.assertSection("plugins")
        print()
        print("  %s:" % _("Plugins"))
        for plugin in installedPlugins:
            config.update("plugins", plugin, _("Enable '%s' plugin") % plugin, validate = ["y", "n"])
        for plugin in config.options("plugins"):
            if plugin not in installedPlugins:
                logging.debug("Removing not installed plugin %s." % plugin)
                config.remove_option("plugins", plugin)

        config.assertSection("geocaching.com")
        print()
        print("  Geocaching.com:")
        config.update("geocaching.com", "username", _("Username"), validate = True)
        config.update("geocaching.com", "password", _("Password"), validate = True)

        templates = []
        if os.path.isdir(pyggsDir + "/templates"):
            for template in os.listdir(pyggsDir + "/templates"):
                if os.path.isdir(pyggsDir + "/templates/" + template):
                    templates.append(template)
        for template in os.listdir(os.path.dirname(__file__) + "/templates"):
            if os.path.isdir(os.path.dirname(__file__) + "/templates/" + template):
                templates.append(template)
        themes = []
        if os.path.isdir(pyggsDir + "/themes"):
            for theme in os.listdir(pyggsDir + "/themes"):
                if os.path.isfile(pyggsDir + "/themes/" + theme):
                    themes.append(theme.replace(".theme", ""))
        for theme in os.listdir(os.path.dirname(__file__) + "/themes"):
            if os.path.isfile(os.path.dirname(__file__) + "/themes/" + theme):
                themes.append(theme.replace(".theme", ""))
        config.assertSection("output")
        print()
        print("  %s:" % _("Output"))
        print("    %s:\n      * %s\n      * %s" % (_("Templates are looked up in these directories (consecutively)"), pyggsDir + "/templates", os.path.dirname(__file__) + "/templates"))
        config.update("output", "template", _("Template"), validate = templates)
        print("    %s:\n      * %s\n      * %s" % (_("Themes are looked up in these directories (consecutively)"), pyggsDir + "/themes", os.path.dirname(__file__) + "/themes"))
        config.update("output", "theme", _("Theme"), validate = themes)
        config.update("output", "directory", _("Directory"), validate = True)

        print()
        print("  Checking plugins dependency tree...")
        self.loadPlugins()

        for plugin in self.plugins:
            print()
            print("  %s:" % _("Configuration of '%s' plugin") % plugin)
            self.plugins[plugin].setup()

        config.save()
        print()
        print(_("Note: You can always edit these setings by re-running setup.py script, or by hand in file %s.") % configFile)


    def run(self):
        """Run pyggs"""
        # Setup working directory structure
        parserDir = self.workDir + "/parser"
        pyggsDir = self.workDir + "/pyggs"
        profileDir = "%s/%s" %(pyggsDir, self.opts.profile)
        if not os.path.isdir(self.workDir) or not os.path.isdir(parserDir) or not os.path.isdir(pyggsDir) or not os.path.isdir(profileDir):
            self.log.error(_("Working directory '%s' is not set up properly, please run setup.py script.") % self.workDir)
            self.die()

        self.log.info("Working directory is '%s'." % self.workDir)

        configFile = "%s/config.cfg" % profileDir
        if not os.path.isfile(configFile):
            self.log.error(_("Configuration file not found for profile '%s', please run setup.py script.") % self.opts.profile)
            self.die()
        self.config = config = Configurator.Profile(configFile)

        # Init GCparser, and redefine again self.log
        GCparser.__init__(self, username = config.get("geocaching.com", "username"), password = config.get("geocaching.com", "password"), dataDir = parserDir)
        self.log = logging.getLogger("Pyggs")

        self.globalStorage  = Storage("%s/storage.db" % pyggsDir)
        self.profileStorage = Storage("%s/storage.db" % profileDir)

        self.handlers = {}
        self.pages    = {}
        self.loadPlugins()
        self.makeDepTree()

        # Prepare plugins
        for plugin in self.depTree:
            self.plugins[plugin].prepare()

        # Run plugins
        for plugin in self.depTree:
            self.plugins[plugin].run()

        # Render output
        templar = Templar(self)
        templar.outputPages(self.pages)


    def registerPage(self, output, template, menutemplate, context, layout = True):
        """Register page for rendering"""
        self.pages[output] = {"template":template, "menu":menutemplate, "context":context, "layout":layout}


    def registerHandler(self, parsername, handler):
        """Register handler that gets Parser object, when parse() method is called"""
        try:
            self.handlers[parsername].append(handler)
        except KeyError:
            self.handlers[parsername] = []
            self.handlers[parsername].append(handler)


    def parse(self, name, *args, **kwargs):
        """Create parser and return it to every registered handler"""
        handlers = self.handlers.get(name)
        if handlers is not None:
            parser = GCparser.parse(self, name, *args, **kwargs)
            for handler in handlers:
                handler(parser)


    def loadPlugin(self, name):
        """ Load a plugin - name is the file and class name"""
        if name not in globals()['plugins'].__dict__:
            self.log.info("Loading plugin '%s'." % name)
            __import__(self.pluginModule(name))
        self.plugins[name] = getattr(globals()['plugins'].__dict__[name], name)(self)
        return True


    def pluginModule(self, name):
        return "%s.%s" % (globals()['plugins'].__name__, name)


    def loadPlugins(self):
        """Loads all plugins and their dependencies"""
        for plugin in self.config.options("plugins"):
            if self.config.get("plugins", plugin) == "y":
                self.loadPlugin(plugin)

        for plugin in list(self.plugins.keys()):
            self.loadWithDeps(plugin)


    def loadWithDeps(self, name):
        """Load plugin and its dependencies"""
        if name not in self.plugins:
            self.loadPlugin(name)
            self.config.set("plugins", name, "y")
        for dep in self.plugins[name].dependencies:
            if dep not in self.plugins:
                self.log.warn("'%s' plugin pulled in as dependency by '%s'." % (dep, name))
                self.loadWithDeps(dep)


    def makeDepTree(self):
        """Rearragne the order of self.plugins according to dependencies"""
        self.depTree = []
        plugins = list(self.plugins.keys())

        fs = 0
        while len(plugins):
            fs = fs +1
            if fs > 100:
                self.log.warn("Cannot make plugin depedency tree for %s. Possible circular dependencies." % ",".join(plugins))
                self.depTree.extend(plugins)

            for plugin in list(plugins):
                if self.pluginDepsLoaded(self.depTree, self.plugins[plugin].dependencies):
                    self.log.debug("Adding plugin '%s' to the deptree." % plugin)
                    plugins.remove(plugin)
                    self.depTree.append(plugin)


    def pluginDepsLoaded(self, loaded, dependencies):
        """Are all required dependencies of plugin in loaded?"""
        ret = True
        for dep in dependencies:
            if dep not in loaded:
                ret = False
                break
        return ret



class Storage(object):
    def __init__(self, filename):
        self.log = logging.getLogger("Pyggs.Storage")
        self.filename = filename
        self.createEnvironment()


    def getDb(self):
        """Return a new DB connection"""
        con = sqlite3.connect(self.filename)
        con.row_factory = sqlite3.Row
        return con

    def fetchAssoc(self, cursor, format = "#"):
        """Fetch result to a dictionary"""
        if format == "":
            format = "#"
        format = format.split(",")

        row = cursor.fetchone()
        if row is None:
            return []

        for field in format:
            if field != "#" and field not in row.keys():
                self.log.error("There is no field '%s' in the result set." % field)
                return []

        # make associative tree
        data = {"result":None}
        while row:
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
                        x[i] = {}
                    try:
                        foo = x[i][row[field]]
                    except:
                        x[i][row[field]] = None
                    x = x[i]
                    i = row[field]
            x[i] = {}
            for k in row.keys():
                x[i][k] = row[k]
            row = cursor.fetchone()
        return data["result"]


    def createEnvironment(self):
        """If Environment table doesn't exist, create it"""
        db = self.getDb()
        db.execute("CREATE TABLE IF NOT EXISTS environment (variable VARCHAR(256) PRIMARY KEY, value VARCHAR(256))")
        db.close()


    def setE(self, variable, value):
        """insert or update env variale"""
        db = self.getDb()
        cur = db.cursor()
        cur.execute("SELECT * FROM environment WHERE variable=?", (variable,))
        if (len(cur.fetchall()) > 0):
            cur.execute("UPDATE environment SET value=? WHERE variable=?", (value, variable))
        else:
            cur.execute("INSERT INTO environment(variable, value) VALUES(?,?)", (variable, value))
        db.commit()
        db.close()


    def getE(self, variable):
        """get env variable"""
        db = self.getDb()
        cur = db.cursor()
        cur.execute("SELECT value FROM environment WHERE variable=? LIMIT 1", (variable,))
        value = cur.fetchone()
        db.close()
        if value is not None:
            value = value[0]
        return value


    def delE(self, variable):
        """delete env variale"""
        db = self.getDb()
        cur = db.cursor()
        cur.execute("DELETE FROM environment WHERE variable=? LIMIT 1", (variable,))
        db.commit()
        db.close()




if __name__ == '__main__':
    pyggs = Pyggs()
    pyggs.run()
