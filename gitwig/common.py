import os
import logging

class NeedsRebuildError(Exception):
    pass

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger('gitwig')

def is_source_file(path, source_extensions):
    base, ext = os.path.splitext(path)
    return not is_hidden_file(path) and ext in source_extensions

def is_hidden_file(path):
    return os.path.basename(path).startswith(".")

def walk(root_dir, source_extensions):
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if is_source_file(filepath, source_extensions):
                yield filepath

def date_tuple(blog_post, key="created"):
    date = blog_post.headers[key]
    return (date.year, date.month, date.day)
