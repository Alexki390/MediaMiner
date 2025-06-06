#!/usr/bin/env python3
"""
Main entry point for the Social Media Bulk Downloader application.
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox
import logging
from pathlib import Path

# Detectar si estamos ejecutando desde un ejecutable PyInstaller
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Ejecutándose desde ejecutable PyInstaller
    application_path = sys._MEIPASS
    base_path = os.path.dirname(sys.executable)
else:
    # Ejecutándose desde script Python normal
    application_path = os.path.dirname(os.path.abspath(__file__))
    base_path = application_path

# Add the current directory to Python path
sys.path.insert(0, application_path)

# Crear directorios necesarios en la ubicación del ejecutable
downloads_dir = os.path.join(base_path, "downloads")
config_dir = os.path.join(base_path, "config")
logs_dir = os.path.join(base_path, "logs")

for directory in [downloads_dir, config_dir, logs_dir]:
    os.makedirs(directory, exist_ok=True)

from gui.main_window import MainWindow
from utils.logger import setup_logging
from utils.config_manager import ConfigManager

def main():
    """Main application entry point."""
    try:
        # Setup logging
        setup_logging()
        logging.info("Starting Social Media Bulk Downloader")
        
        # Initialize configuration
        config_manager = ConfigManager()
        
        # Create main window
        root = tk.Tk()
        app = MainWindow(root, config_manager)
        
        # Start the application
        root.mainloop()
        
    except Exception as e:
        logging.error(f"Fatal error starting application: {e}")
        messagebox.showerror("Fatal Error", f"Failed to start application:\n{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
