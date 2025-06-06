
"""
Cookie management dialog for manual cookie input and browser extraction.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json
from typing import Dict, Any, Optional

class CookieDialog:
    """Dialog for managing cookies manually."""
    
    def __init__(self, parent, platform: str, cookie_manager):
        self.parent = parent
        self.platform = platform
        self.cookie_manager = cookie_manager
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Gestionar Cookies - {platform.title()}")
        self.dialog.geometry("800x600")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.setup_ui()
        self.load_existing_cookies()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + 50,
            parent.winfo_rooty() + 50
        ))
        
    def setup_ui(self):
        """Setup the dialog UI."""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Platform info
        ttk.Label(main_frame, text=f"Gestión de Cookies para {self.platform.title()}", 
                 font=('TkDefaultFont', 12, 'bold')).grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # Method selection
        method_frame = ttk.LabelFrame(main_frame, text="Método de Cookie", padding="5")
        method_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        method_frame.columnconfigure(2, weight=1)
        
        self.method_var = tk.StringVar(value="manual")
        
        ttk.Radiobutton(method_frame, text="Manual", variable=self.method_var, 
                       value="manual", command=self.on_method_change).grid(row=0, column=0, padx=(0, 10))
        ttk.Radiobutton(method_frame, text="Desde Navegador", variable=self.method_var, 
                       value="browser", command=self.on_method_change).grid(row=0, column=1, padx=(0, 10))
        
        # Browser selection (initially hidden)
        self.browser_frame = ttk.Frame(method_frame)
        self.browser_frame.grid(row=0, column=2, sticky=(tk.W, tk.E))
        
        ttk.Label(self.browser_frame, text="Navegador:").grid(row=0, column=0, padx=(10, 5))
        self.browser_combo = ttk.Combobox(self.browser_frame, values=["chrome", "brave", "firefox", "edge"], 
                                         state="readonly", width=10)
        self.browser_combo.set("chrome")
        self.browser_combo.grid(row=0, column=1, padx=(0, 10))
        
        ttk.Button(self.browser_frame, text="Extraer", 
                  command=self.extract_browser_cookies).grid(row=0, column=2)
        
        # Format selection for manual input
        self.format_frame = ttk.Frame(method_frame)
        self.format_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Label(self.format_frame, text="Formato:").grid(row=0, column=0, padx=(0, 5))
        self.format_combo = ttk.Combobox(self.format_frame, 
                                        values=["netscape", "json", "header"], 
                                        state="readonly", width=10)
        self.format_combo.set("netscape")
        self.format_combo.grid(row=0, column=1, padx=(0, 10))
        
        ttk.Button(self.format_frame, text="Plantilla", 
                  command=self.load_template).grid(row=0, column=2, padx=(10, 0))
        ttk.Button(self.format_frame, text="Desde Archivo", 
                  command=self.load_from_file).grid(row=0, column=3, padx=(5, 0))
        
        # Instructions
        instructions_frame = ttk.LabelFrame(main_frame, text="Instrucciones", padding="5")
        instructions_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        instructions = {
            "manual": """Cómo obtener cookies manualmente:
1. Abre tu navegador y ve a {platform}
2. Inicia sesión normalmente
3. Presiona F12 > Application/Almacenamiento > Cookies
4. Copia los valores importantes (session_id, auth_token, etc.)
5. Pégalos en el formato correcto abajo""",
            
            "browser": """Extracción automática desde navegador:
1. Asegúrate de estar logueado en {platform}
2. Cierra todas las ventanas del navegador
3. Selecciona tu navegador y presiona 'Extraer'
4. Las cookies se extraerán automáticamente"""
        }
        
        self.instruction_label = ttk.Label(instructions_frame, 
                                          text=instructions["manual"].format(platform=self.platform),
                                          wraplength=750, justify=tk.LEFT)
        self.instruction_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Cookie content
        content_frame = ttk.LabelFrame(main_frame, text="Contenido de Cookies", padding="5")
        content_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        self.cookie_text = scrolledtext.ScrolledText(content_frame, wrap=tk.WORD, width=80, height=20)
        self.cookie_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Button(button_frame, text="Validar", 
                  command=self.validate_cookies).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Guardar", 
                  command=self.save_cookies).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Cargar Existentes", 
                  command=self.load_existing_cookies).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(button_frame, text="Cancelar", 
                  command=self.cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Aplicar", 
                  command=self.apply_cookies).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Initially hide browser frame
        self.on_method_change()
        
    def on_method_change(self):
        """Handle method selection change."""
        method = self.method_var.get()
        
        if method == "browser":
            self.browser_frame.grid()
            self.format_frame.grid_remove()
            self.instruction_label.config(text=f"""Extracción automática desde navegador:
