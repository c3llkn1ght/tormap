#!/bin/bash

#Script created by s3B-a
# =======================
#      TORmap v1.0.0
# =======================


#Color codes

GREEN="\e[32m"
CYAN="\e[36m"
ORANGE="\e[38;2;255;140;0m"
YELLOW="\e[33m"
RED="\e[31m"
RES="\e[0m"
BOLD="\e[1m"

printAsciiLogo() {
	echo -e "${ORANGE} +-----------------------------------------------------+"
	echo -e "${ORANGE} |████████╗ ██████╗ ██████╗ ███╗   ███╗ █████╗ ██████╗ |"
	echo -e "${ORANGE} |╚══██╔══╝██╔═══██╗██╔══██╗████╗ ████║██╔══██╗██╔══██╗|"
	echo -e "${ORANGE} |   ██║   ██║   ██║██████╔╝██╔████╔██║███████║██████╔╝|"
	echo -e "${ORANGE} |   ██║   ██║   ██║██╔══██╗██║╚██╔╝██║██╔══██║██╔═══╝ |"
	echo -e "${ORANGE} |   ██║   ╚██████╔╝██║  ██║██║ ╚═╝ ██║██║  ██║██║     |"
	echo -e "${ORANGE} |   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝     |"
	echo -e "${ORANGE} +----------------------(v1.0.0)-----------------------+${RES}"
}

log() {
	local color=$1
	local message=$2
	echo -e "${color}${message}${RES}"
}

#Asks for root perms, only necessary for the apt installs
if [ "$EUID" -ne 0 ]; then
	echo "Run as root"
	exec sudo "$0" "$@"
	exit
fi

#Installs Dependancies
log "${YELLOW}" "Checking if tor, privoxy and proxychains are installed..."
# dont blindly apt install, just check if the packages are there and install them if necessary
missing_pkgs=()

for pkg in tor privoxy proxychains; do
    if ! dpkg -s "$pkg" >/dev/null 2>&1; then
        missing_pkgs+=("$pkg")
    fi
done

if [ ${#missing_pkgs[@]} -ne 0 ]; then
    log "${YELLOW}" "Installing missing packages: ${missing_pkgs[*]}"
    apt-get update -y
    apt-get install -y "${missing_pkgs[@]}"
else
    log "${GREEN}" "All dependencies already installed."
fi

# copy the proxychains.conf into the current directory and use that for scans
# makes sure proxy_dns is enabled so we dont leak DNS

TORPROXY_CONF="./torproxy.conf"

#make the file if its not there
if [ ! -f "$TORPROXY_CONF" ]; then
    log "${YELLOW}" "Creating local proxychains config: $TORPROXY_CONF"
    cp /etc/proxychains.conf "$TORPROXY_CONF"
fi

# make sure proxy_dns is there
if ! grep -qE '^[[:space:]]*proxy_dns' "$TORPROXY_CONF"; then
    log "${YELLOW}" "Enabling proxy_dns in $TORPROXY_CONF"
    echo "proxy_dns" >> "$TORPROXY_CONF"
fi

# make sure the required entry is there
if ! grep -qE '^[[:space:]]*socks5[[:space:]]+127\.0\.0\.1[[:space:]]+9050' "$TORPROXY_CONF"; then
    log "${YELLOW}" "Adding Tor SOCKS entry to $TORPROXY_CONF"
    echo "socks5 127.0.0.1 9050" >> "$TORPROXY_CONF"
fi


#Checks if required services are running
if ! systemctl is-active --quiet tor; then
    log "${YELLOW}" "Tor isn't running, launching..."
    systemctl start tor
else
    log "${GREEN}" "Tor is running."
fi

printAsciiLogo

#Lauches TORmap console
log "${GREEN}" "Launching console..."
if [ -f "./console.py" ]; then
    python3 console.py launch
else
    log "${RED}" "console.py not found!"
fi
