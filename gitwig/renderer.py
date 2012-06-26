import os
import markdown
from genshi.template import TemplateLoader
from genshi.filters.transform import Transformer

from . import common

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
