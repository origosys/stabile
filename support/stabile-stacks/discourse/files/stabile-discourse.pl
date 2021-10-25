#!/usr/bin/perl

use JSON;

my $dev = 'ens3';
$ip = $1 if (`ifconfig $dev` =~ /inet (\d+\.\d+\.\d+)\.\d+/);
$gw = "$ip.1" if ($ip);

my $appinfo_ref = get_appinfo();
if (!$appinfo_ref) {
    sleep 10;
    $appinfo_ref = get_appinfo();
}
if (!$appinfo_ref) {
    die "Unable to initialize Stabile API";
}
my %appinfo = %$appinfo_ref;
my $externalip = get_externalip();
my $dnsdomain =  $appinfo{dnsdomain};
my $dnssubdomain = $appinfo{'dnssubdomain'};
my $dom = ($dnsdomain && $dnssubdomain)?"$externalip.$dnssubdomain.$dnsdomain":"$externalip";

unless (-e '/etc/discourse.seeded') {
    # if (`grep ProxyPass /etc/apache2/sites-available/000-default.conf`) {
    #     print `perl -pi -e 's/.*ProxyPass.*\\n//g' /etc/apache2/sites-available/000-default.conf`;
    #     print `perl -pi -e 's/.*ProxyPass.*\\n//g' /etc/apache2/sites-available/default-ssl.conf`;
    # } else {
    #     print `perl -pi -e 's/(DocumentRoot .*)/\$1\\nProxyPass \\/ http:\\/\\/127.0.0.1:9292\\/\\nProxyPassReverse \\/ http:\\/\\/127.0.0.1:9292\\//g' /etc/apache2/sites-available/000-default.conf`;
    #     print `perl -pi -e 's/(DocumentRoot .*)/\$1\\nProxyPass \\/ http:\\/\\/127.0.0.1:9292\\/\\nProxyPassReverse \\/ http:\\/\\/127.0.0.1:9292\\//g' /etc/apache2/sites-available/default-ssl.conf`;
    # }

    print `echo "<h1 align=center><img width=48 height=48 src=https://www.stabile.io/images/apps/discourse_icon.png> Preparing Discourse...</h1><p align=center><img src=https://www.origo.io/images/39.svg></p><script>setTimeout(function(){location.reload() ; }, 8000);</script>" > /var/www/html/index.html`;
    print `sudo -u postgres psql -c "CREATE USER discourse;"`;
    print `sudo -u postgres psql -c "ALTER USER discourse WITH ENCRYPTED PASSWORD 'password';"`;
    print `sudo -u postgres psql -c "CREATE DATABASE discourse WITH OWNER discourse ENCODING 'UTF8' LC_CTYPE='en_US.UTF-8' LC_COLLATE='en_US.UTF-8' TEMPLATE=template0;"`;
#    print `sudo -u postgres psql -c "ALTER DATABASE discourse OWNER TO discourse;"`;
    print `sudo -u postgres psql -c "CREATE ROLE root WITH CREATEDB LOGIN CREATEROLE SUPERUSER;"`;
    print `sudo -u postgres psql discourse -c "CREATE EXTENSION hstore;"`;
    print `sudo -u postgres psql discourse -c "CREATE EXTENSION pg_trgm;"`;

    `perl -pi -e 's/hostname =.*/hostname = $dom/g' /var/discourse/config/discourse.conf`;
    `perl -pi -e 's/smtp_domain =.*/smtp_domain = $dom/g' /var/discourse/config/discourse.conf`;
    `perl -pi -e 's/myhostname =.*/myhostname = $dom/g' /var/discourse/config/discourse.conf`;
#    print `sudo -u postgres psql discourse -c "UPDATE site_settings SET value = 'noreply\@$dom' WHERE name = 'notification_email';"`;

    # https://github.com/lautis/uglifier/issues/127
    `perl -pi -e 's/config\.assets\.js_compressor = :uglifier/config.assets.js_compressor = Uglifier.new(:harmony => true)/' /var/discourse/config/environments/production.rb`;
    `perl -pi -e 's/Uglifier\.new.comments: :none,.*/Uglifier.new(comments: :none, :harmony => true,/' /var/discourse/lib/tasks/assets.rake`;
    `perl -pi -e 's/Uglifier\.new\.compile/Uglifier.new(:harmony => true).compile/' /var/discourse/lib/tasks/javascript.rake`;
    `echo "require 'uglifier'" >> /var/discourse/Gemfile`;

    print `cd /var/discourse ; RAILS_ENV=production bundle exec rake db:migrate >> /tmp/discourse.out 2>&1`;
    print `cd /var/discourse ; RAILS_ENV=production bundle exec rake assets:precompile >> /tmp/discourse.out 2>&1`;
    # We do it twice because, well, Rails...
    print `cd /var/discourse ; RAILS_ENV=production bundle exec rake assets:precompile >> /tmp/discourse.out 2>&1`;
    # print `cd /var/discourse ; RAILS_ENV=production bundle exec rake assets:precompile >> /tmp/discourse.out 2>&1`;

    my $me_json = `curl -k --silent https://$gw/stabile/users/me`;
    my $me_ref = from_json($me_json);
    my $email = $me_ref->[0]->{'email'};
    $email = $me_ref->{'usename'} if (!$email || !($email =~ /\@/) || $email eq '--');
    print "Adding user $email\n";
    my $randpass = `openssl rand -base64 24`;
    chomp $randpass;
    print `cd /var/discourse ; export RAILS_ENV=production; echo "$email\n$randpass\n$randpass\nY " | rake admin:create`;

    unless (`grep PassengerBase /etc/apache2/sites-available/default-ssl.conf`) {
        print `perl -pi -e 's/(DocumentRoot .*)/DocumentRoot \\/var\\/discourse\\/public\\nRailsBaseURI \\/\\nPassengerBaseURI \\/\\nPassengerResolveSymlinksInDocumentRoot on\\nPassengerAppRoot \\/var\\/discourse\\n/g' /etc/apache2/sites-available/default-ssl.conf`;
    #    print `perl -pi -e 's/(DocumentRoot .*)/DocumentRoot \\/var\\/discourse\\/public\\nRailsBaseURI \\/\\nPassengerBaseURI \\/\\nPassengerResolveSymlinksInDocumentRoot on\\nPassengerAppRoot \\/var\\/discourse\\n/g' /etc/apache2/sites-available/000-default.conf`;
    }

    `perl -pi -e 's/PrivateTmp=true/PrivateTemp=false/' /lib/systemd/system/apache2.service`;
    `systemctl daemon-reload`;
    `systemctl restart postfix`;
    `systemctl restart apache2`;
    `touch /etc/discourse.seeded`;
}
`chown -R www-data:www-data /var/www`;
`chown -R www-data:www-data /var/discourse`;
system("cd /var/discourse ; RAILS_ENV=production bundle exec sidekiq -C config/sidekiq.yml &");

