'''
AN-003 - Application note implements the UNH-IOL plugfest test for hotswap of U.2 drives
This application note was written to be used in conjunction with QuarchPy python package and Quarch modules.

########### VERSION HISTORY ###########

05/04/2018 - Andy Norrie	- First version
14/10/2018 - Pedro Cruz	- Added support to other connection types and array controllers
27/11/2019 - Stuart Boon - Compatible with linux, moved to lspci in Qpy, Updated for newest Qpy features like drive and module selection.
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
from quarchpy.user_interface import *
from quarchpy.disk_test.hostInformation import HostInformation
from quarchpy.debug.versionCompare import *
myHostInfo = HostInformation()

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
def main():
    linkSpeed = "ERROR"
    linkWidth = "ERROR"    

    if not requiredQuarchpyVersion("2.0.11"):
        exit()
    # Setting parameters that control the test
    onTime = 10                     # Drive on time
    offTime = 10                    # Drive off time
    mappingMode = False             # lspci mapping mode
    plugSpeeds = [25,100,10,500]    # Hot plug speeds
    cycleIterations = 10            # Number of cycles at each speed

    # Check admin permissions (exits on failure)
    myHostInfo.checkAdmin()

    # Print header intro text
    logWrite ("Quarch Technology Ltd")
    logWrite ("HotPlug Test Suite V3.0")
    logWrite ("(c) Quarch Technology Ltd 2015-2019")
    logWrite ("")

    # Get the connection string
    moduleStr = userSelectDevice(nice=True)

            
    # Create a device using the module connection string
    myDevice = quarchDevice(moduleStr)

    # Sets the module to default state
    setDefaultState (myDevice)

    print(myDevice.sendCommand("run pow up"))
    # Check the module is connected and working
    QuarchSimpleIdentify (myDevice)

    listOfDrives = myHostInfo.getDriveList(mappingMode)
    selectedDrive= None
    while selectedDrive is None or selectedDrive in "Rescan":
        selectedDrive = listSelection(selectionList=listOfDrives, nice=True, additionalOptions=["Rescan", "Quit"], tableHeaders=["Drive"], align="c")
    if selectedDrive in "Quit":
        printText("User quit program")
        exit(1)

    matchObj = re.match('[0-9a-fA-F]+:[0-9a-fA-F]+.[0-9a-fA-F]', selectedDrive)
    if matchObj is not None:
        myDrive = matchObj.group(0)
        driveType = "pcie"
        pcieHotplug(cycleIterations, mappingMode, myDevice, offTime, onTime, myDrive, plugSpeeds, driveType)
    else:
        myDrive = selectedDrive
        driveType = "sas"
        basicHotplug(cycleIterations, mappingMode, myDevice, offTime, onTime, myDrive, plugSpeeds, driveType)

    logWrite ("")
    logWrite ("ALL DONE!")
    logWrite ("\nTest - " + "100% Tests run" + " - Passed")
    logWrite ("")
            
    # Close the module before exiting the script
    myDevice.closeConnection()

def basicHotplug(cycleIterations, mappingMode, myDevice, offTime, onTime, myDrive, plugSpeeds, driveType):
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
                cmdResult = myHostInfo.isDevicePresent(myDrive, mappingMode, driveType)
                currentTime = time.time()
                if cmdResult is False:
                    logWrite("Device removed correctly in " +str(currentTime - startTime)+" sec")
                    break
                if currentTime - startTime > offTime:
                    logWrite("***FAIL: " + testName + " - Drive did not remove after "+ str(offTime)+ " sec ***")
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
                cmdResult = myHostInfo.isDevicePresent(myDrive, mappingMode, driveType)
                currentTime = time.time()
                if cmdResult is True:
                    logWrite("<Device enumerated correctly in " + str(currentTime - startTime) + " sec>")
                    break
                if currentTime - startTime > onTime:
                    logWrite("***FAIL: " + testName + " - Drive did not remove after " + str(onTime) + " sec ***")
                    break

            logWrite("Test - " + testName + " - Passed")


def pcieHotplug(cycleIterations, mappingMode, myDevice, offTime, onTime, myDrive, plugSpeeds, driveType):
    # Get the current link status
    linkStartSpeed, linkStartWidth = myHostInfo.getPcieLinkStatus(myDrive, mappingMode)
    logWrite("PCIe device link speed: " + linkStartSpeed)
    logWrite("PCIe device link width: " + linkStartWidth)
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
                cmdResult = myHostInfo.isDevicePresent(myDrive, mappingMode, driveType)
                currentTime = time.time()
                if cmdResult is False:
                    logWrite("Device removed correctly in " + str(currentTime - startTime) + " sec")
                    break
                if currentTime - startTime > offTime:
                    logWrite("***FAIL: " + testName + " - Drive did not remove after " + str(offTime) + " sec ***")
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
                cmdResult = myHostInfo.isDevicePresent(myDrive, mappingMode, driveType)
                currentTime = time.time()
                if cmdResult is True:
                    logWrite("<Device enumerated correctly in " + str(currentTime - startTime) + " sec>")
                    break
                if currentTime - startTime > onTime:
                    logWrite("***FAIL: " + testName + " - Drive did not remove after " + str(onTime) + " sec ***")
                    break

            # Verify link width and speed
            linkEndSpeed, linkEndWidth = myHostInfo.getPcieLinkStatus(myDrive, mappingMode)
            if linkStartSpeed != linkEndSpeed:
                logWrite(
                    "***FAIL: " + testName + " - Speed Mismatch, " + linkStartSpeed + " -> " + linkEndSpeed + "***")
                exitScript(myDevice)
            if linkStartWidth != linkEndWidth:
                logWrite(
                    "***FAIL: " + testName + " - Width Mismatch, " + linkStartWidth + " -> " + linkEndWidth + "***")
                exitScript(myDevice)

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




if __name__== "__main__":
 main()
