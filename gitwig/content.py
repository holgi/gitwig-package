""" definitions of content types that can be rendered """

# global imports
import codecs
from datetime import datetime
import hashlib
import os
import StringIO
import re

# local imports
from . import settings
from . import common

# separates the headers from the body of the content
HEADER_BODY_SEPERATOR = "\n\n"
# format of the created and updated headers
HEADER_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
# the most important header keys
HEADER_KEYS =  ["title", "tags", "created", "updated", "uuid"]

# regular expression for extracting tags from a string
regex_split_tags = re.compile("[, ]+")

# functions to convert header fields from and to python objects
def parse_date(date_str):
    """ returns a datetime object from a string in the HEADER_DATE_FORMAT """
    return datetime.strptime(date_str, HEADER_DATE_FORMAT)

def format_date(date_obj):
    """ returns a string in the HEADER_DATE_FORMAT from a  datetime object"""
    return datetime.strftime(date_obj, HEADER_DATE_FORMAT)

def parse_tags(tag_str):
    """ returns a set of tags from a string with comma separated tags """
    tags = filter(None, regex_split_tags.split(tag_str.lower()))
    return set(tags)

def format_tags(tag_list):
    """ returns a string with comma separated tags from a set of tags"""
    return ", ".join(tag_list)

def format_header_source(key, value):
    """ pretty formatting of key an value used in headers of the content """
    pretty_key = key.capitalize() + ":"
    return u"%-7s %s\n" % (pretty_key, value)


class BaseContent(object):
    """ Base class for original content like blog posts and pages """

    # defines how some header dicts need to be converted from and to python
    special_header_dict = {
        "created": (parse_date, format_date),
        "updated": (parse_date, format_date),
        "tags":    (parse_tags, format_tags)
    }
    
    # template file used to render the object
    template = None
    
    # flag that this is not a related content like and index
    is_index = False

    def __init__(self, id=None, headers=None):
        """ initialization, accepts an id and a dict with headers """
        self.id = id
        self.headers = headers or {}
        self.body = None
    
    def __eq__(self, other):
        """ compares this object to another one """
        return type(self) == type(other) and self.id == other.id
    
    def __hash__(self):
        """ return a hash for this object, needed for addition to sets """
        md5 = hashlib.md5(str(self.id))
        return int(md5.hexdigest(), 16)

    @classmethod
    def from_file(cls, file_path):
        """ reads and parses the content of a file and returns an instance """
        instance = cls(file_path)
        instance.load(file_path)
        return instance
    
    @classmethod
    def from_handle(cls, file_handle):
        """ reads the from a file like object and returns an instance """
        instance = cls()
        instance.read(file_handle)
        return instance
    
    def load(self, file_path):
        """ reads and parses the content of a file """
        common.log.debug("base content: loading from '%s'" % file_path)
        file_handle = codecs.open(file_path, "r", encoding="utf-8")
        self.read(file_handle)
        file_handle.close()
    
    def read(self, file_handle):
        """ reads and parses the content from a file like object """
        common.log.debug("base content: reading '%s'" % self.id)
        self.parse_content(file_handle.read())
    
    def parse_content(self, content):
        """ parses a content string for headers and body """
        # separate raw headers and the body
        raw_headers, self.body = content.split(HEADER_BODY_SEPERATOR, 1)
        # parse the raw headers
        for line in StringIO.StringIO(raw_headers):
            try:
                # split the line by the first colon, strip white spaces
                # and store key and value in the headers dict
                key, value = line.split(":", 1)
                key, value = key.strip(), value.strip()
                self.headers[key.lower()] = value
            except ValueError:
                # there might be a line without a colon, it will be ignored
                pass
        self._convert_header_values()
    
    def _convert_header_values(self):
        """ converts some header values to a python object """
        for key, functions in self.special_header_dict.iteritems():
            to_python, fom_python = functions
            try:
                self.headers[key] = to_python(self.headers[key])
            except (KeyError, ValueError):
                self.headers[key] = None

    def get_source(self):
        """ returns the source of a content item for storing in a file """
        src_headers = ""
        # find the keys, that are not usual header keys
        additional_keys = [k for k in self.headers if k not in HEADER_KEYS]
        # first we use the typical header keys and later the additional keys
        for key in HEADER_KEYS + additional_keys:
            # make sure that every value is a string
            functions = self.special_header_dict.get(key, (None, unicode))
            to_python, from_python = functions
            value = self.headers.get(key, "")
            # add a line to the source header
            src_header += format_header_source(key, from_python(value))
        return src_header + u"\n" + self.body

    def get_url_parts(self):
        """ should return all parts of the url as a tuple
        
        this should not include any prefix like domain name, protocol, etc
        """
        raise NotImplementedError
    
    def get_body(self):
        """ returns the body of the content item
        
        uses lazy loading if only the headers are set 
        """
        if self.body is None:
            self.load(self.id)
        return self.body
            

