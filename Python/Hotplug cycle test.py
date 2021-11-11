'''
AN-003 - Application note implements the UNH-IOL plugfest test for hotswap of U.2 drives
This application note was written to be used in conjunction with QuarchPy python package and Quarch modules.

########### VERSION HISTORY ###########

05/04/2018 - Andy Norrie	- First version
14/10/2018 - Pedro Cruz	- Added support to other connection types and array controllers
27/11/2019 - Stuart Boon - Compatible with linux, moved to lspci in Qpy, Updated for newest Qpy features like drive and module selection.
11/11/2021 - Stuart Boon / Matt Holsey - Updating for use with newer drive detection mechanisms

########### INSTRUCTIONS ###########

1- Connect a Quarch module to your PC via QTL1260 Interface kit or array controller.
2- Check test parameters.
3- Run this script using in an elevated command prompt.
4- Select the module and drive in your set up and watch the results.
####################################
'''

# Try to make script back compatible to python 2.x
from __future__ import print_function
try:
    input = raw_input
except NameError:
    pass
#Imports QuarchPy library, providing the functions needed to use Quarch modules
import re
from quarchpy.device import *
from quarchpy.device.device import *
from quarchpy.user_interface import *
from QuarchpyQCS.hostInformation import HostInformation
from quarchpy.debug.versionCompare import *
from quarchpy.user_interface.user_interface import displayTable

myHostInfo = HostInformation()
summary_list = []

# Import other libraries used in the examples
import os
import time
import platform
import datetime
#import exceptions

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
    
def is_user_admin():
    if os.name == 'nt':
        import ctypes
        # WARNING: requires Windows XP SP2 or higher!
        try:
            # If == 1, user is running from elevated cmd prompt
            # printText(ctypes.windll.shell32.IsUserAnAdmin() == 1)
            return ctypes.windll.shell32.IsUserAnAdmin() == 1
        except:
            traceback.print_exc()
            return False
    elif os.name == 'posix':
        # Check for root on Posix
        return os.getuid() == 0
    else:
        raise RuntimeError("Unsupported operating system for this module: %s" % (os.name,))


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
        cmdResult = myDevice.sendCommand ("source:" + str(steps) + ":delay " + str(nextDelay))
        if "OK" not in cmdResult:
                logWrite ("***FAIL: Config command failed to execute correctly***")
                logWrite ("***" + cmdResult)
                exitScript (myDevice)
    time.sleep(0.1)

''' 
Opens the connection, call the selected example function(s) and closes the connection.
The constructor opens the connection by default.  You must always close a connection before you exit
'''
def main():
    linkSpeed = "ERROR"
    linkWidth = "ERROR"    

    # if not requiredQuarchpyVersion("2.0.11"):
    #     exit()
    # Setting parameters that control the test
    onTime = 10                     # Drive on time
    offTime = 10                    # Drive off time
    mappingMode = False             # lspci mapping mode
    plugSpeeds = [25,100,10,500]    # Hot plug speeds
    cycleIterations = 3            # Number of cycles at each speed

    # Check admin permissions (exits on failure)
    if not is_user_admin():
        logWrite("Application note must be run with administrative privileges.")

    # Print header intro text
    logWrite ("Quarch Technology Ltd")
    logWrite ("HotPlug Test Suite V3.0")
    logWrite ("(c) Quarch Technology Ltd 2015-2021")
    logWrite ("")

    # Get the connection string
    moduleStr = userSelectDevice(nice=True)


    # Create a device using the module connection string
    myQuarchModule = getQuarchDevice(moduleStr)

    # Sets the module to default state
    setDefaultState (myQuarchModule)

    print(myQuarchModule.sendCommand("run pow up"))
    # Check the module is connected and working
    QuarchSimpleIdentify (myQuarchModule)

    listOfDrives = myHostInfo.return_wrapped_drives()

    listOfDrives = return_drives_as_list(listOfDrives)

    selectedDrive= None
    while selectedDrive is None or selectedDrive in "Rescan":
        selectedDrive = listSelection(selectionList=listOfDrives, nice=True, additionalOptions=["Rescan", "Quit"], tableHeaders=["Drive"], align="c")
    if selectedDrive in "Quit":
        printText("User quit program")
        exit(1)

    selectedDrive = selectedDrive.split(":-")
    myDrive = myHostInfo.get_wrapped_drive_from_choice(selectedDrive[0])

    if myDrive.drive_type == "pcie":
        pcieHotplug(cycleIterations, mappingMode, myQuarchModule, offTime, onTime, myDrive, plugSpeeds)
    else:
        basicHotplug(cycleIterations, mappingMode, myQuarchModule, offTime, onTime, myDrive, plugSpeeds)


    logWrite ("")

    """
    display_options = []
    for item in run_options:        
        short_name = item[1]        
        description = item[3]
        display_options.append([short_name,description])"""
    logWrite("Test Complete")
    if summary_list:
        displayTable(summary_list, align="l", tableHeaders=["Delay (mS)", "Test iteration", "Failure description"])
    else:
        logWrite("All tests Passed!")

    logWrite ("")
            
    # Close the module before exiting the script
    myQuarchModule.closeConnection()

