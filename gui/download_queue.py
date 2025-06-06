"""
Download queue management GUI component.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import logging
from typing import Dict, Any, List
from datetime import datetime

class DownloadQueue:
    """Manages the download queue with progress tracking."""
    
    def __init__(self, parent_frame: ttk.Frame, downloaders: Dict):
        self.parent_frame = parent_frame
        self.downloaders = downloaders
        self.queue_items = []
        self.download_queue = queue.Queue()
        self.is_downloading = False
        self.current_thread = None
        
        self.setup_widgets()
        
    def setup_widgets(self):
        """Setup the queue interface widgets."""
        # Control buttons frame
        controls_frame = ttk.Frame(self.parent_frame)
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.start_button = ttk.Button(controls_frame, text="Start Downloads", 
                                     command=self.start_downloads)
        self.start_button.grid(row=0, column=0, padx=(0, 5))
        
        self.pause_button = ttk.Button(controls_frame, text="Pause", 
                                     command=self.pause_downloads, state=tk.DISABLED)
        self.pause_button.grid(row=0, column=1, padx=(0, 5))
        
        self.clear_button = ttk.Button(controls_frame, text="Clear Completed", 
                                     command=self.clear_completed)
        self.clear_button.grid(row=0, column=2, padx=(0, 5))
        
        # Queue list
        list_frame = ttk.Frame(self.parent_frame)
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Treeview for queue items
        columns = ('Platform', 'URL', 'Status', 'Progress', 'Added')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)
        
        # Configure columns
        self.tree.heading('Platform', text='Platform')
        self.tree.heading('URL', text='URL/Username')
        self.tree.heading('Status', text='Status')
        self.tree.heading('Progress', text='Progress')
        self.tree.heading('Added', text='Added')
        
        self.tree.column('Platform', width=80, minwidth=80)
        self.tree.column('URL', width=200, minwidth=150)
        self.tree.column('Status', width=100, minwidth=80)
        self.tree.column('Progress', width=100, minwidth=80)
        self.tree.column('Added', width=120, minwidth=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Context menu
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="Remove", command=self.remove_selected)
        self.context_menu.add_command(label="Retry", command=self.retry_selected)
        
        self.tree.bind("<Button-3>", self.show_context_menu)
        
    def add_download(self, platform: str, url: str, options: Dict[str, Any]):
        """Add a new download to the queue."""
        item_id = len(self.queue_items)
        queue_item = {
            'id': item_id,
            'platform': platform,
            'url': url,
            'options': options,
            'status': 'Queued',
            'progress': '0%',
            'added': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'error': None
        }
        
        self.queue_items.append(queue_item)
        
        # Add to treeview
        self.tree.insert('', tk.END, iid=item_id, values=(
            platform.capitalize(),
            url[:50] + '...' if len(url) > 50 else url,
            'Queued',
            '0%',
            queue_item['added']
        ))
        
        logging.info(f"Added {platform} download to queue: {url}")
        
    def start_downloads(self):
        """Start processing the download queue."""
        if self.is_downloading:
            return
            
        queued_items = [item for item in self.queue_items if item['status'] == 'Queued']
        if not queued_items:
            messagebox.showinfo("Info", "No queued downloads to process")
            return
            
        self.is_downloading = True
        self.start_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        
        # Start download thread
        self.current_thread = threading.Thread(target=self.process_downloads, daemon=True)
        self.current_thread.start()
        
    def process_downloads(self):
        """Process downloads in background thread."""
        try:
            for item in self.queue_items:
                if not self.is_downloading:  # Check if paused/stopped
                    break
                    
                if item['status'] != 'Queued':
                    continue
                    
                self.update_item_status(item['id'], 'Downloading', '0%')
                
                try:
                    # Get appropriate downloader
                    downloader = self.downloaders.get(item['platform'])
                    if not downloader:
                        raise Exception(f"No downloader available for {item['platform']}")
                    
                    # Set up progress callback
                    def progress_callback(progress):
                        self.update_item_progress(item['id'], f"{progress}%")
                    
                    # Start download
                    result = downloader.download(item['url'], item['options'], progress_callback)
                    
                    if result.get('success', False):
                        self.update_item_status(item['id'], 'Completed', '100%')
                        logging.info(f"Completed download: {item['url']}")
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        self.update_item_status(item['id'], 'Failed', '0%')
                        item['error'] = error_msg
                        logging.error(f"Download failed for {item['url']}: {error_msg}")
                        
                except Exception as e:
                    self.update_item_status(item['id'], 'Failed', '0%')
                    item['error'] = str(e)
                    logging.error(f"Download error for {item['url']}: {e}")
                    
        except Exception as e:
            logging.error(f"Error in download processing: {e}")
        finally:
            self.is_downloading = False
            self.parent_frame.after(0, self.download_finished)
            
    def download_finished(self):
        """Called when download processing is finished."""
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        
    def pause_downloads(self):
        """Pause the download process."""
        self.is_downloading = False
        self.pause_button.config(state=tk.DISABLED)
        
    def update_item_status(self, item_id: int, status: str, progress: str):
        """Update the status of a queue item."""
        def update():
            try:
                item = self.queue_items[item_id]
                item['status'] = status
                item['progress'] = progress
                
                # Update treeview
                self.tree.item(item_id, values=(
                    item['platform'].capitalize(),
                    item['url'][:50] + '...' if len(item['url']) > 50 else item['url'],
                    status,
                    progress,
                    item['added']
                ))
            except (IndexError, tk.TclError):
                pass  # Item may have been removed
                
        self.parent_frame.after(0, update)
        
    def update_item_progress(self, item_id: int, progress: str):
        """Update just the progress of a queue item."""
        def update():
            try:
                item = self.queue_items[item_id]
                item['progress'] = progress
                
                # Update only the progress column
                values = list(self.tree.item(item_id)['values'])
                if len(values) >= 4:
                    values[3] = progress
                    self.tree.item(item_id, values=values)
            except (IndexError, tk.TclError):
                pass
                
        self.parent_frame.after(0, update)
        
    def clear_completed(self):
        """Remove completed downloads from the queue."""
        completed_ids = []
        for i, item in enumerate(self.queue_items):
            if item['status'] in ['Completed', 'Failed']:
                completed_ids.append(i)
                
        # Remove from treeview (in reverse order to maintain indices)
        for item_id in reversed(completed_ids):
            try:
                self.tree.delete(item_id)
            except tk.TclError:
                pass
                
        # Remove from queue_items
        self.queue_items = [item for i, item in enumerate(self.queue_items) 
                           if i not in completed_ids]
        
        # Update IDs
        for i, item in enumerate(self.queue_items):
            item['id'] = i
            
    def show_context_menu(self, event):
        """Show context menu on right-click."""
        item = self.tree.selection()
        if item:
            self.context_menu.post(event.x_root, event.y_root)
            
    def remove_selected(self):
        """Remove selected item from queue."""
        selection = self.tree.selection()
        if not selection:
            return
            
        item_id = int(selection[0])
        if 0 <= item_id < len(self.queue_items):
            # Don't remove if currently downloading
            if self.queue_items[item_id]['status'] == 'Downloading':
                messagebox.showwarning("Warning", "Cannot remove item that is currently downloading")
                return
                
            self.tree.delete(item_id)
            del self.queue_items[item_id]
            
            # Update IDs
            for i, item in enumerate(self.queue_items):
                item['id'] = i
                
    def retry_selected(self):
        """Retry selected failed download."""
        selection = self.tree.selection()
        if not selection:
            return
            
        item_id = int(selection[0])
        if 0 <= item_id < len(self.queue_items):
            item = self.queue_items[item_id]
            if item['status'] == 'Failed':
                item['status'] = 'Queued'
                item['progress'] = '0%'
                item['error'] = None
                self.update_item_status(item_id, 'Queued', '0%')
