# Copyright (c) 2011 by Andrew Lombardi <andrew@mysticcoders.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
# Weather display in channel
# (This script requires WeeChat 0.3.0.)
#
# Usage: Add "weather" to weechat.bar.status.items or other bar you like.
#        Specify city: "/set plugins.var.python.gweather.city Tokyo".
#
#        Formatting: "/set plugins.var.python.gweather.format %C: %D %U, %O".
#            Where: %C - city
#                   %D - temperature degrees
#                   %U - temperature unit
#                   %O - current condition
#
# History:
#
# 2011-02-02, kinabalu <andrew@mysticcoders.com>
#   version 0.1: - initial code to display weather in channel and easier config
#
# Forked from gweather code
#
# 2010-04-15, jkesanen <jani.kesanen@gmail.com>
#   version 0.3: - added output formatting
#                - removed output and city color related options
# 2010-04-09, jkesanen <jani.kesanen@gmail.com>
#   version 0.2.1: - added support for different languages
# 2010-04-07, jkesanen <jani.kesanen@gmail.com>
#   version 0.2: - fetch weather using non-blocking hook_process interface
# 2010-04-06, jkesanen <jani.kesanen@gmail.com>
#   version 0.1: - initial release.
#

import weechat

from urllib import quote
from xml.dom import minidom
from time import time
from sys import version_info

SCRIPT_NAME	= "weather"
SCRIPT_AUTHOR	= "Andrew Lombardi <andrew@mysticcoders.com>"
SCRIPT_VERSION	= "0.1"
SCRIPT_LICENSE	= "GPL3"
SCRIPT_DESC	= "In channel text to display weather from Google"
DEGREE_SYMBOL   = u"\u00B0"
FORMAT		= "Weather for %C: %O / %FF (%EC) - %H / %W"; 

# Script options
settings = {
    # City to monitor (ex. "Tokyo", "Austin, Texas", ...)
    'city'           : '',
    # Language of the conditions (ex. en, ja, fi, fr, ...)
    'language'       : 'en',
    # Temperature units (C or F)
    'unit'           : 'C',
    # Update interval in minutes
    'interval'       : '10',
    # Timeout in seconds for fetching weather data
    'timeout'        : '10',
    # The color of the output
    'output_color'   : 'white',
    # Formatting (%C = city, %D = degrees, %U = unit, %O = condition)
    'format'         : 'Weather for %C: %O / %FF (%EC) - %H / Wind: %W',
}

# Timestamp for the last update
last_run = 0

# The last city, language and format for the need of refresh
last_city = ''
default_city = ''

# Cached copy of the last successful output
gweather_output = 'WAIT'

gweather_hook_process = ''
gweather_stdout = ''

# The url to Google's "unofficial" weather API
GOOGLE_WEATHER_URL = 'http://www.google.com/ig/api?weather=%s&hl=%s'

def parse_google_weather(xml_response):
    '''
    Parses weather report from Google

    This uses code from python-weather-api 0.2.2 by Eugene Kaznacheev <qetzal@gmail.com>.

    Returns:
      weather_data: a dictionary of weather data that exists in XML feed.
    '''
    try:
        dom = minidom.parseString(xml_response)
        weather_data = {}
        weather_dom = dom.getElementsByTagName('weather')[0]
    except:
        return

    data_structure = {
        'forecast_information': ('city', 'postal_code', 'latitude_e6', 'longitude_e6', 'forecast_date', 'current_date_time', 'unit_system'),
        'current_conditions': ('condition','temp_f', 'temp_c', 'humidity', 'wind_condition', 'icon')
    }

    for (tag, list_of_tags2) in data_structure.iteritems():
        tmp_conditions = {}
        for tag2 in list_of_tags2:
            try:
                tmp_conditions[tag2] = weather_dom.getElementsByTagName(tag)[0].getElementsByTagName(tag2)[0].getAttribute('data').strip()
            except IndexError:
                pass
        weather_data[tag] = tmp_conditions

    dom.unlink()

    return weather_data


