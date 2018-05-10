'''
AN-003 - Application note implements the UNH-IOL plugfest test for hotswap of U.2 drives
This application note was written to be used in conjunction with QuarchPy python package and Quarch modules.

########### VERSION HISTORY ###########

05/04/2018 - Andy Norrie	- First version

########### INSTRUCTIONS ###########

1- Connect a Quarch module to your PC via QTL1260 Interface kit and USB cable with the button pushed in
2- If needed, install the FTDI VCOM driver to support the virtual COM port


####################################
'''

#Imports QuarchPy library, providing the functions needed to use Quarch modules
from __future__ import print_function
from quarchpy import quarchDevice
from lspci import pickPcieTarget, checkAdmin, getLinkStatus, devicePresent

# Import other libraries used in the examples
import os
import time
import platform
import datetime
import exceptions

'''
Prints to screen and to the logfile at the same time
'''
logFilePath = os.path.join (os.getcwd(), "LogFile" + str(datetime.datetime.now ()).replace (':','_') + ".txt")
def logWrite (logString):
    print (logString)
    with open(logFilePath, 'a') as logFile:
        logFile.write (logString + "\n")

'''
Exit the script and close connections
'''
def exitScript (myDevice):
    setDefaultState (myDevice)
    myDevice.closeConnection()
    quit()

def setDefaultState (myDevice):
    myDevice.sendCommand ("conf:def:state")
    time.sleep(3)
    

'''
Sets up a simple hot-plug timing.  6 times sources are available on most modules.
Final delay to in 1270mS, so the total delay time must not exceed this
'''
def setupSimpleHotplug (myDevice, delayTime, stepCount):

    # Check parameters
    if delayTime < 1:
        raise ValueError('delaytime must be in range 1 to (1270/sourceCount)mS')
    if stepCount > 1:
        if delayTime > (1270/(stepCount-1)):
            raise ValueError('delaytime must be in range 1 to (1270/sourceCount)mS')
    if (stepCount < 2 or stepCount > 6):
        raise ValueError('stepCount must be between 1 and 6')

    # Run through all 6 timed sources on the module
    for steps in (1, 6):
        # Calculate the next source delay. Additional sources are set to the last value used
        if steps <= stepCount:
            nextDelay = (steps - 1 ) * delayTime
        myDevice.sendCommand ("source:" + str(steps) + ":delay " + str(nextDelay))    
    

