#!/usr/bin/perl

use JSON;

my $dev = 'eth0';
$dev = 'ens3';
my $ipstart = $1 if (`ifconfig $dev` =~ /inet (\d+\.\d+\.\d+)\.\d+/);
my $gw = "$ipstart.1" if ($ipstart);
my $u = `curl -k --silent https://$gw/stabile/users/me`;
my $u_obj = from_json($u);
my $email = $u_obj->[0]->{'email'} || $u_obj->[0]->{'username'};
my $externalip = `cat /tmp/externalip`;
chomp $externalip;
# my $currenttime = `date --rfc-3339=seconds`;
# chomp $currenttime;
#$currenttime =~ s/\+00\:00//;
my $currenttime = time();

my $dnsdomain_json = `curl -k https://$gw/stabile/networks?action=getdnsdomain`;
my $dom_obj = from_json ($dnsdomain_json);
my $dnsdomain =  $dom_obj->{'domain'};
my $dnssubdomain = $dom_obj->{'subdomain'};
$dnsdomain = '' unless ($dnsdomain =~  /\S+\.\S+$/ || $dnsdomain =~  /\S+\.\S+\.\S+$/);
my $dom = ($dnsdomain)?"$externalip.$dnssubdomain.$dnsdomain":$externalip;

unless (-e '/etc/matomo.seeded') {
    print `perl -pi -e 's/ServerAdmin.*/ServerAdmin email\\\n\\\tRedirectMatch \\\^\\\/\\\$ \\\/matomo/' /etc/apache2/sites-available/default-ssl.conf`;
    print `perl -pi -e 's/ServerAdmin.*/ServerAdmin email\\\n\\\tRedirectMatch \\\^\\\/\\\$ \\\/matomo/' /etc/apache2/sites-available/000-default.conf`;
    print `chmod o+rX /var/log/apache2`;
    print `/etc/init.d/apache2 restart`;
    `touch /etc/matomo.seeded`;
}

if (system(qq|mysql -e "use matomo;" 2>/dev/null|))  {
    print `mysql -e "create database matomo;"`;
    print `mysql -e "CREATE USER matomo\@localhost;"`;
    print `mysql -e "GRANT ALL PRIVILEGES ON matomo.* TO matomo\@localhost;"`;
    print `mysql -e "FLUSH PRIVILEGES;"`;
    print `perl -pi -e 's/localhost/$dom/g' /usr/share/webmin/stabile/tabs/matomo/matomo.sql`;
    print `perl -pi -e 's/currenttime/$currenttime/' /usr/share/webmin/stabile/tabs/matomo/matomo.sql`;
    print `mysql matomo < /usr/share/webmin/stabile/tabs/matomo/matomo.sql`;
    print `mysql matomo -e "UPDATE matomo_user SET email = '$email' WHERE login = 'stabile' AND superuser_access = 1;"`;
    print `perl -pi -e 's/myhost/$dom/' /var/www/matomo/config/config.ini.php`;
}

print `su www-data -s /bin/bash -c "/usr/bin/php /var/www/matomo/console core:archive --url=https://$dom/matomo/"`;
print `chmod o+r /var/log/apache2/access.log`;
# Now wait for log file to be modified before importing entries
print `inotifywait -e modify /var/log/apache2/access.log;`;
print `sudo -u www-data python3 /var/www/matomo/misc/log-analytics/import_logs.py --url=https://$dom/matomo --idsite=1 --recorders=4 --enable-http-errors --enable-http-redirects --enable-static --enable-bots /var/log/apache2/access.log`;
