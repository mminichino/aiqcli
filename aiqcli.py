#!/usr/bin/env python
#

try:
    from urllib.parse import urlencode
except ImportError:
     from urllib import urlencode

import getopt, sys, os, stat, subprocess, requests, urllib3, json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
homeDir = os.environ.get('HOME')
authDir = '/activeiq'
authPath = homeDir + authDir
refreshTokenFile = authPath + '/RefreshToken.txt'
accessTokenFile = authPath + '/AccessToken.txt'
arglist = []
repId = None
inventoryId = None
diskId = None
perfId = None
refreshFlag = False
lookupFlag = None
verboseFlag = False
textFormatFlag = False
diskThreshold = 70
perfThreshold = 50

def usage():
    print("NetApp Active IQ CLI")
    print("Usage: " + sys.argv[0] + " [-v] [-r] [-a auth_dir] [-d ID] [-u ID] [-l string] [-i ID] [-f percent] [-p percent] [-t]")
    print("")
    print("-v  Verbose output")
    print("-r  Refresh Access Token from Refresh Token")
    print("-a  Auth directory - location to store the access and refresh tokens")
    print("-d  Display systems with predicted disk capacity over threshold by ID")
    print("-u  Display systems with utilization over threshold by ID - CPU >=90, Disk >=50, Unbalanced >=40")
    print("-l  Find a customer ID with a search string")
    print("-i  Display inventory by ID as comma separated values")
    print("-f  Filter disk results greater or equal to this percentage")
    print("-p  Filter utilization results where possible to greater or equal to this percentage")
    print("-t  Format inventory output for screen display")

options, remainder = getopt.getopt(sys.argv[1:], 'hvrta:d:u:l:i:f:p:', arglist)

for opt, arg in options:
    if opt in ('-a', '--auth'):
        authPath = arg
        refreshTokenFile = authPath + '/RefreshToken.txt'
        accessTokenFile = authPath + '/AccessToken.txt'
    elif opt in ('-d', '--disk'):
        diskId = arg
    elif opt in ('-u', '--usage'):
        perfId = arg
    elif opt in ('-i', '--inventory'):
        inventoryId = arg
    elif opt in ('-r', '--refresh'):
        refreshFlag = True
    elif opt in ('-l', '--lookup'):
        lookupFlag = arg
    elif opt in ('-v', '--verbose'):
        verboseFlag = True
    elif opt in ('-f', '--disk_threshold'):
        try:
            diskThreshold = int(arg)
        except ValueError:
            print("Invalid argument for disk full threshold: " + str(arg))
            sys.exit(1)
    elif opt in ('-p', '--perf_threshold'):
        try:
            perfThreshold = int(arg)
        except ValueError:
            print("Invalid argument for performance threshold: " + str(arg))
            sys.exit(1)
    elif opt in ('-t', '--inventory_format'):
        textFormatFlag = True
    elif opt in ('-h', '--help'):
        usage()
        sys.exit(0)
    else:
        usage()
        sys.exit(1)

if (not os.path.exists(refreshTokenFile)):
    print("Refresh token not found")
    try:
        os.mkdir(authPath)
    except OSError as error:
        print("Auth directory already exists")
    print("Please enter a valid refresh token:")
    inputData = sys.stdin.readline()
    refreshTokenFd = open(refreshTokenFile, "w")
    refreshTokenFd.write(inputData)
    refreshTokenFd.close()
    refreshFlag = True

if refreshFlag:
   refreshTokenFd = open(refreshTokenFile, "r")

   refreshToken = refreshTokenFd.readline()
   refreshToken = refreshToken.rstrip("\n")

   refreshTokenFd.close()

   url = 'https://api.activeiq.netapp.com/v1/tokens/accessToken'
   data = '''{ "refresh_token": "''' + refreshToken + '''" }'''

   response = requests.post(url, data=data, verify=False)
   json_data = json.loads(response.text)

   for key in json_data:
       if key == "error":
          print ("Error: " + json_data[key])
          sys.exit(1)
       if key == "access_token":
          accessTokenFd = open(accessTokenFile, "w")
          if verboseFlag:
              print ("Access Token:")
              print (json_data[key])
          accessTokenFd.write(json_data[key])
          accessTokenFd.close()
       if key == "refresh_token":
          refreshTokenFd = open(refreshTokenFile, "w")
          if verboseFlag:
              print ("Refresh Token:")
              print (json_data[key])
          refreshTokenFd.write(json_data[key])
          refreshTokenFd.close()

