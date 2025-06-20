# -*- coding: utf-8 -*-

##########################################################################
# OpenLP - Open Source Lyrics Projection                                 #
# ---------------------------------------------------------------------- #
# Copyright (c) 2008 OpenLP Developers                                   #
# ---------------------------------------------------------------------- #
# This program is free software: you can redistribute it and/or modify   #
# it under the terms of the GNU General Public License as published by   #
# the Free Software Foundation, either version 3 of the License, or      #
# (at your option) any later version.                                    #
#                                                                        #
# This program is distributed in the hope that it will be useful,        #
# but WITHOUT ANY WARRANTY; without even the implied warranty of         #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
# GNU General Public License for more details.                           #
#                                                                        #
# You should have received a copy of the GNU General Public License      #
# along with this program.  If not, see <https://www.gnu.org/licenses/>. #
##########################################################################
"""
The :mod:`~openlp.core.ui.dark` module looks for and loads a dark theme
"""
from subprocess import Popen, PIPE
from enum import Enum
from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common.platform import is_macosx, is_win
from openlp.core.common.registry import Registry

try:
    import qdarkstyle
    HAS_DARK_THEME = True
except ImportError:
    HAS_DARK_THEME = False

WIN_REPAIR_STYLESHEET = """
QMainWindow::separator
{
  border: none;
}

QDockWidget::title
{
  border: 1px solid palette(dark);
  padding-left: 5px;
  padding-top: 2px;
  margin: 1px 0;
}

QToolBar
{
  border: none;
  margin: 0;
  padding: 0;
}
"""

MEDIA_MANAGER_STYLE = """
QDockWidget#media_manager_dock > QWidget {
    padding-left: 4px;
    padding-right: 4px;
    border-radius: 0px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-top: none;
    border-bottom: none;
}

QDockWidget#media_manager_dock::title {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 4px;
    color: palette(window-text);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-bottom: none;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
}

/* Make the main toolbox transparent */
QToolBox#media_tool_box {
    border: none;
    background: transparent;
}

/* Style for unselected tabs */
QToolBox#media_tool_box::tab {
    background: palette(button);
    border: 0;
    border-radius: 8px;
    margin-top: 0;
    margin-bottom: 0;
    text-align: left;
}

QToolBox#media_tool_box::tab:hover:!selected {
    background: palette(mid);
}

QToolBox#media_tool_box::tab:selected {
    background: rgba(100, 100, 100, 0.7);
}

QToolBox#media_tool_box::pane {
    background: palette(base);
    border: 2px solid palette(highlight);
    border-top: none;
    border-bottom-left-radius: 6px;
    border-bottom-right-radius: 6px;
    margin-top: -2px;
    padding: 8px;
}

#SongList {
	border-radius: 16px;
}
"""

PROGRESSBAR_STYLE = """
QProgressBar{
    height: 10px;
}
"""


class UiThemes(Enum):
    """
    An enumeration for themes.
    """
    Automatic = 'automatic'
    DefaultLight = 'light:default'
    DefaultDark = 'dark:default'
    QDarkStyle = 'dark:qdarkstyle'


def is_ui_theme_dark():
    ui_theme_name = Registry().get('settings').value('advanced/ui_theme_name')

    if ui_theme_name is None or ui_theme_name == UiThemes.Automatic:
        return is_system_darkmode()
    else:
        return ui_theme_name.value.startswith('dark:')


def is_ui_theme(ui_theme: UiThemes):
    ui_theme_name = Registry().get('settings').value('advanced/ui_theme_name')
    return ui_theme_name == ui_theme


def init_ui_theme_if_needed(ui_theme_name):
    return not isinstance(ui_theme_name, UiThemes)


def has_ui_theme(ui_theme: UiThemes):
    if ui_theme == UiThemes.QDarkStyle:
        return HAS_DARK_THEME
    return True


IS_SYSTEM_DARKMODE = None


def is_system_darkmode():
    global IS_SYSTEM_DARKMODE

    if IS_SYSTEM_DARKMODE is None:
        try:
            if is_win():
                IS_SYSTEM_DARKMODE = is_windows_darkmode()
            elif is_macosx():
                IS_SYSTEM_DARKMODE = is_macosx_darkmode()
            else:
                IS_SYSTEM_DARKMODE = False
        except Exception:
            IS_SYSTEM_DARKMODE = False

    return IS_SYSTEM_DARKMODE


def is_windows_darkmode():
    """
    Detects if Windows is using dark mode system theme.

    Source: https://github.com/olivierkes/manuskript/blob/731e017e9e0dd7e4062f1af419705c11b2825515/manuskript/main.py
    (GPL3)

    Changes:
        * Allowed palette to be set on any operating system;
        * Split Windows Dark Mode detection to another function.
    """
    theme_settings = QtCore.QSettings('HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes'
                                      '\\Personalize',
                                      QtCore.QSettings.Format.NativeFormat)
    return theme_settings.value('AppsUseLightTheme') == 0


