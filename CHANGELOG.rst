OpenLP 3.1.3
============

 * Correct media auto start behaviour.
 * Updated translations
 * Deal with PyMuPDF installed as fitz_old
 * Fix that our songbeamer chord parsing was partly based on a malformed file leading to weird imports
 * Web API method "get_language" returns the two-letter ISO 639 language code instead of "en" in case the language in OpenLP is auto detected.
 * Add setting that live preview shows blank screen
 * Add Web API endpoint to delete service items
 * Use correct transition delay when screen is hidden
 * Always show contents in live preview panel
 * Display presentation slides in live preview panel when main display is hidden.
 * Handle Python versions which include release levels by ignoring the release level, and restricting the check to only the major, minor, and micro components of the full version number.
 * Prevent crash by adding check for existence of linked audio file.
 * Do not show screen change message twice
 * Fixed Issue 1584 (switching Windows user account crashes an active OpenLP instance)


OpenLP 3.1.2
============

* Import additional planning center data
* Add "Apply UPPERCASE globally" function to songs plugin
* Update translations
* Stop Service File items from containing more than one audio file
* Fix build part of version number
* Attempt to bubble up permissions errors to the user so that we don't run into None files or hashes
* Hide live when screen setup has changed
* Attempt to fix #1878 by checking if the service item exists first
* Add some registry functions and more that makes it easier for plugins to integrate
* Fix for not found i18n directory
* Fix missing verse translations
* Make the slide height affect the size of the thumbnails generated
* Add ewsx song importer
* Add web API endpoint get configured language
* Add web API endpoint get configured shortcut keys
* Add checks to prevent multiple Linked Audio items on songs
* Set up the Application name as early as possible
* Fix unintentional change of the organization name by the domain name.
* Fix missing translations


OpenLP 3.1.1
============

* Fix path to QtWebEngineProcess binary
* Use Python's version comparison, not Qt's
* Always open downloaded songs as utf-8
* Update translations

OpenLP 3.1.0
============

* Change bug reporting email address to differentiate between affected versions
* Update translations
* Set the app's desktop file name
* tests: add ``assert_`` prefix to a bunch of asserts missing it
* Invalidate the service item cache when the theme changes
* Replace appdirs with platformdirs
* Fix a PermissionError that occurs on Windows 10/11 when qtawesome tries to look at its own fonts
* Change the filter to be SQLAlchemy 2 compatible
* Working version of Community Imports
* Fix #1323 for the Projector Manager
* Made the wordproject import more robust

OpenLP 3.1.0rc4
===============

* Fix a loop in the First Time Wizard on Windows
* Fix portable builds by re-arranging when the settings are created

OpenLP 3.1.0rc3
===============

