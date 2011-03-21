# -*- coding: utf-8 -*-
"""
Parsing geocaching.com website.

Classes:
    HTTPInterface       --- Interface retrieving/sending data directly.
                            from/to geocaching.com website.
    BaseParser          --- Define common parts for all parsers.
    CacheDetails        --- Parse cache details from webpage source.
    MyGeocachingLogs    --- Parse and filter the list of my logs from webpage source.
    SeekCache           --- Parse caches in seek query from webpage source.
    Profile             --- Manage user's profile.
    CredentialsError    --- Raised on invalid credentials.
    LoginError          --- Raised when geocaching.com login fails.

"""

__author__ = "Petr Morávek (xificurk@gmail.com)"
__copyright__ = "Copyright (C) 2009-2011 Petr Morávek"
__license__ = "GPL"

__version__ = "0.7.0"

from collections import defaultdict, namedtuple, Sequence
from datetime import date, datetime, timedelta
from hashlib import md5
from html.parser import HTMLParser
from http.cookiejar import CookieJar, LWPCookieJar
import logging
import os.path
from random import randint
import re
from time import time, sleep
import unicodedata
import urllib.parse
import urllib.request


__all__ = ["HTTPInterface",
           "BaseParser",
           "CacheDetails",
           "MyGeocachingLogs",
           "SeekCache",
           "Profile",
           "Credentials",
           "CacheLog",
           "LogItem",
           "CredentialsError",
           "LoginError"]


############################################################
### Exceptions                                           ###
############################################################

class CredentialsError(ValueError):
    """
    Raised on invalid credentials.

    """
    pass


class LoginError(AssertionError):
    """
    Raised when geocaching.com login fails.

    """
    pass



############################################################
### Data containers & design patterns                    ###
############################################################

Credentials = namedtuple("Credentials", "username password")
CacheLog = namedtuple("CacheLog", "luid type date user user_id text")
LogItem = namedtuple("LogItem", "luid type date cache")


class StaticClass:
    """
    Raise TypeError when attempting to create an instance.

    """

    def __new__(cls, *p, **k):
        raise TypeError("This class cannot be instantionalized.")



############################################################
### HTTP interface.                                      ###
############################################################

