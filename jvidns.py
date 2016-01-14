#!/usr/bin/python

import argparse
import sys
import pprint
import json
import os
import inspect
import yaml
import hashlib

APP_PATH = os.path.realpath(os.path.abspath(os.path.split(inspect.getfile( inspect.currentframe() ))[0]))
if APP_PATH + '/modules' not in sys.path: sys.path.insert(0, APP_PATH + '/modules')

import jvidb
import jviLog

DEBUG=0
MYSQL_USER=None
MYSQL_PASS=None
MYSQL_HOST=None

def get_config(APP_PATH):
  try:
      with open('%s/config/jvidns.yaml' %(APP_PATH), 'r') as f:
          data_yaml = yaml.load(f)

          global DEBUG
          global MYSQL_USER
          global MYSQL_PASS
          global MYSQL_HOST

          DEBUG = data_yaml['debug']
          MYSQL_USER = data_yaml['mysql_user']
          MYSQL_PASS = data_yaml['mysql_pass']
          MYSQL_HOST = data_yaml['mysql_host']

  except (yaml.scanner.ScannerError, KeyError, TypeError) as e:
      print e
      sys.exit(1)

# Get initial configuration 
get_config(APP_PATH)

x = jviLog.jviLog(APP_PATH + "/log/jvidns.log")
dns = jvidb.mysql(host=MYSQL_HOST, username=MYSQL_USER, password=MYSQL_PASS, log=x, debug=DEBUG)


"""
Usage:
~~~~~~
 - this will show all records for a domain name

$ jvidns -d example.com

 - this will create 3 A records www, mail and ftp pointing to the destination IP 192.168.1.100

$ jvidns --domain example.com --dst 192.168.1.100 --type A --records www mail ftp

 - this will create 3 records, www type CNAME pointing to www.booking.com, mail type A pointing to 191.168.10.1 and an ftp type A pointing
   to the IP 200.32.33.34

$ jvidns --domain example.com --records www=CNAME=www.booking.com mail=A=192.168.10.1 ftp=A=200.32.33.34

"""

parser = argparse.ArgumentParser(prog='Jvidns', description='Manage DNS records.', 
    epilog="Usage: jvidns --domain example.com --dst 192.168.1.100 --type A --records www mail ftp")

parser.add_argument('-d', '--domain', dest='domain', help='Domain name (ie.: example.com)', required=True, type=str)
parser.add_argument('--delete-record', dest='delete_record', help='Record to delete', required=False, type=str)
parser.add_argument('--delete-all', dest='delete_all', help='Delete the domain name and all records', action='store_true', required=False)
parser.add_argument('--type', help='Record type. A,CNAME,TXT (default: A)', type=str, default="A")
parser.add_argument('-r', '--records', dest='records', type=str, nargs='+', help='List of records to add ie.: www ftp\
  OR www=CNAME=www.example.com mail=A=192.168.10.1', required=False)

args = parser.parse_args()


recordobj = {}

print args.delete_all

try:
    if args.delete_all==False:
        # add domain if not exists
        dns.add_domain(args.domain)

    if args.records!=None:
        for record in args.records:
            if record.find('=')!=-1 and record.count('=')==2:
                recordline = record.split('=')
                # create a record like this {'www': {'type':'CNAME', 'value':'192.168.1.100'}}
                recordobj[recordline[0]] = {'type': recordline[1].upper(),'value': recordline[2]}
            else:
                if args.dst!=None:
                    # create a record like this {'www': {'type':'CNAME', 'value':'192.168.1.100'}}
                    recordobj[record] = {'type': args.type,'value': args.dst}        
        
        # add/update or delete the information 
        if args.delete_record==None:
            result = dns.add_records(args.domain, recordobj)

    if args.delete_record!=None:
        result = dns.delete_record(args.delete, args.domain)

    if args.delete_all:
        print "Entring"
        result = dns.delete_domain(args.domain)
        

    # return all the information related to a domain
    domain_data = dns.get_all(domain=args.domain)

    # output data as json
    json_out = json.dumps(domain_data, sort_keys=True)
    print json_out

    # get the md5 output to compare with the latest md5 and update the serial number
    # print hashlib.sha224(json_out).hexdigest()
    print hashlib.md5(json_out).hexdigest()

except Exception as e:
    print e