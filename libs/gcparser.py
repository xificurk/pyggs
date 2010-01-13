# -*- coding: utf-8 -*-
"""
    gcparser.py - simple library for parsing geocaching.com website.
    Copyright (C) 2009 Petr Morávek

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

__version__ = "0.3"
__all__ = ["GCparser", "Fetcher", "BaseParser", "CacheParser", "MyFindsParser", "EditProfile", "CredentialsException", "LoginException"]


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
        self.registerParser("cache", CacheParser)
        self.registerParser("editProfile", EditProfile)


    def registerParser(self, name, handler):
        """Register custom parser object"""
        self.parsers[name] = handler


    def parse(self, name, *args, **kwargs):
        """Call parser of the name"""
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
        """Fetch page"""
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
        if data is not None:
            web = opener.open(url, urllib.parse.urlencode(data))
        else:
            web = opener.open(url)

        self.saveUserAgent()
        if authenticate:
            self.saveCookies()

        web = web.read().decode("utf-8")
        if authenticate and check and not self.checkLogin(web):
            self.log.debug("We're not actually logged in, refreshing login and redownloading page.")
            self.login()
            self.fetch(url, authenticate, data)

        return web


    def getCookies(self):
        """Get current cookies, load from file, or create"""
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
        """Try to save cookies, if possible"""
        if isinstance(self.cookies, CJ.LWPCookieJar):
            self.log.debug("Saving cookies.")
            self.cookies.save(ignore_discard=True, ignore_expires=True)


    def userFileName(self):
        """Returns filename to store user's data"""
        if self.username is None or self.dataDir is None:
            return None

        hash = md5(self.username.encode("utf-8")).hexdigest()
        name = ''.join((c for c in unicodedata.normalize('NFD', self.username) if unicodedata.category(c) != 'Mn'))
        name = re.sub("[^a-zA-Z0-9._-]+", "", name, flags=re.A)
        name = name + "_" + hash
        return os.path.join(self.dataDir, name)


    def getUserAgent(self):
        """return current UserAgent, or load from file, or generate random one"""
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
        """Try to save user agent, if possible"""
        if self.userAgent is not None:
            userFile = self.userFileName()
            if userFile is not None:
                UAFile = userFile + ".ua"
                with open(UAFile, "w", encoding="utf-8") as fp:
                    self.log.debug("Saving user agent.")
                    fp.write(self.userAgent)


    def randomUserAgent(self):
        """Generate random UA string - masking as Firefox 3.0.x"""
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
        """Waits for random number of seconds to lessen the load on geocaching.com"""
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
        """Log in to geocaching.com, save cookiejar"""
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
        """Try to log in to geocaching.com"""
        self.log.debug("Attempting to log in.")

        if self.username is None or self.password is None:
            self.log.critical("Cannot log in - no credentials available.")
            raise CredentialsException

        webpage = self.fetch("http://www.geocaching.com/", authenticate=True, check=False)

        data = {}
        data["ctl00$MiniProfile$loginUsername"] = self.username
        data["ctl00$MiniProfile$loginPassword"] = self.password
        data["ctl00$MiniProfile$LoginBtn"] = "Go"
        data["ctl00$MiniProfile$loginRemember"] = "on"

        for line in webpage.splitlines():
            match = re.search('<input type="hidden" name="([^"]+)"[^>]+value="([^"]+)"', line)
            if match:
                data[match.group(1)] = match.group(2)

        webpage = self.fetch("http://www.geocaching.com/Default.aspx", data=data, authenticate=True, check=False)

        logged = False
        for cookie in self.cookies:
            if cookie.name == "userid":
                logged = True

        return logged


    def checkLogin(self, data):
        """Checks the data for not logged in error"""
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
    PARSERS
