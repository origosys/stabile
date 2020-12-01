#!/bin/sh

echo "SUBSYSTEM==\"net\", ACTION==\"add\", DRIVERS==\"?*\", ATTR{address}==\"`ifconfig eth0 | grep -oh '\w\w:\w\w:\w\w:\w\w:\w\w:\w\w'`\", ATTR{dev_id}==\"0x0\", ATTR{type}==\"1\", KERNEL==\"eth*\", NAME=\"eth0\"" > /etc/udev/rules.d/70-persistent-net.rules
