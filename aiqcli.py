#!/usr/bin/env python
#
#

import getopt
import sys
import os
import requests
import urllib3
import json

if sys.version_info < (3, 0):
    from urllib import urlencode
else:
    from urllib.parse import urlencode

def usage():
    print("NetApp Active IQ CLI")
    print("Usage: " + sys.argv[0] + " [-v] [-r] [-a auth_dir] [-d ID] [-c serial] [-l string] [-i ID] [-f percent] [-t]")
    print("")
    print("-v  Verbose output")
    print("-r  Refresh Access Token from Refresh Token")
    print("-a  Auth directory - location to store the access and refresh tokens")
    print("-d  Display systems with predicted disk capacity over threshold by ID")
    print("-c  Cluster lookup by serial number")
    print("-l  Find a customer ID with a search string")
    print("-i  Display inventory by ID as comma separated values")
    print("-f  Filter disk results greater or equal to this percentage")
    print("-t  Format inventory output for screen display")

class parse_args:

    def __init__(self):

        self.homeDir = os.environ.get('HOME')
        self.authDir = '/activeiq'
        self.arglist = []
        self.authPath = self.homeDir + self.authDir
        self.repId = None
        self.inventoryId = None
        self.diskId = None
        self.clusterSn = None
        self.refreshFlag = False
        self.lookupFlag = None
        self.verboseFlag = False
        self.textFormatFlag = False
        self.diskThreshold = 70

    def parse(self):
        options, remainder = getopt.getopt(sys.argv[1:], 'hvrta:d:c:l:i:f:p:', self.arglist)

        for opt, arg in options:
            if opt in ('-a', '--auth'):
                self.authPath = arg
                self.refreshTokenFile = self.authPath + '/RefreshToken.txt'
                self.accessTokenFile = self.authPath + '/AccessToken.txt'
            elif opt in ('-d', '--disk'):
                self.diskId = arg
            elif opt in ('-c', '--cluster'):
                self.clusterSn = arg
            elif opt in ('-i', '--inventory'):
                self.inventoryId = arg
            elif opt in ('-r', '--refresh'):
                self.refreshFlag = True
            elif opt in ('-l', '--lookup'):
                self.lookupFlag = arg
            elif opt in ('-v', '--verbose'):
                self.verboseFlag = True
            elif opt in ('-f', '--disk_threshold'):
                try:
                    self.diskThreshold = int(arg)
                except ValueError:
                    print("Invalid argument for disk full threshold: " + str(arg))
                    sys.exit(1)
            elif opt in ('-t', '--inventory_format'):
                self.textFormatFlag = True
            elif opt in ('-h', '--help'):
                usage()
                sys.exit(0)
            else:
                usage()
                sys.exit(1)

class auth_token:

    def __init__(self, argclass):

        self.argset = argclass
        self.refreshTokenFile = self.argset.authPath + '/RefreshToken.txt'
        self.accessTokenFile = self.argset.authPath + '/AccessToken.txt'
        self.refreshToken = ''
        self.accessToken = ''
        self.verboseFlag = self.argset.verboseFlag

    def makeAuthPath(self):
        if (not os.path.exists(self.refreshTokenFile)):
            print("Refresh token not found")
            try:
                os.mkdir(authPath)
            except OSError as error:
                print("Auth directory already exists")
            print("Please enter a valid refresh token:")
            inputData = sys.stdin.readline()
            refreshTokenFd = open(self.refreshTokenFile, "w")
            refreshTokenFd.write(inputData)
            refreshTokenFd.close()

    def genToken(self):
        refreshTokenFd = open(self.refreshTokenFile, "r")

        self.refreshToken = refreshTokenFd.readline()
        self.refreshToken = self.refreshToken.rstrip("\n")

        refreshTokenFd.close()

        url = 'https://api.activeiq.netapp.com/v1/tokens/accessToken'
        data = '''{ "refresh_token": "''' + self.refreshToken + '''" }'''

        response = requests.post(url, data=data, verify=False)
        json_data = json.loads(response.text)

        for key in json_data:
            if key == "error":
                print("Generate Access Token Error: " + json_data[key])
                sys.exit(1)
            if key == "access_token":
                accessTokenFd = open(self.accessTokenFile, "w")
                if self.verboseFlag:
                    print("Access Token:")
                    print(json_data[key])
                accessTokenFd.write(json_data[key])
                accessTokenFd.close()
            if key == "refresh_token":
                refreshTokenFd = open(self.refreshTokenFile, "w")
                if self.verboseFlag:
                    print("Refresh Token:")
                    print(json_data[key])
                refreshTokenFd.write(json_data[key])
                refreshTokenFd.close()

        self.loadToken()

    def loadToken(self):
        accessTokenFd = open(self.accessTokenFile, "r")

        self.accessToken = accessTokenFd.readline()
        self.accessToken = self.accessToken.rstrip("\n")

        accessTokenFd.close()

