# -*- coding: utf-8 -*-
"""
    colorer.py - make console output colored.
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
__all__ = ["ColorConsole"]


import logging
import platform
import sys

if platform.system() == "Windows":
    from ctypes import windll


class ColorConsole(logging.StreamHandler):
    def __init__(self, useColor=True, fmt="%(levelname)-8s %(name)-15s %(message)s", datefmt=None):
        logging.StreamHandler.__init__(self)
        self.useColor = useColor
        self.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))


    if platform.system() == "Windows":
        colors = {}
        colors["reset"] = 0x0007
        colors["notset"] = 0x0003
        colors["debug"] = 0x0005
        colors["info"] = 0x0008
        colors["warn"] = 0x000E
        colors["error"] = 0x000C
        colors["critical"] = 0x00CE

        def changeColor(self, color, stream):
            if not self.useColor:
                return

            if stream == sys.stdout:
                hdl = windll.kernel32.GetStdHandle(-11)
            elif stream == sys.stderr:
                hdl = windll.kernel32.GetStdHandle(-12)
            else:
                return

            windll.kernel32.SetConsoleTextAttribute(hdl, color)


    else:
        colors = {}
        colors["reset"] = "\x1b[0m"
        colors["notset"] = "\x1b[36m"
        colors["debug"] = "\x1b[35m"
        colors["info"] = "\x1b[1m"
        colors["warn"] = "\x1b[33;1m"
        colors["error"] = "\x1b[31;1m"
        colors["critical"] = "\x1b[33;41;1m"

        def changeColor(self, color, stream):
            if not self.useColor:
                return

            stream.write(color)
            self.flush(stream)


    def emit(self, record):
        if record.levelno >= 50:
            color = self.colors["critical"]
        elif record.levelno >= 40:
            color = self.colors["error"]
        elif record.levelno >= 30:
            color = self.colors["warn"]
        elif record.levelno >= 20:
            color = self.colors["info"]
        elif record.levelno >= 10:
            color = self.colors["debug"]
        else:
            color = self.colors["notset"]

        try:
            msg = self.format(record)
            self.writeln(str(msg), color)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            pass

        if record.levelno >= 50:
            raise SystemExit(1)


    def writeln(self, message, color, stream=None):
        if stream is None:
            stream = self.stream
        self.write(message, color, stream)
        stream.write("\n")
        self.flush(stream)


    def write(self, message, color, stream=None):
        if stream is None:
            stream = self.stream
        self.changeColor(color, stream)
        stream.write(message)
        self.flush(stream)
        self.changeColor(self.colors["reset"], stream)


    def flush(self, stream=None):
        if stream is None:
            stream = self.stream
        if hasattr(stream, "flush"):
            stream.flush()
