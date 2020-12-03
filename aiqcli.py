#!/usr/bin/env python
#
#

import getopt
import sys
import os
import requests
import urllib3
import json
import threading

if sys.version_info < (3, 0):
    from urllib import urlencode
else:
    from urllib.parse import urlencode

def usage():
    print("NetApp Active IQ CLI")
    print("Usage: " + sys.argv[0] + " [-h] [-v] [-r] [-a auth_dir] [-c] [-f] [-l] [-n lookup_name] [-i id] [ -s serial_number ] [-t]")
    print("")
    print("-h  Print this message")
    print("-v  Verbose output")
    print("-r  Refresh Access Token from Refresh Token")
    print("-a  Auth directory - location to store the access and refresh tokens")
    print("-f  Display forecasted storage capacity full timeframe with current capacity")
    print("-c  Cluster lookup by name or serial number")
    print("-l  Find a customer ID with a search string")
    print("-i  Display inventory by name or ID in CSV format by default")
    print("-n  Name to look up")
    print("-s  Serial number to look up")
    print("-i  ID to look up")
    print("-t  Format text output if applicable")

class parse_args:

    def __init__(self):

        self.homeDir = os.environ.get('HOME')
        self.authDir = '/activeiq'
        self.arglist = []
        self.authPath = self.homeDir + self.authDir
        self.id = None
        self.serialNumber = None
        self.lookupName = None
        self.forecastFlag = False
        self.clusterFlag = False
        self.refreshFlag = False
        self.listFlag = False
        self.verboseFlag = False
        self.textFormatFlag = False
        self.diskThreshold = 70
        self.argCount = 0

    def parse(self):
        options, remainder = getopt.getopt(sys.argv[1:], 'hvrtfcla:n:i:s:', self.arglist)

        self.argCount = len(options)
        for opt, arg in options:
            if opt in ('-a', '--auth'):
                self.authPath = arg
                self.refreshTokenFile = self.authPath + '/RefreshToken.txt'
                self.accessTokenFile = self.authPath + '/AccessToken.txt'
            elif opt in ('-f', '--forecast'):
                self.forecastFlag = True
            elif opt in ('-c', '--cluster'):
                self.clusterFlag = True
            elif opt in ('-i', '--id'):
                if self.lookupName:
                    print("Can not combine ID and name: specify either an ID or name")
                    sys.exit(1)
                else:
                    self.id = arg
            elif opt in ('-n', '--name'):
                if self.id:
                    print("Can not combine ID and name: specify either an ID or name")
                    sys.exit(1)
                else:
                    self.lookupName = arg
            elif opt in ('-s', '--serial'):
                self.serialNumber = arg
            elif opt in ('-r', '--refresh'):
                self.refreshFlag = True
            elif opt in ('-l', '--list'):
                self.listFlag = True
            elif opt in ('-v', '--verbose'):
                self.verboseFlag = True
            elif opt in ('-t', '--text_format'):
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
                os.mkdir(self.argset.authPath)
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
        self.customer_data = {}
        self.customer_count = 0
        self.system_list = {}
        self.system_count = 0
        self.capacity_detail = {}
        self.cluster_summary_data = {}
        self.cluster_resolver = {}
        self.cluster_id = {}
        self.node_efficiency = {}
        self.id = []

    def customerLookup(self, lookup):

        headers = {'accept': 'application/json', 'authorizationToken': self.authToken}
        parseparams = {'name': lookup}
        url = 'https://api.activeiq.netapp.com/v1/search/aggregate/level/customer?' + urlencode(parseparams)

        response = requests.get(url, headers=headers, verify=False)
        self.customer_data = json.loads(response.text)
        self.customer_count = len(self.customer_data)

    def systemList(self, lookup):

        headers = {'accept': 'application/json', 'authorizationToken': self.authToken}
        url = 'https://api.activeiq.netapp.com/v1/systemList/aggregate/level/customer/id/' + lookup

        response = requests.get(url, headers=headers, verify=False)
        self.system_list = json.loads(response.text)
        self.system_count = len(self.system_list)

    def capacityDetail(self, lookup):

        headers = {'accept': 'application/json', 'authorizationToken': self.authToken}
        url = 'https://api.activeiq.netapp.com/v2/capacity/details/level/customer/id/' + lookup

        response = requests.get(url, headers=headers, verify=False)
        self.capacity_detail = json.loads(response.text)

    def getClusterSummary(self, lookup):

        headers = {'accept': 'application/json', 'authorizationToken': self.authToken}
        url = 'https://api.activeiq.netapp.com/v1/clusterview/get-cluster-summary/' + lookup

        response = requests.get(url, headers=headers, verify=False)
        self.cluster_summary_data = json.loads(response.text)

    def getClusterResolver(self, lookup):

        headers = {'accept': 'application/json', 'authorizationToken': self.authToken}
        url = 'https://api.activeiq.netapp.com/v1/clusterview/resolver/' + lookup

        response = requests.get(url, headers=headers, verify=False)
        self.cluster_resolver = json.loads(response.text)

    def clusterSearch(self, lookup):

        headers = {'accept': 'application/json', 'authorizationToken': self.authToken}
        parseparams = {'name': lookup}
        url = 'https://api.activeiq.netapp.com/v1/search/aggregate/level/cluster?' + urlencode(parseparams)

        response = requests.get(url, headers=headers, verify=False)
        self.cluster_id = json.loads(response.text)

    def nodeEfficiency(self, lookup, **kwargs):

        headers = {'accept': 'application/json', 'authorizationToken': self.authToken}
        url = 'https://api.activeiq.netapp.com/v1/efficiency/summary/level/serial_numbers/id/' + lookup

        response = requests.get(url, headers=headers, verify=False)
        json_data = json.loads(response.text)
        node_entry = { lookup : {} }
        for key in json_data['efficiency']['systems']['system'][0]:
            node_entry[lookup].update({ key : json_data['efficiency']['systems']['system'][0][key] })
        for key, value in kwargs.items():
            node_entry[lookup].update({ key : value })
        self.node_efficiency.update(node_entry)

    def clusterNodeUpdate(self, json_data):

        self.nodeEfficiency(json_data['serial'], model=json_data['model'])

    def lookup(self, lookup, output=False):

        self.customerLookup(lookup)

        for key in self.customer_data:
            if key == "message":
                print("Lookup Error: " + self.customer_data[key])
                sys.exit(1)
            if key == "results":
                for result in self.customer_data[key]:
                    self.id.append(result['id'])
                    if output is True:
                        print("Name:  " + result['name'])
                        print("Count: " + result['count'])
                        print("ID:    " + result['id'])

    def inventory(self, lookup, name=False):

        if name is True:
            self.lookup(lookup)
            if len(self.id) > 1:
                print("Too many matches found, please narrow your search term")
                sys.exit(1)
            lookup_id = self.id[0]
        else:
            lookup_id = lookup

        listThread = threading.Thread(target=self.systemList, args=(lookup_id,))
        capacityThread = threading.Thread(target=self.capacityDetail, args=(lookup_id,))
        listThread.start()
        capacityThread.start()
        listThread.join()
        capacityThread.join()

        printLineNum = 1

        for key in self.system_list:
            if key == "message":
                print("Error: " + self.system_list[key])
                sys.exit(1)
            if key == "results":
                for result in self.system_list[key]:
                    system_used = 'N/A'
                    system_percent = 'N/A'
                    system_allocated = 'N/A'
                    for key in self.capacity_detail:
                        if key == "message":
                            print("Error: " + self.capacity_detail[key])
                            sys.exit(1)
                        if key == "capacity":
                            stillSearching = 1
                            for detail in self.capacity_detail[key]:
                                for category in self.capacity_detail[key][detail]:
                                    if stillSearching == 0:
                                        break
                                    for system in self.capacity_detail[key][detail][category]:
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

    def disk(self, lookup, name=False):

        if name is True:
            self.lookup(lookup)
            if len(self.id) > 1:
                print("Too many matches found, please narrow your search term")
            lookup_id = self.id[0]
        else:
            lookup_id = lookup

        self.capacityDetail(lookup_id)

        forecast_data = { 'results' : [] }
        sorted_data = {}
        for key in self.capacity_detail:
            if key == "message":
                print("Error: " + self.capacity_detail[key])
                sys.exit(1)
            if key == "capacity":
                for detail in self.capacity_detail[key]:
                    for category in self.capacity_detail[key][detail]:
                        if category == "current_90":
                            fullStatus = "Currently Full"
                        elif category == "1_month_90":
                            fullStatus = "1 Month To Full"
                        elif category == "3_months_90":
                            fullStatus = "3 Months To Full"
                        elif category == "6_months_90":
                            fullStatus = "6 Months To Full"
                        else:
                            fullStatus = "More Than 6 Months To Full"
                        for system in self.capacity_detail[key][detail][category]:
                            system_entry = {}
                            system_hostname = { 'hostname' : system['hostname'] }
                            system_capacity_percent = { 'capacity' : system['percent_capacity'] }
                            system_full_status = { 'status' : fullStatus }
                            system_entry.update(system_hostname)
                            system_entry.update(system_capacity_percent)
                            system_entry.update(system_full_status)
                            forecast_data['results'].append(system_entry)

        sorted_data['results'] = sorted(forecast_data['results'], key=lambda k: k['capacity'], reverse=False)

        for x in range(len(sorted_data['results'])):
            if x == 0:
                print("%s %s %s" % ('Hostname'.ljust(25),
                                    'Percent'.ljust(10),
                                    'Time To Full'))
            print("%s %s %s" % (str(sorted_data['results'][x]['hostname']).ljust(25),
                                str(sorted_data['results'][x]['capacity']).ljust(10),
                                str(sorted_data['results'][x]['status'])))

    def cluster(self, lookup, name=False):

        if name is True:
            self.clusterSearch(lookup)
            if len(self.cluster_id['results']) == 0:
                print("Error: cluster %s not found" % lookup)
                sys.exit(1)
            lookup_id = self.cluster_id['results'][0]['id']
        else:
            lookup_id = lookup

        summaryThread = threading.Thread(target=self.getClusterSummary, args=(lookup_id,))
        resolverThread = threading.Thread(target=self.getClusterResolver, args=(lookup_id,))
        summaryThread.start()
        resolverThread.start()
        summaryThread.join()
        resolverThread.join()

        for key in self.cluster_summary_data:
            if key == "message":
                print("Error: %s" % self.cluster_summary_data[key])
                sys.exit(1)
            elif key == "errors":
                print("Error: %s" % self.cluster_summary_data[key][0]['message'])
                sys.exit(1)
            if key == "data":
                for attribute in self.cluster_summary_data[key][0]:
                    print("%s = %s" % (str(attribute).ljust(25), self.cluster_summary_data[key][0][attribute]))

        threads = []
        for key in self.cluster_resolver:
            if key == "message":
                print("Error: " + self.cluster_resolver[key])
                sys.exit(1)
            if key == "clusters":
                for x in range(len(self.cluster_resolver[key][0]['nodes'])):
                    runThread = threading.Thread(target=self.clusterNodeUpdate, args=(self.cluster_resolver[key][0]['nodes'][x],))
                    runThread.start()
                    threads.append(runThread)

        for x in range(len(threads)):
            threads[x].join()

        total_efficiency = 0.0
        for key in self.node_efficiency:
            total_efficiency = total_efficiency + float(self.node_efficiency[key]['node_overall_efficiency_ratio_without_clone_snapshot'])
            print("%s = Serial: %s Model: %s Efficiency: %s" % (str(self.node_efficiency[key]['hostname']).ljust(25),
                                                           str(self.node_efficiency[key]['serial_number']),
                                                           str(self.node_efficiency[key]['model']).ljust(10),
                                                           str(self.node_efficiency[key]['node_overall_efficiency_ratio_without_clone_snapshot'])))

        average_efficiency = float(total_efficiency) / float(len(self.node_efficiency))
        print("Average Efficiency: %.2f" % average_efficiency)

def main():

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    runargs = parse_args()
    runargs.parse()

    myToken = auth_token(runargs)
    myToken.makeAuthPath()

    if runargs.refreshFlag:
        myToken.genToken()

    query = activeiq(myToken)

    if runargs.lookupName is not None and runargs.argCount == 1:
        query.lookup(runargs.lookupName, output=True)
    elif runargs.listFlag:
        if runargs.lookupName:
            query.inventory(runargs.lookupName, name=True)
        elif runargs.id:
            query.inventory(runargs.id)
        else:
            print("Error: Lookup requires either an ID or name")
    elif runargs.forecastFlag:
        if runargs.lookupName:
            query.disk(runargs.lookupName, name=True)
        elif runargs.id:
            query.disk(runargs.id)
        else:
            print("Error: Forecast requires either an ID or name")
    elif runargs.clusterFlag:
        if runargs.serialNumber:
            query.cluster(runargs.serialNumber)
        elif runargs.lookupName:
            query.cluster(runargs.lookupName, name=True)
        else:
            print("Error: Cluster lookup requires a name or a serial number")

if __name__ == '__main__':

    try:
        main()
    except SystemExit as e:
        if e.code == 0:
            os._exit(0)
        else:
            os._exit(e.code)