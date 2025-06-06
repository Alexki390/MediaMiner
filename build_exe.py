
#!/usr/bin/env python3
"""
Script para compilar el Social Media Bulk Downloader a un ejecutable .exe
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def build_executable():
    """Construye el ejecutable usando PyInstaller."""
    
    print("🔨 Iniciando compilación del ejecutable...")
    
    # Verificar que PyInstaller esté instalado
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__} encontrado")
    except ImportError:
        print("❌ PyInstaller no está instalado. Instalando...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Limpiar compilaciones anteriores
    if os.path.exists("dist"):
        shutil.rmtree("dist")
        print("🧹 Limpiando compilaciones anteriores...")
    
    if os.path.exists("build"):
        shutil.rmtree("build")
    
    # Configuración de PyInstaller
    pyinstaller_args = [
        "pyinstaller",
        "--onefile",  # Un solo archivo ejecutable
        "--windowed",  # Sin ventana de consola
        "--name=SocialMediaDownloader",
        "--clean",  # Limpiar cache
        # Incluir recursos y módulos
        "--add-data=config;config",
        "--add-data=gui;gui", 
        "--add-data=utils;utils",
        "--add-data=downloaders;downloaders",
        # Imports ocultos críticos
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.messagebox",
        "--hidden-import=tkinter.filedialog",
        "--hidden-import=PIL",
        "--hidden-import=PIL._tkinter_finder",
        "--hidden-import=requests",
        "--hidden-import=yt_dlp",
        "--hidden-import=trafilatura", 
        "--hidden-import=cryptography",
        "--hidden-import=cryptography.fernet",
        "--hidden-import=keyring",
        "--hidden-import=keyring.backends",
        "--hidden-import=instaloader",
        "--hidden-import=queue",
        "--hidden-import=threading",
        "--hidden-import=json",
        "--hidden-import=pickle",
        "--hidden-import=base64",
        "--hidden-import=hashlib",
        "--hidden-import=os",
        "--hidden-import=sys",
        "--hidden-import=pathlib",
        "--hidden-import=subprocess",
        "--hidden-import=tempfile",
        "--hidden-import=logging",
        "--hidden-import=time",
        # Recopilar todos los módulos
        "--collect-all=yt_dlp",
        "--collect-all=trafilatura",
        "--collect-all=cryptography",
        "--collect-all=keyring",
        # Excluir módulos innecesarios para reducir tamaño
        "--exclude-module=matplotlib",
        "--exclude-module=numpy",
        "--exclude-module=pandas",
        "--exclude-module=scipy",
        "main.py"
    ]
    
    try:
        # Ejecutar PyInstaller
        print("⚡ Compilando ejecutable...")
        result = subprocess.run(pyinstaller_args, check=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ ¡Ejecutable creado exitosamente!")
            print(f"📁 Ubicación: {os.path.abspath('dist/SocialMediaDownloader.exe')}")
            
            # Crear carpeta de distribución
            dist_folder = "SocialMediaDownloader_Portable"
            if os.path.exists(dist_folder):
                shutil.rmtree(dist_folder)
            
            os.makedirs(dist_folder)
            
            # Copiar ejecutable
            shutil.copy("dist/SocialMediaDownloader.exe", dist_folder)
            
            # Crear archivo README
            with open(f"{dist_folder}/README.txt", "w", encoding="utf-8") as f:
                f.write("""Social Media Bulk Downloader - Versión Portable
============================================

Instrucciones de uso:
1. Ejecuta SocialMediaDownloader.exe
2. La aplicación creará automáticamente las carpetas necesarias
3. Los archivos descargados se guardarán en la carpeta 'downloads'

Requisitos del sistema:
- Windows 7 o superior
- Conexión a Internet
- Al menos 100MB de espacio libre

Soporte:
- Para cuentas privadas de Instagram/TikTok necesitarás credenciales válidas
- FFmpeg se descargará automáticamente si es necesario para procesamiento de video

¡Disfruta descargando contenido de redes sociales!
""")
            
            print(f"📦 Carpeta portable creada: {dist_folder}/")
            print("🎉 ¡Listo para distribuir!")
            
        else:
            print("❌ Error durante la compilación:")
            print(result.stderr)
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error ejecutando PyInstaller: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    build_executable()