class HTTPInterface(StaticClass):
    """
    Interface retrieving/sending data directly from/to geocaching.com website.
    Cannot be instantionalized.

    Attributes:
        stats            --- Dictionary with download stats of pages with auth=True.
        request_avg_time --- Desired average request sleep time for pages with
                             auth=True.

    Methods:
        set_credentials --- Set credentials to use for geocaching.com login.
        set_data_dir    --- Set data directory for for storing cookies,
                            user_agent, download stats...
        request         --- Retrive/send data from/to geocaching.com website.
        wait            --- Handle wait time to lessen the load on geocaching.com
                            website.

    """

    _log = logging.getLogger("gcparser.http")
    _data_dir = None
    _credentials = Credentials(None, None)
    _cookies = None
    _user_agent = None
    _last_download = 0
    _first_download = 0
    _download_count = 0

    stats = defaultdict(int)
    request_avg_time = 600

    @classmethod
    def set_credentials(cls, credentials):
        """
        Set credentials to use for geocaching.com login.

        Arguments:
            credentials --- Credentials instance.

        """
        if not isinstance(credentials, Credentials):
            raise CredentialsError("Credentials must be an instance of Credentials.")
        if credentials.username is None or credentials.password is None:
            cls._log.warn("No geocaching.com credentials given, some features won't be accessible.")
        cls._credentials = credentials
        cls._load_stats()

    @classmethod
    def set_data_dir(cls, data_dir=None):
        """
        Set data directory for for storing cookies, user_agent, download stats...

        Keyworded arguments:
            data_dir    --- Path to data directory (use '~' as a link to user's
                            home directory)

        """
        if data_dir is None:
            cls._log.warn("No data directory provided, caching will be disabled.")
            cls._data_dir = None
        else:
            data_dir = os.path.expanduser(data_dir)
            if os.path.isdir(data_dir):
                cls._log.debug("Setting data directory to '{0}'.".format(data_dir))
                cls._data_dir = data_dir
            else:
                cls._log.warn("Data directory '{0}' does not exist, caching will be disabled.".format(data_dir))
                cls._data_dir = None
        cls._load_stats()

    @classmethod
    def request(cls, url, auth=False, data=None, check=True):
        """
        Retrive/send data from/to geocaching.com website.

        Arguments:
            url         --- Webpage URL.

        Keyworded arguments:
            auth        --- Authenticate before request.
            data        --- Data to send with request.
            check       --- Re-check if we're logged in after download.

        """
        if auth:
            cookies = cls._get_cookies()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
        else:
            opener = urllib.request.build_opener()
        headers = []
        headers.append(("User-agent", cls._get_user_agent()))
        headers.append(("Accept", "text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8"))
        headers.append(("Accept-Language", "en-us,en;q=0.5"))
        headers.append(("Accept-Charset", "utf-8,*;q=0.5"))
        opener.addheaders = headers
        cls.wait(auth)
        cls._log.debug("Downloading page '{0}'.".format(url))
        webpage = cls._download_webpage(opener, url, data)
        if auth:
            cls._save_cookies()
            today = date.today().isoformat()
            cls.stats[today] += 1
            cls._save_stats()
        webpage = webpage.read().decode("utf-8")
        if auth and check and not cls._check_login(webpage):
            cls._log.debug("We're not actually logged in, refreshing login and redownloading page.")
            cls._login()
            return cls.request(url, auth=auth, data=data)
        return webpage

    @classmethod
    def _download_webpage(cls, opener, url, data, retry=1):
        """ Download the page. """
        try:
            if data is not None:
                webpage = opener.open(url, urllib.parse.urlencode(data).encode("utf-8"))
            else:
                webpage = opener.open(url)
        except IOError:
            cls._log.error("An error occured while downloading '{0}', will retry in {1} seconds.".format(url, retry))
            sleep(retry)
            return cls._download_webpage(opener, url, data, retry=min(5*retry, 600))
        return webpage

    @classmethod
    def _user_file_name(cls):
        """ Returns filename to store user's data. """
        username = cls._credentials.username
        if username is None or cls._data_dir is None:
            return None
        hash_ = md5(username.encode("utf-8")).hexdigest()
        name = unicodedata.normalize("NFKD", username).encode("ascii", "ignore").decode("ascii")
        name = _pcre("file_mask").sub("", name)
        name = name + "_" + hash_
        return os.path.join(cls._data_dir, name)

    @classmethod
    def _get_cookies(cls):
        """ Get cookies - load from file, or create. """
        if cls._cookies is not None:
            return cls._cookies
        user_file = cls._user_file_name()
        if user_file is None:
            cls._log.debug("Cannot load cookies - invalid filename.")
            cls._cookies = CookieJar()
            cls._login()
        else:
            cookie_file = user_file + ".cookies"
            if os.path.isfile(cookie_file):
                cls._log.debug("Re-using stored cookies.")
                cls._cookies = LWPCookieJar(cookie_file)
                cls._cookies.load(ignore_discard=True)
                logged = False
                for cookie in cls._cookies:
                    if cookie.name == "userid":
                        logged = True
                        break
                if not logged:
                    cls._login()
            else:
                cls._log.debug("No stored cookies, creating new.")
                cls._cookies = LWPCookieJar(cookie_file)
                cls._login()
        return cls._cookies

    @classmethod
    def _save_cookies(cls):
        """ Try to save cookies, if possible. """
        if isinstance(cls._cookies, LWPCookieJar):
            cls._log.debug("Saving cookies.")
            cls._cookies.save(ignore_discard=True, ignore_expires=True)

    @classmethod
    def _get_user_agent(cls):
        """ Return current user_agent, or load from file, or generate random one. """
        if cls._user_agent is not None:
            return cls._user_agent
        user_file = cls._user_file_name()
        if user_file is None:
            cls._user_agent = cls._generate_user_agent()
        else:
            ua_file = user_file + ".ua"
            if os.path.isfile(ua_file):
                with open(ua_file, "r", encoding="utf-8") as fp:
                    cls._log.debug("Loading user agent.")
                    cls._user_agent = fp.read()
            else:
                cls._user_agent = cls._generate_user_agent()
                cls._save_user_agent()
        return cls._user_agent

    @classmethod
    def _save_user_agent(cls):
        """ Try to save user agent, if possible. """
        if cls._user_agent is None:
            return
        user_file = cls._user_file_name()
        if user_file is None:
            return
        ua_file = user_file + ".ua"
        with open(ua_file, "w", encoding="utf-8") as fp:
            cls._log.debug("Saving user agent.")
            fp.write(cls._user_agent)

    @classmethod
    def _generate_user_agent(cls):
        """ Generate random user_agent string - masking as Firefox 3.0.x. """
        cls._log.debug("Generating user agent.")
        system = randint(1, 5)
        if system <= 1:
            system = "X11"
            system_version = ["Linux i686", "Linux x86_64"]
        elif system <= 2:
            system = "Macintosh"
            system_version = ["PPC Mac OS X 10.5"]
        else:
            system = "Windows"
            system_version = ["Windows NT 5.1", "Windows NT 6.0", "Windows NT 6.1"]
        system_version = system_version[randint(0, len(system_version) - 1)]
        version = randint(1, 13)
        date = "200907{0:02d}{1:02d}".format(randint(1, 31), randint(1, 23))
        return "Mozilla/5.0 ({0}; U; {1}; en-US; rv:1.9.0.{2:d}) Gecko/{3} Firefox/3.0.{2:d}".format(system, system_version, version, date)

    @classmethod
    def _load_stats(cls):
        """ Load download stats from file. """
        cls.stats = defaultdict(int)
        user_file = cls._user_file_name()
        if user_file is None:
            return
        stats_file = user_file + ".stats"
        if os.path.isfile(stats_file):
            today = date.today()
            timeout = today - timedelta(days=93)
            with open(stats_file, "r", encoding="utf-8") as fp:
                cls._log.debug("Loading stats.")
                for line in fp.readlines():
                    line = line.strip()
                    if not line:
                        continue
                    line = line.split("\t")
                    download_date = line[0].split("-")
                    download_date = date(int(download_date[0]), int(download_date[1]), int(download_date[2]))
                    download_count = int(line[1])
                    if download_date > timeout:
                        cls.stats[download_date.isoformat()] = download_count

    @classmethod
    def _save_stats(cls):
        """ Try to save stats, if possible. """
        user_file = cls._user_file_name()
        if user_file is None:
            return
        stats_file = user_file + ".stats"
        with open(stats_file, "w", encoding="utf-8") as fp:
            cls._log.debug("Saving stats.")
            for download_date, download_count in cls.stats.items():
                fp.write("{0}\t{1}\n".format(download_date, download_count))

    @classmethod
    def _login(cls):
        """ Log in to geocaching.com, save cookiejar. """
        if not cls._login_attempt():
            cls._log.debug("Not logged in, re-trying.")
            if not cls._login_attempt():
                cls._log.critical("Login error.")
                raise LoginError
        cls._log.debug("Logged in.")

    @classmethod
    def _login_attempt(cls):
        """ Attempt to log in to geocaching.com. """
        cls._log.debug("Attempting to log in.")
        if cls._credentials.username is None or cls._credentials.password is None:
            raise CredentialsError("Cannot log in - no credentials available.")
        webpage = cls.request("http://www.geocaching.com/", auth=True, check=False)
        data = {}
        data["ctl00$MiniProfile$loginUsername"] = cls._credentials.username
        data["ctl00$MiniProfile$loginPassword"] = cls._credentials.password
        data["ctl00$MiniProfile$LoginBtn"] = "Login"
        data["ctl00$MiniProfile$uxRememberMe"] = "on"
        data["ctl00$ContentBody$GCCode"] = "GC"
        data["ctl00$ContentBody$saddress"] = "98103"
        for hidden_input in _pcre("hidden_input").findall(webpage):
            data[hidden_input[0]] = hidden_input[1]
        webpage = cls.request("http://www.geocaching.com/Default.aspx", data=data, auth=True, check=False)
        for cookie in cls._cookies:
            cls._log.debug("{0}: {1}".format(cookie.name, cookie.value))
            if cookie.name == "userid":
                return True
        return False

    @classmethod
    def _check_login(cls, data):
        """ Checks the downloaded data and determines if we're logged in. """
        cls._log.debug("Checking if we're really logged in...")
        if data is not None:
            for line in data.splitlines():
                if line.find("You are not logged in.") != -1:
                    return False
        return True

    @classmethod
    def wait(cls, auth):
        """
        Handle wait time to lessen the load on geocaching.com website.

        Arguments:
            auth        --- Is this for a page where autentication is needed?

        """
        if not auth:
            sleep_time = 1
        else:
            # No request for a long time => reset _first_download value using desired average.
            cls._first_download = max(time() - cls._download_count * cls.request_avg_time, cls._first_download)
            # Calculate number of downloaded pages ahead of expected average
            count = cls._download_count - int((time() - cls._first_download) / cls.request_avg_time)
            # sleep time 1s: 10/10s => overall 10/10s
            if count < 10:
                sleep_time = 1
            # sleep time 2-8s: 40/3.3m => overall 50/3.5min
            elif count < 50:
                sleep_time = randint(2, 8)
            # sleep time 5-35s: 155/51.6m => overall 205/55.1min
            elif count < 200:
                sleep_time = randint(5, 35)
            # sleep time 10-50s: 315/2.6h => overall 520/3.5h
            elif count < 500:
                sleep_time = randint(10, 50)
            # sleep time 20-80s
            else:
                sleep_time = randint(20, 80)
            cls._download_count += 1
        cls._log.debug("Waiting for {0} seconds.".format(sleep_time))
        sleep(max(0, cls._last_download + sleep_time - time()))
        cls._last_download = time()


HTTPInterface.set_data_dir("~/.geocaching/parser")



############################################################
### Helpers.                                             ###
############################################################

