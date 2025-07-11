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
Functional tests to test the Http Server Class.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

from openlp.core.api.http.server import HttpServer, HttpWorker
from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings


@patch('openlp.core.api.http.server.HttpWorker')
@patch('openlp.core.api.http.server.run_thread')
@patch('openlp.core.api.deploy.AppLocation.get_section_data_path')
def test_server_start(mocked_get_section_data_path: MagicMock, mocked_run_thread: MagicMock,
                      MockHttpWorker: MagicMock, registry: Registry):
    """
    Test the starting of the Waitress Server with the disable flag set off
    """
    # GIVEN: A new httpserver and mocked get_section_data_path
    mocked_get_section_data_path.return_value = Path('.')
    # WHEN: I start the server
    registry.set_flag('no_web_server', False)
    server = HttpServer()
    server.bootstrap_post_set_up()

    # THEN: the api environment should have been created
    assert mocked_run_thread.call_count == 1, 'The qthread should have been called once'
    assert MockHttpWorker.call_count == 1, 'The http thread should have been called once'


@patch('openlp.core.api.http.server.HttpWorker')
@patch('openlp.core.api.http.server.run_thread')
@patch('openlp.core.api.deploy.AppLocation.get_section_data_path')
def test_server_start_not_required(mocked_get_section_data_path: MagicMock, mocked_run_thread: MagicMock,
                                   MockHttpWorker: MagicMock, registry: Registry):
    """
    Test the starting of the Waitress Server with the disable flag set off
    """
    # GIVEN: A new httpserver and mocked get_section_data_path
    mocked_get_section_data_path.return_value = Path('.')

    # WHEN: I start the server
    registry.set_flag('no_web_server', True)
    server = HttpServer()
    server.bootstrap_post_set_up()

    # THEN: the api environment should have been created
    assert mocked_run_thread.call_count == 0, 'The qthread should not have have been called'
    assert MockHttpWorker.call_count == 0, 'The http thread should not have been called'


@patch('openlp.core.api.http.server.application')
@patch('openlp.core.api.http.server.create_server')
@patch('openlp.core.api.http.server.AppLocation.get_section_data_path')
def test_worker_start(mocked_get_path: MagicMock, mocked_create_server: MagicMock,
                      mocked_application: MagicMock, registry: Registry, settings: Settings):
    """Test starting the HTTP worker"""
    # GIVEN: An HttpWorker object and some mocks
    settings.setValue('api/ip address', '127.0.0.1')
    settings.setValue('api/port', '32565')
    mocked_get_path.return_value = Path('remotes')
    mocked_server = MagicMock()
    mocked_create_server.return_value = mocked_server

    # WHEN: The start() method is called
    worker = HttpWorker(None)
    with patch.object(worker, 'quit') as mocked_quit:
        worker.start()

    # THEN: The right calls should have been made
    assert mocked_application.static_folder == str(Path('remotes') / 'static')
    mocked_create_server.assert_called_once_with(mocked_application, host='127.0.0.1', port=32565)
    assert worker.server is mocked_server
    mocked_server.run.assert_called_once_with()
    mocked_quit.emit.assert_called_once_with()


def test_worker_stop_with_map():
    """Test that calling stop() on the worker does the right things (with .map)"""
    # GIVEN: A worker with some mocks
    worker = HttpWorker(None)
    worker.server = MagicMock()
    mock_channel_1 = MagicMock()
    del mock_channel_1.close
    mock_channel_2 = MagicMock()
    worker.server.map.values.return_value = [mock_channel_1, mock_channel_2]
    del worker.server._map

    # WHEN: stop() is called
    worker.stop()

    # THEN: The channels should have been closed
    worker.server.map.values.assert_called_once_with()
    mock_channel_2.close.assert_called_once_with()


def test_worker_stop_with__map():
    """Test that calling stop() on the worker does the right things (with ._map)"""
    # GIVEN: A worker with some mocks
    worker = HttpWorker(None)
    worker.server = MagicMock()
    mock_channel_1 = MagicMock()
    del mock_channel_1.close
    mock_channel_2 = MagicMock()
    worker.server._map.values.return_value = [mock_channel_1, mock_channel_2]
    del worker.server.map

    # WHEN: stop() is called
    worker.stop()

    # THEN: The channels should have been closed
    worker.server._map.values.assert_called_once_with()
    mock_channel_2.close.assert_called_once_with()
