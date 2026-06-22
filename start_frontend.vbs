Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c cd frontend && npm run dev > ..\vite.log 2>&1", 0, False
