#!/usr/bin/env python3
"""
Script to enable the backup bypass setting in OpenLP configuration.
"""

import sys
import os

# Add the openlp directory to the path so we can import openlp modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openlp.core.common.settings import Settings

def enable_backup_bypass():
    """Enable the bypass backup on version change setting."""
    print("Enabling backup bypass setting...")

    # Create settings object
    settings = Settings()

    # Enable the bypass setting
    settings.setValue('advanced/bypass_backup_on_version_change', True)

    # Sync to make sure it's saved
    settings.sync()

    print("Backup bypass setting has been enabled!")
    print(f"Current setting value: {settings.value('advanced/bypass_backup_on_version_change')}")

if __name__ == "__main__":
    enable_backup_bypass()
