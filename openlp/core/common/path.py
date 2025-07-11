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
import os
import shutil
from pathlib import Path

from openlp.core.common.platform import is_win


log = logging.getLogger(__name__)


def replace_params(args, kwargs, params):
    """
    Apply a transformation function to the specified args or kwargs

    :param tuple args: Positional arguments
    :param dict kwargs: Key Word arguments
    :param params: A tuple of tuples with the position and the key word to replace.
    :return: The modified positional and keyword arguments
    :rtype: tuple[tuple, dict]


    Usage:
        Take a method with the following signature, and assume we which to apply the str function to arg2:
            def method(arg1=None, arg2=None, arg3=None)

        As arg2 can be specified postitionally as the second argument (1 with a zero index) or as a keyword, the we
        would call this function as follows:

        replace_params(args, kwargs, ((1, 'arg2', str),))
    """
    args = list(args)
    for position, key_word, transform in params:
        if len(args) > position:
            args[position] = transform(args[position])
        elif key_word in kwargs:
            kwargs[key_word] = transform(kwargs[key_word])
    return tuple(args), kwargs


def which(*args, **kwargs):
    """
    Wraps :func:shutil.which` so that it return a Path objects.

    :rtype: Path

    See the following link for more information on the other parameters:
        https://docs.python.org/3/library/shutil.html#shutil.which
    """
    file_name = shutil.which(*args, **kwargs)
    if file_name:
        return str_to_path(file_name)
    return None


def path_to_str(path=None):
    """
    A utility function to convert a Path object or NoneType to a string equivalent.

    :param Path | None path: The value to convert to a string
    :return: An empty string if :param:`path` is None, else a string representation of the :param:`path`
    :rtype: str
    """
    if isinstance(path, str):
        return path
    if not isinstance(path, Path) and path is not None:
        raise TypeError('parameter \'path\' must be of type Path or NoneType')
    if path is None:
        return ''
    else:
        return str(path)


def str_to_path(string):
    """
    A utility function to convert a str object to a Path or NoneType.

    This function is of particular use because initating a Path object with an empty string causes the Path object to
    point to the current working directory.

    :param str string: The string to convert
    :return: None if :param:`string` is empty, or a Path object representation of :param:`string`
    :rtype: Path | None
    """
    if isinstance(string, Path):
        return string
    if not isinstance(string, str):
        log.error('parameter \'string\' must be of type str, got {} which is a {} instead'.format(string, type(string)))
        return None
    if string == '':
        return None
    return Path(string)


def create_paths(*paths, **kwargs):
    """
    Create one or more paths

    :param Path paths: The paths to create
    :param bool do_not_log: To not log anything. This is need for the start up, when the log isn't ready.
    :rtype: None
    """
    for path in paths:
        if not kwargs.get('do_not_log', False):
            log.debug('create_path {path}'.format(path=path))
        try:
            if not path.exists():
                path.mkdir(parents=True)
        except OSError:
            if not kwargs.get('do_not_log', False):
                log.exception('failed to check if directory exists or create directory')


def files_to_paths(file_names):
    """
    Convert a list of file names in to a list of file paths.

    :param list[str] file_names: The list of file names to convert.
    :return: The list converted to file paths
    :rtype: Path
    """
    if file_names:
        return [str_to_path(file_name) for file_name in file_names]


def resolve(path_obj, is_strict=False):
    """
    Resolve a Path object, bypassing symlink resolving on Windows

    :param Path path_obj: The path object to resolve
    :return: The resolved Path object
    :rtype: Path
    """
    if is_win():
        resolved_path = Path(os.path.realpath(path_obj))
        if is_strict:
            # Mirror the behaviour of Path.resolve(strict=True)
            resolved_path.lstat()
        return resolved_path
    return path_obj.resolve(strict=is_strict)
