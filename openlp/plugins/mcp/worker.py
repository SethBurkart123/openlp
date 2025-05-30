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
The :mod:`~openlp.plugins.mcp.worker` module contains the MCPWorker class
that handles all OpenLP operations for the MCP plugin.
"""

import logging
import threading
from pathlib import Path

from PySide6 import QtCore

from openlp.core.common.registry import Registry
from openlp.core.lib.serviceitem import ServiceItem
from openlp.core.ui.icons import UiIcons
from openlp.core.common.enum import ServiceItemType

from .conversion import ConversionWorker

log = logging.getLogger(__name__)


class MCPWorker(QtCore.QObject):
    """
    Worker class that handles MCP operations on the main thread using Qt signals/slots.
    This ensures all GUI operations happen on the correct thread.
    
    Note: PowerPoint conversion may cause temporary GUI responsiveness issues during
    LibreOffice subprocess execution, but MCP tools will wait for completion properly.
    """
    # Signals for different operations
    create_service_requested = QtCore.Signal()
    load_service_requested = QtCore.Signal(str)  # file_path
    save_service_requested = QtCore.Signal(str)  # file_path (optional)
    get_service_items_requested = QtCore.Signal()
    add_song_requested = QtCore.Signal(str, str, str)  # title, author, lyrics
    add_custom_slide_requested = QtCore.Signal(str, str)  # title, content
    add_media_requested = QtCore.Signal(str, str)  # file_path, title
    go_live_requested = QtCore.Signal(int)  # item_index
    next_slide_requested = QtCore.Signal()
    previous_slide_requested = QtCore.Signal()
    list_themes_requested = QtCore.Signal()
    set_theme_requested = QtCore.Signal(str)  # theme_name
    create_from_structure_requested = QtCore.Signal(object)  # service_structure
    
    # Result signals
    operation_completed = QtCore.Signal(object)  # result
    
    def __init__(self):
        super().__init__()
        self.current_result = None
        self.result_ready = threading.Event()
        
        # Setup background conversion worker and thread
        self.conversion_thread = None
        self.conversion_worker = None
        self.pending_conversion_title = None
        
        # Connect signals to slots
        self.create_service_requested.connect(self.create_service)
        self.load_service_requested.connect(self.load_service)
        self.save_service_requested.connect(self.save_service)
        self.get_service_items_requested.connect(self.get_service_items)
        self.add_song_requested.connect(self.add_song)
        self.add_custom_slide_requested.connect(self.add_custom_slide)
        self.add_media_requested.connect(self.add_media)
        self.go_live_requested.connect(self.go_live)
        self.next_slide_requested.connect(self.next_slide)
        self.previous_slide_requested.connect(self.previous_slide)
        self.list_themes_requested.connect(self.list_themes)
        self.set_theme_requested.connect(self.set_theme)
        self.create_from_structure_requested.connect(self.create_from_structure)
        
        self.operation_completed.connect(self._handle_result)
        
        # Automatically set slide limits to enable cross-item navigation
        self._configure_slide_navigation()
    
    def _handle_result(self, result):
        """Handle the result of an operation."""
        self.current_result = result
        self.result_ready.set()
    
    def wait_for_result(self, timeout=10):
        """Wait for an operation to complete and return the result."""
        self.result_ready.clear()
        if self.result_ready.wait(timeout):
            return self.current_result
        else:
            raise TimeoutError("Operation timed out")
    
    def wait_for_result_long(self, timeout=90):
        """Wait for a long operation (like PowerPoint conversion) to complete."""
        self.result_ready.clear()
        if self.result_ready.wait(timeout):
            return self.current_result
        else:
            raise TimeoutError("Long operation timed out")
    
    @QtCore.Slot()
    def create_service(self):
        try:
            service_manager = Registry().get('service_manager')
            service_manager.new_file()
            service_manager.repaint_service_list(-1, -1)
            self.operation_completed.emit("New service created successfully")
        except Exception as e:
            self.operation_completed.emit(f"Error creating new service: {str(e)}")
    
    @QtCore.Slot(str)
    def load_service(self, file_path):
        try:
            service_manager = Registry().get('service_manager')
            service_manager.load_file(Path(file_path))
            self.operation_completed.emit(f"Service loaded from {file_path}")
        except Exception as e:
            self.operation_completed.emit(f"Error loading service: {str(e)}")
    
    @QtCore.Slot(str)
    def save_service(self, file_path):
        try:
            service_manager = Registry().get('service_manager')
            if file_path:
                service_manager.set_file_name(Path(file_path))
            service_manager.decide_save_method()
            self.operation_completed.emit(f"Service saved{' to ' + file_path if file_path else ''}")
        except Exception as e:
            self.operation_completed.emit(f"Error saving service: {str(e)}")
    
    @QtCore.Slot()
    def get_service_items(self):
        try:
            service_manager = Registry().get('service_manager')
            items = []
            for item in service_manager.service_items:
                service_item = item['service_item']
                items.append({
                    'title': service_item.title,
                    'type': str(service_item.service_item_type),
                    'plugin': service_item.name,
                    'order': item['order']
                })
            self.operation_completed.emit(items)
        except Exception as e:
            self.operation_completed.emit([{"error": str(e)}])
    
    @QtCore.Slot(str, str, str)
    def add_song(self, title, author, lyrics):
        try:
            songs_plugin = Registry().get('plugin_manager').get_plugin_by_name('songs')
            if not songs_plugin or not songs_plugin.is_active():
                self.operation_completed.emit("Songs plugin not available")
                return
            
            # Simple song search by title
            from openlp.plugins.songs.lib.db import Song
            existing_songs = songs_plugin.manager.get_all_objects(Song, Song.title == title)
            
            if existing_songs:
                # Found existing song, use it
                song = existing_songs[0]
                try:
                    from PySide6.QtWidgets import QListWidgetItem
                    from PySide6.QtCore import Qt
                    mock_item = QListWidgetItem()
                    mock_item.setData(Qt.ItemDataRole.UserRole, song.id)
                    
                    media_item = songs_plugin.media_item
                    service_item = ServiceItem(songs_plugin)
                    service_item.add_icon()
                    
                    if media_item.generate_slide_data(service_item, item=mock_item):
                        service_manager = Registry().get('service_manager')
                        service_manager.add_service_item(service_item)
                        service_manager.repaint_service_list(-1, -1)
                        self.operation_completed.emit(f"Song '{song.title}' added from database")
                    else:
                        self._create_song_placeholder(songs_plugin, title, lyrics)
                        self.operation_completed.emit(f"Song '{title}' found but failed to load - added placeholder")
                except Exception:
                    self._create_song_placeholder(songs_plugin, title, lyrics)
                    self.operation_completed.emit(f"Song '{title}' found but failed to load - added placeholder")
            else:
                # No existing song, create placeholder
                self._create_song_placeholder(songs_plugin, title, lyrics)
                self.operation_completed.emit(f"Song '{title}' not found in database - added placeholder")
        except Exception as e:
            self.operation_completed.emit(f"Error adding song: {str(e)}")
    
    def _create_song_placeholder(self, songs_plugin, title, lyrics):
        """Helper method to create a song placeholder."""
        service_item = ServiceItem(songs_plugin)
        service_item.title = title
        service_item.name = 'songs'
        service_item.service_item_type = ServiceItemType.Text
        service_item.add_icon()
        
        if lyrics:
            verses = lyrics.split('\n\n')
            for verse in verses:
                if verse.strip():
                    service_item.add_from_text(verse.strip())
        else:
            service_item.add_from_text(f"Song: {title}\n\n(Lyrics not available)")
        
        service_manager = Registry().get('service_manager')
        service_manager.add_service_item(service_item)
        service_manager.repaint_service_list(-1, -1)
    
    @QtCore.Slot(str, str)
    def add_custom_slide(self, title, content):
        try:
            custom_plugin = Registry().get('plugin_manager').get_plugin_by_name('custom')
            service_item = ServiceItem(custom_plugin)
            service_item.title = title
            service_item.name = 'custom'
            service_item.service_item_type = ServiceItemType.Text
            service_item.add_icon()
            service_item.add_from_text(content)
            
            service_manager = Registry().get('service_manager')
            service_manager.add_service_item(service_item)
            service_manager.repaint_service_list(-1, -1)
            self.operation_completed.emit(f"Custom slide '{title}' added to service")
        except Exception as e:
            self.operation_completed.emit(f"Error adding custom slide: {str(e)}")
    
    @QtCore.Slot(str, str)
    def add_media(self, file_path, title):
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                self.operation_completed.emit(f"Error: File '{file_path}' not found")
                return
            
            # Detect media type
            extension = file_path.suffix.lower()
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.svg'}
            video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp'}
            audio_extensions = {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma'}
            presentation_extensions = {'.pdf', '.pptx', '.ppt', '.pps', '.ppsx', '.odp'}
            
            if extension in image_extensions:
                self._add_image(file_path, title)
            elif extension in video_extensions or extension in audio_extensions:
                self._add_video_audio(file_path, title, extension in video_extensions)
            elif extension in presentation_extensions:
                self._add_presentation(file_path, title)
            else:
                supported = f"images ({', '.join(sorted(image_extensions))}), videos ({', '.join(sorted(video_extensions))}), audio ({', '.join(sorted(audio_extensions))}), presentations ({', '.join(sorted(presentation_extensions))})"
                self.operation_completed.emit(f"Unsupported format: {extension}. Supported: {supported}")
                
        except Exception as e:
            self.operation_completed.emit(f"Error adding media: {str(e)}")
    
    def _add_image(self, file_path, title):
        """Add an image using the images plugin."""
        images_plugin = Registry().get('plugin_manager').get_plugin_by_name('images')
        if not images_plugin or not images_plugin.is_active():
            self.operation_completed.emit("Images plugin not available")
            return
        
        service_item = ServiceItem(images_plugin)
        service_item.title = title or file_path.name
        service_item.name = 'images'
        service_item.add_icon()
        
        # Use add_from_image for proper image handling
        service_item.add_from_image(file_path, file_path.name)
        
        # Set file hash for saving
        from openlp.core.common import sha256_file_hash
        service_item.sha256_file_hash = sha256_file_hash(file_path)
        
        # Add image capabilities
        from openlp.core.lib.serviceitem import ItemCapabilities
        service_item.add_capability(ItemCapabilities.CanMaintain)
        service_item.add_capability(ItemCapabilities.CanPreview)
        service_item.add_capability(ItemCapabilities.CanLoop)
        service_item.add_capability(ItemCapabilities.CanAppend)
        service_item.add_capability(ItemCapabilities.CanEditTitle)
        service_item.add_capability(ItemCapabilities.HasThumbnails)
        service_item.add_capability(ItemCapabilities.ProvidesOwnTheme)
        
        service_manager = Registry().get('service_manager')
        service_manager.add_service_item(service_item)
        service_manager.repaint_service_list(-1, -1)
        self.operation_completed.emit(f"Image '{service_item.title}' added to service")
    
    def _add_video_audio(self, file_path, title, is_video):
        """Add a video or audio file using the media plugin."""
        media_plugin = Registry().get('plugin_manager').get_plugin_by_name('media')
        if not media_plugin or not media_plugin.is_active():
            self.operation_completed.emit("Media plugin not available")
            return
        
        service_item = ServiceItem(media_plugin)
        service_item.title = title or file_path.name
        service_item.name = 'media'
        service_item.service_item_type = ServiceItemType.Command
        service_item.add_icon()
        
        # Use add_from_command for video/audio files
        service_item.add_from_command(str(file_path.parent), file_path.name, UiIcons().clapperboard)
        
        # Set processor and capabilities
        service_item.processor = 'qt6'
        from openlp.core.lib.serviceitem import ItemCapabilities
        service_item.add_capability(ItemCapabilities.CanAutoStartForLive)
        service_item.add_capability(ItemCapabilities.CanEditTitle)
        service_item.add_capability(ItemCapabilities.RequiresMedia)
        
        service_manager = Registry().get('service_manager')
        service_manager.add_service_item(service_item)
        service_manager.repaint_service_list(-1, -1)
        
        media_type = "video" if is_video else "audio"
        self.operation_completed.emit(f"{media_type.capitalize()} '{service_item.title}' added to service")
    
    def _add_presentation(self, file_path, title):
        """Add a presentation file, converting PowerPoint to PDF if needed."""
        try:
            extension = file_path.suffix.lower()
            
            # If it's a PowerPoint file, start background conversion
            if extension in ['.pptx', '.ppt', '.pps', '.ppsx']:
                self._start_powerpoint_conversion(file_path, title)
                return  # Will emit result when conversion completes
            
            # Handle PDF presentations directly (no conversion needed)
            self._add_pdf_presentation(file_path, title)
                
        except Exception as e:
            self.operation_completed.emit(f"Error adding presentation: {str(e)}")
            log.error(f"Presentation error details: {e}", exc_info=True)
    
    def _start_powerpoint_conversion(self, ppt_path, title):
        """Start PowerPoint conversion in background thread."""
        try:
            # Clean up any existing conversion thread
            if self.conversion_thread and self.conversion_thread.isRunning():
                self.conversion_thread.quit()
                self.conversion_thread.wait()
            
            # Store title for when conversion completes
            self.pending_conversion_title = title or f"{ppt_path.stem} (converted)"
            
            log.info(f"Starting PowerPoint conversion for: {ppt_path.name}")
            
            # Create new thread and worker
            self.conversion_thread = QtCore.QThread()
            self.conversion_worker = ConversionWorker()
            self.conversion_worker.moveToThread(self.conversion_thread)
            
            # Connect signals
            self.conversion_worker.conversion_completed.connect(self._on_conversion_completed)
            self.conversion_worker.conversion_failed.connect(self._on_conversion_failed)
            self.conversion_thread.started.connect(lambda: self.conversion_worker.convert_powerpoint(ppt_path, self.pending_conversion_title))
            
            # Start background conversion
            self.conversion_thread.start()
            
        except Exception as e:
            self.operation_completed.emit(f"Error starting PowerPoint conversion: {str(e)}")
    
    @QtCore.Slot(object, str)
    def _on_conversion_completed(self, pdf_path, title):
        """Handle successful PowerPoint conversion - add the PDF to service."""
        try:
            log.info(f"PowerPoint conversion completed, adding to service: {pdf_path}")
            
            # Conversion completed, now add the PDF to service on main thread
            self._add_pdf_presentation(pdf_path, title)
            
            # Clean up conversion thread
            self._cleanup_conversion_thread()
                
        except Exception as e:
            self.operation_completed.emit(f"Error adding converted presentation: {str(e)}")
    
    @QtCore.Slot(str)
    def _on_conversion_failed(self, error_message):
        """Handle failed PowerPoint conversion."""
        log.error(f"PowerPoint conversion failed: {error_message}")
        self.operation_completed.emit(error_message)
        
        # Clean up conversion thread
        self._cleanup_conversion_thread()
    
    def _cleanup_conversion_thread(self):
        """Clean up the conversion thread and worker."""
        if self.conversion_thread:
            self.conversion_thread.quit()
            self.conversion_thread.wait()
            self.conversion_thread = None
            self.conversion_worker = None
    
    def _add_pdf_presentation(self, file_path, title):
        """Add a PDF presentation to the service."""
        try:
            # Now handle as PDF presentation
            presentations_plugin = Registry().get('plugin_manager').get_plugin_by_name('presentations')
            if not presentations_plugin or not presentations_plugin.is_active():
                self.operation_completed.emit("Presentations plugin not available")
                return
            
            # Check if PDF controller is available
            if 'Pdf' not in presentations_plugin.controllers or not presentations_plugin.controllers['Pdf'].enabled():
                self.operation_completed.emit("PDF controller not available - please ensure PDF support is enabled")
                return
            
            controller = presentations_plugin.controllers['Pdf']
            
            # Create a presentation document
            doc = controller.add_document(file_path)
            if not doc:
                self.operation_completed.emit(f"Failed to create PDF document for: {file_path.name}")
                return
                
            if not doc.load_presentation():
                self.operation_completed.emit(f"Failed to load presentation: {file_path.name}")
                return
            
            # Create service item for presentation
            service_item = ServiceItem(presentations_plugin)
            service_item.title = title or file_path.name
            service_item.name = 'presentations'
            service_item.processor = 'Pdf'
            service_item.add_icon()
            
            # Set capabilities
            from openlp.core.lib.serviceitem import ItemCapabilities
            service_item.add_capability(ItemCapabilities.CanEditTitle)
            service_item.add_capability(ItemCapabilities.ProvidesOwnDisplay)
            service_item.add_capability(ItemCapabilities.HasThumbnails)
            
            # Get slide count with better error handling
            slide_count = 1  # Default fallback
            try:
                if hasattr(doc, 'get_slide_count'):
                    count = doc.get_slide_count()
                    if count is not None and count > 0:
                        slide_count = count
                elif hasattr(doc, 'get_page_count'):
                    count = doc.get_page_count()
                    if count is not None and count > 0:
                        slide_count = count
                elif hasattr(doc, 'pageCount'):
                    count = doc.pageCount()
                    if count is not None and count > 0:
                        slide_count = count
                else:
                    # Try to access slide_count attribute directly
                    if hasattr(doc, 'slide_count') and doc.slide_count:
                        slide_count = doc.slide_count
            except Exception as e:
                log.warning(f"Error getting slide count: {e}, using default")
                slide_count = 1
            
            # Add slides to service item
            if slide_count > 0:
                for i in range(1, slide_count + 1):
                    try:
                        thumbnail_path = doc.get_thumbnail_path(i, True) if hasattr(doc, 'get_thumbnail_path') else None
                        file_hash = doc.get_sha256_file_hash() if hasattr(doc, 'get_sha256_file_hash') else ""
                        
                        service_item.add_from_command(
                            str(file_path.parent), 
                            file_path.name, 
                            thumbnail_path or "", 
                            f"Slide {i}", 
                            "",
                            file_hash
                        )
                    except Exception as e:
                        log.warning(f"Error adding slide {i}: {e}")
                        # Add basic slide entry as fallback
                        try:
                            service_item.add_from_command(
                                str(file_path.parent), 
                                file_path.name, 
                                "", 
                                f"Slide {i}", 
                                "",
                                ""
                            )
                        except:
                            pass  # Skip this slide if it fails completely
                
                service_manager = Registry().get('service_manager')
                service_manager.add_service_item(service_item)
                service_manager.repaint_service_list(-1, -1)
                
                try:
                    doc.close_presentation()
                except:
                    pass
                    
                self.operation_completed.emit(f"Presentation '{service_item.title}' with {slide_count} slides added to service")
            else:
                try:
                    doc.close_presentation()
                except:
                    pass
                self.operation_completed.emit(f"No slides found in presentation: {file_path.name}")
                
        except Exception as e:
            self.operation_completed.emit(f"Error adding PDF presentation: {str(e)}")
            log.error(f"PDF presentation error details: {e}", exc_info=True)
    
    @QtCore.Slot(int)
    def go_live(self, item_index):
        try:
            service_manager = Registry().get('service_manager')
            # First select the item
            service_manager.set_item(item_index)
            # Then make it live
            service_manager.make_live()
            self.operation_completed.emit(f"Item {item_index} is now live")
        except Exception as e:
            self.operation_completed.emit(f"Error going live: {str(e)}")
    
    @QtCore.Slot()
    def next_slide(self):
        try:
            live_controller = Registry().get('live_controller')
            
            # Use OpenLP's built-in slide navigation which handles service item transitions
            # based on the slide_limits setting (End/Wrap/Next)
            live_controller.on_slide_selected_next()
            self.operation_completed.emit("Moved to next slide")
        except Exception as e:
            self.operation_completed.emit(f"Error moving to next slide: {str(e)}")
    
    @QtCore.Slot()
    def previous_slide(self):
        try:
            live_controller = Registry().get('live_controller')
            
            # Use OpenLP's built-in slide navigation which handles service item transitions
            # based on the slide_limits setting (End/Wrap/Next)
            live_controller.on_slide_selected_previous()
            self.operation_completed.emit("Moved to previous slide")
        except Exception as e:
            self.operation_completed.emit(f"Error moving to previous slide: {str(e)}")
    
    @QtCore.Slot()
    def list_themes(self):
        try:
            theme_manager = Registry().get('theme_manager')
            themes = theme_manager.get_theme_names()
            self.operation_completed.emit(themes)
        except Exception as e:
            self.operation_completed.emit([f"Error: {str(e)}"])
    
    @QtCore.Slot(str)
    def set_theme(self, theme_name):
        try:
            service_manager = Registry().get('service_manager')
            service_manager.service_theme = theme_name
            self.operation_completed.emit(f"Service theme set to '{theme_name}'")
        except Exception as e:
            self.operation_completed.emit(f"Error setting theme: {str(e)}")
    
    @QtCore.Slot(object)
    def create_from_structure(self, service_structure):
        try:
            service_manager = Registry().get('service_manager')
            service_manager.new_file()
            
            items_added = []
            for item_data in service_structure:
                item_type = item_data.get('type', 'custom')
                title = item_data.get('title', 'Untitled')
                content = item_data.get('content', '')
                
                if item_type == 'song':
                    self.add_song(title, item_data.get('author', ''), item_data.get('lyrics', content))
                    items_added.append(f"Song '{title}'")
                elif item_type == 'custom':
                    self.add_custom_slide(title, content)
                    items_added.append(f"Custom slide '{title}'")
                elif item_type == 'media':
                    file_path = item_data.get('file_path')
                    if file_path:
                        self.add_media(file_path, title)
                        items_added.append(f"Media '{title}'")
            
            service_manager.repaint_service_list(-1, -1)
            self.operation_completed.emit(f"Service created with {len(service_structure)} items: " + ", ".join(items_added))
        except Exception as e:
            self.operation_completed.emit(f"Error creating service: {str(e)}")

    def _configure_slide_navigation(self):
        """Configure slide navigation to automatically move between service items."""
        try:
            from openlp.core.common.registry import Registry
            from openlp.core.common import SlideLimits
            
            settings = Registry().get('settings')
            settings.setValue('advanced/slide limits', SlideLimits.Next)
            
            # Update live controller if it exists
            try:
                live_controller = Registry().get('live_controller')
                live_controller.update_slide_limits()
                log.info('Slide navigation configured to move between service items')
            except:
                log.debug('Live controller not available yet')
                
        except Exception as e:
            log.warning(f'Could not configure slide navigation: {e}') 