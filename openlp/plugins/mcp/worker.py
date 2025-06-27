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
from .url_utils import resolve_file_path, is_url

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
    add_custom_slide_requested = QtCore.Signal(str, str)  # title, content
    add_custom_slides_requested = QtCore.Signal(str, list, str, int)  # title, slides, credits, position
    add_media_requested = QtCore.Signal(str, str, int)  # file_path, title, position
    go_live_requested = QtCore.Signal(int)  # item_index
    next_slide_requested = QtCore.Signal()
    previous_slide_requested = QtCore.Signal()
    list_themes_requested = QtCore.Signal()
    set_theme_requested = QtCore.Signal(str)  # theme_name
    create_from_structure_requested = QtCore.Signal(object)  # service_structure
    
    # Plugin search and add signals
    search_songs_requested = QtCore.Signal(str)  # text
    create_song_requested = QtCore.Signal(str, str, str)  # title, lyrics, author
    add_song_by_id_requested = QtCore.Signal(int, int)  # song_id, position
    
    # Theme management signals
    create_theme_requested = QtCore.Signal(object)  # theme_data
    get_theme_details_requested = QtCore.Signal(str)  # theme_name
    update_theme_requested = QtCore.Signal(object)  # update_data
    delete_theme_requested = QtCore.Signal(str)  # theme_name
    duplicate_theme_requested = QtCore.Signal(str, str)  # existing_theme_name, new_theme_name
    
    # Per-item theme management signals
    set_item_theme_requested = QtCore.Signal(int, str)  # item_index, theme_name
    get_item_theme_requested = QtCore.Signal(int)  # item_index
    
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
        self.add_custom_slide_requested.connect(self.add_custom_slide)
        self.add_custom_slides_requested.connect(self.add_custom_slides)
        self.add_media_requested.connect(self.add_media)
        self.go_live_requested.connect(self.go_live)
        self.next_slide_requested.connect(self.next_slide)
        self.previous_slide_requested.connect(self.previous_slide)
        self.list_themes_requested.connect(self.list_themes)
        self.set_theme_requested.connect(self.set_theme)
        self.create_from_structure_requested.connect(self.create_from_structure)
        
        # Connect plugin search and add signals
        self.search_songs_requested.connect(self.search_songs)
        self.create_song_requested.connect(self.create_song)
        self.add_song_by_id_requested.connect(self.add_song_by_id)
        
        # Connect theme management signals
        self.create_theme_requested.connect(self.create_theme)
        self.get_theme_details_requested.connect(self.get_theme_details)
        self.update_theme_requested.connect(self.update_theme)
        self.delete_theme_requested.connect(self.delete_theme)
        self.duplicate_theme_requested.connect(self.duplicate_theme)
        
        # Connect per-item theme management signals
        self.set_item_theme_requested.connect(self.set_item_theme)
        self.get_item_theme_requested.connect(self.get_item_theme)
        
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
            # Resolve the file path (download if it's a URL)
            resolved_path = resolve_file_path(file_path)
            
            service_manager = Registry().get('service_manager')
            service_manager.load_file(resolved_path)
            
            if is_url(file_path):
                self.operation_completed.emit(f"Service downloaded from {file_path} and loaded successfully")
            else:
                self.operation_completed.emit(f"Service loaded from {file_path}")
        except Exception as e:
            self.operation_completed.emit(f"Error loading service: {str(e)}")
            log.error(f"Error loading service from {file_path}: {e}", exc_info=True)
    
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
    
    @QtCore.Slot(str, list, str, int)
    def add_custom_slides(self, title, slides, credits, position):
        try:
            custom_plugin = Registry().get('plugin_manager').get_plugin_by_name('custom')
            if not custom_plugin or not custom_plugin.is_active():
                self.operation_completed.emit("Custom plugin not available")
                return
            
            # Import required classes
            from openlp.plugins.custom.lib.customxmlhandler import CustomXML
            from openlp.plugins.custom.lib.db import CustomSlide
            
            # Create the XML content with multiple slides
            custom_xml = CustomXML()
            custom_xml.add_title_and_credit(title, credits)
            
            # Add each slide as a verse
            for i, slide_content in enumerate(slides, 1):
                custom_xml.add_verse_to_lyrics('custom', i, slide_content)
            
            # Get the XML string
            xml_content = custom_xml._dump_xml().decode('utf-8')
            
            # Create and save the custom slide to database
            manager = custom_plugin.db_manager
            custom_slide = CustomSlide()
            custom_slide.title = title
            custom_slide.text = xml_content
            custom_slide.credits = credits
            
            if manager.save_object(custom_slide):
                # Now create a service item using the saved custom slide
                service_item = ServiceItem(custom_plugin)
                service_item.title = title
                service_item.name = 'custom'
                service_item.service_item_type = ServiceItemType.Text
                service_item.add_icon()
                
                # Add each slide to the service item
                for slide_content in slides:
                    service_item.add_from_text(slide_content)
                
                # Set the database ID for the service item
                service_item.item_id = custom_slide.id
                service_item.edit_id = custom_slide.id
                service_item.credits = credits
                
                # Add capabilities
                from openlp.core.lib.serviceitem import ItemCapabilities
                service_item.add_capability(ItemCapabilities.CanEdit)
                service_item.add_capability(ItemCapabilities.CanPreview)
                service_item.add_capability(ItemCapabilities.CanLoop)
                service_item.add_capability(ItemCapabilities.CanSoftBreak)
                service_item.add_capability(ItemCapabilities.OnLoadUpdate)
                service_item.add_capability(ItemCapabilities.CanWordSplit)
                
                service_manager = Registry().get('service_manager')
                if position == -1:
                    service_manager.add_service_item(service_item)
                else:
                    service_manager.add_service_item(service_item, replace=False, position=position)
                service_manager.repaint_service_list(-1, -1)
                
                self.operation_completed.emit(f"Custom slides '{title}' with {len(slides)} slides added to service and database")
            else:
                self.operation_completed.emit(f"Error saving custom slide '{title}' to database")
                
        except Exception as e:
            self.operation_completed.emit(f"Error adding custom slides: {str(e)}")
            log.error(f"Error in add_custom_slides: {e}", exc_info=True)
    
    @QtCore.Slot(str, str, int)
    def add_media(self, file_path, title, position):
        try:
            # Get MCP plugin settings for video downloads
            settings = Registry().get('settings')
            video_quality = settings.value('mcp/video_quality')
            download_location = settings.value('mcp/download_location')
            
            # Set custom download directory if specified
            temp_dir = None
            if download_location and download_location.strip():
                from pathlib import Path
                temp_dir = Path(download_location)
            
            # Resolve the file path (download if it's a URL)
            resolved_path = resolve_file_path(file_path, temp_dir=temp_dir, quality=video_quality)
            
            # Detect media type
            extension = resolved_path.suffix.lower()
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.svg'}
            video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp'}
            audio_extensions = {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma'}
            presentation_extensions = {'.pdf', '.pptx', '.ppt', '.pps', '.ppsx', '.odp'}
            
            # Update title to indicate if it was downloaded
            if is_url(file_path) and not title:
                title = f"{resolved_path.name} (downloaded)"
            
            if extension in image_extensions:
                self._add_image(resolved_path, title, position)
            elif extension in video_extensions or extension in audio_extensions:
                self._add_video_audio(resolved_path, title, extension in video_extensions, position)
            elif extension in presentation_extensions:
                self._add_presentation(resolved_path, title, position)
            else:
                supported = f"images ({', '.join(sorted(image_extensions))}), videos ({', '.join(sorted(video_extensions))}), audio ({', '.join(sorted(audio_extensions))}), presentations ({', '.join(sorted(presentation_extensions))})"
                self.operation_completed.emit(f"Unsupported format: {extension}. Supported: {supported}")
                
        except Exception as e:
            self.operation_completed.emit(f"Error adding media: {str(e)}")
            log.error(f"Error adding media from {file_path}: {e}", exc_info=True)
    
    def _add_image(self, file_path, title, position):
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
        if position == -1:
            service_manager.add_service_item(service_item)
        else:
            service_manager.add_service_item(service_item, replace=False, position=position)
        service_manager.repaint_service_list(-1, -1)
        self.operation_completed.emit(f"Image '{service_item.title}' added to service")
    
    def _add_video_audio(self, file_path, title, is_video, position):
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
        if position == -1:
            service_manager.add_service_item(service_item)
        else:
            service_manager.add_service_item(service_item, replace=False, position=position)
        service_manager.repaint_service_list(-1, -1)
        
        media_type = "video" if is_video else "audio"
        self.operation_completed.emit(f"{media_type.capitalize()} '{service_item.title}' added to service")
    
    def _add_presentation(self, file_path, title, position):
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

    # Theme Management Methods
    @QtCore.Slot(object)
    def create_theme(self, theme_data):
        """Create a new theme with the specified properties."""
        try:
            from openlp.core.lib.theme import Theme, BackgroundType, BackgroundGradientType
            from openlp.core.common.registry import Registry
            
            theme_name = theme_data['theme_name']
            theme_manager = Registry().get('theme_manager')
            
            # Check if theme already exists
            if theme_name in theme_manager.get_theme_names():
                self.operation_completed.emit(f"Theme '{theme_name}' already exists")
                return
            
            # Create new theme
            theme = Theme()
            theme.theme_name = theme_name
            
            # Set background properties
            background_type = theme_data.get('background_type', 'solid')
            if background_type == 'solid':
                theme.background_type = BackgroundType.to_string(BackgroundType.Solid)
                theme.background_color = theme_data.get('background_color', '#000000')
            elif background_type == 'gradient':
                theme.background_type = BackgroundType.to_string(BackgroundType.Gradient)
                theme.background_start_color = theme_data.get('background_start_color', '#000000')
                theme.background_end_color = theme_data.get('background_end_color', '#000000')
                theme.background_direction = BackgroundGradientType.to_string(
                    BackgroundGradientType.Vertical if theme_data.get('background_direction', 'vertical') == 'vertical'
                    else BackgroundGradientType.Horizontal
                )
            elif background_type == 'image' and theme_data.get('background_image_path'):
                theme.background_type = BackgroundType.to_string(BackgroundType.Image)
                
                # Resolve the background image path (download if it's a URL)
                image_path = theme_data['background_image_path']
                try:
                    resolved_image_path = resolve_file_path(image_path)
                    # Convert to Path object as expected by OpenLP theme system
                    from pathlib import Path
                    resolved_path = Path(resolved_image_path)
                    theme.background_source = resolved_path
                    theme.background_filename = resolved_path
                    
                    if is_url(image_path):
                        log.info(f"Downloaded background image from {image_path} to {resolved_image_path}")
                except Exception as e:
                    self.operation_completed.emit(f"Error downloading background image from {image_path}: {str(e)}")
                    return
            
            # Set font properties
            theme.font_main_name = theme_data.get('font_main_name', 'Arial')
            theme.font_main_size = theme_data.get('font_main_size', 40)
            theme.font_main_color = theme_data.get('font_main_color', '#FFFFFF')
            theme.font_main_bold = theme_data.get('font_main_bold', False)
            theme.font_main_italics = theme_data.get('font_main_italics', False)
            theme.font_main_outline = theme_data.get('font_main_outline', False)
            theme.font_main_outline_color = theme_data.get('font_main_outline_color', '#000000')
            theme.font_main_outline_size = theme_data.get('font_main_outline_size', 2)
            theme.font_main_shadow = theme_data.get('font_main_shadow', True)
            theme.font_main_shadow_color = theme_data.get('font_main_shadow_color', '#000000')
            theme.font_main_shadow_size = theme_data.get('font_main_shadow_size', 5)
            
            # Set footer font properties
            theme.font_footer_name = theme_data.get('font_footer_name', 'Arial')
            theme.font_footer_size = theme_data.get('font_footer_size', 12)
            theme.font_footer_color = theme_data.get('font_footer_color', '#FFFFFF')
            
            # Save the theme
            theme_manager.save_theme(theme)
            
            # Generate preview and refresh UI
            theme_manager.update_preview_images([theme_name])
            
            success_msg = f"Theme '{theme_name}' created successfully"
            if background_type == 'image' and theme_data.get('background_image_path') and is_url(theme_data['background_image_path']):
                success_msg += f" (background image downloaded from URL)"
            self.operation_completed.emit(success_msg)
            
        except Exception as e:
            self.operation_completed.emit(f"Error creating theme: {str(e)}")
            log.error(f"Error creating theme {theme_data.get('theme_name', 'unknown')}: {e}", exc_info=True)

    @QtCore.Slot(str)
    def get_theme_details(self, theme_name):
        """Get detailed information about a theme."""
        try:
            from openlp.core.common.registry import Registry
            
            theme_manager = Registry().get('theme_manager')
            theme_data = theme_manager.get_theme_data(theme_name)
            
            if not theme_data:
                self.operation_completed.emit(f"Theme '{theme_name}' not found")
                return
            
            details = {
                'theme_name': theme_data.theme_name,
                'background_type': theme_data.background_type,
                'background_color': getattr(theme_data, 'background_color', 'N/A'),
                'background_start_color': getattr(theme_data, 'background_start_color', 'N/A'),
                'background_end_color': getattr(theme_data, 'background_end_color', 'N/A'),
                'background_direction': getattr(theme_data, 'background_direction', 'N/A'),
                'background_filename': str(getattr(theme_data, 'background_filename', 'N/A')),
                'font_main_name': theme_data.font_main_name,
                'font_main_size': theme_data.font_main_size,
                'font_main_color': theme_data.font_main_color,
                'font_main_bold': theme_data.font_main_bold,
                'font_main_italics': theme_data.font_main_italics,
                'font_main_outline': theme_data.font_main_outline,
                'font_main_outline_color': theme_data.font_main_outline_color,
                'font_main_outline_size': theme_data.font_main_outline_size,
                'font_main_shadow': theme_data.font_main_shadow,
                'font_main_shadow_color': theme_data.font_main_shadow_color,
                'font_main_shadow_size': theme_data.font_main_shadow_size,
                'font_footer_name': theme_data.font_footer_name,
                'font_footer_size': theme_data.font_footer_size,
                'font_footer_color': theme_data.font_footer_color,
            }
            
            result = "Theme Details:\n" + "\n".join([f"{k}: {v}" for k, v in details.items()])
            self.operation_completed.emit(result)
            
        except Exception as e:
            self.operation_completed.emit(f"Error getting theme details: {str(e)}")

    @QtCore.Slot(object)
    def update_theme(self, theme_data):
        """Update properties of an existing theme."""
        try:
            from openlp.core.common.registry import Registry
            
            theme_name = theme_data['theme_name']
            updates_data = theme_data.get('updates', {})
            theme_manager = Registry().get('theme_manager')
            
            # Get existing theme
            theme = theme_manager.get_theme_data(theme_name)
            if not theme:
                self.operation_completed.emit(f"Theme '{theme_name}' not found")
                return
            
            # Handle special case for background_image_path
            if 'background_image_path' in updates_data and updates_data['background_image_path']:
                image_path = updates_data['background_image_path']
                try:
                    resolved_image_path = resolve_file_path(image_path)
                    # Convert to Path object as expected by OpenLP theme system
                    from pathlib import Path
                    resolved_path = Path(resolved_image_path)
                    theme.background_source = resolved_path
                    theme.background_filename = resolved_path
                    
                    if is_url(image_path):
                        log.info(f"Downloaded background image from {image_path} to {resolved_image_path}")
                    
                    # Remove from updates_data since we handled it specially
                    updates_data = {k: v for k, v in updates_data.items() if k != 'background_image_path'}
                    
                except Exception as e:
                    self.operation_completed.emit(f"Error downloading background image from {image_path}: {str(e)}")
                    return
            
            # Update other provided properties
            updates = []
            for key, value in updates_data.items():
                if value is not None and hasattr(theme, key):
                    setattr(theme, key, value)
                    updates.append(f"{key}: {value}")
            
            # Add background image to updates list if it was processed
            if 'background_image_path' in theme_data.get('updates', {}):
                original_path = theme_data['updates']['background_image_path']
                if is_url(original_path):
                    updates.append(f"background_image_path: {original_path} (downloaded)")
                else:
                    updates.append(f"background_image_path: {original_path}")
            
            if updates or 'background_image_path' in theme_data.get('updates', {}):
                # Save updated theme
                theme_manager.save_theme(theme)
                
                # Generate preview and refresh UI
                theme_manager.update_preview_images([theme_name])
                
                self.operation_completed.emit(f"Theme '{theme_name}' updated: {', '.join(updates)}")
            else:
                self.operation_completed.emit(f"No valid properties provided to update for theme '{theme_name}'")
                
        except Exception as e:
            self.operation_completed.emit(f"Error updating theme: {str(e)}")
            log.error(f"Error updating theme {theme_data.get('theme_name', 'unknown')}: {e}", exc_info=True)

    @QtCore.Slot(str)
    def delete_theme(self, theme_name):
        """Delete a theme."""
        try:
            from openlp.core.common.registry import Registry
            
            theme_manager = Registry().get('theme_manager')
            
            # Check if theme exists
            if theme_name not in theme_manager.get_theme_names():
                self.operation_completed.emit(f"Theme '{theme_name}' not found")
                return
            
            # Check if it's the default theme or global theme
            if theme_name == 'Default':
                self.operation_completed.emit(f"Cannot delete the default theme 'Default'")
                return
                
            # Check if it's currently set as the global theme
            global_theme = theme_manager.global_theme
            if theme_name == global_theme:
                self.operation_completed.emit(f"Cannot delete the global theme '{theme_name}'. Please set a different global theme first.")
                return
            
            # Delete the theme
            theme_manager.delete_theme(theme_name)
            
            # Refresh the UI
            theme_manager.load_themes()
            
            self.operation_completed.emit(f"Theme '{theme_name}' deleted successfully")
            
        except Exception as e:
            self.operation_completed.emit(f"Error deleting theme: {str(e)}")

    @QtCore.Slot(str, str)
    def duplicate_theme(self, existing_theme_name, new_theme_name):
        """Create a copy of an existing theme with a new name."""
        try:
            from openlp.core.common.registry import Registry
            
            theme_manager = Registry().get('theme_manager')
            
            # Check if source theme exists
            if existing_theme_name not in theme_manager.get_theme_names():
                self.operation_completed.emit(f"Source theme '{existing_theme_name}' not found")
                return
            
            # Check if new theme name already exists
            if new_theme_name in theme_manager.get_theme_names():
                self.operation_completed.emit(f"Theme '{new_theme_name}' already exists")
                return
            
            # Get source theme data
            theme_data = theme_manager.get_theme_data(existing_theme_name)
            
            # Use OpenLP's built-in clone method which properly handles background images
            theme_manager.clone_theme_data(theme_data, new_theme_name)
            
            self.operation_completed.emit(f"Theme '{existing_theme_name}' duplicated as '{new_theme_name}'")
            
        except Exception as e:
            self.operation_completed.emit(f"Error duplicating theme: {str(e)}")

    # Per-Item Theme Management Methods
    @QtCore.Slot(int, str)
    def set_item_theme(self, item_index, theme_name):
        """Set a theme for a specific service item."""
        try:
            from openlp.core.common.registry import Registry
            
            service_manager = Registry().get('service_manager')
            
            # Check if item index is valid
            if item_index < 0 or item_index >= len(service_manager.service_items):
                self.operation_completed.emit(f"Invalid item index: {item_index}")
                return
            
            # Get the service item
            service_item = service_manager.service_items[item_index]['service_item']
            
            # Check if theme exists (unless it's None to clear theme)
            if theme_name and theme_name.lower() != 'none':
                theme_manager = Registry().get('theme_manager')
                if theme_name not in theme_manager.get_theme_names():
                    self.operation_completed.emit(f"Theme '{theme_name}' not found")
                    return
                theme_to_set = theme_name
            else:
                # Clear theme (use None to fall back to service/global theme)
                theme_to_set = None
            
            # Update the service item's theme
            service_item.update_theme(theme_to_set)
            
            # Refresh the service list to show changes
            service_manager.repaint_service_list(item_index, -1)
            service_manager.set_modified()
            
            # If this item is currently live and hot reload is enabled, refresh it
            try:
                live_controller = Registry().get('live_controller')
                if (live_controller.service_item and 
                    service_item.unique_identifier == live_controller.service_item.unique_identifier and
                    Registry().get('settings').value('themes/hot reload')):
                    live_controller.refresh_service_item(service_item)
            except:
                pass  # Not critical if live refresh fails
            
            if theme_to_set:
                self.operation_completed.emit(f"Item {item_index} ('{service_item.title}') theme set to '{theme_to_set}'")
            else:
                self.operation_completed.emit(f"Item {item_index} ('{service_item.title}') theme cleared (using service/global theme)")
            
        except Exception as e:
            self.operation_completed.emit(f"Error setting item theme: {str(e)}")

    @QtCore.Slot(int)
    def get_item_theme(self, item_index):
        """Get the theme for a specific service item."""
        try:
            from openlp.core.common.registry import Registry
            from openlp.core.common import ThemeLevel
            
            service_manager = Registry().get('service_manager')
            
            # Check if item index is valid
            if item_index < 0 or item_index >= len(service_manager.service_items):
                self.operation_completed.emit(f"Invalid item index: {item_index}")
                return
            
            # Get the service item
            service_item = service_manager.service_items[item_index]['service_item']
            
            # Get theme info
            item_specific_theme = service_item.theme
            effective_theme_data = service_item.get_theme_data()
            effective_theme_name = effective_theme_data.theme_name if effective_theme_data else "Unknown"
            
            # Get theme level setting
            theme_level = Registry().get('settings').value('themes/theme level')
            level_names = {
                ThemeLevel.Global: "Global",
                ThemeLevel.Service: "Service", 
                ThemeLevel.Song: "Song/Item"
            }
            level_name = level_names.get(theme_level, "Unknown")
            
            # Build result
            if item_specific_theme:
                result = f"Item {item_index} ('{service_item.title}'):\n"
                result += f"  Item-specific theme: '{item_specific_theme}'\n"
                result += f"  Effective theme: '{effective_theme_name}'\n"
                result += f"  Theme level: {level_name}"
            else:
                result = f"Item {item_index} ('{service_item.title}'):\n"
                result += f"  Item-specific theme: None (using service/global theme)\n"
                result += f"  Effective theme: '{effective_theme_name}'\n"
                result += f"  Theme level: {level_name}"
            
            self.operation_completed.emit(result)
            
        except Exception as e:
            self.operation_completed.emit(f"Error getting item theme: {str(e)}")

    # Plugin Search and Add Methods
    @QtCore.Slot(str)
    def search_songs(self, text):
        """Search for songs in the songs plugin and return results with [id, title, alternate_title] format."""
        try:
            # Validate input
            if not text or not text.strip():
                self.operation_completed.emit([])
                return
            
            # Check if songs plugin is available and active
            plugin_manager = Registry().get('plugin_manager')
            if not plugin_manager:
                log.error("Plugin manager not available")
                self.operation_completed.emit([])
                return
                
            songs_plugin = plugin_manager.get_plugin_by_name('songs')
            if not songs_plugin:
                log.error("Songs plugin not found")
                self.operation_completed.emit([])
                return
                
            from openlp.core.common.enum import PluginStatus
            if songs_plugin.status != PluginStatus.Active:
                log.error("Songs plugin is not active")
                self.operation_completed.emit([])
                return
            
            # Perform search using API
            from openlp.core.api.versions.v2.plugins import search
            results = search('songs', text.strip())
            
            if results is None:
                log.debug(f"No songs found for search: {text}")
                self.operation_completed.emit([])
            else:
                log.debug(f"Found {len(results)} songs for search: {text}")
                self.operation_completed.emit(results)
                
        except Exception as e:
            log.error(f"Error searching songs with text '{text}': {e}", exc_info=True)
            self.operation_completed.emit([])

    @QtCore.Slot(str, str, str)
    def create_song(self, title, lyrics, author):
        """Create a new song in the database."""
        try:
            songs_plugin = Registry().get('plugin_manager').get_plugin_by_name('songs')
            if not songs_plugin or not songs_plugin.is_active():
                self.operation_completed.emit("Error: Songs plugin not available")
                return
            
            # Import necessary classes
            from openlp.plugins.songs.lib.db import Song, Author
            from openlp.plugins.songs.lib import clean_song, VerseType
            from openlp.plugins.songs.lib.openlyricsxml import SongXML
            
            # Create the song
            song = Song()
            song.title = title.strip()
            
            # Process lyrics into proper XML format
            song_xml = SongXML()
            lyrics_text = lyrics.strip()
            
            # Parse verse labels like [Verse 1], [Chorus], etc.
            import re
            verse_pattern = re.compile(r'^\[(.*?)\]', re.MULTILINE)
            
            # Map common verse types to OpenLP VerseType
            verse_type_map = {
                'verse': VerseType.Verse,
                'chorus': VerseType.Chorus,
                'bridge': VerseType.Bridge,
                'pre-chorus': VerseType.PreChorus,
                'intro': VerseType.Intro,
                'ending': VerseType.Ending,
                'outro': VerseType.Ending,
                'tag': VerseType.Other,
                'other': VerseType.Other
            }
            
            # Split by verse markers
            sections = verse_pattern.split(lyrics_text)
            
            if len(sections) > 1:
                # Has verse markers - process each section
                verse_order = []
                for i in range(1, len(sections), 2):
                    if i + 1 < len(sections):
                        label = sections[i].strip().lower()
                        content = sections[i + 1].strip()
                        
                        if content:  # Only add non-empty sections
                            # Extract verse type and number
                            verse_type = VerseType.Verse  # default
                            verse_number = 1
                            
                            # Parse label like "Verse 1", "Chorus", "Bridge"
                            for key, vtype in verse_type_map.items():
                                if key in label:
                                    verse_type = vtype
                                    break
                            
                            # Extract number if present
                            number_match = re.search(r'(\d+)', label)
                            if number_match:
                                verse_number = int(number_match.group(1))
                            
                            song_xml.add_verse_to_lyrics(VerseType.tags[verse_type], verse_number, content)
                            verse_order.append(f'{VerseType.tags[verse_type]}{verse_number}')
                
                # Set verse order
                song.verse_order = ' '.join(verse_order)
            else:
                # No verse markers - treat as single verse
                if lyrics_text:
                    song_xml.add_verse_to_lyrics(VerseType.tags[VerseType.Verse], 1, lyrics_text)
            
            song.lyrics = song_xml.extract_xml()
            
            # If author is provided, find or create the author
            if author and author.strip():
                author_name = author.strip()
                existing_author = songs_plugin.manager.get_object_filtered(Author, Author.display_name == author_name)
                if not existing_author:
                    # Create new author
                    name_parts = author_name.rsplit(' ', 1)
                    first_name = name_parts[0] if name_parts else ''
                    last_name = name_parts[1] if len(name_parts) > 1 else ''
                    existing_author = Author(
                        first_name=first_name,
                        last_name=last_name,
                        display_name=author_name
                    )
                song.add_author(existing_author)
            
            # Clean and save the song
            clean_song(songs_plugin.manager, song)
            songs_plugin.manager.save_object(song)
            
            # Return success message with song ID
            author_text = f" by {author}" if author and author.strip() else ""
            self.operation_completed.emit(f"Song '{song.title}'{author_text} created successfully (ID: {song.id})")
            
        except Exception as e:
            error_msg = f"Error creating song '{title}': {str(e)}"
            log.error(error_msg, exc_info=True)
            self.operation_completed.emit(f"Error: {error_msg}")

    @QtCore.Slot(int, int)
    def add_song_by_id(self, song_id, position):
        """Add a song to the service by its database ID at the specified position."""
        try:
            songs_plugin = Registry().get('plugin_manager').get_plugin_by_name('songs')
            if not songs_plugin or not songs_plugin.is_active():
                self.operation_completed.emit("Error: Songs plugin not available")
                return
            
            # Get the song from database
            from openlp.plugins.songs.lib.db import Song
            song = songs_plugin.manager.get_object(Song, song_id)
            if not song:
                self.operation_completed.emit(f"Error: Song with ID {song_id} not found")
                return
            
            # Create a mock item to represent the song
            from PySide6.QtWidgets import QListWidgetItem
            from PySide6.QtCore import Qt
            mock_item = QListWidgetItem()
            mock_item.setData(Qt.ItemDataRole.UserRole, song_id)
            
            # Build the service item using the songs plugin's media item
            from openlp.core.lib.serviceitem import ServiceItem
            from openlp.core.lib import ServiceItemContext
            service_item = ServiceItem(songs_plugin)
            service_item.add_icon()
            
            # Use the songs plugin's generate_slide_data method
            if songs_plugin.media_item.generate_slide_data(service_item, item=mock_item, context=ServiceItemContext.Service):
                service_item.from_plugin = False
                
                # Add the service item to the service at the specified position
                service_manager = Registry().get('service_manager')
                if position == -1:
                    service_manager.add_service_item(service_item)
                else:
                    service_manager.add_service_item(service_item, replace=False, position=position)
                
                success_msg = f"Song '{song.title}' (ID: {song_id}) added to service"
                log.info(success_msg)
                self.operation_completed.emit(success_msg)
            else:
                error_msg = f"Failed to generate service item for song ID {song_id}"
                log.error(error_msg)
                self.operation_completed.emit(f"Error: {error_msg}")
                
        except Exception as e:
            error_msg = f"Error adding song ID {song_id} to service: {str(e)}"
            log.error(error_msg, exc_info=True)
            self.operation_completed.emit(f"Error: {error_msg}") 