sub get_internalip {
    my $internalip;
    if (!(-e "/tmp/internalip") && !(-e "/etc/stabile/internalip")) {
        $internalip = $1 if (`curl -sk https://$gw/stabile/networks/this` =~ /"internalip" : "(.+)",/);
        chomp $internalip;
        `echo "$internalip" > /tmp/internalip` if ($internalip);
        `mkdir /etc/stabile` unless (-e '/etc/stabile');
        `echo "$internalip" > /etc/stabile/internalip` if ($internalip);
    } else {
        $internalip = `cat /tmp/internalip` if (-e "/tmp/internalip");
        $internalip = `cat /etc/stabile/internalip` if (-e "/etc/stabile/internalip");
        chomp $internalip;
    }
    return $internalip;
}

sub get_externalip {
    my $externalip;
    if (!(-e "/tmp/externalip")) {
        $externalip = $1 if (`curl -sk https://$gw/stabile/networks/this` =~ /"externalip" : "(.+)",/);
        chomp $externalip;
        if ($externalip eq '--') {
            # Assume we have ens4 up with an external IP address
            $externalip = `ifconfig ens4 | grep -o 'inet addr:\\\S*' | sed -n -e 's/^inet addr://p'`;
            chomp $externalip;
        }
        `echo "$externalip" > /tmp/externalip` if ($externalip);
    } else {
        $externalip = `cat /tmp/externalip` if (-e "/tmp/externalip");
        chomp $externalip;
    }
    return $externalip;
}

sub get_appid {
    my $appid;
    if (!(-e "/tmp/appid")) {
        $appid = $1 if (`curl -sk https://$gw/stabile/servers?action=getappid` =~ /appid: (.+)/);
        chomp $appid;
        `echo "$appid" > /tmp/appid` if ($appid);
    } else {
        $appid = `cat /tmp/appid` if (-e "/tmp/appid");
        chomp $appid;
    }
    return $appid;
}

sub get_appinfo {
    my $appinfo;
    $appinfo = `curl -sk https://$gw/stabile/servers?action=getappinfo`;
    if ($appinfo =~ /^\{/) {
        my $json_hash_ref = from_json($appinfo);
        return $json_hash_ref;
    } else {
        return '';
    }
}