class activeiq:

    def __init__(self, auth):

        auth.genToken()
        self.token = auth
        self.authToken = self.token.accessToken
        self.verboseFlag = self.token.verboseFlag
        self.textFormatFlag = self.token.argset.textFormatFlag
        self.diskThreshold = self.token.argset.diskThreshold

    def lookup(self, lookup):

        headers = {'accept': 'application/json', 'authorizationToken': self.authToken}
        parseparams = {'name': lookup}
        url = 'https://api.activeiq.netapp.com/v1/search/aggregate/level/customer?' + urlencode(parseparams)

        response = requests.get(url, headers=headers, verify=False)
        json_data = json.loads(response.text)

        for key in json_data:
            if key == "message":
                print("Lookup Error: " + json_data[key])
                sys.exit(1)
            if key == "results":
                for result in json_data[key]:
                    print("Name:  " + result['name'])
                    print("Count: " + result['count'])
                    print("ID:    " + result['id'])

    def inventoryId(self, lookup):

        headers = {'accept': 'application/json', 'authorizationToken': self.authToken}
        url = 'https://api.activeiq.netapp.com/v1/systemList/aggregate/level/customer/id/' + lookup

        response = requests.get(url, headers=headers, verify=False)
        json_data = json.loads(response.text)

        headers = {'accept': 'application/json', 'authorizationToken': self.authToken}
        url = 'https://api.activeiq.netapp.com/v2/capacity/details/level/customer/id/' + lookup

        response = requests.get(url, headers=headers, verify=False)
        json_disk_data = json.loads(response.text)

        system_used = 'N/A'
        system_percent = 'N/A'
        system_allocated = 'N/A'
        stillSearching = 0
        printLineNum = 1

        for key in json_data:
            if key == "message":
                print("Error: " + json_data[key])
                sys.exit(1)
            if key == "results":
                for result in json_data[key]:
                    system_used = 'N/A'
                    system_percent = 'N/A'
                    system_allocated = 'N/A'
                    for key in json_disk_data:
                        if key == "message":
                            print("Error: " + json_disk_data[key])
                            sys.exit(1)
                        if key == "capacity":
                            stillSearching = 1
                            for detail in json_disk_data[key]:
                                for category in json_disk_data[key][detail]:
                                    if stillSearching == 0:
                                        break
                                    for system in json_disk_data[key][detail][category]:
                                        if (system['serial_number'] == result['serial_number']):
                                            system_used = str(system['used_capacity_GB'])
                                            system_percent = str(system['percent_capacity'])
                                            system_allocated = str(system['allocated_capacity_GB'])
                                            stillSearching = 0
                                            break
                    if self.textFormatFlag:
                        if printLineNum == 1:
                            print('%s %s %s %s %s %s %s %s %s %s' % (
                                'Hostname'.ljust(20), 'Platform'.ljust(20),
                                'System ID'.ljust(40), 'Serial'.ljust(20),
                                'Model'.ljust(15), 'Mode'.ljust(15),
                                'Version'.ljust(10), 'Used'.ljust(12), 'Percent'.ljust(12),
                                'Allocated'.ljust(12)))
                            printLineNum += 1
                        else:
                            print('%s %s %s %s %s %s %s %s %s %s' % (
                                str(result['hostname']).ljust(20), str(result['platform_type']).ljust(20),
                                str(result['system_id']).ljust(40), str(result['serial_number']).ljust(20),
                                str(result['model']).ljust(15), str(result['operating_mode']).ljust(15),
                                str(result['version']).ljust(10), str(system_used).ljust(12),
                                str(system_percent).ljust(12),
                                str(system_allocated).ljust(12)))
                    else:
                        if printLineNum == 1:
                            print("Hostname," + "Platform,"
                                  + "SystemID," + "Serial,"
                                  + "Model," + "Mode,"
                                  + "Version," + "Used,"
                                  + "Percent," + "Allocated")
                            printLineNum += 1
                        else:
                            print(result['hostname'] + ","
                                  + result['platform_type'] + ","
                                  + result['system_id'] + ","
                                  + result['serial_number'] + ","
                                  + result['model'] + ","
                                  + result['operating_mode'] + ","
                                  + result['version'] + ","
                                  + system_used + ","
                                  + system_percent + ","
                                  + system_allocated)

    def diskId(self, lookup):

        headers = {'accept': 'application/json', 'authorizationToken': self.authToken}
        url = 'https://api.activeiq.netapp.com/v2/capacity/details/level/customer/id/' + lookup

        response = requests.get(url, headers=headers, verify=False)
        json_data = json.loads(response.text)

        for key in json_data:
            if key == "message":
                print("Error: " + json_data[key])
                sys.exit(1)
            if key == "capacity":
                for detail in json_data[key]:
                    for category in json_data[key][detail]:
                        if category == "current_90":
                            fullStatus = "Currently_Full"
                        elif category == "1_month_90":
                            fullStatus = "1_Month_to_Full"
                        elif category == "3_months_90":
                            fullStatus = "3_Months_to_Full"
                        elif category == "6_months_90":
                            fullStatus = "6_Months_to_Full"
                        else:
                            fullStatus = "More_than_6_Months"
                        for system in json_data[key][detail][category]:
                            if (system['percent_capacity'] >= self.diskThreshold):
                                print(fullStatus + ": Hostname: " + system['hostname'] + " Capacity: " + str(system['percent_capacity']))

    def cluster(self, lookup):

        headers = {'accept': 'application/json', 'authorizationToken': self.authToken}
        url = 'https://api.activeiq.netapp.com/v1/clusterview/get-cluster-summary/' + lookup

        response = requests.get(url, headers=headers, verify=False)
        json_data = json.loads(response.text)

        for key in json_data:
            if key == "message":
                print("Error: " + json_data[key])
                sys.exit(1)
            if key == "data":
                for attribute in json_data[key][0]:
                    print("%s = %s" % (str(attribute).ljust(25), json_data[key][0][attribute]))

        headers = {'accept': 'application/json', 'authorizationToken': self.authToken}
        url = 'https://api.activeiq.netapp.com/v1/clusterview/resolver/' + lookup

        response = requests.get(url, headers=headers, verify=False)
        json_data = json.loads(response.text)

        for key in json_data:
            if key == "message":
                print("Error: " + json_data[key])
                sys.exit(1)
            if key == "clusters":
                for x in range(len(json_data[key][0]['nodes'])):
                    print("Node [%02d] %s = Serial: %s Model: %s" % (x+1,
                                                                    str(json_data[key][0]['nodes'][x]['name']).ljust(25),
                                                                    str(json_data[key][0]['nodes'][x]['serial']),
                                                                    str(json_data[key][0]['nodes'][x]['model'])))

def main():

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    runargs = parse_args()
    runargs.parse()

    myToken = auth_token(runargs)
    myToken.makeAuthPath()

    if runargs.refreshFlag:
        myToken.genToken()

    query = activeiq(myToken)

    if runargs.lookupFlag:
        query.lookup(runargs.lookupFlag)
    elif runargs.inventoryId:
        query.inventoryId(runargs.inventoryId)
    elif runargs.diskId:
        query.diskId(runargs.diskId)
    elif runargs.clusterSn:
        query.cluster(runargs.clusterSn)

if __name__ == '__main__':

    try:
        main()
    except SystemExit as e:
        if e.code == 0:
            os._exit(0)
        else:
            os._exit(e.code)