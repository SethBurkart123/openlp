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
The :mod:`upgrade` module provides the migration path for the OLP Paths database
"""
import json
import logging
import shutil
from pathlib import Path

from sqlalchemy import Column, ForeignKey, MetaData, Table, inspect, select, func
from sqlalchemy.orm import Session
from sqlalchemy.types import Integer, Unicode

from openlp.core.common import sha256_file_hash
from openlp.core.common.applocation import AppLocation
from openlp.core.common.json import OpenLPJSONEncoder, OpenLPJSONDecoder
from openlp.core.db.types import PathType
from openlp.core.db.upgrades import get_upgrade_op


log = logging.getLogger(__name__)
__version__ = 4


def upgrade_1(session: Session, metadata: MetaData):
    """
    Version 1 upgrade - old db might/might not be versioned.
    """
    log.debug('Skipping upgrade_1 of files DB - not used')


def upgrade_2(session: Session, metadata: MetaData):
    """
    Version 2 upgrade - Move file path from old db to JSON encoded path to new db. Added during 2.5 dev
    """
    log.debug('Starting upgrade_2 for file_path to JSON')
    op = get_upgrade_op(session)
    conn = op.get_bind()
    # Check if the table exists
    table_names = inspect(conn).get_table_names()
    if 'image_filenames' not in table_names:
        # Bypass this upgrade, it has already been performed
        return
    images_table = Table('image_filenames', metadata, extend_existing=True, autoload_with=metadata.bind)
    if 'file_path' not in [col.name for col in images_table.c.values()]:
        with op.batch_alter_table('image_filenames') as batch_op:
            batch_op.add_column(Column('file_path', PathType()))
        # Refresh the table definition
        images_table = Table('image_filenames', metadata, extend_existing=True, autoload_with=metadata.bind)
        conn = op.get_bind()
        results = conn.execute(select(images_table))
        data_path = AppLocation.get_data_path()
        for row in results.fetchall():
            file_path_json = json.dumps(Path(row.filename), cls=OpenLPJSONEncoder, base_path=data_path)
            conn.execute(images_table.update().where(images_table.c.id == row.id).values(file_path=file_path_json))
        # Drop old columns
        with op.batch_alter_table('image_filenames') as batch_op:
            # if metadata.bind.url.get_dialect().name != 'sqlite':
            #     for fk in old_table.foreign_keys:
            #         batch_op.drop_constraint(fk.name, 'foreignkey')
            batch_op.drop_column('filename')
    del images_table


def upgrade_3(session: Session, metadata: MetaData):
    """
    Version 3 upgrade - add sha256 hash
    """
    log.debug('Starting upgrade_3 for adding sha256 hashes')
    op = get_upgrade_op(session)
    conn = op.get_bind()
    # Check if the table exists
    table_names = inspect(conn).get_table_names()
    if 'image_filenames' not in table_names:
        # Bypass this upgrade, it has already been performed
        return
    images_table = Table('image_filenames', metadata, extend_existing=True, autoload_with=metadata.bind)
    if 'file_hash' not in [col.name for col in images_table.c.values()]:
        op = get_upgrade_op(session)
        with op.batch_alter_table('image_filenames') as batch_op:
            batch_op.add_column(Column('file_hash', Unicode(128)))
        conn = op.get_bind()
        results = conn.execute(select(images_table))
        thumb_path = AppLocation.get_data_path() / 'images' / 'thumbnails'
        for row in results.fetchall():
            file_path = json.loads(row.file_path, cls=OpenLPJSONDecoder)
            if file_path.exists():
                hash_ = sha256_file_hash(file_path)
            else:
                log.warning('{image} does not exists, so no sha256 hash added.'.format(image=str(file_path)))
                # set a fake "hash" to allow for the upgrade to go through. The image will be marked as invalid
                hash_ = None
            conn.execute(images_table.update().where(images_table.c.id == row.id).values(file_hash=hash_))
            # rename thumbnail to use file hash
            ext = file_path.suffix.lower()
            old_thumb = thumb_path / '{name:d}{ext}'.format(name=row.id, ext=ext)
            new_thumb = thumb_path / '{name:s}{ext}'.format(name=hash_, ext=ext)
            try:
                shutil.move(old_thumb, new_thumb)
            except OSError:
                log.exception('Failed in renaming image thumb from {oldt} to {newt}'.format(oldt=old_thumb,
                                                                                            newt=new_thumb))
    del images_table


def upgrade_4(session: Session, metadata: MetaData):
    """
    Version 4 upgrade - convert to the common folders/items model
    """
    log.debug('Starting upgrade_4 for converting to common folders/items model')
    op = get_upgrade_op(session)
    conn = op.get_bind()
    # Check if the folder table exists
    table_names = inspect(conn).get_table_names()
    if 'image_groups' not in table_names:
        # Bypass this upgrade, it has already been performed
        return
    # Get references to the old tables
    old_folder_table = Table('image_groups', metadata, extend_existing=True, autoload_with=metadata.bind)
    old_item_table = Table('image_filenames', metadata, extend_existing=True, autoload_with=metadata.bind)
    # Create the new tables
    if 'folder' not in table_names:
        new_folder_table = op.create_table(
            'folder',
            Column('id', Integer, primary_key=True),
            Column('name', Unicode(255), nullable=False, index=True),
            Column('parent_id', Integer, ForeignKey('folder.id'))
        )
    else:
        new_folder_table = Table('folder', metadata, autoload_with=metadata.bind)
    if 'item' not in table_names:
        new_item_table = op.create_table(
            'item',
            Column('id', Integer, primary_key=True),
            Column('name', Unicode(255), nullable=False, index=True),
            Column('file_path', Unicode(255)),
            Column('file_hash', Unicode(255)),
            Column('folder_id', Integer)
        )
    else:
        new_item_table = Table('item', metadata, autoload_with=metadata.bind)
    # Bulk insert all the data from the old tables to the new tables
    # - Preserve folder IDs only when the folder table is empty.
    # - Insert items without explicit IDs to avoid PK collisions.
    # - If target tables already have rows, skip inserting to avoid duplicates on reruns.

    # Insert folders if none exist yet
    folder_count = conn.execute(select(func.count()).select_from(new_folder_table)).scalar()
    if folder_count == 0:
        folders = []
        for old_folder in conn.execute(old_folder_table.select()).fetchall():
            folders.append({
                'id': old_folder.id,
                'name': old_folder.group_name,
                'parent_id': old_folder.parent_id if getattr(old_folder, 'parent_id', 0) != 0 else None
            })
        if folders:
            op.bulk_insert(new_folder_table, folders)

    # Insert items if none exist yet; do not specify 'id' to avoid PK conflicts
    item_count = conn.execute(select(func.count()).select_from(new_item_table)).scalar()
    if item_count == 0:
        items = []
        for old_item in conn.execute(old_item_table.select()).fetchall():
            file_path = json.loads(old_item.file_path, cls=OpenLPJSONDecoder)
            items.append({
                'name': file_path.name,
                'file_path': str(file_path),
                'file_hash': old_item.file_hash,
                'folder_id': getattr(old_item, 'group_id', None)
            })
        if items:
            op.bulk_insert(new_item_table, items)
    # Remove the old tables
    del old_item_table
    del old_folder_table
    op.drop_table('image_filenames')
    op.drop_table('image_groups')
