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

__version__ = "0.2"


from collections import OrderedDict
import configparser
import datetime
import gettext
import locale
import logging
import math
from optparse import OptionParser
import os
import platform
import re
from shutil import rmtree
import sys

import libs.console as console
from libs.gcparser import GCparser
import libs.tenjin as tenjin

from plugins.base import Storage
import plugins

# Autodetect translations
localeDir = os.path.join(os.path.dirname(__file__), "translations")
langs = {}
for lang in os.listdir(localeDir):
    if os.path.isdir(os.path.join(localeDir, lang)):
        langs[lang] = gettext.translation("pyggs", localedir=localeDir, codeset="utf-8", languages=[lang])
gettext.install("pyggs", localedir=localeDir, codeset="utf-8")


class Pyggs(GCparser):
    def __init__(self, workDir, profile):
        self.log = logging.getLogger("Pyggs")
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
        """Interactive setup script"""
        print()
        console.writeln(_("Entering setup menu for profile {0}.").format(self.profile), console.color("G", True))
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
            console.writeln(_("Main menu"), console.color("RB", True))
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
        """Full setup script"""
        print()
        console.writeln(_("Entering full setup for profile {0}.").format(self.profile), console.color("G", True))
        self.setupWorkDir()
        self.setupGeneral()
        self.setupGeocachingCom()
        self.setupOutput()
        self.setupPlugins()
        self.setupEnd()


    def setupWorkDir(self):
        """Setup structure of working directory"""
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

        self.log.info("Working directory is {0}.".format(self.workDir))

        profileDir = os.path.join(profilesDir, self.profile)
        if not os.path.isdir(profileDir):
            os.mkdir(profileDir)
        if not os.path.isdir(profileDir):
            self.log.critical(_("Unable to create profile directory {0}.").format(profileDir))


    def setupGeneral(self):
        """Config: general section"""
        config = self.config
        config.assertSection("general")
        print()
        console.writeln(_("General options"), console.color("G", True))

        langs = globals()["langs"]
        config.update("general", "language", _("Please, select user interface language ({CHOICES})."), validate=list(langs.keys()))
        langs[config.get("general", "language")].install()

        print("    " + _("Enter your home coordinates in degrees as deciamal number (N means positive value, S negative; E means positive value, W negative)."))
        config.update("general", "homelat", _("Latitude:"), validate=lambda val: None if re.search("^-?[0-9]+\.?[0-9]*$", val) is not None else _("Please, use decimal number."))
        config.update("general", "homelon", _("Longitude:"), validate=lambda val: None if re.search("^-?[0-9]+\.?[0-9]*$", val) is not None else _("Please, use decimal number."))
        config.save()


    def setupGeocachingCom(self):
        """Config: geocaching.com section"""
        config = self.config
        config.assertSection("geocaching.com")
        print()
        console.writeln("Geocaching.com", console.color("G", True))

        config.update("geocaching.com", "username", _("Username:"), validate=True)
        config.update("geocaching.com", "password", _("Password:"), validate=True)
        config.save()


    def setupOutput(self):
        """Config: output section"""
        config = self.config
        config.assertSection("output")
        print()
        console.writeln(_("Output"), console.color("G", True))

        templates = self.detectTemplates()
        print("    " + _("Templates are looked up in these directories (consecutively):") + "\n      * " + "\n      * ".join(self.templateDirs))
        config.update("output", "template", _("Template ({CHOICES}):"), validate=templates)

        themes = self.detectThemes()
        print("    " + _("Themes are looked up in these directories (consecutively):") + "\n      * " + "\n      * ".join(self.themeDirs))
        config.update("output", "theme", _("Theme ({CHOICES}):"), validate=themes)

        config.update("output", "directory", _("Directory:"), validate=lambda val: None if os.path.isdir(os.path.expanduser(val)) else _("You have to input existing directory."))
        config.save()


    def setupPluginsSettings(self):
        """Config of every enabled plugin"""
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
        print(plugins)
        print(choices)
        while True:
            print()
            console.writeln("  " + _("Plugins settings menu"), console.color("RB"))
            choice = console.menu(_("Plugins:"), choices, padding=1)
            if choice == choices[0]:
                break
            plugin = plugins[choices.index(choice) - 1]
            console.write("  " + _("Configuration of") + " ", console.color("GB"))
            console.writeln(plugin, console.color("GB", True))
            self.plugins[plugin].setup()
            config.save()


    def setupPlugins(self):
        """Config: plugins section"""
        config = self.config
        config.assertSection("plugins")
        print()
        console.writeln(_("Plugins"), console.color("G", True))

        # Remove not installed plugins
        installedPlugins = self.detectPlugins()
        for plugin in config.options("plugins"):
            if plugin not in installedPlugins:
                logging.debug("Removing not installed plugin {0}.".format(plugin))
                config.remove_option("plugins", plugin)
        # Setup new found plugins
        for plugin in installedPlugins:
            self.loadPlugin(plugin)
            if plugin not in config.options("plugins"):
                console.writeln("  " + _("Plugin") + " " + plugin + ": " + self.plugins[plugin].about, console.color("G"))
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
            console.writeln("  " + _("Enable/Disable plugins menu"), console.color("RB"))
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
        """Enable and setup plugin with all dependencies"""
        if hasattr(self.plugins[plugin], "setup"):
            console.write("  " + _("Configuration of") + " ", console.color("GB"))
            console.writeln(plugin, console.color("GB", True))
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


    def setupEnd(self):
        """Save config etc"""
        self.config.save()
        with open(os.path.join(self.workDir, "pyggs", "version"), "w") as fp:
            fp.write(__version__)
        print()
        console.writeln(_("Note: You can always edit these setings by running pyggs with --setup (-s) switch."), console.color("G", True))


    def run(self):
        """Run pyggs"""
        config = self.config
        # Init GCparser, and redefine again self.log
        GCparser.__init__(self, username=config.get("geocaching.com", "username"), password=config.get("geocaching.com", "password"), dataDir=os.path.join(self.workDir, "parser"))
        self.log = logging.getLogger("Pyggs")

        self.globalStorage = Storage(os.path.join(self.workDir, "pyggs", "storage.sqlite"))
        self.profileStorage = Storage(os.path.join(self.workDir, "pyggs", "profiles", profile, "storage.sqlite"))

        self.handlers = {}
        self.pages = {}
        self.loadPlugins()
        self.makeDepTree()

        # Prepare plugins
        for plugin in self.plugins:
            if hasattr(self.plugins[plugin], "prepare"):
                self.log.info("Preparing plugin {0}...".format(plugin))
                self.plugins[plugin].prepare()

        # Run plugins
        for plugin in self.plugins:
            if hasattr(self.plugins[plugin], "run"):
                self.log.info("Running plugin {0}...".format(plugin))
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
                self.log.info("Finishing plugin {0}...".format(plugin))
                self.plugins[plugin].finish()


    def registerPage(self, output, template, menutemplate, context, layout=True):
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
        if name not in globals()["plugins"].__dict__:
            self.log.info("Loading plugin {0}.".format(name))
            __import__("{0}.{1}".format(globals()["plugins"].__name__, name))
        if name not in self.plugins:
            self.plugins[name] = getattr(globals()["plugins"].__dict__[name], "Plugin")(self)


    def loadPlugins(self):
        """Loads all plugins and their dependencies"""
        for plugin in self.config.options("plugins"):
            if self.config.get("plugins", plugin) == "y":
                self.loadPlugin(plugin)
        deps = self.findDeps(list(self.plugins.keys()))
        if len(deps) > 0:
            self.log.critical(_("Missing dependencies {0}.").format(", ".join(deps)))


    def findDeps(self, plugins):
        """Finds all dependencies that are not loaded"""
        result = []
        for plugin in plugins:
            self.loadPlugin(plugin)
            result.extend(self.findPluginDeps(plugins, self.plugins[plugin].dependencies))
        return list(set(result))


    def findPluginDeps(self, loaded, deps):
        """findDeps recursive callback"""
        result = list(deps)
        for plugin in deps:
            if plugin in loaded:
                result.remove(plugin)
            else:
                self.loadPlugin(plugin)
                result.extend(self.findPluginDeps(loaded, self.plugins[plugin].dependencies))
        return list(set(result))


    def makeDepTree(self):
        """Rearragne the order of self.plugins according to dependencies"""
        plugins = OrderedDict()
        fs = 0
        while len(self.plugins):
            fs = fs +1
            if fs > 100:
                self.log.warn("Cannot make plugin depedency tree for {0}. Possible circular dependencies.".format(",".join(list(self.plugins.keys()))))
                for plugin in list(self.plugins.keys()):
                    plugins[plugin] = self.plugins.pop(plugin)

            for plugin in list(self.plugins.keys()):
                if len(self.findPluginDeps(list(plugins.keys()), self.plugins[plugin].dependencies)) == 0:
                    plugins[plugin] = self.plugins.pop(plugin)

        self.plugins = plugins


    def detectTemplates(self):
        """Search for available templates"""
        templates = []
        for dir in self.templateDirs:
            if os.path.isdir(dir):
                for template in os.listdir(dir):
                    if os.path.isdir(os.path.join(dir, template)):
                        templates.append(template)
        templates.sort()
        return templates


    def getTemplate(self):
        """find selected template directory"""
        template = self.config.get("output", "template")
        for dir in self.templateDirs:
            if os.path.isdir(os.path.join(dir, template)):
                return os.path.join(dir, template)
        self.log.critical(_("Cannot find template {0}.").format(template))


    def detectThemes(self):
        """Search for available themes"""
        themes = []
        for dir in self.themeDirs:
            if os.path.isdir(dir):
                for theme in os.listdir(dir):
                    if os.path.isfile(os.path.join(dir, theme)):
                        themes.append(theme.replace(".theme", ""))
        themes.sort()
        return themes


    def getTheme(self):
        """find selected theme file"""
        theme = self.config.get("output", "theme")
        for dir in self.themeDirs:
            if os.path.isfile(os.path.join(dir, theme + ".theme")):
                return os.path.join(dir, theme + ".theme")
        self.log.critical(_("Cannot find theme {0}.").format(theme))


    def detectPlugins(self):
        """Search for available plugins"""
        plugins = []
        for plugin in os.listdir(os.path.join(os.path.dirname(__file__), "plugins")):
            if plugin.endswith(".py") and not plugin.startswith("__init__") and not plugin.startswith("example") and plugin[:-3] != "base":
                plugins.append(plugin[:-3])
        plugins.sort()
        return plugins



