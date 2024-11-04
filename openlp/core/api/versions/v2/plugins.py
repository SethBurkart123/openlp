# -*- coding: utf-8 -*-
# vim: autoindent shiftwidth=4 expandtab textwidth=120 tabstop=4 softtabstop=4

##########################################################################
# OpenLP - Open Source Lyrics Projection                                 #
# ---------------------------------------------------------------------- #
# Copyright (c) 2008-2024 OpenLP Developers                              #
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
import json
import re

from flask import abort, request, Blueprint, jsonify, Response
from PyQt5 import QtCore

from openlp.core.api.lib import login_required, extract_request, old_success_response, old_auth
from openlp.core.lib.plugin import PluginStatus
from openlp.core.common.json import OpenLPJSONEncoder
from openlp.core.common.registry import Registry
from openlp.plugins.songs.lib import transpose_lyrics

log = logging.getLogger(__name__)


plugins = Blueprint('v2-plugins', __name__)
alert_1_views = Blueprint('v1-alert-plugin', __name__)
alert_2_views = Blueprint('v2-alert-plugin', __name__)


def search(plugin_name, text):
    plugin = Registry().get('plugin_manager').get_plugin_by_name(plugin_name)
    if plugin.status == PluginStatus.Active and plugin.media_item and plugin.media_item.has_search:
        if hasattr(plugin.media_item.search, '__pyqtSignature__'):
            # If this method has a signature, it means that it should be called from the parent thread
            results = plugin.media_item.staticMetaObject.invokeMethod(
                plugin.media_item, 'search', QtCore.Qt.ConnectionType.DirectConnection,
                QtCore.Q_RETURN_ARG(list), QtCore.Q_ARG(str, text), QtCore.Q_ARG(bool, False))
        else:
            # Fall back to original behaviour
            results = plugin.media_item.search(text, False)
        return results
    return None


def live(plugin_name, id):
    plugin = Registry().get('plugin_manager').get_plugin_by_name(plugin_name)
    if plugin.status == PluginStatus.Active and plugin.media_item:
        getattr(plugin.media_item, '{action}_go_live'.format(action=plugin_name)).emit([id, True])


def add(plugin_name, id):
    plugin = Registry().get('plugin_manager').get_plugin_by_name(plugin_name)
    if plugin.status == PluginStatus.Active and plugin.media_item:
        item_id = plugin.media_item.create_item_from_id(id)
        getattr(plugin.media_item, '{action}_add_to_service'.format(action=plugin_name)).emit([item_id, True])


def get_options(plugin_name):
    plugin = Registry().get('plugin_manager').get_plugin_by_name(plugin_name)
    if plugin.status == PluginStatus.Active and plugin.media_item:
        options = plugin.media_item.search_options()
        return options
    return []


def set_option(plugin_name, search_option, value):
    plugin = Registry().get('plugin_manager').get_plugin_by_name(plugin_name)
    success = False
    if plugin.status == PluginStatus.Active and plugin.media_item:
        success = plugin.media_item.set_search_option(search_option, value)
    return success


@plugins.route('/<plugin>/search')
@login_required
def search_view(plugin):
    log.debug(f'{plugin}/search called')
    text = request.args.get('text', '')
    result = search(plugin, text)
    return jsonify(result)


@plugins.route('/<plugin>/add', methods=['POST'])
@login_required
def add_view(plugin):
    log.debug(f'{plugin}/add called')
    data = request.json
    if not data:
        abort(400)
    id = data.get('id', -1)
    add(plugin, id)
    return '', 204


@plugins.route('/<plugin>/live', methods=['POST'])
@login_required
def live_view(plugin):
    log.debug(f'{plugin}/live called')
    data = request.json
    if not data:
        abort(400)
    id = data.get('id', -1)
    live(plugin, id)
    return '', 204


@plugins.route('/<plugin>/search-options', methods=['GET'])
def search_options(plugin):
    """
    Get the plugin's search options
    """
    log.debug(f'{plugin}/search-options called')
    return jsonify(get_options(plugin))


@plugins.route('/<plugin>/search-options', methods=['POST'])
@login_required
def set_search_option(plugin):
    """
    Sets the plugin's search options
    """
    log.debug(f'{plugin}/search-options-set called')
    data = request.json
    if not data:
        log.error('Missing request data')
        abort(400)
    option = data.get('option', None)
    value = data.get('value', None)
    if value is None:
        log.error('Invalid data passed in value')
        abort(400)

    if set_option(plugin, option, value):
        return '', 204
    else:
        log.error('Invalid option or value')
        return '', 400


@plugins.route('/songs/transpose-live-item/<transpose_value>', methods=['GET'])
def transpose(transpose_value):
    log.debug('songs/transpose-live-item called')
    response_format = request.args.get('response_format', None, type=str)
    return_service_item = response_format == 'service_item'
    if transpose_value:
        try:
            transpose_value = int(transpose_value)
        except ValueError:
            abort(400)
        # Get lyrics from the live serviceitem in the live-controller and transpose it
        live_controller = Registry().get('live_controller')
        current_item = live_controller.service_item
        # make sure an service item is currently displayed and that it is a song
        if not current_item or current_item.name != 'songs':
            abort(400)
        live_item = current_item.to_dict()
        live_item['id'] = str(current_item.unique_identifier)
        chord_song_text = ''
        verse_index = 1
        for item in live_item['slides']:
            chord_song_text += ('---[Verse:%d]---' % verse_index) + '\n'
            chord_song_text += item['chords'] + '\n'
            verse_index += 1
        # transpose
        transposed_lyrics = transpose_lyrics(chord_song_text, transpose_value)
        # re-split into verses
        chord_slides = []
        verse_list = re.split(r'---\[Verse:(.+?)\]---', transposed_lyrics)
        # remove first blank entry
        verse_list = verse_list[1:]
        j = 0
        for i in range(0, len(verse_list), 2):
            if return_service_item:
                live_item['slides'][j]['chords'] = verse_list[i + 1].strip()
                j += 1
            else:
                chord_slides.append({'chords': verse_list[i + 1].strip(), 'verse': verse_list[i]})
        if return_service_item:
            live_item['chords_transposed'] = True
            live_item['slides'][live_controller.selected_row]['selected'] = True
            json_live_item = json.dumps(live_item, cls=OpenLPJSONEncoder)
            return Response(json_live_item, mimetype='application/json')
        else:
            return jsonify(chord_slides), 200
    abort(400)


@alert_2_views.route('', methods=['POST'])
@login_required
def alert():
    data = request.json
    if not data:
        abort(400)
    alert = data.get('text', '')
    if alert:
        if Registry().get('plugin_manager').get_plugin_by_name('alerts').status == PluginStatus.Active:
            Registry().get('alerts_manager').alerts_text.emit([alert])
            return '', 204
    abort(400)


@alert_1_views.route('')
@old_auth
def old_alert():
    alert = extract_request(request.args.get('data', ''), 'text')
    if alert:
        if Registry().get('plugin_manager').get_plugin_by_name('alerts').status == PluginStatus.Active:
            Registry().get('alerts_manager').alerts_text.emit([alert])
    return old_success_response()
