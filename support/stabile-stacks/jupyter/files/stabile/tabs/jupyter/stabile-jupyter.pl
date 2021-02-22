#!/usr/bin/perl

use JSON;

my $hostname = `hostname`;
my $email = `curl -k --silent https://10.0.0.1/stabile/users/me/username`;
my $internalip = `hostname -I | xargs echo -n`;
my $externalip = `cat /tmp/externalip`;
chomp $externalip;
my $currenttime = `date --rfc-3339=seconds`;
chomp $currenttime;
$currenttime =~ s/\+00\:00//;

my $appinfo = `curl -ks "https://10.0.0.1/stabile/servers?action=getappinfo"`;
my $info_ref = from_json($appinfo);
my $dnsdomain = $info_ref->{dnsdomain};

unless (-e '/etc/jupyter.seeded') {
    print `perl -pi -e 's/ubuntu-xenial/jupyter/g' /etc/hosts`;
    `touch /etc/jupyter.seeded`;
}
#my $sslconf = "/etc/apache2/sites-available/000-default-le-ssl.conf";
#print `perl -pi -e 's/.*\\\/VirtualHost.*/\\\tProxyPass \\\/ http:\\\/\\\/127.0.0.1:8888\\\/ \\\n\\\tProxyPassReverse \\\/ http:\\\/\\\/127.0.0.1:8888\\\/\\\n<\\\/VirtualHost>/' $sslconf` unless ( !(-e $sslconf) || `grep ProxyPass $sslconf`);

print `perl -pi -e "s/.*c\\.NotebookApp\\.port =.*/c.NotebookApp.port = 8889/" /home/stabile/.jupyter/jupyter_notebook_config.py`;
print `perl -pi -e "s/.*c\\.NotebookApp\\.ip =.*/c.NotebookApp.ip = '$internalip'/" /home/stabile/.jupyter/jupyter_notebook_config.py`;
my $certfile = "/home/stabile/.jupyter/ssl-cert-snakeoil.pem";
my $keyfile = "/home/stabile/.jupyter/ssl-cert-snakeoil.key";

if (-e "/etc/letsencrypt/live/$externalip.$dnsdomain") {
    print `cp -L /etc/letsencrypt/live/$externalip.$dnsdomain/* /home/stabile/.jupyter/`;
    $certfile = "/home/stabile/.jupyter/cert.pem";
    $keyfile = "/home/stabile/.jupyter/privkey.pem";
} else {
    print `cp /etc/ssl/certs/ssl-cert-snakeoil.pem /home/stabile/.jupyter`;
    print `cp /etc/ssl/private/ssl-cert-snakeoil.key /home/stabile/.jupyter`;
}
`chown stabile:stabile /home/stabile/.jupyter/*`;

print `su stabile -c "/home/stabile/anaconda/bin/jupyter notebook --config=/home/stabile/.jupyter/jupyter_notebook_config.py --notebook-dir=/home/stabile/notebooks --certfile=$certfile --keyfile=$keyfile"`;
