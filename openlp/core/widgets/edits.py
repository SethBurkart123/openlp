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
The :mod:`~openlp.core.widgets.edits` module contains all the customised edit widgets used in OpenLP
"""
import logging
import re
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common import CONTROL_CHARS
from openlp.core.common.i18n import UiStrings, translate
from openlp.core.common.path import path_to_str, str_to_path
from openlp.core.common.registry import Registry
from openlp.core.lib.formattingtags import FormattingTags
from openlp.core.lib.ui import create_action, create_widget_action
from openlp.core.ui.icons import UiIcons
from openlp.core.widgets.dialogs import FileDialog
from openlp.core.widgets.enums import PathEditType


try:
    import enchant
    from enchant import DictNotFoundError
    from enchant.errors import Error
    ENCHANT_AVAILABLE = True
except ImportError:
    ENCHANT_AVAILABLE = False

log = logging.getLogger(__name__)


class SearchEdit(QtWidgets.QLineEdit):
    """
    This is a specialised QLineEdit with a "clear" button inside for searches.
    """
    searchTypeChanged = QtCore.Signal(int)

    def __init__(self, parent, settings_section):
        """
        Constructor.
        """
        super().__init__(parent)
        self.settings_section = settings_section
        self._current_search_type = -1
        self.clear_button = QtWidgets.QToolButton(self)
        self.clear_button.setIcon(UiIcons().backspace)
        self.clear_button.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
        self.clear_button.setStyleSheet('QToolButton { border: none; padding: 0px; }')
        self.clear_button.resize(18, 18)
        self.clear_button.hide()
        self.clear_button.clicked.connect(self._on_clear_button_clicked)
        self.textChanged.connect(self._on_search_edit_text_changed)
        self._update_style_sheet()
        self.settings = Registry().get('settings')
        self.setAcceptDrops(False)

    def _update_style_sheet(self):
        """
        Internal method to update the stylesheet depending on which widgets are available and visible.
        """
        frame_width = self.style().pixelMetric(QtWidgets.QStyle.PixelMetric.PM_DefaultFrameWidth)
        right_padding = self.clear_button.width() + frame_width
        if hasattr(self, 'menu_button'):
            left_padding = self.menu_button.width()
            stylesheet = 'QLineEdit {{ padding-left:{left}px; padding-right: {right}px; }} '.format(left=left_padding,
                                                                                                    right=right_padding)
        else:
            stylesheet = 'QLineEdit {{ padding-right: {right}px; }} '.format(right=right_padding)
        self.setStyleSheet(stylesheet)
        msz = self.minimumSizeHint()
        self.setMinimumSize(max(msz.width(), self.clear_button.width() + (frame_width * 2) + 2),
                            max(msz.height(), self.clear_button.height() + (frame_width * 2) + 2))

    def resizeEvent(self, event):
        """
        Reimplemented method to react to resizing of the widget.

        :param event: The event that happened.
        """
        size = self.clear_button.size()
        frame_width = self.style().pixelMetric(QtWidgets.QStyle.PixelMetric.PM_DefaultFrameWidth)
        self.clear_button.move(self.rect().right() - frame_width - size.width(),
                               (self.rect().bottom() + 1 - size.height()) // 2)
        if hasattr(self, 'menu_button'):
            size = self.menu_button.size()
            self.menu_button.move(self.rect().left() + frame_width + 2, (self.rect().bottom() + 1 - size.height()) // 2)

    def current_search_type(self):
        """
        Readonly property to return the current search type.
        """
        return self._current_search_type

    def set_current_search_type(self, identifier):
        """
        Set a new current search type.

        :param identifier: The search type identifier (int).
        """
        menu = self.menu_button.menu()
        for action in menu.actions():
            if identifier == action.data():
                self.setPlaceholderText(action.placeholder_text)
                self.menu_button.setDefaultAction(action)
                self._current_search_type = identifier
                self.settings.setValue('{section}/last used search type'.
                                       format(section=self.settings_section), identifier)
                self.searchTypeChanged.emit(identifier)
                return True

    def set_search_types(self, items):
        """
        A list of tuples to be used in the search type menu. The first item in the list will be preselected as the
        default.

         :param items:     The list of tuples to use. The tuples should contain an integer identifier, an icon (QIcon
             instance or string) and a title for the item in the menu. In short, they should look like this::

                    (<identifier>, <icon>, <title>, <place holder text>)

                For instance::

                    (1, <QIcon instance>, "Titles", "Search Song Titles...")

                Or::

                    (2, ":/songs/authors.png", "Authors", "Search Authors...")
        """
        menu = QtWidgets.QMenu(self)
        for identifier, icon, title, placeholder in items:
            action = create_widget_action(
                menu, text=title, icon=icon, data=identifier, triggers=self._on_menu_action_triggered)
            action.placeholder_text = placeholder
        if not hasattr(self, 'menu_button'):
            self.menu_button = QtWidgets.QToolButton(self)
            self.menu_button.setIcon(UiIcons().shortcuts)
            self.menu_button.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            self.menu_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
            self.menu_button.setStyleSheet('QToolButton { border: none; padding: 0px 10px 0px 0px; }')
            self.menu_button.resize(QtCore.QSize(28, 18))
        self.menu_button.setMenu(menu)
        self.set_current_search_type(
            self.settings.value('{section}/last used search type'.format(section=self.settings_section)))
        self.menu_button.show()
        self._update_style_sheet()

    def _on_search_edit_text_changed(self, text):
        """
        Internally implemented slot to react to when the text in the line edit has changed so that we can show or hide
        the clear button.

        :param text: A :class:`~PySide6.QtCore.QString` instance which represents the text in the line edit.
        """
        self.clear_button.setVisible(bool(text))

    def _on_clear_button_clicked(self):
        """
        Internally implemented slot to react to the clear button being clicked to clear the line edit.
        """
        self.clear()

    def _on_menu_action_triggered(self):
        """
        Internally implemented slot to react to the select of one of the search types in the menu. Once it has set the
        correct action on the button, and set the current search type (using the list of identifiers provided by the
        developer), the ``searchTypeChanged(int)`` signal is emitted with the identifier.
        """
        for action in self.menu_button.menu().actions():
            # Why is this needed?
            action.setChecked(False)
        self.set_current_search_type(self.sender().data())


class PathEdit(QtWidgets.QWidget):
    """
    The :class:`~openlp.core.widgets.edits.PathEdit` class subclasses QWidget to create a custom widget for use when
    a file or directory needs to be selected.
    """
    pathChanged = QtCore.Signal(Path)

    def __init__(self, parent=None, path_type=PathEditType.Files, default_path=None, dialog_caption=None,
                 show_revert=True):
        """
        Initialise the PathEdit widget

        :param QtWidget.QWidget | None: The parent of the widget. This is just passed to the super method.
        :param str dialog_caption: Used to customise the caption in the QFileDialog.
        :param Path default_path: The default path. This is set as the path when the revert
            button is clicked
        :param bool show_revert: Used to determine if the 'revert button' should be visible.
        :rtype: None
        """
        super().__init__(parent)
        self.default_path = default_path
        self.dialog_caption = dialog_caption
        self._path_type = path_type
        self._path = None
        self.filters = '{all_files} (*)'.format(all_files=UiStrings().AllFiles)
        self._setup(show_revert)

    def _setup(self, show_revert):
        """
        Set up the widget
        :param bool show_revert: Show or hide the revert button
        :rtype: None
        """
        widget_layout = QtWidgets.QHBoxLayout()
        widget_layout.setContentsMargins(0, 0, 0, 0)
        self.line_edit = QtWidgets.QLineEdit(self)
        widget_layout.addWidget(self.line_edit)
        self.browse_button = QtWidgets.QToolButton(self)
        self.browse_button.setIcon(UiIcons().open)
        widget_layout.addWidget(self.browse_button)
        self.revert_button = QtWidgets.QToolButton(self)
        self.revert_button.setIcon(UiIcons().undo)
        self.revert_button.setVisible(show_revert)
        widget_layout.addWidget(self.revert_button)
        self.setLayout(widget_layout)
        # Signals and Slots
        self.browse_button.clicked.connect(self.on_browse_button_clicked)
        self.revert_button.clicked.connect(self.on_revert_button_clicked)
        self.line_edit.editingFinished.connect(self.on_line_edit_editing_finished)
        self.update_button_tool_tips()

    @QtCore.Property(Path)
    def path(self):
        """
        A property getter method to return the selected path.

        :return: The selected path
        :rtype: Path
        """
        return self._path

    @path.setter
    def path(self, path):
        """
        A Property setter method to set the selected path

        :param Path path: The path to set the widget to
        :rtype: None
        """
        if path:
            self._path = Path(path)
            text = path_to_str(self._path)
            self.line_edit.setText(text)
            self.line_edit.setToolTip(text)

    @QtCore.Property(PathEditType)
    def path_type(self):
        """
        A property getter method to return the path_type. Path type allows you to sepecify if the user is restricted to
        selecting a file or directory.

        :return: The type selected
        :rtype: PathType
        """
        return self._path_type

    @path_type.setter
    def path_type(self, path_type):
        """
        A Property setter method to set the path type

        :param PathType path_type: The type of path to select
        :rtype: None
        """
        self._path_type = path_type
        self.update_button_tool_tips()

    def update_button_tool_tips(self):
        """
        Called to update the tooltips on the buttons. This is changing path types, and when the widget is initalised

        :rtype: None
        """
        if self._path_type == PathEditType.Directories:
            self.browse_button.setToolTip(translate('OpenLP.PathEdit', 'Browse for directory.'))
            self.revert_button.setToolTip(translate('OpenLP.PathEdit', 'Revert to default directory.'))
        else:
            self.browse_button.setToolTip(translate('OpenLP.PathEdit', 'Browse for file.'))
            self.revert_button.setToolTip(translate('OpenLP.PathEdit', 'Revert to default file.'))

    def on_browse_button_clicked(self):
        """
        A handler to handle a click on the browse button.

        Show the QFileDialog and process the input from the user

        :rtype: None
        """
        caption = self.dialog_caption
        path = None
        if self._path_type == PathEditType.Directories:
            if not caption:
                caption = translate('OpenLP.PathEdit', 'Select Directory')
            path = FileDialog.getExistingDirectory(self, caption, self._path, FileDialog.Option.ShowDirsOnly)
        elif self._path_type == PathEditType.Files:
            if not caption:
                caption = self.dialog_caption = translate('OpenLP.PathEdit', 'Select File')
            path, filter_used = FileDialog.getOpenFileName(self, caption, self._path, self.filters)
        if path:
            self.on_new_path(path)

    def on_revert_button_clicked(self):
        """
        A handler to handle a click on the revert button.

        Set the new path to the value of the default_path instance variable.

        :rtype: None
        """
        self.on_new_path(self.default_path)

    def on_line_edit_editing_finished(self):
        """
        A handler to handle when the line edit has finished being edited.

        :rtype: None
        """
        path = str_to_path(self.line_edit.text())
        self.on_new_path(path)

    def on_new_path(self, path):
        """
        A method called to validate and set a new path.

        Emits the pathChanged Signal

        :param Path path: The new path
        :rtype: None
        """
        if path and self._path != path:
            self.path = path
            self.pathChanged.emit(path)


class SpellTextEdit(QtWidgets.QPlainTextEdit):
    """
    Spell checking widget based on QPlanTextEdit.

    Based on code from http://john.nachtimwald.com/2009/08/22/qplaintextedit-with-in-line-spell-check
    """
    def __init__(self, parent=None, formatting_tags_allowed=True):
        """
        Constructor.
        """
        global ENCHANT_AVAILABLE
        super(SpellTextEdit, self).__init__(parent)
        self.formatting_tags_allowed = formatting_tags_allowed
        # Default dictionary based on the current locale.
        if ENCHANT_AVAILABLE:
            try:
                self.dictionary = enchant.Dict()
                self.highlighter = Highlighter(self.document())
                self.highlighter.spelling_dictionary = self.dictionary
            except (Error, DictNotFoundError):
                ENCHANT_AVAILABLE = False
                log.debug('Could not load default dictionary')

    def mousePressEvent(self, event):
        """
        Handle mouse clicks within the text edit region.
        """
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            # Rewrite the mouse event to a left button event so the cursor is moved to the location of the pointer.
            event = QtGui.QMouseEvent(QtCore.QEvent.Type.MouseButtonPress,
                                      event.pos(),
                                      QtCore.Qt.MouseButton.LeftButton,
                                      QtCore.Qt.MouseButton.LeftButton,
                                      QtCore.Qt.KeyboardModifier.NoModifier)
        QtWidgets.QPlainTextEdit.mousePressEvent(self, event)

    def contextMenuEvent(self, event):
        """
        Provide the context menu for the text edit region.
        """
        popup_menu = self.createStandardContextMenu()
        # Select the word under the cursor.
        cursor = self.textCursor()
        # only select text if not already selected
        if not cursor.hasSelection():
            cursor.select(QtGui.QTextCursor.SelectionType.WordUnderCursor)
        self.setTextCursor(cursor)
        # Add menu with available languages.
        if ENCHANT_AVAILABLE:
            lang_menu = QtWidgets.QMenu(translate('OpenLP.SpellTextEdit', 'Language:'))
            for lang in enchant.list_languages():
                action = create_action(lang_menu, lang, text=lang, checked=lang == self.dictionary.tag)
                lang_menu.addAction(action)
            popup_menu.insertSeparator(popup_menu.actions()[0])
            popup_menu.insertMenu(popup_menu.actions()[0], lang_menu)
            lang_menu.triggered.connect(self.set_language)
        # Check if the selected word is misspelled and offer spelling suggestions if it is.
        if ENCHANT_AVAILABLE and self.textCursor().hasSelection():
            text = self.textCursor().selectedText()
            if not self.dictionary.check(text):
                spell_menu = QtWidgets.QMenu(translate('OpenLP.SpellTextEdit', 'Spelling Suggestions'))
                for word in self.dictionary.suggest(text):
                    action = SpellAction(word, spell_menu)
                    action.correct.connect(self.correct_word)
                    spell_menu.addAction(action)
                # Only add the spelling suggests to the menu if there are suggestions.
                if spell_menu.actions():
                    popup_menu.insertMenu(popup_menu.actions()[0], spell_menu)
        tag_menu = QtWidgets.QMenu(translate('OpenLP.SpellTextEdit', 'Formatting Tags'))
        if self.formatting_tags_allowed:
            for html in FormattingTags.get_html_tags():
                action = SpellAction(html['desc'], tag_menu)
                action.correct.connect(self.html_tag)
                tag_menu.addAction(action)
            popup_menu.insertSeparator(popup_menu.actions()[0])
            popup_menu.insertMenu(popup_menu.actions()[0], tag_menu)
        popup_menu.exec(event.globalPos())

    def set_language(self, action):
        """
        Changes the language for this spelltextedit.

        :param action: The action.
        """
        self.dictionary = enchant.Dict(action.text())
        self.highlighter.spelling_dictionary = self.dictionary
        self.highlighter.highlightBlock(self.toPlainText())
        self.highlighter.rehighlight()

    def correct_word(self, word):
        """
        Replaces the selected text with word.
        """
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(word)
        cursor.endEditBlock()

    def html_tag(self, tag):
        """
        Replaces the selected text with word.
        """
        tag = tag.replace('&', '')
        for html in FormattingTags.get_html_tags():
            if tag == html['desc']:
                cursor = self.textCursor()
                if self.textCursor().hasSelection():
                    text = cursor.selectedText()
                    cursor.beginEditBlock()
                    cursor.removeSelectedText()
                    cursor.insertText(html['start tag'])
                    cursor.insertText(text)
                    cursor.insertText(html['end tag'])
                    cursor.endEditBlock()
                else:
                    cursor = self.textCursor()
                    cursor.insertText(html['start tag'])
                    cursor.insertText(html['end tag'])

    def insertFromMimeData(self, source):
        """
        Reimplement `insertFromMimeData` so that we can remove any control characters

        :param QtCore.QMimeData source: The mime data to insert
        :rtype: None
        """
        self.insertPlainText(CONTROL_CHARS.sub('', source.text()))


class Highlighter(QtGui.QSyntaxHighlighter):
    """
    Provides a text highlighter for pointing out spelling errors in text.
    """
    WORDS = r'(?i)[\w\']+'

    def __init__(self, *args):
        """
        Constructor
        """
        super(Highlighter, self).__init__(*args)
        self.spelling_dictionary = None

    def highlightBlock(self, text):
        """
        Highlight mis spelt words in a block of text.

        Note, this is a Qt hook.
        """
        if not self.spelling_dictionary:
            return
        text = str(text)
        char_format = QtGui.QTextCharFormat()
        char_format.setUnderlineColor(QtCore.Qt.GlobalColor.red)
        char_format.setUnderlineStyle(QtGui.QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
        for word_object in re.finditer(self.WORDS, text):
            if not self.spelling_dictionary.check(word_object.group()):
                self.setFormat(word_object.start(), word_object.end() - word_object.start(), char_format)


class SpellAction(QtGui.QAction):
    """
    A special QAction that returns the text in a signal.
    """
    correct = QtCore.Signal(str)

    def __init__(self, *args):
        """
        Constructor
        """
        super(SpellAction, self).__init__(*args)
        self.triggered.connect(lambda x: self.correct.emit(self.text()))


class HistoryComboBox(QtWidgets.QComboBox):
    """
    The :class:`~openlp.core.common.historycombobox.HistoryComboBox` widget emulates the QLineEdit ``returnPressed``
    signal for when the :kbd:`Enter` or :kbd:`Return` keys are pressed, and saves anything that is typed into the edit
    box into its list.
    """
    returnPressed = QtCore.Signal()

    def __init__(self, parent=None):
        """
        Initialise the combo box, setting duplicates to False and the insert policy to insert items at the top.

        :param parent: The parent widget
        """
        super().__init__(parent)
        self.setDuplicatesEnabled(False)
        self.setEditable(True)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        self.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.InsertAtTop)

    def keyPressEvent(self, event):
        """
        Override the inherited keyPressEvent method to emit the ``returnPressed`` signal and to save the current text to
        the dropdown list.

        :param event: The keyboard event
        """
        # Handle Enter and Return ourselves
        if event.key() == QtCore.Qt.Key.Key_Enter or event.key() == QtCore.Qt.Key.Key_Return:
            # Emit the returnPressed signal
            self.returnPressed.emit()
            # Save the current text to the dropdown list
            if self.currentText() and self.findText(self.currentText()) == -1:
                self.insertItem(0, self.currentText())
        # Let the parent handle any keypress events
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        """
        Override the inherited focusOutEvent to save the current text to the dropdown list.

        :param event: The focus event
        """
        # Save the current text to the dropdown list
        if self.currentText() and self.findText(self.currentText()) == -1:
            self.insertItem(0, self.currentText())
        # Let the parent handle any keypress events
        super().focusOutEvent(event)

    def getItems(self):
        """
        Get all the items from the history

        :return: A list of strings
        """
        return [self.itemText(i) for i in range(self.count())]
