import os

from . import common
from . import content


class Renderset(object):

    def __init__(self, config, cache):
        self.config = config
        self.cache = cache
    
    def items_to_delete(self):
        return set()
        
    def items_to_render(self):
        return set()
        

class Rebuild(Renderset):
    
    def __init__(self, config, cache):
        super(Rebuild, self).__init__(config, cache)
    
    def items_to_render(self):
        config = self.config
        # static pages
        for page_path in common.walk(config.page_dir, config.source_exts):
            yield content.StaticPage.from_file(page_path)
        # blog posts
        for posting_path in common.walk(config.blog_dir, config.source_exts):
            blog_post = content.BlogPost.from_file(posting_path)
            yield blog_post
            self.cache.add(blog_post)
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
    
    def __init__(self, config, cache):
        super(Update, self).__init__(config, cache)
        self.to_render = set()
        self.to_delete = set()
    
    def items_to_render(self):
        return self.to_render

    def items_to_delete(self):
        return self.to_delete
    
    def patch(self, gitdiff):
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
        # old index items that are still in the cache and therefor have other
        # related posts should be rerendered, every thing else should be
        # deleted
        for item in old_items:
            if item.is_index and item.is_in_cache(self.cache):
                self.to_render.add(item)
            else:
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
        gp = git_item.path
        if gp.startswith(self.config.template_dir):
            raise common.NeedsRebuildError('a template has changed')
        elif not common.is_source_file(gp, self.config.source_exts):
            common.log.debug("renderset: git item is not a source file")
            return            
        elif gp.startswith(self.config.page_dir):
            common.log.debug("renderset: git item is static page")
            changes = self._process_static_page(git_item, is_old)
        elif gp.startswith(self.config.blog_dir):
            common.log.debug("renderset: git item is blog post")
            changes = self._process_blog_post(git_item, is_old)
        else:
            common.log.debug("renderset: git item is unrelated to update")
            # all other things must not be rerendered
            return
        storage.update(changes)

    def _process_static_page(self, git_item, is_old):
        page = content.StaticPage(git_item.path)
        if not is_old:
            page.read(git_item.data_stream)
        return [page]
        
    def _process_blog_post(self, git_item, is_old):
        if is_old:
            posting = self.cache.pop(git_item.path, None)
            if not posting:
                raise common.NeedsRebuildError('"%s" not in cache' %\
                                                git_item.path)
        else:
            posting = content.BlogPost(git_item.path)
            posting.read(git_item.data_stream)
            self.cache.add(posting)
        day_id = common.date_tuple(posting)
        day = content.DayIndex(day_id)
        month = content.MonthIndex(day_id[:2])
        year = content.YearIndex(day_id[:1])
        tags = [content.TagPage(tag) for tag in posting.headers["tags"]]
        return [posting, day, month, year] + tags