''' 
Opens the connection, call the selected example function(s) and closes the connection.
The constructor opens the connection by default.  You must always close a connection before you exit
'''
def main():
    linkSpeed = "ERROR"
    linkWidth = "ERROR"    
    
    # Setting parameters that control the test
    onTime = 10                     # Drive on time
    offTime = 10                    # Drive off time
    mappingMode = False             # lspci mapping mode
    plugSpeeds = [25,100,10,500]    # Hot plug speeds
    cycleIterations = 10            # Number of cycles at each speed

    # Check admin permissions (exits on failure)
    checkAdmin ()

    # Print header intro text
    logWrite ("Quarch Technology Ltd")
    logWrite ("HotPlug Test Suite V2.0")
    logWrite ("(c) Quarch Technology Ltd 2015-2018")
    logWrite ("")

    # Get the connection string
    moduleStr = raw_input ("Enter the com port number to use (COMx): ")
    moduleStr = "SERIAL:" + moduleStr
            
    # Create a device using the module connection string
    myDevice = quarchDevice(moduleStr)
    # Check the module is connected and working
    QuarchSimpleIdentify (myDevice)

    # Select the PCIe device to use
    pcieDevice = pickPcieTarget ('none', mappingMode)
    if (pcieDevice == 0):
        logWrite ("***FAIL: Valid PCIe device was not selected***")
        quit()

    # Get the current link status
    linkStartSpeed, linkStartWidth = getLinkStatus (pcieDevice)
    logWrite ("PCIe device link speed: " + linkStartSpeed)
    logWrite ("PCIe device link width: " + linkStartWidth)

    # Loop through the list of plug speeds
    for testDelay in plugSpeeds:
        testName = str(testDelay) + "mS HotPlug Test"
        iteration = 0

        # Loop through plug iterations
        for currentIteration in range (0, cycleIterations):
            logWrite ("")
            logWrite ("")
            logWrite ("=====================")
            logWrite ("Test -" + testName + " - " + str(currentIteration+1) + "/" + str(cycleIterations))
            logWrite ("")

            # Setup hotplug timing (QTL1743 uses 3 sources by default)
            setupSimpleHotplug (myDevice, testDelay, 3)
            logWrite ("")
            logWrite ("")

            # Pull the drive
            logWrite ("Beginning the test sequence")
            logWrite ("  - Pulling the device")
            cmdResult = myDevice.sendCommand ("RUN:POWer DOWN")
            if cmdResult.find ("FAIL") != -1:
                logWrite ("***FAIL: Power down command failed to execute correctly***")
                logWrite ("***" + cmdResult)
                exitScript (myDevice)

            # Wait for device to remove
            logWrite ("  - Waiting for device removal (" + str(offTime) + " Seconds)")
            time.sleep(offTime)

            # Check that the device removed correctly
            cmdResult = devicePresent (pcieDevice ,mappingMode)
            if cmdResult == True:
                logWrite ("***FAIL: " + testName + " - Device did not remove***")
                exitScript (myDevice)
            else:
                logWrite ("  - Device removed correctly")

            # Power up the drive
            logWrite ("  - Plugging the device")
            cmdResult = myDevice.sendCommand ("RUN:POWer UP")
            if cmdResult.find ("FAIL") != -1:
                logWrite ("***FAIL: Power down command failed to execute correctly***")
                exitScript (myDevice)

            # Wait for device to enumerate
            logWrite ("  - Waiting for device enumeration (" + str(onTime) + " Seconds)")
            time.sleep(onTime)

            # Verify the device is back
            cmdResult = devicePresent (pcieDevice, mappingMode)
            if cmdResult == False:
                logWrite ("***FAIL: " + testName + " - Device not present***")
                exitScript (myDevice)
            else:
                logWrite ("  - Device enumerated correctly")

            # Verify link width and speed
            linkEndSpeed, linkEndWidth = getLinkStatus (pcieDevice)
            if linkStartSpeed != linkEndSpeed:
                logWrite ("***FAIL: " + testName + " - Speed Mismatch, " + linkStartSpeed + " -> " + linkEndSpeed + "***")
                exitScript (myDevice)
            if linkStartWidth != linkEndWidth:
                logWrite ("***FAIL: " + testName + " - Width Mismatch, " + linkStartWidth + " -> " + linkEndWidth + "***")
                exitScript (myDevice)
            
            logWrite ("Test - " + testName + " - Passed")

    logWrite ("")
    logWrite ("ALL DONE!")
    logWrite ("Test - " + "100% Tests run" + " - Passed")
    logWrite ("")
            
    # Close the module before exiting the script
    myDevice.closeConnection()

'''
This function demonstrates a very simple module identify, that will work with any Quarch device
'''
def QuarchSimpleIdentify(device1):
    # Print the module name
    print("Running the simple identify example.\n")
    print("Module Name:"),
    print(device1.sendCommand("hello?"))
    # Print the module identify and version information
    print("\nModule Status:")
    print(device1.sendCommand("*tst?"))
    print("")

