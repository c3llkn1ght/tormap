#!/usr/bin/env python3

# Script created by s3B-a
# =======================
#  TORmap Console v1.0.0
# =======================

import cmd
import logging
import shlex
import subprocess
import sys
import random
import ipaddress

logging.basicConfig(
    level=logging.INFO,
    format='\033[1;36m[TORmap]\033[0m %(message)s',
)
logger = logging.getLogger('TORmap')

def gen_decoys(count=4) -> str:
    """
    gen a decoy string for -D
    """

    ranges = [
        "138.197.0.0/16",
        "185.228.168.0/24",
        "23.67.0.0/16"
    ]

    def rand_cidr_ip(cidr: str) -> str:
        net = ipaddress.IPv4Network(cidr, strict=False)

        network_int = int(net.network_address)
        broadcast_int = int(net.broadcast_address)

        random_int = random.randint(network_int + 1, broadcast_int - 1)

        return str(ipaddress.IPv4Address(random_int))

    decoys = set()

    while len(decoys) < count:
        cidr = random.choice(ranges)
        decoys.add(rand_cidr_ip(cidr))

    decoy_list = list(decoys)
    insert_pos = random.randint(0, len(decoy_list))
    decoy_list.insert(insert_pos, "ME")

    return ",".join(decoy_list)


# Class that contains the console
class TORmapConsole(cmd.Cmd):
    prompt = "TORmap > "

    # variables
    def __init__(self):
        super().__init__()
        self.target = ""
        self.flags = []
        # -O and -f wont work over tor/proxychains
        self.allowed_flags = {
            "-sV", "-p-"
        }
        # --spoof-mac doesnt do anything over tor. you arent sending ethernet frames or exposing your NIC.
        self.valuesFlag = {
            "-p", "--data-length", "--max-retries"
        }

    # on input "set target" or "set flags"
    def do_set(self, args):
        parts = shlex.split(args)
        if len(parts) < 2:
            logger.warning("Usage: set [target|flags] <value>")
            return

        key, value = parts[0], " ".join(parts[1:])
        if key == "target":
            self.target = value
            logger.info(f"Target set to: {self.target}")

        elif key == "flags":
            rawFlags = shlex.split(value)
            validFlags = []
            i = 0
            while i < len(rawFlags):
                flag = rawFlags[i]

                if flag in self.valuesFlag:
                    if i + 1 < len(rawFlags):
                        param = rawFlags[i + 1]

                        if flag == "-p-" or param == "-":
                            validFlags.append("-p-")
                        else:
                            validFlags.extend([flag, param])
                        i += 2
                        continue
                    else:
                        logger.warning(f"Missing value for {flag}")
                        break

                elif flag in self.allowed_flags:
                    validFlags.append(flag)
                    i += 1
                    continue

                else:
                    logger.warning(f"Ignoring unrecognized flag: {flag}")
                    i += 1

            self.flags = validFlags
            logger.info(f"Flags set to: {' '.join(self.flags)}")
        else:
            logger.warning("Unknown key. Use 'target' or 'flags'")

    # on input "show"
    def do_show(self, args):
        logger.info("Current settings:")
        logger.info(f"Target: {self.target}")
        logger.info(f"Flags: {' '.join(self.flags)}")

    # on input "run"
    def do_run(self, args):
        if not self.target:
            logger.error("Target not set. Use: set target <IP/host>")
            return

        # -sS wont work over proxychains, Tor only allows tcp connections over SOCKS
        # these flags are mandatory for nmap to work over proxychains
        # -n i guess isnt technically mandatory, but should definitely be used
        mandatory_flags = ["-sT", "-Pn", "-n"]
        final_flags = list(self.flags)

        for flag in mandatory_flags:
            if flag not in final_flags:
                final_flags.append(flag)

        # decoys technically dont do anything for the user in this chain, but there is no harm in using them
        # they won't improve anonymity and they dont change tor routing, but whatever, its fun
        decoys = gen_decoys(count=5)

        command = (
                # use the file made in the .sh
                ["proxychains", "-f", "./torproxy.conf"]
                + ["nmap"]
                + final_flags
                + ["-D", decoys, "-vvv"]
                + [self.target]
        )

        logger.info(f"Running: {shlex.join(command)}")

        result = subprocess.run(command)

        if result.returncode != 0:
            logger.error(f"Nmap exited with code {result.returncode}")

    # on input "exit"
    def do_exit(self, args):
        logger.info("Exiting...")
        return True

    # on input "help" or "?"
    def do_help(self, args):
        helpTxt = """
[console help]
Available Commands:

    set target <ip>		Set the target IP or Host
    set flags <options>	Set the Nmap flags
    show			    Show the current settings
    run			        Run Nmap through proxychains
    exit			    Exit the console
    help			    Show this message


Flags Available (Use with: set flags <flags>):

    Mandatory Flags:
      -sT           Only scan type Tor supports
      -Pn			Skip ICMP host discovery (won’t work on tor)
      -n            Prevents DNS leaks (Target will still see Tor exit node IP)
    
    Scan Tags:
      -sV			Service Version Detection
      -p			Specified Ports to scan

    Agressiveness:
      --max-retries <n>	Number of times nmap will retry sending a probe

    Bypass:
      --data-length <n>	Append random data to packets

    Note: you can combine flags by typing 'set flags -sV -p-'

"""
        logger.info(helpTxt.strip())


# Confirms Launch of terminal
def launch():
    logger.info("Welcome to the TORmap console!")
    logger.info("Map a network like Anon")
    shell = TORmapConsole()
    shell.cmdloop()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "launch":
        launch()
    else:
        logger.info("Usage: ./console.py launch")

