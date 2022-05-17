#!/usr/bin/perl

sub mongotests {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    if ($action eq 'form') {
# Generate and return the HTML form for this tab
        my $form = <<END
<div class="tab-pane container" id="mongotests">
<span class="dropdown">
    Number of DB operations to run:
    <button class="btn btn-primary dropdown-toggle dropdown" data-toggle="dropdown" id="run_test">select<span class="caret"></span></button>
    <span class="dropdown-arrow dropdown-arrow-inverse"></span>
    <ul class="dropdown-menu dropdown-inverse">
        <li>
            <a href="#" onclick="\$('#myChart').empty(); \$('#wait_test').html(waittxt); return false;">Show info</a>
        </li>
        <li>
            <a href="#" onclick="runTest('100'); return false;">100</a>
        </li>
        <li>
            <a href="#" onclick="runTest('1000'); return false;">1000</a>
        </li>
        <li>
            <a href="#" onclick="runTest('10000'); return false;">10000</a>
        </li>
        <li>
            <a href="#" onclick="runTest('100000'); return false;">100000</a>
        </li>
    </ul>
</span>
<span id="wait_test">
</span>
<div class="chart-container" style="margin-top:10px; max-width:800px; max-height: 400px;">
<div id="myChart"></div>
</div>
</div>
END
;
        return $form;

    } elsif ($action eq 'js') {
# Generate and return javascript the UI for this tab needs
        my $js = <<END

    var waittxt = '<div class="well" style="font-size:16px; margin-top:20px; max-width:800px;">\\
        This test will try to insert, update, read and delete the number of test documents you select into a test database, that is created for the purpose.<br>\\
        The test database is named "testDB", so please make sure that you do not use a database with this name, before beginning this test, as it will be dropped before testing!\\
</div>'

    function runTest(test) {
        console.log("running test", test);
        testnames = {'100': '100', '1000': '1000', '10000': '10000', '100000': '100000'};
        \$( "#run_test" ).prop( "disabled", true );
        \$("#wait_test").html('<span class="label" style="color:gray;"><img src="images/loader.gif"> Waiting for results for 4 x ' + testnames[test] + ' DB operations...</span>');
        \$.post( "index.cgi?action=runtest&tab=mongotests", { command: test })
        .done(function( data ) {
            getTestResults(test);
        })
        .fail(function() {
            salert( "An error occurred :(" );
            \$( "#run_test" ).prop( "disabled", false );
        });
    }

    function getTestResults(test) {
        \$.post( "index.cgi?action=gettestresults&tab=mongotests", {test: test})
        .done(function( data ) {
            if (data) {
                \$("#run_test" ).prop( "disabled", false );
                \$("#wait_test").html('<span class="label" style="color:gray;">Ran 4 x ' + data.name + ' DB operations. Results are shown in seconds.</span>');
                var options = {
                    barShowStroke: true,
                    responsive: true,
                    maintainAspectRatio: false
                };
                var canvas = document.createElement('canvas');
                canvas.id     = "myCanvas";
                \$("#myChart").empty();
                \$("#myChart").append(canvas);
                var ctx = canvas.getContext("2d");
                ctx.canvas.width  = 800;
                ctx.canvas.height = 400;
                var myBarChart = new Chart(ctx, {type: 'bar', data: data, options: options});
            } else { // http probably timeout because of a long running command - try again
                if (testtries < 20) {
                    testtries++;
                    \$("#wait_test").html('<span class="label" style="color:gray;"><img src="images/loader.gif"> Still waiting for test results...(' + testtries + ')</span>');
                    getTestResults(test);
                } else {
                    cancelTestResults();
                }
            }
        })
        .fail(function() {
                if (testtries < 20) {
                    testtries++;
                    \$("#wait_test").html('<span class="label" style="color:gray;"><img src="images/loader.gif"> Still waiting for test results...(' + testtries + ')</span>');
                    getTestResults(test);
                } else {
                    cancelTestResults();
                }
        });
    }

    function cancelTestResults() {
        testtries = 0;
        \$.get( "index.cgi?action=canceltestresults&tab=mongotests")
        .done(function( data ) {
            \$( "#run_test" ).prop( "disabled", false );
            \$("#wait_test").html('<span class="label" style="color:gray;">No results received :(</span>');
        });
    }

    \$(document).ready(function () {
        \$.getScript("https://cdn.jsdelivr.net/npm/chart.js", function(data, textStatus, jqxhr) {
            console.log("Loaded Chart.js", textStatus);
        });
        \$("#wait_test").html(waittxt);
    });

END
;
        return $js;

    } elsif ($action eq 'runtest') {
        my $res = "Content-type: application/json\n\n";
        $res .= run_test($in{command}, $internalip);
        return $res;

    } elsif ($action eq 'gettestresults') {
        my $res = "Content-type: application/json\n\n";
        my $test = $in{test};
        $res .= get_test_results($test);
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
        "100", "100",
        "1000", "1000",
        "10000", "10000",
        "100000", "100000"
    );
    my $command = $tests{$test};
    `/usr/bin/mkfifo -m666 "/tmp/OTEST-0"` unless (-e "/tmp/OTEST-0");
    my $forkid = 1;
    $forkid = fork();
    if (!$forkid) {
        # Run the command in a subprocess
        # Run the command and capture output
        my $json = `/usr/share/webmin/stabile/tabs/mongotests/mongotester.pl -i $command -j`;
        my $res = from_json($json);
        my $result = &serialise_variable($res);
        #my @rv = split(" ", $res);
        #my $result = &serialise_variable(\@rv);
        `/bin/echo "$result" > "/tmp/OTEST-0"`;
        exit; # Exit forked process
    }
    return qq|{"status": "OK: Ran command $command"}|;
}

