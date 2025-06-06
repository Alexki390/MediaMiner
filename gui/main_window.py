"""
Main GUI window for the Social Media Bulk Downloader.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import logging
from typing import Dict, Any

from gui.download_queue import DownloadQueue
from gui.settings_dialog import SettingsDialog
from downloaders.youtube_downloader import YouTubeDownloader
from downloaders.tiktok_downloader import TikTokDownloader
from downloaders.instagram_downloader import InstagramDownloader
from downloaders.reddit_downloader import RedditDownloader
from downloaders.redgifs_downloader import RedgifsDownloader
from downloaders.pornhub_downloader import PornhubDownloader
from downloaders.twitter_downloader import TwitterDownloader
from downloaders.generic_downloader import GenericDownloader

class MainWindow:
    """Main application window with tabbed interface for different platforms."""

    def __init__(self, root: tk.Tk, config_manager):
        self.root = root
        self.config_manager = config_manager
        self.config = config_manager.get_config()

        # Initialize downloaders
        self.downloaders = {
            'youtube': YouTubeDownloader(config_manager),
            'tiktok': TikTokDownloader(config_manager),
            'instagram': InstagramDownloader(config_manager),
            'reddit': RedditDownloader(config_manager),
            'redgifs': RedgifsDownloader(config_manager),
            'pornhub': PornhubDownloader(config_manager),
            'twitter': TwitterDownloader(config_manager),
            'generic': GenericDownloader(config_manager),
            'erome': self._get_erome_downloader(config_manager),
            'kwai': self._get_kwai_downloader(config_manager)
        }

        # Setup GUI
        self.setup_window()
        self.create_widgets()
        self.download_queue = DownloadQueue(self.queue_frame, self.downloaders)

    def setup_window(self):
        """Configure the main window."""
        self.root.title("Social Media Bulk Downloader")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

    def create_widgets(self):
        """Create and arrange GUI widgets."""
        # Menu bar
        self.create_menu_bar()

        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Platform tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        self.create_platform_tabs()

        # Download queue frame
        queue_label = ttk.Label(main_frame, text="Download Queue", font=('TkDefaultFont', 10, 'bold'))
        queue_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))

        self.queue_frame = ttk.Frame(main_frame)
        self.queue_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.queue_frame.columnconfigure(0, weight=1)
        self.queue_frame.rowconfigure(0, weight=1)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Settings", command=self.open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

    def create_platform_tabs(self):
        """Create tabs for different social media platforms."""
        # YouTube tab
        youtube_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(youtube_frame, text="YouTube")
        self.create_youtube_tab(youtube_frame)

        # TikTok tab
        tiktok_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tiktok_frame, text="TikTok")
        self.create_tiktok_tab(tiktok_frame)

        # Instagram tab
        instagram_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(instagram_frame, text="Instagram")
        self.create_instagram_tab(instagram_frame)

        # Reddit tab
        reddit_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(reddit_frame, text="Reddit")
        self.create_reddit_tab(reddit_frame)

        # Redgifs tab
        redgifs_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(redgifs_frame, text="Redgifs")
        self.create_redgifs_tab(redgifs_frame)

        # Pornhub tab
        pornhub_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(pornhub_frame, text="Pornhub")
        self.create_pornhub_tab(pornhub_frame)

        # Twitter tab
        twitter_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(twitter_frame, text="Twitter")
        self.create_twitter_tab(twitter_frame)

        # Generic tab
        generic_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(generic_frame, text="Otros Sitios")
        self.create_generic_tab(generic_frame)

        # Erome tab
        erome_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(erome_frame, text="Erome")
        self.create_erome_tab(erome_frame)

        # Kwai tab
        kwai_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(kwai_frame, text="Kwai")
        self.create_kwai_tab(kwai_frame)

        # Batch URLs tab
        batch_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(batch_frame, text="URLs Múltiples")
        self.create_batch_urls_tab(batch_frame)

    def create_youtube_tab(self, parent):
        """Create YouTube download interface."""
        # URL input
        ttk.Label(parent, text="Channel URL or Video URL:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.youtube_url_var = tk.StringVar()
        url_entry = ttk.Entry(parent, textvariable=self.youtube_url_var, width=60)
        url_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Options
        options_frame = ttk.LabelFrame(parent, text="Options", padding="5")
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.youtube_video_quality = tk.StringVar(value="best")
        ttk.Label(options_frame, text="Video Quality:").grid(row=0, column=0, sticky=tk.W)
        quality_combo = ttk.Combobox(options_frame, textvariable=self.youtube_video_quality, 
                                   values=["best", "worst", "720p", "480p", "360p"], state="readonly")
        quality_combo.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))

        self.youtube_audio_only = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Audio only", variable=self.youtube_audio_only).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))

        self.youtube_entire_channel = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Download entire channel", variable=self.youtube_entire_channel).grid(row=1, column=1, sticky=tk.W, pady=(5, 0))

        # Download button
        ttk.Button(parent, text="Add to Queue", command=self.add_youtube_download).grid(row=3, column=0, pady=(10, 0))

        parent.columnconfigure(0, weight=1)

    def create_tiktok_tab(self, parent):
        """Create TikTok download interface."""
        # URL input
        ttk.Label(parent, text="TikTok Username or Video URL:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.tiktok_url_var = tk.StringVar()
        url_entry = ttk.Entry(parent, textvariable=self.tiktok_url_var, width=60)
        url_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Options
        options_frame = ttk.LabelFrame(parent, text="Options", padding="5")
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.tiktok_process_slideshows = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Process slideshows (combine images with audio)", 
                       variable=self.tiktok_process_slideshows).grid(row=0, column=0, sticky=tk.W)

        self.tiktok_limit = tk.IntVar(value=50)
        ttk.Label(options_frame, text="Max videos to download:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Spinbox(options_frame, from_=1, to=1000, textvariable=self.tiktok_limit, width=10).grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(5, 0))

        # Download button
        ttk.Button(parent, text="Add to Queue", command=self.add_tiktok_download).grid(row=3, column=0, pady=(10, 0))

        parent.columnconfigure(0, weight=1)

    def create_instagram_tab(self, parent):
        """Create Instagram download interface."""
        # URL input
        ttk.Label(parent, text="Instagram Username or Post URL:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.instagram_url_var = tk.StringVar()
        url_entry = ttk.Entry(parent, textvariable=self.instagram_url_var, width=60)
        url_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Options
        options_frame = ttk.LabelFrame(parent, text="Options", padding="5")
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.instagram_stories = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Include stories", variable=self.instagram_stories).grid(row=0, column=0, sticky=tk.W)

        self.instagram_limit = tk.IntVar(value=50)
        ttk.Label(options_frame, text="Max posts to download:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Spinbox(options_frame, from_=1, to=1000, textvariable=self.instagram_limit, width=10).grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(5, 0))

        # Download button
        ttk.Button(parent, text="Add to Queue", command=self.add_instagram_download).grid(row=3, column=0, pady=(10, 0))

        parent.columnconfigure(0, weight=1)

    def create_reddit_tab(self, parent):
        """Create Reddit download interface."""
        # URL input
        ttk.Label(parent, text="Subreddit name (without r/):").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.reddit_url_var = tk.StringVar()
        url_entry = ttk.Entry(parent, textvariable=self.reddit_url_var, width=60)
        url_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Options
        options_frame = ttk.LabelFrame(parent, text="Options", padding="5")
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.reddit_sort = tk.StringVar(value="hot")
        ttk.Label(options_frame, text="Sort by:").grid(row=0, column=0, sticky=tk.W)
        sort_combo = ttk.Combobox(options_frame, textvariable=self.reddit_sort, 
                                values=["hot", "new", "top", "rising"], state="readonly")
        sort_combo.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))

        self.reddit_limit = tk.IntVar(value=100)
        ttk.Label(options_frame, text="Max posts to download:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.limit_spinbox = ttk.Spinbox(options_frame, from_=1, to=1000, textvariable=self.reddit_limit, width=10)
        self.limit_spinbox.grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(5, 0))

        self.reddit_unlimited = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Descarga ilimitada", variable=self.reddit_unlimited, command=self._toggle_reddit_limit).grid(row=2, column=0, sticky=tk.W)

        # Download button
        ttk.Button(parent, text="Add to Queue", command=self.add_reddit_download).grid(row=3, column=0, pady=(10, 0))

        parent.columnconfigure(0, weight=1)

    def add_youtube_download(self):
        """Add YouTube download to queue."""
        url = self.youtube_url_var.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a YouTube URL")
            return

        options = {
            'quality': self.youtube_video_quality.get(),
            'audio_only': self.youtube_audio_only.get(),
            'entire_channel': self.youtube_entire_channel.get()
        }

        self.download_queue.add_download('youtube', url, options)
        self.youtube_url_var.set("")

    def add_tiktok_download(self):
        """Add TikTok download to queue."""
        url = self.tiktok_url_var.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a TikTok username or URL")
            return

        options = {
            'process_slideshows': self.tiktok_process_slideshows.get(),
            'limit': self.tiktok_limit.get()
        }

        self.download_queue.add_download('tiktok', url, options)
        self.tiktok_url_var.set("")

    def add_instagram_download(self):
        """Add Instagram download to queue."""
        url = self.instagram_url_var.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter an Instagram username or URL")
            return

        options = {
            'include_stories': self.instagram_stories.get(),
            'limit': self.instagram_limit.get()
        }

        self.download_queue.add_download('instagram', url, options)
        self.instagram_url_var.set("")

    def _toggle_reddit_limit(self):
        """Toggle between limited and unlimited Reddit downloads."""
        if self.reddit_unlimited.get():
            self.limit_spinbox.configure(state='disabled')
        else:
            self.limit_spinbox.configure(state='normal')

    def add_reddit_download(self):
        """Add Reddit download to queue."""
        url = self.reddit_url_var.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a subreddit name")
            return

        options = {
            'sort': self.reddit_sort.get(),
            'limit': 0 if self.reddit_unlimited.get() else self.reddit_limit.get()
        }

        self.download_queue.add_download('reddit', url, options)
        self.reddit_url_var.set("")

    def create_redgifs_tab(self, parent):
        """Create Redgifs download interface."""
        # URL input
        ttk.Label(parent, text="URL de Redgifs o Usuario:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.redgifs_url_var = tk.StringVar()
        url_entry = ttk.Entry(parent, textvariable=self.redgifs_url_var, width=60)
        url_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Options
        options_frame = ttk.LabelFrame(parent, text="Opciones", padding="5")
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.redgifs_quality = tk.StringVar(value="hd")
        ttk.Label(options_frame, text="Calidad:").grid(row=0, column=0, sticky=tk.W)
        quality_combo = ttk.Combobox(options_frame, textvariable=self.redgifs_quality, 
                                   values=["hd", "sd"], state="readonly")
        quality_combo.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))

        self.redgifs_limit = tk.IntVar(value=50)
        ttk.Label(options_frame, text="Máximo a descargar:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Spinbox(options_frame, from_=1, to=500, textvariable=self.redgifs_limit, width=10).grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(5, 0))

        # Download button
        ttk.Button(parent, text="Añadir a Cola", command=self.add_redgifs_download).grid(row=3, column=0, pady=(10, 0))

        parent.columnconfigure(0, weight=1)

    def create_pornhub_tab(self, parent):
        """Create Pornhub download interface."""
        # URL input
        ttk.Label(parent, text="URL de Video o Usuario/Canal:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.pornhub_url_var = tk.StringVar()
        url_entry = ttk.Entry(parent, textvariable=self.pornhub_url_var, width=60)
        url_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Options
        options_frame = ttk.LabelFrame(parent, text="Opciones", padding="5")
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.pornhub_quality = tk.StringVar(value="720p")
        ttk.Label(options_frame, text="Calidad preferida:").grid(row=0, column=0, sticky=tk.W)
        quality_combo = ttk.Combobox(options_frame, textvariable=self.pornhub_quality, 
                                   values=["1080p", "720p", "480p", "360p"], state="readonly")
        quality_combo.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))

        self.pornhub_limit = tk.IntVar(value=25)
        ttk.Label(options_frame, text="Máximo videos:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Spinbox(options_frame, from_=1, to=200, textvariable=self.pornhub_limit, width=10).grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(5, 0))

        # Download button
        ttk.Button(parent, text="Añadir a Cola", command=self.add_pornhub_download).grid(row=3, column=0, pady=(10, 0))

        parent.columnconfigure(0, weight=1)

    def create_twitter_tab(self, parent):
        """Create Twitter download interface."""
        # URL input
        ttk.Label(parent, text="URL de Tweet o Usuario:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.twitter_url_var = tk.StringVar()
        url_entry = ttk.Entry(parent, textvariable=self.twitter_url_var, width=60)
        url_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Options
        options_frame = ttk.LabelFrame(parent, text="Opciones", padding="5")
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.twitter_media_only = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Solo descargar tweets con media", 
                       variable=self.twitter_media_only).grid(row=0, column=0, sticky=tk.W)

        self.twitter_limit = tk.IntVar(value=100)
        ttk.Label(options_frame, text="Máximo tweets:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Spinbox(options_frame, from_=1, to=1000, textvariable=self.twitter_limit, width=10).grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(5, 0))

        # API info
        info_label = ttk.Label(options_frame, text="Nota: Requiere configurar credenciales de Twitter API", 
                              font=('TkDefaultFont', 8))
        info_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # Download button
        ttk.Button(parent, text="Añadir a Cola", command=self.add_twitter_download).grid(row=3, column=0, pady=(10, 0))

        parent.columnconfigure(0, weight=1)

    def create_generic_tab(self, parent):
        """Create generic sites download interface."""
        # URL input
        ttk.Label(parent, text="URL del Sitio Web:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.generic_url_var = tk.StringVar()
        url_entry = ttk.Entry(parent, textvariable=self.generic_url_var, width=60)
        url_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Supported sites info
        info_frame = ttk.LabelFrame(parent, text="Sitios Soportados", padding="5")
        info_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        sites_text = """• Xvideos, XNXX, YouPorn, Tube8