_months_abbr = {"Jan":1, "Feb":2, "Mar":3, "Apr":4, "May":5, "Jun":6, "Jul":7, "Aug":8, "Sep":9, "Oct":10, "Nov":11, "Dec":12}
_months_full = {"January":1, "February":2, "March":3, "April":4, "May":5, "June":6, "July":7, "August":8, "September":9, "October":10, "November":11, "December":12}
_cache_types = {}
_cache_types["2"] = "Traditional Cache"
_cache_types["3"] = "Multi-cache"
_cache_types["8"] = "Mystery/Puzzle Cache"
_cache_types["5"] = "Letterbox Hybrid"
_cache_types["earthcache"] = "Earthcache"
_cache_types["1858"] = "Wherigo Cache"
_cache_types["6"] = "Event Cache"
_cache_types["4"] = "Virtual Cache"
_cache_types["11"] = "Webcam Cache"
_cache_types["13"] = "Cache In Trash Out Event"
_cache_types["mega"] = "Mega-Event Cache"
_cache_types["3653"] = "Lost and Found Event Cache"

def _clean_HTML(text):
    """ Cleans text from HTML markup and unescapes entities. """
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")
    text = _pcre("HTMLp").sub("\n** ", text)
    text = _pcre("HTMLbr").sub("\n", text)
    text = _pcre("HTMLli").sub("\n - ", text)
    text = _pcre("HTMLh").sub("\n", text)
    text = _pcre("HTMLimg_wink").sub(" ;-) ", text)
    text = _pcre("HTMLimg_smile_big").sub(" :D ", text)
    text = _pcre("HTMLimg_smile").sub(" :-) ", text)
    text = _pcre("HTMLimgalt").sub("[img \\1]", text)
    text = _pcre("HTMLimg").sub("[img]", text)
    text = _pcre("HTMLtag").sub("", text)
    # Escape entities
    text = _unescape(text)
    # Remove unnecessary spaces
    text = _pcre("blank_line").sub("", text)
    text = _pcre("double_space").sub(" ", text)
    return text

_unescape = HTMLParser().unescape

_pcres = {}
_pcre_masks = {}

def _pcre(name):
    """ Return compiled PCRE. """
    if name not in _pcre_masks:
        logging.getLogger("gcparser.helpers").error("Uknown PCRE '{0}'.".format(name))
        name = "null"
    if name not in _pcres:
        _pcres[name] = re.compile(*_pcre_masks[name])
    return _pcres[name]

########################################
# PCRE: System.                        #
########################################
_pcre_masks["null"] = (".*", 0)
_pcre_masks["file_mask"] = ("[^a-zA-Z0-9._-]+", re.A)

########################################
# PCRE: HTML.                        #
########################################
_pcre_masks["HTMLp"] = ("<p[^>]*>", re.I)
_pcre_masks["HTMLbr"] = ("<br[^>]*>", re.I)
_pcre_masks["HTMLli"] = ("<li[^>]*>", re.I)
_pcre_masks["HTMLh"] = ("</?h[0-9][^>]*>", re.I)
_pcre_masks["HTMLimg_wink"] = ("<img\s+src=\s*['\"]http://www\.geocaching\.com/images/icons/icon_smile_wink\.gif['\"][^>]*>", re.I)
_pcre_masks["HTMLimg_smile"] = ("<img\s+src=\s*['\"]http://www\.geocaching\.com/images/icons/icon_smile\.gif['\"][^>]*>", re.I)
_pcre_masks["HTMLimg_smile_big"] = ("<img\s+src=\s*['\"]http://www\.geocaching\.com/images/icons/icon_smile_big\.gif['\"][^>]*>", re.I)
_pcre_masks["HTMLimgalt"] = ("<img[^>]*alt=['\"]([^'\"]+)['\"][^>]*>", re.I)
_pcre_masks["HTMLimg"] = ("<img[^>]*>", re.I)
_pcre_masks["HTMLtag"] = ("<[^>]*>", re.I)
_pcre_masks["blank_line"] = ("^\s+|\s+$|^\s*$\n", re.M)
_pcre_masks["double_space"] = ("\s\s+", 0)



############################################################
### Parsers.                                             ###
############################################################

LOG_PARSER = 5
logging.addLevelName(LOG_PARSER, "PARSER")

########################################
# BaseParser.                          #
########################################
_pcre_masks["hidden_input"] = ("<input type=[\"']hidden[\"'] name=\"([^\"]+)\"[^>]+value=\"([^\"]*)\"", re.I)
_pcre_masks["guid"] = ("^[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+$", re.I)


class BaseParser:
    """
    Define common parts for all parsers.

    Attributes:
        http        --- Object with 'request' method for retrieving/sending data.

    """

    http = HTTPInterface

    def __init__(self):
        if hasattr(self, "_log"):
            self._log.log_parser = lambda x: self._log.log(LOG_PARSER, x)


