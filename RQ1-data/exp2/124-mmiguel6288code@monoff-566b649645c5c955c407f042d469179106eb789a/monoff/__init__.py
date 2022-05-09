from sys import platform
from os import system

__version__ = '0.0.2'

def monoff():
    if platform == 'linux':
        system('xset dpms force off')
    elif platform == 'win32' or platform == 'cygwin':
        from win32gui import SendMessage
        from win32con import HWND_BROADCAST, WM_SYSCOMMAND
        from os import getpid
        from threading import Timer
        SC_MONITORPOWER = 0xF170
        SC_MONITORPOWER_OFF = 2
        def end_thread():
            pid = getpid()
            system('taskkill /pid %s /f' % pid)
        monoff_thread = Timer(1,end_thread)
        monoff_thread.start()
        SendMessage(HWND_BROADCAST,WM_SYSCOMMAND,SC_MONITORPOWER,SC_MONITORPOWER_OFF)
        monoff_thread.cancel()
    elif platform == 'darwin':
        from os import system
        system('pmset displaysleepnow')
    else:
        raise Exception('Monoff does not support this platform: %s' % repr(platform))