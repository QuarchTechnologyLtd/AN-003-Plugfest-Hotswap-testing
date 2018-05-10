import-module $PSScriptRoot\Quarch_Serial.psm1

<# 
 .Synopsis
  Sets up a Quarch Module with a basic hotplug of the specified length.

 .Description
  Sets up a Quarch control module with the default signal to source mappings, the delays are determined
  by the parameter.

 .Parameter Delay
  The time in mS to delay between mating of successive groups of pins.

 .Example
   # Set up module for a hotplug with 25mS delay between first and second mate signals, and 25mS delay between 2nd and 3rd mate signals.
   Setup-Basic-Hotplug(25)

#>
function Setup_Basic_Hotplug([System.IO.Ports.SerialPort]$ComPort, [int] $delay)
{
	$Result = 0

    # Set The module to a known state
    $Result += Execute_Command $ComPort "CONFig:DEFault STATE"

    #Set up Source Delays
    $Result += Execute_Command $ComPort "SOURce:1:DELay 0"
    $Result += Execute_Command $ComPort "SOURce:2:DELay $delay"
    $Result += Execute_Command $ComPort $("SOURce:3:DELay " + $delay*2)
    $Result += Execute_Command $ComPort "SOURce:4:DELay 0"
    $Result += Execute_Command $ComPort "SOURce:5:DELay 0"
    $Result += Execute_Command $ComPort "SOURce:6:DELay 0"
	
	if ($Result -ne 7)
    {
		return 0
    }
	else
    {
		return 1
    }
}
export-modulemember -function Setup_Basic_Hotplug