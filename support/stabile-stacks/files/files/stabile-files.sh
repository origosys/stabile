#!/bin/bash

if  [ !  -f /mnt/data/users ]
  then
    mkdir /mnt/data/users
    mkdir /mnt/data/shared
    mkdir /mnt/data/groups
fi
if  [ !  -f /mnt/data/users/administrator ] # First run - set administrator password
  then
    passwd=`openssl rand -base64 12`
    echo "$passwd" > /tmp/administrator.pass
    mkdir /mnt/data/users/administrator
    echo "$passwd
$passwd" | /usr/bin/smbpasswd -s administrator 2>&1
    systemctl restart samba-ad-dc
    perl -pi -e "s/TKTAuthSecret .*/TKTAuthSecret $passwd/" /etc/apache2/conf-available/auth_tkt.conf
    systemctl restart apache2
fi
chmod 777 /mnt/data/shared /mnt/data/users /mnt/data/groups

if  pgrep -x "samba" >/dev/null
then
  echo "samba is running"
else
  echo "Starting samba"
  samba
fi
