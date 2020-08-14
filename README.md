# aiqcli

NetApp Active IQ CLI

To use this script you will need to get access to Active IQ APIs and generate a Refresh Token. The first time the script is run it will prompt for the Refresh Token and create the Access and Refresh Token files under the current user's home directory. This script needs the requests Python module.

````
$ pip install requests
$ git clone https://github.com/mminichino/aiqcli
$ cd aiqcli
$ ./aiqcli.py -r
$ ./aiqcli.py -l "Company Name"
Name:  Company Name Inc.
Count: 100
ID:    1234567
$ ./aiqcli.py -i 1234567 -t
$ ./aiqcli.py -i 1234567 > $HOME/inventory.csv
