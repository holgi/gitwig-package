import codecs
from datetime import datetime
import hashlib
import os
import StringIO
import re

from . import settings
from . import common

HEADER_BODY_SEPERATOR = "\n\n"

HEADER_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
HEADER_KEYS =  ["title", "tags", "date", "uuid"]


# regular expression for extracting tags from a string
regex_split_tags = re.compile("[, ]+")

def parse_date(date_str):
    return datetime.strptime(date_str, HEADER_DATE_FORMAT)

def format_date(date_obj):
    return datetime.strftime(date_obj, HEADER_DATE_FORMAT)

def parse_tags(tag_str):
    tags = filter(None, regex_split_tags.split(tag_str))
    return set(t.lower() for t in tags)

def format_tags(tag_list):
    return ", ".join(tag_list)

def format_header_source(key, value):
    pretty_key = key.capitalize() + ":"
    return u"%-7s %s\n" % (pretty_key, value)


class BaseContent(object):

    special_header_dict = {
        "created": (parse_date, format_date),
        "updated": (parse_date, format_date),
        "tags":    (parse_tags, format_tags)
    }
    
    template = None
    is_index = False

    def __init__(self, id=None, headers=None):
        self.id = id
        self.headers = headers or {}
        self.body = None
    
    def __eq__(self, other):
        return type(self) == type(other) and self.id == other.id
    
    def __hash__(self):
        md5 = hashlib.md5(str(self.id))
        return int(md5.hexdigest(), 16)


    @classmethod
    def from_file(cls, file_path, only_headers=False):
        instance = cls(file_path)
        instance.load(file_path, only_headers)
        return instance
    
    @classmethod
    def from_handle(cls, file_handle, only_headers=False):
        instance = cls()
        instance.read(file_handle, only_headers)
        return instance
    
    @classmethod
    def from_content(cls, file_content, only_headers=False):
        instance = cls()
        instance.parse_content(file_content, only_headers)
        return instance
    
    def load(self, file_path, only_headers=False):
        common.log.debug("base content: loading from '%s'" % file_path)
        file_handle = codecs.open(file_path, "r")
        self.read(file_handle, only_headers)
        file_handle.close()
    
    def read(self, file_handle, only_headers=False):
        common.log.debug("base content: reading '%s'" % self.id)
        fh = file_handle
        file_content = fh.read(1024) if only_headers else fh.read()
        self.parse_content(file_content, only_headers)
    
    def parse_content(self, content, only_headers=False):
        raw_headers, tmp_body = content.split(HEADER_BODY_SEPERATOR, 1)
        if not only_headers:
            self.body = tmp_body
        self.parse_raw_headers(raw_headers)
        
    def parse_raw_headers(self, raw_headers):
        for line in StringIO.StringIO(raw_headers):
            try:
                key, value = line.split(":", 1)
                key, value = key.strip(), value.strip()
                self.headers[key.lower()] = value
            except ValueError:
                # there might be a line without a colon, it will be ignored
                pass
        self._prepare_special_header_values()
    
    def _prepare_special_header_values(self):
        for key, functions in self.special_header_dict.iteritems():
            to_python, fom_python = functions
            try:
                self.headers[key] = to_python(self.headers[key])
            except (KeyError, ValueError):
                self.headers[key] = None

    def get_source(self):
        src_headers = ""
        additional_keys = [k for k in self.headers if k not in HEADER_KEYS]
        for key in HEADER_KEYS + additional_keys:
            functions = self.special_header_dict.get(key, (None, unicode))
            to_python, from_python = functions
            value = self.headers.get(key, "")
            src_header += format_header_source(key, from_python(value))
        return src_header + u"\n" + self.body

    def get_url_parts(self):
        raise NotImplementedError
    
    def get_body(self):
        if self.body is None:
            self.load(self.id)
        return self.body
            

class BlogPost(BaseContent):

    template = "post.html"
    
    def __init__(self, id=None, headers=None):
        super(BlogPost, self).__init__(id, headers)
    
    def get_url_parts(self):
        slug, ext = os.path.splitext(os.path.basename(self.id))
        date_tuple = common.date_tuple(self)
        date_parts = ["%02d" % part for part in date_tuple]
        return tuple(date_parts + [slug + ".html"])
    

class StaticPage(BaseContent):

    template = "page.html"
    
    def __init__(self, id=None, headers=None):
        super(StaticPage, self).__init__(id, headers)
    
    def get_url_parts(self):
        slug, ext = os.path.splitext(os.path.basename(self.id))
        dir_paths = os.path.dirname(self.id)
        directories = dir_paths.split(os.path.sep)[1:]
        return tuple(directories + [slug + ".html"])