def format_weather(weather_data):
    '''
    Formats the weather data dictionary received from Google

    Returns:
      output: a string of formatted weather data.
    '''
    output = weechat.color(weechat.config_get_plugin('output_color')) + FORMAT
    output = output.replace('%C', weechat.config_get_plugin('city'))

    ftemp = 'N/A'
    ctemp = 'N/A'
    condition = 'N/A'
    city = weechat.config_get_plugin('city')
    wind = 'None'
    humidity = 'N/A'

    if weather_data:
	ftemp = weather_data['current_conditions']['temp_f'].encode('utf-8')
	ctemp = weather_data['current_conditions']['temp_c'].encode('utf-8')	

        if weather_data['current_conditions'].has_key('condition'):
            condition = weather_data['current_conditions']['condition'].encode('utf-8')

	city = weather_data['forecast_information']['city'].encode('utf-8')
	humidity = weather_data['current_conditions']['humidity'].encode('utf-8')
	if weather_data['current_conditions'].has_key('wind_condition'):
	    wind = weather_data['current_conditions']['wind_condition'].encode('utf-8')		

    output = output.replace('%F', ftemp)
    output = output.replace('%E', ctemp)
    output = output.replace('%O', condition)
    output = output.replace('%C', city)
    output = output.replace('%H', humidity)
    output = output.replace('%W', wind)

    output += weechat.color('reset')

    return output


def weather_data_cb(data, command, rc, stdout, stderr):
    '''
    Callback for the data fetching process.
    '''
    global last_city, last_lang, last_run, last_format
    global gweather_hook_process, gweather_stdout, gweather_output

    if rc == weechat.WEECHAT_HOOK_PROCESS_ERROR or stderr != '':
        weechat.prnt('', '%sgweather: Weather information fetching failed: %s' % (\
            weechat.prefix("error"), stderr))
        return weechat.WEECHAT_RC_ERROR

    if stdout:
        gweather_stdout += stdout

    if int(rc) < 0:
        # Process not ready
        return weechat.WEECHAT_RC_OK

    # Update status variables for succesful run
    last_run = time()
    last_location = weechat.config_get_plugin('location')
    gweather_hook_process = ''

    if not gweather_stdout:
        return weechat.WEECHAT_RC_OK

    try:
        # The first row should contain "content-type" from HTTP header
        content_type, xml_response = gweather_stdout.split('\n', 1)
    except:
        # Failed to split received data in two at carridge return
        weechat.prnt('', '%sweather: Invalid data received' % (weechat.prefix("error")))
        gweather_stdout = ''
        return weechat.WEECHAT_RC_ERROR

    gweather_stdout = ''

    # Determine the used character set in the response
    try:
        charset = content_type.split('charset=')[1]
    except:
        charset = 'utf-8'

    if charset.lower() != 'utf-8':
        xml_response = xml_response.decode(charset).encode('utf-8')

    # Feed the respose to parser and parsed data to formatting
    weather_data = parse_google_weather(xml_response)
    gweather_output = format_weather(weather_data)

    weechat.command(weechat.current_buffer(), gweather_output);

    return weechat.WEECHAT_RC_OK


def weather_cb(server, buffer, argList):
    ''' Callback for the Google weather bar item. '''
    global last_run, last_city
    global gweather_output, gweather_hook_process

    if(argList.partition(" ")[0] == "default"):
	default_city = argList.partition(" ")[2]
	last_city = default_city
	weechat.prnt(weechat.current_buffer(), "Saving new location as: %s" % default_city)

    if(default_city is ''):
	if(argList == ''):
		weechat.prnt(weechat.current_buffer(), "Error: no default city, provide one with command")
		return weechat.WEECHAT_RC_ERROR
	default_city = argList	
	

    # Use cached copy if it is updated recently enough
    if weechat.config_get_plugin('city') == last_city and \
       weechat.config_get_plugin('language') == last_lang and \
       weechat.config_get_plugin('format') == last_format and \
       (time() - last_run) < (int(weechat.config_get_plugin('interval')) * 60):
	weechat.command(weechat.current_buffer(), gweather_output)
	return weechat.WEECHAT_RC_OK

    location_id, hl = map(quote, (weechat.config_get_plugin('city'), \
                                  weechat.config_get_plugin('language')))
    url = GOOGLE_WEATHER_URL % (location_id, hl)

    command = 'urllib2.urlopen(\'%s\')' % (url)

    if gweather_hook_process != "":
        weechat.unhook(gweather_hook_process)
        gweather_hook_process = ''

	weechat.prnt(weechat.current_buffer(), "hi mom")
    # Fire up the weather informationg fetching
    gweather_hook_process = weechat.hook_process(\
        "python -c \"import urllib2;\
                     handler = " + command + ";\
                     print handler.info().dict['content-type'];\
                     print handler.read();\
                     handler.close();\"",
        int(weechat.config_get_plugin('timeout')) * 1000, "weather_data_cb", "")

    # The old cached string is returned here. gweather_data_cb() will 
    # request a new update after the data is fetched and parsed.
    return weechat.WEECHAT_RC_OK


weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", "")

weechat.hook_command("weather", 
	"Display the current weather from Google", 
	"[default] [zip/city]",
	"adding default saves zip/city so arg is not needed on second run, then provide default preceding zip/city argument to resave your default", 
	"", 
	"weather_cb", 
	"")
