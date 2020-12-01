#!/usr/bin/perl

sub tests {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    if ($action eq 'form') {
# Generate and return the HTML form for this tab
        my $form = <<END
<div class="tab-pane" id="tests">
<span class="dropdown">
    Select test:
    <button class="btn btn-primary dropdown-toggle dropdown" data-toggle="dropdown" id="run_test">Run test<span class="caret"></span></button>
    <span class="dropdown-arrow dropdown-arrow-inverse"></span>
    <ul class="dropdown-menu dropdown-inverse">
        <li>
            <a href="#" onclick="runTest('iops'); return false;">IOPS</a>
        </li>
        <li>
            <a href="#" onclick="runTest('io'); return false;">I/O</a>
        </li>
        <li>
            <a href="#" onclick="runTest('iopsdirect'); return false;">IOPS direct</a>
        </li>
        <li>
            <a href="#" onclick="runTest('iodirect'); return false;">I/O direct</a>
        </li>
        <li>
            <a href="#" onclick="runTest('dd'); return false;">Disk</a>
        </li>
        <li>
            <a href="#" onclick="runTest('ddnfs'); return false;">NFS</a>
        </li>
        <li>
            <a href="#" onclick="runTest('cpu'); return false;">CPU</a>
        </li>
        <li>
            <a href="#" onclick="runTest('cpu5'); return false;">CPU 5 threads</a>
        </li>
        <li>
            <a href="#" onclick="runTest('memory'); return false;">Memory</a>
        </li>
        <li id="net_test">
            <a href="#" onclick="runTest('network'); return false;">Network</a>
        </li>
        <li>
            <a href="#" onclick="runTest('netgw'); return false;">Network gateway</a>
        </li>
    </ul>
</span>
<span id="wait_test">
<div class="well" style="font-size:12px; margin-top:10px;">
IOPS: iozone -a -s 4096 -r 32 -O -i0 -i1 -i2<br>
I/O: iozone -a -s 4096 -r 32 -i0 -i1 -i2<br>
IOPS direct: iozone -I -a -s 4096 -r 32 -O -i0 -i1 -i2<br>
I/O direct: iozone -I -a -s 4096 -r 32 -i0 -i1 -i2<br>
Disk: dd bs=1M count=64 if=/dev/zero of=/tmp/test conv=fdatasync<br>
NFS: dd bs=1M count=64 if=/dev/zero of=/mnt/fuel/poolX/ddtest conv=fdatasync<br>
CPU: sysbench --test=cpu --cpu-max-prime=10000 run<br>
CPU 5 threads: sysbench --test=cpu --cpu-max-prime=10000 run --num-threads=5<br>
Memory: sysbench --test=memory --memory-total-size=4G run<br>
Network: netperf -f M -H \&lt;HOST\&gt; -l 10<br>
Network gateway: netperf -f M -H 10.0.0.1 -l 10<br>
</div>
</span>
<div id="myChart" width="700" height="240" style="margin-top:10px;"></div>
</div>
END
;
        return $form;

    } elsif ($action eq 'js') {
# Generate and return javascript the UI for this tab needs
        my $js = <<END
    function runTest(test) {
        console.log("running test", test);
        testnames = {'iops': 'IOPS', 'io': 'I/O', 'iopsdirect': 'IOPS direct', 'iodirect': 'I/O direct',
                     'dd': 'disk performance', 'cpu': 'CPU performance', 'cpu5': 'CPU5 performance',
                     'memory': 'memory performance', 'network': 'network performance', 'netgw': 'network gw performance',
                     'ddnfs': 'NFS performance'};
        \$( "#run_test" ).prop( "disabled", true );
        \$("#wait_test").html('<span class="label" style="color:gray;"><img src="images/loader.gif"> Waiting for results for ' + testnames[test] + '...</span>');
        \$.post( "index.cgi?action=runtest&tab=tests", { command: test })
        .done(function( data ) {
            getTestResults(data.servers, test);
        })
        .fail(function() {
            salert( "An error occurred :(" );
            \$( "#run_test" ).prop( "disabled", false );
        });
    }

    function getTestResults(servs, test) {
        \$.post( "index.cgi?action=gettestresults&tab=tests", {test: test, servers: JSON.stringify(servs)})
        .done(function( data ) {
            if (data) {
                \$("#run_test" ).prop( "disabled", false );
                \$("#wait_test").html('');
                var options = {
                    legendTemplate: '<span class="' + data.name + '-legend label"><span style="color:gray; vertical-align:middle;">' + data.name + ': </span><\% for (var i=0; i<datasets.length; i++){\%><span style="background-color:<\%=datasets[i].fillColor\%>" class="label"><\%=datasets[i].label\%></span> <\%}\%><span>',
                    barShowStroke: false
                };
                var canvas = document.createElement('canvas');
                canvas.id     = "myCanvas";
                canvas.width  = 700;
                canvas.height = 280;
                \$("#myChart").empty();
                \$("#myChart").append(canvas);
                var ctx = canvas.getContext("2d");
                var myBarChart = new Chart(ctx).Bar(data, options);
                \$("#wait_test").html(myBarChart.generateLegend());
            } else { // http probably timeout because of a long running command - try again
                if (testtries < 3) {
                    testtries++;
                    \$("#wait_test").html('<span class="label" style="color:gray;">Still waiting for test results...(' + testtries + ')</span>');
                    getTestResults(servs, test);
                } else {
                    cancelTestResults();
                }
            }
        })
        .fail(function() {
            cancelTestResults();
        });
    }

    function cancelTestResults() {
        testtries = 0;
        \$.get( "index.cgi?action=canceltestresults&tab=tests")
        .done(function( data ) {
            \$( "#run_test" ).prop( "disabled", false );
            \$("#wait_test").html('<span class="label" style="color:gray;">No results received :(</span>');
        });
    }
END
;
        return $js;

    } elsif ($action eq 'runtest') {
        my $res = "Content-type: application/json\n\n";
        $res .= run_test($in{command}, $internalip);
        return $res;

    } elsif ($action eq 'gettestresults') {
        my $res = "Content-type: application/json\n\n";
        my $servers = from_json($in{servers});
        my $test = $in{test};
        $res .= get_test_results($test, $servers);
        return $res;

    } elsif ($action eq 'canceltestresults') {
        my $res = "Content-type: text/html\n\n";
        $res .= cancel_test_results();
        return $res;
    }
}

