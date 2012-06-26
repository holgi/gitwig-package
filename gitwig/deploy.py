# global imports

from genshi.template import TemplateLoader
from genshi.filters.transform import Transformer

import git
import markdown
import os
import socket

# local imports
from . import cache
from . import common
from . import renderset

class Renderer(object):

    def __init__(self, settings, template_function, converter_function):
        self.deploy_dir = settings.deploy_dir
        self.templating = template_function
        self.common_data = {
            "settings": settings,
            "converter": converter_function
        }
            
    def __call__(self, content_object):
        self.render(content_object)
    
    def render(self, content_object):
        data = self.common_data.copy()
        data["content"] = content_object
        sub_path_parts = content_object.get_url_parts()
        deploy_path = self._check_deploy_dir(self.deploy_dir, *sub_path_parts)
        common.log.info("render: deploying '%s'" % deploy_path)
        deploy_handle = open(deploy_path, "w")
        deploy_handle.write(self.templating(content_object.template, data))
        deploy_handle.close()

    def _check_deploy_dir(self, *parts):
        for i in xrange(1, len(parts)):
            dir_to_check = os.path.join(*parts[:i])
            if not os.path.exists(dir_to_check):
                os.mkdir(dir_to_check)
        return os.path.join(*parts)

class MarkdownConverter(object):

    def __init__(self, markdown_instance):
        self.markdown_instance =  markdown_instance

    def __call__(self, content_to_convert):
        self.markdown_instance.reset()
        return self.markdown_instance.convert(content_to_convert)


class GenshiTemplating(object):

    def __init__(self, config):
        self.config = config
        self.template_loader = TemplateLoader(config.template_dir)

    def __call__(self, template, data):
        render_type, doctype = self._types_by_template(template)
        template = self.template_loader.load(template)
        stream = self._transform_stream(template.generate(**data))
        return stream.render(render_type, doctype=doctype)

    def _types_by_template(self, template):
        return ("xml", None) if template.endswith(".xml") else ("html", "html5")

    def _transform_stream(self, stream):
        stream |= Transformer('//*[@href]').attr('href', self._absolutize)
        stream |= Transformer('//*[@src]').attr('src', self._absolutize)
        return stream

    def _absolutize(self, name, event):
        attrs = event[1][1]
        href = attrs.get(name)
        if href and not href.startswith("#") and "/" not in href:
            href = self.config.media_prefix + "/" + href
        return href



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

