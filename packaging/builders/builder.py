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
Base class for the Windows and macOS builders.
"""
import os
import runpy
import sys
from argparse import ArgumentParser
from configparser import ConfigParser
from io import StringIO
from packaging.version import InvalidVersion, Version
from pathlib import Path
from shutil import copy, rmtree
from subprocess import Popen, PIPE

BUILDER_DESCRIPTION = 'Build OpenLP for {platform}. Options are provided on both the command line and a ' \
    'configuration file. Options in the configuration file are overridden by the command line options.\n\n' \
    'This build system can produce either development or release builds. A development release uses the ' \
    'code as-is in the specified branch directory. The release build exports a tag from git and uses the ' \
    'exported code for building. The two modes are invoked by the presence or absence of the --release ' \
    'option. If this option is omitted, a development build is built, while including the --release ' \
    'option with a version number will produce a build of that exact version.'


def _which(program):
    """
    Return absolute path to a command found on system PATH.
    """
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath and is_exe(os.path.abspath(program)):
        return os.path.abspath(program)
    else:
        for path in os.environ['PATH'].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None


class Builder(object):
    """
    A Generic class to base other operating system specific builders on
    """
    def __init__(self):
        self.setup_args()
        self.setup_system_paths()
        self.read_config()
        self.setup_paths()
        self.setup_executables()
        self.setup_extra()

    def _print(self, text, *args):
        """
        Print stuff out. Later we might want to use a log file.
        """
        if len(args) > 0:
            text = text % tuple(args)
        print(text)

    def _print_verbose(self, text, *args):
        """
        Print output, obeying "verbose" mode.
        """
        if self.args.verbose:
            self._print(text, *args)

    def _run_command(self, cmd, err_msg, exit_code=0):
        """
        Run command in subprocess and print error message in case of Exception.

        Return text from stdout.
        """
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        output, error = proc.communicate()
        code = proc.wait()
        if code != exit_code:
            self._print(output)
            self._print(error)
            raise Exception(err_msg)
        return output, error

    def _run_module(self, module, argv, err_msg, run_name=None):
        """
        Run a python module as if python -m <module>
        """
        self._run_runpy('module', module, argv, err_msg, run_name)

    def _run_path(self, path, argv, err_msg, run_name=None):
        """
        Run a python script as if python <path>
        """
        self._run_runpy('path', path, argv, err_msg, run_name)

    def _run_runpy(self, run_type, exe_arg, argv, err_msg, run_name=None):
        """
        Run a python script or module
        """
        # Capture stdout and stderr
        stdout_back = sys.stdout
        stderr_back = sys.stderr
        new_stdout = StringIO()
        new_stderr = StringIO()
        sys.stdout = new_stdout
        sys.stderr = new_stderr
        # Set args
        sys.argv = argv
        exit_code: str | int = 0
        try:
            self._print_verbose('... {}'.format(' '.join(argv)))
            if run_type == 'module':
                runpy.run_module(exe_arg, run_name=run_name)
            else:
                runpy.run_path(exe_arg, run_name=run_name)
        except SystemExit as se:
            if se.code and se.code != 0:
                exit_code = se.code
        finally:
            # Set stdout and stderr back to standard
            sys.stdout = stdout_back
            sys.stderr = stderr_back
        if exit_code != 0:
            self._print(new_stdout.getvalue())
            self._print(new_stderr.getvalue())
            raise Exception(err_msg)
        else:
            self._print_verbose(new_stdout.getvalue())
            self._print_verbose(new_stderr.getvalue())

    def _git(self, command, work_path, args=[], err_msg='There was an error running git'):
        """
        Update the code in the branch.
        """
        os.chdir(work_path)
        output, _ = self._run_command(['git', command] + args, err_msg)
        return output

    def parse_pep440_version(self, version: str) -> Version | None:
        """Parse a PEP440-compatible version number into a dictionary"""
        try:
            return Version(version)
        except InvalidVersion:
            return None

    def get_platform(self):
        """
        Return the platform we're building for
        """
        return 'unspecified'

    def get_config_defaults(self):
        """
        Build some default values for the config file
        """
        return {
            'here': os.path.dirname(self.config_path),
            'home': str(Path.home())
        }

    def get_qt_translations_path(self):
        """
        Return the path to Qt's translation files
        """
        return ''

    def add_extra_args(self, parser):
        """
        Add extra arguments to the argument parser
        """
        pass

    def setup_args(self):
        """
        Set up an argument parser and parse the command line arguments.
        """
        parser = ArgumentParser(description=BUILDER_DESCRIPTION.format(platform=self.get_platform()))
        parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', default=False,
                            help='Print out additional information')
        parser.add_argument('-c', '--config', metavar='FILENAME', required=True,
                            help='Specify the path to the configuration file')
        parser.add_argument('-b', '--branch', metavar='PATH', help='Specify the path to the branch you wish to build')
        parser.add_argument('-r', '--release', metavar='VERSION', default=None,
                            help='Build a release version of OpenLP with the version specified')
        parser.add_argument('-x', '--export', dest='can_export', action='store_true', default=False,
                            help='Export when building a release. Defaults to false, ignored for non-release builds')
        parser.add_argument('-t', '--update-translations', action='store_true', default=False,
                            help='Update the translations from Transifex')
        parser.add_argument('-u', '--transifex-user', metavar='USERNAME', default=None, help='Transifex username')
        parser.add_argument('-p', '--transifex-pass', metavar='PASSWORD', default=None, help='Transifex password')
        parser.add_argument('--skip-update', action='store_true', default=False,
                            help='Do NOT update the branch before building')
        parser.add_argument('--skip-translations', action='store_true', default=False,
                            help='Do NOT update the language translation files')
        parser.add_argument('--use-qt5', action='store_true', default=False,
                            help='Compile Qt5 language translation files')
        parser.add_argument('--debug', action='store_true', default=False, help='Create a debug build')
        parser.add_argument('--tag-override', metavar='<tag>.dev<revision-count>+<commit-hash>', default=None,
                            help='Override tag and revision, should be in format <tag>.dev<revision-count>+<commit-hash>')  # noqa
        self.add_extra_args(parser)
        self.args = parser.parse_args()

    def read_config(self):
        """
        Read the configuration from the configuration file.
        """
        self.config = ConfigParser(defaults=self.get_config_defaults())
        self.config.read(self.config_path)

    def setup_system_paths(self):
        """
        Set up some system paths.
        """
        self.python = sys.executable
        self.script_path = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.abspath(self.args.config)
        self._print_verbose('System paths:')
        self._print_verbose('   {:.<20}: {}'.format('python: ', self.python))
        self._print_verbose('   {:.<20}: {}'.format('script: ', self.script_path))
        self._print_verbose('   {:.<20}: {}'.format('config: ', self.config_path))

    def setup_executables(self):
        """
        Set up the paths to the executables we use.
        """
        self._print_verbose('Executables:')
        for executable in self.config.options('executables'):
            path = self.config.get('executables', executable)
            if not path.strip():
                path = None
            else:
                path = _which(path)
            setattr(self, '{exe}_exe'.format(exe=executable), path)
            self._print_verbose('   {exe:.<20} {path}'.format(exe=executable + ': ', path=path))

    def setup_paths(self):
        """
        Set up a variety of paths that we use throughout the build process.
        """
        self._print_verbose('Paths:')
        for name in self.config.options('paths'):
            path = os.path.abspath(self.config.get('paths', name))
            setattr(self, '{name}_path'.format(name=name), path)
            self._print_verbose('   {name:.<20} {path}'.format(name=name + ': ', path=path))
        # Make any command line options override the config file
        if self.args.branch:
            self.branch_path = os.path.abspath(self.args.branch)
        if self.args.release:
            self.version = self.args.release
        else:
            self.version = None
        if self.args.release and self.args.can_export:
            self.work_path = os.path.abspath(os.path.join(self.branch_path, '..', 'OpenLP-' + self.version))
        else:
            self.work_path = self.branch_path
        self.openlp_script = os.path.abspath(os.path.join(self.work_path, 'openlp', '__main__.py'))
        self.source_path = os.path.join(self.work_path, 'openlp')
        self.i18n_utils = os.path.join(self.work_path, 'scripts', 'translation_utils.py')
        self.i18n_path = os.path.join(self.work_path, 'resources', 'i18n')
        self.build_path = os.path.join(self.work_path, 'build')
        # Print out all the values
        self._print_verbose('   {:.<20} {}'.format('openlp script: ', self.openlp_script))
        self._print_verbose('   {:.<20} {}'.format('source: ', self.source_path))
        self._print_verbose('   {:.<20} {}'.format('i18n utils: ', self.i18n_utils))
        self._print_verbose('   {:.<20} {}'.format('i18n path: ', self.i18n_path))
        self._print_verbose('   {:.<20} {}'.format('build path: ', self.build_path))
        self._print_verbose('Overrides:')
        self._print_verbose('   {:.<20} {}'.format('branch **: ', self.branch_path))
        self._print_verbose('   {:.<20} {}'.format('version: ', self.version))
        self._print_verbose('   {:.<20} {}'.format('work path: ', self.work_path))

    def setup_extra(self):
        """
        Extra setup to run
        """
        pass

    def update_code(self):
        """
        Update the code in the branch.
        """
        self._print('Reverting any changes to the code...')
        self._git('reset', self.branch_path, ['--hard'], err_msg='Error reverting the code')
        self._print('Cleaning any extra files...')
        self._git('clean', self.branch_path, ['--quiet', '--force', '-d'],
                  err_msg='Error cleaning up extra files')
        self._print('Updating the code...')
        self._git('pull', self.branch_path, ['--rebase'], err_msg='Error updating the code')

    def export_release(self):
        """
        Export a particular release
        """
        if os.path.exists(self.work_path):
            rmtree(self.work_path)
        self._print('Exporting the release version...')
        # Note that it is very important that the prefix ends with a slash to get the files into the folder
        self._git('checkout-index', self.branch_path, ['-f', '-a', '--prefix={folder}/'.format(folder=self.work_path)],
                  'Error exporting the code')

    def get_extra_parameters(self):
        """
        Return a list of any extra parameters we wish to use
        """
        return []

    def run_pyinstaller(self):
        """
        Run PyInstaller on the branch to build an executable.
        """
        self._print('Running PyInstaller...')
        os.chdir(self.work_path)
        cmd = ['pyinstaller'
               '--clean',
               '--noconfirm',
               '--windowed',
               '--noupx',
               '--additional-hooks-dir', self.hooks_path,
               '--runtime-hook', os.path.join(self.hooks_path, 'rthook_ssl.py'),
               # Import to make sqlalchemy work.
               # Can't be in the custom hook folder because it will conflict with PyInstallers hook
               '--hidden-import', 'sqlalchemy.ext.baked',
               '-i', self.icon_path,
               '-n', 'OpenLP',
               *self.get_extra_parameters(),  # Adds any extra parameters we wish to use
               self.openlp_script
               ]
        if self.args.verbose:
            cmd.append('--log-level=DEBUG')
        else:
            cmd.append('--log-level=ERROR')
        if self.args.debug:
            cmd.append('-d')
        self._run_module('PyInstaller', cmd, 'Error running PyInstaller', run_name='__main__')

    def write_version_file(self):
        """
        Write the version number to a file for reading once installed.
        """
        self._print('Writing version file...')
        if not self.args.release:
            if self.args.tag_override:
                self.version = self.args.tag_override
            else:
                # This is a development build, get the version info based on tags
                git_version = self._git('describe', self.branch_path, ['--tags'], err_msg='Error running git describe')
                if not git_version or len(git_version.strip()) == 0:
                    self.version = '0.0.0'
                else:
                    self.version = '+'.join(git_version.strip().rsplit('-g', 1))
                    self.version = '.dev'.join(self.version.rsplit('-', 1))
        try:
            os.makedirs(self.dist_path)
        except FileExistsError:
            pass
        # Write the version to the version file
        with open(os.path.join(self.dist_path, '.version'), 'w') as version_file:
            version_file.write(str(self.version))

    def copy_default_theme(self):
        """
        Copy the default theme to the correct directory for OpenLP.
        """
        self._print('Copying default theme...')
        source = os.path.join(self.source_path, 'core', 'lib', 'json')
        dest = os.path.join(self.dist_path, 'core', 'lib', 'json')
        for root, _, files in os.walk(source):
            for filename in files:
                if filename.endswith('.json'):
                    dest_path = os.path.join(dest, root[len(source) + 1:])
                    if not os.path.exists(dest_path):
                        os.makedirs(dest_path)
                    self._print_verbose('... %s', filename)
                    copy(os.path.join(root, filename), os.path.join(dest_path, filename))

    def copy_plugins(self):
        """
        Copy all the plugins to the correct directory so that OpenLP sees that
        it has plugins.
        """
        self._print('Copying plugins...')
        source = os.path.join(self.source_path, 'plugins')
        dest = os.path.join(self.dist_path, 'plugins')
        for root, _, files in os.walk(source):
            for filename in files:
                if not filename.endswith('.pyc'):
                    dest_path = os.path.join(dest, root[len(source) + 1:])
                    if not os.path.exists(dest_path):
                        os.makedirs(dest_path)
                    self._print_verbose('... %s', filename)
                    copy(os.path.join(root, filename), os.path.join(dest_path, filename))

    def copy_media_player(self):
        """
        Copy the media players to the correct directory for OpenLP.
        """
        self._print('Copying media player...')
        source = os.path.join(self.source_path, 'core', 'ui', 'media')
        dest = os.path.join(self.dist_path, 'core', 'ui', 'media')
        for root, _, files in os.walk(source):
            for filename in files:
                if not filename.endswith('.pyc'):
                    dest_path = os.path.join(dest, root[len(source) + 1:])
                    if not os.path.exists(dest_path):
                        os.makedirs(dest_path)
                    self._print_verbose('... %s', filename)
                    copy(os.path.join(root, filename), os.path.join(dest_path, filename))

    def copy_font_files(self):
        """
        Copy OpenLP font files
        """
        self._print('Copying OpenLP fonts files...')
        src_dir = os.path.join(self.source_path, 'core', 'ui', 'fonts')
        dst_dir = os.path.join(self.dist_path, 'core', 'ui', 'fonts')
        font_files = ['OpenLP.ttf', 'openlp-charmap.json']
        try:
            os.makedirs(dst_dir)
        except FileExistsError:
            pass
        for font_file in font_files:
            src = os.path.join(src_dir, font_file)
            dst = os.path.join(dst_dir, font_file)
            copy(src, dst)

    def copy_display_files(self):
        """
        Copy OpenLP display HTML files
        """
        self._print('Copying OpenLP HTML display files...')
        src_dir = os.path.join(self.source_path, 'core', 'display', 'html')
        dst_dir = os.path.join(self.dist_path, 'core', 'display', 'html')
        try:
            os.makedirs(dst_dir)
        except FileExistsError:
            pass
        for display_file in os.listdir(src_dir):
            src = os.path.join(src_dir, display_file)
            dst = os.path.join(dst_dir, display_file)
            copy(src, dst)

    def copy_extra_files(self):
        """
        Copy any extra files which are particular to a platform
        """
        pass

    def update_translations(self):
        """
        Update the translations.
        """
        self._print('Updating translations...')
        username = None
        password = None
        if self.args.transifex_user:
            username = self.args.transifex_user
        if self.args.transifex_password:
            password = self.args.transifex_pass
        if (not username or not password) and not self.config.has_section('transifex'):
            raise Exception('No section named "transifex" found.')
        elif not username and not self.config.has_option('transifex', 'username'):
            raise Exception('No option named "username" found.')
        elif not password and not self.config.has_option('transifex', 'password'):
            raise Exception('No option named "password" found.')
        if not username:
            username = self.config.get('transifex', 'username')
        if not password:
            password = self.config.get('transifex', 'password')
        os.chdir(os.path.split(self.i18n_utils)[0])
        self._run_command([self.python, self.i18n_utils, '-qdpu', '-U', username, '-P', password],
                          err_msg='Error running translation_utils.py')

    def compile_translations(self):
        """
        Compile the translations for Qt.
        """
        self._print('Compiling translations...')
        if not os.path.exists(os.path.join(self.dist_path, 'i18n')):
            os.makedirs(os.path.join(self.dist_path, 'i18n'))
        for filename in os.listdir(self.i18n_path):
            if filename.endswith('.ts'):
                self._print_verbose('... %s', filename)
                source_path = os.path.join(self.i18n_path, filename)
                dest_path = os.path.join(self.dist_path, 'i18n', filename.replace('.ts', '.qm'))
                lrelease_command = ('pyside6-lrelease', '-compress', source_path, '-qm', dest_path)
                self._run_command(lrelease_command,
                                  err_msg='Error running lconvert on %s' % source_path)
        self._print('Copying Qt translation files...')
        source = self.get_qt_translations_path()
        for filename in os.listdir(source):
            if filename.startswith('qt') and filename.endswith('.qm'):
                self._print_verbose('... %s', filename)
                copy(os.path.join(source, filename), os.path.join(self.dist_path, 'i18n', filename))

    def build_package(self):
        """
        Actually package the resultant build
        """
        pass

    def main(self):
        """
        The main function to run the builder.
        """
        self._print_verbose('OpenLP main script: ......%s', self.openlp_script)
        self._print_verbose('Script path: .............%s', self.script_path)
        self._print_verbose('Branch path: .............%s', self.branch_path)
        self._print_verbose('')
        if not self.args.skip_update:
            self.update_code()
        if self.args.release and self.args.can_export:
            self.export_release()
        self.run_pyinstaller()
        self.write_version_file()
        self.copy_default_theme()
        self.copy_plugins()
        self.copy_media_player()
        self.copy_font_files()
        self.copy_display_files()
        self.copy_extra_files()
        if not self.args.skip_translations:
            if self.args.update_translations:
                self.update_translations()
            self.compile_translations()
        self.build_package()

        self._print('Done.')
        raise SystemExit()
