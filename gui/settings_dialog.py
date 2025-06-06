"""
Settings dialog for configuring application preferences.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

class SettingsDialog:
    """Settings configuration dialog."""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.config = config_manager.get_config().copy()
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.create_widgets()
        
    def create_widgets(self):
        """Create settings interface widgets."""
        # Main frame with padding
        main_frame = ttk.Frame(self.dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Download settings
        download_frame = ttk.LabelFrame(main_frame, text="Download Settings", padding="10")
        download_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Download directory
        ttk.Label(download_frame, text="Download Directory:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        dir_frame = ttk.Frame(download_frame)
        dir_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), columnspan=2, pady=(0, 10))
        dir_frame.columnconfigure(0, weight=1)
        
        self.download_dir_var = tk.StringVar(value=self.config['download_directory'])
        dir_entry = ttk.Entry(dir_frame, textvariable=self.download_dir_var)
        dir_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Button(dir_frame, text="Browse", command=self.browse_download_dir).grid(row=0, column=1)
        
        # Max concurrent downloads
        ttk.Label(download_frame, text="Max Concurrent Downloads:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.max_downloads_var = tk.IntVar(value=self.config['max_concurrent_downloads'])
        ttk.Spinbox(download_frame, from_=1, to=10, textvariable=self.max_downloads_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=(0, 10))
        
        # File naming settings
        naming_frame = ttk.LabelFrame(main_frame, text="File Naming", padding="10")
        naming_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.organize_by_platform = tk.BooleanVar(value=self.config['organize_by_platform'])
        ttk.Checkbutton(naming_frame, text="Organize files by platform", 
                       variable=self.organize_by_platform).pack(anchor=tk.W)
        
        self.add_date_to_filename = tk.BooleanVar(value=self.config['add_date_to_filename'])
        ttk.Checkbutton(naming_frame, text="Add date to filename", 
                       variable=self.add_date_to_filename).pack(anchor=tk.W, pady=(5, 0))
        
        self.sanitize_filenames = tk.BooleanVar(value=self.config['sanitize_filenames'])
        ttk.Checkbutton(naming_frame, text="Sanitize filenames (remove special characters)", 
                       variable=self.sanitize_filenames).pack(anchor=tk.W, pady=(5, 0))
        
        # Quality settings
        quality_frame = ttk.LabelFrame(main_frame, text="Quality Settings", padding="10")
        quality_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(quality_frame, text="Default Video Quality:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.default_quality_var = tk.StringVar(value=self.config['default_video_quality'])
        quality_combo = ttk.Combobox(quality_frame, textvariable=self.default_quality_var, 
                                   values=["best", "720p", "480p", "360p", "worst"], state="readonly")
        quality_combo.grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(quality_frame, text="Audio Format:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.audio_format_var = tk.StringVar(value=self.config['audio_format'])
        audio_combo = ttk.Combobox(quality_frame, textvariable=self.audio_format_var, 
                                 values=["mp3", "m4a", "wav", "best"], state="readonly")
        audio_combo.grid(row=1, column=1, sticky=tk.W, pady=(0, 5))
        
        # Advanced settings
        advanced_frame = ttk.LabelFrame(main_frame, text="Advanced", padding="10")
        advanced_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.skip_existing = tk.BooleanVar(value=self.config['skip_existing_files'])
        ttk.Checkbutton(advanced_frame, text="Skip existing files", 
                       variable=self.skip_existing).pack(anchor=tk.W)
        
        self.enable_logging = tk.BooleanVar(value=self.config['enable_detailed_logging'])
        ttk.Checkbutton(advanced_frame, text="Enable detailed logging", 
                       variable=self.enable_logging).pack(anchor=tk.W, pady=(5, 0))
        
        # Retry settings
        retry_frame = ttk.Frame(advanced_frame)
        retry_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(retry_frame, text="Retry attempts on failure:").pack(side=tk.LEFT)
        self.retry_attempts_var = tk.IntVar(value=self.config['retry_attempts'])
        ttk.Spinbox(retry_frame, from_=0, to=10, textvariable=self.retry_attempts_var, width=10).pack(side=tk.LEFT, padx=(5, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="OK", command=self.save_settings).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_defaults).pack(side=tk.LEFT)
        
    def browse_download_dir(self):
        """Browse for download directory."""
        directory = filedialog.askdirectory(initialdir=self.download_dir_var.get())
        if directory:
            self.download_dir_var.set(directory)
            
    def save_settings(self):
        """Save settings and close dialog."""
        # Validate download directory
        download_dir = self.download_dir_var.get()
        if not os.path.exists(download_dir):
            try:
                os.makedirs(download_dir, exist_ok=True)
            except OSError as e:
                messagebox.showerror("Error", f"Cannot create download directory: {e}")
                return
                
        # Update configuration
        self.config.update({
            'download_directory': download_dir,
            'max_concurrent_downloads': self.max_downloads_var.get(),
            'organize_by_platform': self.organize_by_platform.get(),
            'add_date_to_filename': self.add_date_to_filename.get(),
            'sanitize_filenames': self.sanitize_filenames.get(),
            'default_video_quality': self.default_quality_var.get(),
            'audio_format': self.audio_format_var.get(),
            'skip_existing_files': self.skip_existing.get(),
            'enable_detailed_logging': self.enable_logging.get(),
            'retry_attempts': self.retry_attempts_var.get()
        })
        
        # Save to file
        try:
            self.config_manager.save_config(self.config)
            messagebox.showinfo("Success", "Settings saved successfully!")
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
            
    def reset_defaults(self):
        """Reset all settings to defaults."""
        if messagebox.askyesno("Confirm", "Reset all settings to defaults?"):
            self.config_manager.reset_to_defaults()
            self.config = self.config_manager.get_config().copy()
            
            # Update UI
            self.download_dir_var.set(self.config['download_directory'])
            self.max_downloads_var.set(self.config['max_concurrent_downloads'])
            self.organize_by_platform.set(self.config['organize_by_platform'])
            self.add_date_to_filename.set(self.config['add_date_to_filename'])
            self.sanitize_filenames.set(self.config['sanitize_filenames'])
            self.default_quality_var.set(self.config['default_video_quality'])
            self.audio_format_var.set(self.config['audio_format'])
            self.skip_existing.set(self.config['skip_existing_files'])
            self.enable_logging.set(self.config['enable_detailed_logging'])
            self.retry_attempts_var.set(self.config['retry_attempts'])
