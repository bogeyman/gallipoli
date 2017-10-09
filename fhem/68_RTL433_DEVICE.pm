package main;

use strict;                          #
use warnings;                        #
use IO::Select;

sub RTL433_DEVICE_Parse($);                  #

#########################################################################

sub RTL433_DEVICE_Initialize($)
{
	my ($hash) = @_;

	$hash->{ParseFn} = "RTL433_DEVICE_Parse";
	$hash->{DefFn}   = "RTL433_DEVICE_Define";
	$hash->{UndefFn} = "RTL433_DEVICE_Undef";
	$hash->{AttrList} =
	  "do_not_notify:1,0 " . $readingFnAttributes;
	$hash->{Match} = "^.*"; 
	$hash->{AutoCreate} = {"X_.*"  => { ATTR   => "event-on-change-reading:.* event-min-interval:.*:300",
		FILTER => "%NAME",
		GPLOT  => "temp4hum4:Temp/Hum,",
		autocreateThreshold => "2:140"} };
}

#########################################################################									#

sub RTL433_DEVICE_Define($$)
{
	my ( $hash, $def ) = @_;
	my @a = split( "[ \t][ \t]*", $def );

	return "wrong syntax: define <name> RTL433_DEVICE addr"
	  if ( @a != 3 );

	my $name = $a[0];
	my $addr = $a[2];

	$modules{RTL433_DEVICE}{defptr}{$addr} = $hash;
	$hash->{addr} = $addr;

	$hash->{STATE} = "Init";

	return undef;
}

#########################################################################

sub RTL433_DEVICE_Undef($$)    
{                   
	my ( $hash, $arg ) = @_;    
	RemoveInternalTimer($hash); 
	delete($modules{RTL433_DEVICE}{defptr}{$hash->{addr}});
	return undef;               
}    

#########################################################################

sub RTL433_DEVICE_Parse($$)
{
	my ($hash, $message) = @_;
	my $name = $hash->{NAME};
	Log3 $name, 4, "$name Parse: §message" ;

	my ($time,$device,$channel,$temperature_F,$temperature_C,$humidity,$battery ) = (split (",", $message));
	my $addr = $channel . "_" . $device;
	if(!exists($modules{RTL433_DEVICE}{defptr}{$addr}))
	{
		return "UNDEFINED RTL433_$addr RTL433_DEVICE $addr";
	}
	my $shash = $modules{RTL433_DEVICE}{defptr}{$addr};
	my $t = sprintf('%.1f', $temperature_C);
	readingsBeginUpdate($shash);
	readingsBulkUpdate( $shash, "temperature", $t );
	readingsBulkUpdate( $shash, "humidity", $humidity );
	readingsBulkUpdate( $shash, "battery", $battery );
	readingsEndUpdate( $shash, 1 );
	$shash->{STATE} = "T:$t H:$humidity B:$battery";
	return $shash->{NAME};
}

#########################################################################

1;

=pod
=begin html

<a name="RTL433_DEVICE"></a>
<h3>RTL433_DEVICE</h3>
<ul>
  This FHEM module is able to run the rtl_433 command.<br>
  <br><br>

  <a name="RTL433_DEVICEdefine"></a>
  <b>Define</b>
  <ul>
    <code>define &lt;name&gt; RTL433_DEVICE addr</code><br>
    <br><br>
    Example:
    <ul>
      <code>define myRtl433 RTL433_DEVICE 192</code><br>
    </ul>
  </ul>
  <br>

=end html
=cut

