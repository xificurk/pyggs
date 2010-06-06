# -*- coding: utf-8 -*-
"""
    gcparser.py - simple library for parsing geocaching.com website.
    Copyright (C) 2009-2010 Petr Morávek

    This file is part of GCparser.

    GCparser is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    GCparser is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

__version__ = "0.4.4"
__all__ = ["GCparser", "Fetcher", "BaseParser", "CacheParser", "MyFindsParser", "SeekParser", "EditProfile", "CredentialsException", "LoginException"]


import datetime
from hashlib import md5
from html.parser import HTMLParser
import http.cookiejar as CJ
import logging
import os
import random
import re
import time
import unicodedata
import urllib


class GCparser(object):
    def __init__(self, username=None, password=None, dataDir="~/.geocaching/parser"):
        self.log = logging.getLogger("GCparser")

        self.fetcher = Fetcher(username, password, dataDir)
        self.parsers = {}
        # Register standard distribution parsers
        self.registerParser("myFinds", MyFindsParser)
        self.registerParser("seek", SeekParser)
        self.registerParser("cache", CacheParser)
        self.registerParser("editProfile", EditProfile)


    def registerParser(self, name, handler):
        """ Register parser object.
        """
        self.parsers[name] = handler


    def parse(self, name, *args, **kwargs):
        """ Call parser of the name.
        """
        return self.parsers[name](self.fetcher, *args, **kwargs)



class Fetcher(object):
    def __init__(self, username=None, password=None, dataDir="~/.geocaching/parser"):
        self.log = logging.getLogger("GCparser.Fetcher")

        self.username = username
        self.password = password
        if username is None or password is None:
            self.log.warn("No geocaching.com credentials given, some features will be disabled.")

        dataDir = os.path.expanduser(dataDir)
        if os.path.isdir(dataDir):
            self.dataDir = dataDir
            self.log.info("Setting data directory to '{0}'.".format(dataDir))
        else:
            self.log.warn("Data directory '{0}' does not exist, caching will be disabled.".format(dataDir))
            self.dataDir = None

        self.cookies = None
        self.userAgent = None

        self.firstFetch = 0
        self.lastFetch = 0
        self.fetchCount = 0
        # Desired average fetch sleep time
        self.fetchAvgTime = 600


    def fetch(self, url, authenticate=False, data=None, check=True):
        """ Fetch page.
        """
        if authenticate:
            cookies = self.getCookies()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
        else:
            opener = urllib.request.build_opener()

        headers = []
        headers.append(("User-agent", self.getUserAgent()))
        headers.append(("Accept", "text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8"))
        headers.append(("Accept-Language", "en-us,en;q=0.5"))
        headers.append(("Accept-Charset", "utf-8,*;q=0.5"))
        opener.addheaders = headers

        if authenticate:
            self.wait()
        else:
            time.sleep(max(0, self.lastFetch + 1 - time.time()))
            self.lastFetch = time.time()

        self.log.debug("Fetching page '{0}'.".format(url))
        web = self.fetchData(opener, url, data)

        self.saveUserAgent()
        if authenticate:
            self.saveCookies()

        web = web.read().decode("utf-8")
        if authenticate and check and not self.checkLogin(web):
            self.log.debug("We're not actually logged in, refreshing login and redownloading page.")
            self.login()
            self.fetch(url, authenticate, data)

        return web


    def fetchData(self, opener, url, data, retry=1):
        """ Performs download of the page.
        """
        try:
            if data is not None:
                web = opener.open(url, urllib.parse.urlencode(data))
            else:
                web = opener.open(url)
        except(IOError):
            self.log.error("An error occured while downloading '{0}', will retry in {1} seconds.".format(url, retry))
            time.sleep(retry)
            retry = min(5*retry, 600)
            return self.fetchData(opener, url, data, retry)
        return web


    def getCookies(self):
        """ Get current cookies, load from file, or create.
        """
        if self.cookies is not None:
            return self.cookies

        userFile = self.userFileName()
        if userFile is None:
            self.log.debug("Cannot load cookies - invalid filename.")
            self.cookies = CJ.CookieJar()
            self.login()
        else:
            cookieFile = userFile + ".cookie"
            if os.path.isfile(cookieFile):
                self.log.debug("Re-using stored cookies.")
                self.cookies = CJ.LWPCookieJar(cookieFile)
                self.cookies.load(ignore_discard=True)
                logged = False
                for cookie in self.cookies:
                    if cookie.name == "userid":
                        logged = True
                        break
                if not logged:
                    self.login()
            else:
                self.log.debug("No stored cookies, creating new.")
                self.cookies = CJ.LWPCookieJar(cookieFile)
                self.login()

        return self.cookies


    def saveCookies(self):
        """ Try to save cookies, if possible.
        """
        if isinstance(self.cookies, CJ.LWPCookieJar):
            self.log.debug("Saving cookies.")
            self.cookies.save(ignore_discard=True, ignore_expires=True)


    def userFileName(self):
        """ Returns filename to store user's data.
        """
        if self.username is None or self.dataDir is None:
            return None

        hash = md5(self.username.encode("utf-8")).hexdigest()
        name = ''.join((c for c in unicodedata.normalize('NFD', self.username) if unicodedata.category(c) != 'Mn'))
        name = pcre("fileMask").sub("", name)
        name = name + "_" + hash
        return os.path.join(self.dataDir, name)


    def getUserAgent(self):
        """ Return current UserAgent, or load from file, or generate random one.
        """
        if self.userAgent is not None:
            return self.userAgent

        userFile = self.userFileName()
        if userFile is None:
            self.userAgent = self.randomUserAgent()
        else:
            UAFile = userFile + ".ua"
            if os.path.isfile(UAFile):
                with open(UAFile, "r", encoding="utf-8") as fp:
                    self.userAgent = fp.read()
            else:
                self.userAgent = self.randomUserAgent()

        return self.userAgent


    def saveUserAgent(self):
        """ Try to save user agent, if possible.
        """
        if self.userAgent is not None:
            userFile = self.userFileName()
            if userFile is not None:
                UAFile = userFile + ".ua"
                with open(UAFile, "w", encoding="utf-8") as fp:
                    self.log.debug("Saving user agent.")
                    fp.write(self.userAgent)


    def randomUserAgent(self):
        """ Generate random UA string - masking as Firefox 3.0.x.
        """
        system = random.randint(1,5)
        if system <= 1:
            system = "X11"
            systemVersion = ["Linux i686", "Linux x86_64"]
        elif system <= 2:
            system = "Macintosh"
            systemVersion = ["PPC Mac OS X 10.5"]
        else:
            system = "Windows"
            systemVersion = ["Windows NT 5.1", "Windows NT 6.0", "Windows NT 6.1"]

        systemVersion = systemVersion[random.randint(0, len(systemVersion) - 1)]
        version = random.randint(1, 13)
        date = "200907{0:02d}{1:02d}".format(random.randint(1, 31), random.randint(1, 23))

        return "Mozilla/5.0 ({0}; U; {1}; en-US; rv:1.9.0.{2:d}) Gecko/{3} Firefox/3.0.{2:d}".format(system, systemVersion, version, date)


    def wait(self):
        """ Waits for random number of seconds to lessen the load on geocaching.com.
        """
        # no fetch for a long time => reset firstFetch value using desired average
        self.firstFetch = max(time.time() - self.fetchCount*self.fetchAvgTime, self.firstFetch)
        # Compute count
        count = self.fetchCount - int((time.time() - self.firstFetch)/self.fetchAvgTime)

        # sleep time 1s: 10/10s => overall 10/10s
        if count < 10:
            sleepTime = 1
        # sleep time 2-8s: 40/3.3m => overall 50/3.5min
        elif count < 50:
            sleepTime = random.randint(2,8)
        # sleep time 5-35s: 155/51.6m => overall 205/55.1min
        elif count < 200:
            sleepTime = random.randint(5,35)
        # sleep time 10-50s: 315/2.6h => overall 520/3.5h
        elif count < 500:
            sleepTime = random.randint(10,50)
        # sleep time 20-80s
        else:
            sleepTime = random.randint(20,80)
        time.sleep(max(0, self.lastFetch + sleepTime - time.time()))
        self.fetchCount = self.fetchCount + 1
        self.lastFetch = time.time()


    def login(self):
        """ Log in to geocaching.com, save cookiejar.
        """
        logged = self.loginAttempt()
        if not logged:
            self.log.debug("Not logged in, re-trying.")
            logged = self.loginAttempt()

        if not logged:
            self.log.critical("Login error.")
            raise LoginException

        self.log.debug("Logged in.")
        self.saveCookies()


    def loginAttempt(self):
        """ Try to log in to geocaching.com.
        """
        self.log.debug("Attempting to log in.")

        if self.username is None or self.password is None:
            self.log.critical("Cannot log in - no credentials available.")
            raise CredentialsException

        webpage = self.fetch("http://www.geocaching.com/", authenticate=True, check=False)

        data = {}
        data["ctl00$MiniProfile$loginUsername"] = self.username
        data["ctl00$MiniProfile$loginPassword"] = self.password
        data["ctl00$MiniProfile$LoginBtn"] = "Go"
        data["ctl00$MiniProfile$uxRememberMe"] = "on"

        for line in webpage.splitlines():
            match = pcre("hiddenInput").search(line)
            if match:
                data[match.group(1)] = match.group(2)

        webpage = self.fetch("http://www.geocaching.com/Default.aspx", data=data, authenticate=True, check=False)

        logged = False
        for cookie in self.cookies:
            self.log.debug("{0}: {1}".format(cookie.name, cookie.value))
            if cookie.name == "userid":
                logged = True

        return logged


    def checkLogin(self, data):
        """ Checks the data for not logged in error.
        """
        self.log.debug("Checking if we're really logged in...")
        logged = True
        if data is not None:
            for line in data.splitlines():
                if line.find("Sorry, the owner of this listing has made it viewable to Premium Members only") != -1:
                    self.log.debug("PM only cache.")
                    break
                if line.find("You are not logged in.") != -1:
                    logged = False
                    break
        return logged


"""
    HELPERS