def basicHotplug(cycleIterations, mappingMode, myDevice, offTime, onTime, myDrive, plugSpeeds):


    # Loop through the list of plug speeds
    for testDelay in plugSpeeds:
        testName = str(testDelay) + "mS HotPlug Test"
        iteration = 0

        # Loop through plug iterations
        for currentIteration in range(0, cycleIterations):
            logWrite("")
            logWrite("")
            logWrite("===============================")
            logWrite("Test -" + testName + " - " + str(currentIteration + 1) + "/" + str(cycleIterations))
            logWrite("===============================")
            logWrite("")

            # Setup hotplug timing (QTL1743 uses 3 sources by default)
            setupSimpleHotplug(myDevice, testDelay, 3)

            # Pull the drive
            logWrite("Beginning the test sequence:\n")
            logWrite("  - Pulling the device...")
            cmdResult = myDevice.sendCommand("RUN:POWer DOWN")
            print("    <" + cmdResult + ">")
            if "OK" not in cmdResult:
                logWrite("***FAIL: Power down command failed to execute correctly***")
                logWrite("***" + cmdResult)
                exitScript(myDevice)
            # Wait for device to remove
            logWrite("  - Waiting for device removal (" + str(offTime) + " Seconds Max)...")
            startTime = time.time()
            currentTime = time.time()
            while True:
                cmdResult = myHostInfo.is_wrapped_device_present(myDrive)
                currentTime = time.time()
                if cmdResult is False:
                    logWrite("Device removed correctly in " +str(currentTime - startTime)+" sec")
                    break
                if currentTime - startTime > offTime:
                    logWrite("***FAIL: " + testName + " - Drive was not removed after "+ str(offTime)+ " sec ***")

                    summary_list.append([str(testDelay), str(currentIteration + 1) + "/" + str(cycleIterations),
                                         "Drive was not removed after "+ str(offTime) + " sec"])
                    break



            # Power up the drive
            logWrite("\n  - Plugging the device")
            cmdResult = myDevice.sendCommand("RUN:POWer UP")
            print("    <" + cmdResult + ">")
            if "OK" not in cmdResult:
                logWrite("***FAIL: Power down command failed to execute correctly***")
                logWrite("***" + cmdResult)
                exitScript(myDevice)
            # Wait for device to enumerate
            logWrite("  - Waiting for device enumeration (" + str(onTime) + " Seconds Max)...")
            startTime = time.time()
            currentTime = time.time()
            while True:
                cmdResult = myHostInfo.is_wrapped_device_present(myDrive)
                currentTime = time.time()
                if cmdResult is True:
                    logWrite("<Device enumerated correctly in " + str(currentTime - startTime) + " sec>")
                    break
                if currentTime - startTime > onTime:
                    logWrite("***FAIL: " + testName + " - Drive did not return after " + str(onTime) + " sec ***")

                    summary_list.append([str(testDelay), str(currentIteration + 1) + "/" + str(cycleIterations),
                                         "Drive did not return after " + str(onTime) + " sec"])
                    break

            logWrite("Test - " + testName + " - Passed")


