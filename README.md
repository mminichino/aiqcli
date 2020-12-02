# aiqcli

NetApp Active IQ CLI

To use this script you will need to get access to Active IQ APIs and generate a Refresh Token. The first time the script is run it will prompt for the Refresh Token and create the Access and Refresh Token files under the current user's home directory. This script needs the ````requests```` Python module.

````
$ pip install requests
$ git clone https://github.com/mminichino/aiqcli
$ cd aiqcli
$ ./aiqcli.py -r
````

To list an account:
````
$ ./aiqcli.py -n "Company Name"
Name:  Company Name Inc.
Count: 100
ID:    1234567
````

To list the inventory at an account:
````
$ ./aiqcli.py -i 1234567 -l
````

Or to list the inventory by name:
````
$ ./aiqcli.py -n "Company Name" -l
````

View the inventory with easy to read output (as opposed to CSV):
````
$ ./aiqcli.py -i 1234567 -l -t
````

To view the capacity forecast (with current capacity by hostname):
````
$ ./aiqcli.py -i 1234567 -f
````

To view the capacity forecast by name:
````
$ ./aiqcli.py -n "Company Name" -f
````

View information about an ONTAP cluster by node serial number:
````
$ ./aiqcli.py -c -s 1234567890
````

To view cluster information by cluster name:
````
$ ./aiqcli.py -c -n ntapclu1234
````
