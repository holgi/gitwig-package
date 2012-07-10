#!/Users/holgerfrey/Developer/gitwig/bin/python
#
# An example hook script to prepare a packed repository for use over
# dumb transports.
#
# rename it to gitwig-update, move it to your path and set the execution bit

import gitwig
import markdown
import locale

locale.setlocale(locale.LC_ALL, 'de_DE')

gitwig.common.log.setLevel(20)

config = gitwig.settings.Settings.from_file("config.yaml")

md_instance = markdown.Markdown(['codehilite(force_linenos=True)'])
md_converter = gitwig.deploy.MarkdownConverter(md_instance)
templating = gitwig.deploy.GenshiTemplating(config)
rendering = gitwig.deploy.Renderer(config, templating, md_converter)

worker = gitwig.deploy.Workflow(config, rendering)
worker.update()
