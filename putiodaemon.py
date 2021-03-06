#!/usr/bin/python

import daemon
import time
import shutil
import os
import putio
import lockfile
import sys
import getopt 
import ConfigParser
import BaseHTTPServer
import urlparse
import logging
import threading
import SocketServer
import cgi
import signal

from lockfile.pidlockfile import PIDLockFile
from lockfile import AlreadyLocked
from SimpleHTTPServer import SimpleHTTPRequestHandler

class ThreadedHTTPServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    pass 

class MyHandler(SimpleHTTPRequestHandler):

    def log_message(self, format, *args):
        """ wanted to write to a file rather then stderr so I have to override log_message for the http server """
        logging.info("%s - - [%s] %s\n" %
                         (self.client_address[0],
                          self.log_date_time_string(),
                          format%args))

    def do_POST(self):
        """ The HTTP server calls this for ever post message """
        parsedParams = urlparse.urlparse(self.path)
        queryParsed = urlparse.parse_qs(parsedParams.query)
        try: 
            uri = instance.httppath
        except: 
            logging.error('Something failed: %s', sys.exc_info())
        # We respond with a 404 unless you put in this url  I'm using the PUTIO token maybe something
        # else would be safer
        if  '/' + instance.httppath + '/api/' + instance.token in parsedParams.path :
            form = cgi.FieldStorage(
                fp=self.rfile, 
                headers=self.headers,
                environ={'REQUEST_METHOD':'POST',
                     'CONTENT_TYPE':self.headers['Content-Type'],
                })
            self.send_response(200)
            self.end_headers()
            self.wfile.write("Recieved")
            instance.download(form)
            self.wfile.close
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write("NotFound")
            self.wfile.close

    def do_GET(self):
        """ The HTTP server should return 404 for EVERYTHING """
        self.send_response(404)
        self.end_headers()
        self.wfile.write("NotFound")
        self.wfile.close
 

class putioDaemon():

    def __init__(self):
        self.torrentdir = "/var/tmp" 
        self.token = ""
        self.pidfile = "/var/run/putiodaemon/putiodaemon.pid"
        self.conffile = "/etc/putiodaemon"
        self.logfile = "/tmp/putiodaemon.log"
        self.listen = True
        self.delete = True
        self.debug = 2
	self.ip = "127.0.0.1"
        self.port = "8765"
        self.httppath = "/"
        self.callback = ""
        self.downoad_dir = "/var/tmp"
        self.downloadtemp_dir = "/var/tmp"

    def readconfig(self):
       config = ConfigParser.RawConfigParser(allow_no_value=True)
       config.read(self.conffile)
       if config.has_section('putioDaemon'):
          configlist = config.options('putioDaemon')
          if ('oauth_token' in configlist):
             self.token = config.get('putioDaemon', 'oauth_token')
          else:
             print ('Config is missing oauth_token')
             sys.exit(3)
          if 'torrentdirectory' in configlist:
             self.torrentdir = config.get('putioDaemon', 'TorrentDirectory')
          if 'listen' in configlist:
             self.listen = config.getboolean('putioDaemon', 'listen')
          if 'logfile' in configlist:
             self.logfile = config.get('putioDaemon', 'logfile')
          if 'putiodelete' in configlist:
             self.delete = config.getboolean('putioDaemon', 'putiodelete')
             if self.listen:
                if ('ip' in configlist and 'port' in configlist and 'httppath' in configlist 
                         and 'callback' in configlist and 'downloaddir' in configlist and 'downloadtempdir' in configlist):
                   self.ip = config.get('putioDaemon', 'ip')
                   self.port = config.get('putioDaemon', 'port')
                   self.httppath = config.get ('putioDaemon', 'httppath')
                   self.callback = config.get ('putioDaemon', 'callback')
                   self.download_dir = config.get ('putioDaemon','downloaddir')
                   self.downloadtemp_dir = config.get ('putioDaemon','downloadtempdir')
                else:
                   print ('Config has Listen set to true but does not contain all of the required elements (ip,port,httppath,callback,downloaddir and downloadtempdir)')
                   sys.exit(3)
       else:
          print 'Config file is missing section putioDaemon'
          sys.exit(3)
          
    def getinputs(self, argv):
        try:
            opts, args = getopt.getopt(argv,"hi:o:",["confile=","pidfile=","debug="])
        except getopt.GetoptError:
             print 'putiodaemon.py -c <configfile> -p <pidfile> -debug <1/2/3>'
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
             elif opt in ("-d", "--debug"):
                  self.debug = int(arg)

    def setuplogging(self):
        try:
            loglevel = logging.INFO
            if self.debug == 3:
               loglevel = logging.DEBUG
            if self.debug == 1:
               loglevel = logging.ERROR
            logging.basicConfig(filename=self.logfile, format='%(levelname)s %(asctime)s:%(message)s', level=loglevel)
        except:
            print "Can't Open Logfile:", sys.exc_info()
        logging.info('Started')

    def download(self,form):
        """ This gets called when putio does the call back URL """
        logging.info("Got Call back with data: %s",form)
        logging.info("Processing file_id %s",form['file_id'].value)
        client = putio.Client(self.token)
        files = client.File.list()
        self.delete = 0 #May want to change this later
        for f in files:
            if str(f.id) == str(form['file_id'].value):
                logging.info('Download of %s starting',f.name)
                client.File.download(f, dest=self.downloadtemp_dir, delete_after_download=self.delete)
                logging.info('Download of %s completed',f.name)
		# We use a temporary location and move it just incase you have a renamer in place.  
                shutil.move(self.downloadtemp_dir+"/"+str(f.name),self.download_dir)

