import git
import os
import socket

from . import cache
from . import common
from . import renderer
from . import renderset

class Workflow(object):

    def __init__(self, config, renderer_func):
        self.config = config
        self.render = renderer_func

    def rebuild(self):
        tmp_cache = cache.BlogCache()
        what = renderset.Rebuild(self.config, tmp_cache)
        for item in what.items_to_render():
            self.render(item)
        tmp_cache.write(self.config.cache_path)
        self._clean_empty_directories()
        
    def update(self):
        try:
            tmp_cache = cache.BlogCache.from_file(self.config.cache_path)
            repo = git.Repo(".")
            head_commit = repo.head.commit
            parent_commit = head_commit.parents[0]
            git_diff = head_commit.diff(parent_commit)
            common.log.info("workflow: found %d changes in git" % len(git_diff))
            what = renderset.Update(self.config, tmp_cache)
            what.patch(git_diff)
            for item in what.items_to_delete():
                self.delete(item)
            for item in what.items_to_render():
                self.render(item)
            tmp_cache.write(self.config.cache_path)
            self._clean_empty_directories()
        except common.NeedsRebuildError, e:
            common.log.warn(" %s, issuing rebuild" % e.message)
            self.rebuild()
    
    def delete(self, item):
        sub_path_parts = item.get_url_parts()
        deploy_path = os.path.join(self.config.deploy_dir, *sub_path_parts)
        common.log.info("workflow: deleting '%s'" % deploy_path)
        if os.path.isfile(deploy_path):
            os.remove(deploy_path)
    
    def _clean_empty_directories(self):
        maybe_empty_dirs = []
        for dirpath, dirnames, filenames in os.walk(self.config.deploy_dir):
            if not filenames:
                maybe_empty_dirs.append(dirpath)
        for dir in sorted(maybe_empty_dirs, reverse=True):
            if not os.listdir(dir):
                common.log.info("workflow: deleting empty directory %s" % dir)
                os.rmdir(dir)

def serve(directory="."):
    import SimpleHTTPServer
    import SocketServer
    import os

    os.chdir(directory)

    PORT = 8000
    handler = SimpleHTTPServer.SimpleHTTPRequestHandler

    httpd = None
    while not httpd:
        try:
            httpd = SocketServer.TCPServer(("", PORT), handler)
        except socket.error:
            if httpd is None:
                print "waiting for socket"
                httpd = False

    print "serving at port", PORT
    httpd.serve_forever()

