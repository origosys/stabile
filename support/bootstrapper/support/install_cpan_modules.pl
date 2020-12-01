#!/usr/bin/perl

my $perlmodules_file = '/usr/share/stabile/cpan_modules';
open(my $pm_fh, '<', $perlmodules_file) or die $!;
my @cpan_modules = <$pm_fh>;
close($pm_fh);

chomp(@cpan_modules);

foreach my $pack(@cpan_modules) {
	my $cmd = "PERL_MM_USE_DEFAULT=1 perl -MCPAN -e 'install $pack'";
	print $cmd . "\n";

	# Run command and continue if successfull, else return error.
	my $ret = system($cmd);

	if($ret != 0 ) {
		print "Got an error: $ret\n";
	}
}
