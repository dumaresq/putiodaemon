pudiodaemon
===========
  * This is very ALPHA use at your own RISK!
  * It will allow you "watch a directory" and upload that to putio.  
  * Then after the torrent is on putio it will download it.
  * You need the follwing on your computer:
    * Python 2.7
    * putio API (https://github.com/cenkalti/putio.py)
  * You need a putio OAUTH_TOKEN (https://put.io/v2/oauth2/register)
    * I should probably allow you to register here... 
  * To run this:
    * update putiodeamon.default
    * update putiodaemon.config
    * cp putiodaemon.default /etc/default/putiodaemon
    * cp putiodaemon.init /etc/init.d/putiodaemon
    * cp putiodeamon.config to /etc/putiodaemon
  * You can run it manually without doing the above
  