########################################
# CacheDetails                         #
########################################
_pcre_masks["waypoint"] = ("GC[A-Z0-9]+", 0)
# The owner of <strong>The first Czech premium member cache</strong> has chosen to make this cache listing visible to Premium Members only.
_pcre_masks["PMonly"] = ("<img [^>]*alt=['\"]Premium Members only['\"][^>]*/>\s*The owner of <strong>\s*([^<]+)\s*</strong> has chosen to make this cache listing visible to Premium Members only\.", re.I)
# <span id="ctl00_ContentBody_uxCacheType">A cache by Pc-romeo</span>
_pcre_masks["PMowner"] = ("<span[^>]*>\s*A cache by ([^<]+)\s*</span>", re.I)
# <img src="/images/icons/container/regular.gif" alt="Size: Regular" />&nbsp<small>(Regular)</small>
_pcre_masks["PMsize"] = ("\s*<img [^>]*alt=['\"]Size: ([^'\"]+)['\"][^>]*/>", re.I)
# <strong><span id="ctl00_ContentBody_lblDifficulty">Difficulty:</span></strong>
# <img src="http://www.geocaching.com/images/stars/stars1.gif" alt="1 out of 5" />
_pcre_masks["PMdifficulty"] = ("<strong><span[^>]*>Difficulty:</span></strong>\s*<img [^>]*alt=['\"]([0-9.]+) out of 5['\"][^>]*/>", re.I)
# <strong><span id="ctl00_ContentBody_lblTerrain">Terrain:</span></strong>
# <img src="http://www.geocaching.com/images/stars/stars1_5.gif" alt="1.5 out of 5" />
_pcre_masks["PMterrain"] = ("<strong><span[^>]*>Terrain:</span></strong>\s*<img [^>]*alt=['\"]([0-9.]+) out of 5['\"][^>]*/>", re.I)
# <img id="ctl00_ContentBody_uxWptTypeImage" src="http://www.geocaching.com/images/wpttypes/2.gif" style="border-width:0px;vertical-align:middle" />
_pcre_masks["PMcache_type"] = ("<img id=['\"]ctl00_ContentBody_uxWptTypeImage['\"] src=['\"][^'\"]*/images/wpttypes/(earthcache|mega|[0-9]+).gif['\"][^>]*>", re.I)
# <p class="Warning">This is a Premium Member Only cache.</p>
_pcre_masks["cache_pm"] = ("<p class=['\"]Warning['\"]>This is a Premium Member Only cache\.</p>", re.I)
# <span class="favorite-value">8</span>
_pcre_masks["cache_favorites"] = ("<span class=['\"]favorite-value['\"][^>]*>([0-9]+)</span>", re.I)
# <meta name="description" content="Pendulum - Prague Travel Bug Hotel (GCHCE0) was created by Saman on 12/23/2003. It&#39;s a Regular size geocache, with difficulty of 2, terrain of 2.5. It&#39;s located in Hlavni mesto Praha, Czech Republic. Literary - kinetic cache with the superb view of the Praguepanorama. A suitable place for the incoming and outgoing travelbugs." />
_pcre_masks["cache_details"] = ("<meta\s+name=\"description\" content=\"([^\"]+) \(GC[A-Z0-9]+\) was created by ([^\"]+) on ([0-9]+)/([0-9]+)/([0-9]+)\. It('|(&#39;))s a ([a-zA-Z ]+) size geocache, with difficulty of ([0-9.]+), terrain of ([0-9.]+). It('|(&#39;))s located in (([^,.]+), )?([^.]+)\.[^\"]*\"[^>]*>", re.I|re.S)
# <a href="/about/cache_types.aspx" target="_blank" title="About Cache Types"><img src="/images/WptTypes/8.gif" alt="Unknown Cache" width="32" height="32" />
_pcre_masks["cache_type"] = ("<img src=['\"](http://www\.geocaching\.com)?/images/WptTypes/[^'\"]+['\"] alt=\"([^\"]+)\"[^>]*></a>", re.I)
# by <a href="http://www.geocaching.com/profile/?guid=ed7a2040-3bbb-485b-9b03-21ae8507d2d7&wid=92322d1b-d354-4190-980e-8964d7740161&ds=2">
_pcre_masks["cache_owner_id"] = ("by <a href=['\"]http://www\.geocaching\.com/profile/\?guid=([a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)&wid=([a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)&ds=2['\"][^>]*>", re.I)
# <p class="OldWarning"><strong>Cache Issues:</strong></p><ul class="OldWarning"><li>This cache is temporarily unavailable. Read the logs below to read the status for this cache.</li></ul></span>
_pcre_masks["disabled"] = ("<p class=['\"]OldWarning['\"][^>]*><strong>Cache Issues:</strong></p><ul[^>]*><li>This cache (has been archived|is temporarily unavailable)[^<]*</li>", re.I)
# <span id="ctl00_ContentBody_LatLon" style="font-weight:bold;">N 50° 02.173 E 015° 46.386</span>
_pcre_masks["cache_coords"] = ("<span id=['\"]ctl00_ContentBody_LatLon['\"][^>]*>([NS]) ([0-9]+)° ([0-9.]+) ([WE]) ([0-9]+)° ([0-9.]+)</span>", re.I)
_pcre_masks["cache_shortDesc"] = ("<div class=['\"]UserSuppliedContent['\"]>\s*<span id=['\"]ctl00_ContentBody_ShortDescription['\"]>(.*?)</span>\s+</div>", re.I|re.S)
_pcre_masks["cache_longDesc"] = ("<div class=['\"]UserSuppliedContent['\"]>\s*<span id=['\"]ctl00_ContentBody_LongDescription['\"]>(.*?)</span>\s*</div>\s*<p>\s+</p>\s+</td>", re.I|re.S)
"""
<div id="div_hint" class="HalfLeft">
                Hint text
</div>
"""
_pcre_masks["cache_hint"] = ("<div id=['\"]div_hint['\"][^>]*>\s*(.*?)\s*</div>", re.I)
"""
<div class="CacheDetailNavigationWidget Spacing">
    <img src="/images/attributes/wheelchair-no.gif" alt="not wheelchair accessible" title="not wheelchair accessible" width="30" height="30" /> <img src="/images/attributes/firstaid-yes.gif" alt="needs maintenance" title="needs maintenance" width="30" height="30" /> <img src="/images/attributes/stealth-yes.gif" alt="stealth required" title="stealth required" width="30" height="30" /> <img src="/images/attributes/available-yes.gif" alt="available 24-7" title="available 24-7" width="30" height="30" /> <img src="/images/attributes/scenic-yes.gif" alt="scenic view" title="scenic view" width="30" height="30" /> <img src="/images/attributes/onehour-yes.gif" alt="takes less than 1  hour" title="takes less than 1  hour" width="30" height="30" /> <img src="/images/attributes/kids-yes.gif" alt="kid friendly" title="kid friendly" width="30" height="30" /> <img src="/images/attributes/dogs-yes.gif" alt="dogs allowed" title="dogs allowed" width="30" height="30" /> <img src="/images/attributes/attribute-blank.gif" alt="blank" title="blank" width="30" height="30" /> <img src="/images/attributes/attribute-blank.gif" alt="blank" title="blank" width="30" height="30" /> <img src="/images/attributes/attribute-blank.gif" alt="blank" title="blank" width="30" height="30" /> <img src="/images/attributes/attribute-blank.gif" alt="blank" title="blank" width="30" height="30" /> <p class="NoSpacing"><small><a href="/about/icons.aspx" title="What are Attributes?">What are Attributes?</a></small></p>
</div>
"""
_pcre_masks["cache_attributes"] = ("<div class=\"CacheDetailNavigationWidget Spacing\">\s*(.*?)\s*<p[^>]*><small><a href=['\"]/about/icons\.aspx['\"] title=['\"]What are Attributes\?['\"]>What are Attributes\?</a></small></p>\s*</div>", re.I|re.S)
_pcre_masks["cache_attributes_item"] = ("title=\"([^\"]+)\"", re.I)
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
_pcre_masks["cache_inventory"] = ("<span\s+id=\"ctl00_ContentBody_uxTravelBugList_uxInventoryLabel\">Inventory</span>\s*</h3>\s*<div[^>]*>\s*<ul[^>]*>(.*?)</ul>", re.I|re.S)
"""
<a href="http://www.geocaching.com/track/details.aspx?guid=b82c9582-3d66-425a-91e1-c99f1e3e88d9" class="lnk">
    <img src="http://www.geocaching.com/images/wpttypes/sm/2059.gif" width="16" /><span>Travel Ingot Mr. East</span></a>
"""
_pcre_masks["cache_inventory_item"] = ("<a href=['\"][^'\"]*/track/details\.aspx\?guid=([a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)['\"][^>]*>\s*<img[^>]*>\s*<span>([^<]+)</span></a>", re.I)
# <span id="ctl00_ContentBody_lblFindCounts"><p><img src="/images/icons/icon_smile.gif" alt="Found it" />113&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/icon_note.gif" alt="Write note" />19&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/icon_remove.gif" alt="Needs Archived" />1&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/icon_disabled.gif" alt="Temporarily Disable Listing" />2&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/icon_enabled.gif" alt="Enable Listing" />1&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/icon_greenlight.gif" alt="Publish Listing" />1&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/icon_maint.gif" alt="Owner Maintenance" />2&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="/images/icons/big_smile.gif" alt="Post Reviewer Note" />3&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</p></span>
_pcre_masks["cache_visits"] = ("<span id=['\"]ctl00_ContentBody_lblFindCounts['\"][^>]*><p[^>]*>(.*?)</p></span>", re.I)
# <img src="/images/icons/icon_smile.gif" alt="Found it" />113
_pcre_masks["cache_log_count"] = ("<img[^>]*alt=\"([^\"]+)\"[^>]*/>([0-9]+)", re.I)
_pcre_masks["cache_logs"] = ("<table class=\"LogsTable Table\">(.*?)</table>\s+<p>", re.I|re.S)
_pcre_masks["cache_log"] = ("<tr><td[^>]*><strong><img.*?title=['\"]([^\"']+)['\"][^>]*/>&nbsp;([a-z]+) ([0-9]+)(, ([0-9]+))? by <a href=['\"](http://www\.geocaching\.com)?/profile/\?guid=([a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)['\"][^>]*>([^<]+)</a></strong>(&nbsp;| )\([0-9]+ found\)<br\s*/><br\s*/>(.*?)<br\s*/><br\s*/><small><a href=['\"]log.aspx\?LUID=([a-z0-9-]+)['\"] title=['\"]View Log['\"]>View Log</a></small>", re.I|re.S)


