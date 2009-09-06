#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    setup.py - setup script for Pyggs.
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
import Configurator

import gettext
langs = {}
langs["cs"] = gettext.translation("pyggs", localedir = os.path.dirname(__file__) + "/translations", codeset="utf-8", languages = ["cs"])
langs["en"] = gettext.translation("pyggs", localedir = os.path.dirname(__file__) + "/translations", codeset="utf-8", languages = ["en"])
langs["en"].install()

if __name__ == '__main__':
    # Setup console output logging
    console = ColorConsole(fmt="%(levelname)-8s %(name)-20s %(message)s")
    rootlog = logging.getLogger("")
    rootlog.addHandler(console)
    rootlog.setLevel(logging.WARN)

    # Parse command line arguements
    optp = OptionParser()

    optp.add_option('-q','--quiet', help='set logging to ERROR', action='store_const', dest='loglevel', const=logging.ERROR, default=logging.WARN)
    optp.add_option('-v','--verbose', help='set logging to INFO', action='store_const', dest='loglevel', const=logging.INFO)
    optp.add_option('-d','--debug', help='set logging to DEBUG', action='store_const', dest='loglevel', const=logging.DEBUG)
    optp.add_option('-D','--Debug', help='set logging to ALL', action='store_const', dest='loglevel', const=0)

    optp.add_option("-w","--workdir", dest="workdir", default="~/.geocaching", help="set working directory, default is ~/.geocaching")
    optp.add_option("-p","--profile", dest="profile", help="choose profile")

    opts,args = optp.parse_args()

    rootlog.setLevel(opts.loglevel)
    log = logging.getLogger("Pyggs.setup")

    # Setup working directory structure
    workDir = os.path.expanduser(opts.workdir)
    if not os.path.isdir(workDir):
        os.mkdir(workDir)
    if not os.path.isdir(workDir):
        log.critical("Unable to create working directory '%s'." % workDir)
        sys.exit()

    parserDir = workDir + "/parser"
    if not os.path.isdir(parserDir):
        os.mkdir(parserDir)
    pyggsDir = workDir + "/pyggs"
    if not os.path.isdir(pyggsDir):
        os.mkdir(pyggsDir)
    if not os.path.isdir(parserDir) or not os.path.isdir(pyggsDir):
        log.critical("Unable to set up base directory structure in working directory write to working directory '%s'." % workDir)
        sys.exit()

    log.info("Working directory is '%s'." % workDir)

    if opts.profile is None:
        log.error("You have to select a profile.")
        sys.exit()

    profileDir = "%s/%s" %(pyggsDir, opts.profile)
    if not os.path.isdir(profileDir):
        os.mkdir(profileDir)
    if not os.path.isdir(profileDir):
        log.critical("Unable to create profile directory '%s'." % profileDir)
        sys.exit()

    # Let's ask some questions and create config
    configFile = "%s/config.cfg" % profileDir
    config = Configurator.Profile(configFile)

    config.assertSection("global")
    langs[config.get("global", "language")].install()
    print()
    config.update("global", "language", _("Please, select user interface language - %s.") % "/".join(langs.keys()), validate = langs.keys())
    langs[config.get("global", "language")].install()

    gconfigFile = "%s/config.cfg" % pyggsDir
    gconfig = Configurator.Global(gconfigFile)

    gconfig.assertSection("plugins")
    print()
    print(_("Check if these are all installed plugins. You can enable/disable each of them for your profile later."))
    print(_("Please, use comma separated list."))
    gconfig.update("plugins", "list", _("Installed plugins"), validate = True)
    gconfig.save()

    print()
    print(_("Now, we're going to setup your profile named '%s'.") % opts.profile)

    config.assertSection("plugins")
    print("  %s:" % _("Plugins"))
    for plugin in gconfig.getPlugins():
        config.update("plugins", plugin, _("Enable %s") % plugin, validate = ["y", "n"])

    config.assertSection("geocaching.com")
    print("  Geocaching.com:")
    config.update("geocaching.com", "username", _("Username"), validate = True)
    config.update("geocaching.com", "password", _("Password"), validate = True)

    config.save()
    print()
    print(_("Note: You can always edit these setings by re-running setup.py script, or by hand in file %s.") % configFile)