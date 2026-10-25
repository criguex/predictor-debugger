param([string]$Script, [string]$Log, [string]$Machine = "", [string]$Jobs = "")
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = "cmd /c C:\ADN\pd-exp-r4\round4\tools\$Script $Machine $Jobs > C:\ADN\pd-exp-r4\$Log 2>&1"; CurrentDirectory = "C:\ADN\pd-exp-r4"}
"pid=$($r.ProcessId) return=$($r.ReturnValue)"