"""

monthsAbbr = {"Jan":1, "Feb":2, "Mar":3, "Apr":4, "May":5, "Jun":6, "Jul":7, "Aug":8, "Sep":9, "Oct":10, "Nov":11, "Dec":12}
months = {"January":1, "February":2, "March":3, "April":4, "May":5, "June":6, "July":7, "August":8, "September":9, "October":10, "November":11, "December":12}


__pcres = {}
__pcresMask = {}

""" PCRE: SYSTEM """
__pcresMask["null"] = (".*", 0)
__pcresMask["fileMask"] = ("[^a-zA-Z0-9._-]+", re.A)

def pcre(name):
    """ Prepare PCRE.
    """
    if name not in __pcresMask:
        logging.getLogger("GCparser.helpers").error("Uknown PCRE {0}.".format(name))
        name = "null"

    if name not in __pcres:
        __pcres[name] = re.compile(__pcresMask[name][0], __pcresMask[name][1])

    return __pcres[name]


""" PCRE: HTML """
__pcresMask["HTMLp"] = ("<p[^>]*>", re.I)
__pcresMask["HTMLbr"] = ("<br[^>]*>", re.I)
__pcresMask["HTMLli"] = ("<li[^>]*>", re.I)
__pcresMask["HTMLh"] = ("</?h[0-9][^>]*>", re.I)
__pcresMask["HTMLimgalt"] = ("<img[^>]*alt=['\"]([^'\"]+)['\"][^>]*>", re.I)
__pcresMask["HTMLimg"] = ("<img[^>]*>", re.I)
__pcresMask["HTMLtag"] = ("<[^>]*>", re.I)
__pcresMask["blankLine"] = ("^\s+|\s+$|^\s*$\n", re.M)
__pcresMask["doubleSpace"] = ("\s\s+", 0)

def cleanHTML(text):
    """ Cleans text from HTML markup and unescapes entities.
    """
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")

    text = pcre("HTMLp").sub("\n** ", text)
    text = pcre("HTMLbr").sub("\n", text)
    text = pcre("HTMLli").sub("\n - ", text)

    text = pcre("HTMLh").sub("\n", text)

    text = pcre("HTMLimgalt").sub("[img \\1]", text)
    text = pcre("HTMLimg").sub("[img]", text)

    text = pcre("HTMLtag").sub("", text)

    # Escape entities
    text = unescape(text)

    # Remove unnecessary spaces
    text = pcre("blankLine").sub("", text)
    text = pcre("doubleSpace").sub(" ", text)

    return text

unescape = HTMLParser().unescape


"""
    PARSERS
