package main;

use strict;                          #
use warnings;                        #
use IO::Select;

sub RTL433_Read($);                  #
sub RTL433_Ready($);                 #

my $Readpart = "";   # Hilfsvariable für auslesen des Puffers. Warum muss die hier stehen? 
					 # bei Definition in der Read-Funktion funktioniert das Modul nicht.
my $RTL433pid;
my $RTL433select;
my $RTL433interval=60;

#########################################################################

sub RTL433_Initialize($)
{
	my ($hash) = @_;

	$hash->{ReadFn}  = "RTL433_Read";
	$hash->{ReadyFn} = "RTL433_Ready";
	$hash->{DefFn}   = "RTL433_Define";
	$hash->{UndefFn} = "RTL433_Undef";
	$hash->{AttrList} =
	  "do_not_notify:1,0 loglevel:0,1,2,3,4,5,6 " . $readingFnAttributes;
}

#########################################################################									#

sub RTL433_Define($$)
{
	my ( $hash, $def ) = @_;
	my @a = split( "[ \t][ \t]*", $def );

	return "wrong syntax: define <name> RTL433"
	  if ( @a != 2 );

	my $name = $a[0];


#	$RTL433pid = open(KID_TO_READ, "rtl_433 -R 20 -C si -q -F csv 2>/dev/null & |");
#	if(!defined($RTL433pid)) {
#		$hash->{STATE} = "Could not start";
#		$RTL433select = undef;
#		return "Could not start binary rtl_433";
#	}
#	if ($RTL433pid) {
#		$hash->{STATE} = "Running";
#		$RTL433select  = IO::Select->new();
#		$RTL433select->add(\*KID_TO_READ);
#	}
	$RTL433pid = open(KID_TO_READ, "-|");
	if(!defined($RTL433pid)) {
		$hash->{STATE} = "Could not start";
		$RTL433select = undef;
		return "Could not start binary rtl_433";
	}
	if ($RTL433pid) {
		$hash->{STATE} = "Running";
		$RTL433select  = IO::Select->new();
		$RTL433select->add(\*KID_TO_READ);
	} else {
		# Start die forked program
		exec("rtl_433 -R 20 -C si -q -F csv");
	}

	#InternalTimer(gettimeofday()+10, "RTL433_Read", $hash, 0);
	RTL433_Read($hash);
	return undef;
}

#########################################################################

sub                   
  RTL433_Undef($$)    
{                   
	my ( $hash, $arg ) = @_;    
	system("kill $RTL433pid");
	RemoveInternalTimer($hash); 
	return undef;               
}    

#########################################################################

# called from the global loop, when the select for hash->{FD} reports data
sub RTL433_Read($)
{
	my ($hash) = @_;
	my $name = $hash->{NAME};

	my @ready;
	if($RTL433select and @ready=$RTL433select->can_read(0))
        {
		my $tmp;
		my $len;
		if($len = sysread($ready[0], $tmp, 16*1024)) {
			$Readpart .= "$tmp";
		}
		#if(eof($ready[0]) ) {
		if( $len == undef ) {
			$RTL433select = undef;
			$hash->{STATE} = "Crashed";
			return;
		} 
		
	}
	readingsBeginUpdate($hash);
	my $substrlen = 0;
	while($Readpart =~ m/(.*)\n/g) {
		my $line = $1;
		$substrlen += length($line)+1;
		chomp $line;
		Log3 $name, 4, "line: $line\n" ;
		my ($time,$device,$channel,$temperature_F,$temperature_C,$humidity,$battery ) = (split (",", $line));
		readingsBulkUpdate( $hash, "$channel-$device-temp", $temperature_C );
		readingsBulkUpdate( $hash, "$channel-$device-humi", $humidity );
		readingsBulkUpdate( $hash, "$channel-$device-batt", $battery );
	}	
	$Readpart = substr($Readpart, $substrlen);
	###### in die READINGS schreiben
	readingsBulkUpdate( $hash, "RTL433pid", $RTL433pid );
	readingsBulkUpdate( $hash, "RTL433select", $RTL433select != undef  );
	readingsBulkUpdate( $hash, "ReadpartLength", length ($Readpart)  );
	readingsEndUpdate( $hash, 1 );

	if(length ($Readpart) > 16*1024) {
		$Readpart = "";
	}
	InternalTimer(gettimeofday()+$RTL433interval, "RTL433_Read", $hash, 0);
}

#########################################################################

sub RTL433_Ready($)
{
	my ($hash) = @_;
	return (1>0);
}

1;

=pod
=begin html

<a name="RTL433"></a>
<h3>RTL433</h3>
<ul>
  This FHEM module is able to run the rtl_433 command.<br>
  <br><br>

  <a name="RTL433define"></a>
  <b>Define</b>
  <ul>
    <code>define &lt;name&gt; RTL433</code><br>
    <br><br>
    Example:
    <ul>
      <code>define myRtl433 RTL433</code><br>
    </ul>
  </ul>
  <br>

=end html
=cut

