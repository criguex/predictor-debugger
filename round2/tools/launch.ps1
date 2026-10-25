param([string]$Script, [string]$Log, [string]$Arg = "")
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = "cmd /c C:\ADN\pd-exp-r2\round2\tools\$Script $Arg > C:\ADN\pd-exp-r2\$Log 2>&1"; CurrentDirectory = "C:\ADN\pd-exp-r2"}
"pid=$($r.ProcessId) return=$($r.ReturnValue)"