class CacheDetails(BaseParser):
    """
    Parse cache details from webpage source.

    Attributes:
        logs        --- Whether to return complete list of logs by default.

    Methods:
        get         --- Get cache details as dictionary by guid or waypoint.

    """

    _url = "http://www.geocaching.com/seek/cache_details.aspx?decrypt=y"

    logs = False

    def __init__(self, logs=False):
        """
        Keyworded arguments:
            logs        --- Whether to return complete list of logs by default.

        """
        self._log = logging.getLogger("gcparser.parser.CacheDetails")
        self.logs = logs
        BaseParser.__init__(self)

    def get(self, id_, logs=None):
        """
        Get cache details by guid or waypoint.

        Arguments:
            id_         --- Geocache waypoint or guid.

        Keyworded arguments:
            logs        --- Download complete list of logs.

        """
        if logs is None:
            logs = self.logs
        if _pcre("guid").match(id_) is not None:
            type_ = "guid"
        else:
            type_ = "wp"
        url = self._url + "&{0}={1}".format(type_, id_)
        if logs:
            url = url + "&log=y"
        data = self.http.request(url, auth=True)

        details = {}
        if type_ == "wp":
            details["waypoint"] = id_
        else:
            details["guid"] = id_
            match = _pcre("waypoint").search(data)
            if match is not None:
                details["waypoint"] = match.group(0)
                self._log.log_parser("waypoint = {0}".format(details["waypoint"]))
            else:
                self._log.error("Waypoint not found.")

        match = _pcre("PMonly").search(data)
        if match is not None:
            details["PMonly"] = True
            self._log.warn("PM only cache at '{0}'.".format(url))

            details["name"] = _unescape(match.group(1)).strip()
            self._log.log_parser("name = {0}".format(details["name"]))

            match = _pcre("PMowner").search(data)
            if match is not None:
                details["owner"] = _unescape(match.group(1)).strip()
                self._log.log_parser("owner = {0}".format(details["owner"]))
            else:
                self._log.error("Could not parse cache owner.")

            match = _pcre("PMsize").search(data)
            if match is not None:
                details["size"] = match.group(1).strip()
                self._log.log_parser("size = {0}".format(details["size"]))
            else:
                self._log.error("Could not parse cache size.")

            match = _pcre("PMdifficulty").search(data)
            if match is not None:
                details["difficulty"] = float(match.group(1))
                self._log.log_parser("difficulty = {0:.1f}".format(details["difficulty"]))
            else:
                self._log.error("Could not parse cache difficulty.")

            match = _pcre("PMterrain").search(data)
            if match is not None:
                details["terrain"] = float(match.group(1))
                self._log.log_parser("terrain = {0:.1f}".format(details["terrain"]))
            else:
                self._log.error("Could not parse cache terrain.")

            match = _pcre("PMcache_type").search(data)
            if match is not None and match.group(1) in _cache_types:
                details["type"] = _cache_types[match.group(1)]
                self._log.log_parser("type = {0}".format(details["type"]))
            else:
                self._log.error("Type not found.")
        else:
            details["PMonly"] = _pcre("cache_pm").search(data) is not None

            match = _pcre("cache_details").search(data)
            if match is not None:
                details["name"] = _unescape(_unescape(match.group(1))).strip()
                details["owner"] = _unescape(_unescape(match.group(2))).strip()
                details["hidden"] = "{0:04d}-{1:02d}-{2:02d}".format(int(match.group(5)), int(match.group(3)), int(match.group(4)))
                details["size"] = match.group(8).strip()
                details["difficulty"] = float(match.group(9))
                details["terrain"] = float(match.group(10))
                if match.group(14) is not None:
                    details["province"] = _unescape(match.group(14)).strip()
                else:
                    details["province"] = ""
                details["country"] = _unescape(match.group(15)).strip()
                self._log.log_parser("name = {0}".format(details["name"]))
                self._log.log_parser("owner = {0}".format(details["owner"]))
                self._log.log_parser("hidden = {0}".format(details["hidden"]))
                self._log.log_parser("size = {0}".format(details["size"]))
                self._log.log_parser("difficulty = {0:.1f}".format(details["difficulty"]))
                self._log.log_parser("terrain = {0:.1f}".format(details["terrain"]))
                self._log.log_parser("country = {0}".format(details["country"]))
                self._log.log_parser("province = {0}".format(details["province"]))
            else:
                self._log.error("Could not parse cache details.")

            match = _pcre("cache_type").search(data)
            if match is not None:
                details["type"] = _unescape(match.group(2)).strip()
                # GS weird changes bug
                if details["type"] == "Unknown Cache":
                    details["type"] = "Mystery/Puzzle Cache"
                self._log.log_parser("type = {0}".format(details["type"]))
            else:
                self._log.error("Type not found.")

            match = _pcre("cache_owner_id").search(data)
            if match is not None:
                details["owner_id"] = match.group(1)
                details["guid"] = match.group(2)
                self._log.log_parser("guid = {0}".format(details["guid"]))
                self._log.log_parser("owner_id = {0}".format(details["owner_id"]))
            else:
                self._log.error("Owner id not found.")
                if "guid" not in details:
                    self._log.error("Guid not found.")

            details["disabled"] = 0
            details["archived"] = 0
            match = _pcre("disabled").search(data)
            if match is not None:
                if match.group(1) == "has been archived":
                    details["archived"] = 1
                details["disabled"] = 1
                self._log.log_parser("archived = {0}".format(details["archived"]))
                self._log.log_parser("disabled = {0}".format(details["disabled"]))

            match = _pcre("cache_favorites").search(data)
            if match is not None:
                details["favorites"] = int(match.group(1))
                self._log.log_parser("favorites = {0}".format(details["favorites"]))
            else:
                self._log.error("Favorites count not found.")

            match = _pcre("cache_coords").search(data)
            if match is not None:
                details["lat"] = float(match.group(2)) + float(match.group(3))/60
                if match.group(1) == "S":
                    details["lat"] = -details["lat"]
                details["lon"] = float(match.group(5)) + float(match.group(6))/60
                if match.group(4) == "W":
                    details["lon"] = -details["lon"]
                self._log.log_parser("lat = {0:.5f}".format(details["lat"]))
                self._log.log_parser("lon = {0:.5f}".format(details["lon"]))
            else:
                self._log.error("Lat, lon not found.")

            match = _pcre("cache_shortDesc").search(data)
            if match is not None:
                details["shortDescHTML"] = match.group(1)
                details["shortDesc"] = _clean_HTML(match.group(1))
                self._log.log_parser("shortDesc = {0}...".format(details["shortDesc"].replace("\n"," ")[0:50]))
            else:
                details["shortDescHTML"] = ""
                details["shortDesc"] = ""

            match = _pcre("cache_longDesc").search(data)
            if match is not None:
                details["longDescHTML"] = match.group(1)
                details["longDesc"] = _clean_HTML(match.group(1))
                self._log.log_parser("longDesc = {0}...".format(details["longDesc"].replace("\n"," ")[0:50]))
            else:
                details["longDescHTML"] = ""
                details["longDesc"] = ""

            match = _pcre("cache_hint").search(data)
            if match is not None:
                details["hint"] = _unescape(match.group(1).replace("<br>", "\n")).strip()
                self._log.log_parser("hint = {0}...".format(details["hint"].replace("\n"," ")[0:50]))
            else:
                details["hint"] = ""

            match = _pcre("cache_attributes").search(data)
            if match is not None:
                details["attributes"] = []
                for item in _pcre("cache_attributes_item").finditer(match.group(1)):
                    attr = _unescape(item.group(1)).strip()
                    if attr != "blank":
                        details["attributes"].append(attr)
                details["attributes"] = ", ".join(details["attributes"])
                self._log.log_parser("attributes = {0}".format(details["attributes"]))
            else:
                details["attributes"] = ""

            details["inventory"] = {}
            match = _pcre("cache_inventory").search(data)
            if match is not None:
                for part in match.group(1).split("</li>"):
                    match = _pcre("cache_inventory_item").search(part)
                    if match is not None:
                        details["inventory"][match.group(1)] = _unescape(match.group(2)).strip()
                self._log.log_parser("inventory = {0}".format(details["inventory"]))

            details["visits"] = {}
            match = _pcre("cache_visits").search(data)
            if match is not None:
                for part in match.group(1).split("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"):
                    match = _pcre("cache_log_count").search(part)
                    if match is not None:
                        details["visits"][_unescape(match.group(1)).strip()] = int(match.group(2))
                self._log.log_parser("visits = {0}".format(details["visits"]))

            details["logs"] = []
            match = _pcre("cache_logs").search(data)
            if match is not None:
                for part in match.group(1).split("</tr>"):
                    match = _pcre("cache_log").match(part)
                    if match is not None:
                        if match.group(5) is not None:
                            year = match.group(5)
                        else:
                            year = datetime.now().year
                        log_date = "{0:04d}-{1:02d}-{2:02d}".format(int(year), int(_months_full[match.group(2)]), int(match.group(3)))
                        details["logs"].append(CacheLog(match.group(11), match.group(1), log_date, match.group(8), match.group(7), match.group(10)))
                self._log.log_parser("Found {0} logs.".format(len(details["logs"])))

        return details


