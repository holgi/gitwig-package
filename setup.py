from setuptools import setup, find_packages

version = "0.2"

setup(

    # general stuff
    name = "gitwig",
    version = version,
    
    description = "a static blog engine with git backend",
    long_description=""" """,
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    
    # metadata for upload to PyPI
    author = "Holger Frey",
    author_email = "mail@holgerfrey.de",
    license = "BSD",
    keywords = "blog",
    #url = "http://holgerfrey.de/projects/gitwig/",   # project home page, if any

    # package definition
    packages=['gitwig'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "markdown>=2.1",
        "Pygments>=1.5",
        "genshi>=0.6",
        "GitPython>=0.3.2.RC1",
        "PyYAML>=3.10"
    ],
    entry_points="""
    # -*- Entry points: -*-
    """,
    # package_data={'': ['safeguard_logo.jpg']},
    
    # addition for testing
    # test_suite="nose.collector",
    # tests_require="nose",
)
