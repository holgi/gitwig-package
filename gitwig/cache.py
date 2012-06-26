""" Caching of blog post headers and creation of indices for dates and tags """

# global imports
import os
try:
    import cPickle as pickle
except ImportError:
    # fallback
    import pickle

# local imports
from . import common
from . import content


class BlogCache(object):
    """ caches blog post headers and calculates indices for dates and tags """

    def __init__(self):
        """ initialization """
        self.cache = dict()
        self._reset_indices()
        
    def _reset_indices(self):
        """ resets all related indices for dates and tags """
        self.days = dict()
        self.months = dict()
        self.years = dict()
        self.tags = dict()
        # this list is for presorting the ids of blog-posts
        self.sorted_ids = list()
    
    def add(self, blog_post):
        """ adds a blog post to the cache """
        common.log.debug("cache: adding blog post '%s'" % blog_post.id)
        self.cache[blog_post.id] = blog_post
    
    def pop(self, id, default=None):
        """ removes a blog post from the cache
        
        if the blog post is not in the cache the default value (None) will be
        returned
        """
        common.log.debug("cache: removing blog post '%s'" % id)
        return self.cache.pop(id, default)
    
    def build_indices(self):
        """ builds the indices for dates and tags from the cache """
        common.log.debug("cache: building indices ...")
        self._reset_indices()
        # temporary list, used later for presorting blog posts
        unsorted = list()
        for id, blog_post in self.cache.iteritems():
            # the ids for day, month and year are tuples with the corresponding
            # values retrieved from the 'created' header of a blog post
            date_tuple = common.date_tuple(blog_post)
            self.days.setdefault(date_tuple, set()).add(id)
            self.months.setdefault(date_tuple[:2], set()).add(id)
            self.years.setdefault(date_tuple[:1], set()).add(id)
            for tag in blog_post.headers["tags"]:
                self.tags.setdefault(tag, set()).add(id)
            # we append a tuple consisting of the 'created' header of the blog 
            # post and its id to the temporary list for presorting the posts
            unsorted.append( (blog_post.headers["created"], id) )
        # tuple sorting is used to create the final list of presorted blog posts
        self.sorted_ids = [id for created, id in sorted(unsorted, reverse=True)]
        common.log.debug("cache: ... done")
            
    def posts_by_id_list(self, post_ids):
        """ returns a sorted list of blog posts by their ids """
        common.log.debug("cache: listing %d posts by id" % len(post_ids))
        sorted_post_ids = (pid for pid in self.sorted_ids if pid in post_ids)
        return (self.cache[post_id] for post_id in sorted_post_ids)
    
    def get_latest(self, number_of_posts):
        """ returns the latest blog posts in the cache"""
        common.log.debug("cache: listing the latest %d posts" % number_of_posts)
        return self.posts_by_id_list(self.sorted_ids[:number_of_posts])
    
    def get_tag_count(self):
        """ returns a sorted list of tags from blog posts and their count """
        return sorted( (id, len(posts)) for id, posts in self.tags.iteritems() )

    def write(self, cache_path):
        """ writes a version of the cache to a specified file """
        common.log.info("cache: writing cache to '%s' ..." % cache_path)
        items = [ (id, post.headers) for id, post in self.cache.iteritems() ]
        file_handle = open(cache_path, "wb")
        pickle.dump(items, file_handle, pickle.HIGHEST_PROTOCOL)
        file_handle.close()
        common.log.info("cache: ... done")

    def load(self, cache_path):
        """ loads the cache from a given file path
        
        will raise a gitwig.common.NeedsRebuildError if the file could not be
        opened or the data could not be unpickled
        """
        try:
            common.log.info("cache: loading cache from '%s' ..." % cache_path)
            file_handle = open(cache_path, "rb")
            self.read(file_handle)
            file_handle.close()
            common.log.info("cache: ... done")
        except (IOError, pickle.PickleError):
            raise common.NeedsRebuildError("could not load cache from '%s'" %\
                                           cache_path)
    
    def read(self, file_handle):
        """ reads the cache from a given file like object """
        common.log.debug("cache: reading ...")
        items = pickle.load(file_handle)
        file_handle.close()
        for id, headers in items:
            self.cache[id] = content.BlogPost(id, headers)
        self.build_indices()
        common.log.debug("cache: ... done")
    
    @classmethod
    def from_file(cls, cache_path):
        """ returns an instance and loads the cache from file in one go """
        instance = cls()
        instance.load(cache_path)
        return instance

    @classmethod
    def from_handle(cls, file_handle):
        """ returns an instance and loads the cache from a file like object """
        instance = cls()
        instance.read(file_handle)
        return instance
