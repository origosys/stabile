#!/bin/bash

## Written by Kasper Eenberg on Sept. 30 - 2011 on behalf of Cabo Communications ##

DESTDIR="sql"
DATABASE='steamregister'
TABLES=`mysql -u root -D $DATABASE -e 'show tables;' -ss`

if [ ! -e $DESTDIR ]
	then
	/bin/mkdir $DESTDIR
fi

/usr/bin/mysqldump --skip-add-drop-table -u root $DATABASE documentation > $DESTDIR/documentation.sqldump

for i in $TABLES; do
	`mysqldump -d --skip-add-drop-table -u root $DATABASE $i > $DESTDIR/$i.sql`
done