''' 
This function demonstrates simple control over modules that are attached via an Array Controller.  This will require you to connect to
a QTL1461 or QTL1079 Array Controller, with a module attached on port 1
'''
def QuarchArrayExample(device1):
    # Print the controller name
    print("Running the array identify test.\n")
    print("Controller Name:"),
    print(device1.sendCommand("hello?"))
    
    # Try to talk to the module on port 1
    print("Module Name on port 1:"),
    deviceDesc = (device1.sendCommand("hello? <1>"))
    print (deviceDesc)
    
    # If we get 'FAIL' then there is no module attached
    if "FAIL" in deviceDesc:
        print("Error: No module on port <1>")	
    # Otherwise we can take to the module and query its power state
    else:
        print("Check power state of module on array port 1:"),
        print(device1.sendCommand("RUN:POWER? <1>"))

''' 
This function is a simple demonstration of working with a standard hot-plug module (Drive Modules, Card Modules and Cable Modules will all work with this function)
It will first query the name of the module attached, then move it into a known (plugged) state.  Finally it performs a looped power cycle
'''
def QuarchHotPlugExample(device1):
    # Prints out the ID of the attached module
    print("Running the hot-plug module example.\n")

    print("Module Name:"),
    print(device1.sendCommand("hello?"))

    # Check the power up state of the module
    print("\nChecking the State of the Device and Power up if necessary.")
    isPulled = device1.sendCommand("run:power?")
    print("State of the Device:"),
    print(isPulled + "\n")

    # Ensure the module is in Power up state
    if isPulled == "PULLED":
        print("Device is PULLED. Plugging the device...")
        device1.sendCommand("run:power up")
        for i in xrange(30):
            time.sleep(1)
            print ('Waiting {0}/30 seconds for power up to complete.\r'.format(i)),
        print ("\n")

    #Creating a loop for Hot-Plug cycle
    print("Starting HotPlug cycle:")
    for i in range (1,6):
        print("\n   HotPlug Cycle: %d"%i)
        print("   Pulling the device" + ","),
        # Power down (pull) the device
        device1.sendCommand("run:power down"),
        time.sleep(3)
        
        '''
        Here you could insert your own code to query the host and make sure everything worked and the drive disconnected cleanly
        '''
        
        # Power up (plug) the device
        print("plugging the device.\n"),
        device1.sendCommand("run:power up"),
        time.sleep(3)
        
        '''
        Here you could insert your own code to query the host and make sure everything worked and the drive was enumerated
        '''

    print("\nCycle finished!")

'''
This function is a simple demonstration of working with a switch module.  It is designed to work with SAS switches.
It first displays the name of the attached module, then cycles between 2 different connections, first with the currently selected connection time,
then with a time of 2x the initial value.  The connection time is the delay between the first connection being removed, and the now one being created.
'''
def QuarchSwitchExample(device1):
    print("Running the physical layer switch example.\n")

    # Prints out the ID of the attached module
    print("Controller name:"),
    print(device1.sendCommand("hello?") + "\n")
    
    time.sleep(0.1) # Makes sure the last command had time to be executed.
    # Checks the current delay
    switchDelay = device1.sendCommand("CONFig:MUX Delay?")
    switchDelay = float(switchDelay)
    print("Current current delay is: " + str(switchDelay) + " seconds." +"\n")
    
    # Adds a delay if none. 
    if switchDelay == 0:
        switchDelay = 1
        print ("Set New Delay: ")
        print (device1.sendCommand("CONFig:MUX:DELAY " + str(switchDelay)))

    # Create a new delay, as double the current one, this will be used for the second part of the test.
    newDelay = switchDelay * 2 
    
    # Set a device1 between Port 1 and 8.
    print("   Setting a device1 between Port 1 and Port 8:"),
    print(device1.sendCommand("MUX:CONnect 1 8"))
    # Sleep until the connection is in place
    time.sleep(switchDelay)

    #TODO: Here you would check if your connected equipment is working correctly.

    #Set a device1 between Port 1 and 4.
    print("   Setting a device1 between Port 1 and Port 4:"),
    print(device1.sendCommand("MUX:CONnect 1 4"))
    time.sleep(switchDelay)

    '''
    Here you would check if your connected equipment is working correctly.
    '''

    #Set a delay of double the existing delay.
    print("")
    print("Running the test with new delay:"),
    command = "CONFig:MUX:DELay " + str(int(newDelay))
    print(device1.sendCommand( command))
    print("")
    
    time.sleep(0.1) # Makes sure the last command had time to be executed.
    #Set a device1 between Port 1 and 8
    print("   Setting a device1 between Port 1 and Port 8:"),
    print(device1.sendCommand("MUX:CONnect 1 8"))
    time.sleep(newDelay)

    '''
    Here you would check if your connected equipment is working correctly
    '''

    #Set a device1 between Port 1 and 4
    print("   Setting a device1 between Port 1 and Port 4:"),
    print(device1.sendCommand("MUX:CONnect 1 4"))
    time.sleep(newDelay)

    '''
    Here you would check if your connected equipment is working correctly
    '''

    #Set the switch back to initial delay we had at the start
    print("")
    print("Changing the delay back to the previous settings:"),
    command = "CONFig:MUX:DELay " + str(int(switchDelay))
    print(device1.sendCommand( command))

    print("\nTest concluded!")

