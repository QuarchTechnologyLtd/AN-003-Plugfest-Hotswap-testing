Param([String]$Port,[String]$Device="none",[int]$Iterations=10) 

import-module $PSScriptRoot\Basic_Hotplug.psm1
import-module $PSScriptRoot\Pci_Utils.psm1
import-module $PSScriptRoot\Quarch_Serial.psm1

# Check if we are in admin mode, and if not, restart with admin permissions (required for lspci calls)
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator"))
{   
	$arguments = "& '" + $myinvocation.mycommand.definition + "'"
	Start-Process powershell -Verb runAs -ArgumentList $arguments
	Break
}
# lspci will not run with spaces in the path, watch for this here
If ($PSScriptRoot -match " ")
{
	Write-host "WARNING: Path contains a space, script will not run correctly!"
	break;
}


# Initialize variables that will be used for reference calls
$link_speed = "NONE"
$link_width = "NONE"
#$LogRoot = "c:\Hotplug_PowerShell"
$LogRoot = $PSScriptRoot
# Set to '1' to enable bus mapping mode when running lspci.exe (not required for most devices)
$MappingMode = 0

$Date = Get-Date -format u
$Date = $Date -replace ':','-'
$Logfile = $LogRoot + "\LogFile " + $Date
$Logfile = $Logfile + ".txt"

# Define the on and off time for the drive during each test cycle
$on_time = 10
$off_time = 10

# Exit the script, closing the COM port first
Function exitScript($COMMport, [int] $code)
{
    if ($COMMport.IsOpen)
    {
        # return module to user mode
        $COMMport.WriteLine("conf:term user")
        # close serial port
        $COMMport.Close()
    }
    exit($code)
}

# Logs the output to a file.  Comment out the 'Add-content' string if you want to disable logging!
Function LogWrite
{
   Param ([string]$logstring)

   Add-content $Logfile -value $logstring
   Write-Host $logstring
}

LogWrite 
LogWrite "Quarch Technology Ltd"
LogWrite "HotPlug Test Suite V1.1"
LogWrite "(c) Quarch Technology Ltd 2015-2018"
LogWrite 
Write-Host "Log Path: $Logfile"

# Validate COM port or request user to specify one
$Port = Pick_Comm_Port $Port

# Validate PCIe device or request user to specify one
$Device = Pick_PCI_Target $Device $MappingMode
if ($Device -eq 0)
{
	Write-Host "***FAIL: Valid PCIe device was not selected***"
    exitScript(1)
}

LogWrite "Connecting to Quarch module"
# Open comms with the Quarch module
$ComPort = Open_Comm_Port $Port
LogWrite
LogWrite 

# Get initial link details of PCIe device
Get_Link_Status $Device ([ref]$link_speed) ([ref] $link_width) $MappingMode
$starting_speed = $link_speed
$starting_width = $link_width

# Get serial number of connected module
$serial = Get_Response $ComPort "*serial?"
$serial = $serial -replace " |`t|`n|`r",""

# Verify serial number is a Quarch module
if ($serial.length -gt 4)
{
    # This is an Quarch Module
    LogWrite "Found Module "$serial" on "$Port
	write-host "Found Module "$serial" on "$Port
}
else
{
    LogWrite "Unrecognized Module "$serial" on "$Port
	write-host "Unrecognized Module "$serial" on "$Port
    exitScript $ComPort 1
}

LogWrite "PCIe device link speed: $starting_speed"
LogWrite "PCIe device link width: $starting_width"
LogWrite 
LogWrite 

#=================================================================================
# Start Test Section

# Setup the list of hot-plug timings to use
$Test_Delay_List = @(25,100,10,500)

# Loop through each of the timing options in order
for ($TestStage=0;$TestStage -lt $Test_Delay_List.length; $TestStage++)
{
	$Test = " " + $Test_Delay_List[$TestStage] + "mS HotPlug Test"
	$Delay = $Test_Delay_List[$TestStage]
	
	# Loop through each of the test iterations for the current timing
	for ($loop=1;$loop -le $Iterations;$loop++)
	{
        LogWrite
        LogWrite
		LogWrite "====================="
		LogWrite "Test -$Test - Iteration $loop/$Iterations"
		LogWrite 

		# Set up the timing sequence
		LogWrite "Setting up hot-plug timing sequence"
		$Result = Setup_Basic_Hotplug $ComPort $delay
		if ($Result -eq 0)
		{
			LogWrite "***FAIL: Timing setup commands failed to execute correctly***"
			exitScript $ComPort 1
		}
		LogWrite 
		LogWrite 

		# Pull the drive
		LogWrite "Beginning the test sequence"
		LogWrite "  - Pulling the device"
		$Result = Execute_Command $ComPort "RUN:POWer DOWN"
		if ($Result -eq 0)
		{
			LogWrite "***FAIL: Power down command failed to execute correctly***"
			exitScript $ComPort 1
		}
		
		#wait for device to remove
		LogWrite "  - Waiting for device removal ($off_time Seconds)"
		Start-Sleep -s $off_time

		#verify device has gone away
		$result = Device_Present $Device $MappingMode

		if ($result -eq $true)
		{
			LogWrite "***FAIL: $Test - Device did not remove***"
			exitScript $ComPort 0
		}
		else
		{
			LogWrite "  - Device removed correctly"
		}

		#power up
		LogWrite "  - Plugging the device"
		$Result = Execute_Command $ComPort "RUN:POWer UP"
		if ($Result -eq 0)
		{
			LogWrite "***FAIL: Power down command failed to execute correctly***"
			exitScript $ComPort 1
		}

		#wait for device to enumerate
		LogWrite "  - Waiting for device enumeration ($on_time Seconds)"
		Start-Sleep -s $on_time

		#verify device is back
		$result = Device_Present $Device $MappingMode

		if ($result -eq $false)
		{
			LogWrite "***FAIL: $Test - Device not present***"
			exitScript $ComPort 0
		}
		else
		{
			LogWrite "  - Device enumerated correctly"
		}

		#verify link width and speed
		Get_Link_Status $Device ([ref]$link_speed) ([ref]$link_width) $MappingMode
		if ($link_speed -ne $starting_speed)
		{
			LogWrite "***FAIL: $Test - Speed Mismatch, $starting_speed -> $link_speed***"
			exitScript $ComPort 1
		}
		else
		{
			LogWrite "  - Device link speed is still: $link_speed"
		}
		
		if ($link_width -ne $starting_width)
		{
			LogWrite "***FAIL: $Test - Width Mismatch, $starting_width -> $link_width***"
			exitScript $ComPort 1
		}
		else
		{
			LogWrite "  - Device link width is still: $link_width"
		}

		LogWrite "Test - $test - Passed"
	} # Iteration loop
} # Hot-plug timing loop

exitScript(0)
