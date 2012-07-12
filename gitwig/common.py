""" common functions used in the package """

# global imports
import os
import logging

# setup of logging
logging.basicConfig(level=logging.WARNING)
log = logging.getLogger('gitwig')

class NeedsRebuildError(Exception):
    """ an update from git is not possible and a rebuild should be issued """
    pass

class InboxFileExistsError(Exception):
    """ an update from git is not possible and a rebuild should be issued """
    pass



def is_source_file(path, source_extensions):
    """ checks if the file is not hidden and has an source file extension """
    base, ext = os.path.splitext(path)
    return not is_hidden_file(path) and ext in source_extensions

def is_hidden_file(path):
    """ checks if the file is hidden """
    return os.path.basename(path).startswith(".")

def walk(root_dir, source_extensions):
    """ generator that walks a directory tree and emits found source files """
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if is_source_file(filepath, source_extensions):
                yield filepath

def date_tuple(blog_post, key="created"):
    """ returns a (year, month, day) tuple from a blog post header """
    date = blog_post.headers[key]
    return (date.year, date.month, date.day)
