Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = base
sh.Run "cmd /c run_task.bat", 0, False
