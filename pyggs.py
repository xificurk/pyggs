#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    pyggs.py - base script for Pyggs.
    Copyright (C) 2009-2011 Petr Morávek

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

__version__ = "0.2.21"


from collections import OrderedDict
import gettext
import logging
from optparse import IndentedHelpFormatter
from optparse import OptionParser
import os
import platform
import re
from shutil import rmtree
import sys
import urllib.request

sys.path.insert(0, os.path.join(sys.path[0], "libs"))

from configuration import ProfileConfig
from output import Templar, Theme
import console as console
import gcparser as gcparser
from versioning import VersionInfo

from plugins.base import Storage
import plugins

# Autodetect translations
localeDir = os.path.join(os.path.dirname(__file__), "locale")
langs = {}
for lang in os.listdir(localeDir):
    if os.path.isdir(os.path.join(localeDir, lang)):
        langs[lang] = gettext.translation("pyggs", localedir=localeDir, codeset="utf-8", languages=[lang])
gettext.install("pyggs", localedir=localeDir, codeset="utf-8")


class Pyggs(object):
    def __init__(self, workDir, profile):
        self.log = logging.getLogger("Pyggs")
        self.version = VersionInfo(__version__)
        self.workDir = workDir
        self.profile = profile
        self.config = ProfileConfig(os.path.join(workDir, "pyggs", "profiles", profile, "config.ini"))
        self.plugins = {}
        self.templateDirs = [os.path.join(self.workDir, "pyggs", "templates"), os.path.join(os.path.abspath(os.path.dirname(__file__)), "templates")]
        self.themeDirs = [os.path.join(self.workDir, "pyggs", "themes"), os.path.join(os.path.abspath(os.path.dirname(__file__)), "themes")]
        # Set prefered language
        langs = globals()["langs"]
        lang = self.config.get("general", "language")
        if len(lang) > 0 and lang in langs:
            langs[lang].install()


    def interactiveSetup(self):
        """ Interactive setup script.
        """
        print()
        console.writeln(_("Entering setup menu for profile {0}.").format(self.profile), console.color("G", True, ""))
        self.setupWorkDir()

        choice = ""
        choices = []
        choices.append(_("Exit"))
        choices.append(_("General options"))
        choices.append("Geocaching.com")
        choices.append(_("Output"))
        choices.append(_("Enable/Disable plugins"))
        choices.append(_("Plugins settings"))
        while choice != choices[0]:
            print()
            console.writeln(_("Main menu"), console.color("RB", True, ""))
            choice = console.menu(_("Action:"), choices)
            if choice == choices[1]:
                self.setupGeneral()
            elif choice == choices[2]:
                self.setupGeocachingCom()
            elif choice == choices[3]:
                self.setupOutput()
            elif choice == choices[4]:
                self.setupPlugins()
            elif choice == choices[5]:
                self.setupPluginsSettings()
        self.setupEnd()


    def fullSetup(self):
        """ Full setup script.
        """
        print()
        console.writeln(_("Entering full setup for profile {0}.").format(self.profile), console.color("G", True, ""))
        self.setupWorkDir()
        self.setupGeneral()
        self.setupGeocachingCom()
        self.setupOutput()
        self.setupPlugins()
        self.setupEnd()


    def setupWorkDir(self):
        """ Setup structure of working directory.
        """
        self.log.debug("Setting up base working directory structure.")
        if not os.path.isdir(self.workDir):
            os.makedirs(self.workDir, 0o750)
        if not os.path.isdir(self.workDir):
            self.log.critical(_("Unable to create working directory {0}.").format(self.workDir))

        parserDir = os.path.join(self.workDir, "parser")
        if not os.path.isdir(parserDir):
            os.mkdir(parserDir, 0o750)
        pyggsDir = os.path.join(self.workDir, "pyggs")
        if not os.path.isdir(pyggsDir):
            os.mkdir(pyggsDir, 0o750)
        profilesDir = os.path.join(pyggsDir, "profiles")
        if not os.path.isdir(profilesDir):
            os.mkdir(profilesDir, 0o750)
        if not os.path.isdir(parserDir) or not os.path.isdir(pyggsDir) or not os.path.isdir(profilesDir):
            self.log.critical(_("Unable to set up base directory structure in working directory {0}.").format(self.workDir))

        self.log.info(_("Working directory is {0}.").format(self.workDir))

        profileDir = os.path.join(profilesDir, self.profile)
        if not os.path.isdir(profileDir):
            os.mkdir(profileDir)
        if not os.path.isdir(profileDir):
            self.log.critical(_("Unable to create profile directory {0}.").format(profileDir))


    def setupGeneral(self):
        """ Config: general section
        """
        config = self.config
        config.assertSection("general")
        print()
        console.writeln(_("General options"), console.color("G", True, ""))

        langs = globals()["langs"]
        config.update("general", "language", _("Please, select user interface language ({CHOICES})."), validate=list(langs.keys()))
        langs[config.get("general", "language")].install()

        print("    " + _("Enter your home coordinates in degrees as decimal number (N means positive value, S negative; E means positive value, W negative)."))
        config.update("general", "homelat", _("Latitude:"), validate=lambda val: None if re.search("^-?[0-9]+\.?[0-9]*$", val) is not None else _("Please, use decimal number."))
        config.update("general", "homelon", _("Longitude:"), validate=lambda val: None if re.search("^-?[0-9]+\.?[0-9]*$", val) is not None else _("Please, use decimal number."))
        config.save()


    def setupGeocachingCom(self):
        """ Config: geocaching.com section
        """
        config = self.config
        config.assertSection("geocaching.com")
        print()
        console.writeln("Geocaching.com", console.color("G", True, ""))

        config.update("geocaching.com", "username", _("Username:"), validate=True)
        config.update("geocaching.com", "password", _("Password:"), validate=True)
        config.save()


    def setupOutput(self):
        """ Config: output section
        """
        config = self.config
        config.assertSection("output")
        print()
        console.writeln(_("Output"), console.color("G", True, ""))

        templates = self.detectTemplates()
        print("    " + _("Templates are looked up in these directories (consecutively):") + "\n      * " + "\n      * ".join(self.templateDirs))
        config.update("output", "template", _("Template ({CHOICES}):"), validate=templates)

        themes = self.detectThemes()
        print("    " + _("Themes are looked up in these directories (consecutively):") + "\n      * " + "\n      * ".join(self.themeDirs))
        config.update("output", "theme", _("Theme ({CHOICES}):"), validate=themes)

        config.update("output", "directory", _("Output directory:"), validate=lambda val: None if os.path.isdir(os.path.expanduser(val)) else _("You have to input existing directory."))
        config.save()


    def setupPlugins(self):
        """ Config: plugins section
        """
        config = self.config
        config.assertSection("plugins")
        print()
        console.writeln(_("Plugins"), console.color("G", True, ""))

        # Remove not installed plugins
        installedPlugins = self.detectPlugins()
        for plugin in config.options("plugins"):
            if plugin not in installedPlugins:
                logging.debug("Removing not installed plugin {0}.".format(plugin))
                config.remove_option("plugins", plugin)
        # Setup new found plugins
        for plugin in installedPlugins:
            if plugin not in config.options("plugins"):
                self.loadPlugin(plugin)
                console.writeln("  " + _("Plugin") + " " + plugin + ": " + self.plugins[plugin].about, console.color("G", False, ""))
                config.update("plugins", plugin, _("Enable") + " " + plugin + " ({CHOICES})?", validate=["y", "n"])
                if config.get("plugins", plugin) == "y":
                    self.setupPluginsEnable(plugin)
                print()
        config.save()

        plugins = config.options("plugins")
        plugins.sort()
        while True:
            choices = []
            choices.append(_("Exit"))
            for plugin in plugins:
                self.loadPlugin(plugin)
                if config.get("plugins", plugin) == "y":
                    choices.append("[x] {0:25s} {1}".format(plugin, self.plugins[plugin].about))
                else:
                    choices.append("[ ] {0:25s} {1}".format(plugin, self.plugins[plugin].about))
            print()
            console.writeln("  " + _("Enable/Disable plugins menu"), console.color("RB", False, ""))
            choice = console.menu(_("Plugins:"), choices, padding=1)
            if choice == choices[0]:
                break
            plugin = plugins[choices.index(choice) - 1]
            if config.get("plugins", plugin) == "y":
                block = []
                for bl in plugins:
                    if plugin in self.plugins[bl].dependencies:
                        block.append(bl)
                if len(block) > 0:
                    self.log.error(_("Cannot disable plugin {0}, because {1} depend on it.").format(plugin, ", ".join(block)))
                else:
                    print("  " + _("Disabling plugin {0}.").format(plugin))
                    config.set("plugins", plugin, "n")
            else:
                print("  " + _("Enabling plugin {0}.").format(plugin))
                config.set("plugins", plugin, "y")
                self.setupPluginsEnable(plugin)
            config.save()


    def setupPluginsEnable(self, plugin):
        """ Enable and setup plugin with all dependencies
        """
        if hasattr(self.plugins[plugin], "setup"):
            console.write("  " + _("Configuration of") + " ", console.color("GB", False, ""))
            console.writeln(plugin, console.color("GB", True, ""))
            self.plugins[plugin].setup()

        loaded = []
        for plugin in self.config.options("plugins"):
            if self.config.get("plugins", plugin) == "y":
                loaded.append(plugin)
        deps = self.findDeps(loaded)
        for plugin in deps:
            self.log.warn(_("Plugin {0} pulled in as dependency.").format(plugin))
            self.config.set("plugins", plugin, "y")
        for plugin in deps:
            self.setupPluginsEnable(plugin)
        self.config.save()


    def setupPluginsSettings(self):
        """ Config of every enabled plugin
        """
        config = self.config
        choices = []
        choices.append(_("Exit"))
        plugins = config.options("plugins")
        plugins.sort()
        for plugin in list(plugins):
            self.loadPlugin(plugin)
            if hasattr(self.plugins[plugin], "setup"):
                choices.append("{0:25s} {1}".format(plugin, self.plugins[plugin].about))
            else:
                plugins.remove(plugin)
        while True:
            print()
            console.writeln("  " + _("Plugins settings menu"), console.color("RB", False, ""))
            choice = console.menu(_("Plugins:"), choices, padding=1)
            if choice == choices[0]:
                break
            plugin = plugins[choices.index(choice) - 1]
            console.write("  " + _("Configuration of") + " ", console.color("GB", False, ""))
            console.writeln(plugin, console.color("GB", True, ""))
            self.plugins[plugin].setup()
            config.save()


    def setupEnd(self):
        """ Save config, etc
        """
        self.config.save()
        with open(os.path.join(self.workDir, "pyggs", "version"), "w") as fp:
            fp.write(__version__)
        with open(os.path.join(self.workDir, "pyggs" , "profiles", self.profile, "version"), "w") as fp:
            fp.write(__version__)
        print()
        console.writeln(_("Note: You can always edit these setings by running pyggs with --setup (-s) switch."), console.color("G", True, ""))


    def run(self):
        """ Run pyggs
        """
        config = self.config
        # Init GCparser, and redefine again self.log
        gcparser.HTTPInterface.set_data_dir(os.path.join(self.workDir, "parser"))
        gcparser.HTTPInterface.set_credentials(gcparser.Credentials(config.get("geocaching.com", "username"), password=config.get("geocaching.com", "password")))

        self.parsers = {}
        self.parsers["cache"] = gcparser.CacheDetails().get
        self.parsers["myFinds"] = gcparser.MyGeocachingLogs().get_finds
        self.parsers["editProfile"] = gcparser.Profile().update

        self.globalStorage = Storage(os.path.join(self.workDir, "pyggs", "storage.sqlite"))
        self.profileStorage = Storage(os.path.join(self.workDir, "pyggs", "profiles", profile, "storage.sqlite"))

        self.handlers = {}
        self.pages = {}
        self.loadPlugins()
        self.makeDepTree()

        # Prepare plugins
        for plugin in self.plugins:
            if hasattr(self.plugins[plugin], "prepare"):
                self.log.info(_("Preparing plugin {0}...").format(plugin))
                self.plugins[plugin].prepare()

        # Run plugins
        for plugin in self.plugins:
            if hasattr(self.plugins[plugin], "run"):
                self.log.info(_("Running plugin {0}...").format(plugin))
                self.plugins[plugin].run()

        # Render output
        self.outDir = os.path.abspath(os.path.expanduser(self.config.get("output", "directory")))
        if not os.path.isdir(self.outDir):
            self.log.critical(_("Invalid ouput directory {0}.").format(self.outDir))
        templar = Templar(self.getTemplate(), self.getTheme(), self.outDir)
        templar.outputPages(self.pages)

        # Finish plugins
        for plugin in self.plugins:
            if hasattr(self.plugins[plugin], "finish"):
                self.log.info(_("Finishing plugin {0}...").format(plugin))
                self.plugins[plugin].finish()


    def registerPage(self, output, template, menutemplate, context, layout=True):
        """ Register page for rendering.
        """
        self.pages[output] = {"template":template, "menu":menutemplate, "context":context, "layout":layout}


    def registerHandler(self, parsername, handler):
        """ Register handler that gets Parser object, when parse() method is called.
        """
        try:
            self.handlers[parsername].append(handler)
        except KeyError:
            self.handlers[parsername] = []
            self.handlers[parsername].append(handler)


    def parse(self, name, *args, **kwargs):
        """ Create parser and return it to every registered handler.
        """
        handlers = self.handlers.get(name)
        if handlers is not None:
            result = self.parsers[name](*args, **kwargs)
            for handler in handlers:
                handler(result)


    def loadPlugin(self, name):
        """ Load a plugin - name is the file and class name.
        """
        if name not in globals()["plugins"].__dict__:
            self.log.info(_("Loading plugin {0}.").format(name))
            __import__("{0}.{1}".format(globals()["plugins"].__name__, name))
        if name not in self.plugins:
            self.plugins[name] = getattr(globals()["plugins"].__dict__[name], "Plugin")(self)


    def loadPlugins(self):
        """ Loads all plugins and their dependencies.
        """
        for plugin in self.config.options("plugins"):
            if self.config.get("plugins", plugin) == "y":
                self.loadPlugin(plugin)
        deps = self.findDeps(list(self.plugins.keys()))
        if len(deps) > 0:
            self.log.critical(_("Missing dependencies {0}.").format(", ".join(deps)))


    def findDeps(self, plugins):
        """ Finds all dependencies that are not loaded.
        """
        result = []
        for plugin in plugins:
            self.loadPlugin(plugin)
            result.extend(self.findPluginDeps(plugins, self.plugins[plugin].dependencies))
        return list(set(result))


    def findPluginDeps(self, loaded, deps):
        """ findDeps recursive callback
        """
        result = list(deps)
        for plugin in deps:
            if plugin in loaded:
                result.remove(plugin)
            else:
                self.loadPlugin(plugin)
                result.extend(self.findPluginDeps(loaded, self.plugins[plugin].dependencies))
        return list(set(result))


    def makeDepTree(self):
        """ Rearragne the order of self.plugins according to dependencies.
        """
        plugins = OrderedDict()
        fs = 0
        while len(self.plugins):
            fs = fs +1
            if fs > 100:
                self.log.warn(_("Cannot make plugin depedency tree for {0}. Possible circular dependencies.").format(",".join(list(self.plugins.keys()))))
                for plugin in list(self.plugins.keys()):
                    plugins[plugin] = self.plugins.pop(plugin)

            for plugin in list(self.plugins.keys()):
                if len(self.findPluginDeps(list(plugins.keys()), self.plugins[plugin].dependencies)) == 0:
                    plugins[plugin] = self.plugins.pop(plugin)

        self.plugins = plugins


    def detectTemplates(self):
        """ Search for available templates.
        """
        templates = []
        for dir in self.templateDirs:
            if os.path.isdir(dir):
                for template in os.listdir(dir):
                    if os.path.isdir(os.path.join(dir, template)):
                        templates.append(template)
        templates.sort()
        return templates


    def getTemplate(self):
        """ Find directory of selected template.
        """
        template = self.config.get("output", "template")
        for dir in self.templateDirs:
            if os.path.isdir(os.path.join(dir, template)):
                return os.path.join(dir, template)
        self.log.critical(_("Cannot find template {0}.").format(template))


    def detectThemes(self):
        """ Search for available themes.
        """
        themes = []
        for dir in self.themeDirs:
            if os.path.isdir(dir):
                for theme in os.listdir(dir):
                    if os.path.isfile(os.path.join(dir, theme)):
                        themes.append(theme.replace(".theme", ""))
        themes.sort()
        return themes


    def getTheme(self):
        """ Find file of selected theme.
        """
        theme = self.config.get("output", "theme")
        for dir in self.themeDirs:
            if os.path.isfile(os.path.join(dir, theme + ".theme")):
                return os.path.join(dir, theme + ".theme")
        self.log.critical(_("Cannot find theme {0}.").format(theme))


    def detectPlugins(self):
        """ Search for available plugins.
        """
        plugins = []
        for plugin in os.listdir(os.path.join(os.path.dirname(__file__), "plugins")):
            if plugin.endswith(".py") and not plugin.startswith("__init__") and not plugin.startswith("example") and plugin[:-3] != "base":
                plugins.append(plugin[:-3])
        plugins.sort()
        return plugins


    def fetch(self, url, data=None, timeout=20):
        self.log.debug("Downloading {0}".format(url))
        try:
            if data is not None:
                data = urllib.parse.urlencode(data).encode("utf-8")
            response = urllib.request.urlopen(url, data=data, timeout=timeout)
            responseData = response.read()
        except IOError:
            self.log.error(_("Could not fetch URL {0}.").format(url))
            return None
        if response.getcode() != 200:
            self.log.error(_("Got error code {0} while fetching {1}.").format(response.getcode(), url))
            return None
        return responseData