1. Asegúrate de estar logueado en {self.platform}
2. Cierra todas las ventanas del navegador
3. Selecciona tu navegador y presiona 'Extraer'
4. Las cookies se extraerán automáticamente""")
        else:
            self.browser_frame.grid_remove()
            self.format_frame.grid()
            self.instruction_label.config(text=f"""Cómo obtener cookies manualmente:
1. Abre tu navegador y ve a {self.platform}
2. Inicia sesión normalmente
3. Presiona F12 > Application/Almacenamiento > Cookies
4. Copia los valores importantes (session_id, auth_token, etc.)
5. Pégalos en el formato correcto abajo""")
            
    def extract_browser_cookies(self):
        """Extract cookies from browser."""
        try:
            browser = self.browser_combo.get()
            success = self.cookie_manager.store_browser_cookies(self.platform, browser)
            
            if success:
                messagebox.showinfo("Éxito", f"Cookies extraídas exitosamente desde {browser}")
                self.load_existing_cookies()
            else:
                messagebox.showerror("Error", f"No se pudieron extraer cookies desde {browser}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error extrayendo cookies: {e}")
            
    def load_template(self):
        """Load cookie template."""
        try:
            template = self.cookie_manager.export_cookies_template(self.platform)
            self.cookie_text.delete(1.0, tk.END)
            self.cookie_text.insert(1.0, template)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error cargando plantilla: {e}")
            
    def load_from_file(self):
        """Load cookies from file."""
        try:
            file_path = filedialog.askopenfilename(
                title="Seleccionar archivo de cookies",
                filetypes=[
                    ("Archivos de texto", "*.txt"),
                    ("Archivos JSON", "*.json"),
                    ("Todos los archivos", "*.*")
                ]
            )
            
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                self.cookie_text.delete(1.0, tk.END)
                self.cookie_text.insert(1.0, content)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error cargando archivo: {e}")
            
    def load_existing_cookies(self):
        """Load existing cookies if available."""
        try:
            cookies_file = self.cookie_manager.get_cookies_file(self.platform)
            if cookies_file:
                with open(cookies_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                self.cookie_text.delete(1.0, tk.END)
                self.cookie_text.insert(1.0, content)
                
        except Exception as e:
            pass  # No existing cookies is fine
            
    def validate_cookies(self):
        """Validate the entered cookies."""
        try:
            cookies_text = self.cookie_text.get(1.0, tk.END).strip()
            if not cookies_text:
                messagebox.showwarning("Advertencia", "No hay contenido de cookies para validar")
                return
                
            # Create temporary file for validation
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                temp_file.write(cookies_text)
                temp_file_path = temp_file.name
                
            # Validate
            is_valid = self.cookie_manager.validate_cookies_file(temp_file_path)
            
            # Clean up
            import os
            os.unlink(temp_file_path)
            
            if is_valid:
                messagebox.showinfo("Válido", "Las cookies son válidas")
            else:
                messagebox.showwarning("Inválido", "Las cookies no son válidas o están mal formateadas")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error validando cookies: {e}")
            
    def save_cookies(self):
        """Save cookies to file."""
        try:
            cookies_text = self.cookie_text.get(1.0, tk.END).strip()
            if not cookies_text:
                messagebox.showwarning("Advertencia", "No hay contenido de cookies para guardar")
                return
                
            format_type = self.format_combo.get()
            success = self.cookie_manager.store_manual_cookies(self.platform, cookies_text, format_type)
            
            if success:
                messagebox.showinfo("Éxito", "Cookies guardadas exitosamente")
                self.result = "saved"
            else:
                messagebox.showerror("Error", "No se pudieron guardar las cookies")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error guardando cookies: {e}")
            
    def apply_cookies(self):
        """Apply cookies and close dialog."""
        self.save_cookies()
        if self.result == "saved":
            self.dialog.destroy()
            
    def cancel(self):
        """Cancel and close dialog."""
        self.result = "cancelled"
        self.dialog.destroy()
        
def show_cookie_dialog(parent, platform: str, cookie_manager) -> Optional[str]:
    """Show cookie management dialog."""
    dialog = CookieDialog(parent, platform, cookie_manager)
    parent.wait_window(dialog.dialog)
    return dialog.result