class BaseConfig(configparser.RawConfigParser):
    def __init__(self, configFile):
        self.log = logging.getLogger("Pyggs.Config")
        configparser.RawConfigParser.__init__(self)

        # Let's make option names case-sensitive
        self.optionxform = str

        self.defaults = {}

        self.configFile = configFile
        if os.path.isfile(configFile):
            self.load(configFile)


    def save(self):
        """Save config to a file"""
        with open(self.configFile, "w", encoding="utf-8") as cfp:
            self.write(cfp)


    def load(self, configFile):
        """Loads config from a file"""
        with open(configFile, encoding="utf-8") as cfp:
            self.readfp(cfp)


    def get(self, section, option):
        """Get section->option, from config, or self.defaults"""
        try:
            value = configparser.RawConfigParser.get(self, section, option)
        except (configparser.NoSectionError, configparser.NoOptionError):
            try:
                value = self.defaults[section][option]
            except KeyError:
                value = ""
        return value


    def assertSection(self, section):
        """Add section, if not present"""
        try:
            self.add_section(section)
        except configparser.DuplicateSectionError:
            pass


    def update(self, section, option, prompt, validate=None):
        """Update option via user input"""
        default = self.get(section, option)
        value = console.prompt(prompt, padding=2, default=default, validate=validate)
        self.set(section, option, value)
        return self.get(section, option)