accessTokenFd = open(accessTokenFile, "r")

accessToken = accessTokenFd.readline()
accessToken = accessToken.rstrip("\n")

accessTokenFd.close()

if lookupFlag:

   headers = {'accept':'application/json','authorizationToken':accessToken}
   parseparams = {'name':lookupFlag}
   url = 'https://api.activeiq.netapp.com/v1/search/aggregate/level/customer?' + urlencode(parseparams)

   response = requests.get(url, headers=headers, verify=False)
   json_data = json.loads(response.text)

   for key in json_data:
       if key == "message":
          print ("Error: " + json_data[key])
          sys.exit(1)
       if key == "results":
          for result in json_data[key]:
              print ("Name:  " + result['name'])
              print ("Count: " + result['count'])
              print ("ID:    " + result['id'])

if inventoryId:

   headers = {'accept':'application/json','authorizationToken': accessToken}
   url = 'https://api.activeiq.netapp.com/v1/systemList/aggregate/level/customer/id/' + inventoryId

   response = requests.get(url, headers=headers, verify=False)
   json_data = json.loads(response.text)

   headers = {'accept': 'application/json', 'authorizationToken': accessToken}
   url = 'https://api.activeiq.netapp.com/v2/capacity/details/level/customer/id/' + inventoryId

   response = requests.get(url, headers=headers, verify=False)
   json_disk_data = json.loads(response.text)

   system_used = 'N/A'
   system_percent = 'N/A'
   system_allocated = 'N/A'
   stillSearching = 0
   printLineNum = 1

   for key in json_data:
       if key == "message":
          print ("Error: " + json_data[key])
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
              if textFormatFlag:
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
                      str(result['version']).ljust(10), str(system_used).ljust(12), str(system_percent).ljust(12),
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

if diskId:

    headers = {'accept': 'application/json', 'authorizationToken': accessToken}
    url = 'https://api.activeiq.netapp.com/v2/capacity/details/level/customer/id/' + diskId

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
                        if (system['percent_capacity'] >= diskThreshold):
                            print(fullStatus + ": Hostname: " + system['hostname'] + " Capacity: " + str(system['percent_capacity']))

if perfId:

    headers = {'accept': 'application/json', 'authorizationToken': accessToken}
    url = 'https://api.activeiq.netapp.com/v1/performance/summary/level/customer/id/' + perfId

    response = requests.get(url, headers=headers, verify=False)
    json_data = json.loads(response.text)

    for key in json_data:
        if key == "message":
            print("Error: " + json_data[key])
            sys.exit(1)
        if key == "sections":
            for section in json_data[key]:
                if section == "diskBusy":
                    for system in json_data[key][section]:
                        if (system['max_diskbusy_percent'] >= perfThreshold):
                            print("Disk: Hostname: " + system['node_name'] + " DiskBusy: " + str(system['max_diskbusy_percent']))
                if section == "cpuBusy":
                    for system in json_data[key][section]:
                        if (system['max_cpubusy_percent'] >= perfThreshold):
                            print("CPU: Hostname: " + system['node_name'] + " MaxCPUBusy: " + str(system['max_cpubusy_percent']) + " AvgCPUBusy: " + str(system['avg_cpubusy_percent']))
                if section == "unbalancedNode":
                    for system in json_data[key][section]:
                        if (system['average_cpu_busy'] >= perfThreshold):
                            print("Balance: Hostname: " + system['node_name'] + " CPUBusy: " + str(system['average_cpu_busy']) + " PartnerBusy: " + str(system['partner_average_cpu_busy']))
                if section == "noData":
                    for system in json_data[key][section]:
                        print("NoData: Hostname: " + system['node_name'] + " SerialNumber: " + str(system['serial_number']))