if __name__ == "__main__":
    # Setup console output logging
    coloredLog = console.ColorLogging(fmt="%(levelname)-8s %(name)s >> %(message)s")
    rootlog = logging.getLogger("")
    rootlog.addHandler(coloredLog)
    rootlog.setLevel(logging.WARN)

    # Parse command line arguements
    optp = OptionParser(formatter=IndentedHelpFormatter(max_help_position=40), conflict_handler="resolve", version="%prog "+__version__)
    optp.add_option("-p", "--profile", help=_("choose profile"), dest="profile", default=None)
    optp.add_option("-n", "--no-color", help=_("disable usage of colored output"), dest="color", action="store_false", default=True)
    optp.add_option("-s", "--setup", help=_("run setup script"), dest="setup", action="store_const", const="interactive", default=False)
    optp.add_option("-w", "--workdir", help=_("set working directory, default is {0}").format("~/.geocaching"), dest="workdir", default="~/.geocaching")
    optp.add_option("-q", "--quiet", help=_("set logging to ERROR"), dest="loglevel", action="store_const", const=logging.ERROR, default=logging.WARN)
    optp.add_option("-v", "--verbose", help=_("set logging to INFO"), dest="loglevel", action="store_const", const=logging.INFO)
    optp.add_option("-d", "--debug", help=_("set logging to DEBUG"), dest="loglevel", action="store_const", const=logging.DEBUG)
    optp.add_option("-D", "--Debug", help=_("set logging to ALL"), dest="loglevel", action="store_const", const=0)

    opts,args = optp.parse_args()
    rootlog.setLevel(opts.loglevel)
    console.useColor = opts.color
    console.changeColor(console.colors["reset"], sys.stdout)
    console.changeColor(console.colors["reset"], sys.stderr)
    print("")
    setup = opts.setup

    # Check requirements
    # NOTE: Ubuntu modifies version string by '+', OMG :-(, so we drop all but numbers and dots
    version = re.sub("[^0-9.]+", "", platform.python_version())
    version = VersionInfo(version)
    minVersion = "3.1"
    if version < minVersion:
        rootlog.critical(_("You need at least Python {0} to run this script.").format(minVersion))

    workDir = os.path.expanduser(opts.workdir)
    parserDir = os.path.join(workDir, "parser")
    pyggsDir = os.path.join(workDir, "pyggs")
    profilesDir = os.path.join(pyggsDir, "profiles")

    # Check if the upgrade script is needed
    if os.path.isdir(pyggsDir):
        if os.path.isfile(os.path.join(pyggsDir, "version")):
            with open(os.path.join(pyggsDir, "version")) as fp:
                version = VersionInfo(fp.read())
        else:
            version = VersionInfo("0.1")
        if version < __version__:
            if version < "0.2":
                rootlog.error(_("Detected incompatible version of working directory {0}. Please, delete the directory and set up your profiles from start.").format(workDir))
                delete = console.prompt(_("Do you want to delete the working directory and enter the setup script now ({CHOICES})?"), validate=["y", "n"], default="y")
                if delete == "n":
                    raise SystemExit
                else:
                    rootlog.warn(_("Deleting content of working directory {0}.").format(workDir))
                    rmtree(workDir)
                    setup = "full"
            else:
                if version < "0.2.7":
                    if os.path.isfile(os.path.join(pyggsDir, "storage.sqlite")):
                        globalStorage = Storage(os.path.join(pyggsDir, "storage.sqlite"))
                        globalStorage.query("UPDATE environment SET variable = REPLACE(variable, '.db.', '.') WHERE variable LIKE 'plug.%.db.%'")
                        rootlog.info(_("Updating environment variables in global storage."))
            with open(os.path.join(pyggsDir, "version"), "w") as fp:
                fp.write(__version__)

    # Check directory structure
    if setup is None and (not os.path.isdir(workDir) or not os.path.isdir(parserDir) or not os.path.isdir(pyggsDir) or not os.path.isdir(profilesDir)):
        rootlog.warn(_("Working directory is not set up properly, initiating setup script."))
        setup = "full"

    # Try to find selected profile
    choices = []
    if os.path.isdir(profilesDir):
        for name in os.listdir(profilesDir):
            if os.path.isdir(os.path.join(profilesDir, name)):
                choices.append(name)
    if opts.profile is None:
        if len(choices) == 1:
            profile = choices[0]
            rootlog.warn(_("No profile name given, auto-chosing the only available profile '{0}'.").format(profile))
        else:
            if len(choices) > 0:
                choices.insert(0, _("Create new"))
                profile = console.menu(_("No profile name given, please select your profile."), choices)
            if len(choices) == 0 or profile == choices[0]:
                profile = console.prompt(_("Profile name") + ":", validate=lambda val: None if val.isalnum() else _("Please, use only alpha-numeric characters."))
                setup = "full"
    else:
        profile = opts.profile
        if profile not in choices:
            rootlog.warn(_("Profile '{0}' does not exist, creating profile directory and initiating setup script.").format(profile))
            setup = "full"

    # Check if the upgrade script for profile data is needed
    if os.path.isdir(os.path.join(profilesDir, profile)):
        if os.path.isfile(os.path.join(profilesDir, profile, "version")):
            with open(os.path.join(profilesDir, profile, "version")) as fp:
                version = VersionInfo(fp.read())
        else:
            version = VersionInfo("0.2.5")
        if version < __version__:
            if version < "0.2.7":
                if os.path.isfile(os.path.join(profilesDir, profile, "storage.sqlite")):
                    globalStorage = Storage(os.path.join(profilesDir, profile, "storage.sqlite"))
                    globalStorage.query("UPDATE environment SET variable = REPLACE(variable, '.db.', '.') WHERE variable LIKE 'plug.%.db.%'")
                    globalStorage.query("UPDATE environment SET variable = REPLACE(variable, 'Storage.plug.', 'plug.') WHERE variable LIKE 'Storage.plug.%'")
                    rootlog.info(_("Updating environment variables in profile storage."))
            with open(os.path.join(profilesDir, profile, "version"), "w") as fp:
                fp.write(__version__)

    pyggs = Pyggs(workDir, profile)
    if setup == "full":
        pyggs.fullSetup()
    elif setup == "interactive":
        pyggs.interactiveSetup()
    else:
        pyggs.run()