class ProfileConfig(BaseConfig):
    def __init__(self, configFile):
        BaseConfig.__init__(self, configFile)
        self.log = logging.getLogger("Pyggs.ProfileConfig")

        # set default values
        self.defaults["output"] = {}
        self.defaults["output"]["template"] = "default.en"
        self.defaults["output"]["theme"] = "default"
        self.defaults["plugins"] = {}
        self.defaults["plugins"]["stats"] = "y"
        self.defaults["plugins"]["general"] = "y"
        self.defaults["plugins"]["myfinds_averages"] = "y"



# Double the brackets
tenjin.Template.EXPR_PATTERN = re.compile(r"([#$])\{\{(.*?)\}\}", re.S)
tenjin.Preprocessor.EXPR_PATTERN = re.compile(r"([#$])\{\{\{(.*?)\}\}\}", re.S)

class Templar(tenjin.Engine):
    def __init__(self, template, theme, outDir):
        self.log = logging.getLogger("Pyggs.Templar")
        tenjin.Engine.__init__(self, postfix=".pyhtml", layout=":@layout", path=[template])
        self.theme = Theme(theme)
        self.outDir = outDir


    def include(self, template_name, append_to_buf=True, context = None):
        """This allows to pass different context to the subtemplate"""
        frame = sys._getframe(1)
        locals = frame.f_locals
        globals = frame.f_globals
        assert "_context" in locals
        if context is None:
            context = locals["_context"]
        else:
            self.hook_context(context)
        # context and globals are passed to get_template() only for preprocessing.
        template = self.get_template(template_name, context, globals)
        if append_to_buf:
            _buf = locals["_buf"]
        else:
            _buf = None
        return template.render(context, globals, _buf=_buf)


    def outputPages(self, pages):
        """Render and save all pages"""
        for output in pages:
            globals = { "escape":tenjin.helpers.escape,
                        "to_str":tenjin.helpers.to_str,
                        "echo":tenjin.helpers.echo,
                        "css_header":self.theme.cssHeader,
                        "css":self.theme.css,
                        "gradient":self.theme.cssGradient,
                        "locale":locale,
                        "datetime":datetime,
                        "dateRange":self.dateRange,
                        "date":self.formatDate,
                        "dist":self.formatDistance,
                        "lat":self.formatLat,
                        "lon":self.formatLon,
                        "ctype":self.cacheType,
                        "csize":self.cacheSize}
            context = pages[output]["context"]
            context["pages"] = pages
            result = self.render(pages[output]["template"], context, globals=globals, layout=pages[output]["layout"])
            with open(os.path.join(self.outDir, output), "w") as fp:
                fp.write(result)
                fp.flush()


    def formatDate(self, value = None, format = "{day:d}.&nbsp;{month:d}.&nbsp;{year:d}"):
        """Return date in string fromat"""
        if isinstance(value, str):
            value = datetime.datetime.strptime(value, "%Y-%m-%d")
        elif isinstance(value, int):
            value = datetime.datetime.fromtimestamp(value)
        elif value is None:
            value = datetime.datetime.today()

        return format.format(year=value.year, month=value.month, day=value.day, hour=value.hour, minute=value.minute, monthname=value.strftime("%B"), monthabr=value.strftime("%b"))


    def dateRange(self, start, end = None):
        """Returns date range in string format"""
        if isinstance(start, str):
            start = datetime.datetime.strptime(start, "%Y-%m-%d")
        elif isinstance(start, int):
            start = datetime.datetime.fromtimestamp(start)
        elif start is None:
            start = datetime.datetime.today()

        if end is None:
            return self.formatDate(start, "{day:d}.&nbsp;{month:d}.&nbsp;{year:d}")
        elif isinstance(end, datetime.timedelta):
            end = start + end
        elif isinstance(end, str):
            end = datetime.datetime.strptime(end, "%Y-%m-%d")
        elif isinstance(end, int):
            end = datetime.datetime.fromtimestamp(end)

        if start > end:
            (start,end) = (end,start)

        if self.formatDate(start, "{year:d}-{month:d}") == self.formatDate(end, "{year:d}-{month:d}"):
            string = self.formatDate(start, "{day:d}.");
        elif self.formatDate(start, "{year:d}") == self.formatDate(end, "{year:d}"):
            string = self.formatDate(start, "{day:d}.&nbsp;{month:d}.")
        else:
            string = self.formatDate(start, "{day:d}.&nbsp;{month:d}.&nbsp;{year:d}")
        string = string + "&nbsp;– " + self.formatDate(end, "{day:d}.&nbsp;{month:d}.&nbsp;{year:d}")

        return string


    def formatDistance(self, value):
        """Returns distance with suitable precision"""
        if value < 10:
            return "{0:.2f}".format(value)
        elif value < 100:
            return "{0:.1f}".format(value)
        else:
            return "{0:.0f}".format(value)


    def formatLat(self, lat):
        """Formats latitude"""
        if lat > 0:
            pre = "N"
        else:
            pre = "S"
        lat = abs(lat)
        dg = math.floor(lat)
        mi = (lat-dg)*60
        return "{0} {1:02d}° {2:06.3f}".format(pre, dg, mi)


    def formatLon(self, lon):
        """Formats Longitude"""
        if lon > 0:
            pre = "E"
        else:
            pre = "W"
        lon = abs(lon)
        dg = math.floor(lon)
        mi = (lon-dg)*60
        return "{0} {1:03d}° {2:06.3f}".format(pre, dg, mi)


    def cacheSize(self, size):
        return "<img alt=\"{0}\" title=\"{0}\" src=\"http://www.geocaching.com/images/icons/container/{1}.gif\" width=\"45\" height=\"12\" />".format(size, size.lower().replace(" ", "_"))


    def cacheType(self, ctype):
        ctypes = {}
        ctypes["Traditional Cache"] = 2
        ctypes["Multi-cache"] = 3
        ctypes["Unknown Cache"] = 8
        ctypes["Letterbox Hybrid"] = 5
        ctypes["Earthcache"] = "earthcache"
        ctypes["Wherigo Cache"] = 1858
        ctypes["Event Cache"] = 6
        ctypes["Virtual Cache"] = 4
        ctypes["Webcam Cache"] = 11
        ctypes["Cache In Trash Out Event"] = 13
        ctypes["Mega-Event Cache"] = "mega"

        return "<img alt=\"{0}\" title=\"{0}\" src=\"http://www.geocaching.com/images/WptTypes/sm/{1}.gif\" width=\"16\" height=\"16\" />".format(ctype, ctypes[ctype])



