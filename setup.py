#!/usr/bin/env python3
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

from subprocess import run

from setuptools import setup, find_packages


VERSION_FILE = 'openlp/.version'


ver_file = None
try:
    # Get the revision of this tree.
    git_version = run(['git', 'describe', '--tags'], capture_output=True, check=True, universal_newlines=True).stdout
    version_string = '+'.join(git_version.strip().rsplit('-g', 1))
    version_string = '.dev'.join(version_string.rsplit('-', 1))
    ver_file = open(VERSION_FILE, 'w')
    ver_file.write(version_string)
except Exception:
    ver_file = open(VERSION_FILE, 'r')
    version_string = ver_file.read().strip()
finally:
    ver_file.close()


setup(
    name='OpenLP',
    version=version_string,
    description="Open source Church presentation and lyrics projection application.",
    long_description="""
OpenLP (previously openlp.org) is free church presentation software, or lyrics projection software, used to display
slides of songs, Bible verses, videos, images, and even presentations (if PowerPoint is installed) for church worship
using a computer and a display/projector.""",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: MacOS X',
        'Environment :: Win32 (MS Windows)',
        'Environment :: X11 Applications',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Religion',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: Afrikaans',
        'Natural Language :: Dutch',
        'Natural Language :: English',
        'Natural Language :: French',
        'Natural Language :: German',
        'Natural Language :: Hungarian',
        'Natural Language :: Indonesian',
        'Natural Language :: Japanese',
        'Natural Language :: Norwegian',
        'Natural Language :: Portuguese (Brazilian)',
        'Natural Language :: Russian',
        'Natural Language :: Swedish',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: BSD :: FreeBSD',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Desktop Environment :: Gnome',
        'Topic :: Desktop Environment :: K Desktop Environment (KDE)',
        'Topic :: Multimedia',
        'Topic :: Multimedia :: Graphics :: Presentation',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Video',
        'Topic :: Religion'
    ],  # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='open source church presentation lyrics projection song bible display project',
    author='Raoul Snyman',
    author_email='raoulsnyman@openlp.org',
    url='https://openlp.org/',
    license='GPL-3.0-or-later',
    packages=find_packages(exclude=['ez_setup', 'tests*']),
    include_package_data=True,
    zip_safe=False,
    python_requires='>=3.9',
    install_requires=[
        'alembic',
        'beautifulsoup4',
        'chardet',
        'dbus-python; platform_system=="Linux"',
        'distro; platform_system=="Linux"',
        'flask',
        'flask-cors',
        'lxml',
        'Mako',
        'packaging',
        'platformdirs',
        'PyICU',
        'pyobjc; platform_system=="Darwin"',
        'pyobjc-framework-Cocoa; platform_system=="Darwin"',
        'PySide6 >= 6.8',
        'Pyro5; platform_system=="Darwin"',
        'pywin32; platform_system=="Windows"',
        'QtAwesome',
        "qrcode",
        'requests',
        'SQLAlchemy',
        'waitress',
        'websockets',
        'fastmcp'
    ],
    extras_require={
        'darkstyle': ['QDarkStyle'],
        'mysql': ['PyMySQL'],
        'odbc': ['pyodbc'],
        'postgresql': ['psycopg2_binary'],
        'spellcheck': ['pyenchant >= 1.6'],
        'sword-bibles': ['pysword'],
        'test': [
            'pyodbc',
            'pysword',
            'pytest',
            'pytest-qt',
            'flake8',
        ]
    },
    entry_points={'gui_scripts': ['openlp = openlp.__main__:start']}
)