########################################
# MyGeocachingLogs                     #
########################################
#<tr class="">
#<td>
#<img src="/images/icons/icon_smile.gif" width="16" height="16" alt="Found it" />
#</td>
#<td>
#</td>
#<td>
#12/29/2010
#</td>
#<td>
#<a href="http://www.geocaching.com/seek/cache_details.aspx?guid=e78fd364-18f4-48dd-98c1-a8af910dfe76" class="ImageLink"><img src="http://www.geocaching.com/images/wpttypes/sm/2.gif" title="Traditional Cache" /></a> <a href="http://www.geocaching.com/seek/cache_details.aspx?guid=e78fd364-18f4-48dd-98c1-a8af910dfe76">Hradiste Zamka</a>&nbsp;
#</td>
#<td>
#Hlavni mesto Praha, Czech Republic
#&nbsp;
#</td>
#<td>
#<a href="http://www.geocaching.com/seek/log.aspx?LUID=af2e28fa-e12e-4d2b-b6b1-64a2441996e3" target="_blank" title="Visit Log">Visit Log</a>
#</td>
#</tr>
_pcre_masks["logs_item"] = ("<tr[^>]*>\s*<td[^>]*>\s*<img [^>]*alt=\"([^\"]+)\"[^>]*>\s*</td>\s*<td[^>]*>.*?</td>\s*<td[^>]*>\s*([0-9]+)/([0-9]+)/([0-9]+)\s*</td>\s*<td[^>]*>\s*(<a[^>]*>)?\s*<img src=['\"](http://www\.geocaching\.com)?/images/wpttypes/[^'\"]+['\"][^>]*title=\"([^\"]+)\"[^>]*>\s*(</a>)?\s*<a href=['\"](http://www\.geocaching\.com)?/seek/cache_details.aspx\?guid=([a-z0-9-]+)['\"][^>]*>\s*(<span class=['\"]Strike(\s*OldWarning)?['\"]>)?\s*([^<]+)\s*(</span>)?\s*</a>[^<]*</td>\s*<td[^<]*>\s*(([^,<]+), )?([^<]+?)(\s*&nbsp;)?\s*</td>\s*<td[^<]*>\s*<a href=['\"][^'\"]*/seek/log\.aspx\?LUID=([a-z0-9-]+)['\"][^>]*>Visit Log</a>\s*</td>\s*</tr>", re.I|re.S)
# <a href="http://www.geocaching.com/seek/cache_details.aspx?guid=331f0c62-ef78-4ab3-b8d7-be569246771d" class="ImageLink"><img src="http://www.geocaching.com/images/wpttypes/sm/2.gif" title="Traditional Cache" /></a> <a href="http://www.geocaching.com/seek/cache_details.aspx?guid=331f0c62-ef78-4ab3-b8d7-be569246771d">Stepankovi hrosi</a>&nbsp;
# <a href="http://www.geocaching.com/seek/cache_details.aspx?guid=d3e80a41-4218-4136-bb63-ac0de3ef0b5a" class="ImageLink"><img src="http://www.geocaching.com/images/wpttypes/sm/8.gif" title="Unknown Cache" /></a> <a href="http://www.geocaching.com/seek/cache_details.aspx?guid=d3e80a41-4218-4136-bb63-ac0de3ef0b5a"><span class="Strike">Barva Kouzel</span></a>&nbsp;
# <a href="http://www.geocaching.com/seek/cache_details.aspx?guid=29444383-4607-4e2d-bc65-bcf2e9919e5d" class="ImageLink"><img src="http://www.geocaching.com/images/wpttypes/sm/2.gif" title="Traditional Cache" /></a> <a href="http://www.geocaching.com/seek/cache_details.aspx?guid=29444383-4607-4e2d-bc65-bcf2e9919e5d"><span class="Strike OldWarning">Krizovatka na kopci / Crossroad on a hill</span></a>&nbsp;
# <a href="http://www.geocaching.com/seek/log.aspx?LUID=af2e28fa-e12e-4d2b-b6b1-64a2441996e3" target="_blank" title="Visit Log">Visit Log</a>
_pcre_masks["logs_visit"] = ("<a href=['\"][^'\"]*/seek/log.aspx\?LUID=[a-z0-9-]+['\"][^>]*>Visit Log</a>", re.I)


