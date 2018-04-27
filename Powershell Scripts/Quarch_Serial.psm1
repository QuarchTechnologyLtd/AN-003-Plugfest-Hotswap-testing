
# Gets the response from a module command
Function Get_Response([System.IO.Ports.SerialPort]$ComPort, [String]$command)
{
    $ComPort.WriteLine($command)
    $ComPort.ReadTo(">")
}
export-modulemember -function Get_Response

# Executes a basic command that is expected to return 'OK'.  Fails on other responses
Function Execute_Command([System.IO.Ports.SerialPort]$ComPort, [String]$command)
{
    Write-Host $command
    $ComPort.WriteLine($command)
    if ($ComPort.ReadTo(">") -notmatch 'OK')
    {
        Write-Host "Command Failed: "$command
        return 0
    }
	else
	{
		return 1
	}
}
export-modulemember -function Execute_Command

# Validates the given COM port, going through a cycle to select the port if the selected port does not exist
Function Pick_Comm_Port([string] $ThisPort)
{
    $Port = $ThisPort

    #get a list of serial ports on the system
    $SerialPortList = [System.IO.Ports.SerialPort]::getportnames()

    while ($SerialPortList -notcontains $Port)
    {
        Write-Host "Comm Port $Port not found"
        Write-Host "Available Comm Ports:"
        Write-Host
    
        for ($item=1;$item -le $SerialPortList.length;$item++) {
            Write-host $item")" $SerialPortList[$item-1]
        }

        Write-Host

        #ask for a serial port
        $selection = Read-Host 'Please select a serial port (or q to exit)'

        #if user entered "q" then exit script
        if ($selection -eq "q")
        {
            write-host "Exiting...."
            exit(1)
        }
        #elseif the entry was numeric and within range
        elseif (($selection -match '[0-9]+') -and ($selection -gt 0) -and ($selection -le $SerialPortList.Length))
        {
            $Port = $SerialPortList[$selection-1]
        }
    }
	
	return $Port
}
export-modulemember -function Pick_Comm_Port

# Opens the selected COM port with Quarch standard settings
function Open_Comm_Port($Port)
{
    $COMMport = new-Object System.IO.Ports.SerialPort $Port,19200,None,8,one
    $COMMport.ReadTimeout = 1000
    $COMMport.NewLine = "`r"
    $result = $COMMport.open()
    $result = Execute_Command $COMMport "conf:term script"
	
	return $COMMport
}
export-modulemember -function Open_Comm_Port