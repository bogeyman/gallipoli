#!/bin/sh
if [ ! -e python/gallipoli.py ]; then
	echo "Bitte im gallipoli Verzeichnis ausfuehren"
	exit 1
fi

# Munin scripts
# test with "munin-run gallipoli-temperature"

# dependencies
# 
apt-get install -y python-rrdtool
# 
rm /usr/local/share/munin/plugins/gallipoli*
cp munin/gallipoli* /usr/local/share/munin/plugins/
rm /etc/munin/plugins/gallipoli*
( cd /etc/munin/plugins/ && ln -s /usr/local/share/munin/plugins/gallipoli* .)
service munin-node restart