class Theme(BaseConfig):
    def __init__(self, theme):
        BaseConfig.__init__(self, theme)
        self.log = logging.getLogger("Pyggs.Theme")


    def options(self, section):
        """Handle missing section error"""
        try:
            return BaseConfig.options(self, section)
        except configparser.NoSectionError:
            self.log.warn("This theme has no section {0}.".format(section))
            return []


    def css(self, *classes):
        """Merge definitions from classe and return them"""
        all = OrderedDict()
        for cl in classes:
            tomerge = {}
            if isinstance(cl, dict):
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
            ret = ret + "{0}:{1};".format(property, all[property])

        if len(ret) > 0:
            return " style=\"{0}\"".format(ret)


    def cssHeader(self):
        """Render common styles in the header"""
        ret = ""
        for option in self.options("@screen"):
            ret = ret + "\n" + option + " {" + self.get("@screen", option) + "}"
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

        if match1 is None:
            self.log.error("Cannost parse color {0}.".format(color1))
            return "inherit"
        if match2 is None:
            self.log.error("Cannost parse color {0}.".format(color2))
            return "inherit"

        share = max(0, min(float(share), 1))

        red = round((1-share)*float(match1.group(1)) + share*float(match2.group(1)))
        green = round((1-share)*float(match1.group(2)) + share*float(match2.group(2)))
        blue = round((1-share)*float(match1.group(3)) + share*float(match2.group(3)))

        return "#{0:02x}{1:02x}{2:02x}".format(red, green, blue)



