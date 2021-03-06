#
# Copyright (c) 2009 by kinabalu (andrew AT mysticcoders DOT com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

#
# Growl Notification script over network using Net::Growl
#
# History:
#
# 2009-04-16, kinabalu <andrew AT mysticcoders DOT com>
#	version 0.2, removed need for Parse::IRC
#
# 2009-04-10, kinabalu <andrew AT mysticcoders DOT com>
#	version 0.1, initial version rewritten from growl-notify
#   - original inspiration from growl-notify.pl author Zak Elep
#
# /growl and /gl can be used in combination with these actions
#
# /growl on
# /growl off
# /growl setup [host] [password]
# /growl inactive [time_in_seconds]
# /growl status
# /growl test [message]
# /help growl
#
# The script can be laoded into WeeChat by executing:
#
# /perl load growl-net-notify.pl
#
# The script may also be auto-loaded by WeeChat.  See the
# WeeChat manual for instructions about how to do this.
#
# This script was tested with WeeChat version 0.2.6.  An
# updated version of this script will be available when
# the new WeeChat API is officially released.
#
# For up-to-date information about this script, and new
# version downloads, please go to:
#
# http://www.mysticcoders.com/apps/growl-notify/
#
# If you have any questions, please contact me on-line at:
#
# irc.freenode.net - kinabalu (op): ##java
#
# - kinabalu
#

use Net::Growl;
use integer;

my $growl_app = "growl-net-notify";				# name given to Growl for configuration
my $growl_active = 1;
my $weechat_version = "0.2.6";

sub message_process_init {

	weechat::add_message_handler("weechat_highlight", "highlight_public");
	weechat::add_message_handler("weechat_pv", "highlight_privmsg");
}

#
# support for private messages, have to parse the IRC message
#
sub highlight_privmsg {
    my ( $nick, $message ) = ( $_[1] =~ /:([^!]+)[^:]+:(.*)/ );
    
	send_message($nick, $message);    
	return weechat::PLUGIN_RC_OK;	
}

