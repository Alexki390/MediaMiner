
#!/usr/bin/env python3
"""
Script para crear un instalador de Windows usando NSIS (opcional)
Requiere tener NSIS instalado en el sistema
"""

import os
import sys

def create_nsis_script():
    """Crea el script NSIS para el instalador."""
    
    nsis_script = """
!define APP_NAME "Social Media Bulk Downloader"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "Tu Nombre"
!define APP_URL "https://tu-sitio-web.com"
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
    File "dist\\SocialMediaDownloader.exe"
    
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
    
    with open("installer.nsi", "w", encoding="utf-8") as f:
        f.write(nsis_script)
    
    print("✅ Script NSIS creado: installer.nsi")
    print("📋 Para crear el instalador:")
    print("   1. Instala NSIS desde https://nsis.sourceforge.io/")
    print("   2. Ejecuta: makensis installer.nsi")

if __name__ == "__main__":
    create_nsis_script()