if __name__ == "__main__":
    # Setup console output logging
    coloredLog = console.ColorLogging(fmt="%(levelname)-8s %(name)s >> %(message)s")
    rootlog = logging.getLogger("")
    rootlog.addHandler(coloredLog)
    rootlog.setLevel(logging.WARN)

    # Parse command line arguements
    optp = OptionParser()
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
    setup = opts.setup

    # Check requirements
    if float(platform.python_version()) < 3.1:
        rootlog.critical(_("You need at least Python {0} to run this script.").format(3.1))

    workDir = os.path.expanduser(opts.workdir)
    parserDir = os.path.join(workDir, "parser")
    pyggsDir = os.path.join(workDir, "pyggs")
    profilesDir = os.path.join(pyggsDir, "profiles")

    # Check if the upgrade script is needed
    if os.path.isdir(pyggsDir):
        if os.path.isfile(os.path.join(pyggsDir, "version")):
            with open(os.path.join(pyggsDir, "version")) as fp:
                version = float(fp.read())
        else:
            version = 0.1
        if version < float(__version__):
            if version < 0.2:
                rootlog.error(_("Detected incompatible version of working directory {0}. Please, delete the directory and set up your profiles from start.").format(workDir))
                delete = console.prompt(_("Do you want to delete the working directory and enter the setup script now ({CHOICES})?"), validate=["y", "n"], default="y")
                if delete == "n":
                    raise SystemExit
                else:
                    rootlog.warn(_("Deleting content of working directory {0}.").format(workDir))
                    rmtree(workDir)
                    setup = "full"

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


    pyggs = Pyggs(workDir, profile)
    if setup == "full":
        pyggs.fullSetup()
    elif setup == "interactive":
        pyggs.interactiveSetup()
    else:
        pyggs.run()
