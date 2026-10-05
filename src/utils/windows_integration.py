"""Windows integration without blocking the image viewer."""
import ctypes
import os
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import quote


def _reveal(path):
    shell = ctypes.windll.shell32
    ole = ctypes.windll.ole32
    ole.CoInitialize(None)
    shell.ILCreateFromPathW.argtypes = [ctypes.c_wchar_p]
    shell.ILCreateFromPathW.restype = ctypes.c_void_p
    shell.ILFree.argtypes = [ctypes.c_void_p]
    shell.SHOpenFolderAndSelectItems.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
    shell.SHOpenFolderAndSelectItems.restype = ctypes.c_long
    pidl = None
    try:
        pidl = shell.ILCreateFromPathW(path)
        if not pidl or shell.SHOpenFolderAndSelectItems(pidl, 0, None, 0) < 0:
            subprocess.Popen(['explorer.exe', f'/select,{path}'])
    finally:
        if pidl:
            shell.ILFree(pidl)
        ole.CoUninitialize()


def reveal_in_explorer(path):
    # No resolve()/stat() here: they can block for seconds on network shares.
    path = os.path.abspath(os.path.normpath(str(path)))
    threading.Thread(target=_reveal, args=(path,), daemon=True).start()


COMMON_IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.jfif', '.png', '.gif', '.bmp', '.tif', '.tiff',
                           '.webp', '.avif', '.ico')


def register_default_viewer(executable):
    import winreg
    executable = str(Path(executable).absolute())
    def write(key, name, value):
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as handle:
            winreg.SetValueEx(handle, name, 0, winreg.REG_SZ, value)
    progid = 'TABaTABCash.Image'
    classes = r'Software\Classes'
    write(classes + '\\' + progid, '', 'Image TABaTAB Cash')
    write(classes + '\\' + progid + r'\DefaultIcon', '', f'"{executable}",0')
    write(classes + '\\' + progid + r'\shell\open\command', '', f'"{executable}" "%1"')
    application = classes + r'\Applications\TABaTAB Cash.exe'
    write(application, 'FriendlyAppName', 'TABaTAB Cash')
    write(application + r'\DefaultIcon', '', f'"{executable}",0')
    write(application + r'\shell\open\command', '', f'"{executable}" "%1"')
    capabilities = r'Software\TABaTAB Cash\Capabilities'
    write(capabilities, 'ApplicationName', 'TABaTAB Cash')
    write(capabilities, 'ApplicationDescription', 'Visionneuse de photos à onglets')
    write(capabilities, 'ApplicationIcon', f'"{executable}",0')
    for extension in COMMON_IMAGE_EXTENSIONS:
        write(capabilities + r'\FileAssociations', extension, progid)
        write(classes + '\\' + extension + r'\OpenWithProgids', progid, '')
        write(application + r'\SupportedTypes', extension, '')
    write(r'Software\RegisteredApplications', 'TABaTAB Cash', capabilities)
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


def configure_default_viewer(parent):
    from PyQt6.QtWidgets import QMessageBox
    try:
        if not getattr(sys, 'frozen', False):
            raise OSError('Utilisez la version portable compilée pour définir les associations Windows.')
        register_default_viewer(sys.executable)
        os.startfile('ms-settings:defaultapps?registeredAppUser=' + quote('TABaTAB Cash'))
    except OSError as error:
        QMessageBox.warning(parent, 'Applications par défaut', str(error))
