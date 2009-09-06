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
from GCparser.GCparser import GCparser
from optparse import OptionParser
import Configurator

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

    optp.add_option("-w","--workdir", dest="workdir", default="~/.geocaching", help="set work dir, default is ~/.geocaching")
    optp.add_option("-p","--profile", dest="profile", help="choose profile")

    opts,args = optp.parse_args()

    rootlog.setLevel(opts.loglevel)
    log = logging.getLogger("Pyggs")

    # Setup working directory structure
    workDir = os.path.expanduser(opts.workdir)
    if not os.path.isdir(workDir):
        log.critical("Working directory '%s' does not exist, please run setup.py script." % workDir)
        sys.exit()

    parserDir = workDir + "/parser"
    pyggsDir = workDir + "/pyggs"
    if not os.path.isdir(parserDir) or not os.path.isdir(pyggsDir):
        log.critical("Working directory '%s' is not set up properly, please run setup.py script." % workDir)
        sys.exit()

    log.info("Working directory is '%s'." % workDir)

    if opts.profile is None:
        log.error("You have to select a profile.")
        sys.exit()

    configFile = "%s/%s/config.xml" %(pyggsDir, opts.profile)
    if not os.path.isfile(configFile):
        log.critical("Configuration file not found for profile '%s', please run setup.py script." % opts.profile)
        sys.exit()
