#!/usr/bin/env python3
#
# Inmanta documentation build configuration file, created by
# sphinx-quickstart on Wed Aug 21 10:14:55 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.
import importlib.metadata
import shutil
import sys, os, datetime, re
from importlib.metadata import PackageNotFoundError
from sphinx.errors import ConfigError


# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
# sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc', 'sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.graphviz', 'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode', 'sphinxarg.ext', 'sphinxcontrib.contentui', 'sphinxcontrib.inmanta.config',
    'sphinxcontrib.inmanta.dsl', 'sphinxcontrib.inmanta.environmentsettings', 'sphinx_click.ext', 'sphinx_design',
    'myst_parser', 'sphinx_substitution_extensions', 'sphinxcontrib.datatemplates',
]

myst_enable_extensions = ["colon_fence"]

def setup(app):
    # cut off license headers
    from sphinx.ext.autodoc import cut_lines
    app.connect('autodoc-process-docstring', cut_lines(15, what=['module']))
def check_dot_command():
    if shutil.which("dot") is None:
        raise Exception("The 'dot' command is not available. Please install Graphviz (https://graphviz.org) "
                        "and ensure that the 'dot' command is in the PATH.")

# Check for dot command availability during documentation build
check_dot_command()

try:
    # noinspection PyUnresolvedReferences
    # "tags" are injected while the file is being read
    if tags.has("include_redoc"):
        extensions.append('sphinxcontrib.redoc')
except NameError as e:
    # Openapi definition with Redoc won't be included
    pass

redoc_uri = 'https://cdn.jsdelivr.net/npm/redoc/bundles/redoc.standalone.js'
redoc = [
    {
        'name': 'Inmanta REST API',
        'page': 'reference/openapi',
        'spec': 'reference/openapi.json',
        'opts': {
            'hide-hostname': True,
            'path-in-middle-panel': True,
        }
    },
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# The encoding of source files.
# source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'Inmanta'
copyright = f'{datetime.datetime.now().year} Inmanta NV'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version: str
try:
    # if product's conf.py injected version information, use that one
    version
except NameError:
    if "INMANTA_DONT_DISCOVER_VERSION" in os.environ:
        # Used to:
        # Decouple the inmanta-core package from the inmanta package when running the tests.
        version = "1.0.0"
    else:
        try:
            version = importlib.metadata.version("inmanta")
        except PackageNotFoundError:
            raise ConfigError(
                """
The inmanta package is not installed. This way sphinx failed to discover the version number that should be
displayed on the documentation pages. Either install the inmanta package or set the environment variable
INMANTA_DONT_DISCOVER_VERSION when the version number is not important for this documentation build. The latter
solution will set the version number to 1.0.0.
                """
            )

# The full version, including alpha/beta/rc tags.
release = version


iso_gpg_key: str
oss_gpg_key: str = "A34DD0A274F07713"

try:
    # if product's conf.py injected an iso_gpg_key, use that one
    iso_gpg_key
except NameError:
    # else set a dummy value
    iso_gpg_key = "<gpg_key>"


version_major = int(version.split(".")[0])
rst_prolog = f"""\
.. |version_major| replace:: {version_major}
.. |iso_gpg_key| replace:: {iso_gpg_key}
.. |oss_gpg_key| replace:: {oss_gpg_key}
.. |release| replace:: {release}
"""



# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
# language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
# today = ''
# Else, today_fmt is used as the format for a strftime call.
# today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# The documentation build tool overrides this when extensions are included in the documentation build.

# Make sure iso-only documents are excluded from the doc build by default and only included for iso builds.
# We can't use the  `.. only:: iso` directive here because it is only suited to control the content of
# the documents and not their structure.


exclude_patterns = ['adr/*.md']

if not tags.has("iso"):
    exclude_patterns += [
        "lsm",
        "administrators/operational_procedures_with_lsm.rst",
        "administrators/support.rst"
    ]

# The reST default role (used for this markup: `text`) to use for all documents.
# default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
# add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
# add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
# show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
# modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

html_theme = "furo"

html_theme_options = {
    "footer_icons": [
        {
            "name": "Website",
            "url": "https://inmanta.com",
            "class": "fa-solid fa-globe",
        },
        {
            "name": "Linkedin",
            "url": "https://www.linkedin.com/company/inmanta-nv/",
            "class": "fa-brands fa-linkedin",
        },
        {
            "name": "Twitter",
            "url": "https://twitter.com/inmanta_com",
            "class": "fa-brands fa-twitter",
        },
        {
            "name": "GitHub",
            "url": "https://github.com/inmanta",
            "class": "fa-brands fa-github",
        },
    ],
    "light_css_variables": {
        "color-announcement-background": "#f0ab00",
        "color-announcement-text": "#000000",
    }
}

if tags.has("iso") and "INMANTA_ADD_OLD_VERSION_BANNER" in os.environ:
    html_theme_options["announcement"] = "This is the documentation for an old ISO version. You may want to consult the documentation for the <a href='https://docs.inmanta.com/inmanta-service-orchestrator/latest/'>latest ISO release</a>."

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = f"Inmanta OSS {release}"

# A shorter title for the navigation bar.  Default is the same as html_title.
# html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = "_static/inmanta-logo.png"

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = "_static/favicon.ico"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
# html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
# html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
# html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
# html_additional_pages = {}

# If false, no module index is generated.
# html_domain_indices = True

# If false, no index is generated.
# html_use_index = True

# If true, the index is split into individual pages for each letter.
# html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
# html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
# html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'InmantaDoc'

html_css_files = [
    "css/custom.css",
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/fontawesome.min.css",
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/solid.min.css",
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/brands.min.css",
]


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
    'papersize': 'a4paper',

# The font size ('10pt', '11pt' or '12pt').
# 'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
# 'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'inmanta.tex', 'Inmanta Documentation',
   'Inmanta NV', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
# latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
# latex_use_parts = False

# If true, show page references after internal links.
# latex_show_pagerefs = False

# If true, show URL addresses after external links.
# latex_show_urls = False

# Documents to append as an appendix to all manuals.
# latex_appendices = []

# If false, no module index is generated.
# latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'inmanta', 'Inmanta Documentation',
     ['Inmanta NV'], 1)
]

# If true, show URL addresses after external links.
# man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Inmanta', 'Inmanta Documentation',
   'Inmanta NV', 'Inmanta', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
# texinfo_appendices = []

# If false, no module index is generated.
# texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
# texinfo_show_urls = 'footnote'

# Ingnore link check of openapi.html because it's used in a toctree.
# A trick was required to include a non-sphinx document in a toctee.
linkcheck_ignore = [
    r'http(s)?://localhost:\d+/',
    r'http://127.0.0.1:\d+',
    r'http(s)?://172(.\d{1,3}){3}(:\d+)?',  # Ignoring all docker ips links
    r'openapi.html',
    r'https://twitter.com/inmanta_com',
    '../_specs/openapi.json',
    'extensions/inmanta-ui/index.html',
    '../extensions/inmanta-ui/index.html',
    '../../reference/modules/std.html#std.validate_type',
    '../reference/modules/std.html#std.getfact',
    r'https://github.com/inmanta/examples/tree/master/Networking/SR%20Linux#user-content-sr-linux-topology',
]

linkcheck_anchors_ignore=[
    # Ignore Scroll To Text Fragment anchors, because they are not supposed to be present in the HTML body.
    f"{re.escape(':~:text=')}.*",
]

graphviz_output_format = "svg"
