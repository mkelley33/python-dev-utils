#!/usr/local/bin/python
"""
A helper program for managing the birth, life, and death of a MySQL ramdisk.

Thank you Wayne Moore at http://kotega.com/ for the following article: 
"Running MySQL in a ramdisk on OS X" 
http://kotega.com/blog/2010/apr/12/mysql-ramdisk-osx/

"""

from optparse import OptionGroup, OptionParser 
from subprocess import Popen, PIPE


# Overrideable defaults for ramdisk:
RAMDISK_SIZE = 128 # default to 128 MB. override with -s option
RAMDISK_PATH = '/dev/disk1' # overide with -p option 


def main():
    parser = OptionParser()
    
    # Option group for killing ramdisk:
    group_kill_ramdisk = OptionGroup(parser, 'The death of a ramdisk',
                                     'Short for `hdiutil detach /dev/disk1`'
                                     ' with some extra handling and default'
                                     ' location of /dev/disk1.') 
    group_kill_ramdisk.add_option('-k', '--kill-ramdisk', action='store_true', 
                                  dest='kill_ramdisk')
    group_kill_ramdisk.add_option('-p', '--path-to-ramdisk', type='string', 
                                  default=RAMDISK_PATH,
                                  dest='path_to_ramdisk')
    parser.add_option_group(group_kill_ramdisk)
    
    # Option group for creating ramdisk (and maybe loading it up with mysql):
    group_create_ramdisk = OptionGroup(parser, 'The birth of a ramdisk',
                                       'Creates a ramdisk, installs,'
                                       ' and starts MySQL')
    group_create_ramdisk.add_option('-c', '--create-ramdisk', 
                                    action='store_true', 
                                    dest='create_ramdisk')
    group_create_ramdisk.add_option('-s', '--ramdisk-size', 
                                    default=RAMDISK_SIZE, 
                                    type='int', dest='ramdisk_size')
    # I group installing and starting the mysql db here out of convenience. 
    # TODO create an option for Solr here too.
    group_create_ramdisk.add_option('-m', '--with-mysql', 
                                    action='store_true',
                                    dest='with_mysql')

    parser.add_option_group(group_create_ramdisk)
    
    (options, args) = parser.parse_args()
    
    if options.create_ramdisk:    
        create_ramdisk(calc_ramdisk_size(options.ramdisk_size))
        if options.with_mysql:
            install_db()
            start_db()
    elif options.kill_ramdisk:
        kill_ramdisk(options.path_to_ramdisk)


def calc_ramdisk_size(num_megabytes):
    return num_megabytes * 1048576 / 512 # MB * MiB/KB; 


def create_ramdisk(ramdisk_size):
    print 'Creating ramdisk...'
    disk_path = Popen('hdiutil attach -nomount ram://%s' % ramdisk_size, 
                      stdout=PIPE, shell=True).communicate()[0]
    Popen('diskutil eraseVolume HFS+ ramdisk %s' % disk_path, stdout=PIPE,
          shell=True).communicate()
    print 'Done creating ramdisk: %s' % disk_path


def kill_ramdisk(path_to_ramdisk):
    # TODO make sure that MySQL isn't running first!
    print Popen(('hdiutil detach %s' % path_to_ramdisk), stdout=PIPE, 
                 shell=True).communicate()[0]

def install_db():
    # TODO support other dbs?
    print 'Installing new db...'
    p = Popen('/usr/local/mysql/scripts/mysql_install_db '
              '--user=mysql '
              '--basedir=/usr/local/mysql '
              '--datadir=/Volumes/ramdisk', shell=True)
    p.communicate()
    print 'Done installing db.' 


def start_db():
    # TODO support other dbs?
    # TODO make it more configurable?
    print 'Starting db...'
    p = Popen('/usr/local/mysql/bin/mysqld '
              '--basedir=/usr/local/mysql '
              '--datadir=/Volumes/ramdisk '
              '--user=mysql '
              '--log-error=/Volumes/ramdisk/mysql.ramdisk.err '
              '--pid-file=/Volumes/ramdisk/mysql.ramdisk.pid '
              '--port=3308 '
              '--socket=/tmp/mysql.sock &', stdout=PIPE, shell=True)
    p.communicate()
    print 'Done starting db.'

if __name__ == "__main__":
    main()
