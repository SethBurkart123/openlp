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
This module contains tests for the PdfController
"""
import pytest
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from unittest.mock import MagicMock

from PySide6 import QtCore, QtGui

from openlp.core.display.screens import ScreenList
from openlp.plugins.presentations.lib.pdfcontroller import PdfController, PdfDocument
from tests.utils.constants import RESOURCE_PATH


@pytest.fixture()
def pdf_env(settings, mock_plugin, mocked_qapp):
    temp_folder_path = Path(mkdtemp())
    thumbnail_folder_path = Path(mkdtemp())
    mocked_screen = MagicMock()
    mocked_screen.geometry.return_value = QtCore.QRect(0, 0, 1024, 768)
    mocked_qapp.screens.return_value = [mocked_screen]
    mocked_qapp.primaryScreen = MagicMock()
    mocked_qapp.primaryScreen.return_value = mocked_screen
    ScreenList.create(mocked_qapp)
    yield mock_plugin, temp_folder_path, thumbnail_folder_path
    rmtree(thumbnail_folder_path)
    rmtree(temp_folder_path)


def test_constructor(settings, mock_plugin):
    """
    Test the Constructor from the PdfController
    """
    # GIVEN: No presentation controller
    controller = None

    # WHEN: The presentation controller object is created
    controller = PdfController(plugin=mock_plugin)

    # THEN: The name of the presentation controller should be correct
    assert 'Pdf' == controller.name, 'The name of the presentation controller should be correct'


def test_load_pdf(pdf_env):
    """
    Test loading a Pdf using the PdfController
    """
    # GIVEN: A Pdf-file
    test_file_path = RESOURCE_PATH / 'presentations' / 'pdf_test1.pdf'

    # WHEN: The Pdf is loaded
    mock_plugin = pdf_env[0]
    temp_folder_path = pdf_env[1]
    thumbnail_folder_path = pdf_env[2]
    controller = PdfController(plugin=mock_plugin)
    controller.temp_folder = temp_folder_path
    controller.thumbnail_folder = thumbnail_folder_path
    document = PdfDocument(controller, test_file_path)
    loaded = document.load_presentation()

    # THEN: The load should succeed and we should be able to get a pagecount
    assert loaded is True, 'The loading of the PDF should succeed.'
    assert 3 == document.get_slide_count(), 'The pagecount of the PDF should be 3.'


def test_load_pdf_pictures(pdf_env):
    """
    Test loading a Pdf and check the generated pictures' size
    """
    # GIVEN: A Pdf-file
    test_file_path = RESOURCE_PATH / 'presentations' / 'pdf_test1.pdf'

    # WHEN: The Pdf is loaded
    mock_plugin = pdf_env[0]
    temp_folder_path = pdf_env[1]
    thumbnail_folder_path = pdf_env[2]
    controller = PdfController(plugin=mock_plugin)
    controller.temp_folder = temp_folder_path
    controller.thumbnail_folder = thumbnail_folder_path
    document = PdfDocument(controller, test_file_path)
    loaded = document.load_presentation()

    # THEN: The load should succeed and pictures should be created and have been scaled to fit the screen
    assert loaded is True, 'The loading of the PDF should succeed.'
    image = QtGui.QImage(document.image_files[0])
    # Calculate the width of the PDF based on the aspect ratio of the PDF
    height = 768
    width = int(round(height * 0.70572917, 0))
    assert image.height() == height, 'The height should be {height}'.format(height=height)
    assert image.width() == width, 'The width should be {width}'.format(width=width)