• SpankBang, xHamster, Beeg, ThisVid
• Motherless, EPorner, FapHouse
• OnlyFans (requiere autenticación)
• Cualquier sitio con enlaces directos a media"""

        ttk.Label(info_frame, text=sites_text, justify=tk.LEFT).grid(row=0, column=0, sticky=tk.W)

        # Options
        options_frame = ttk.LabelFrame(parent, text="Opciones", padding="5")
        options_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.generic_auto_detect = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Auto-detectar tipo de contenido", 
                       variable=self.generic_auto_detect).grid(row=0, column=0, sticky=tk.W)

        self.generic_quality = tk.StringVar(value="best")
        ttk.Label(options_frame, text="Calidad preferida:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        quality_combo = ttk.Combobox(options_frame, textvariable=self.generic_quality, 
                                   values=["best", "720p", "480p", "360p"], state="readonly")
        quality_combo.grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(5, 0))

        # Download button
        ttk.Button(parent, text="Añadir a Cola", command=self.add_generic_download).grid(row=4, column=0, pady=(10, 0))

        parent.columnconfigure(0, weight=1)

    def add_redgifs_download(self):
        """Add Redgifs download to queue."""
        url = self.redgifs_url_var.get().strip()
        if not url:
            messagebox.showwarning("Advertencia", "Por favor ingresa una URL de Redgifs")
            return

        options = {
            'quality': self.redgifs_quality.get(),
            'limit': self.redgifs_limit.get()
        }

        self.download_queue.add_download('redgifs', url, options)
        self.redgifs_url_var.set("")

    def add_pornhub_download(self):
        """Add Pornhub download to queue."""
        url = self.pornhub_url_var.get().strip()
        if not url:
            messagebox.showwarning("Advertencia", "Por favor ingresa una URL de Pornhub")
            return

        options = {
            'quality': self.pornhub_quality.get(),
            'limit': self.pornhub_limit.get()
        }

        self.download_queue.add_download('pornhub', url, options)
        self.pornhub_url_var.set("")

    def add_twitter_download(self):
        """Add Twitter download to queue."""
        url = self.twitter_url_var.get().strip()
        if not url:
            messagebox.showwarning("Advertencia", "Por favor ingresa una URL de Twitter")
            return

        options = {
            'media_only': self.twitter_media_only.get(),
            'limit': self.twitter_limit.get()
        }

        self.download_queue.add_download('twitter', url, options)
        self.twitter_url_var.set("")

    def add_generic_download(self):
        """Add generic site download to queue."""
        url = self.generic_url_var.get().strip()
        if not url:
            messagebox.showwarning("Advertencia", "Por favor ingresa una URL")
            return

        options = {
            'auto_detect': self.generic_auto_detect.get(),
            'quality': self.generic_quality.get()
        }

        self.download_queue.add_download('generic', url, options)
        self.generic_url_var.set("")

    def open_settings(self):
        """Open settings dialog."""
        dialog = SettingsDialog(self.root, self.config_manager)

    def show_about(self):
        """Show about dialog."""
        messagebox.showinfo("Acerca de", 
                          "Descargador Masivo de Redes Sociales\n\n"
                          "Herramienta para descarga masiva de contenido desde múltiples plataformas.\n\n"
                          "Plataformas soportadas:\n"
                          "• YouTube (canales y videos)\n"
                          "• TikTok (cuentas y slideshows)\n"
                          "• Instagram (cuentas y posts)\n"
                          "• Reddit (subreddits)\n"
                          "• Redgifs (GIFs y usuarios)\n"
                          "• Pornhub (videos y canales)\n"
                          "• Twitter (tweets y timelines)\n"
                          "• Otros sitios (Xvideos, XNXX, YouPorn, etc.)")

    def update_status(self, message: str):
        """Update status bar message."""
        self.status_var.set(message)

    def manage_cookies(self):
        """Show cookie management dialog."""
        try:
            from gui.cookie_dialog import show_cookie_dialog
            from utils.cookie_manager import CookieManager

            # Let user select platform
            platforms = ["youtube", "tiktok", "instagram", "twitter"]

            # Create platform selection dialog
            platform_dialog = tk.Toplevel(self.root)
            platform_dialog.title("Seleccionar Plataforma")
            platform_dialog.geometry("300x200")
            platform_dialog.resizable(False, False)
            platform_dialog.transient(self.root)
            platform_dialog.grab_set()

            # Center dialog
            platform_dialog.geometry("+%d+%d" % (
                self.root.winfo_rootx() + 200,
                self.root.winfo_rooty() + 150
            ))

            frame = ttk.Frame(platform_dialog, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)

            ttk.Label(frame, text="Selecciona la plataforma para gestionar cookies:", 
                     font=('TkDefaultFont', 10)).pack(pady=(0, 20))

            selected_platform = tk.StringVar()

            for platform in platforms:
                ttk.Radiobutton(frame, text=platform.title(), 
                               variable=selected_platform, value=platform).pack(anchor=tk.W, pady=2)

            selected_platform.set(platforms[0])

            def on_select():
                platform = selected_platform.get()
                platform_dialog.destroy()

                cookie_manager = CookieManager(self.config_manager)
                result = show_cookie_dialog(self.root, platform, cookie_manager)

                if result == "saved":
                    messagebox.showinfo("Éxito", f"Cookies configuradas para {platform}")

            def on_cancel():
                platform_dialog.destroy()

            button_frame = ttk.Frame(frame)
            button_frame.pack(pady=(20, 0))

            ttk.Button(button_frame, text="Continuar", command=on_select).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="Cancelar", command=on_cancel).pack(side=tk.LEFT)

        except Exception as e:
            messagebox.showerror("Error", f"Error abriendo gestión de cookies: {e}")

    def _get_erome_downloader(self, config_manager):
        """Get Erome downloader if available."""
        try:
            from downloaders.erome_downloader import EromeDownloader
            return EromeDownloader(config_manager)
        except ImportError as e:
            logging.warning(f"Erome downloader not available: {e}")
            return None

    def _get_kwai_downloader(self, config_manager):
        """Get Kwai downloader if available."""
        try:
            from downloaders.kwai_downloader import KwaiDownloader
            return KwaiDownloader(config_manager)
        except ImportError as e:
            logging.warning(f"Kwai downloader not available: {e}")
            return None

    def create_erome_tab(self, parent):
        """Create Erome download interface."""
        # URL input
        ttk.Label(parent, text="URL de Album/Usuario de Erome:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.erome_url_var = tk.StringVar()
        url_entry = ttk.Entry(parent, textvariable=self.erome_url_var, width=60)
        url_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Options
        options_frame = ttk.LabelFrame(parent, text="Opciones", padding="5")
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.erome_max_pages = tk.IntVar(value=10)
        ttk.Label(options_frame, text="Máximo páginas (perfiles):").grid(row=0, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Spinbox(options_frame, from_=1, to=50, textvariable=self.erome_max_pages, width=10).grid(row=0, column=1, sticky=tk.W, padx=(5, 0), pady=(5, 0))

        # Info
        info_text = """• Soporta albums individuales y perfiles completos