class BlogPost(BaseContent):
    """ content class for a blog post """

    # template file used to render the blog post
    template = "post.html"
    
    def __init__(self, id=None, headers=None):
        """ initialization """
        super(BlogPost, self).__init__(id, headers)
    
    def get_url_parts(self):
        """ returns all parts of the url as a tuple 
        
        a blog post url consists of the year, month, day and a slug. 
        e.g. "2012/06/31/slug.html". For this example the url parts would 
        be ("2012", "06", "31", "slug.html")
        """
        slug, ext = os.path.splitext(os.path.basename(self.id))
        date_tuple = common.date_tuple(self)
        date_parts = ["%02d" % part for part in date_tuple]
        return tuple(date_parts + [slug + ".html"])
    

class StaticPage(BaseContent):
    """ content class for a static page """

    # template file used to render the blog post
    template = "page.html"
    
    def __init__(self, id=None, headers=None):
        """ initialization """
        super(StaticPage, self).__init__(id, headers)
    
    def get_url_parts(self):
        """ returns all parts of the relative url as a tuple """
        slug, ext = os.path.splitext(os.path.basename(self.id))
        dir_paths = os.path.dirname(self.id)
        directories = dir_paths.split(os.path.sep)[1:]
        return tuple(directories + [slug + ".html"])


class BaseIndex(object):
    """ Base class for related indices of blog posts """
    
    # template file used to render the blog post
    template = None
    
    # flag that this is a related content like and index
    is_index = True
    
    # attribute for this index in the cache
    cache_attribute = None

    def __init__(self, id=None, content=None):
        """ initialization """
        self.id = id
        self.content = content
    
    def get_url_parts(self):
        """ returns all parts of the relative url as a tuple """
        date_parts = ["%02d" % part for part in self.id]
        return tuple(date_parts + ["index.html"])
    
    def __iter__(self):
        """ implementation of the iter protocol """
        return self.content
        
    def __eq__(self, other):
        """ compares this object to another one """
        return type(self) == type(other) and self.id == other.id
    
    def __hash__(self):
        """ return a hash for this object, needed for addition to sets """
        md5 = hashlib.md5(str(self.id))
        return int(md5.hexdigest(), 16)
    
    def is_in_cache(self, cache):
        """ checks if this index is found in the cache """
        return self.id in getattr(cache, self.cache_attribute)
    
    def set_content_from_cache(self, cache):
        """ sets the content of this index from cache """
        blog_ids = getattr(cache, self.cache_attribute)[self.id]
        self.content = cache.posts_by_id_list(blog_ids)
    
    @classmethod
    def from_cache(cls, id=None, cache=None):
        """ sets the content of the index from cache and returns an instance """
        instance = cls(id)
        instance.set_content_from_cache(cache)
        return instance


class YearIndex(BaseIndex):
    """ content class for the yearly index of blog posts """

    # template file used to render the blog post
    template = "year.html"
    
    # attribute for this index in the cache
    cache_attribute = "years"
    
    def as_datetime(self):
        """ returns the first of january of the year as a datetime object """
        year = self.id[0]
        return datetime(year, 1, 1)
        

