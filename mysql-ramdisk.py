#!/usr/bin/env python
"""
A helper program for managing the birth, life, and death of a MySQL ramdisk.

Thank you Wayne Moore at http://kotega.com/ for the following article: 
"Running MySQL in a ramdisk on OS X" 
http://kotega.com/blog/2010/apr/12/mysql-ramdisk-osx/

"""

import os
import sys
from optparse import OptionGroup, OptionParser 
from subprocess import Popen, PIPE, call


# Overrideable defaults for ramdisk:
RAMDISK_SIZE = 128 # default to 128 MB. override with -s option
RAMDISK_PATH = '/dev/disk1' # overide with -p option 


def main():
    # TODO: maybe change RAMDISK_PATH from being a constant to *variable*?
    if is_linux():
        RAMDISK_PATH = '/mnt/ramdisk'
    else:
        RAMDISK_PATH = '/dev/disk1'       
    
    parser = OptionParser()
    
    # Option group for killing ramdisk:
    group_kill_ramdisk = OptionGroup(parser, 'The death of a ramdisk',
                                     'Short for `hdiutil detach /dev/disk1`'
                                     ' with some extra handling and default'
                                     ' location of %s.' % RAMDISK_PATH) 
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
    group_create_ramdisk.add_option('-a', '--disable-apparmor', 
                                    action='store_true', 
                                    dest='apparmor')
    # I group installing and starting the mysql db here out of convenience. 
    # TODO create an option for Solr here too.
    group_create_ramdisk.add_option('-m', '--with-mysql', 
                                    action='store_true',
                                    dest='with_mysql')

    parser.add_option_group(group_create_ramdisk)
    
    (options, args) = parser.parse_args()
    
    if options.create_ramdisk:
        create_ramdisk(calc_ramdisk_size(options.ramdisk_size), 
                       options.path_to_ramdisk)
        if options.with_mysql:
            if options.apparmor:
                disable_apparmor()
            install_db(options.path_to_ramdisk)
            start_db(options.path_to_ramdisk)
    elif options.kill_ramdisk:
        kill_ramdisk(options.path_to_ramdisk)

def is_linux():
    " Return true if os type is linux, and false otherwise. "
    # TODO: will this work in Windows? idk, but OS 10.6.4 in mac
    # is also posix, thus the need for the sys.platform check.
    return os.name == 'posix' and sys.platform != 'darwin'

def disable_apparmor():
    if is_linux():
        call(['sudo aa-complain mysqld'], shell=True)

def calc_ramdisk_size(num_megabytes):
    return num_megabytes * 1048576 / 512 # MB * MiB/KB; 


def create_ramdisk(ramdisk_size, disk_path=RAMDISK_PATH):
    print 'Creating ramdisk...'
    if is_linux():
        size_in_mb = ramdisk_size * 512 / 1048576
        # TODO: What if dir already exists? Destroy data?
        call(['sudo mkdir -p %s' % disk_path], shell=True)
        call(['sudo mount -t tmpfs -o size=%sM tmpfs %s' % (size_in_mb, disk_path)],
             shell=True)
    else:
        disk_path = Popen('hdiutil attach -nomount ram://%s' % ramdisk_size, 
                          stdout=PIPE, shell=True).communicate()[0]
        Popen('diskutil eraseVolume HFS+ ramdisk %s' % disk_path, stdout=PIPE,
              shell=True).communicate()
    print 'Done creating ramdisk: %s' % disk_path

def kill_ramdisk(path_to_ramdisk):
    # TODO make sure that MySQL isn't running first!
    if is_linux():
        # TODO:
        # make this use path_to_ramdisk.
        print "Unmounting ramdisk '%s'." % path_to_ramdisk
        # Nonzero return codes are bad. Wouldn't want to accidently remove rm anything
        # other than the ramdisk.
        if call(['sudo umount %s' % path_to_ramdisk], shell=True):
            raise Exception("Unmounting of ramdisk at '%s' failed." \
                            % path_to_ramdisk)

        print "Deleting ramdisk '%s'." % path_to_ramdisk
        call(['sudo rm -rf %s' % path_to_ramdisk], shell=True)
    else:
        print Popen(('hdiutil detach %s' % path_to_ramdisk), stdout=PIPE, 
                     shell=True).communicate()[0]

def install_db(path_to_ramdisk=None):
    # TODO support other dbs?
    print 'Installing new db...'
    if is_linux():
        call(['/usr/bin/mysql_install_db '
              '--user=mysql '
              '--basedir=/usr '
              '--datadir=%s' % path_to_ramdisk], shell=True)
        call(['sudo chmod 777 -R %s' % path_to_ramdisk], shell=True)
    else:
        p = Popen('/usr/local/mysql/scripts/mysql_install_db '
                  '--user=mysql '
                  '--basedir=/usr/local/mysql '
                  '--datadir=/Volumes/ramdisk', shell=True)
        p.communicate()
    print 'Done installing db.' 


def start_db(path_to_ramdisk=None):
    # TODO support other dbs?
    # TODO make it more configurable?
    print 'Starting db...'
    if is_linux():
        call(['sudo mysqld '
              '--basedir=/usr '
              '--datadir=%s '
              '--user=mysql '
              '--log-error=%s/mysql.ramdisk.err '
              '--pid-file=%s/mysql.ramdisk.pid '
              '--port=3308 '
              '--socket=/tmp/mysql.ramdisk.sock &' % ((path_to_ramdisk,) * 3)], 
              stdout=PIPE, shell=True)
        print "To log into mysql use: 'msyql --socket=/tmp/mysql.ramdisk.sock [OPTIONS]'"
    else:
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
