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
Windows Build Script
--------------------

This script is used to build the Windows binary and the accompanying installer.
For this script to work out of the box, it depends on a number of things:

Python 3.12

PySide6
    You should already have this installed, OpenLP doesn't work without it. The
    version the script expects is the packaged one available from pypi.

PyEnchant
    This script expects the precompiled, installable version of PyEnchant to be
    installed. You can find this on the PyEnchant site.

WiX Toolset
    The toolset should be installed into "C:\\%PROGRAMFILES%\\WiX Toolset v3.14"
    or similar.

PyInstaller
    PyInstaller can be installed from pypi.

Git
    You need the command line "git" client installed.

OpenLP
    A checkout of the latest code, in a branch directory, which is in a Bazaar
    shared repository directory. This means your code should be in a directory
    structure like this: "openlp\\branch-name".

windows-builder.py
    This script, of course. It should be in the "windows-installer" directory
    at the same level as OpenLP trunk.

Mako
    Mako Templates for Python.  This package is required for building the
    remote plugin.  It can be installed by going to your
    python_directory\\scripts\\.. and running "easy_install Mako".  If you do not
    have easy_install, the Mako package can be obtained here:

        http://www.makotemplates.org/download.html

Portable App Builds
    The following are required if you are planning to make a portable build of
    OpenLP.  The portable build conforms to the standards published by
    PortableApps.com:

        http://portableapps.com/development/portableapps.com_format

    PortableApps.com Installer:

        http://portableapps.com/apps/development/portableapps.com_installer

    PortableApps.com Launcher:

        http://portableapps.com/apps/development/portableapps.com_launcher

    NSIS Portable (Unicode version):

        http://portableapps.com/apps/development/nsis_portable
