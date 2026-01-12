$TargetFile = "$PSScriptRoot\run_babel.bat"
$ShortcutFile = "$env:USERPROFILE\Desktop\Project Babel.lnk"
$IconPath = "C:\Users\vanes\THI\Vibe Coding\Project Babel\src\assets\icon.ico"

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutFile)
$Shortcut.TargetPath = $TargetFile
$Shortcut.WorkingDirectory = "$PSScriptRoot"

if (Test-Path $IconPath) {
    $Shortcut.IconLocation = $IconPath
} else {
    Write-Warning "Icon file not found at $IconPath. Using default icon."
}

$Shortcut.Save()
Write-Host "Shortcut created at $ShortcutFile"