"""

LOG_PARSER = 5
logging.addLevelName(5, "PARSER")

""" PCRE: geocaching.com general """
__pcresMask["hiddenInput"] = ("<input type=[\"']hidden[\"'] name=\"([^\"]+)\"[^>]+value=\"([^\"]*)\"", re.I)
__pcresMask["PMonly"] = ("<p class=['\"]Warning['\"][^>]*>Sorry, the owner of this listing has made it viewable to Premium Members only", re.I)
__pcresMask["guid"] = ("^[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+$", re.I)


class BaseParser(object):
    def __init__(self, fetcher):
        self.fetcher = fetcher
        self.data = None


    def _load(self, url, authenticate=False, data=None):
        """ Loads data from webpage.
        """
        if self.data is None:
            self.data = self.fetcher.fetch(url, authenticate=authenticate, data=data)



""" PCRE: cache details """
# <p class="OldWarning"><strong>Cache Issues:</strong></p><ul class="OldWarning"><li>This cache is temporarily unavailable. Read the logs below to read the status for this cache.</li></ul></span>
__pcresMask["disabled"] = ("<p class=['\"]OldWarning['\"][^>]*><strong>Cache Issues:</strong></p><ul[^>]*><li>This cache (has been archived|is temporarily unavailable)[^<]*</li>", re.I)
__pcresMask["waypoint"] = ("GC[A-Z0-9]+", 0)
# <meta name="og:url" content="http://www.geocaching.com/seek/cache_details.aspx?guid=92322d1b-d354-4190-980e-8964d7740161" property="og:url" />
__pcresMask["cacheGuid"] = ("<meta\s+name=\"og:url\"\s+content=\"http://www\.geocaching.com/seek/cache_details\.aspx\?guid=([a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)\"", re.I)
# <meta name="description" content="Cajova chyse/ Tea hut (GCRBCA) was created by adp. on 11/15/2005. It's a Micro size geocache, with difficulty of 1, terrain of 1. It's located in Hlavni mesto Praha, Czech Republic. Cache je um&amp;iacute;stena v Japonske casti botanicke zahrady vTroji/ Cache is located in Japan compartment of the Prague botanicgarden in Troja. Souradnice v&amp;#225;s zavedou doJaponsk&amp;#233; zahrady v Botanick&amp;#233; zahrade v Tr&amp;#243;ji." />
# <meta name="description" content="PGME - Neco pro deti (GC25HWC) was created by gordici on 06/26/2010. It's a Other size geocache, with difficulty of 1.5, terrain of 1.5. It's located in Hlavni mesto Praha, Czech Republic. Mezi nami je rada rodin s detmi, tak aby deti neprisly zkratka,pripravili jsme pro ne take nejakou zabavu." />
__pcresMask["cacheDetails"] = ("<meta\s+name=\"description\" content=\"([^\"]+) \(GC[A-Z0-9]+\) was created by ([^\"]+) on ([0-9]+)/([0-9]+)/([0-9]+)\. It's a ([a-zA-Z ]+) size geocache, with difficulty of ([0-9.]+), terrain of ([0-9.]+). It's located in (([^,]+), )?([^.]+)\.[^\"]*\"[^>]*>", re.I|re.S)
# <a href="/about/cache_types.aspx" target="_blank" title="About Cache Types"><img src="/images/WptTypes/8.gif" alt="Unknown Cache" width="32" height="32" />
__pcresMask["cacheType"] = ("<img src=['\"]/images/WptTypes/[^'\"]+['\"] alt=\"([^\"]+)\"[^>]*></a>", re.I)
# by <a href="http://www.geocaching.com/profile/?guid=ed7a2040-3bbb-485b-9b03-21ae8507d2d7&wid=92322d1b-d354-4190-980e-8964d7740161&ds=2">
__pcresMask["cacheOwnerId"] = ("by <a href=['\"]http://www\.geocaching\.com/profile/\?guid=[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+&wid=([a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)&ds=2['\"][^>]*>", re.I)
# <span id="ctl00_ContentBody_LatLon" style="font-weight:bold;">N 50° 02.173 E 015° 46.386</span>
__pcresMask["cacheLatLon"] = ("<span id=['\"]ctl00_ContentBody_LatLon['\"][^>]*>([NS]) ([0-9]+)° ([0-9.]+) ([WE]) ([0-9]+)° ([0-9.]+)</span>", re.I)
__pcresMask["cacheShortDesc"] = ("<div class=['\"]UserSuppliedContent['\"]>\s*<span id=['\"]ctl00_ContentBody_ShortDescription['\"]>(.*?)</span>\s+</div>", re.I|re.S)
__pcresMask["cacheLongDesc"] = ("<div class=['\"]UserSuppliedContent['\"]>\s*<span id=['\"]ctl00_ContentBody_LongDescription['\"]>(.*?)</span>\s*</div>\s*<p>\s+</p>\s+</td>", re.I|re.S)
"""
<div id="div_hint" class="HalfLeft">
                Hint text