class MonthIndex(BaseIndex):
    """ content class for the monthly index of blog posts """

    # template file used to render the blog post
    template = "month.html"
    
    # attribute for this index in the cache
    cache_attribute = "months"
    
    def as_datetime(self):
        """ returns the first of the month as a datetime object """
        year, month = self.id
        return datetime(year, month, 1)


class DayIndex(BaseIndex):
    """ content class for the daily index of blog posts """

    # template file used to render the blog post
    template = "day.html"
    
    # attribute for this index in the cache
    cache_attribute = "days"

    def as_datetime(self):
        """ returns the day as a datetime object """
        year, month, day = self.id
        return datetime(year, month, day)

        
class TagPage(BaseIndex):
    """ content class for a single tag index of blog posts """

    # template file used to render the blog post
    template = "tag.html"
    
    # attribute for this index in the cache
    cache_attribute = "tags"

    def get_url_parts(self):
        """ returns all parts of the relative url as a tuple """
        return ("tags", self.id + ".html")


class TagIndex(BaseIndex):
    """ content class for a all tags of all blog posts """

    # template file used to render the blog post
    template = "tags.html"
    
    def __init__(self, id=None, content=None):
        """ initialization 
        
        why this strange id format:
        the ids are used to generate hashes, so for a fixed index we need to
        have an id that does not collide with any other ids:
        - the ids for blog postings and static pages are file paths, so by
          using the wildcards "?" and "*" pretty sure no path matches
        - the ids for date related indices are tuples of integers, so no 
          problem here
        - the ids for tags are strings since these are colon or space 
          separated, the addition of a space prevents a mistake
        """
        content = content or []
        super(TagIndex, self).__init__("*tag index?", content)
    
    def get_url_parts(self):
        """ returns all parts of the relative url as a tuple """
        return ("tags", "index.html")
    
    def __iter__(self):
        """ implementation of the iter protocol a generator """
        for id, count in self.content:
            yield (TagPage(id), count)

    def is_in_cache(self, cache):
        """ dummy method to be method complete against the base class 
        
        this will always return true, since this is a page that should always
        be rendered and cannot expire.
        """
        return True
    
    def set_content_from_cache(self, cache):
        """ sets the content of the all tag index from cache """
        self.content = cache.get_tag_count()
        

class BlogIndex(BaseIndex):
    """ content class for the blog index page """

    # template file used to render the blog post
    template = "blog.html"
    
    def __init__(self, id=None, content=None):
        """ initialization, see also TagIndex """
        content = content or []
        super(BlogIndex, self).__init__("*blog index?", content)

    def get_url_parts(self):
        """ returns all parts of the relative url as a tuple """
        return ("index.html",)

    def is_in_cache(self, cache):
        """ dummy method to be method complete against the base class 
        
        this will always return true, since this is a page that should always
        be rendered and cannot expire.
        """
        return True
        
    def set_content_from_cache(self, cache, number_of_posts):
        """ sets the content of the blog index from cache """
        self.content = cache.get_latest(number_of_posts)
    
    @classmethod
    def from_cache(cls, id=None, cache=None, number_of_posts=25):
        """ sets the content of the index from cache and returns an instance """
        instance = cls(id)
        instance.set_content_from_cache(cache, number_of_posts)
        return instance


class FeedIndex(BaseIndex):
    """ content class for the blog feed """

    # template file used to render the blog post
    template = "feed.xml"
    
    def __init__(self, id=None, content=None):
        """ initialization, see also TagIndex """
        content = content or []
        super(FeedIndex, self).__init__("*feed index?", content)

    def get_url_parts(self):
        """ returns all parts of the relative url as a tuple """
        return ("feed.xml",)

    def is_in_cache(self, cache):
        """ dummy method to be method complete against the base class 
        
        this will always return true, since this is a page that should always
        be rendered and cannot expire.
        """
        return True
            
    def set_content_from_cache(self, cache, number_of_posts):
        """ sets the content of the blog index from cache """
        self.content = cache.get_latest(number_of_posts)

    @classmethod
    def from_cache(cls, id=None, cache=None, number_of_posts=25):
        """ sets the content of the index from cache and returns an instance """
        instance = cls(id)
        instance.set_content_from_cache(cache, number_of_posts)
        return instance
