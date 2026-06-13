#SingleInstance Force

; Hotkey: Ctrl + Alt + P
^!p::{
    ; Types the commands into the active window (cmd, PowerShell, etc.)
    SendText("git add .`n")
    Sleep(300)
    SendText('git commit -m "auto-push"`n')
    Sleep(300)
    SendText("git push origin main --force`n")
}