class BaseIndex(object):
    
    template = None
    is_index = True

    def __init__(self, id=None, content=None):
        self.id = id
        self.content = content
    
    def get_url_parts(self):
        date_parts = ["%02d" % part for part in self.id]
        return tuple(date_parts + ["index.html"])
    
    def __iter__(self):
        return self.content
        
    def __eq__(self, other):
        return type(self) == type(other) and self.id == other.id
    
    def __hash__(self):
        md5 = hashlib.md5(str(self.id))
        return int(md5.hexdigest(), 16)
    
    def is_in_cache(self, cache):
        raise NotImplementedError
    
    def set_content_from_cache(self, cache):
        raise NotImplementedError
    
    @classmethod
    def from_cache(cls, id=None, cache=None):
        instance = cls(id)
        instance.set_content_from_cache(cache)
        return instance


class YearIndex(BaseIndex):

    template = "year.html"
    
    def as_datetime(self):
        year = self.id[0]
        return datetime(year, 1, 1)
    
    def set_content_from_cache(self, cache):
        blog_ids = cache.years[self.id]
        self.content = cache.posts_by_id_list(blog_ids)

    def is_in_cache(self, cache):
        return self.id in cache.years
        

class MonthIndex(BaseIndex):

    template = "month.html"
    
    def as_datetime(self):
        year, month = self.id
        return datetime(year, month, 1)
    
    def set_content_from_cache(self, cache):
        blog_ids = cache.months[self.id]
        self.content = cache.posts_by_id_list(blog_ids)

    def is_in_cache(self, cache):
        return self.id in cache.months


class DayIndex(BaseIndex):

    template = "day.html"

    def as_datetime(self):
        year, month, day = self.id
        return datetime(year, month, day)
    
    def set_content_from_cache(self, cache):
        blog_ids = cache.days[self.id]
        self.content = cache.posts_by_id_list(blog_ids)

    def is_in_cache(self, cache):
        return self.id in cache.days

        
class TagPage(BaseIndex):

    template = "tag.html"

    def get_url_parts(self):
        return ("tags", self.id + ".html")
    
    def set_content_from_cache(self, cache):
        blog_ids = cache.tags[self.id]
        self.content = cache.posts_by_id_list(blog_ids)

    def is_in_cache(self, cache):
        return self.id in cache.tags


class TagIndex(BaseIndex):

    template = "tags.html"
    
    def __init__(self, id=None, content=None):
        # why this strange id format:
        # the ids are used to generate hashes, so for a fixed index we need to
        # have an id that does not collide with any other ids:
        # - the ids for blog postings and static pages are file paths, so by
        #   using the wildcards "?" and "*" pretty sure no path matches
        # - the ids for date related indices are tuples of integers, so no 
        #   problem here
        # - the ids for tags are strings since these are colon or space 
        #   separated, the addition of a space prevents a mistake
        super(TagIndex, self).__init__("*tag index?", content)
    
    def get_url_parts(self):
        return ("tags", "index.html")
    
    def __iter__(self):
        for id, count in self.content:
            yield (TagPage(id), count)
    
    def set_content_from_cache(self, cache):
        self.content = cache.get_tag_count()

    def is_in_cache(self, cache):
        return True
        

class BlogIndex(BaseIndex):

    template = "blog.html"
    
    def __init__(self, id=None, content=None):
        # why this strange id format: see TagIndex
        super(BlogIndex, self).__init__("*blog index?", content)

    def get_url_parts(self):
        return ("index.html",)
        
    def set_content_from_cache(self, cache, number_of_posts):
        self.content = cache.get_latest(number_of_posts)

    def is_in_cache(self, cache):
        return True
    
    @classmethod
    def from_cache(cls, id=None, cache=None, number_of_posts=25):
        instance = cls(id)
        instance.set_content_from_cache(cache, number_of_posts)
        return instance


class FeedIndex(BaseIndex):

    template = "feed.xml"
    
    def __init__(self, id=None, content=None):
        # why this strange id format: see TagIndex
        super(FeedIndex, self).__init__("*feed index?", content)

    def get_url_parts(self):
        return ("feed.xml",)
            
    def set_content_from_cache(self, cache, number_of_posts):
        self.content = cache.get_latest(number_of_posts)

    def is_in_cache(self, cache):
        return True

    @classmethod
    def from_cache(cls, id=None, cache=None, number_of_posts=25):
        instance = cls(id)
        instance.set_content_from_cache(cache, number_of_posts)
        return instance