</div>
"""
__pcresMask["cacheHint"] = ("<div id=['\"]div_hint['\"][^>]*>\s*(.*?)\s*</div>", re.I)
"""
<div class="CacheDetailNavigationWidget Spacing">
    <img src="/images/attributes/wheelchair-no.gif" alt="not wheelchair accessible" title="not wheelchair accessible" width="30" height="30" /> <img src="/images/attributes/firstaid-yes.gif" alt="needs maintenance" title="needs maintenance" width="30" height="30" /> <img src="/images/attributes/stealth-yes.gif" alt="stealth required" title="stealth required" width="30" height="30" /> <img src="/images/attributes/available-yes.gif" alt="available 24-7" title="available 24-7" width="30" height="30" /> <img src="/images/attributes/scenic-yes.gif" alt="scenic view" title="scenic view" width="30" height="30" /> <img src="/images/attributes/onehour-yes.gif" alt="takes less than 1  hour" title="takes less than 1  hour" width="30" height="30" /> <img src="/images/attributes/kids-yes.gif" alt="kid friendly" title="kid friendly" width="30" height="30" /> <img src="/images/attributes/dogs-yes.gif" alt="dogs allowed" title="dogs allowed" width="30" height="30" /> <img src="/images/attributes/attribute-blank.gif" alt="blank" title="blank" width="30" height="30" /> <img src="/images/attributes/attribute-blank.gif" alt="blank" title="blank" width="30" height="30" /> <img src="/images/attributes/attribute-blank.gif" alt="blank" title="blank" width="30" height="30" /> <img src="/images/attributes/attribute-blank.gif" alt="blank" title="blank" width="30" height="30" /> <p class="NoSpacing"><small><a href="/about/icons.aspx" title="What are Attributes?">What are Attributes?</a></small></p>
</div>
"""
__pcresMask["cacheAttributes"] = ("<div class=\"CacheDetailNavigationWidget Spacing\">\s*(.*?)\s*<p[^>]*><small><a href=['\"]/about/icons\.aspx['\"] title=['\"]What are Attributes\?['\"]>What are Attributes\?</a></small></p>\s*</div>", re.I|re.S)
__pcresMask["cacheAttributesItem"] = ("title=\"([^\"]+)\"", re.I)
"""
    <span id="ctl00_ContentBody_uxTravelBugList_uxInventoryLabel">Inventory</span>
</h3>
<div class="WidgetBody">
    <ul>
    <li>
        <a href="http://www.geocaching.com/track/details.aspx?guid=0eac9e5f-dc6c-4ec3-b1b7-4663245982ef" class="lnk">
            <img src="http://www.geocaching.com/images/wpttypes/sm/21.gif" width="16" /><span>Bob the Bug</span></a>
    </li>
    <li>

        <a href="http://www.geocaching.com/track/details.aspx?guid=0511b8eb-ddaa-4484-9a38-a2d8b3b6a77b" class="lnk">
            <img src="http://www.geocaching.com/images/wpttypes/sm/1998.gif" width="16" /><span>Barusky trsatko ;-)</span></a>
    </li>
    <li>
        <a href="http://www.geocaching.com/track/details.aspx?guid=b82c9582-3d66-425a-91e1-c99f1e3e88d9" class="lnk">
            <img src="http://www.geocaching.com/images/wpttypes/sm/2059.gif" width="16" /><span>Travel Ingot Mr. East</span></a>
    </li>
    </ul>
"""
__pcresMask["cacheInventory"] = ("<span\s+id=\"ctl00_ContentBody_uxTravelBugList_uxInventoryLabel\">Inventory</span>\s*</h3>\s*<div[^>]*>\s*<ul[^>]*>(.*?)</ul>", re.I|re.S)
"""
<a href="http://www.geocaching.com/track/details.aspx?guid=b82c9582-3d66-425a-91e1-c99f1e3e88d9" class="lnk">
    <img src="http://www.geocaching.com/images/wpttypes/sm/2059.gif" width="16" /><span>Travel Ingot Mr. East</span></a>