class MyGeocachingLogs(BaseParser):
    """
    Parse and filter the list of my logs from webpage source.

    Methods:
        get         --- Parse and return list of user's geocaching logs.
        get_finds   --- Parse and return logs of type: Found it,
                        Webcam Photo Taken, Attended

    """

    _url = "http://www.geocaching.com/my/logs.aspx?s=1"

    def __init__(self):
        self._log = logging.getLogger("gcparser.parser.MyGeocachingLogs")
        BaseParser.__init__(self)

    def get(self, log_types=None):
        """
        Parse and return list of user's geocaching logs.

        Keyworded arguments:
            log_types       --- If not None return only logs of listed type.

        """
        data = self.http.request(self._url, auth=True)
        expected_count = len(_pcre("logs_visit").findall(data))
        logs = []
        for log in _pcre("logs_item").findall(data):
            expected_count -= 1

            log_type = _unescape(log[0]).strip()
            self._log.log_parser("type = {0}".format(log_type))
            if log_types is not None and log_type not in log_types:
                self._log.debug("Wrong log type, continuing...")
                continue
            log_date = "{0:04d}-{1:02d}-{2:02d}".format(int(log[3]), int(log[1]), int(log[2]))
            log_id = log[18]
            self._log.log_parser("date = {0}".format(log_date))
            self._log.log_parser("luid = {0}".format(log_id))

            cache = {}
            cache["type"] = _unescape(log[6]).strip()
            # GS weird changes bug
            if cache["type"] == "Unknown Cache":
                cache["type"] = "Mystery/Puzzle Cache"
            cache["disabled"] = 0
            cache["archived"] = 0
            if log[10]:
                cache["disabled"] = 1
                if log[11]:
                    cache["archived"] = 1
            if log[15]:
                cache["province"] = _unescape(log[15]).strip()
            else:
                cache["province"] = ""
            cache["country"] = _unescape(log[16]).strip()
            cache["guid"] = log[9]
            cache["name"] = _unescape(_unescape(log[12])).strip()
            self._log.log_parser("cache_name = {0}".format(cache["name"]))
            self._log.log_parser("cache_type = {0}".format(cache["type"]))
            self._log.log_parser("cache_guid = {0}".format(cache["guid"]))
            self._log.log_parser("archived = {0}".format(cache["archived"]))
            self._log.log_parser("disabled = {0}".format(cache["disabled"]))
            self._log.log_parser("country = {0}".format(cache["country"]))
            self._log.log_parser("province = {0}".format(cache["province"]))

            logs.append(LogItem(log_id, log_type, log_date, cache))
        if expected_count > 0:
            self._log.error("Seems like I missed {0} geocaching logs for some reason.".format(expected_count))
        logs.reverse()
        return logs

    def get_finds(self):
        """
        Parse and return logs of type: Found it, Webcam Photo Taken, Attended

        """
        return self.get(("Found it", "Webcam Photo Taken", "Attended"))




########################################
# SeekCache                            #
########################################
# <td class="PageBuilderWidget"><span>Total Records: <b>5371</b> - Page: <b>1</b> of <b>269</b>
_pcre_masks["search_totals"] = ("<td class=\"PageBuilderWidget\"><span>Total Records: <b>([0-9]+)</b>", re.I)
_pcre_masks["seek_results"] = ("<th[^>]*>\s*<img [^>]*alt=['\"]Send to GPS['\"][^>]*>\s*</th>(.*?)</table>", re.I|re.S)
_pcre_masks["seek_row"] = ("<tr bg[^>]*>(.*?)<td[^>]*>\s*</td>\s*</tr>", re.I|re.S)
# <span id="ctl00_ContentBody_dlResults_ctl01_uxFavoritesValue" title="9 - Click to view the Favorites/Premium Logs ratio." class="favorite-rank">9</span>
_pcre_masks["seek_favorites"] = ("<span[^>]*class=['\"]favorite-rank['\"][^>]*>([0-9]+)</span>", re.I)
# <a href="/seek/cache_details.aspx?guid=dffb4ac7-65ea-409b-9e2c-134d41824db7" class="lnk"><img src="http://www.geocaching.com/images/wpttypes/sm/2.gif" alt="Traditional Cache" title="Traditional Cache" /></a> <a href="/seek/cache_details.aspx?guid=dffb4ac7-65ea-409b-9e2c-134d41824db7" class="lnk OldWarning Strike Strike"><span>Secska vyhlidka </span></a>
# by Milancer
# (GCNXY6)<br />
# Pardubicky kraj, Czech Republic
_pcre_masks["seek_cache"] = ("(<a[^>]*>)?\s*<img src=['\"](http://www\.geocaching\.com)?/images/wpttypes/[^'\"]+['\"][^>]*title=\"([^\"]+)\"[^>]*>\s*(</a>)?\s*<a href=['\"](http://www\.geocaching\.com)?/seek/cache_details.aspx\?guid=([a-z0-9-]+)['\"]([^>]*class=['\"][^'\"]*?(\s+OldWarning)?(\s+Strike)?[^'\"]*?['\"])?[^>]*>\s*(<span[^>]*>)?\s*([^<]+)\s*(</span>)?\s*</a>\s*by (.*?)\s*\((GC[A-Z0-9]+)\)<br[^>]*>\s*(([^,<]+), )?([^<]+?)\s*\n", re.I)
# <a id="ctl00_ContentBody_dlResults_ctl02_uxTravelBugList" class="tblist"
_pcre_masks["seek_items"] = ("<a [^>]*class=['\"]tblist['\"][^>]*>", re.I)
# <img src="/images/small_profile.gif" alt="Premium Member Only Cache" title="Premium Member Only Cache" with="15" height="13" />
_pcre_masks["seek_PMonly"] = ("<img [^>]*alt=['\"]Premium Member Only Cache['\"][^>]*>", re.I)
# 30 Oct 09
_pcre_masks["seek_date"] = ("\s*<td[^>]*>\s*([0-9]+) ([A-Z]+) ([0-9]+)", re.I)
# 2 days ago
_pcre_masks["seek_dateDays"] = ("\s*<td[^>]*>\s*([0-9]+) days ago", re.I)
# Yesterday
# Today
_pcre_masks["seek_dateWords"] = ("\s*<td[^>]*>\s*((Yester|To)day)", re.I)


