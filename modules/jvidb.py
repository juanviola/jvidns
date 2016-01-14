import MySQLdb
import MySQLdb.cursors
import datetime
import pprint 
import hashlib
import json

# Mysql 
class mysql:
    def __init__(self, username='', password='', host='localhost', database='jvidns', connect_timeout=30, port=3306, log=None, debug=0):
        self.username = username
        self.password = password
        self.hostname = host
        self.database = database
        self.connect_timeout = connect_timeout
        self.port = port

        # database object
        self.db = None

        # logging info
        self.debug  = debug
        self.log    = log

    def connect(self):
        try:
            db = MySQLdb.connect(user=self.username, passwd=self.password, db=self.database, host=self.hostname, cursorclass=MySQLdb.cursors.DictCursor)
            return db
        except Exception as e:
            #print "connect(): %s" %e
            self.log.Log('jvidb.mysql.connect: %s' %e)
            pass

    def add_domain(self, name, serial=None, refresh=604800, retry=86400, expire=2419200, negative_cache_ttl=604800):
        """
        add a new domain name
        """
        if len(name)>253:
            self.log.Log('Name length exceeded')
            raise Exception('Name length exceeded')

        if serial==None:
            serial = datetime.datetime.today().strftime('%Y%m%d%w') + '0'

        query = "INSERT INTO domains(name,serial,refresh,retry,expire,negative_cache_ttl) " \
                "VALUES('%s','%s','%s','%s','%s','%s')" %(name,int(serial),int(refresh), \
                    int(retry),int(expire),int(negative_cache_ttl))

        if self.debug>0: self.log.Log('jvidb.mysql.add_domain: %s' %query)

        try:
            self.db = self.connect()
            cursor = self.db.cursor()
            cursor.execute(query)
            self.db.commit()
            self.create_hash(name)
        except (MySQLdb.Error,Exception,AttributeError) as e:
            self.log.Log('jvidb.mysql.add_domain: %s' %e)
            # print "add_domain(): %s" %(e) + "-"*20


    def add_records(self, name=None, records={}):
        if name==None:
            self.log.Log('add_records: domain name is required')
            raise Exception('add_records(): domain name is required')

        domain_id = self.get_domain_id(name)

        # print "domain: %s" %name
        # print "domain id: %s" %domain_id
        # print type(records)

        # try:
        #     self.db = self.connect()
        #     cursor = self.db.cursor()
        # except (MySQLdb.Error,Exception,AttributeError) as e:
        #     print "add_records(): %s" %(e) + "-"*20

        for key,value in records.iteritems():
            # print key
            # print value['type']
            # print value['value']
            
            if self.debug>0: self.log.Log("jvidb.mysql.add_records: key=%s value.type=%s value.value=%s" %(key,value['type'],value['value']))

            record_id = self.get_record(name=key,value=value['value'],domain_id=domain_id)

            if record_id==None:
                """ create new record """
                query = "INSERT INTO domain_records(domain_id,name,type,dst) VALUES('%s','%s','%s','%s')" \
                    %(domain_id, key, value['type'], value['value'])
                # print query
            else:
                """ update new record """
                query = "UPDATE domain_records SET name='%s', type='%s', dst='%s' WHERE id='%s'" \
                    %(key,value['type'],value['value'],record_id)
                # print query

            if self.debug>0: self.log.Log('jvidb.mysql.add_records: %s' %query)

            try:
                #print "trying insert................."
                self.db = self.connect()
                cursor = self.db.cursor()
                cursor.execute(query)
                self.db.commit()
            except (Exception,AttributeError) as e:
                print "add_records(): %s" %(e) + "-"*20

        self.db.close()

    def get_domain_id(self, name=None):
        """ 
        return int(id) from str(domain) name
        """
        if name==None:
            raise Exception('Domain name must be specified')

        query = "SELECT id FROM domains WHERE name='%s' " %(name)

        try:
            self.db = self.connect()
            cursor = self.db.cursor()
            cursor.execute(query)
            data = cursor.fetchone()
            return int(data['id'])
        except (Exception,AttributeError) as e:
            print "get_domain_id(): %s" %(e)
            self.log.Log('jvidb.mysql.get_domain_id: %s' %e, msg_type='error')

    def get_record(self, name=None, value=None, domain_id=None):
        if name==None or domain_id==None:
            self.log.Log('jvidb.mysql.get_record: record name and domain name are required')
            raise Exception('get_records(): domain name is required')

        try:
            self.db = self.connect()
            cursor = self.db.cursor()
            query = "SELECT * FROM domain_records WHERE domain_id='%s' AND name='%s'" %(domain_id, name)
            if self.debug>0: self.log.Log('jvidb.mysql.get_record: query: %s' %query)
            cursor.execute(query)
            data = cursor.fetchone()
            if data==None:
                return None
            return data['id']
        except Exception as e:
            self.log.Log('jvidb.mysql.get_record: query: %s' %e)


    def delete_domain(self, domain=None):
        if domain==None:
            self.log.Log('jvidb.mysql.delete_domain: domain name is required')
            raise Exception('delete_domain(): domain name is required')

        domain_id = self.get_domain_id(domain)

        query = "DELETE domains,domain_records FROM domains INNER JOIN domain_records ON domain_records.domain_id = domains.id WHERE domains.id = %s" %(domain_id) 

        try:
            self.db = self.connect()
            cursor = self.db.cursor()
            cursor.execute(query)
            self.db.commit()
            self.log.Log('jvidb.mysql.delete_domain: %s' %query, msg_type='info')
        except (Exception,AttributeError) as e:
            print "delete_domain(): %s" %(e)
            self.log.Log('jvidb.mysql.delete_domain: %s' %e, msg_type='error')

    def delete_record(self, name=None, domain=None):
        if name==None or domain==None:
            self.log.Log('jvidb.mysql.delete_record: domain name is required')
            raise Exception('delete_records(): domain name is required')

        domain_id = self.get_domain_id(domain)

        try:
            record_id = self.get_record(name=name, domain_id=domain_id)

            if record_id!=None:
                self.db = self.connect()
                cursor = self.db.cursor()
                query = "DELETE FROM domain_records WHERE domain_id='%s' AND name='%s'" %(domain_id, name)
                if self.debug>0: self.log.Log('jvidb.mysql.delete_record: query: %s' %query)
                x = cursor.execute(query)
                self.db.commit()
                print x
                return True
            
            if data==None:
                return None
            return data['id']
        except Exception as e:
            self.log.Log('jvidb.mysql.delete_record: query: %s' %e)
            # print e

    def get_all(self, domain=None):
        if domain==None:
            self.log.Log('jvidb.mysql.get_all: record name and domain name are required')
            raise Exception('get_records(): domain name is required')

        try:
            self.db = self.connect()
            cursor = self.db.cursor()
            # query = "SELECT * FROM domains WHERE domain_id='%s' AND name='%s'" %(domain_id, name)

            query = "SELECT domains.name,dr.name AS record,dr.type AS type, dr.dst AS dst from domains "\
                "INNER JOIN domain_records AS dr ON (dr.domain_id=domains.id) WHERE domains.name='%s' ORDER BY record"\
                %(domain)

            if self.debug>0: self.log.Log('jvidb.mysql.get_all: query: %s' %query)
            cursor.execute(query)
            data = cursor.fetchall()
            if data==None:
                return None
            return data
            # pprint.pprint(data)
        except Exception as e:
            self.log.Log('jvidb.mysql.get_all: query: %s' %e)

    def update_hash(self, domain=None, hashmd=None):
        query = "SELECT hashmd5 FROM domains WHERE name='%s'" %(domain)
        print query
        return False

    def get_hash(self, domain=None, hashmd=None):
        query = "UPDATE domains SET hashmd5='%s' WHERE name='%s'" %(hashmd,domain)
        print query
        return False

    def create_hash(self, domain=None):
        data = self.get_all(domain)
        json_out = json.dumps(data, sort_keys=True)
        hashmd = hashlib.md5(json_out).hexdigest()
        self.update_hash(domain, hashmd)

    def fetchdict(self, query=''):
        try:
            db = self.connect()
            cursor = db.cursor()
            cursor.execute(query)
            data = cursor.fetchall()
            return data
        except Exception as e:
            return e