#
# support for highlights of nicks in public, have to parse the IRC message
#
sub highlight_public {
	my ( $nick, $channel, $message ) = ( $_[1] =~ /:([^!]+)[^#]+([^:]+):(.*)/ );
		
	send_message($nick, $message . " in " . $channel); 
	return weechat::PLUGIN_RC_OK;	
}

sub send_message {
	my ( $nick, $message ) = @_;
	
	my $inactivity = 0;
	
	$inactivity = weechat::get_info("inactivity");
		
	if((&getc('growl_net_inactivity') - $inactivity) <= 0 && $growl_active) {
		growl_notify( &getc('growl_net_client'), &getc('growl_net_pass'), &getc('growl_net_port'), "$growl_app", "$nick", "$message" );
	}			
}

#
# smaller way to do weechat::get_plugin_config
#
sub getc {
	return weechat::get_plugin_config($_[0]);
}

#
# smaller way to do weechat::get_plugin_config
#
sub setc {
	return weechat::set_plugin_config($_[0], $_[1]);
}

#
# print function
# 
sub prt {
	weechat::print($_[0]);
}

#
# Send notification through growl
#
# args: $host, $pass, $port, $application_name, $title, $description
#
sub growl_notify {
	Net::Growl::notify( host=> $_[0], 
						password=> $_[1], 
						port=> $_[2], 
						application=> $_[3], 
						title=> $_[4], 
						description => $_[5], 
						priority=> 0, 
						sticky=> '1' );
}

#
# Register your app with Growl system
#
# args: $host, $pass, $port, $app
#
sub growl_register {	
	Net::Growl::register( host=> $_[0], 
						  password=> $_[1], 
						  port=> $_[2], 
						  application=> $_[3] );	
}

#
# Handler will process commands
#
# /growl on
# /growl off
# /growl setup [host] [password] [port]
# /growl inactive [time_in_seconds]
# /growl status
# /growl test [message]
# /help growl
#
sub handler {
	no strict 'refs';	# access symbol table
	
	my $server = shift;
	my $argList = shift;

	my @args = split(/ /, $argList);
	my $command = $args[0];	
		
	if(!$command) {
		prt("Rawr!");
		return weechat::PLUGIN_RC_OK;
	}
	
	if($command eq "off") {
		$growl_active = 0;
		prt("Growl notifications: OFF");
		return weechat::PLUGIN_RC_OK;
	} elsif($command eq "on") {
		$growl_active = 1;
		prt("Growl notifications: ON");
		return weechat::PLUGIN_RC_OK;
	} elsif($command eq "inactive") {
		if(exists $args[1] && $args[1] >= 0) {
			setc("growl_net_inactivity", $args[1]);
			prt("Growl notifications inactivity set to: " . $args[1] . "s");
			return weechat::PLUGIN_RC_OK;
		}
		return weechat::PLUGIN_RC_KO;	
	} elsif($command eq "setup") {
		if(exists $args[1] && $args[1] ne "") {
			setc("growl_net_client", $args[1]);			
		} 
		if(exists $args[2] && $args[2] ne "") {
			setc("growl_net_pass", $args[2]);
		}
		if(exists $args[3] && $args[3] ne "") {
			setc("growl_net_port", $args[3]);
		}
		growl_register( &getc('growl_net_client'), &getc('growl_net_pass'), &getc('growl_net_port'), "$growl_app" );				
		prt("Growl setup re-registered with: [host: " . &getc('growl_net_client') . ":"  . &getc('growl_net_port') . ", pass: " . &getc('growl_net_pass') . "]"); 
		return weechat::PLUGIN_RC_OK;
	} elsif($command eq "status") {
		prt("Growl notifications: " . ($growl_active ? "ON" : "OFF") . ", inactivity timeout: " . &getc("growl_net_inactivity"));
		return weechat::PLUGIN_RC_OK;
	} elsif($command eq "test") {
		my $test_message = substr $argList, 5;
		prt("Sending test message: " . $test_message);
		growl_notify( &getc('growl_net_client'), &getc('growl_net_pass'), &getc('growl_net_port'), "$growl_app", "Test Message", $test_message );
		return weechat::PLUGIN_RC_OK;
	}

    return weechat::PLUGIN_RC_KO;
}


#
# setup
#
my $version = '0.2';

weechat::register $growl_app, $version, '',	'Send Weechat notifications thru Net::Growl';
		
weechat::add_command_handler ("growl", "handler", "setup the growl notify script",
							  "on|off|setup [host] [password] [port]|inactive [time_in_seconds]|status|help",
							   " on: turn on growl notifications (default)\n"
							  ."off: turn off growl notifications\n"
							  ."setup [host] [password] [port]: change the parameters for registration/notification with Growl\n"
							  ."inactive [time_in_seconds]: number of seconds of inactivity before we notify (default: 30)\n"
							  ."status: gives info on notification and inactivity settings\n"
							  ."test [message]: send a test message\n",
							  "on|off|setup|inactive|status");
weechat::add_command_handler ("gl", "handler", "setup the growl notify script",
							  "on|off|setup [host] [password] [port]|inactive [time_in_seconds]|status|help",
							  "on: turn on growl notifications (default)\n"
							  ."off: turn off growl notifications\n"
							  ."setup [host] [password] [port]: change the parameters for registration/notification with Growl\n"
							  ."inactive [time_in_seconds]: number of seconds of inactivity before we notify (default: 30)\n"
							  ."status: gives info on notification and inactivity settings\n"
							  ."test [message]: send a test message\n",
							  "on|off|setup|inactive|status");	

my $default_growl_net_pass = "password";
my $default_growl_net_client = "localhost";
my $default_growl_net_inactivity = 30;
my $default_growl_net_port = 9887;				# default UDP port used by Growl

&setc("growl_net_pass", $default_growl_net_pass) if (&getc("growl_net_pass") eq "");
&setc("growl_net_client", $default_growl_net_client) if (&getc("growl_net_client") eq "");
&setc("growl_net_inactivity", $default_growl_net_inactivity) if (&getc("growl_net_inactivity") eq "");
&setc("growl_net_port", $default_growl_net_port) if (&getc("growl_net_port") eq "");
		
# register our app with growl		
growl_register( &getc('growl_net_client'), &getc('growl_net_pass'), &getc('growl_net_port'), "$growl_app" );

# send up a we're here and notifying 
growl_notify( &getc('growl_net_client'), &getc('growl_net_pass'), &getc('growl_net_port'), "$growl_app", "Starting Up", "Weechat notification through Growl = on" );

message_process_init();
