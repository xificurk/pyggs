# -*- coding: utf-8 -*-
"""
    versioning.py - interface for version comparison.
    Based on http://code.activestate.com/recipes/521888/
    Copyright (C) 2007 Alexander Belchenko
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

__version__ = "0.1"
__all__ = ["VersionInfo"]

class VersionInfo(object):
    """Version info container and comparator"""

    __slots__ = ["major", "minor", "release", "build"]

    def __init__(self, v):
        if isinstance(v, str):
            # convert string to list
            v = [int(i) for i in v.split(".")]
        else:
            v = list(v)
        # build from sequence
        size = len(v)
        if size > 4:
            raise ValueError("Incorrect version info format. "
                             "Accepted max 4 numbers")
        if size < 4:
            v += [0] * (4-size)

        for ix, name in enumerate(self.__slots__):
            num = int(v[ix])
            setattr(self, name, num)

    def __getitem__(self, name):
        return getattr(self, name)

    def __repr__(self):
        return ('VersionInfo("{major:d}.{minor:d}.{release:d}.{build:d}")'.format(**self._dict()))

    def _dict(self):
        dict = {}
        for name in self.__slots__:
            dict[name] = self[name]
        return dict

    def __str__(self):
        if self.build > 0:
            fmt = "{major:d}.{minor:d}.{release:d}.{build:d}"
        elif self.release > 0:
            fmt = "{major:d}.{minor:d}.{release:d}"
        else:
            fmt = "{major:d}.{minor:d}"
        return fmt.format(**self._dict())

    def __cmp__(self, other):
        """Called for objects comparison.
        Return a negative integer if self < other,
        zero if self == other,
        a positive integer if self > other.
        """
        if not isinstance(other, VersionInfo):
            other = VersionInfo(other)
        res = 0
        for name in self.__slots__:
            res = getattr(self, name) - getattr(other, name)
            if res != 0:
                break
        return res

    def __eq__(self, other):
        return self.__cmp__(other) == 0

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __le__(self, other):
        return self.__cmp__(other) <= 0

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __ge__(self, other):
        return self.__cmp__(other) >= 0