* Fix the coverage badge on GitLab by producing an XML report
* Fix irregular service theme saving (closes #1723)
* Fix AuthorType not getting translated
* Fix bug in _has_header
* Fix issues with upgrading 2.9.x databases
* Update translations
* Fix OpenLP startup by reordering statements
* High DPI Fixes
* Fix traceback on bible import when no bible available
* Check before initialising a None Bible
* Fix #1700 by typecasting the calls to Paths
* Make PathEdit handle None values
* Fix external DB settings
* Fix alerts
* Fix handling of missing VLC
* Better handling of attempts to load invalid SWORD folder or zip-file
* Ensure a path set in PathEdit is a Path instance
* Fix trimming leading whitespaces
* Inject String.replaceAll javascript implementation if needed into webengine when browsing SongSelect.
* Do not start the same presentation again when it's already live.
* Prevent key error when unblank screen at start of presentation.

OpenLP 3.1.0rc2
===============

* Revert the Registry behaviour
* Fix the multiselect in the images plugin
* Spoof the songselect webengine user agent

OpenLP 3.1.0rc1
===============

* Don't build manual, use online manual instead
* Update AppVeyor for Mac to install Pyro5 instead of Pyro4
* Silence error when shutting down threads
* Fix saving of songs
* Update some system messaging
* Re introduce the selective turning off logging - correctly this time.
* Fix some issues with building on macOS
* Fix spelling in songimport.py
* Bypass image db updates if the db has already been upgraded
* Fix a couple of macOS issues
* Fix issue with database cleanup code
* Make some forward compatibility changes
* Refactor last instances of TestCase-based tests
* Change SongSelect import procedure to import when clicking download on webpage
* Add test coverage for __main__.py and remove some unused files
* Remove unused flag in Registry
* When a permission error is raised during generation of the sha256 hash when deleting a presentation from the controller don't crash but continue.
* Fix presentations not being able to return from Display Screen
* fix the deadlock on macos
* Fix issue #1618 by ignoring the messages if the event loop is not running
* Fix issue #1382 by waiting for the service_manager to become available, or giving up after 2m
* Display API abstraction
* Try to fix an issue with MediaInfo perhaps returning a str instead of an int
* Fix issue #1582 by running the search in the original thread
* Try to fix an issue that only seems to happen on macOS
* Allow loading the same presentation file multiple times from 2.4.x service file. Fixes bug #1601.
* Fix endless loop at the end of a PowerPoint presentation
* Implement a filelock for shared data folder.
* Add detection for presentation files that were uploaded from the cloud.
* Move "Live" / "Preview" and current item on one line
* feat(importer): add authors to powerpraise importer
* Add the list of associated songs to the delete dialog in the song maintenance form
* Create a connection and then run execute
* Update appveyor.yml to use python 3.11.
* Fix an issue with the arguments of with_only_columns
* Fix song search by author
* Remove dependency on PIL since the latest version does not support PyQt5
* Fixing freezing screenshot test
* Fix Datasoul translate strings
* RFC/Proposal: Fallback code for display screenshot code (used on '/main'  Web Remote)
* Update translations
* New theme adjustments: Adding letter spacing to theme main area; adding line and letter spacing to footer
* Fix the GitLab CI yaml config
* Fix issue #1297 by reducing the number by 1024 times
* Update resource generation for ARM64 platforms (e.g. Apple M2)
* Enumm Conversion
* Upgrade to Pyro5
* Ignore the thumbnails if the path doesn't exist (fixes #914)
* Adding Footer Content as Extra First Slide
* Fix an issue where an item's parent is None
* Migrate to SQLAlchemy 2 style queries
* Fix the 415 errors due to a change in Werkzeug
* Update CI to use the GitLab container registry
* Display Custom Scheme
* Implementing new message websocket endpoint
* Fix bug in icon definition - Typr only
* Take account of VLC on macOS being bundled with OpenLP
* Fix for #1495 task: wrapped C/C++ object of type QTreeWidgetItem has been deleted
* Fixing Images not being able to be inserted on Service
* Reusable Media Toolbar
* Adding foundational support to Footer per slide
* Merge CustomXMLBuilder and CustomXMLParser
* Add Datasoul song importer
* fix: tests on windows failing due to MagicMock in Path
* Migrate from FontAwesome4 to Material Design Icons v5.9.55
* Highlighted slidecontroller buttons
* Fix translations loading on linux system-wide installation
* Migrate database metadata to declarative base
* Migrate Song Usage to declarative
* Migrate alerts to declarative
* Migrate Images plugin to use shared folder code
* Fix a typo in creating custom slides from other text items
* Migrate images plugin to declarative base
* Convert Bibles to use declarative_base
* Convert custom slides to declarative
* Migrate to using Declarative Base in Songs
* Fix: Correct About references and Remove Unused
* Minor fix for EasyWorship import
* Improve Powerpoint detection by trying to start the application instead of looking it up in the registry.
* Fix selected=True not being set at new Transpose API Endpoint
* Allow the remote interface update notification to be turned off.
* Skip missing thumbnails when loading a service
* Rework the songs settings, so that they're not as squashed.
* Remove WebOb -- we don't need it
* Add a grid view to themes manager

OpenLP 3.0.2
============

* Only show hash if song book number exists
* FIX: Missing looping for theme background videos
* Fixing Songs' Topics media manager icon to be the same from the Song Maintenance dialog
* Adding ability to return transposed item with service_item format to avoid duplicate calls on remote
* Fix OpenLyrics whitespaces being 'eaten' (again)
* Fixing service manager's list exception when pressing 'Left' keyboard key without any item selected
* Force the use of SqlAlchemy 1.4 for now
* Removing login requirement from transpose endpoint
* Handle verse ranges in BibleServer
* Fix up loading 2.9.x services
* Attempt to fix #1287 by checking for both str and bytes, and decoding bytes to unicode
* Add debugging for VLC and fix strange state.
* Display the closing progress dialog during plugin shutdown
* Fix an issue with the Worship Center Pro importer
* Fix white preview display when previewing presentations
* Fix an issue where the websockets server would try to shut down even when -w is supplied
* Use a simpler approach when creating a tmp file when saving service files

OpenLP 2.5.1
============

* Fixed a bug where the author type upgrade was being ignore because it was looking at the wrong table
* Fixed a bug where the songs_songbooks table was not being created because the if expression was the wrong way round
* Changed the songs_songbooks migration SQL slightly to take into account a bug that has (hopefully) been fixed
* Sometimes the timer goes off as OpenLP is shutting down, and the application has already been deleted (reported via support system)
* Fix opening the data folder (KDE thought the old way was an SMB share)
* Fix a problem with the new QMediaPlayer not controlling the playlist anymore
* Added importing of author types to the OpenLP 2 song importer
* Refactored the merge script and gave it some options
* Fix a problem with loading Qt's translation files, bug #1676163
