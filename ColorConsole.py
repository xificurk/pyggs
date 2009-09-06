# -*- coding: utf-8 -*-
"""
    ColorConsole.py - make console output colored.
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

import logging, platform, sys
if platform.system() == "Windows":
    from ctypes import windll

class ColorConsole(logging.StreamHandler):
    def __init__(self, use_color = True, fmt="%(levelname)-8s %(name)-15s %(message)s", datefmt=None):
        logging.StreamHandler.__init__(self)
        self.use_color = use_color
        if platform.system() == "Windows":
            self.emit = self.emit_win

            self.colors = {}
            self.colors["reset"] = 0x0007
            self.colors["notset"] = 0x0003
            self.colors["debug"] = 0x0005
            self.colors["info"] = 0x0008
            self.colors["warn"] = 0x000E
            self.colors["error"] = 0x000C
            self.colors["critical"] = 0x00CE
        else:
            self.emit = self.emit_ansi

            self.colors = {}
            self.colors["reset"] = "\x1b[0m"
            self.colors["notset"] = "\x1b[36m"
            self.colors["debug"] = "\x1b[35m"
            self.colors["info"] = "\x1b[1m"
            self.colors["warn"] = "\x1b[33;1m"
            self.colors["error"] = "\x1b[31;1m"
            self.colors["critical"] = "\x1b[33;41;1m"

            fmt = fmt + self.colors["reset"]

        self.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))

    def emit_ansi(self, record):
        if self.use_color:
            levelname = record.levelname
            if record.levelno >= 50:
                sys.stderr.write(self.colors["critical"])
            elif record.levelno >= 40:
                sys.stderr.write(self.colors["error"])
            elif record.levelno >= 30:
                sys.stderr.write(self.colors["warn"])
            elif record.levelno >= 20:
                sys.stderr.write(self.colors["info"])
            elif record.levelno >= 10:
                sys.stderr.write(self.colors["debug"])
            else:
                sys.stderr.write(self.colors["notset"])

        logging.StreamHandler.emit(self, record)

    def emit_win(self, record):
        if self.use_color:
            levelname = record.levelname
            hdl = windll.kernel32.GetStdHandle(-11)
            if record.levelno >= 50:
                windll.kernel32.SetConsoleTextAttribute(hdl, self.colors["critical"])
            elif record.levelno >= 40:
                windll.kernel32.SetConsoleTextAttribute(hdl, self.colors["error"])
            elif record.levelno >= 30:
                windll.kernel32.SetConsoleTextAttribute(hdl, self.colors["warn"])
            elif record.levelno >= 20:
                windll.kernel32.SetConsoleTextAttribute(hdl, self.colors["info"])
            elif record.levelno >= 10:
                windll.kernel32.SetConsoleTextAttribute(hdl, self.colors["debug"])
            else:
                windll.kernel32.SetConsoleTextAttribute(hdl, self.colors["notset"])

        logging.StreamHandler.emit(self, record)

        if self.use_color:
            windll.kernel32.SetConsoleTextAttribute(hdl, self.colors["reset"])
