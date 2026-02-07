# -*- coding: utf-8 -*-

"""
Bundled print service templates

Importing this package auto-registers the templates with the
`TemplateRegistry` in `openlp.core.ui.printservice_templates`.
"""

# Import submodules to trigger registration
from . import professional  # noqa: F401
from . import minimal       # noqa: F401
from . import compact       # noqa: F401
from . import modern        # noqa: F401

__all__ = [
    'professional',
    'minimal',
    'compact',
    'modern',
]

