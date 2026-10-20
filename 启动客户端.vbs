Set WshShell = CreateObject("WScript.Shell")
currentDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = currentDir
WshShell.Run """C:\Program Files\Python311\pythonw.exe"" """ & currentDir & "\dashboard.py""", 0, False
