""" rendering and deployment of items defined by a renderset """

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
    """ callable to render a content object
    
    the content object may be first converted from another syntax like markdown
    and then rendered using a template
    """

    def __init__(self, settings, template_function, converter_function):
        """ initialization
        
        converter_function:
            callable to convert a content object (e.g. markdown)
            the callable has the responsebilty to eventually reset itself 
            between converting different content objects
            the callable should only accept a single content object
        template_function:
            callable to render a content object using a template
            the callable should accept a template path and a data dict
        """
        
        self.deploy_dir = settings.deploy_dir
        self.templating = template_function
        # standard set of data that is used in a template
        self.common_data = {
            "settings": settings,
            "converter": converter_function
        }
            
    def __call__(self, content_object):
        """ makes an object callable """
        self.render(content_object)
    
    def render(self, content_object):
        """ deploys a content object by using the template function """
        # setup of the data used in the template
        data = self.common_data.copy()
        data["content"] = content_object
        # calculate the file path to deploy to
        sub_path_parts = content_object.get_url_parts()
        deploy_path = self._check_deploy_dir(self.deploy_dir, *sub_path_parts)
        common.log.info("render: deploying '%s'" % deploy_path)
        # render to file using the templating function
        deploy_handle = open(deploy_path, "w")
        deploy_handle.write(self.templating(content_object.template, data))
        deploy_handle.close()

    def _check_deploy_dir(self, *parts):
        """ checks if all directories exist and creates them if necessary """
        for i in xrange(1, len(parts)):
            dir_to_check = os.path.join(*parts[:i])
            if not os.path.exists(dir_to_check):
                os.mkdir(dir_to_check)
        return os.path.join(*parts)


class MarkdownConverter(object):
    """ callable to convert a content object by using a markdown instance """

    def __init__(self, markdown_instance):
        """ initialization """
        self.markdown_instance =  markdown_instance

    def __call__(self, content_to_convert):
        """ resets the markdown instance and returns the converted content """
        self.markdown_instance.reset()
        return self.markdown_instance.convert(content_to_convert)


class GenshiTemplating(object):
    """ callable to use genshi as a templating function """

    def __init__(self, config):
        """ initialization """
        self.config = config
        self.template_loader = TemplateLoader(config.template_dir)

    def __call__(self, template, data):
        """ returns the rendered genshi stream """
        render_type, doctype = self._types_by_template(template)
        template = self.template_loader.load(template)
        stream = self._transform_stream(template.generate(**data))
        return stream.render(render_type, doctype=doctype)

    def _types_by_template(self, template):
        """ how a template should be rendered """
        return ("xml", None) if template.endswith(".xml") else ("html", "html5")

    def _transform_stream(self, stream):
        """ transformations of the genshi stream
        
        the basic transformation is to point directory local references to 
        the static media directory
        """
        stream |= Transformer('//*[@href]').attr('href', self._dll2smd)
        stream |= Transformer('//*[@src]').attr('src', self._dll2smd)
        return stream

    def _dll2smd(self, name, event):
        """ points directory local references to the static media directory 
        
        see _transform_stream and genshi api documentation
        """
        attrs = event[1][1]
        href = attrs.get(name)
        if href and not href.startswith("#") and "/" not in href:
            href = self.config.media_prefix + "/" + href
        return href


class Workflow(object):
    """ defines workflows for rebuilding and updating the site 
    
    the current working directory must be the base content directory of the site
    """


    def __init__(self, config, render_function):
        """ initialization 
        
        render_function:
            callable that accepts a conten item and renders it to a file
            see Renderer
        """
        self.config = config
        self.render = render_function

    def rebuild(self):
        """ workflow for rebuilding a complete site """
        tmp_cache = cache.BlogCache()
        what = renderset.Rebuild(self.config, tmp_cache)
        for item in what.items_to_render():
            self.render(item)
        tmp_cache.write(self.config.cache_path)
        self._clean_empty_directories()
        
    def update(self):
        """ workflow for updating a site according to the last git commit """
        try:
            # query git repo for the changes in the last commit
            repo = git.Repo(".")
            head_commit = repo.head.commit
            parent_commit = head_commit.parents[0]
            git_diff = head_commit.diff(parent_commit)
            common.log.info("workflow: found %d changes in git" % len(git_diff))
            # load cache and build renderset
            tmp_cache = cache.BlogCache.from_file(self.config.cache_path)
            what = renderset.Update(self.config, tmp_cache)
            what.patch(git_diff)
            # first delete old items, than render the new ones
            for item in what.items_to_delete():
                self.delete(item)
            for item in what.items_to_render():
                self.render(item)
            # write update cache back to file and clean empty direcotries
            tmp_cache.write(self.config.cache_path)
            self._clean_empty_directories()
        except common.NeedsRebuildError, e:
            # if a cache error occurs or a template has changed, we need to 
            # rebuild the site
            common.log.warn(" %s, issuing rebuild" % e.message)
            self.rebuild()
    
    def delete(self, item):
        """ deletes a deployed content item """
        sub_path_parts = item.get_url_parts()
        deploy_path = os.path.join(self.config.deploy_dir, *sub_path_parts)
        common.log.info("workflow: deleting '%s'" % deploy_path)
        if os.path.isfile(deploy_path):
            os.remove(deploy_path)
    
    def _clean_empty_directories(self):
        """ removes empty directories in the deploy directory """
        # first we check wich directories don't contain files and might therefor
        # be deleted
        maybe_empty_dirs = []
        for dirpath, dirnames, filenames in os.walk(self.config.deploy_dir):
            if not filenames:
                maybe_empty_dirs.append(dirpath)
        # the possible empty directories have to be deleted from the leaf dir 
        # upwards. but first we check if its really empty and does not contain
        # other directories that might be not empty
        for dir in sorted(maybe_empty_dirs, reverse=True):
            if not os.listdir(dir):
                common.log.info("workflow: deleting empty directory %s" % dir)
                os.rmdir(dir)


def serve(directory="."):
    """ quick helper function to start a http server """
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

