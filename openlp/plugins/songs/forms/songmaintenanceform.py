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
import logging

from PySide6 import QtCore, QtWidgets
from sqlalchemy.sql import and_

from openlp.core.common.i18n import UiStrings, get_natural_key, translate
from openlp.core.common.mixins import RegistryProperties
from openlp.core.common.registry import Registry
from openlp.core.lib.ui import critical_error_message_box
from openlp.plugins.songs.forms.authorsform import AuthorsForm
from openlp.plugins.songs.forms.songbookform import SongBookForm
from openlp.plugins.songs.forms.topicsform import TopicsForm
from openlp.plugins.songs.lib.db import Author, AuthorSong, SongBook, Song, Topic, SongBookEntry

from .songmaintenancedialog import Ui_SongMaintenanceDialog


log = logging.getLogger(__name__)


class SongMaintenanceForm(QtWidgets.QDialog, Ui_SongMaintenanceDialog, RegistryProperties):
    """
    Class documentation goes here.
    """
    def __init__(self, manager, parent=None):
        """
        Constructor
        """
        super(SongMaintenanceForm, self).__init__(parent,
                                                  QtCore.Qt.WindowType.WindowSystemMenuHint |
                                                  QtCore.Qt.WindowType.WindowTitleHint |
                                                  QtCore.Qt.WindowType.WindowCloseButtonHint)
        self.setup_ui(self)
        self.manager = manager
        self.author_form = AuthorsForm(self)
        self.topic_form = TopicsForm(self)
        self.song_book_form = SongBookForm(self)
        # Disable all edit and delete buttons, as there is no row selected.
        self.delete_author_button.setEnabled(False)
        self.edit_author_button.setEnabled(False)
        self.delete_topic_button.setEnabled(False)
        self.edit_topic_button.setEnabled(False)
        self.delete_book_button.setEnabled(False)
        self.edit_book_button.setEnabled(False)
        # Signals
        self.add_author_button.clicked.connect(self.on_add_author_button_clicked)
        self.add_topic_button.clicked.connect(self.on_add_topic_button_clicked)
        self.add_book_button.clicked.connect(self.on_add_book_button_clicked)
        self.edit_author_button.clicked.connect(self.on_edit_author_button_clicked)
        self.edit_topic_button.clicked.connect(self.on_edit_topic_button_clicked)
        self.edit_book_button.clicked.connect(self.on_edit_book_button_clicked)
        self.delete_author_button.clicked.connect(self.on_delete_author_button_clicked)
        self.delete_topic_button.clicked.connect(self.on_delete_topic_button_clicked)
        self.delete_book_button.clicked.connect(self.on_delete_book_button_clicked)
        self.authors_list_widget.currentRowChanged.connect(self.on_authors_list_row_changed)
        self.topics_list_widget.currentRowChanged.connect(self.on_topics_list_row_changed)
        self.song_books_list_widget.currentRowChanged.connect(self.on_song_books_list_row_changed)

    def exec(self, from_song_edit=False):
        """
        Show the dialog.


        :param from_song_edit: Indicates if the maintenance dialog has been opened from song edit
            or from the media manager. Defaults to **False**.
        """
        self.from_song_edit = from_song_edit
        self.type_list_widget.setCurrentRow(0)
        self.reset_authors()
        self.reset_topics()
        self.reset_song_books()
        self.type_list_widget.setFocus()
        return QtWidgets.QDialog.exec(self)

    def _get_current_item_id(self, list_widget):
        """
        Get the ID of the currently selected item.

        :param list_widget: The list widget to examine.
        """
        item = list_widget.currentItem()
        if item:
            item_id = (item.data(QtCore.Qt.ItemDataRole.UserRole))
            return item_id
        else:
            return -1

    def _delete_item(self, item_class, list_widget, reset_func, dlg_title, del_text, err_text):
        """
        Delete an item.
        """
        item_id = self._get_current_item_id(list_widget)
        if item_id == -1:
            critical_error_message_box(dlg_title, UiStrings().NISs)
            return
        item = self.manager.get_object(item_class, item_id)
        if item:
            song_titles = [song.title for song in item.songs]
            if song_titles:
                critical_error_message_box(dlg_title, err_text + '\n\n' + '\n'.join(song_titles))
            elif (critical_error_message_box(dlg_title, del_text, self, True) ==
                  QtWidgets.QMessageBox.StandardButton.Yes):
                self.manager.delete_object(item_class, item.id)
                reset_func()
        else:
            critical_error_message_box(dlg_title, err_text)

    def reset_authors(self):
        """
        Reloads the Authors list.
        """
        def get_author_key(author):
            """Get the key to sort by"""
            return get_natural_key(author.display_name)

        self.authors_list_widget.clear()
        authors = self.manager.get_all_objects(Author)
        authors.sort(key=get_author_key)
        for author in authors:
            if author.display_name:
                author_name = QtWidgets.QListWidgetItem(author.display_name)
            else:
                author_name = QtWidgets.QListWidgetItem(' '.join([author.first_name, author.last_name]))
            author_name.setData(QtCore.Qt.ItemDataRole.UserRole, author.id)
            self.authors_list_widget.addItem(author_name)

    def reset_topics(self):
        """
        Reloads the Topics list.
        """
        def get_topic_key(topic):
            """Get the key to sort by"""
            return get_natural_key(topic.name)

        self.topics_list_widget.clear()
        topics = self.manager.get_all_objects(Topic)
        topics.sort(key=get_topic_key)
        for topic in topics:
            topic_name = QtWidgets.QListWidgetItem(topic.name)
            topic_name.setData(QtCore.Qt.ItemDataRole.UserRole, topic.id)
            self.topics_list_widget.addItem(topic_name)

    def reset_song_books(self):
        """
        Reloads the Books list.
        """
        def get_book_key(book):
            """Get the key to sort by"""
            return get_natural_key(book.name)

        self.song_books_list_widget.clear()
        books = self.manager.get_all_objects(SongBook)
        books.sort(key=get_book_key)
        for book in books:
            book_name = QtWidgets.QListWidgetItem('{name} ({publisher})'.format(name=book.name,
                                                                                publisher=book.publisher))
            book_name.setData(QtCore.Qt.ItemDataRole.UserRole, book.id)
            self.song_books_list_widget.addItem(book_name)

    def check_author_exists(self, new_author, edit=False):
        """
        Returns *False* if the given Author already exists, otherwise *True*.

        :param new_author: The new Author.
        :param edit: Are we editing the song?
        """
        authors = self.manager.get_all_objects(
            Author,
            and_(
                Author.first_name == new_author.first_name,
                Author.last_name == new_author.last_name,
                Author.display_name == new_author.display_name
            )
        )
        return self._check_object_exists(authors, new_author, edit)

    def check_topic_exists(self, new_topic, edit=False):
        """
        Returns *False* if the given Topic already exists, otherwise *True*.

        :param new_topic: The new Topic.
        :param edit: Are we editing the song?
        """
        topics = self.manager.get_all_objects(Topic, Topic.name == new_topic.name)
        return self._check_object_exists(topics, new_topic, edit)

    def check_song_book_exists(self, new_book, edit=False):
        """
        Returns *False* if the given Topic already exists, otherwise *True*.

        :param new_book: The new Book.
        :param edit: Are we editing the song?
        """
        books = self.manager.get_all_objects(
            SongBook, and_(SongBook.name == new_book.name, SongBook.publisher == new_book.publisher))
        return self._check_object_exists(books, new_book, edit)

    def _check_object_exists(self, existing_objects, new_object, edit):
        """
        Utility method to check for an existing object.

        :param existing_objects: The objects reference
        :param new_object: An individual object
        :param edit: If we edit an item, this should be *True*.
        """
        if existing_objects:
            # If we edit an existing object, we need to make sure that we do
            # not return False when nothing has changed.
            if edit:
                for existing_object in existing_objects:
                    if existing_object.id != new_object.id:
                        return False
                return True
            else:
                return False
        else:
            return True

    def on_add_author_button_clicked(self):
        """
        Add an author to the list.
        """
        self.author_form.auto_display_name = True
        if self.author_form.exec():
            author = Author(
                first_name=self.author_form.first_name,
                last_name=self.author_form.last_name,
                display_name=self.author_form.display_name
            )
            if self.check_author_exists(author):
                if self.manager.save_object(author):
                    self.reset_authors()
                else:
                    critical_error_message_box(
                        message=translate('SongsPlugin.SongMaintenanceForm', 'Could not add your author.'))
            else:
                critical_error_message_box(
                    message=translate('SongsPlugin.SongMaintenanceForm', 'This author already exists.'))

    def on_add_topic_button_clicked(self):
        """
        Add a topic to the list.
        """
        if self.topic_form.exec():
            topic = Topic(name=self.topic_form.name)
            if self.check_topic_exists(topic):
                if self.manager.save_object(topic):
                    self.reset_topics()
                else:
                    critical_error_message_box(
                        message=translate('SongsPlugin.SongMaintenanceForm', 'Could not add your topic.'))
            else:
                critical_error_message_box(
                    message=translate('SongsPlugin.SongMaintenanceForm', 'This topic already exists.'))

    def on_add_book_button_clicked(self):
        """
        Add a book to the list.
        """
        if self.song_book_form.exec():
            book = SongBook(name=self.song_book_form.name_edit.text(),
                            publisher=self.song_book_form.publisher_edit.text())
            if self.check_song_book_exists(book):
                if self.manager.save_object(book):
                    self.reset_song_books()
                else:
                    critical_error_message_box(
                        message=translate('SongsPlugin.SongMaintenanceForm', 'Could not add your book.'))
            else:
                critical_error_message_box(
                    message=translate('SongsPlugin.SongMaintenanceForm', 'This book already exists.'))

    def on_edit_author_button_clicked(self):
        """
        Edit an author.
        """
        author_id = self._get_current_item_id(self.authors_list_widget)
        if author_id == -1:
            return
        author = self.manager.get_object(Author, author_id)
        self.author_form.auto_display_name = False
        self.author_form.first_name_edit.setText(author.first_name)
        self.author_form.last_name_edit.setText(author.last_name)
        self.author_form.display_edit.setText(author.display_name)
        # Save the author's first and last name as well as the display name
        # for the case that they have to be restored.
        temp_first_name = author.first_name
        temp_last_name = author.last_name
        temp_display_name = author.display_name
        if self.author_form.exec(False):
            author.first_name = self.author_form.first_name_edit.text()
            author.last_name = self.author_form.last_name_edit.text()
            author.display_name = self.author_form.display_edit.text()
            if self.check_author_exists(author, True):
                if self.manager.save_object(author):
                    for song in author.songs:
                        song.init_on_load(force_song_detail_recalculation=True)
                    self.reset_authors()
                    if not self.from_song_edit:
                        Registry().execute('songs_load_list')
                else:
                    critical_error_message_box(
                        message=translate('SongsPlugin.SongMaintenanceForm', 'Could not save your changes.'))
            elif critical_error_message_box(
                    message=translate(
                        'SongsPlugin.SongMaintenanceForm',
                        'The author {original} already exists. Would you like to make songs with author {new} use the '
                        'existing author {original}?').format(original=author.display_name, new=temp_display_name),
                    parent=self, question=True) == QtWidgets.QMessageBox.StandardButton.Yes:
                self._merge_objects(author, self.merge_authors, self.reset_authors)
            else:
                # We restore the author's old first and last name as well as
                # his display name.
                author.first_name = temp_first_name
                author.last_name = temp_last_name
                author.display_name = temp_display_name
                critical_error_message_box(
                    message=translate('SongsPlugin.SongMaintenanceForm',
                                      'Could not save your modified author, because the author already exists.'))

    def on_edit_topic_button_clicked(self):
        """
        Edit a topic.
        """
        topic_id = self._get_current_item_id(self.topics_list_widget)
        if topic_id == -1:
            return
        topic = self.manager.get_object(Topic, topic_id)
        self.topic_form.name = topic.name
        # Save the topic's name for the case that he has to be restored.
        temp_name = topic.name
        if self.topic_form.exec(False):
            topic.name = self.topic_form.name_edit.text()
            if self.check_topic_exists(topic, True):
                if self.manager.save_object(topic):
                    self.reset_topics()
                else:
                    critical_error_message_box(
                        message=translate('SongsPlugin.SongMaintenanceForm', 'Could not save your changes.'))
            elif critical_error_message_box(
                    message=translate('SongsPlugin.SongMaintenanceForm',
                                      'The topic {original} already exists. Would you like to make songs with '
                                      'topic {new} use the existing topic {original}?').format(original=topic.name,
                                                                                               new=temp_name),
                    parent=self, question=True) == QtWidgets.QMessageBox.StandardButton.Yes:
                self._merge_objects(topic, self.merge_topics, self.reset_topics)
            else:
                # We restore the topics's old name.
                topic.name = temp_name
                critical_error_message_box(
                    message=translate('SongsPlugin.SongMaintenanceForm',
                                      'Could not save your modified topic, because it already exists.'))

    def on_edit_book_button_clicked(self):
        """
        Edit a book.
        """
        book_id = self._get_current_item_id(self.song_books_list_widget)
        if book_id == -1:
            return
        book = self.manager.get_object(SongBook, book_id)
        if book.publisher is None:
            book.publisher = ''
        self.song_book_form.name_edit.setText(book.name)
        self.song_book_form.publisher_edit.setText(book.publisher)
        # Save the book's name and publisher for the case that they have to
        # be restored.
        temp_name = book.name
        temp_publisher = book.publisher
        if self.song_book_form.exec(False):
            book.name = self.song_book_form.name_edit.text()
            book.publisher = self.song_book_form.publisher_edit.text()
            if self.check_song_book_exists(book, True):
                if self.manager.save_object(book):
                    self.reset_song_books()
                else:
                    critical_error_message_box(
                        message=translate('SongsPlugin.SongMaintenanceForm', 'Could not save your changes.'))
            elif critical_error_message_box(
                    message=translate('SongsPlugin.SongMaintenanceForm',
                                      'The book {original} already exists. Would you like to make songs with '
                                      'book {new} use the existing book {original}?').format(original=book.name,
                                                                                             new=temp_name),
                    parent=self, question=True) == QtWidgets.QMessageBox.StandardButton.Yes:
                self._merge_objects(book, self.merge_song_books, self.reset_song_books)
            else:
                # We restore the book's old name and publisher.
                book.name = temp_name
                book.publisher = temp_publisher

    def _merge_objects(self, db_object, merge, reset):
        """
        Utility method to merge two objects to leave one in the database.
        """
        self.application.set_busy_cursor()
        merge(db_object)
        reset()
        if not self.from_song_edit:
            Registry().execute('songs_load_list')
        self.application.set_normal_cursor()

    def merge_authors(self, old_author):
        """
        Merges two authors into one author.

        :param old_author: The object, which was edited, that will be deleted
        """
        # Find the duplicate.
        existing_author = self.manager.get_object_filtered(
            Author,
            and_(
                Author.first_name == old_author.first_name,
                Author.last_name == old_author.last_name,
                Author.display_name == old_author.display_name,
                Author.id != old_author.id
            )
        )
        # Find the songs, which have the old_author as author.
        songs = self.manager.get_all_objects(
            Song,
            and_(
                Song.id == AuthorSong.song_id,
                AuthorSong.author_id == old_author.id
            )
        )
        for song in songs:
            for author_song in song.authors_songs:
                song.add_author(existing_author, author_song.author_type)
                song.remove_author(old_author, author_song.author_type)
            song.init_on_load(force_song_detail_recalculation=True)
            self.manager.save_object(song)
        self.manager.delete_object(Author, old_author.id)

    def merge_topics(self, old_topic):
        """
        Merges two topics into one topic.

        :param old_topic: The object, which was edited, that will be deleted
        """
        # Find the duplicate.
        existing_topic = self.manager.get_object_filtered(
            Topic, and_(Topic.name == old_topic.name, Topic.id != old_topic.id)
        )
        # Find the songs, which have the old_topic as topic.
        songs = self.manager.get_all_objects(Song, Song.topics.contains(old_topic))
        for song in songs:
            # We check if the song has already existing_topic as topic. If that
            # is not the case we add it.
            if existing_topic not in song.topics:
                song.topics.append(existing_topic)
            song.topics.remove(old_topic)
            self.manager.save_object(song)
        self.manager.delete_object(Topic, old_topic.id)

    def merge_song_books(self, old_song_book):
        """
        Merges two books into one book.

        ``old_song_book``
            The object, which was edited, that will be deleted
        """
        # Find the duplicate.
        existing_book = self.manager.get_object_filtered(
            SongBook,
            and_(
                SongBook.name == old_song_book.name,
                SongBook.publisher == old_song_book.publisher,
                SongBook.id != old_song_book.id
            )
        )
        if existing_book is None:
            return False
        # Find the songs which have the old_song_book as book, via matching entries in the songs_songbooks table
        songbook_entries = self.manager.get_all_objects(SongBookEntry, SongBookEntry.songbook_id == old_song_book.id)
        affected_songs = []
        for songbook_entry in songbook_entries:
            affected_songs.append(songbook_entry.song_id)
        for song_id in affected_songs:
            song = self.manager.get_object(Song, song_id)
            # Go through the song's song/songbook link records to look for the link to the old songbook.
            # Store the song number in that book so we can apply it in the link record to the existing songbook.
            old_book_song_number = ''
            for index, record in enumerate(song.songbook_entries):
                if record.songbook_id == old_song_book.id:
                    old_book_song_number = record.entry
                    break
            # Look through the same link records to see if there's a link to the duplicate (existing) songbook
            # If so, transfer the song number in 'entry' field (if appropriate) ...
            found = False
            for record in song.songbook_entries:
                if record.songbook_id == existing_book.id:
                    if not record.entry and old_book_song_number:
                        record.entry = old_book_song_number
                    found = True
                    break
            # ... otherwise create a new link record
            if not found:
                new_songbook_entry = SongBookEntry()
                new_songbook_entry.songbook_id = existing_book.id
                new_songbook_entry.song_id = song.id
                new_songbook_entry.entry = old_book_song_number
                song.songbook_entries.append(new_songbook_entry)
            self.manager.save_object(song)
            self.manager.delete_object(SongBookEntry, (old_song_book.id, song_id, old_book_song_number))

        self.manager.delete_object(SongBook, old_song_book.id)

    def on_delete_author_button_clicked(self):
        """
        Delete the author if the author is not attached to any songs.
        """
        self._delete_item(Author, self.authors_list_widget, self.reset_authors,
                          translate('SongsPlugin.SongMaintenanceForm', 'Delete Author'),
                          translate('SongsPlugin.SongMaintenanceForm',
                                    'Are you sure you want to delete the selected author?'),
                          translate('SongsPlugin.SongMaintenanceForm',
                                    'This author cannot be deleted, they are currently assigned to at least one song'
                                    '.'))

    def on_delete_topic_button_clicked(self):
        """
        Delete the Book if the Book is not attached to any songs.
        """
        self._delete_item(Topic, self.topics_list_widget, self.reset_topics,
                          translate('SongsPlugin.SongMaintenanceForm', 'Delete Topic'),
                          translate('SongsPlugin.SongMaintenanceForm',
                                    'Are you sure you want to delete the selected topic?'),
                          translate('SongsPlugin.SongMaintenanceForm',
                                    'This topic cannot be deleted, it is currently assigned to at least one song.'))

    def on_delete_book_button_clicked(self):
        """
        Delete the Book if the Book is not attached to any songs.
        """
        self._delete_item(SongBook, self.song_books_list_widget, self.reset_song_books,
                          translate('SongsPlugin.SongMaintenanceForm', 'Delete Book'),
                          translate('SongsPlugin.SongMaintenanceForm',
                                    'Are you sure you want to delete the selected book?'),
                          translate('SongsPlugin.SongMaintenanceForm',
                                    'This book cannot be deleted, it is currently assigned to at least one song.'))

    def on_authors_list_row_changed(self, row):
        """
        Called when the *authors_list_widget*'s current row has changed.
        """
        self._row_change(row, self.edit_author_button, self.delete_author_button)

    def on_topics_list_row_changed(self, row):
        """
        Called when the *topics_list_widget*'s current row has changed.
        """
        self._row_change(row, self.edit_topic_button, self.delete_topic_button)

    def on_song_books_list_row_changed(self, row):
        """
        Called when the *song_books_list_widget*'s current row has changed.
        """
        self._row_change(row, self.edit_book_button, self.delete_book_button)

    def _row_change(self, row, edit_button, delete_button):
        """
        Utility method to toggle if buttons are enabled.

        ``row``
            The current row. If there is no current row, the value is -1.
        """
        if row == -1:
            delete_button.setEnabled(False)
            edit_button.setEnabled(False)
        else:
            delete_button.setEnabled(True)
            edit_button.setEnabled(True)