sub run_test {
    my $test = shift;
    my $internalip = shift;
    my %tests = (
        "iops", "iozone -a -s 4096 -r 32 -O -i0 -i1 -i2",
        "io", "iozone -a -s 4096 -r 32 -i0 -i1 -i2",
        "iopsdirect", "iozone -I -a -s 2048 -r 32 -O -i0 -i1 -i2",
        "iodirect", "iozone -I -a -s 2048 -r 32 -i0 -i1 -i2",
        "dd", "dd bs=128M count=1 if=/dev/zero of=/tmp/ddtest conv=fdatasync oflag=direct",
        "ddnfs", "dd bs=1M count=64 if=/dev/zero of=/mnt/fuel/POOL/ddtest conv=fdatasync oflag=direct",
        "cpu", "sysbench --test=cpu --cpu-max-prime=10000 run",
        "cpu5", "sysbench --test=cpu --cpu-max-prime=10000 run --num-threads=5",
        "memory", "sysbench --test=memory --memory-total-size=4G run",
        "network", "netperf -f M -H HOST -l 10",
        "netgw", "netperf -f M -H 10.0.0.1 -l 10"
    );
    my $command = $tests{$test};
    foreign_require("cluster-shell", "cluster-shell-lib.pl");
    foreign_require("servers", "servers-lib.pl");
    my @servers = &foreign_call("servers", "list_servers");
    my @servs;

    # Make sure admin server is registered
    if (!@servers && $internalip) {
        save_webmin_server($internalip);
        @servers = &foreign_call("servers", "list_servers");
    }

    # Index actual servers so we don't run a command on a server that has been removed but is still in Webmin
    my $sservers_ref = list_simplestack_servers();
    @sservers = @$sservers_ref;
    my %sstatuses;
    foreach my $sserv (@sservers) {
        $sstatuses{$sserv->{internalip}} = $sserv->{status};
    }

    $p = 1;
    my $skip = 1;
    my $skiphost;
    my $nfsfork = 1;
    # Run the command for each storage pool and capture output
    if ($test eq 'ddnfs') {
        @servers = ();
        mountPools();
        my @mounts = split("\n", `cat /proc/mounts | grep fuel`);
        foreach my $mount (@mounts) {
            next unless ($mount =~ /\/mnt\/fuel\/(pool\d+)/);
            my $pool = $1;
            push @servers, {host=>$pool} if ($pool);
            push @servs, $pool;
        }
        $nfsfork = fork(); # Run nfs tests sequentially in separate thread
    }
    my $scommand;
    if ($test ne 'ddnfs' || !$nfsfork) {
        # Run one each one in parallel and display the output (unless doing nfs)
        foreach $s (@servers) {
            next unless ($sstatuses{$s->{'host'}} eq 'running' || $test eq 'ddnfs');
            push @servs, $s->{'host'};
            `/usr/bin/mkfifo -m666 "/tmp/OTEST-$s->{'host'}"` unless (-e "/tmp/OTEST-$s->{'host'}");
            $scommand = $command;
            my $hostip = $s->{'host'};
            if ($test eq 'network') { # Net test is between 2 hosts, so we skip every other
                if ($skip) {
                    $skip = 0;
                    $skippedhost = $hostip;
                    next;
                } else {
                    $skip = 1;
                    $scommand =~ s/HOST/$skippedhost/;
                }
            }
            my $forkid = 1;
            $forkid = fork() unless ($test eq 'ddnfs'); # Don't parallelize nfs test
            if ($test eq 'ddnfs' || !$forkid) {
                # Run the command in a subprocess
                close($rh);
                if ($test eq 'ddnfs') {
                    $scommand =~ s/POOL/$s->{'host'}/;
                    $hostip = $internalip;
                }
                &remote_foreign_require($hostip, "webmin", "webmin-lib.pl");
                if ($inst_error_msg) {
                    # Failed to contact host ..
                    exit;
                }
                # Run the command and capture output
                local $q = quotemeta($scommand);
                local $rv = &remote_eval($hostip, "webmin", "\$x=`($q) </dev/null 2>&1`");
                my $result = &serialise_variable([ 1, $rv ]);
                `/bin/echo "$result" > "/tmp/OTEST-$s->{'host'}"`;
                exit if (!$forkid); # Exit forked process
            }
            $p++;
        }
        exit if (!$nfsfork); # Exit thread running nfs tests
    }
    return qq|{"status": "OK: Ran command $scommand on | . (scalar @servs) . qq| servers", "servers": | . to_json(\@servs). "}";
}

sub get_test_results {
    # Get back all the results
    my $test = shift;
    my $servers_ref = shift;
    my @servers = @$servers_ref;
    my %tests;
    `pkill -f "/bin/cat < /tmp/OTEST"`; # Terminate previous blocking reads that still hang
    $p = 0;
    my $res;
    my %testnames = ('iops', 'IOPS', 'io', 'I/O (MB/s)', 'iopsdirect', 'IOPS direct', 'iodirect', 'I/O direct (MB/s)',
                     'dd', 'Disk performance (MB/s)','ddnfs', 'NFS performance (MB/s)', 'cpu', 'CPU (sec)', 'cpu5', 'CPU 5 threads (sec)',
                     'memory', 'Memory (MB/s)', 'network', 'Network (MB/s)', 'netgw', 'Network gateway (MB/s)');
    my $skip = 1;
    my @tservers;
    my $skippedhost;
    foreach $d (@servers) {
        if ($test eq 'network') {
            if ($skip) {
                $skip = 0;
                $skippedhost = $d;
                next;
            } else {
                $skip = 1;
            }
            push @tservers, "$d->$skippedhost";
        } elsif ($test eq 'netgw') {
            push @tservers, "$d->gw";
        }
        $line = `/bin/cat < /tmp/OTEST-$d`; # Read from pipe - this blocks, eventually http read will time out
        local $rv = &unserialise_variable($line);
        my $result;
        if (!$line) {
            # Comms error with subprocess
            $res .= qq|{"message": "$d failed to run the command for unknown reasons :(</span><br />"}, |;
        } elsif (!$rv->[0]) {
            # Error with remote server
            $res .= qq|{"message": "$d returned an error $rv->[1]"}, |;
        } else {
            # Done - show output
            $result = &html_escape($rv->[1]);
            if ($test eq 'iops' || $test eq 'iopsdirect' || $test eq 'io' || $test eq 'iodirect') {
                my @testkeys = ('KB','reclen', 'write',' rewrite', 'read', 'reread', 'random read', 'random write');
                for (split /^/, $result)  {
                    next unless $_;
                    # iozone
                    # KB, reclen, write, rewrite, (read), (reread), random read, random write
                    if ($_ =~ /(\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+)/) {
                        my @numbers = split /\s+/, $_;
                        my $n = 0;
                        foreach my $number (@numbers) {
                            if ($number) {
                                my $testkey = $testkeys[$n];
                                $n++;
                                unless ($testkey eq 'KB' || $testkey eq 'reclen') {
                                    unless ($tests{$testkey}){my @a1; $tests{$testkey} = \@a1;}
                                    if ($test eq 'io' || $test eq 'iodirect') {push $tests{$testkey}, int($number/1024);}
                                    else {push $tests{$testkey}, $number+0;}
                                }
                            }
                        }
                    }
                }
            } else {
                for (split /^/, $result)  {
                    next unless $_;
                    if ($test eq 'dd' || $test eq 'ddnfs') {
                        my $testkey = 'write';
                        unless ($tests{$testkey}){my @a1; $tests{$testkey} = \@a1;}
                        push $tests{$testkey}, $1 if ($_ =~ / s, (.+) \S+\/s/);
                        `echo "$_" >> /tmp/nfs.out`;
                    } elsif ($test eq 'cpu') {
                        my $testkey = 'max prime 10000';
                        unless ($tests{$testkey}){my @a1; $tests{$testkey} = \@a1;}
                        push $tests{$testkey}, $1 if ($_ =~ /total time:\s+ (\S+)s/);
                    } elsif ($test eq 'cpu5') {
                        my $testkey = 'max prime 10000';
                        unless ($tests{$testkey}){my @a1; $tests{$testkey} = \@a1;}
                        push $tests{$testkey}, $1 if ($_ =~ /total time:\s+ (\S+)s/);
                    } elsif ($test eq 'memory') {
                        my $testkey = 'r/w';
                        unless ($tests{$testkey}){my @a1; $tests{$testkey} = \@a1;}
                        push $tests{$testkey}, $1 if ($_ =~ /transferred \((\S+) MB\/sec\)/);
                    } elsif ($test eq 'network' || $test eq 'netgw') {
                        my $testkey = 'r/w';
                        unless ($tests{$testkey}){my @a1; $tests{$testkey} = \@a1;}
                        push $tests{$testkey}, $1 if ($_ =~ /\d+\s+\d+\s+\d+\s+\d+\.\d+\s+(\d+\.\d+)/);
                    }
                }
            }
        }
        $p++;
    }
    my @colors = (
        "#1ABC9C",
        "#16A085",
        "#2ECC71",
        "#27AE60",
        "#3498DB",
        "#2980B9",
        "#9B59B6",
        "#8E44AD",
        "#34495E",
        "#2C3E50",
        "#F1C40F",
        "#F39C12",
        "#E67E22",
        "#D35400",
        "#E74C3C",
        "#C0392B"
    );

    my @datasets;
    my $color = 2;
    foreach my $key (keys %tests) {
        next unless $tests{$key};
        my %dataset;
        $dataset{'label'} = $key;
        $dataset{'data'} = $tests{$key};
        $dataset{'fillColor'} = $colors[$color];
        $dataset{'strokeColor'} = $colors[$color+1];
#        $dataset{'fillColor'} = "rgba(220,220,220,0.5)";
#        $dataset{'strokeColor'} = "rgba(220,220,220,0.8)";
#        $dataset{'highlightFill'} = "rgba(220,220,220,0.75)";
#        $dataset{'highlightStroke'} = "rgba(220,220,220,1)";
        $dataset{'name'} = uc($test);
        push(@datasets, \%dataset);
        $color += 2;
    }
    my @labels = ($test eq 'network' || $test eq 'netgw')?@tservers:@servers;
    $res = '{"labels": ' . to_json(\@labels) . ', "datasets": ' . to_json(\@datasets) . ', "name": "' . $testnames{$test} . '"}';
    return $res;
}

sub cancel_test_results {
    `pkill -f "/bin/cat < /tmp/OTEST"`; # Terminate previous blocking reads that still hang
}

1;