class SeekCache(BaseParser):
    """
    Parse caches in seek query from webpage source.

    Methods:
        coord       --- Parse and return sequence of found caches by coordinates.
        user        --- Parse and return sequence of found caches found by user.
        owner       --- Parse and return sequence of found caches placed by user.
        get         --- Parse and return sequence of found caches on url.

    """

    _url = "http://www.geocaching.com/seek/nearest.aspx?"

    def __init__(self):
        self._log = logging.getLogger("gcparser.parser.SeekCache")
        BaseParser.__init__(self)

    def coord(self, lat, lon, dist):
        """
        Parse and return sequence of found caches by coordinates.

        Arguments:
            lat         --- Latitude of center.
            lon         --- Longitude of center.
            dist        --- Maximum distance from center.

        """
        if not isinstance(lat, float) or not isinstance(lon, float):
            self._log.critical("LatLon must be float.")
        if not isinstance(dist, int):
            self._log.critical("Dist must be integer.")
        url = self._url + "origin_lat={0:.5f}&origin_long={1:.5f}&dist={2}&submit3=Search".format(lat, lon, dist)
        return self.get(url)

    def user(self, user):
        """
        Parse and return sequence of found caches found by user.

        Arguments:
            user        --- Username.

        """
        url = self._url + urllib.parse.urlencode({"ul":user, "submit4":"Go"})
        return self.get(url)

    def owner(self, user):
        """
        Parse and return sequence of found caches placed by user.

        Arguments:
            user        --- Username.

        """
        url = self._url + urllib.parse.urlencode({"u":user, "submit4":"Go"})
        return self.get(url)

    def get(self, url):
        """
        Parse and return sequence of found caches on url.

        Arguments:
            url         --- URL where to start search.

        """
        data = self.http.request(url)
        post_data = self._parse_post_data(data)
        caches = self._parse_caches(data)
        count = self._parse_count(data)
        return SeekResult(caches, count, url, post_data, self)

    def _parse_post_data(self, data):
        post_data = {}
        for hidden_input in _pcre("hidden_input").findall(data):
            post_data[hidden_input[0]] = hidden_input[1]
        post_data["__EVENTTARGET"] = "ctl00$ContentBody$pgrTop$ctl08"
        return post_data

    def _parse_count(self, data):
        """ Parse total count of found caches. """
        match = _pcre("search_totals").search(data)
        if match is not None:
            return int(match.group(1))
        else:
            self._log.warn("Could not find total count of found caches... assuming zero.")
            return 0

    def _parse_caches(self, data):
        caches = []
        match = _pcre("seek_results").search(data)
        if match is not None:
            for data in _pcre("seek_row").findall(match.group(1)):
                cache = {}
                data = data.split("</td>")
                #print(data)
                #print("------------------------------")

                match = _pcre("seek_cache").search(data[4])
                if match is not None:
                    cache["type"] = _unescape(match.group(3)).strip()
                    # GS weird changes bug
                    if cache["type"] == "Unknown Cache":
                        cache["type"] = "Mystery/Puzzle Cache"
                    cache["guid"] = match.group(6)
                    if match.group(8) is not None:
                        cache["archived"] = 1
                    else:
                        cache["archived"] = 0
                    if match.group(9) is not None:
                        cache["disabled"] = 1
                    else:
                        cache["disabled"] = 0
                    cache["name"] = _unescape(match.group(11)).strip()
                    cache["owner"] = _unescape(match.group(13)).strip()
                    cache["waypoint"] = match.group(14)
                    if match.group(16) is not None:
                        cache["province"] = _unescape(match.group(16)).strip()
                    else:
                        cache["province"] = ""
                    cache["country"] = _unescape(match.group(17)).strip()
                    self._log.log_parser("name = {0}".format(cache["name"]))
                    self._log.log_parser("waypoint = {0}".format(cache["waypoint"]))
                    self._log.log_parser("guid = {0}".format(cache["guid"]))
                    self._log.log_parser("type = {0}".format(cache["type"]))
                    self._log.log_parser("owner = {0}".format(cache["owner"]))
                    self._log.log_parser("disabled = {0}".format(cache["disabled"]))
                    self._log.log_parser("archived = {0}".format(cache["archived"]))
                    self._log.log_parser("province = {0}".format(cache["province"]))
                    self._log.log_parser("country = {0}".format(cache["country"]))
                else:
                    self._log.critical("Could not parse cache details.")

                match = _pcre("seek_date").match(data[7])
                if match is not None:
                    cache["hidden"] = "{0:04d}-{1:02d}-{2:02d}".format(int(match.group(3))+2000, _months_abbr[match.group(2)], int(match.group(1)))
                    self._log.log_parser("hidden = {0}".format(cache["hidden"]))
                else:
                    self._log.error("Hidden date not found.")

                match = _pcre("seek_date").match(data[8])
                if match is not None:
                    cache["found"] = "{0:04d}-{1:02d}-{2:02d}".format(int(match.group(3))+2000, _months_abbr[match.group(2)], int(match.group(1)))
                else:
                    match = _pcre("seek_dateDays").match(data[8])
                    if match is not None:
                        found_date = date.today() - timedelta(days=int(match.group(1)))
                        cache["found"] = found_date.isoformat()
                    else:
                        match = _pcre("seek_dateWords").match(data[8])
                        if match is not None:
                            found_date = date.today()
                            if match.group(1) == "Yesterday":
                                found_date = found_date - timedelta(days=1)
                            cache["found"] = found_date.isoformat()
                if "found" in cache:
                    self._log.log_parser("found = {0}".format(cache["found"]))
                else:
                    cache["found"] = None
                    self._log.log_parser("Never found.")

                cache["PMonly"] = _pcre("seek_PMonly").search(data[5]) is not None
                if cache["PMonly"]:
                    self._log.log_parser("PM only cache.")
                cache["items"] = _pcre("seek_items").search(data[5]) is not None
                if cache["items"]:
                    self._log.log_parser("Cache has items inside.")

                match = _pcre("seek_favorites").search(data[2])
                if match is not None:
                    cache["favorites"] = int(match.group(1))
                    self._log.log_parser("favorites = {0:d}".format(cache["favorites"]))
                else:
                    cache["favorites"] = 0
                    self._log.error("Favorites count not found.")

                caches.append(cache)
        return caches


class SeekResult(Sequence):
    """ Sequence wrapper for a result of seek query with lazy loading of next pages. """

    def __init__(self, caches, count, url, post_data, parser):
        self._log = logging.getLogger("gcparser.SeekResult")
        self._count = count
        self._caches = list(caches)
        if len(self._caches) not in (self._count, 20):
            self._log.critical("Seems like I missed some caches in the list, got only {0} caches on first page out of total {1}.".format(len(self._caches), self._count))
        self._url = url
        self._post_data = post_data
        self._parser = parser

    def _load_next_page(self):
        data = self._parser.http.request(self._url, data=self._post_data)
        self._post_data = self._parser._parse_post_data(data)
        caches = self._parser._parse_caches(data)
        if not (len(caches) == 20 or len(caches) + len(self._caches) == self._count):
            self._log.critical("Seems like I missed some caches in the list, got only {0} caches on this page, total {1} caches out of {2}.".format(len(caches), len(caches)+len(self._caches), self._count))
        self._caches.extend(caches)

    def __getitem__(self, index):
        if not isinstance(index, int):
            raise IndexError
        if index < 0:
            index += len(self)
        if 0 <= index < len(self):
            while index >= len(self._caches):
                self._load_next_page()
            return self._caches[index]
        else:
            raise IndexError

    def __len__(self):
        return self._count



########################################
# Profile                              #
########################################
class Profile(BaseParser):
    """
    Manage user's profile.

    Methods:
        update      --- Update user's geocaching.com profile.

    """

    def __init__(self):
        self._log = logging.getLogger("gcparser.parser.Profile")
        BaseParser.__init__(self)

    def update(self, profile_data):
        """
        Update user's geocaching.com profile.

        """
        data = self.http.request("http://www.geocaching.com/account/editprofiledetails.aspx", auth=True)
        post_data = {}
        for hidden_input in _pcre("hidden_input").findall(data):
            post_data[hidden_input[0]] = hidden_input[1]
        post_data["ctl00$ContentBody$uxProfileDetails"] = str(profile_data)
        post_data["ctl00$ContentBody$uxSave"] = "Save Changes"
        self.http.request("http://www.geocaching.com/account/editprofiledetails.aspx", auth=True, data=post_data)

