#!/usr/bin/python

import daemon
import time
import os
import putio
import lockfile
import sys
import getopt 
import ConfigParser
import BaseHTTPServer
import urlparse

from lockfile.pidlockfile import PIDLockFile
from lockfile import AlreadyLocked
from SimpleHTTPServer import SimpleHTTPRequestHandler


class MyHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsedParams = urlparse.urlparse(self.path)
        queryParsed = urlparse.parse_qs(parsedParams.query)
        try: 
            uri = putioDaemon.uri
        except: 
            print "Something failed:", sys.exc_info()
        if parsedParams.path == "/putiodaemon" :
            self.processMyRequest(queryParsed)
        else:
            SimpleHTTPRequestHandler.do_GET(self);

    def processMyRequest(self, query):
        self.send_response(200)
        self.end_headers()
        self.wfile.write("recieved")
        self.wfile.close
 

class putioDaemon():

    def __init__(self):
        self.torrentdir = "/var/tmp" 
        self.token = ""
        self.pidfile = "/var/run/putiodaemon/putiodaemon.pid"
        self.conffile = "/etc/putiodaemon"
        self.listen = 0
        self.uri = "/moo"



    def readconfig(self):
       config = ConfigParser.RawConfigParser(allow_no_value=True)
       config.read(self.conffile)
       # Needs work, maybe use .items or has_option ?
       self.torrentdir = config.get('putioDaemon', 'TorrentDirectory')
       self.token = config.get('putioDaemon', 'oauth_token')
       self.listen = config.get('putioDaemon', 'listen')
       if self.listen:
           self.ip = config.get('putioDaemon', 'ip')
           self.port = config.get('putioDaemon', 'port')
           self.httppath = config.get ('putioDaemon', 'httppath')
          
    def getinputs(self, argv):
        try:
            opts, args = getopt.getopt(argv,"hi:o:",["confile=","pidfile="])
        except getopt.GetoptError:
             print 'putiodaemon.py -c <configfile> -p <pidfile>'
             sys.exit(2)
        except:
             print "Something failed:", sys.exc_info()
             sys.exit(2)
        for opt, arg in opts:
             if opt == '-h':
                 print 'putiodaemon.py -c <configfile> -p <pidfile>'
                 sys.exit()
             elif opt in ("-p", "--pidfile"):
                  self.pidfile = arg
             elif opt in ("-c", "--conffile"):
                  self.conffile = arg

    def WebServer(self):
        HandlerClass = SimpleHTTPRequestHandler
        ServerClass  = BaseHTTPServer.HTTPServer
        HandlerClass.protocal_version = "HTTP/1.1"
        try:
            self.httpd = ServerClass((self.ip,int(self.port)),MyHandler)
        except:
            print "Failed to set ServerClass", sys.exc_info()
        self.sa = self.httpd.socket.getsockname()
        print "Serving HTTP on", self.sa[0], "port", self.sa[1], "..."
        self.httpd.serve_forever()
 



def putioCheck():
    instance = putioDaemon()
    instance.getinputs(sys.argv[1:])
    instance.readconfig()
    pidfile = PIDLockFile(instance.pidfile, timeout=-1)
    try:
        pidfile.acquire()
    except AlreadyLocked:
        try: 
            os.kill(pidfile.read_pid(),0)
            print 'Process already running!'
            exit (1)
        except OSError:
            pidfile.break_lock()
    except: 
        print "Something failed:", sys.exc_info()
        exit (1)
    if instance.listen:
       print "About to start web server"
       instance.WebServer()
    while True:
        if os.path.exists(instance.torrentdir):
#            print "Found Dir %s" % instance.torrentdir 
            onlyfiles = [ f for f in os.listdir(instance.torrentdir) if os.path.isfile(os.path.join(instance.torrentdir,f))] 
            if len(onlyfiles):  
                client = putio.Client(instance.token)
                for torrent in onlyfiles:
#                    print "working on %s" % torrent 
                    client.Transfer.add_torrent(instance.torrentdir+"/"+torrent)
		    os.remove(instance.torrentdir+"/"+torrent)
        time.sleep(5)

#def run():
#    context = daemon.DaemonContext(stdout=sys.stdout)
#    with context:
#        putioCheck()
putioCheck()
#if __name__ == "__main__":
#    run()
