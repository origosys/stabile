#!/bin/bash

if  [ !  -f ./samba/users ]
  then
  mkdir -p ./samba/users/administrator ./samba/groups ./samba/shared
  chmod -R 777 ./samba/users ./samba/groups ./samba/shared
fi
