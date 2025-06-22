# -*- coding: utf-8 -*-
# vim: autoindent shiftwidth=4 expandtab textwidth=120 tabstop=4 softtabstop=4

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
Flatpak Builder
===============

This is the script that builds the Flatpak

Requirements
------------

You will need the following requirements installed (these are the names of the Debian packages):

 - flatpak
 - flatpak builder
 - python3-requests
 - python3-requirements
 - python3-ruamel.yaml
 - python3-lxml

Running the script
------------------

If you're running this within the context of a GitLab CI pipeline, all you really need to do is provide the version
number to build. The script should pick up the environment variables present in job for the rest of the arguments.
For example:

.. code::

   python builders/flatpak-builder.py $CI_COMMIT_TAG


If you're running this outside of GitLab, you'll need te generate a private token for yourself, get the project ID of
the OpenLP repository, and run the script the following way:

.. code::

   python builders/flatpak-builder.py 3.1.6 --project 12345 --token gl1234abcd --token-type private


This generates a flatpak in the "flatpak" directory.
"""
import os
import sys
from argparse import ArgumentParser, Namespace
from hashlib import sha256
from pathlib import Path
from subprocess import run

import requests
from lxml import etree, objectify
from ruamel.yaml import YAML


FPG_URL = 'https://raw.githubusercontent.com/flatpak/flatpak-builder-tools/master/pip/flatpak-pip-generator'
IGNORE_VERSIONS = ['3.1.5', '3.1.4', '3.1.0', '3.1.0rc4', '3.1.0rc3', '3.1.0rc2', '3.1.0rc1', '3.0.2', '3.0.1',
                   '3.0.0', '2.9.5', '2.9.4', '2.9.3', '2.9.2', '2.9.1', '2.9.0']


def parse_args() -> Namespace:
    """Parse the command line arguments"""
    parser = ArgumentParser()
    parser.add_argument('version', help='The version to build a Flatpak for')
    parser.add_argument('--project', '-p', help='The project ID from GitLab')
    parser.add_argument('--token', '-t', help='The GitLab API token for authentication')
    parser.add_argument('--token-type', default='ci', help='The type of token, "ci" or "private", defaults to "ci"')
    parser.add_argument('--bundle', '-b', default='1', help='The bundle number, defaults to 1')
    return parser.parse_args()


def get_base_path() -> Path:
    """Return the base path of the repository"""
    return Path(__file__).parent.joinpath('..').absolute()


def get_yaml():
    """Return a standardised YAML object"""
    yaml = YAML(pure=True)
    yaml.sequence_indent = 4                                                    # type: ignore[assignment]
    yaml.sequence_dash_offset = 2
    yaml.explicit_start = False                                                 # type: ignore[assignment]
    return yaml


def use_environment(args: Namespace):
    """Populate the args object with environment variables"""
    if not args.token and os.environ.get('CI_JOB_TOKEN'):
        args.token = os.environ['CI_JOB_TOKEN']
    if not args.project and os.environ.get('CI_PROJECT_ID'):
        args.project = os.environ['CI_PROJECT_ID']


def get_releases(project_id: str, api_token: str, token_type: str) -> list[tuple[str, str, str]]:
    """Get the list of releases and their dates from GitLab

    :param project_id: The GitLab project ID
    :param api_token: The API token to authenticate this request against the API
    :return: A list of tuples, in the format (tag, date, link-to-tarball)
    """
    releases = []
    headers = {}
    if token_type == 'private':
        headers['PRIVATE-TOKEN'] = api_token
    else:
        headers['JOB-TOKEN'] = api_token
    response = requests.get(f'https://gitlab.com/api/v4/projects/{project_id}/releases', headers=headers)
    if response.status_code == 200:
        for release in response.json():
            asset_url = ''
            for asset in release['assets']['sources']:
                if asset['format'] == 'tar.gz':
                    asset_url = asset['url']
                    break
            releases.append((release['tag_name'], release['released_at'][:10], asset_url))
    else:
        print(response.text)
    return releases


def get_version_url(version: str, releases: list[tuple]) -> str:
    """Loop through the releases and get the link to the tarball for the selected version"""
    for (tag, date, url) in releases:
        if tag == version:
            return url
    return ''


def download_and_get_hash(version_url: str) -> str:
    """Download the file and generate a hash"""
    hasher = sha256()
    with requests.get(version_url, stream=True) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def update_appdata_xml(releases: list[tuple]) -> bool:
    """Update the releases in the appdata XML"""
    appdata_file = get_base_path().joinpath('flatpak', 'org.openlp.OpenLP.appdata.xml')
    el = objectify.E
    with appdata_file.open('r') as fd:
        xml = objectify.parse(fd)
    component = xml.getroot()
    component.releases.clear()
    for release in releases:
        if release[0] in IGNORE_VERSIONS:
            continue
        component.releases.append(el.release(version=f'{release[0]}-1', date=release[1]))
    objectify.deannotate(component, cleanup_namespaces=True)
    with appdata_file.open('w') as fd:
        fd.write(etree.tostring(component, encoding='utf8', xml_declaration=True, pretty_print=True).decode('utf8'))
    return True


def update_build_yml(version: str, version_url: str, sha256_hash: str) -> bool:
    """Build the YAML file needed to build the flatpak"""
    yaml = get_yaml()
    build_file = get_base_path().joinpath('flatpak', 'org.openlp.OpenLP.yml')
    with build_file.open('r') as fd:
        openlp_yml = yaml.load(fd)
    for module in openlp_yml['modules']:
        if isinstance(module, dict) and module['name'] == 'OpenLP':
            for source in module['sources']:
                if source['type'] == 'archive':
                    source['url'] = version_url
                    source['sha256'] = sha256_hash
    yaml.dump(openlp_yml, build_file)
    return True


def build_flatpak(version: str, bundle: str):
    """Build the flatpak"""
    base_path = get_base_path()
    response = requests.get(FPG_URL)
    fpg_path = base_path.joinpath('flatpak', 'flatpak-pip-generator')
    with fpg_path.open('w') as fpg:
        fpg.write(response.text)
    result = run([sys.executable, str(fpg_path), '--requirements-file', 'requirements.txt'],
                 cwd=str(base_path / 'flatpak'))
    if result.returncode != 0:
        return False
    result = run(['flatpak-builder', '--user', '--install', '--force-clean', '--repo=repo', 'build',
                  'org.openlp.OpenLP.yml'], cwd=str(base_path / 'flatpak'))
    if result.returncode != 0:
        return False
    result = run(['flatpak', 'build-bundle', 'repo', f'openlp-{version}-{bundle}.flatpak', 'org.openlp.OpenLP'],
                 cwd=str(base_path / 'flatpak'))
    if result.returncode != 0:
        return False


def main() -> int:
    """The main entrypoint for the script"""
    args = parse_args()
    use_environment(args)
    releases = get_releases(args.project, args.token, args.token_type)
    if not releases:
        print(f'No releases found for project "{args.project}", aborting...')
        return 1
    version_url = get_version_url(args.version, releases)
    if not version_url:
        print(f'No URL found for version "{args.version}", aborting...')
        return 2
    sha256_hash = download_and_get_hash(version_url)
    if not sha256_hash:
        print(f'Unable to download "{version_url}" to generate hash, aborting...')
        return 3
    if not update_appdata_xml(releases):
        print('Unable to update the appdata XML file, aborting...')
        return 4
    if not update_build_yml(args.version, version_url, sha256_hash):
        print('Unable to build YAML file, aborting...')
        return 5
    if not build_flatpak(args.version, args.bundle):
        return 6
    return 0


if __name__ == '__main__':
    sys.exit(main())
