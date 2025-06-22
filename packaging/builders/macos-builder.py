# -*- coding: utf-8 -*-
# vim: autoindent shiftwidth=4 expandtab textwidth=120 tabstop=4 softtabstop=4

##########################################################################
# OpenLP - Open Source Lyrics Projection                                 #
# ---------------------------------------------------------------------- #
# Copyright (c) 2008-2019 OpenLP Developers                              #
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
macOS Build Script
--------------------

This script is used to build the macOS app bundle and pack it into dmg file.
For this script to work out of the box, it depends on a number of things:

Python 3.12

PySide6
    You should already have this installed, OpenLP doesn't work without it. The
    version the script expects is the packaged one available from River Bank
    Computing.

PyEnchant
    This script expects the precompiled, installable version of PyEnchant to be
    installed. You can find this on the PyEnchant site.

PyInstaller
    PyInstaller can be installed with pip

Git
    You need the command line "git" client installed.

OpenLP
    A checkout of the latest code, in a branch directory, which is in a Bazaar
    shared repository directory. This means your code should be in a directory
    structure like this: "openlp\branch-name".

macos-builder.py
    This script, of course. It should be in the "macos-package" directory
    at the same level as OpenLP trunk.

Mako
    Mako Templates for Python.  This package is required for building the
    remote plugin.

Alembic
    Required for upgrading the databases used in OpenLP.

config.ini.default
    The configuration file contains settings of the version string to include
    in the bundle as well as directory and file settings for different
    purposes (e.g. PyInstaller location or installer background image)

To install everything you should install latest python 3.12 from python.org. It
is recommended to create virtual environment. You can install all dependencies
like this:

    $ python -m pip install alembic
      beautifulsoup4
      chardet
      flask
      flask-cors
      lxml
      Mako
      mock
      mysql-connector-python
      packaging
      platformdirs
      psycopg2-binary
      pyenchant
      PySide6
      pysword
      pytest
      pytest-qt
      QDarkStyle
      qrcode
      QtAwesome
      requests
      six
      sqlalchemy
      waitress
      websockets
      py-applescript
      pyobjc-core
      pyobjc-framework-Cocoa
      Pyro5
      PyInstaller