def is_macosx_darkmode():
    """
    Detects if Mac OS X is using dark mode system theme.

    Source: https://stackoverflow.com/a/65357166 (CC BY-SA 4.0)

    Changes:
        * Using OpenLP formatting rules
        * Handling exceptions
    """
    try:
        command = 'defaults read -g AppleInterfaceStyle'
        process = Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
        stdin = process.communicate()[0]
        return bool(stdin)
    except Exception:
        return False


def set_default_theme(app):
    """
    Setup theme
    """
    if is_ui_theme(UiThemes.DefaultDark) or (is_ui_theme(UiThemes.Automatic) and is_ui_theme_dark()):
        set_default_darkmode(app)
    elif is_ui_theme(UiThemes.DefaultLight):
        set_default_lightmode(app)


def set_default_lightmode(app):
    """
    Setup lightmode on the application if Default Lightt theme is enabled in the OpenLP Settings.
    """
    app.setStyle('Fusion')
    app.setPalette(app.style().standardPalette())


def set_default_darkmode(app):
    """
    Setup darkmode on the application if enabled in the OpenLP Settings or using a dark mode system theme.

    Source:
    https://github.com/olivierkes/manuskript/blob/731e017e9e0dd7e4062f1af419705c11b2825515/manuskript/main.py
    (GPL3)

    Changes:
        * Allowed palette to be set on any operating system;
        * Split Windows Dark Mode detection to another function.
    """
    app.setStyle('Fusion')
    dark_palette = QtGui.QPalette()
    dark_color = QtGui.QColor(45, 45, 45)
    disabled_color = QtGui.QColor(127, 127, 127)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Window, dark_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtCore.Qt.GlobalColor.white)
    dark_palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.WindowText, disabled_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(18, 18, 18))
    dark_palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, dark_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtCore.Qt.GlobalColor.white)
    dark_palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, QtCore.Qt.GlobalColor.black)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Text, QtCore.Qt.GlobalColor.white)
    dark_palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.Text, disabled_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Button, dark_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtCore.Qt.GlobalColor.white)
    dark_palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.ButtonText, disabled_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtCore.Qt.GlobalColor.red)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtCore.Qt.GlobalColor.black)
    dark_palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.HighlightedText, disabled_color)
    # Fixes ugly (not to mention hard to read) disabled menu items.
    # Source: https://bugreports.qt.io/browse/QTBUG-10322?focusedCommentId=371060#comment-371060
    dark_palette.setColor(QtGui.QPalette.ColorGroup.Disabled,
                          QtGui.QPalette.ColorRole.Light,
                          QtCore.Qt.GlobalColor.transparent)
    # Fixes ugly media manager headers.
    dark_palette.setColor(QtGui.QPalette.ColorRole.Mid, QtGui.QColor(64, 64, 64))
    app.setPalette(dark_palette)


def get_alternate_rows_repair_stylesheet(base_color_name):
    return 'QTableWidget, QListWidget, QTreeWidget {alternate-background-color: ' + base_color_name + ';}\n'


def get_application_stylesheet():
    """
    Return the correct application stylesheet based on the current style and operating system

    :return str: The correct stylesheet as a string
    """
    stylesheet = ''
    if is_ui_theme(UiThemes.QDarkStyle):
        stylesheet = qdarkstyle.load_stylesheet_pyqt()
    else:
        if not Registry().get('settings').value('advanced/alternate rows'):
            base_color = QtWidgets.QApplication.palette().color(QtGui.QPalette.ColorGroup.Active,
                                                                QtGui.QPalette.ColorRole.Base)
            alternate_rows_repair_stylesheet = get_alternate_rows_repair_stylesheet(base_color.name())
            stylesheet += alternate_rows_repair_stylesheet
        if is_win():
            stylesheet += WIN_REPAIR_STYLESHEET
    
    stylesheet += '''    
    QDockWidget > QWidget {
        border-radius: 12px;
    }

    QWidget#main_content {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
    }
    
    QStatusBar#status_bar {
        background: rgba(0, 0, 0, 0.2);
        border: none;
        border-top: 1px solid rgba(255, 255, 255, 0.15);
    }

    QToolBar {
        background: rgba(255, 255, 255, 0.1);
        border: none;
        border-radius: 8px;
    }
    
    QSplitter::handle {
        background: rgba(255, 255, 255, 0.2);
        border-radius: 2px;
    }
    
    QSplitter::handle:horizontal {
        width: 2px;
    }
    
    QSplitter::handle:vertical {
        height: 2px;
    }
    '''
    
    stylesheet += 'QWidget#slide_controller_toolbar QToolButton::checked {' \
        '  background-color: palette(highlight);' \
        '  color: palette(highlighted-text);' \
        '}'
    return stylesheet


def get_library_stylesheet():
    """
    Return the correct stylesheet for the main window

    :return str: The correct stylesheet as a string
    """
    if not is_ui_theme(UiThemes.QDarkStyle):
        return MEDIA_MANAGER_STYLE
    else:
        return ''
