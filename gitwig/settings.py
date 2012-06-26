""" some sensible defaults and loading of a settings file """

import codecs
import yaml

from . import common

class Settings(object):
    """ some sensible defaults and loading of a settings file """

    template_dir =  "templates"
    blog_dir =      "blog"
    page_dir =      "pages"
    deploy_dir =    "deploy"
    media_dir =     "static/media"
    
    cache_path = "cache.pickle"

    posts_in_blog = 25
    posts_in_feed = 50

    url_prefix =    "http://www.example.com"
    media_prefix =  "http://www.example.com/static/media"
    blog_title =    "my gitwig blog"
    author =        "myself"
    
    # extension of source files
    source_exts = [".md", ".mkd", ".mdown", ".mkdown", ".markdown", ".html"]
    
    def __init__(self):
        """ initialization """
        pass

    @classmethod
    def from_file(cls, path):
        """ loads a config file and returns an instance """
        common.log.info("settings: reading from file '%s'" % path)
        instance = cls()
        file_handle = codecs.open(path, "r")
        instance.load(file_handle)
        file_handle.close()
        return instance
    
    def load(self, file_handle):
        """ loads the settings from a file like object """
        tmp_settings = yaml.load(file_handle)
        for key, value in tmp_settings.iteritems():
            setattr(self, key, value if value else "")
