# -*- coding: utf-8 -*-
"""
/***************************************************************************
        begin                : 2026-07-18
        copyright            : (C) 2026 by Bruno Vermeulen
        email                : bruno.vermeulen@hotmail.com
 ***************************************************************************/
"""

from pathlib import Path
import os
import sys

# add path to required site-packages not available in QGIS depending on OS
if os.name == "posix":
    import_path = Path(
        "~/.local/share/QGIS/QGIS3/profiles/default/python/site-packages"
    )

elif os.name == "nt":
    import_path = (
        Path(os.getenv("APPDATA")) / "QGIS/QGIS3/profiles/default/python/site-packages"
    )

else:
    import_path = ""

import_path = str(import_path)
if import_path and import_path not in sys.path:
    sys.path.insert(0, import_path)


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load BinSelect class from file bin_select.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .bin_select import BinSelect

    return BinSelect(iface)
