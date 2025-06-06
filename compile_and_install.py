
#!/usr/bin/env python3
"""
Script completo para compilar el ejecutable y crear el instalador
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_dependencies():
    """Instalar dependencias necesarias."""
    print("📦 Instalando dependencias...")
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements_optional.txt"], check=True)
        print("✅ Dependencias instaladas correctamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando dependencias: {e}")
        return False

def build_executable():
    """Compilar el ejecutable."""
    print("🔨 Compilando ejecutable...")
    
    # Limpiar compilaciones anteriores
    for folder in ["dist", "build"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"🧹 Limpiando {folder}...")
    
    try:
        # Ejecutar PyInstaller
        result = subprocess.run([
            "pyinstaller", 
            "--onefile", 
            "--windowed",
            "--name=SocialMediaDownloader",
            "--clean",
            "--add-data=config;config",
            "--add-data=gui;gui",
            "--add-data=utils;utils", 
            "--add-data=downloaders;downloaders",
            "--hidden-import=tkinter",
            "--hidden-import=tkinter.ttk",
            "--hidden-import=tkinter.messagebox",
            "--hidden-import=PIL",
            "--hidden-import=requests",
            "--hidden-import=yt_dlp",
            "--hidden-import=cryptography",
            "--hidden-import=cryptography.fernet",
            "--hidden-import=keyring",
            "--hidden-import=instaloader",
            "--collect-all=yt_dlp",
            "--collect-all=cryptography",
            "main.py"
        ], check=True)
        
        if os.path.exists("dist/SocialMediaDownloader.exe"):
            print("✅ Ejecutable compilado exitosamente")
            print(f"📁 Ubicación: {os.path.abspath('dist/SocialMediaDownloader.exe')}")
            return True
        else:
            print("❌ El ejecutable no se generó correctamente")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error compilando ejecutable: {e}")
        return False

def create_installer():
    """Crear el instalador NSIS."""
    print("📦 Creando instalador...")
    
    # Verificar que existe el ejecutable
    if not os.path.exists("dist/SocialMediaDownloader.exe"):
        print("❌ No se encontró SocialMediaDownloader.exe en dist/")
        return False
    
    # Crear script NSIS actualizado
    nsis_script = """
!define APP_NAME "Social Media Bulk Downloader"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "Social Media Tools"
!define APP_URL "https://github.com/tu-usuario/social-media-downloader"
!define APP_EXE "SocialMediaDownloader.exe"

Name "${APP_NAME}"
OutFile "SocialMediaDownloader_Setup.exe"
InstallDir "$PROGRAMFILES\\${APP_NAME}"
RequestExecutionLevel admin

Page components
Page directory
Page instfiles

UninstPage uninstConfirm
UninstPage instfiles

Section "Aplicación Principal" SEC01
    SetOutPath "$INSTDIR"
    
    ; Verificar que el archivo existe antes de intentar copiarlo
    IfFileExists "dist\\${APP_EXE}" 0 FileNotFound
        File "dist\\${APP_EXE}"
        Goto FileCopied
    
    FileNotFound:
        MessageBox MB_OK "Error: No se encontró ${APP_EXE} en la carpeta dist/"
        Abort
    
    FileCopied:
    
    ; Crear acceso directo en el escritorio
    CreateShortCut "$DESKTOP\\${APP_NAME}.lnk" "$INSTDIR\\${APP_EXE}"
    
    ; Crear acceso directo en el menú inicio
    CreateDirectory "$SMPROGRAMS\\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk" "$INSTDIR\\${APP_EXE}"
    CreateShortCut "$SMPROGRAMS\\${APP_NAME}\\Desinstalar.lnk" "$INSTDIR\\uninstall.exe"
    
    ; Crear desinstalador
    WriteUninstaller "$INSTDIR\\uninstall.exe"
    
    ; Registrar en el panel de control
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "UninstallString" "$INSTDIR\\uninstall.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "URLInfoAbout" "${APP_URL}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "NoModify" 1
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "NoRepair" 1
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\\${APP_EXE}"
    Delete "$INSTDIR\\uninstall.exe"
    
    Delete "$DESKTOP\\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\\${APP_NAME}\\Desinstalar.lnk"
    RMDir "$SMPROGRAMS\\${APP_NAME}"
    RMDir "$INSTDIR"
    
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}"
SectionEnd
"""
    
    try:
        with open("installer.nsi", "w", encoding="utf-8") as f:
            f.write(nsis_script)
        
        print("✅ Script NSIS creado: installer.nsi")
        
        # Intentar compilar con NSIS si está disponible
        try:
            result = subprocess.run(["makensis", "installer.nsi"], 
                                  capture_output=True, text=True, check=True)
            print("✅ Instalador creado exitosamente: SocialMediaDownloader_Setup.exe")
            return True
            
        except FileNotFoundError:
            print("⚠️  NSIS no encontrado en PATH")
            print("📋 Para crear el instalador manualmente:")
            print("   1. Instala NSIS desde https://nsis.sourceforge.io/")
            print("   2. Ejecuta: makensis installer.nsi")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error creando instalador: {e}")
            print("Output:", e.stdout)
            print("Error:", e.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error creando script NSIS: {e}")
        return False

def main():
    """Proceso completo de compilación e instalación."""
    print("🚀 Iniciando proceso completo de compilación...")
    
    steps = [
        ("Instalando dependencias", install_dependencies),
        ("Compilando ejecutable", build_executable), 
        ("Creando instalador", create_installer)
    ]
    
    for step_name, step_func in steps:
        print(f"\n📋 {step_name}...")
        if not step_func():
            print(f"❌ Falló: {step_name}")
            return False
    
    print("\n🎉 ¡Proceso completado exitosamente!")
    print("📁 Archivos generados:")
    print("   • dist/SocialMediaDownloader.exe")
    print("   • SocialMediaDownloader_Setup.exe (si NSIS está disponible)")
    
    return True

if __name__ == "__main__":
    main()