'''
This function works with our Programmable Power Modules, and demonstrates how to identify the module, set the power output then perform a series
of simple power margining measurements
'''
def QuarchPowerMarginingExample(device1):
    print("Running the power module example.\n")

    # Prints out the ID of the attached module.
    print("Module attached:"),
    print(device1.sendCommand("hello?") + "\n")

    #Set the 5V channel and 12V channel to 5000mV and 12000mV to ensure that they are at the right level.
    print ("Setting PPM into default voltage state.\n")
    device1.sendCommand("Sig:5v:Volt 5000")
    device1.sendCommand("Sig:12v:Volt 12000")
    device1.sendCommand("CONF:OUT:MODE 5v")

    #Check the state of the module and power up if necessary.
    print("Checking the State of the Device and power up if necessary.")
    currentState = device1.sendCommand("run:power?")
    print("State of the Device: " + (currentState))
    
    # If the outputs are off
    if currentState =="OFF":
        # Power up
        device1.sendCommand("run:power up"),
        print("Powering up the device:"),
        # Let the attached device power up fully
        time.sleep(3)
        print ("OK!")

    # Print headers
    print("\nRunning power margining test...\n")
    print("Margining Results for 12V rail:\n")

    # Loop through 6 different voltage levels, reducing by 200mV on each loop
    testVoltage = 12000
    i = 0
    for i in range (6):

        # Set the new voltage level
        device1.sendCommand("Sig:12V:Volt " + str(testVoltage))

        # Wait for the voltage rails to settle at the new level
        time.sleep(1)

        # Request and print(the voltage and current measurements
        print(device1.sendCommand("Measure:Voltage 12V?")+  " = "  + device1.sendCommand("Measure:Current 12V?"))

        # Decreasing the testVoltage by 200mv
        testVoltage -= 200

    # Set the 12v level aback to default
    print("\nSetting the 12V back to default state.\n")
    device1.sendCommand("Sig:12V:Volt 12000")

    # Print headers
    print("Margining Results for 5V rail:\n")

    # Loop through 6 different voltage levels, reducing by 200mV on each loop
    testVoltage = 5000
    i = 0
    for i in range (6):

        # Set the new voltage level
        device1.sendCommand("Sig:5V:Volt " + str(testVoltage))
        # Wait for the voltage rails to settle at the new level
        time.sleep(1)
        # Request and print(the voltage and current measurements
        print(   device1.sendCommand("Measure:Voltage 5V?")+  " = "  + device1.sendCommand("Measure:Current 5V?"))
        # Decreasing the testVoltage by 200mv
        testVoltage -= 200

    print("\nSetting the 5V back to default state.\n")
    device1.sendCommand("Sig:5V:Volt 5000")

    print("Test finished!")

if __name__== "__main__":
 main()
