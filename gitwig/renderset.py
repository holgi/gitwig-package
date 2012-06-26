""" classes to determine what should be rendered and updating the cache

there are two possibilities: 
 -  Rebuild: renders everything
 -  Update: uses git to calculate what should be rendered
"""

# global imports
import codecs
import os

# local imports
from . import common
from . import content


class Renderset(object):
    """ Base class for all renderset types """

    def __init__(self, config, cache):
        """ initialization """
        self.config = config
        self.cache = cache
    
    def items_to_delete(self):
        """ returns an iterable of all items that should be deleted """
        return set()
        
    def items_to_render(self):
        """ returns an iterable of all items that should be rendered """
        return set()
        

class Rebuild(Renderset):
    """ class for rendering all blog posts and static pages """
    
    def __init__(self, config, cache):
        """ initialization """
        super(Rebuild, self).__init__(config, cache)
    
    def items_to_render(self):
        """ iterable of all items that should be rendered 
        
        this is implemented as a generator method.
        """
        config = self.config
        # find and emit all static pages
        for page_path in common.walk(config.page_dir, config.source_exts):
            yield content.StaticPage.from_file(page_path)
        # find and emit all blog posts, adds these to the cache
        for posting_path in common.walk(config.blog_dir, config.source_exts):
            blog_post = content.BlogPost.from_file(posting_path)
            self.cache.add(blog_post)
            yield blog_post
        # rebuild the cache indices for the related content pages
        self.cache.build_indices()
        # base indizes
        pinb, pinf = self.config.posts_in_blog, self.config.posts_in_feed
        yield content.BlogIndex.from_cache(None, self.cache, pinb)
        yield content.FeedIndex.from_cache(None, self.cache, pinf)
        yield content.TagIndex.from_cache(cache=self.cache)
        # tag pages
        for content_id in self.cache.tags:
            yield content.TagPage.from_cache(content_id, self.cache)
        # date indizes
        for content_id in self.cache.days:
            yield content.DayIndex.from_cache(content_id, self.cache)
        for content_id in self.cache.months:
            yield content.MonthIndex.from_cache(content_id, self.cache)
        for content_id in self.cache.years:
            yield content.YearIndex.from_cache(content_id, self.cache)


class Update(Renderset):
    """ class for rendering blog posts and static pages that have changed
    
    to determ what items have changed, the last git commit is queried. If a 
    template has changed or a caching error occurs, a NeedsRebuildError will be 
    raised
    """
    
    def __init__(self, config, cache):
        """ initialization """
        super(Update, self).__init__(config, cache)
        # storage for item to render or delete
        self.to_render = set()
        self.to_delete = set()
    
    def items_to_render(self):
        """ returns the storage of all items that should be rendered """
        return self.to_render

    def items_to_delete(self):
        """ returns the storage of all items that should be deleted """
        return self.to_delete
    
    def patch(self, gitdiff):
        """ calculates what should be rendered or deleted by a git diff """
        # old items are old versions of items or were deleted
        old_items = set()
        for diff in gitdiff:
            new_git_item, old_git_item = diff.a_blob, diff.b_blob
            if old_git_item:
                common.log.debug("renderset: found old git item '%s'" %\
                                 old_git_item.path)
                self._process_item(old_items, old_git_item, is_old=True)
            if new_git_item:
                common.log.debug("renderset: found new git item '%s'" %\
                                 new_git_item.path)
                self._process_item(self.to_render, new_git_item, is_old=False)
        # rebuild the cache indices for related items
        self.cache.build_indices()
        for item in old_items:
            if item.is_index and item.is_in_cache(self.cache):
                # old index items that are still in the cache and therefor have 
                # other related blog posts should be rerendered
                self.to_render.add(item)
            elif item not in self.to_render:
                # content items that will be not rendered again should be 
                # deleted.
                self.to_delete.add(item)
        # all items related to blog posts need their content to be set with the
        # updated cache information
        for item in self.to_render:
            if item.is_index:
                item.set_content_from_cache(self.cache)
        # we need to add the basic indices to the things to render
        pinb, pinf = self.config.posts_in_blog, self.config.posts_in_feed
        blog = content.BlogIndex.from_cache(None, self.cache, pinb)
        feed = content.FeedIndex.from_cache(None, self.cache, pinf)
        tags = content.TagIndex.from_cache(cache=self.cache)
        self.to_render.update([blog, feed, tags])
        # and an info
        common.log.info("renderset: %d items to delete" % len(self.to_delete))
        common.log.info("renderset: %d items to render" % len(self.to_render))
        
    def _process_item(self, storage, git_item, is_old):
        """ chooses how a git item should be processed
        
        If a template has changed or a caching error occurs, a NeedsRebuildError 
        will be raised
        """
        gp = git_item.path
        if gp.startswith(self.config.template_dir):
            # a template has changed, the blog should be rebuild
            raise common.NeedsRebuildError('a template has changed')
        elif not common.is_source_file(gp, self.config.source_exts):
            # it's not a source file that could be rendered
            common.log.debug("renderset: git item is not a source file")
            return            
        elif gp.startswith(self.config.page_dir):
            # a static page has changed
            common.log.debug("renderset: git item is static page")
            changes = self._process_static_page(git_item, is_old)
        elif gp.startswith(self.config.blog_dir):
            # a blog post has changed
            common.log.debug("renderset: git item is blog post")
            changes = self._process_blog_post(git_item, is_old)
        else:
            # all other things must not be rerendered
            common.log.debug("renderset: git item is unrelated to update")
            return
        # store the changed items
        storage.update(changes)

    def _process_static_page(self, git_item, is_old):
        """ process a changed static page """
        page = content.StaticPage(git_item.path)
        if not is_old:
            # if it is a new or updated page, read its content from the git blob
            utf8_content = codecs.decode(git_item.data_stream.read(), "utf-8")
            page.parse_content(utf8_content)
        return [page]
        
    def _process_blog_post(self, git_item, is_old):
        """ processes a changed blog post and it's related indices 
        
        will raise a NeedsRebuildError if a deleted blog post or an old version
        of a blog post is not found in the cache.
        """
        if is_old:
            # the item is deleted or an old version
            posting = self.cache.pop(git_item.path, None)
            if not posting:
                raise common.NeedsRebuildError('"%s" not in cache' %\
                                                git_item.path)
        else:
            # if it is a new or updated blog post, read its content from the git 
            # blob and add it to the cache
            posting = content.BlogPost(git_item.path)
            utf8_content = codecs.decode(git_item.data_stream.read(), "utf-8")
            posting.parse_content(utf8_content)
            self.cache.add(posting)
        # calculate the related date and tag indices of the blog post
        day_id = common.date_tuple(posting)
        day = content.DayIndex(day_id)
        month = content.MonthIndex(day_id[:2])
        year = content.YearIndex(day_id[:1])
        tags = [content.TagPage(tag) for tag in posting.headers["tags"]]
        return [posting, day, month, year] + tags
