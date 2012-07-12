""" classes and functions for content in the inbox directory """

# global imports
import datetime
import os
import shutil
import uuid

from . import common
from . import content


class FolderInbox(object):
    """ processes media files and blog posts in a inbox directory """

    def __init__(self, config):
        """ initialization """
        self.config = config
        self.media_files  = []
        self.source_files = []
        self._media_map  = []
        self._article_map  = []

    def process(self):
        """ the complete workflow """
        self.scan(self.config.inbox_dir)
        self.check_media_files()
        self.prepare_source_files()
        self.move_media_files()
        self.move_source_files()
    
    def scan(self, inbox_dir):
        """ scans the inbox folder for source and media files """
        paths =   ( os.path.join(inbox_dir, p) for p in os.listdir(inbox_dir) )
        no_link = ( p for p in paths if not os.path.islink(p) )
        files =   ( p for p in no_link if os.path.isfile(p) )
        for file_path in files:
            if common.is_source_file(file_path, self.config.source_exts):
                common.log.debug("inbox: found source file '%s'" % file_path)
                self.source_files.append(file_path)
            elif not common.is_hidden_file(file_path):
                common.log.debug("inbox: found media file '%s'" % file_path)
                self.media_files.append(file_path)
    
    def check_media_files(self):
        """ checks if the media files can be moved without replacing content 

        will raise a InboxFileExistsError exception if a media file with the
        same name exists in the media folder
        """
        for inbox_file_path in self.media_files:
            name = os.path.basename(inbox_file_path)
            dest_path = os.path.join(self.config.media_dir, name)
            if os.path.exists(dest_path):
                msg = "the file '%s' already exists in the media folder" % name
                raise common.InboxFileExistsError(msg)
            self._media_map.append( (inbox_file_path, dest_path) )

    def prepare_source_files(self):
        """ reads blog posts in the inbox directory, sets default headers """
        for inbox_file_path in self.source_files:
            common.log.debug("inbox: prepping blog post " % inbox_file_path)
            default_headers = self.get_default_article_headers(inbox_file_path)
            blog_post = content.BlogPost(inbox_file_path, default_headers)
            blog_post.load(inbox_file_path)
            rel_path = blog_post.get_archive_path()
            dest_path = os.path.join(self.config.blog_dir, rel_path)
            self._article_map.append( (inbox_file_path, dest_path, blog_post) )
    
    def move_media_files(self):
        """ moves the media files to the media directory """
        for src_path, dest_path in self._media_map:
            common.log.info("inbox: '%s' -> '%s' " % (src_path, dest_path))
            self._check_intermediate_directories(dest_path)
            shutil.move(src_path, dest_path)
    
    def move_source_files(self):
        """ writes the blog posts to the blog directory """
        for src_path, dest_path, blog_post in self._article_map:
            common.log.info("inbox: '%s' -> '%s' " % (src_path, dest_path))
            self._check_intermediate_directories(dest_path)
            blog_post.write(dest_path)
            os.remove(src_path)

    def get_default_article_headers(self, path):
        """ sets the default header field as strings """
        # use the modification date of the file as the creation date
        # this is a bit tricky since the headers are parsed later,
        # we need to set them as a string that gets parsed again
        mod_timestamp = os.path.getmtime(path)
        mod_datetime = datetime.datetime.fromtimestamp(mod_timestamp)
        mod_date_str = content.format_date(mod_datetime)
        defaults = {
            "title":   self.config.default_title,
            "tags":    self.config.default_tags,
            "uuid":    str(uuid.uuid4()),           # a random uuid
            "created": mod_date_str,
            "updated": mod_date_str }
        return defaults
    
    def _check_intermediate_directories(self, file_path):
        """ checks if all directories exist and creates them if necessary """
        dir_path, file_name = os.path.split(file_path)
        dir_to_check = ""
        for sub_dir in dir_path.split(os.path.sep):
            dir_to_check = os.path.join(dir_to_check, sub_dir)
            if not os.path.exists(dir_to_check):
                os.mkdir(dir_to_check)
