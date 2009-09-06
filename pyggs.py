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

import logging, os, sys
from ColorConsole import ColorConsole
from optparse import OptionParser

from GCparser.GCparser import GCparser

import Configurator
import plugins

import gettext
langs = {}
langs["cs"] = gettext.translation("pyggs", localedir = os.path.dirname(__file__) + "/translations", codeset="utf-8", languages = ["cs"])
langs["en"] = gettext.translation("pyggs", localedir = os.path.dirname(__file__) + "/translations", codeset="utf-8", languages = ["en"])
langs["en"].install()


class Pyggs(object):
    def __init__(self):
        # Setup console output logging
        console = ColorConsole(fmt="%(levelname)-8s %(name)-20s %(message)s")
        rootlog = logging.getLogger("")
        rootlog.addHandler(console)
        rootlog.setLevel(logging.WARN)

        # Parse command line arguements
        optp = OptionParser()

        optp.add_option("-q","--quiet", help=_("set logging to ERROR"), action="store_const", dest="loglevel", const=logging.ERROR, default=logging.WARN)
        optp.add_option("-v","--verbose", help=_("set logging to INFO"), action="store_const", dest="loglevel", const=logging.INFO)
        optp.add_option("-d","--debug", help=_("set logging to DEBUG"), action="store_const", dest="loglevel", const=logging.DEBUG)
        optp.add_option("-D","--Debug", help=_("set logging to ALL"), action="store_const", dest="loglevel", const=0)

        optp.add_option("-w","--workdir", dest="workdir", default="~/.geocaching", help=_("set working directory, default is ~/.geocaching"))
        optp.add_option("-p","--profile", dest="profile", help=_("choose profile"))

        opts,args = optp.parse_args()

        rootlog.setLevel(opts.loglevel)
        self.log     = logging.getLogger("Pyggs")
        self.opts    = opts
        self.workDir = os.path.expanduser(opts.workdir)
        self.plugins = {}

        if self.opts.profile is None:
            self.log.error(_("You have to select a profile."))
            sys.exit()


    def setup(self):
        """Setup script"""
        # Setup working directory structure
        if not os.path.isdir(self.workDir):
            os.mkdir(self.workDir)
        if not os.path.isdir(self.workDir):
            self.log.critical(_("Unable to create working directory '%s'.") % self.workDir)
            sys.exit()

        parserDir = self.workDir + "/parser"
        if not os.path.isdir(parserDir):
            os.mkdir(parserDir)
        pyggsDir = self.workDir + "/pyggs"
        if not os.path.isdir(pyggsDir):
            os.mkdir(pyggsDir)
        if not os.path.isdir(parserDir) or not os.path.isdir(pyggsDir):
            self.log.critical(_("Unable to set up base directory structure in working directory write to working directory '%s'.") % self.workDir)
            sys.exit()

        self.log.info(_("Working directory is '%s'.") % self.workDir)

        profileDir = "%s/%s" %(pyggsDir, self.opts.profile)
        if not os.path.isdir(profileDir):
            os.mkdir(profileDir)
        if not os.path.isdir(profileDir):
            self.log.critical(_("Unable to create profile directory '%s'.") % profileDir)
            sys.exit()

        # Let's ask some questions and create config
        configFile = "%s/config.cfg" % profileDir
        self.config = config = Configurator.Profile(configFile)

        config.assertSection("global")
        globals()["langs"][config.get("global", "language")].install()
        print()
        config.update("global", "language", _("Please, select user interface language - %s.") % "/".join(globals()["langs"].keys()), validate = globals()["langs"].keys())
        globals()["langs"][config.get("global", "language")].install()

        gconfigFile = "%s/config.cfg" % pyggsDir
        gconfig = Configurator.Global(gconfigFile)

        gconfig.assertSection("plugins")
        print()
        print(_("Check if these are all installed plugins. You can enable/disable each of them for your profile later."))
        print(_("Please, use comma separated list."))
        gconfig.update("plugins", "list", _("Installed plugins"), validate = True)
        gconfig.save()
        gplugins = gconfig.getPlugins()

        print()
        print(_("Now, we're going to setup your profile named '%s'.") % self.opts.profile)

        config.assertSection("plugins")
        print("  %s:" % _("Plugins"))
        for plugin in gplugins:
            config.update("plugins", plugin, _("Enable '%s' plugin") % plugin, validate = ["y", "n"])
        for plugin in config.options("plugins"):
            if plugin not in gplugins:
                config.remove_option("plugins", plugin)

        config.assertSection("geocaching.com")
        print("  Geocaching.com:")
        config.update("geocaching.com", "username", _("Username"), validate = True)
        config.update("geocaching.com", "password", _("Password"), validate = True)

        print("  Checking plugins dependency tree...")
        self.loadPlugins()

        for plugin in self.plugins:
            print("  %s:" % _("Configuration of '%s' plugin") % plugin)
            self.plugins[plugin].setup(config)

        config.save()
        print()
        print(_("Note: You can always edit these setings by re-running setup.py script, or by hand in file %s.") % configFile)


    def run(self):
        """Run pyggs"""
        # Setup working directory structure
        if not os.path.isdir(self.workDir):
            self.log.critical(_("Working directory '%s' does not exist, please run setup.py script.") % self.workDir)
            sys.exit()

        parserDir = self.workDir + "/parser"
        pyggsDir = self.workDir + "/pyggs"
        if not os.path.isdir(parserDir) or not os.path.isdir(pyggsDir):
            self.log.critical(_("Working directory '%s' is not set up properly, please run setup.py script.") % self.workDir)
            sys.exit()

        self.log.info(_("Working directory is '%s'.") % self.workDir)

        configFile = "%s/%s/config.cfg" %(pyggsDir, self.opts.profile)
        if not os.path.isfile(configFile):
            self.log.critical(_("Configuration file not found for profile '%s', please run setup.py script.") % self.opts.profile)
            sys.exit()
        self.config = config = Configurator.Profile(configFile)

        self.GCparser = GCparser(username = config.get("geocaching.com", "username"), password = config.get("geocaching.com", "password"), dataDir = parserDir)

        self.checkPlugins()


    def loadPlugin(self, name):
        """ Load a plugin - name is the file and class name"""
        if name not in globals()['plugins'].__dict__:
            self.log.info(_("Loading plugin '%s'.") % name)
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

        for plugin in self.plugins:
            self.loadWithDeps(plugin)


    def loadWithDeps(self, name):
        """Load plugin and its dependencies"""
        if name not in self.plugins:
            self.loadPlugin(name)
            self.config.set("plugins", name, "y")
        for dep in self.plugins[name].dependencies:
            if dep not in self.plugins:
                self.log.warn(_("'%s' plugin pulled in as dependency by '%s'.") % (dep, name))
                self.loadWithDeps(dep)

if __name__ == '__main__':
    pyggs = Pyggs()
    pyggs.run()
