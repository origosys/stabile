#!/usr/bin/perl

sub files {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    if ($action eq 'form') {
# Generate and return the HTML form for this tab
        my $elfinderlinks;
        my $suuid;

        my $sservers_ref = list_simplestack_networks();
        my @sservers = @$sservers_ref;

        foreach my $sserv (@sservers) {
            my $sip = $sserv->{internalip};
            my $uuid = $sserv->{uuid};
            $suuid = $uuid if ($sip eq $internalip);
            $elfinderlinks .= qq|<li><a href="#" onclick='openElfinder("$sip", "$uuid");'>Files on $sip</a></li>|;
        }

        my %activepools = mountPools();
        foreach my $p (values %activepools) {
            my $sid = $p->{id};
            $elfinderlinks .= qq|<li><a href="#" onclick='openElfinder("$p->{pool}", "$suuid", "$p->{name}");'>Files on $p->{name} ($p->{pool})</a></li>\n|;
        }

        my $form = <<END
<div class="tab-pane" id="files">
    <div>
        Here you can browse, download and upload files on your servers and shared storagepools you have access to.
    </div>
    <span class="dropdown" id="browse_files">
        Browse:
        <button class="btn btn-primary dropdown-toggle dropdown" data-toggle="dropdown">Location<span class="caret"></span></button>
        <span class="dropdown-arrow dropdown-arrow-inverse"></span>
        <ul class="dropdown-menu dropdown-inverse">
            $elfinderlinks
        </ul>
    </span>
</div>
END
;
        return $form;

    } elsif ($action eq 'js') {
# Generate and return javascript the UI for this tab needs
        my $js = <<END
    function openElfinder(sip, uuid, nfsname) {
        var url = "/stabile/pipe/http://" + uuid + ":10000/stabile/index.cgi?tab=files&action=elfinder&storageid=" + sip;
        if (nfsname) url += "&nfsname=" + nfsname;
        window.open(url, sip);
        return false;
    }
END
;
        return $js;

    } elsif ($action eq 'upgrade') {
        my $res;
        my $dumploc = $in{targetdir};
        my $srcloc = "/usr/share/webmin/origo/files";
        if (-d $srcloc && -d $dumploc) {
            `rm -r $dumploc/files`;
            `cp -r $srcloc $dumploc`;
        }

        my $srcsize = `du -bs $srcloc`;
        $srcsize = $1 if ($srcsize =~ /(\d+)/);
        my $dumpsize = `du -bs $dumploc/files`;
        $dumpsize = $1 if ($dumpsize =~ /(\d+)/);
        if ($srcsize == $dumpsize) {
            $res = "OK: $srcsize bytes dumped successfully to $dumploc";
        } else {
            $res = "There was a problem dumping data to $dumploc ($srcsize <> $dumpsize)!";
        }
        return $res;

# This is called from origo-ubuntu.pl when rebooting and with status "upgrading"
    } elsif ($action eq 'restore') {
        my $srcloc = $in{sourcedir};
        my $dumploc = "/usr/share/webmin/origo/";
        `mkdir -p $dumploc` unless (-e $dumploc);
        my $res;
        if (-e "$srcloc/files") {
            $res = "OK: ";
            $res .= `cp -r $srcloc/files $dumploc`;
            chomp $res;
        }
        $res .= "Not copying $srcloc/* -> $dumploc" unless ($res);
        return $res;

    } elsif ($action eq 'elfinder') {
        my $url = 'elfinder/php/connector.cgi';
        my $title = "Browse files on $in{storageid}";
        if ($in{nfsname}) {
            $url .= "?nfs=$in{storageid}";
            $title = "Browse files on $in{nfsname} ($in{storageid})";
        }
        my $elfinder = <<END
Content-type: text/html

<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <title>$title</title>
        <link rel="stylesheet" type="text/css" href="https://ajax.googleapis.com/ajax/libs/jqueryui/1.8.23/themes/smoothness/jquery-ui.css">
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.8.0/jquery.min.js"></script>
        <script src="https://ajax.googleapis.com/ajax/libs/jqueryui/1.8.23/jquery-ui.min.js"></script>
        <link rel="stylesheet" type="text/css" href="elfinder/css/elfinder.full.css">
        <link rel="stylesheet" type="text/css" href="elfinder/css/theme.css">
        <script>
            IRIGO = {tktuser: "$user"};
        </script>
        <script src="elfinder/js/elfinder.full.js"></script>
        <script type="text/javascript" charset="utf-8">
            // Documentation for client options:
            // https://github.com/Studio-42/elFinder/wiki/Client-configuration-options
            \$(document).ready(function() {
                \$('#elfinder').elfinder({
                    url : "$url",  // connector URL (REQUIRED)
                    height: '600',
                    commands: ['open', 'reload', 'home', 'up', 'back', 'forward', 'getfile', 'quicklook',
                                'download', 'rm', 'duplicate', 'rename', 'mkdir', 'mkfile', 'upload', 'copy',
                                'cut', 'paste', 'edit', 'extract', 'archive', 'search', 'info', 'view', 'help', 'resize', 'sort']
                });
            });
        </script>
    </head>
    <body>
        <div id="elfinder"></div>
    </body>
</html>
END
;
        return $elfinder;
    }
}

1;
