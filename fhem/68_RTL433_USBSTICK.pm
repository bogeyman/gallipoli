package main;

use strict;                          #
use warnings;                        #
use IO::Select;

sub RTL433_USBSTICK_Read($);                  #
sub RTL433_USBSTICK_Ready($);                 #

my $Readpart = "";   # Hilfsvariable für auslesen des Puffers. Warum muss die hier stehen? 
					 # bei Definition in der Read-Funktion funktioniert das Modul nicht.
my $RTL433_USBSTICK_pid;
my $RTL433_USBSTICK_select;
my $RTL433_USBSTICK_interval=60;

#########################################################################

sub RTL433_USBSTICK_Initialize($)
{
	my ($hash) = @_;

	$hash->{ReadFn}  = "RTL433_USBSTICK_Read";
	$hash->{ReadyFn} = "RTL433_USBSTICK_Ready";
	$hash->{DefFn}   = "RTL433_USBSTICK_Define";
	$hash->{UndefFn} = "RTL433_USBSTICK_Undef";
	$hash->{AttrList} =
	  "do_not_notify:1,0 " . $readingFnAttributes;
}

#########################################################################									#

sub RTL433_USBSTICK_Define($$)
{
	my ( $hash, $def ) = @_;
	my @a = split( "[ \t][ \t]*", $def );

	return "wrong syntax: define <name> RTL433_USBSTICK"
	  if ( @a != 2 );

	my $name = $a[0];


	$RTL433_USBSTICK_pid = open(KID_TO_READ, "-|");
	if(!defined($RTL433_USBSTICK_pid)) {
		$hash->{STATE} = "Could not start";
		$RTL433_USBSTICK_select = undef;
		return "Could not start binary rtl_433";
	}
	if ($RTL433_USBSTICK_pid) {
		$hash->{STATE} = "Running";
		$RTL433_USBSTICK_select  = IO::Select->new();
		$RTL433_USBSTICK_select->add(\*KID_TO_READ);
		$selectlist{$hash->{NAME}} = $hash;
		$hash->{FD} = fileno(\*KID_TO_READ);# fileno();
	} else {
		# forked program
		exec("rtl_433 -R 20 -C si -q -F csv");
	}

	#InternalTimer(gettimeofday()+10, "RTL433_USBSTICK_Read", $hash, 0);
	#RTL433_USBSTICK_Read($hash);
	return undef;
}

#########################################################################

sub RTL433_USBSTICK_Undef($$)    
{                   
	my ( $hash, $arg ) = @_;    
	delete $selectlist{$hash->{NAME}};
	system("kill $RTL433_USBSTICK_pid");
	RemoveInternalTimer($hash); 
	return undef;               
}    

#########################################################################

# called from the global loop, when the select for hash->{FD} reports data
sub RTL433_USBSTICK_Read($)
{
	my ($hash) = @_;
	my $name = $hash->{NAME};

	my @ready;
	if($RTL433_USBSTICK_select and @ready=$RTL433_USBSTICK_select->can_read(0))
        {
		my $tmp;
		my $len;
		if($len = sysread($ready[0], $tmp, 16*1024)) {
			$Readpart .= "$tmp";
		}
		if( $len == undef ) {
			$RTL433_USBSTICK_select = undef;
			delete $selectlist{$hash->{NAME}};
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
		Log3 $name, 4, "line: $line" ;
		my ($time,$device,$channel,$temperature_F,$temperature_C,$humidity,$battery ) = (split (",", $line));
		readingsBulkUpdate( $hash, "$channel-$device-temp", $temperature_C );
		readingsBulkUpdate( $hash, "$channel-$device-humi", $humidity );
		readingsBulkUpdate( $hash, "$channel-$device-batt", $battery );
	}	
	$Readpart = substr($Readpart, $substrlen);
	###### in die READINGS schreiben
	$hash->{RTL433_USBSTICK_pid} = $RTL433_USBSTICK_pid;
	$hash->{RTL433_USBSTICK_select} = $RTL433_USBSTICK_select;
	readingsBulkUpdate( $hash, "ReadpartLength", length ($Readpart)  );
	readingsEndUpdate( $hash, 1 );

	if(length ($Readpart) > 16*1024) {
		$Readpart = "";
	}
	#InternalTimer(gettimeofday()+$RTL433_USBSTICK_interval, "RTL433_USBSTICK_Read", $hash, 0);
}

#########################################################################

sub RTL433_USBSTICK_Ready($)
{
	my ($hash) = @_;
	return (1>0);
}

1;

=pod
=begin html

<a name="RTL433_USBSTICK"></a>
<h3>RTL433_USBSTICK</h3>
<ul>
  This FHEM module is able to run the rtl_433 command.<br>
  <br><br>

  <a name="RTL433_USBSTICKdefine"></a>
  <b>Define</b>
  <ul>
    <code>define &lt;name&gt; RTL433_USBSTICK</code><br>
    <br><br>
    Example:
    <ul>
      <code>define myRtl433 RTL433_USBSTICK</code><br>
    </ul>
  </ul>
  <br>

=end html
=cut

