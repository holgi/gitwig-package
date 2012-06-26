import os
try:
    import cPickle as pickle
except ImportError:
    import pickle


from . import common
from . import content


class BlogCache(object):

    def __init__(self):
        self.cache = dict()
        self._reset_indices()
        
    def _reset_indices(self):
        self.days = dict()
        self.months = dict()
        self.years = dict()
        self.tags = dict()
        self.sorted_ids = list()
    
    def add(self, blog_post):
        common.log.debug("cache: adding blog post '%s'" % blog_post.id)
        self.cache[blog_post.id] = blog_post
    
    def pop(self, id, default=None):
        common.log.debug("cache: removing blog post '%s'" % id)
        return self.cache.pop(id, default)
    
    def build_indices(self):
        common.log.debug("cache: building indices ...")
        self._reset_indices()
        unsorted = list()
        for id, blog_post in self.cache.iteritems():
            date_tuple = common.date_tuple(blog_post)
            self.days.setdefault(date_tuple, set()).add(id)
            self.months.setdefault(date_tuple[:2], set()).add(id)
            self.years.setdefault(date_tuple[:1], set()).add(id)
            for tag in blog_post.headers["tags"]:
                self.tags.setdefault(tag, set()).add(id)
            unsorted.append( (blog_post.headers["created"], id) )
        self.sorted_ids = [id for created, id in sorted(unsorted, reverse=True)]
        common.log.debug("cache: ... done")
            
    def posts_by_id_list(self, post_ids):
        common.log.debug("cache: listing %d posts by id" % len(post_ids))
        sorted_post_ids = (pid for pid in self.sorted_ids if pid in post_ids)
        return (self.cache[post_id] for post_id in sorted_post_ids)
    
    def get_latest(self, number_of_posts):
        common.log.debug("cache: listing the latest %d posts" % number_of_posts)
        return self.posts_by_id_list(self.sorted_ids[:number_of_posts])
    
    def get_tag_count(self):
        return sorted( (id, len(posts)) for id, posts in self.tags.iteritems() )

    def write(self, cache_path):
        common.log.info("cache: writing cache to '%s' ..." % cache_path)
        items = ( (id, post.headers) for id, post in self.cache.iteritems() )
        file_handle = open(cache_path, "wb")
        pickle.dump(list(items), file_handle, pickle.HIGHEST_PROTOCOL)
        file_handle.close()
        common.log.info("cache: ... done")

    def load(self, cache_path):
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
        common.log.debug("cache: reading ...")
        items = pickle.load(file_handle)
        file_handle.close()
        for id, headers in items:
            self.cache[id] = content.BlogPost(id, headers)
        self.build_indices()
        common.log.debug("cache: ... done")
    
    @classmethod
    def from_file(cls, cache_path):
        instance = cls()
        instance.load(cache_path)
        return instance

    @classmethod
    def from_handle(cls, file_handle):
        instance = cls()
        instance.read(file_handle)
        return instance