"""
__pcresMask["cacheInventoryItem"] = ("<a href=['\"][^'\"]*/track/details\.aspx\?guid=([a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)['\"][^>]*>\s*<img[^>]*>\s*<span>([^<]+)</span></a>", re.I)
# <span id="ctl00_ContentBody_lblFindCounts"><p><img src="/images/icons/icon_smile.gif" alt="Found it" />113&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/icon_note.gif" alt="Write note" />19&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/icon_remove.gif" alt="Needs Archived" />1&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/icon_disabled.gif" alt="Temporarily Disable Listing" />2&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/icon_enabled.gif" alt="Enable Listing" />1&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/icon_greenlight.gif" alt="Publish Listing" />1&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/icon_maint.gif" alt="Owner Maintenance" />2&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/big_smile.gif" alt="Post Reviewer Note" />3&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</p></span>
__pcresMask["cacheVisits"] = ("<span id=['\"]ctl00_ContentBody_lblFindCounts['\"][^>]*><p[^>]*>(.*?)</p></span>", re.I)
# <img src="/images/icons/icon_smile.gif" alt="Found it" />113
__pcresMask["cacheLogCount"] = ("<img[^>]*alt=\"([^\"]+)\"[^>]*/>([0-9]+)", re.I)

class CacheParser(BaseParser):
    def __init__(self, fetcher, id, logs=False):
        BaseParser.__init__(self, fetcher)
        self.log = logging.getLogger("GCparser.CacheParser")
        self.details = None
        self.id = id
        if pcre("guid").match(id) is not None:
            self.type = "guid"
        else:
            self.type = "waypoint"

        self.url = "http://www.geocaching.com/seek/cache_details.aspx?decrypt=y"
        if self.type == "guid":
            self.url = self.url + "&guid=" + self.id
        else:
            self.url = self.url + "&wp=" + self.id

        if logs:
            self.url = self.url + "&log=y"
            self.logs = None
        else:
            self.logs = False


    def load(self):
        """ Loads data from webpage.
        """
        self._load(self.url, True)


    def getDetails(self):
        """ Returns parsed details of this cache.
        """
        if self.details is not None:
            return self.details

        self.load()

        self.details = {}

        match = pcre("cacheGuid").search(self.data)
        if match is not None:
            self.details["guid"] = match.group(1)
            self.log.log(LOG_PARSER, "guid = {0}".format(self.details["guid"]))
        else:
            self.details["guid"] = ""
            self.log.error("GUID not found.")

        match = pcre("PMonly").search(self.data)
        if match is not None:
            self.log.warn("PM only cache at '{0}'.".format(self.url))
            if self.type == "guid":
                self.details["guid"] = self.id
            else:
                self.details["waypoint"] = self.id
            return self.details

        match = pcre("waypoint").search(self.data)
        if match is not None:
            self.details["waypoint"] = match.group(0)
            self.log.log(LOG_PARSER, "waypoint = {0}".format(self.details["waypoint"]))
        else:
            self.details["waypoint"] = ""
            self.log.error("Waypoint not found.")

        self.details["disabled"] = 0
        self.details["archived"] = 0
        match = pcre("disabled").search(self.data)
        if match is not None:
            if match.group(1) == "has been archived":
                self.details["archived"] = 1
            self.details["disabled"] = 1
            self.log.log(LOG_PARSER, "archived = {0}".format(self.details["archived"]))
            self.log.log(LOG_PARSER, "disabled = {0}".format(self.details["disabled"]))

        match = pcre("cacheDetails").search(self.data)
        if match is not None:
            self.details["name"] = unescape(unescape(match.group(1))).strip()
            self.details["owner"] = unescape(unescape(match.group(2))).strip()
            self.details["hidden"] = "{0:04d}-{1:02d}-{2:02d}".format(int(match.group(5)), int(match.group(3)), int(match.group(4)))
            self.details["size"] = unescape(match.group(6)).strip()
            self.details["difficulty"] = float(match.group(7))
            self.details["terrain"] = float(match.group(8))
            if match.group(10) is not None:
                self.details["province"] = unescape(match.group(10)).strip()
            else:
                self.details["province"] = ""
            self.details["country"] = unescape(match.group(11)).strip()
            self.log.log(LOG_PARSER, "name = {0}".format(self.details["name"]))
            self.log.log(LOG_PARSER, "owner = {0}".format(self.details["owner"]))
            self.log.log(LOG_PARSER, "hidden = {0}".format(self.details["hidden"]))
            self.log.log(LOG_PARSER, "size = {0}".format(self.details["size"]))
            self.log.log(LOG_PARSER, "difficulty = {0:.1f}".format(self.details["difficulty"]))
            self.log.log(LOG_PARSER, "terrain = {0:.1f}".format(self.details["terrain"]))
            self.log.log(LOG_PARSER, "country = {0}".format(self.details["country"]))
            self.log.log(LOG_PARSER, "province = {0}".format(self.details["province"]))
        else:
            self.details["name"] = ""
            self.details["owner"] = ""
            self.details["hidden"] = "1980-01-01"
            self.details["size"] = ""
            self.details["difficulty"] = 0
            self.details["terrain"] = 0
            self.log.error("Could not parse cache details.")

        match = pcre("cacheType").search(self.data)
        if match is not None:
            self.details["type"] = unescape(match.group(1)).strip()
            # GS weird changes bug
            if self.details["type"] == "Unknown Cache":
                self.details["type"] = "Mystery/Puzzle Cache"
            self.log.log(LOG_PARSER, "type = {0}".format(self.details["type"]))
        else:
            self.details["type"] = ""
            self.log.error("Type not found.")

        match = pcre("cacheOwnerId").search(self.data)
        if match is not None:
            self.details["owner_id"] = match.group(1)
            self.log.log(LOG_PARSER, "owner_id = {0}".format(self.details["owner_id"]))
        else:
            self.details["owner_id"] = ""
            self.log.error("Owner id not found.")

        match = pcre("cacheLatLon").search(self.data)
        if match is not None:
            self.details["lat"] = float(match.group(2)) + float(match.group(3))/60
            if match.group(1) == "S":
                self.details["lat"] = -self.details["lat"]
            self.details["lon"] = float(match.group(5)) + float(match.group(6))/60
            if match.group(4) == "W":
                self.details["lon"] = -self.details["lon"]
            self.log.log(LOG_PARSER, "lat = {0:.5f}".format(self.details["lat"]))
            self.log.log(LOG_PARSER, "lon = {0:.5f}".format(self.details["lon"]))
        else:
            self.details["lat"] = 0
            self.details["lon"] = 0
            self.log.error("Lat, lon not found.")

        match = pcre("cacheShortDesc").search(self.data)
        if match is not None:
            self.details["shortDescHTML"] = match.group(1)
            self.details["shortDesc"] = cleanHTML(match.group(1))
            self.log.log(LOG_PARSER, "shortDesc = {0}...".format(self.details["shortDesc"].replace("\n"," ")[0:50]))
        else:
            self.details["shortDescHTML"] = ""
            self.details["shortDesc"] = ""

        match = pcre("cacheLongDesc").search(self.data)
        if match is not None:
            self.details["longDescHTML"] = match.group(1)
            self.details["longDesc"] = cleanHTML(match.group(1))
            self.log.log(LOG_PARSER, "longDesc = {0}...".format(self.details["longDesc"].replace("\n"," ")[0:50]))
        else:
            self.details["longDescHTML"] = ""
            self.details["longDesc"] = ""

        match = pcre("cacheHint").search(self.data)
        if match is not None:
            self.details["hint"] = unescape(match.group(1).replace("<br>", "\n")).strip()
            self.log.log(LOG_PARSER, "hint = {0}...".format(self.details["hint"].replace("\n"," ")[0:50]))
        else:
            self.details["hint"] = ""

        match = pcre("cacheAttributes").search(self.data)
        if match is not None:
            self.details["attributes"] = []
            for item in pcre("cacheAttributesItem").finditer(match.group(1)):
                if item != "blank":
                    self.details["attributes"].append(unescape(item.group(1)).strip())
            self.details["attributes"] = ", ".join(self.details["attributes"])
            self.log.log(LOG_PARSER, "attributes = {0}".format(self.details["attributes"]))
        else:
            self.details["attributes"] = ""

        self.details["inventory"] = {}
        match = pcre("cacheInventory").search(self.data)
        if match is not None:
            for part in match.group(1).split("</li>"):
                match = pcre("cacheInventoryItem").search(part)
                if match is not None:
                    self.details["inventory"][match.group(1)] = unescape(match.group(2)).strip()
            self.log.log(LOG_PARSER, "inventory = {0}".format(self.details["inventory"]))

        self.details["visits"] = {}
        match = pcre("cacheVisits").search(self.data)
        if match is not None:
            for part in match.group(1).split("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"):
                match = pcre("cacheLogCount").search(part)
                if match is not None:
                    self.details["visits"][unescape(match.group(1)).strip()] = int(match.group(2))
            self.log.log(LOG_PARSER, "visits = {0}".format(self.details["visits"]))

        return self.details



""" PCRE: logs list """
# <td><img src="/images/icons/icon_smile.gif" width="16" height="16" alt="Found it" /></td>
__pcresMask["logsFound"] = ("<td[^>]*><img[^>]*(Found it|Webcam Photo Taken|Attended)[^>]*></td>", re.I)
# <td>7/23/2008</td>
__pcresMask["logsDate"] = ("<td[^>]*>([0-9]+)/([0-9]+)/([0-9]+)</td>", re.I)
# <td><a href="http://www.geocaching.com/seek/cache_details.aspx?guid=2bb2acc4-1689-4169-953c-4a69e7ccd43d"><span class="Strike Warning">Zumberk</span></a>&nbsp;</td>
__pcresMask["logsName"] = ("<td[^>]*><a href=['\"][^'\"]*/seek/cache_details.aspx\?guid=([a-z0-9-]+)['\"][^>]*>(<span class=\"Strike Warning\">)?(<strike>)?([^<]+)(</strike>)?[^<]*(</span>)?[^<]*</a>[^<]*</td>", re.I)
# <td><a href="http://www.geocaching.com/seek/log.aspx?LUID=a3e234b3-7d34-4a26-bde5-487e4297133c" target="_blank" title="Visit Log">Visit Log</a></td>
__pcresMask["logsLog"] = ("<td[^>]*><a href=['\"][^'\"]*/seek/log.aspx\?LUID=([a-z0-9-]+)['\"][^>]*>Visit Log</a></td>", re.I)

class MyFindsParser(BaseParser):
    def __init__(self, fetcher):
        BaseParser.__init__(self, fetcher)
        self.log = logging.getLogger("GCparser.MyFindsParser")
        self.cacheList = None
        self.count = None


    def load(self):
        """ Loads data from webpage.
        """
        self._load("http://www.geocaching.com/my/logs.aspx?s=1", True)


    def getList(self):
        """ Returns parsed list of found caches.
        """
        if self.cacheList is not None:
            return self.cacheList

        self.load()

        total = self.getCount()
        self.cacheList = []

        if total > 0:
            cache = None
            for line in self.data.splitlines():
                match = pcre("logsFound").search(line)
                if match is not None:
                    cache = {"sequence":total-len(self.cacheList)}
                    self.log.debug("NEW cache record.")
                    self.log.log(LOG_PARSER, "sequence = {0}".format(cache["sequence"]))

                if cache is not None:
                    if "f_date" not in cache:
                        match = pcre("logsDate").search(line)
                        if match is not None:
                            cache["f_date"] = "{0:04d}-{1:02d}-{2:02d}".format(int(match.group(3)), int(match.group(1)), int(match.group(2)))
                            self.log.log(LOG_PARSER, "f_date = {0}".format(cache["f_date"]))

                    if "guid" not in cache:
                        match = pcre("logsName").search(line)
                        if match is not None:
                            cache["guid"] = match.group(1)
                            cache["name"] = unescape(match.group(4)).strip()
                            if match.group(2):
                                cache["archived"] = 1
                                cache["disabled"] = 1
                            else:
                                cache["archived"] = 0
                                if match.group(3):
                                    cache["disabled"] = 1
                                else:
                                    cache["disabled"] = 0
                            self.log.log(LOG_PARSER, "guid = {0}".format(cache["guid"]))
                            self.log.log(LOG_PARSER, "name = {0}".format(cache["name"]))
                            self.log.log(LOG_PARSER, "disabled = {0}".format(cache["disabled"]))
                            self.log.log(LOG_PARSER, "archived = {0}".format(cache["archived"]))

                    match = pcre("logsLog").search(line)
                    if match is not None:
                        cache["f_luid"] = match.group(1)
                        self.log.log(LOG_PARSER, "f_luid = {0}".format(cache["f_luid"]))
                        self.log.debug("END of cache record '{0}'.".format(cache["name"]))
                        self.cacheList.append(cache)
                        cache = None

        return self.cacheList


    def getCount(self):
        """ Returns total count of found logs.
        """
        if self.count is not None:
            return self.count

        self.load()

        self.count = len(pcre("logsFound").findall(self.data))

        return self.count

""" PCRE: cache search """
# <td class="PageBuilderWidget"><span>Total Records: <b>5371</b> - Page: <b>1</b> of <b>269</b>
__pcresMask["searchTotals"] = ("<td class=\"PageBuilderWidget\"><span>Total Records: <b>([0-9]+)</b> - Page: <b>[0-9]+</b> of <b>([0-9]+)</b>", re.I)
# <img src="/images/icons/compass/NW.gif" alt="NW" />NW<br />0.19mi
__pcresMask["listCompass"] = ("<img src=['\"]/images/icons/compass/[EWNS]+.gif['\"][^>]*>[EWNS]+<br />([0-9.]+)(ft|mi)", re.I)
# <img src="/images/small_profile.gif" alt="Premium Member Only Cache" with="15" height="13" />
__pcresMask["listPMonly"] = ("<img src=['\"]/images/small_profile.gif['\"] alt=['\"]Premium Member Only Cache['\"][^>]*>", re.I)
# <img src="http://www.geocaching.com/images/wpttypes/794.gif" alt="Police Geocaching Squad 2007 Geocoin (1 item(s))" />
__pcresMask["listItem"] = ("<img src=\"[^\"]+wpttypes/[^\"]+\"[^>]*>", re.I)
# (3.5/1.5)<br />
__pcresMask["listDT"] = ("^\s+\(([12345.]+)/([12345.]+)\)<br />", re.I)
# <img src="/images/icons/container/small.gif" alt="Size: Small" />
__pcresMask["listSize"] = ("^\s+<img[^>]*src=['\"][^'\"]*/icons/container/[^'\"]*['\"][^>]*alt=['\"]Size: ([^'\"]+)['\"][^>]*>", re.I)
# 25 Jun 10 <img src="/images/new3.gif" alt="New!" />
__pcresMask["listHidden"] = ("([0-9]+) ([A-Za-z]+) ([0-9]+)( <img[^>]*alt=['\"]New!['\"][^>]*>)?", re.I)
# <a href="/seek/cache_details.aspx?guid=673d255f-45e8-4b91-8c61-a47878ec65de"><span class="Strike">Pribehy Franty Omacky 3.: Dochazi benzin</span></a>
__pcresMask["listName"] = ("<a href=['\"][^'\"]*/seek/cache_details.aspx\?guid=([a-z0-9-]+)['\"]>(<span class=\"Strike\">)?([^<]+)(</span>)?</a>", re.I)
# by Franta Omacka
__pcresMask["listOwner"] = ("^\s*by (.*)\s*$", re.I)
# (GC1NF8Y)<br />
__pcresMask["listWaypoint"] = ("^\s*\((GC[0-9A-Z]+)\)<br />\s*$", re.I)
# Hlavni mesto Praha
__pcresMask["listLocation"] = ("^\s*(.+?)\s*$", re.I)
# 30 Oct 09<br />
__pcresMask["listFoundDate"] = ("^\s*([0-9]+) ([A-Za-z]+) ([0-9]+)<br />\s*$", re.I)
# 2 days ago*<br />
__pcresMask["listFoundDays"] = ("^\s*([0-9]+) days ago((<strong>)?\*(</strong>)?)?<br />\s*$", re.I)
# Yesterday<strong>*</strong><br />
# Today<strong>*</strong><br />
__pcresMask["listFoundWords"] = ("^\s*((Yester|To)day)((<strong>)?\*(</strong>)?)?<br />\s*$", re.I)
# End
__pcresMask["listEnd"] = ("</tr>", re.I)

class SeekParser(BaseParser):
    def __init__(self, fetcher, type="coord", data={}):
        BaseParser.__init__(self, fetcher)
        self.log = logging.getLogger("GCparser.SeekParser")
        self.url = "http://www.geocaching.com/seek/nearest.aspx?"

        if type == "coord":
            if "lat" not in data.keys() or "lon" not in data.keys():
                self.log.critical("'coord' type seek needs 'lat' and 'lon' parameters.")
            if not isinstance(data["lat"], float) or not isinstance(data["lon"], float):
                self.log.critical("LatLon needs to be float.")
            if not "dist" in data.keys() or not isinstance(data["dist"], int):
                data["dist"] = ""
            if data["lat"] == 0:
                data["lat_ns"] = 1
            else:
                data["lat_ns"] = int(data["lat"]/abs(data["lat"]))
            if data["lon"] == 0:
                data["lon_ew"] = 1
            else:
                data["lon_ew"] = int(data["lon"]/abs(data["lon"]))
            data["lat_mmss"] = (data["lat"] - int(abs(data["lat"])))*60
            data["lon_mmss"] = (data["lon"] - int(abs(data["lon"])))*60
            data["lat"] = int(abs(data["lat"]))
            data["lon"] = int(abs(data["lon"]))
            self.url += "lat_ns={lat_ns:d}&lat_h={lat:d}&lat_mmss={lat_mmss:.4f}&long_ew={lon_ew:d}&long_h={lon:d}&long_mmss={lon_mmss:.4f}&dist={dist}&submit8=Search".format(**data)
        else:
            self.log.critical("Uknown seek type.")

        self.page = 0
        self.postData = None
        self.cacheList = []
        self.cacheCount = None
        self.pageCount = None


    def loadNext(self):
        """ Loads data from webpage.
        """
        if self.page >= 1 and self.page >= self.getPageCount():
            return False
        self.page = self.page + 1
        if self.postData is not None:
            self.postData["__EVENTTARGET"] = "ctl00$ContentBody$pgrTop$ctl08"
        self.data = self.fetcher.fetch(self.url, data=self.postData)


    def getNextPage(self):
        """ Returns parsed list of caches from next page, or False.
        """
        if self.postData is not None:
            if self.page >= self.getPageCount():
                return False

        if self.postData is not None or self.data is None:
            self.loadNext()

        if self.postData is None:
            self.postData = {}

        cacheList = []
        cache = None
        for line in self.data.splitlines():
            # POST data
            match = pcre("hiddenInput").search(line)
            if match is not None:
                self.postData[match.group(1)] = match.group(2)

            match = pcre("listCompass").search(line)
            if match is not None:
                self.log.debug("NEW cache record.")
                cache = {"PMonly":False, "items":False, "found":False}
                if match.group(2) == "ft":
                    cache["distance"] = float(match.group(1)) * 0.0003048
                else:
                    cache["distance"] = float(match.group(1)) * 1.609344
                self.log.log(LOG_PARSER, "distance = {0:.3f}".format(cache["distance"]))

            if cache is not None:
                if "type" not in cache:
                    match = pcre("cacheType").search(line)
                    if match is not None:
                        cache["type"] = unescape(match.group(1)).strip()
                        # GS weird changes bug
                        if cache["type"] == "Unknown Cache":
                            cache["type"] = "Mystery/Puzzle Cache"
                        self.log.log(LOG_PARSER, "type = {0}".format(cache["type"]))
                elif "difficulty" not in cache:
                    match = pcre("listPMonly").search(line)
                    if match is not None:
                        cache["PMonly"] = True
                        self.log.log(LOG_PARSER, "PM only cache")

                    match = pcre("listItem").search(line)
                    if match is not None:
                        cache["items"] = True
                        self.log.log(LOG_PARSER, "Has items inside")
                    match = pcre("listDT").search(line)
                    if match is not None:
                        cache["difficulty"] = float(match.group(1))
                        cache["terrain"] = float(match.group(2))
                        self.log.log(LOG_PARSER, "difficulty = {0:.1f}".format(cache["difficulty"]))
                        self.log.log(LOG_PARSER, "terrain = {0:.1f}".format(cache["terrain"]))
                elif "size" not in cache:
                    match = pcre("listSize").search(line)
                    if match is not None:
                        cache["size"] = unescape(match.group(1)).strip()
                        self.log.log(LOG_PARSER, "size = {0}".format(cache["size"]))
                elif "hidden" not in cache:
                    match = pcre("listHidden").search(line)
                    if match is not None:
                        cache["hidden"] = "{0:04d}-{1:02d}-{2:02d}".format(int(match.group(3))+2000, monthsAbbr[match.group(2)], int(match.group(1)))
                        self.log.log(LOG_PARSER, "hidden = {0}".format(cache["hidden"]))
                elif "name" not in cache:
                    match = pcre("listName").search(line)
                    if match is not None:
                        cache["guid"] = match.group(1)
                        cache["name"] = unescape(match.group(3)).strip()
                        if match.group(2):
                            cache["disabled"] = 1
                        else:
                            cache["disabled"] = 0
                        self.log.log(LOG_PARSER, "guid = {0}".format(cache["guid"]))
                        self.log.log(LOG_PARSER, "name = {0}".format(cache["name"]))
                        self.log.log(LOG_PARSER, "disabled = {0}".format(cache["disabled"]))
                elif "owner" not in cache:
                    match = pcre("listOwner").search(line)
                    if match is not None:
                        cache["owner"] = unescape(match.group(1)).strip()
                        self.log.log(LOG_PARSER, "owner = {0}".format(cache["owner"]))
                elif "waypoint" not in cache:
                    match = pcre("listWaypoint").search(line)
                    if match is not None:
                        cache["waypoint"] = match.group(1).strip()
                        self.log.log(LOG_PARSER, "waypoint = {0}".format(cache["waypoint"]))
                elif "location" not in cache:
                    match = pcre("listLocation").search(line)
                    if match is not None:
                        cache["location"] = unescape(match.group(1)).strip()
                        self.log.log(LOG_PARSER, "location = {0}".format(cache["location"]))
                elif not cache["found"]:
                    match = pcre("listFoundDate").search(line)
                    if match is not None:
                        cache["found"] = "{0:04d}-{1:02d}-{2:02d}".format(int(match.group(3))+2000, monthsAbbr[match.group(2)], int(match.group(1)))
                    else:
                        match = pcre("listFoundDays").search(line)
                        if match is not None:
                            date = datetime.datetime.today() - datetime.timedelta(days=int(match.group(1)))
                            cache["found"] = date.strftime("%Y-%m-%d")
                        else:
                            match = pcre("listFoundWords").search(line)
                            if match is not None:
                                date = datetime.datetime.today()
                                if match.group(1) == "Yesterday":
                                    date = date - datetime.timedelta(days=1)
                                cache["found"] = date.strftime("%Y-%m-%d")
                    if cache["found"]:
                        self.log.log(LOG_PARSER, "found = {0}".format(cache["found"]))

                match = pcre("listEnd").search(line)
                if match is not None:
                    if "distance" in cache and "type" in cache and "difficulty" in cache and "size" in cache and "hidden" in cache and "name" in cache and "owner" in cache and "waypoint" in cache and "location" in cache:
                        self.log.debug("END of cache record {0}.".format(cache["name"]))
                        cacheList.append(cache)
                        cache = None
                    else:
                        self.log.warn("Seems like end of cache record, but some keys were not found.")

        if not (len(cacheList) == 20 or (len(cacheList) == self.getCacheCount()%20 and self.page == self.getPageCount())):
            self.log.error("Seems like I missed some caches in the list, got only {0} caches on page {1}/{2}.".format(len(cacheList), self.page, self.getPageCount()))

        self.cacheList.extend(cacheList)
        return cacheList


    def getList(self):
        """ Returns complete parsed list of caches.
        """
        while self.getNextPage():
            pass

        return self.cacheList


    def getPageCount(self):
        """ Returns the number of pages from the search result.
        """
        if self.pageCount is not None:
            return self.pageCount

        if self.data is None:
            self.loadNext()

        self.parseTotals()
        return self.pageCount


    def getCacheCount(self):
        """ Returns the number of caches in the search result.
        """
        if self.cacheCount is not None:
            return self.cacheCount

        if self.data is None:
            self.loadNext()

        self.parseTotals()
        return self.cacheCount


    def parseTotals(self):
        """ Parse cacheCount, pageCount.
        """
        match = pcre("searchTotals").search(self.data)
        if match is not None:
            self.cacheCount = int(match.group(1))
            self.pageCount = int(match.group(2))
        else:
            self.log.error("Could not find cacheCount and pageCount.")



class EditProfile(BaseParser):
    def __init__(self, fetcher, profileData):
        BaseParser.__init__(self, fetcher)
        self.log = logging.getLogger("GCparser.ProfileEdit")
        self.profileData = profileData


    def save(self):
        """ Saves data in user's profile.
        """
        self._load("http://www.geocaching.com/account/editprofiledetails.aspx", True)

        data = {}
        for line in self.data.splitlines():
            match = pcre("hiddenInput").search(line)
            if match is not None:
                data[match.group(1)] = match.group(2)
        data["ctl00$ContentBody$uxProfileDetails"] = self.profileData
        data["ctl00$ContentBody$uxSave"] = "Save Changes"

        self.data = None
        self._load("http://www.geocaching.com/account/editprofiledetails.aspx", True, data=data)



"""
    EXCEPTIONS
"""

class CredentialsException(AssertionError):
    pass

class LoginException(AssertionError):
    pass