"""

import glob
import os
import platform
from pathlib import Path
from shutil import copy, move, rmtree

from macholib.MachO import MachO
from macholib.util import in_system_path

from builder import Builder


class MacOSBuilder(Builder):
    """
    The :class:`MacOSBuilder` class encapsulates everything that is needed
    to build a macOS .dmg file.
    """

    def _pep440_to_mac_version(self, version: str) -> str:
        """Convert a PEP440-compatible version to a Mac compatible version"""
        if pep440 := self.parse_pep440_version(version):
            # macOS doesn't support anything other than [major].[minor].[patch], so we just drop everything else
            return pep440.base_version
        else:
            return '0.0.0'

    def _get_directory_size(self, directory):
        """
        Return directory size - size of everything in the dir.
        """
        dir_size = 0
        for (path, dirs, files) in os.walk(directory):
            for file in files:
                filename = os.path.join(path, file)
                dir_size += os.path.getsize(filename)
        return dir_size

    def _create_symlink(self, folder):
        """
        Create the appropriate symlink in the MacOS folder pointing to the Resources folder.
        """
        sibling = Path(str(folder).replace('MacOS', ''))

        # PyQt5/Qt/qml/QtQml/Models.2
        root = str(sibling).partition('Contents')[2].lstrip('/')
        # ../../../../
        backward = '../' * len(root.split('/'))
        # ../../../../Resources/PyQt5/Qt/qml/QtQml/Models.2
        good_path = f'{backward}Resources/{root}'

        folder.symlink_to(good_path)

    def _fix_qt_dll(self, dll_file):
        """
        Fix the DLL lookup paths to use relative ones for Qt dependencies.
        Inspiration: PyInstaller/depend/dylib.py:mac_set_relative_dylib_deps()
        Currently one header is pointing to (we are in the Resources folder):
            @loader_path/../../../../QtCore (it is referencing to the old MacOS folder)
        It will be converted to:
            @loader_path/../../../../../../MacOS/QtCore
        """

        def match_func(pth):
            """
            Callback function for MachO.rewriteLoadCommands() that is
            called on every lookup path setted in the DLL headers.
            By returning None for system libraries, it changes nothing.
            Else we return a relative path pointing to the good file
            in the MacOS folder.
            """
            basename = os.path.basename(pth)
            if not basename.startswith('Qt'):
                return None
            return f'@loader_path{good_path}/{basename}'

        # Skip it if it's not a dylib file
        if dll_file.suffix != '.dylib':
            return

        # Resources/PyQt5/Qt/qml/QtQuick/Controls.2/Fusion
        root = str(dll_file.parent).partition('Contents')[2][1:]
        # /../../../../../../..
        backward = '/..' * len(root.split('/'))
        # /../../../../../../../MacOS
        good_path = f'{backward}/MacOS'

        # Rewrite Mach headers with corrected @loader_path
        dll = MachO(dll_file)
        dll.rewriteLoadCommands(match_func)
        with open(dll.filename, 'rb+') as f:
            for header in dll.headers:
                f.seek(0)
                dll.write(f)
            f.seek(0, 2)
            f.flush()

    def _find_problematic_qt_folders(self, folder):
        """
        Recursively yields problematic folders (containing a dot in their name).
        """
        for path in folder.iterdir():
            if not path.is_dir() or path.is_symlink():
                # Skip simlinks as they are allowed (even with a dot)
                continue
            if path.name == 'qml':
                yield path
            else:
                yield from self._find_problematic_qt_folders(path)

    def _move_contents_to_resources(self, folder):
        """
        Recursively move any non symlink file from a problematic folder to the sibling one in Resources.
        """
        for path in folder.iterdir():
            if path.is_symlink():
                continue
            if path.is_dir():
                yield from self._move_contents_to_resources(path)
            else:
                sibling = Path(str(path).replace('MacOS', 'Resources'))
                sibling.parent.mkdir(parents=True, exist_ok=True)
                move(path, sibling)
                yield sibling

    def _fix_qt_paths(self):
        """
        Fix the Qt paths
        """
        app_path = Path(self.dist_app_path) / 'Contents' / 'MacOS'
        for folder in self._find_problematic_qt_folders(app_path):
            for problematic_file in self._move_contents_to_resources(folder):
                self._fix_qt_dll(problematic_file)
            rmtree(folder)
            self._create_symlink(folder)

    def _relink_binary(self, bin_name):
        """
        Relink bundled libraries
        """
        self._print('Linking {bin_name} with bundled libraries...'.format(bin_name=bin_name))
        libname = os.path.join(self.dist_path, bin_name)
        distname = os.path.relpath(self.dist_path, libname)
        self._print_verbose('... {bin_name} path {path}'.format(bin_name=bin_name, path=libname))

        # Determine how many directories up is the directory with shared
        # dynamic libraries. '../'
        # E.g.  ./qt4_plugins/images/ -> ./../../
        parent_dir = ''
        # Check if distname is not only base filename.
        if os.path.dirname(distname):
            parent_level = len(os.path.dirname(distname).split(os.sep))
            parent_dir = parent_level * (os.pardir + os.sep)

        def match_func(pth):
            """
            For system libraries leave path unchanged.
            """
            # Match non system dynamic libraries.
            if not in_system_path(pth):
                # Use relative path to dependend dynamic libraries bases on
                # location of the executable.
                pth = os.path.join('@loader_path', parent_dir, os.path.basename(pth))
                self._print_verbose('... %s', pth)
                return pth

        # Rewrite mach headers with @loader_path.
        dll = MachO(libname)
        dll.rewriteLoadCommands(match_func)

        # Write changes into file.
        # Write code is based on macholib example.
        try:
            self._print_verbose('... writing new library paths')
            with open(dll.filename, 'rb+') as dll_file:
                for header in dll.headers:
                    dll_file.seek(0)
                    dll.write(dll_file)
                dll_file.seek(0, 2)
        except Exception:
            pass

    def _install_pyro5(self):
        """
        Install Pyro5 into the vendor directory
        """
        self._print('Installing Pyro5 for LibreOffice')
        target = os.path.join(self.dist_path, 'plugins', 'presentations', 'lib', 'vendor')
        argv = ['pip', 'install', 'Pyro5', '-t', target, '--disable-pip-version-check', '--no-compile']
        self._run_module('pip', argv, 'Error installing Pyro5 with pip', run_name='__main__')
        egg_info_glob = glob.glob(os.path.join(target, '*.egg-info'))
        egg_info_glob.extend(glob.glob(os.path.join(target, '*.dist-info')))
        self._print_verbose('... glob: {}'.format(egg_info_glob))
        for path in egg_info_glob:
            rmtree(path, True)

    def _copy_bundle_files(self):
        """
        Copy Info.plist and OpenLP.icns to app bundle.
        """
        self._print_verbose('... OpenLP.icns')
        try:
            os.makedirs(os.path.join(self.dist_app_path, 'Contents', 'Resources'))
        except FileExistsError:
            pass
        copy(self.icon_path, os.path.join(self.dist_app_path, 'Contents', 'Resources',
                                          os.path.basename(self.icon_path)))
        self._print_verbose('... Info.plist')
        # Add OpenLP version to Info.plist and add it to app bundle.
        with open(os.path.join(self.dist_app_path, 'Contents', os.path.basename(self.bundle_info_path)), 'w') as fw, \
                open(self.bundle_info_path, 'r') as fr:
            text = fr.read()
            # Strip the 'v' prefix if present to make version compatible with PEP440
            version_for_conversion = self.version.lstrip('v') if self.version.startswith('v') else self.version
            text = text % {'openlp_version': self._pep440_to_mac_version(version_for_conversion)}
            fw.write(text)

    def _copy_macos_files(self):
        """
        Copy all the macOS specific files.
        """
        self._print_verbose('... LICENSE.txt')
        copy(self.license_path, os.path.join(self.dist_path, 'LICENSE.txt'))

    def _code_sign(self):
        certificate = self.config.get('codesigning', 'certificate')
        self._print('Checking for certificate...')
        if not certificate:
            self._print('Certificate not set, skipping code signing!')
            return
        self._run_command(['security', 'find-certificate', '-c', certificate],
                          'Could not find certificate "{certificate}" in keychain, '.format(certificate=certificate) +
                          'codesigning will not work without a certificate')
        self._print('Codesigning app...')
        self._run_command(['codesign', '--deep', '-s', certificate, self.dist_app_path], 'Error running codesign')

    def _create_dmg(self):
        """
        Create .dmg file.
        """
        self._print('Creating dmg file...')
        arch = platform.machine()
        dmg_name = f'OpenLP-{self.version}-{arch}.dmg'
        dmg_title = f'OpenLP {self.version}'

        self.dmg_file = os.path.join(self.work_path, 'dist', dmg_name)
        # Remove dmg if it exists.
        if os.path.exists(self.dmg_file):
            os.remove(self.dmg_file)
        # Get size of the directory in bytes, convert to MB, and add padding
        size = self._get_directory_size(self.dist_app_path)
        size = size / (1000 * 1000)
        size += 10

        os.chdir(os.path.dirname(self.dmg_settings_path))
        argv = ['dmgbuild', '-s', self.dmg_settings_path, '-D', 'size={size}M'.format(size=size),
                '-D', 'icon={icon_path}'.format(icon_path=self.icon_path),
                '-D', 'app={dist_app_path}'.format(dist_app_path=self.dist_app_path), dmg_title, self.dmg_file]
        self._run_module('dmgbuild', argv, 'Error running dmgbuild', run_name='__main__')
        self._print('Finished creating dmg file, resulting file: %s' % self.dmg_file)

    def get_platform(self):
        """
        Return the plaform we're building for
        """
        return 'macOS'

    def get_extra_parameters(self):
        """
        Return a list of any extra parameters we wish to use for macOS builds
        """
        return [
            '--runtime-hook', os.path.join(self.hooks_path, 'rthook_mcp.py')
        ]

    def get_qt_translations_path(self):
        """
        Return the path to Qt translation files on macOS
        """
        if self.args.use_qt5:
            from PyQt5.QtCore import QCoreApplication
        else:
            from PySide6.QtCore import QCoreApplication
        qt_library_path = QCoreApplication.libraryPaths()[0]
        return os.path.join(os.path.dirname(qt_library_path), 'translations')

    def setup_extra(self):
        """
        Extra setup to run
        """
        self.dist_app_path = os.path.join(self.work_path, 'dist', 'OpenLP.app')
        self.dist_path = os.path.join(self.work_path, 'dist', 'OpenLP.app', 'Contents', 'MacOS')

    def copy_extra_files(self):
        """
        Copy any extra files which are particular to a platform
        """
        self._print('Copying extra files for macOS...')
        self._copy_bundle_files()
        self._copy_macos_files()
        self._install_pyro5()

    def build_package(self):
        """
        Build the actual DMG
        """
        self._fix_qt_paths()
        # self._code_sign()
        self._create_dmg()


if __name__ == '__main__':
    MacOSBuilder().main()