def pcieHotplug(cycleIterations, mappingMode, myQuarchModule, offTime, onTime, myDrive, plugSpeeds):
    # Get the current link status
    linkStartSpeed = myDrive.link_speed
    linkStartWidth = myDrive.lane_width
    logWrite("PCIe device link speed: " + myDrive.link_speed)
    logWrite("PCIe device link width: " + myDrive.lane_width)
    # Loop through the list of plug speeds
    for testDelay in plugSpeeds:
        testName = str(testDelay) + "mS HotPlug Test"
        iteration = 0

        # Loop through plug iterations
        for currentIteration in range(0, cycleIterations):
            logWrite("")
            logWrite("")
            logWrite("===============================")
            logWrite("Test -" + testName + " - " + str(currentIteration + 1) + "/" + str(cycleIterations))
            logWrite("===============================")
            logWrite("")

            # Setup hotplug timing (QTL1743 uses 3 sources by default)
            setupSimpleHotplug(myQuarchModule, testDelay, 3)

            # Pull the drive
            logWrite("Beginning the test sequence:\n")
            logWrite("  - Pulling the device...")
            cmdResult = myQuarchModule.sendCommand("RUN:POWer DOWN")
            print("    <" + cmdResult + ">")
            if "OK" not in cmdResult:
                logWrite("***FAIL: Power down command failed to execute correctly***")
                logWrite("***" + cmdResult)
                exitScript(myQuarchModule)
            # Wait for device to remove
            logWrite("  - Waiting for device removal (" + str(offTime) + " Seconds Max)...")
            startTime = time.time()
            currentTime = time.time()
            while True:
                pullResult = myHostInfo.is_wrapped_device_present(myDrive)
                currentTime = time.time()
                if not pullResult:
                    logWrite("Device removed correctly in " + str(currentTime - startTime) + " sec")
                    break
                if currentTime - startTime > offTime:
                    logWrite("***FAIL: " + testName + " - Drive was not removed after " + str(offTime) + " sec ***")

                    summary_list.append([str(testDelay), str(currentIteration + 1) + "/" + str(cycleIterations),
                                         "Drive was not removed after " + str(offTime) + " sec"])
                    break

            # Power up the drive
            logWrite("\n  - Plugging the device")
            cmdResult = myQuarchModule.sendCommand("RUN:POWer UP")
            print("    <" + cmdResult + ">")
            if "OK" not in cmdResult:
                logWrite("***FAIL: Power down command failed to execute correctly***")
                logWrite("***" + cmdResult)
                exitScript(myQuarchModule)
            # Wait for device to enumerate
            logWrite("  - Waiting for device enumeration (" + str(onTime) + " Seconds Max)...")
            startTime = time.time()
            currentTime = time.time()
            while True:
                plugResult = myHostInfo.is_wrapped_device_present(myDrive)
                currentTime = time.time()
                if plugResult is True:
                    logWrite("<Device enumerated correctly in " + str(currentTime - startTime) + " sec>")
                    break
                if currentTime - startTime > onTime:
                    logWrite("***FAIL: " + testName + " - Drive did not return after " + str(onTime) + " sec ***")

                    summary_list.append([str(testDelay), str(currentIteration + 1) + "/" + str(cycleIterations),
                                         "Drive did not return after " + str(onTime) + " sec"])
                    break

            # Verify link width and speed
            linkEndSpeed = myHostInfo.return_wrapped_drive_link(myDrive)
            linkEndWidth = myHostInfo.return_wrapped_drive_width(myDrive)
            if linkStartSpeed != linkEndSpeed:
                logWrite(
                    "***FAIL: " + testName + " - Speed Mismatch, " + linkStartSpeed + " -> " + linkEndSpeed + "***")
                exitScript(myQuarchModule)
            if linkStartWidth != linkEndWidth:
                logWrite(
                    "***FAIL: " + testName + " - Width Mismatch, " + linkStartWidth + " -> " + linkEndWidth + "***")
                exitScript(myQuarchModule)

            logWrite("Test - " + testName + " - Passed")


'''
This function demonstrates a very simple module identify, that will work with any Quarch device
'''
def QuarchSimpleIdentify(device1):
    # Print the module name
    time.sleep(0.1)
    print("\nModule Name:")
    print(device1.sendCommand("hello?"))
    time.sleep(0.1)
    # Print the module identify and version information
    print("\nModule Status:")
    print(device1.sendCommand("*tst?"))
    print("")

def return_drives_as_list(drive_list):
    new_return = []

    for drive in drive_list:
        new_return.append("{0} :- {1}".format(drive.identifier_str, drive.description))

    return new_return

if __name__== "__main__":
    main()