• Descarga automática de videos e imágenes
• Organización por album/usuario"""

        info_label = ttk.Label(options_frame, text=info_text, justify=tk.LEFT, font=('TkDefaultFont', 8))
        info_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

        # Download button
        ttk.Button(parent, text="Añadir a Cola", command=self.add_erome_download).grid(row=3, column=0, pady=(10, 0))

        parent.columnconfigure(0, weight=1)

    def create_kwai_tab(self, parent):
        """Create Kwai download interface."""
        # URL input
        ttk.Label(parent, text="URL de Video/Usuario de Kwai:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.kwai_url_var = tk.StringVar()
        url_entry = ttk.Entry(parent, textvariable=self.kwai_url_var, width=60)
        url_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Options
        options_frame = ttk.LabelFrame(parent, text="Opciones", padding="5")
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.kwai_limit = tk.IntVar(value=50)
        ttk.Label(options_frame, text="Máximo videos:").grid(row=0, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Spinbox(options_frame, from_=1, to=500, textvariable=self.kwai_limit, width=10).grid(row=0, column=1, sticky=tk.W, padx=(5, 0), pady=(5, 0))

        # Info
        info_text = """• Videos cortos estilo TikTok
• Perfiles completos de usuarios
• Descarga en alta calidad"""

        info_label = ttk.Label(options_frame, text=info_text, justify=tk.LEFT, font=('TkDefaultFont', 8))
        info_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

        # Download button
        ttk.Button(parent, text="Añadir a Cola", command=self.add_kwai_download).grid(row=3, column=0, pady=(10, 0))

        parent.columnconfigure(0, weight=1)

    def create_batch_urls_tab(self, parent):
        """Create batch URLs download interface."""
        # Instructions
        ttk.Label(parent, text="URLs Múltiples (una por línea o separadas por comas):", 
                 font=('TkDefaultFont', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        # URL text area
        text_frame = ttk.Frame(parent)
        text_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self.batch_urls_text = tk.Text(text_frame, height=10, width=70, wrap=tk.WORD)
        self.batch_urls_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Scrollbar for text area
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.batch_urls_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.batch_urls_text.configure(yscrollcommand=scrollbar.set)

        # Options
        options_frame = ttk.LabelFrame(parent, text="Opciones de Procesamiento", padding="5")
        options_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.batch_auto_detect = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Auto-detectar plataforma", 
                       variable=self.batch_auto_detect).grid(row=0, column=0, sticky=tk.W)

        self.batch_skip_errors = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Continuar si hay errores", 
                       variable=self.batch_skip_errors).grid(row=0, column=1, sticky=tk.W, padx=(20, 0))

        self.batch_delay = tk.IntVar(value=5)
        ttk.Label(options_frame, text="Delay entre descargas (seg):").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Spinbox(options_frame, from_=1, to=30, textvariable=self.batch_delay, width=10).grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(5, 0))

        # Buttons frame
        buttons_frame = ttk.Frame(parent)
        buttons_frame.grid(row=3, column=0, sticky=tk.W, pady=(10, 0))

        ttk.Button(buttons_frame, text="Procesar URLs", command=self.process_batch_urls).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Limpiar", command=self.clear_batch_urls).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Validar URLs", command=self.validate_batch_urls).pack(side=tk.LEFT)

        # Status label
        self.batch_status_var = tk.StringVar(value="Listo para procesar URLs")
        ttk.Label(parent, textvariable=self.batch_status_var, font=('TkDefaultFont', 8)).grid(row=4, column=0, sticky=tk.W, pady=(10, 0))

        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

    def add_erome_download(self):
        """Add Erome download to queue."""
        url = self.erome_url_var.get().strip()
        if not url:
            messagebox.showwarning("Advertencia", "Por favor ingresa una URL de Erome")
            return

        options = {
            'max_pages': self.erome_max_pages.get()
        }

        self.download_queue.add_download('erome', url, options)
        self.erome_url_var.set("")

    def add_kwai_download(self):
        """Add Kwai download to queue."""
        url = self.kwai_url_var.get().strip()
        if not url:
            messagebox.showwarning("Advertencia", "Por favor ingresa una URL de Kwai")
            return

        options = {
            'limit': self.kwai_limit.get()
        }

        self.download_queue.add_download('kwai', url, options)
        self.kwai_url_var.set("")

    def process_batch_urls(self):
        """Process multiple URLs from text area."""
        urls_text = self.batch_urls_text.get("1.0", tk.END).strip()

        if not urls_text:
            messagebox.showwarning("Advertencia", "Por favor ingresa al menos una URL")
            return

        # Parse URLs
        urls = self._parse_multiple_urls(urls_text)

        if not urls:
            messagebox.showwarning("Advertencia", "No se encontraron URLs válidas")
            return

        self.batch_status_var.set(f"Procesando {len(urls)} URLs...")

        # Process each URL
        added_count = 0
        failed_count = 0

        for url in urls:
            try:
                platform = self._detect_url_platform(url)

                if platform and platform in self.downloaders:
                    options = self._get_default_options_for_platform(platform)
                    self.download_queue.add_download(platform, url, options)
                    added_count += 1
                else:
                    # Try generic downloader
                    options = {'auto_detect': True, 'quality': 'best'}
                    self.download_queue.add_download('generic', url, options)
                    added_count += 1

            except Exception as e:
                logging.warning(f"Failed to process URL {url}: {e}")
                failed_count += 1

                if not self.batch_skip_errors.get():
                    messagebox.showerror("Error", f"Error procesando URL: {url}\n{str(e)}")
                    break

        self.batch_status_var.set(f"Completado: {added_count} añadidas, {failed_count} fallidas")

        if added_count > 0:
            messagebox.showinfo("Completado", f"Se añadieron {added_count} descargas a la cola")

    def validate_batch_urls(self):
        """Validate URLs in text area."""
        urls_text = self.batch_urls_text.get("1.0", tk.END).strip()

        if not urls_text:
            messagebox.showwarning("Advertencia", "Por favor ingresa URLs para validar")
            return

        urls = self._parse_multiple_urls(urls_text)

        valid_count = 0
        invalid_urls = []

        for url in urls:
            if self._is_valid_url(url):
                valid_count += 1
            else:
                invalid_urls.append(url)

        message = f"URLs válidas: {valid_count}\nURLs inválidas: {len(invalid_urls)}"

        if invalid_urls:
            message += f"\n\nURLs inválidas:\n" + "\n".join(invalid_urls[:5])
            if len(invalid_urls) > 5:
                message += f"\n... y {len(invalid_urls) - 5} más"

        messagebox.showinfo("Validación de URLs", message)

    def clear_batch_urls(self):
        """Clear the batch URLs text area."""
        self.batch_urls_text.delete("1.0", tk.END)
        self.batch_status_var.set("Listo para procesar URLs")

    def _parse_multiple_urls(self, text: str) -> list[str]:
        """Parse multiple URLs from text input."""
        import re

        # Split by common separators
        urls = []

        # Split by newlines first
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line contains multiple URLs separated by commas, spaces, or semicolons
            if ',' in line:
                parts = line.split(',')
            elif ';' in line:
                parts = line.split(';')
            elif ' http' in line:
                parts = re.split(r'\s+(?=https?://)', line)
            else:
                parts = [line]

            for part in parts:
                part = part.strip()
                if part and self._is_valid_url(part):
                    urls.append(part)

        return list(set(urls))  # Remove duplicates

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        import re

        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        return bool(url_pattern.match(url))

    def _detect_url_platform(self, url: str) -> str:
        """Detect platform from URL."""
        url_lower = url.lower()

        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        elif 'tiktok.com' in url_lower:
            return 'tiktok'
        elif 'instagram.com' in url_lower:
            return 'instagram'
        elif 'reddit.com' in url_lower:
            return 'reddit'
        elif 'redgifs.com' in url_lower:
            return 'redgifs'
        elif 'pornhub.com' in url_lower:
            return 'pornhub'
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            return 'twitter'
        elif 'erome.com' in url_lower:
            return 'erome'
        elif 'kwai.com' in url_lower:
            return 'kwai'
        else:
            return 'generic'

    def _get_default_options_for_platform(self, platform: str) -> dict:
        """Get default options for each platform."""
        defaults = {
            'youtube': {'quality': 'best', 'audio_only': False, 'entire_channel': False},
            'tiktok': {'process_slideshows': True, 'limit': 50},
            'instagram': {'include_stories': False, 'limit': 50},
            'reddit': {'sort': 'hot', 'limit': 100},
            'redgifs': {'quality': 'hd', 'limit': 50},
            'pornhub': {'quality': '720p', 'limit': 25},
            'twitter': {'media_only': True, 'limit': 100},
            'erome': {'max_pages': 10},
            'kwai': {'limit': 50},
            'generic': {'auto_detect': True, 'quality': 'best'}
        }

        return defaults.get(platform, {})