Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c python server.py > server_restart.log 2>&1", 0, False
