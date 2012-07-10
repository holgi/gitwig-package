gitwig
======

`gitwig` is another of these blog enabled static site generators. You want some more buzzwords? It's written in [python][py], uses [markdown][md] for the content and [genshi][ge] as a templating engine. As a bonus [git][gi] is used for deploying the content to the server.

What makes it different from the other projects? Well most of them don't combine them in the way I like :-) The main focus here is, that the rendering of the content to HTML happens on the server and not locally on my machine. This has the main advantage is, that I don't have to wait for my laptop to finish the rendering and deploying all the changes to the server. The main disadvantages might be that there is no good error reporting in place and that the rendering might take longer.

requirements
------------

If you want to use `gitwig` you need access to a server where you can 

- install python packages
- add files to your $PATH
- create git repositories that are accessible from your local machine
- configure different directories served by a webserver (I would suggest [nginx][6])

blog support
------------

I should define this a little bit more. With "blog support" I mean the automatic creation of daily, monthly, yearly and tag indices. And of cause a blog page, an atom feed and a tag overview page.

how the repositories are used
-----------------------------

The basic setup depends on at least three git repositories:

1. the `hub`: this is the bare main repository on the server that gets cloned
2. `live`: a clone of `hub` on the server. This is provides the data to render the site in an accessible way
3. `local`: a local clone of the `hub`, where blog posts etc. are added

By using hooks inside the two server repositories, any changes pushed to the `hub` repository will automatically be rendered.

setup of the server
-------------------

A short notice: To destinquish between server and local commands I will use `s>` for the server and `l>` for local commands

1. setup the `hub` repository: `s> git init --bare --shared blog-hub.git`
2. clone the `live` repository: `s> git clone <path to hub> blog-live`
3. download the [example blog][7] into the `live` repository, don't clone it!
4. push the changes to the `hub`: 
   
       s:live> git add -A
       s:live> git commit -m "import of example blog"
       s:live> git push origin master

5. download this project on your server and run `python setup.py install`
6. in the direcotry `files` are five files that need your attention.
    1. `bare-post-update-hook.sh` 
        
        adjust the paths, move it to `blog-hub.git/hooks/post-update` and set the execution bit.
        
        This will pull any changes from the `hub` to the `live` repository.
    
    2. `live-post-merge-hook.py`
        
        move it to `blog-live/hooks/post-merge` and set the execution bit.
        
        This will render the changes after they were pulled from the `hub`.
        
    3. `live-post-commit-hook.sh` 
    
        adjust the path, move it to `blog-live/hooks/post-commit` and set the execution bit.
    
        This will push any changes commited to the `live` repository to the `hub` and render the site.
        
    4. `gitwig-update.py`
        
        move it somewhere in your $PATH as `gitwig-update` and set the execution bit
        
        This script is run to render the site. You might need to adjust the locale in the script. If you want to change some things – for example adding code highlighting – this is your starting point.
    
    5. `config.yaml` 
        
        move this to your live repository and adjust the settings. All config possibilities can be found in the `settings.py` module of the `gitwig` package.

7. Adjust your webserver path to point to the deploy directory and the static directory. On my server I keep the deploy directory outside of the `live` directory and use a symlink to the static directory inside the `live` repository.

setup of the local machine
--------------------------

    l> git clone <url to bare> blog-local
    # make some changes to the static page or template
    l> git add -A
    l> git push origin master

That was easy!

some unsorted remarks
----------------------

- changes to content files like static pages or blog posts will only render this files and related index files
- if a template file is changed, the complete site will be rerendered
- the rerendering of the site will not delete old items first. this is intentional.
- the deploy directory should not be under git control.
- if a path to a linked file - like an image - does not contain a slash `/`, the path will be prepended with the setting of `media_prefix`. Just write your content normally and put all linked stuff in the `static/media` directory.
- all headers must be set in a blog post.

todos
-----

Make it easier to write blog posts :-) Currently the blog posts must be written including all headers and put in the right directory. That's not nice. 

For the next step I will include an `inbox` folder, where new blog posts and related media files can be stored. The headers of the posts will be automatically added accordingly and the media files moved to the target folder.

I still think about a possibility to add a cron based mail inbox…

---

An example of such a blog can be found at [holgerfrey.de][8].

Did I forget something? Sure, but I don't know what since I forgot…


[py]: http://www.python.org
[md]: http://daringfireball.net/projects/markdown/
[ge]: http://genshi.edgewall.org/
[gi]: http://git-scm.com/

[5]: http://www.dejaaugustine.com/2011/05/leveraging-git-as-a-full-fledged-web-development-tool/
[6]: http://nginx.org/
[7]: http://github.com/holgi/gitwig-example
[8]: http://holgerfrey.de