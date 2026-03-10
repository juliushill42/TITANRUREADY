$h = (Get-Process | Where-Object { $_.MainWindowTitle -like 'TitanU OS*' }).MainWindowHandle
if ($h) {
    Add-Type -Name 'User32' -Namespace 'Win32' -MemberDefinition '[DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow); [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);'
    [Win32.User32]::ShowWindowAsync($h, 9) | Out-Null
    [Win32.User32]::SetForegroundWindow($h) | Out-Null
}