def WebServer():
    """ Sets up the Web server for the call back URL from putio """
    HandlerClass = SimpleHTTPRequestHandler
    ServerClass  = BaseHTTPServer.HTTPServer
    HandlerClass.protocal_version = "HTTP/1.1"
    try:
        instance.httpd = ThreadedHTTPServer((instance.ip,int(instance.port)),MyHandler)
    except:
        logging.error('Failed to set ServerClass %s', sys.exc_info())
    instance.sa = instance.httpd.socket.getsockname()
    logging.info('Serving HTTP on %s port %s...', instance.sa[0], instance.sa[1])
    threading.Thread(target=instance.httpd.serve_forever).start()

def handler(signum, frame):
    """ I'm not sure why this is needed but it won't shutdown unless I manually kill httpd"""
    logging.info('Signal handler called with signali %s', signum);
    if instance.listen:
      logging.info('Trying to Shutdown HTTP Server')
      try:
         instance.httpd.shutdown()
      except: 
         logging.error('Failed to shutdown %s', sys.exc_info())
    sys.exit(0)
 
def putioCheck():
    """ Should probably be in a class """
    global instance 
    instance = putioDaemon()
    instance.getinputs(sys.argv[1:])
    instance.readconfig()
    instance.setuplogging()
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
    logging.debug('Listen is %s', instance.listen)
    if instance.listen:
       WebServer()
    signal.signal(signal.SIGTERM,handler)
    while True:
        if os.path.exists(instance.torrentdir):
            onlyfiles = [ f for f in os.listdir(instance.torrentdir) if os.path.isfile(os.path.join(instance.torrentdir,f))] 
            if len(onlyfiles):  
                client = putio.Client(instance.token)
                for torrent in onlyfiles:
                    logging.info('working on %s', torrent) 
                    # if we are listening then use the callback_url
                    callback_url = None
                    if instance.listen:
                       callback_url = 'http://'+instance.callback+'/'+instance.httppath+'/api/'+instance.token
                    logging.info('Calling add_torrent for %s with %s',torrent,callback_url)
                    client.Transfer.add_torrent(instance.torrentdir+"/"+torrent, callback_url=callback_url)
                    os.remove(instance.torrentdir+"/"+torrent)
        time.sleep(5)

def run():
    context = daemon.DaemonContext(stdout=sys.stdout)
    with context:
        putioCheck()
#    putioCheck()

if __name__ == "__main__":
    run()
