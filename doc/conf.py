project = "lemke"
copyright = "2026, Bernhard von Stengel"
author = "Bernhard von Stengel"

extensions = [
    "matplotlib.sphinxext.plot_directive",
    "sphinx_click",
    "sphinx_design",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

autosummary_generate = True
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
}

templates_path = ["_templates"]
exclude_patterns = ["_build"]

master_doc = "index"

html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/gambitproject/lemke",
            "icon": "fab fa-github-square",
            "type": "fontawesome",
        }
    ],
    "shorten_urls": False,
}

plot_html_show_source_link = False
plot_html_show_formats = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}
