<# 
 .Synopsis
  Set of functions giving access to pci_utils.

 .Description
  A set of functions for listing pci devices and determining link status.

 .Example
   # Return a list of PCI devices on the system.
   List-Devices

#>

import-module $PSScriptRoot\Quarch_Serial.psm1

function List_PCI_Devices([bool]$MappingMode)
{
	if ($MappingMode)
	{
		$DevList = cmd /c "$PSScriptRoot\pciutils\lspci.exe" "-M" 2`>`&1
	}
	else
	{
		$DevList = cmd /c "$PSScriptRoot\pciutils\lspci.exe" "" 2`>`&1
	}
	$script:PCIeDeviceList = @()
	foreach ($Line in $DevList)
	{
		# If line is not a 'real' device then skip it
		#if ($Line.StartsWith("#") -or $Line.StartsWith(" "))
		if ($Line -match '[0-9a-fA-F]+:[0-9a-fA-F]+.[0-9a-fA-F]')
		{
			if ($Line -notlike "*##*")
			{
				$script:PCIeDeviceList += @($Line)				
			}
			else
			{				
			}
		}
		# Else it is a device and can be stored in the final list
		else
		{
		}
	}
}
export-modulemember -function List_PCI_Devices

function Device_Present([string] $Device, [bool]$MappingMode)
{
    List_PCI_Devices $MappingMode > $null
    #make sure device id is not present in list
    ($PCIeDeviceList -split ' ' -contains $Device)
}
export-modulemember -function Device_Present

Function Get_Link_Status([string] $Device, [ref]$Speed, [ref]$Width, [bool]$MappingMode)
{
    if ($MappingMode)
	{
		$output = cmd /c "$PSScriptRoot\pciutils\lspci.exe" "-M" "-vv" "-s $Device" 2`>`&1
	}
    else
    {
        $output = cmd /c "$PSScriptRoot\pciutils\lspci.exe" "-vv" "-s $Device" 2`>`&1
    }
    
    #get link status line
    $link_status = $output | select-string -pattern "lnksta:"
    #get current speed "Speed [x.xGT/s],"
    $link_status -match 'Speed (.*?),' > $null
    $link_speed = $matches[1]
    #get current width "Width [x.xGT/s],"
    $link_status -match 'Width (.*?),' > $null
    $link_width = $matches[1]

	$Speed.value = $link_speed
	$Width.value = $link_width
}
export-modulemember -function Get_Link_Status

function Pick_PCI_Target([string] $Device, [bool]$MappingMode)
{
    #get a list of pci devices on the system
    List_PCI_Devices $MappingMode

    while ($Device -contains "none" -and $PCIeDeviceList -split ' ' -notcontains $Device)
    {
        Write-Host "PCI Device $Device was not specified"
        Write-Host "Select from the detected Devices:"
        Write-Host
    
        for ($item=1;$item -le $PCIeDeviceList.length;$item++) {
            Write-host $item")" $PCIeDeviceList[$item-1]
        }

        Write-Host

        #ask for a pci device
        $selection = Read-Host 'Please select a target device (or q to exit)'

        #if user entered "q" then exit script
        if ($selection -eq "q")
        {
            write-host "Exiting...."
            return 0
        }
        elseif (($selection -match '[0-9]+') -and ($selection -gt 0) -and ($selection -le $PCIeDeviceList.Length))
        {
            $Device = $PCIeDeviceList[$selection-1]
            #get PCI bus id from selected device
            $Device -match '[0-9a-fA-F]+:[0-9a-fA-F]+.[0-9a-fA-F]' > $null
            $Device = $matches[0]
        }

    }
	
	return $Device
}
export-modulemember -function Pick_PCI_Target