sub get_test_results {
    # Get back all the results
    my $test = shift;
    my %tests;
    `pkill -f "/bin/cat < /tmp/OTEST"`; # Terminate previous blocking reads that still hang
    $p = 0;
    my $res;

    $line = `/bin/cat < /tmp/OTEST-0`; # Read from pipe - this blocks, eventually http read will time out
    # local $rv = &unserialise_variable($line);
    my $rv = &unserialise_variable($line);
    my %results = %{$rv};
    my $result;
    if (!$line) {
        # Comms error with subprocess
        $res .= qq|{"message": "Failed to run the command for unknown reasons :(</span><br />"}, |;
    } elsif (!$rv->{insert}) {
        $res .= qq|{"message": "Test returned an error $rv"}, |;
    } else {
        # Done - show output
#        $result = &html_escape($rv->[0]);
        my @testkeys = ('insert','update', 'read',' delete');
        my $n = 0;
        foreach my $testkey (keys %results) {
            unless ($tests{$testkey}) {my @a1; $tests{$testkey} = \@a1;}
            my @b1 = @{$tests{$testkey}}; push @b1, $results{$testkey}+0;
            $tests{$testkey} = \@b1;
        }
        # foreach my $number (@{$rv}) {
        #     my $testkey = $testkeys[$n];
        #     $n++;
        #     unless ($tests{$testkey}) {my @a1; $tests{$testkey} = \@a1;}
        #     my @b1 = @{$tests{$testkey}}; push @b1, $number+0;
        #     $tests{$testkey} = \@b1;
        # }
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
    foreach my $key (sort keys %tests) {
        next unless $tests{$key};
        my %dataset;
        $dataset{'label'} = $key;
        $dataset{'data'} = $tests{$key};
        $dataset{'backgroundColor'} = $colors[$color];
        $dataset{'borderColor'} = $colors[$color+1];
        $dataset{'name'} = uc($test);
        push(@datasets, \%dataset);
        $color += 2;
    }
    my @labels = ("localhost");
    $res = '{"labels": ' . to_json(\@labels) . ', "datasets": ' . to_json(\@datasets) . ', "name": "' . $test . '"}';
    return $res;
}

sub cancel_test_results {
    `pkill -f "/bin/cat < /tmp/OTEST"`; # Terminate previous blocking reads that still hang
}

1;
