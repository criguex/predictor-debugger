param([string]$Script, [string]$Log)
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = "cmd /c C:\ADN\pd-exp\tools\$Script > C:\ADN\pd-exp\$Log 2>&1"; CurrentDirectory = "C:\ADN\pd-exp"}
"pid=$($r.ProcessId) return=$($r.ReturnValue)"