"""

logging.addLevelName(5, "PARSER")


class BaseParser(object):
    __rot13Trans = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm")
    __unescape = HTMLParser().unescape

    def __init__(self, fetcher):
        self.fetcher = fetcher
        self.data = None


    def _load(self, url, authenticate=False, data=None):
        """Loads data from webpage"""
        if self.data is None:
            self.data = self.fetcher.fetch(url, authenticate=authenticate, data=data)


    def rot13(self, text):
        """Perform rot13"""
        return text.translate(self.__rot13Trans)


    def unescape(self, text):
        """Unescape HTML entities"""
        return self.__unescape(text)


    def cleanHTML(self, text):
        """Cleans text from HTML markup and unescapes entities"""
        text = text.replace("\r", " ")
        text = text.replace("\n", " ")

        text = re.sub("<p[^>]*>", "\n** ", text, flags = re.I)
        text = re.sub("<br[^>]*>", "\n", text, flags = re.I)
        text = re.sub("<li[^>]*>", "\n - ", text, flags = re.I)

        text = re.sub("</?h[0-9][^>]*>", "\n", text, flags = re.I)

        text = re.sub("<img[^>]*alt=['\"]([^'\"]+)['\"][^>]*>", "[img \\1]", text, flags = re.I)
        text = re.sub("<img[^>]*>", "[img]", text, flags = re.I)

        text = re.sub("<[^>]*>", "", text)

        # Escape entities
        text = self.unescape(text)

        # Remove unnecessary spaces
        text = re.sub("^\s+", "", text, flags = re.M)
        text = re.sub("\s+$", "", text, flags = re.M)
        text = re.sub("^\s*$\n", "", text, flags = re.M)
        text = re.sub("\s\s+", " ", text)

        return text



class CacheParser(BaseParser):
    def __init__(self, fetcher, guid=None, waypoint=None, logs=False):
        BaseParser.__init__(self, fetcher)
        self.log = logging.getLogger("GCparser.CacheParser")
        self.details = None
        self.waypoint = waypoint
        self.guid = guid

        if guid is None and waypoint is None:
            self.log.error("No guid or waypoint given - don't know what to parse.")
            raise ValueError

        self.url = "http://www.geocaching.com/seek/cache_details.aspx?pf=y&numlogs=&decrypt=y"
        if guid is not None:
            self.url = self.url + "&guid=" + guid
        else:
            self.url = self.url + "&wp=" + waypoint

        if logs:
            self.url = self.url + "&log=y"
            self.logs = None
        else:
            self.url = self.url + "&log="
            self.logs = False


    def load(self):
        """Loads data from webpage"""
        self._load(self.url, True)


    def getDetails(self):
        """returns parsed details of this cache"""
        if self.details is not None:
            return self.details

        self.load()

        self.details = {}

        match = re.search("<p class=['\"]Warning['\"][^>]*>Sorry, the owner of this listing has made it viewable to Premium Members only", self.data, re.I)
        if match is not None:
            self.log.warn("PM only cache at '{0}'.".format(self.url))
            if self.guid is not None:
                self.details["guid"] = self.guid
            elif self.waypoint is not None:
                self.details["waypoint"] = self.waypoint
            return self.details

        # <span id="ctl00_ContentBody_ErrorText"><p class="OldWarning"><strong>Cache Issues:</strong></p><ul class="OldWarning"><li>This cache is temporarily unavailable. Read the logs below to read the status for this cache.</li></ul></span>
        self.details["disabled"] = 0
        self.details["archived"] = 0
        match = re.search("<p class=['\"]OldWarning['\"][^>]*><strong>Cache Issues:</strong></p><ul[^>]*><li>This cache (has been archived|is temporarily unavailable)[^<]*</li>", self.data, re.I)
        if match is not None:
            if match.group(1) == "has been archived":
                self.details["archived"] = 1
            self.details["disabled"] = 1
            self.log.log(5, "archived = {0}".format(self.details["archived"]))
            self.log.log(5, "disabled = {0}".format(self.details["disabled"]))

        match = re.search("GC[A-Z0-9]+", self.data)
        if match is not None:
            self.details["waypoint"] = match.group(0)
            self.log.log(5, "waypoint = {0}".format(self.details["waypoint"]))
        else:
            self.details["waypoint"] = ""
            self.log.error("Waypoint not found.")

        # <span id="ctl00_ContentBody_CacheName">Jazyky</span>
        match = re.search("<span id=['\"]ctl00_ContentBody_CacheName['\"]>([^<]+)</span>", self.data, re.I)
        if match is not None:
            self.details["name"] = self.unescape(match.group(1)).strip()
            self.log.log(5, "name = {0}".format(self.details["name"]))
        else:
            self.details["name"] = ""
            self.log.error("Name not found.")

        # <span id="ctl00_ContentBody_DateHidden">6/13/2008</span>
        match = re.search("<span id=['\"]ctl00_ContentBody_DateHidden['\"]>([0-9]+)/([0-9]+)/([0-9]+)</span>", self.data, re.I)
        if match is not None:
            self.details["hidden"] = "{0:04d}-{1:02d}-{2:02d}".format(int(match.group(3)), int(match.group(1)), int(match.group(2)))
            self.log.log(5, "hidden = {0}".format(self.details["hidden"]))
        else:
            # <span id="ctl00_ContentBody_DateHidden">Saturday, January 16, 2010</span>
            match = re.search("<span id=['\"]ctl00_ContentBody_DateHidden['\"]>[A-Za-z]+, ([A-Za-z]+) ([0-9]+), ([0-9]+)</span>", self.data, re.I)
            if match is not None:
                month = {"January":1, "February":2, "March":3, "April":4, "May":5, "June":6, "July":7, "August":8, "September":9, "October":10, "November":11, "December":12}[match.group(1)]
                self.details["hidden"] = "{0:04d}-{1:02d}-{2:02d}".format(int(match.group(3)), month, int(match.group(2)))
                self.log.log(5, "hidden = {0}".format(self.details["hidden"]))
            else:
                self.details["hidden"] = "1980-01-01"
                self.log.error("Hidden date not found.")

        # <span id="ctl00_ContentBody_CacheOwner">Letterbox Hybrid<br />Size: Regular<br />by <a href="http://www.geocaching.com/profile/?guid=d5a1fb67-d246-4d6a-b835-20b1be093b87&wid=8583f541-dfcf-4690-99f3-73430e7c0f52&ds=2">onovy, cherubin</a></span>
        match = re.search("<span id=['\"]ctl00_ContentBody_CacheOwner['\"]>([^<]+)<br />Size: ([^<]+)<br />by <a href=['\"]http://www.geocaching.com/profile/\?guid=([a-z0-9-]+)&wid=([a-z0-9-]+)[^'\"]*['\"]>([^<]+)</a></span>", self.data, re.I)
        if match is not None:
            self.details["type"] = self.unescape(match.group(1)).strip()
            # GS weird changes bug
            if self.details["type"] == "Unknown Cache":
                self.details["type"] = "Mystery/Puzzle Cache"
            self.details["size"] = self.unescape(match.group(2)).strip()
            self.details["guid"] = match.group(4)
            self.details["owner"] = self.unescape(match.group(5)).strip()
            self.details["owner_id"] = match.group(3)
            self.log.log(5, "guid = {0}".format(self.details["guid"]))
            self.log.log(5, "type = {0}".format(self.details["type"]))
            self.log.log(5, "size = {0}".format(self.details["size"]))
            self.log.log(5, "owner = {0}".format(self.details["owner"]))
            self.log.log(5, "owner_id = {0}".format(self.details["owner_id"]))
        else:
            self.details["type"] = ""
            self.details["size"] = ""
            self.details["guid"] = ""
            self.details["owner"] = ""
            self.details["owner_id"] = ""
            self.log.error("Type, size, guid, owner, owner_id not found.")

        # <span id="ctl00_ContentBody_Difficulty"><img src="http://www.geocaching.com/images/stars/stars3.gif" alt="3 out of 5" /></span>
        match = re.search("<span id=['\"]ctl00_ContentBody_Difficulty['\"]><img src=['\"]http://www.geocaching.com/images/stars/[^\"']*['\"] alt=['\"]([0-9.]+) out of 5['\"]", self.data, re.I)
        if match is not None:
            self.details["difficulty"] = float(match.group(1))
            self.log.log(5, "difficulty = {0:.1f}".format(self.details["difficulty"]))
        else:
            self.details["difficulty"] = 0
            self.log.error("Difficulty not found.")

        # <span id="ctl00_ContentBody_Terrain"><img src="http://www.geocaching.com/images/stars/stars1_5.gif" alt="1.5 out of 5" /></span>
        match = re.search("<span id=['\"]ctl00_ContentBody_Terrain['\"]><img src=['\"]http://www.geocaching.com/images/stars/[^\"']*['\"] alt=['\"]([0-9.]+) out of 5['\"]", self.data, re.I)
        if match is not None:
            self.details["terrain"] = float(match.group(1))
            self.log.log(5, "terrain = {0:.1f}".format(self.details["terrain"]))
        else:
            self.details["terrain"] = 0
            self.log.error("Terrain not found.")

        # <span id="ctl00_ContentBody_LatLon" style="font-weight:bold;">N 50° 02.173 E 015° 46.386</span>
        match = re.search("<span id=['\"]ctl00_ContentBody_LatLon['\"][^>]*>([NS]) ([0-9]+)° ([0-9.]+) ([WE]) ([0-9]+)° ([0-9.]+)</span>", self.data, re.I)
        if match is not None:
            self.details["lat"] = float(match.group(2)) + float(match.group(3))/60
            if match.group(1) == "S":
                self.details["lat"] = -self.details["lat"]
            self.details["lon"] = float(match.group(5)) + float(match.group(6))/60
            if match.group(4) == "W":
                self.details["lon"] = -self.details["lon"]
            self.log.log(5, "lat = {0:.5f}".format(self.details["lat"]))
            self.log.log(5, "lon = {0:.5f}".format(self.details["lon"]))
        else:
            self.details["lat"] = 0
            self.details["lon"] = 0
            self.log.error("Lat, lon not found.")

        self.details["province"] = ""
        # <span id="ctl00_ContentBody_Location">In Pardubicky kraj, Czech Republic</span>
        match = re.search("<span id=['\"]ctl00_ContentBody_Location['\"]>In (([^,<]+), )?([^<]+)</span>", self.data, re.I)
        if match is not None:
            self.details["country"] = self.unescape(match.group(3)).strip()
            if match.group(2) is not None:
                self.details["province"] = self.unescape(match.group(2)).strip()
                self.log.log(5, "province = {0}".format(self.details["province"]))
            self.log.log(5, "country = {0}".format(self.details["country"]))
        else:
            self.details["country"] = ""
            self.log.error("Country not found.")

        match = re.search("<span id=['\"]ctl00_ContentBody_ShortDescription['\"]>(.*?)</span><div class=\"Clear\"></div>", self.data, re.I|re.S)
        if match is not None:
            self.details["shortDescHTML"] = match.group(1)
            self.details["shortDesc"] = self.cleanHTML(match.group(1))
            self.log.log(5, "shortDesc = {0}...".format(self.details["shortDesc"].replace("\n"," ")[0:50]))
        else:
            self.details["shortDescHTML"] = ""
            self.details["shortDesc"] = ""

        match = re.search("<span id=['\"]ctl00_ContentBody_LongDescription['\"]>(.*?)</span>\s*\n\s+<p>\s+</p>\s+</td>", self.data, re.I|re.S)
        if match is not None:
            self.details["longDescHTML"] = match.group(1)
            self.details["longDesc"] = self.cleanHTML(match.group(1))
            self.log.log(5, "longDesc = {0}...".format(self.details["longDesc"].replace("\n"," ")[0:50]))
        else:
            self.details["longDescHTML"] = ""
            self.details["longDesc"] = ""

        # <span id="ctl00_ContentBody_Hints" class="displayMe">Esoteric programming language<br></span>
        match = re.search("<span id=['\"]ctl00_ContentBody_Hints['\"][^>]*>(.*?)</span>", self.data, re.I)
        if match is not None:
            self.details["hint"] = self.unescape(match.group(1).replace("<br>", "\n")).strip()
            self.log.log(5, "hint = {0}...".format(self.details["hint"].replace("\n"," ")[0:50]))
        else:
            self.details["hint"] = ""

        # <p class="NoSpacing"><small><a href="/about/icons.aspx" title="What are Attributes?">What are Attributes?</a></small></p>stroller accessible, stealth required, recommended at night, available 24-7, bikes allowed, takes less than 1  hour, telephone nearby, public transit available, parking available, dogs allowed
        match = re.search("<p[^>]*><small><a href=['\"]/about/icons\.aspx['\"] title=['\"]What are Attributes\?['\"]>What are Attributes\?</a></small></p>([^<]+)", self.data, re.I)
        if match is not None:
            self.details["attributes"] = self.unescape(match.group(1)).strip()
            self.log.log(5, "attributes = {0}".format(self.details["attributes"]))
        else:
            self.details["attributes"] = ""

        self.details["inventory"] = {}
        # <img src="/images/WptTypes/sm/tb_coin.gif" width="16" height="16" alt="Inventory" />&nbsp;Inventory</h3>
        # <p class="NoSpacing"><a href="/track/search.aspx?wid=31908057-2da9-460b-a02c-3a246ffca7e7&ccid=1372939">more...</a><br /><a href="/track/search.aspx?wid=31908057-2da9-460b-a02c-3a246ffca7e7">See the history...</a><br /><a href="/track/faq.aspx" title="What is a Travel Bug?">What is a Travel Bug?</a></p>
        match = re.search("<img src=['\"]/images/WptTypes/sm/tb_coin\.gif['\"][^>]*>[^<]*?Inventory</h3>[^<]*<div class=['\"]WidgetBody['\"]>[^<]*<ul[^>]*>(.*?)</ul>[^<]*<p[^>]*>[^<]*<a[^>]*>(more\.\.\.|See the history)</a>", self.data, re.I|re.S)
        if match is not None:
            for part in match.group(1).split("</li>"):
                # <a href="http://www.geocaching.com/track/details.aspx?guid=bbf74f7a-510e-4a3c-8ebf-5eb140b40440">**Voortrekkers** Racenijntje</a>
                match = re.search("<a href=['\"]http://www.geocaching.com/track/details.aspx\?guid=([a-z0-9-]+)['\"]>([^<]+)</a>", part, re.I)
                if match is not None:
                    self.details["inventory"][match.group(1)] = self.unescape(match.group(2)).strip()
            self.log.log(5, "inventory = {0}".format(self.details["inventory"]))

        self.details["visits"] = {}
        # <span id="ctl00_ContentBody_lblFindCounts"><p><img src="/images/icons/icon_smile.gif" alt="Found it" />113&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/icon_note.gif" alt="Write note" />19&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/icon_remove.gif" alt="Needs Archived" />1&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/icon_disabled.gif" alt="Temporarily Disable Listing" />2&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/icon_enabled.gif" alt="Enable Listing" />1&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/icon_greenlight.gif" alt="Publish Listing" />1&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/icon_maint.gif" alt="Owner Maintenance" />2&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/big_smile.gif" alt="Post Reviewer Note" />3&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</p></span>
        match = re.search("<span id=['\"]ctl00_ContentBody_lblFindCounts['\"][^>]*><p[^>]*>(.*?)</p></span>", self.data, re.I)
        if match is not None:
            for part in match.group(1).split("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"):
                # <img src="/images/icons/icon_smile.gif" alt="Found it" />113
                match = re.search("<img[^>]*alt=\"([^\"]+)\"[^>]*/>([0-9]+)", part, re.I)
                if match is not None:
                    self.details["visits"][self.unescape(match.group(1)).strip()] = int(match.group(2))
            self.log.log(5, "visits = {0}".format(self.details["visits"]))

        return self.details



class MyFindsParser(BaseParser):
    def __init__(self, fetcher):
        BaseParser.__init__(self, fetcher)
        self.log = logging.getLogger("GCparser.MyFindsParser")
        self.cacheList = None
        self.count = None


    def load(self):
        """Loads data from webpage"""
        self._load("http://www.geocaching.com/my/logs.aspx?s=1", True)


    def getList(self):
        """returns parsed list of found caches"""
        if self.cacheList is not None:
            return self.cacheList

        self.load()

        total = self.getCount()
        self.cacheList = []

        if total > 0:
            """
                <td><img src="/images/icons/icon_smile.gif" width="16" height="16" alt="Found it" /></td>
                <td>7/23/2008</td>
                <td><a href="http://www.geocaching.com/seek/cache_details.aspx?guid=2bb2acc4-1689-4169-953c-4a69e7ccd43d"><span class="Strike Warning">Zumberk</span></a>&nbsp;</td>
                <td>Czech Republic &nbsp;</td>
                <td><a href="http://www.geocaching.com/seek/log.aspx?LUID=a3e234b3-7d34-4a26-bde5-487e4297133c" target="_blank" title="Visit Log">Visit Log</a></td>
            """
            cache = None
            for line in self.data.splitlines():
                match = re.search("<td[^>]*><img[^>]*(Found it|Webcam Photo Taken|Attended)[^>]*></td>", line, re.I)
                if match is not None:
                    cache = {"sequence":total-len(self.cacheList)}
                    self.log.debug("NEW cache record")
                    self.log.log(5, "sequence = {0}".format(cache["sequence"]))

                if cache is not None:
                    if "f_date" not in cache:
                        match = re.search("<td[^>]*>([0-9]+)/([0-9]+)/([0-9]+)</td>", line, re.I)
                        if match is not None:
                            cache["f_date"] = "{0:04d}-{1:02d}-{2:02d}".format(int(match.group(3)), int(match.group(1)), int(match.group(2)))
                            self.log.log(5, "f_date = {0}".format(cache["f_date"]))

                    if "guid" not in cache:
                        match = re.search("<td[^>]*><a href=['\"]http://www.geocaching.com/seek/cache_details.aspx\?guid=([a-z0-9-]+)['\"][^>]*>(<span class=\"Strike Warning\">)?(<strike>)?([^<]+)(</strike>)?[^<]*(</span>)?[^<]*</a>[^<]*</td>", line, re.I)
                        if match is not None:
                            cache["guid"] = match.group(1)
                            cache["name"] = self.unescape(match.group(4)).strip()
                            if match.group(2):
                                cache["archived"] = 1
                                cache["disabled"] = 1
                            else:
                                cache["archived"] = 0
                                if match.group(3):
                                    cache["disabled"] = 1
                                else:
                                    cache["disabled"] = 0
                            self.log.log(5, "guid = {0}".format(cache["guid"]))
                            self.log.log(5, "name = {0}".format(cache["name"]))
                            self.log.log(5, "disabled = {0}".format(cache["disabled"]))
                            self.log.log(5, "archived = {0}".format(cache["archived"]))

                    match = re.search("<td[^>]*><a href=['\"]http://www.geocaching.com/seek/log.aspx\?LUID=([a-z0-9-]+)['\"][^>]*>Visit Log</a></td>", line, re.I)
                    if match is not None:
                        cache["f_luid"] = match.group(1)
                        self.log.log(5, "f_luid = {0}".format(cache["f_luid"]))
                        self.log.debug("END of cache record '{0}'".format(cache["name"]))
                        self.cacheList.append(cache)
                        cache = None

        return self.cacheList


    def getCount(self):
        """returns total count of found logs"""
        if self.count is not None:
            return self.count

        self.load()

        self.count = len(re.findall("<td[^>]*><img[^>]*(Found it|Webcam Photo Taken|Attended)[^>]*></td>", self.data, re.I))

        return self.count



class EditProfile(BaseParser):
    def __init__(self, fetcher, profileData):
        BaseParser.__init__(self, fetcher)
        self.log = logging.getLogger("GCparser.ProfileEdit")
        self.profileData = profileData


    def save(self):
        """Saves data in user's profile"""
        self._load("http://www.geocaching.com/account/editprofiledetails.aspx", True)

        data = {}
        for line in self.data.splitlines():
            match = re.search('<input type="hidden" name="([^"]+)"[^>]+value="([^"]+)"', line)
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