"""

import os
import glob
import sys
from distutils import dir_util
from hashlib import md5
from shutil import copy, move, rmtree

from lxml.etree import ElementTree
from lxml.builder import E, ElementMaker
from lxml.objectify import fromstring

from builder import Builder


class WindowsBuilder(Builder):
    """
    The :class:`WindowsBuilder` class encapsulates everything that is needed
    to build a Windows installer.
    """
    # Make mypy happy
    program_files: str
    candle_exe: str
    light_exe: str
    dist_path: str
    icon_path: str
    license_path: str
    portable_source_path: str
    portable_dest_path: str
    portablelauncher_exe: str
    portableinstaller_exe: str

    def _pep440_to_windows_version(self, version: str) -> str:
        """Convert a PEP440-compatible version string to a Windows version string"""
        self._print_verbose('Converting version: {}'.format(version))
        if pep440 := self.parse_pep440_version(version):
            self._print_verbose('Parsed as PEP440: {}'.format(pep440))
            build_number = 0
            if pep440.is_devrelease:
                build_number = pep440.dev
            elif pep440.is_prerelease:
                if pep440.pre[0] == 'a':
                    build_number = 1000 + pep440.pre[1]
                elif pep440.pre[0] == 'b':
                    build_number = 2000 + pep440.pre[1]
                elif pep440.pre[0] == 'rc':
                    build_number = 3000 + pep440.pre[1]
            else:
                build_number = 5000
            result = f'{pep440.base_version}.{build_number}'
            self._print_verbose('PEP440 result: {}'.format(result))
            return result
        else:
            self._print_verbose('Not valid PEP440, trying regex patterns')
            # Handle common git tag formats that aren't valid PEP440
            import re
            # Try to match patterns like "3.1.2-beta.dev13", "3.1.2-beta.11", "3.1.2-alpha.5", "3.1.2-rc.1"
            match = re.match(r'^(\d+\.\d+\.\d+)-?(alpha|beta|rc)\.?dev?(\d+)$', version)
            if match:
                base_version, pre_type, pre_number = match.groups()
                self._print_verbose('Regex match: base={}, type={}, number={}'.format(base_version, pre_type, pre_number))
                pre_number = int(pre_number)
                if pre_type == 'alpha':
                    build_number = 1000 + pre_number
                elif pre_type == 'beta':
                    build_number = 2000 + pre_number
                elif pre_type == 'rc':
                    build_number = 3000 + pre_number
                result = f'{base_version}.{build_number}'
                self._print_verbose('Regex result: {}'.format(result))
                return result
            
            # Try to match simple version patterns like "3.1.2"
            match = re.match(r'^(\d+\.\d+\.\d+)$', version)
            if match:
                result = f'{match.group(1)}.5000'
                self._print_verbose('Simple version result: {}'.format(result))
                return result
            
            # Fallback
            self._print_verbose('Using fallback version: 0.0.0.0')
            return '0.0.0.0'

    def _walk_dirs(self, dir_dict, path):
        """
        Walk a dictionary according to path
        """
        parts = path.split(os.sep)
        search_key = parts.pop(0)
        if search_key in dir_dict.keys():
            if not parts:
                return dir_dict[search_key]
            else:
                return self._walk_dirs(dir_dict[search_key], os.sep.join(parts))
        else:
            return None

    def _get_dirs_and_files(self, install_dir, start_dir):
        """
        Walk down a directory recursively and build up the XML for WiX
        """
        self._openlp_id = None
        start_base, start_path = os.path.split(start_dir)
        element = install_dir
        directories = {start_path: {'__dir__': element}}
        components = []
        component_ids = []
        FxE = ElementMaker(namespace='http://schemas.microsoft.com/wix/FirewallExtension',
                           nsmap={'fw': 'http://schemas.microsoft.com/wix/FirewallExtension'})

        for root, _, files in os.walk(start_dir):
            parent = os.sep.join(root.replace(os.path.join(start_base, ''), '').split(os.sep)[:-1])
            base = os.path.basename(root)
            if root != start_dir:
                dir_id = 'd_{}'.format(md5(os.path.join(parent, base).encode('utf8')).hexdigest())
                new_element = E.Directory(Id=dir_id, Name=base)
                element.append(new_element)
                element = new_element
                new_dir = {'__dir__': element}
                parent_dir = self._walk_dirs(directories, parent)
                parent_dir[base] = new_dir
                parent_dir['__dir__'].append(element)
            for fname in files:
                source = os.path.join(root, fname)
                source_id = 'f_{}'.format(md5(source.encode('utf8')).hexdigest())
                component_ids.append(source_id)
                if self.arch == 'x64':
                    file_ = E.File(Id=source_id, Name=fname, Source=source, ProcessorArchitecture='x64')
                    component = E.Component(file_, Id=source_id, Guid='*', DiskId='1', Win64='yes')
                else:
                    file_ = E.File(Id=source_id, Name=fname, Source=source)
                    component = E.Component(file_, Id=source_id, Guid='*', DiskId='1')
                if source.endswith('OpenLP.exe'):
                    self._openlp_id = source_id
                    file_.set('KeyPath', 'yes')
                    fw_program = '[#{}]'.format(source_id)
                    component.append(FxE.FirewallException(Id='OpenLP_TCP', Name='$(var.ProductName)',
                                                           IgnoreFailure='yes', Program=fw_program,
                                                           Protocol='tcp', Scope='any'))
                    component.append(FxE.FirewallException(Id='OpenLP_UDP', Name='$(var.ProductName)',
                                                           IgnoreFailure='yes', Program=fw_program,
                                                           Protocol='udp', Scope='any'))
                    component.append(E.Shortcut(Id='ApplicationStartMenuShortcut', Name='$(var.ProductName)',
                                                Description='$(var.Description)', Directory='ProgramMenuDir',
                                                Icon='OpenLP.ico', Advertise='yes', WorkingDirectory='INSTALLDIR'))
                    component.append(E.Shortcut(Id='DebugStartMenuShortcut', Name='$(var.ProductName) (Debug)',
                                                Description='Run $(var.ProductName) with debug logging enabled',
                                                Directory='ProgramMenuDir', Arguments='--log-level debug',
                                                Icon='OpenLP.ico', Advertise='yes', WorkingDirectory='INSTALLDIR'))
                    component.append(E.ProgId(
                        E.Extension(
                            E.Verb(Id="Open", Command="Open", Argument=" &quot;%1&quot;"),
                            E.MIME(Advertise="yes", ContentType="application/-x-openlp-service", Default="yes"),
                            Id="osz"
                        ),
                        E.Extension(
                            E.Verb(Id="Open", Command="Open", Argument=" &quot;%1&quot;"),
                            E.MIME(Advertise="yes", ContentType="application/-x-openlp-service-lite", Default="yes"),
                            Id="oszl"
                        ),
                        Id="OpenLP.Service",
                        Description="OpenLP Service File",
                        Icon="service_file.ico",
                        Advertise="yes"
                    ))
                element.append(component)
                components.append(component)
        return component_ids

    def _create_wix_file(self):
        """
        Create a WiX project file
        """
        self._print('Creating WiX file...')
        config_dir = os.path.dirname(self.config_path)
        self._print_verbose('Reading base WiX file')
        with open(os.path.join(config_dir, 'OpenLP-base.wxs'), 'rt') as base_file:
            xml = base_file.read()
        # Strip the 'v' prefix if present to make version compatible with PEP440
        version_for_conversion = self.version.lstrip('v') if self.version.startswith('v') else self.version
        self._print_verbose('Original version: {}'.format(self.version))
        self._print_verbose('Version for conversion: {}'.format(version_for_conversion))
        
        # Handle .dev versions properly by converting them to Windows format
        if '.dev' in version_for_conversion:
            # First clean up the version by removing git hash
            clean_version = version_for_conversion.rsplit('+', 1)[0]
            self._print_verbose('Cleaned dev version: {}'.format(clean_version))
            
            # Now try to convert using our enhanced method
            windows_version = self._pep440_to_windows_version(clean_version)
            self._print_verbose('Dev version converted to: {}'.format(windows_version))
        else:
            windows_version = self._pep440_to_windows_version(version_for_conversion)
        
        self._print_verbose('Final Windows version: {}'.format(windows_version))
        xml = xml % {
            'dialog': os.path.join(config_dir, 'WizardMain.bmp'),
            'banner': os.path.join(config_dir, 'WizardBanner.bmp'),
            'license': os.path.join(config_dir, 'LICENSE.rtf'),
            'platform': self.arch,
            'progfilefolder': 'ProgramFiles64Folder' if self.arch == 'x64' else 'ProgramFilesFolder',
            'systemfolder': 'System64Folder' if self.arch == 'x64' else 'SystemFolder',
            'version': windows_version
        }
        root = fromstring(xml.encode('utf8'))
        # Find the INSTALLDIR directory component and populate it with our files and folders
        install_dir = root.xpath('//wix:Directory[@Id="INSTALLDIR"]',
                                 namespaces={'wix': 'http://schemas.microsoft.com/wix/2006/wi'})[0]
        self._print_verbose('Creating XML fragments from files and directories')
        component_ids = self._get_dirs_and_files(install_dir, self.dist_path)
        # Write the property for the "Run OpenLP" checkbox
        product = root.xpath('//wix:Product',
                             namespaces={'wix': 'http://schemas.microsoft.com/wix/2006/wi'})[0]
        product.append(E.Property(Id='WixShellExecTarget', Value='[#{}]'.format(self._openlp_id)))
        # Set the component ids for the feature
        feature = root.xpath('//wix:Feature',
                             namespaces={'wix': 'http://schemas.microsoft.com/wix/2006/wi'})[0]
        for component_id in component_ids:
            feature.append(E.ComponentRef(Id=component_id))
        self._print_verbose('Writing new WiX file')
        tree = ElementTree(root)
        with open(os.path.join(config_dir, 'OpenLP.wxs'), 'wb') as f:
            tree.write(f, encoding='utf-8', xml_declaration=True, pretty_print=True)

    def _run_wix_tools(self):
        """
        Run the WiX toolset to create an installer
        """
        self._print('Running WiX tools...')
        if self.arch == 'x64':
            version = '{}-x64'.format(self.version)
        else:
            version = self.version
        msi_file = os.path.abspath(os.path.join(self.dist_path, '..', 'OpenLP-{}.msi'.format(version)))
        if os.path.exists(msi_file):
            self._print_verbose('Removing old MSI file')
            os.unlink(msi_file)
        config_dir = os.path.dirname(self.config_path)
        os.chdir(self.dist_path)
        self._run_command([self.candle_exe, '-ext', 'WiXUtilExtension', '-ext', 'WixUIExtension',
                           '-ext', 'WixFirewallExtension', os.path.join(config_dir, 'OpenLP.wxs')],
                          'Error running WiX tool: candle')
        self._run_command([self.light_exe, '-ext', 'WiXUtilExtension', '-ext', 'WixUIExtension',
                           '-ext', 'WixFirewallExtension', '-sice:ICE60', '-sice:ICE61', 'OpenLP.wixobj',
                           '-o', msi_file],
                          'Error running WiX tool: light')

    def _create_portableapp_structure(self):
        """
        Checks the PortableApp directory structure amd creates
        missing subdirs
        """
        self._print('... Checking PortableApps directory structure...')
        launcher_path = os.path.join(self.portable_dest_path, 'App', 'Appinfo', 'Launcher')
        if not os.path.exists(launcher_path):
            os.makedirs(launcher_path)
        settings_path = os.path.join(self.portable_dest_path, 'Data', 'Settings')
        if not os.path.exists(settings_path):
            os.makedirs(settings_path)

    def _create_portableapps_appinfo_file(self):
        """
        Create a Portabbleapps appinfo.ini file.
        """
        self._print_verbose('... Creating PortableApps appinfo file ...')
        config_dir = os.path.dirname(self.config_path)
        # Strip the 'v' prefix if present to make version compatible with PEP440
        version_for_conversion = self.version.lstrip('v') if self.version.startswith('v') else self.version
        if '.dev' in version_for_conversion:
            version, revision = version_for_conversion.split('.dev')
            version = version + '.0' * (2 - version.count('.'))
            self.portable_version = version + '.' + revision.split('+')[0]
        else:
            self.portable_version = self._pep440_to_windows_version(version_for_conversion)
        with open(os.path.join(config_dir, 'appinfo.ini.default'), 'r') as input_file, \
                open(os.path.join(self.portable_dest_path, 'App', 'Appinfo', 'appinfo.ini'), 'w') as output_file:
            content = input_file.read()
            content = content.replace('%(display_version)s', self.portable_version)
            content = content.replace('%(package_version)s', self.portable_version)
            content = content.replace('%(arch)s', self.arch)
            output_file.write(content)

    def _run_portableapp_builder(self):
        """
        Creates a portable installer.
        1  Copies the distribution to the portable apps directory
        2  Builds the PortableApps Launcher
        3  Builds the PortableApps Install
        """
        self._print('Running PortableApps Builder...')
        self._print_verbose('... Clearing old files')
        # Remove previous contents of portableapp build directory.
        if os.path.exists(self.portable_dest_path):
            rmtree(self.portable_dest_path)
        self._print_verbose('... Creating PortableApps build directory')
        # Copy the contents of the OpenLPPortable directory to the portable
        # build directory.
        dir_util.copy_tree(self.portable_source_path, self.portable_dest_path)
        self._create_portableapp_structure()
        self._create_portableapps_appinfo_file()
        # Copy distribution files to portableapp build directory.
        self._print_verbose('... Copying distribution files')
        portable_app_path = os.path.join(self.portable_dest_path, 'App', 'OpenLP')
        dir_util.copy_tree(self.dist_path, portable_app_path)
        # Build the launcher.
        self._print_verbose('... Building PortableApps Launcher')
        self._run_command([self.portablelauncher_exe, self.portable_dest_path],
                          'Error creating PortableApps Launcher')
        # Build the portable installer.
        self._print_verbose('... Building PortableApps Installer')
        self._run_command([self.portableinstaller_exe, self.portable_dest_path],
                          'Error running PortableApps Installer')
        portable_exe_name = 'OpenLPPortable_{ver}-{arch}.paf.exe'.format(ver=self.portable_version, arch=self.arch)
        portable_exe_path = os.path.abspath(os.path.join(self.portable_dest_path, '..', portable_exe_name))
        self._print_verbose('... Portable Build: {}'.format(portable_exe_path))
        if os.path.exists(portable_exe_path):
            move(portable_exe_path, os.path.join(self.dist_path, '..', portable_exe_name))
            self._print('PortableApp build complete')
        else:
            raise Exception('PortableApp failed to build')

    def get_platform(self):
        """
        Return the platform we're building for
        """
        return 'Windows'

    def get_config_defaults(self):
        """
        Build some default values for the config file
        """
        config_defaults = super().get_config_defaults()
        config_defaults.update({
            'pyroot': self.python_root,
            'progfiles': self.program_files,
            'progfilesx86': self.program_files_x86,
            'sitepackages': self.site_packages,
            'projects': os.path.abspath(os.path.join(self.script_path, '..', '..'))
        })
        return config_defaults

    def get_qt_translations_path(self):
        """
        Return the path to Qt translation files on Windows
        """
        return os.path.join(self.site_packages, 'PyQt5', 'Qt5', 'translations') \
            if self.args.use_qt5 else os.path.join(self.site_packages, 'PySide6', 'translations')

    def add_extra_args(self, parser):
        """
        Add extra arguments to the command line argument parser
        """
        parser.add_argument('--portable', action='store_true', default=False,
                            help='Build a PortableApps.com build of OpenLP too')

    def setup_system_paths(self):
        """
        Set up some system paths.
        """
        super().setup_system_paths()
        self.python_root = os.path.dirname(self.python)
        self.site_packages = os.path.join(self.python_root, 'Lib', 'site-packages')
        self.program_files = os.environ['PROGRAMFILES']
        self.program_files_x86 = os.getenv('PROGRAMFILES(x86)')
        self._print_verbose('   {:.<20}: {}'.format('site packages: ', self.site_packages))
        self._print_verbose('   {:.<20}: {}'.format('program files: ', self.program_files))
        self._print_verbose('   {:.<20}: {}'.format('program files x86: ', self.program_files_x86))

    def setup_paths(self):
        """
        Set up a variety of paths that we use throughout the build process.
        """
        super().setup_paths()
        self.dist_path = os.path.join(self.work_path, 'dist', 'OpenLP')
        self.winres_path = os.path.join(self.branch_path, 'resources', 'windows')

    def setup_extra(self):
        """
        Extra setup to run
        """
        # Detect python instance bit size
        self.arch = 'x86' if sys.maxsize == 0x7fffffff else 'x64'

    def _copy_vlc_files(self):
        """
        Copy the VLC files into the app bundle
        """
        self._print('Copying VLC files...')
        from shutil import copytree
        vlc_path = os.path.join(self.program_files, 'VideoLAN', 'VLC')
        vlc_dest = os.path.join(self.dist_path, 'vlc')
        if not os.path.exists(vlc_dest):
            os.makedirs(vlc_dest)
        for fname in ['libvlc.dll', 'libvlccore.dll']:
            self._print_verbose('... {}'.format(fname))
            copy(os.path.join(vlc_path, fname), os.path.join(vlc_dest, fname))
        if os.path.exists(os.path.join(vlc_dest, 'plugins')):
            rmtree(os.path.join(vlc_dest, 'plugins'))
        self._print_verbose('... copying VLC plugins')
        copytree(os.path.join(vlc_path, 'plugins'), os.path.join(vlc_dest, 'plugins'))

    def copy_extra_files(self):
        """
        Copy all the Windows-specific files.
        """
        self._print('Copying extra files for Windows...')
        self._print_verbose('... OpenLP.ico')
        copy(self.icon_path, os.path.join(self.dist_path, 'OpenLP.ico'))
        self._print_verbose('... LICENSE.txt')
        copy(self.license_path, os.path.join(self.dist_path, 'LICENSE.txt'))
        self._print_verbose('... service_file.ico')
        config_dir = os.path.dirname(self.config_path)
        copy(os.path.join(config_dir, 'service_file.ico'), os.path.join(self.dist_path, 'service_file.ico'))
        if self.args.use_qt5:
            self._copy_vlc_files()

    def build_package(self):
        """
        Build the installer
        """
        self._create_wix_file()
        self._run_wix_tools()
        if self.args.portable:
            self._run_portableapp_builder()

    def get_extra_parameters(self):
        """
        Return a list of any extra parameters we wish to use
        """
        parameters = []
        dll_path = '{pf}\\Windows Kits\\10\\Redist\\ucrt\\DLLs\\{arch}\\*.dll'.format(pf=self.program_files_x86,
                                                                                      arch=self.arch)
        # Finds the UCRT DDLs available from the Windows 10 SDK
        for binary in glob.glob(dll_path):
            parameters.append('--add-binary')
            parameters.append(binary + ";.")
        return parameters


if __name__ == '__main__':
    WindowsBuilder().main()
