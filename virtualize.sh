#!/bin/bash
#
# Copyright (C) 2015 eNovance SAS <licensing@enovance.com>
#
# Author: Frederic Lepied <frederic.lepied@enovance.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


source common/infra-virt.function

### virtualize.sh specific functions

usage () {
        echo "
usage: $0 [OPTION]
Collect architecture information from the edeploy directory as generated
by config-tools/download.sh and use the virtulizor.py to boostrap a SpS platform.

arguments:
    -h|--help                     Show this help
    -H|--hypervisor=name          Set the hypervisor hostname, default (${virthost})
    -d|--debug                    Set the debug mode for this script, default: disabled
    -v|--virt=virt_platform.yml   Set the path to the infra's yaml, default: (${platform})
    -e|--extra='--replace'        Add extra parameters to virtulizor.py
    -p|--prefix                   Change the platform's prefix, default: unix user
    -s|--socks                    Create a socks server to test your platform
    -t|--tempest                  Launch the sanity job at the end of a deployement

For example:
./virtualize.sh -H localhost -e '--replace' I.1.2.1/
will deploy the environment from the I.1.2.1/ directory.

and
./virtualize.sh -H localhost -e '--replace' -w ../config-tools/ --sockets --tempest
will deploy the env in your directory config-tools/, create a tunnel socks and launch tempest"
}

debug() {
    set -x
}


### Arguments parsing

ARGS=$(getopt -o w:v:ste:p:dH:h -l "wordkir:,virt:,socks,tempest,extra:,platform,debug,hypervisor:,help" -- "$@");
#Bad arguments
if [ $? -ne 0 ]; then
    usage
    exit 1
fi

extra_args=""

eval set -- "$ARGS";
while true; do
    case "$1" in
        -d|--debug)
            shift
            debug
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -H|--hypervisor)
            shift;
            if [ -n "$1" ]; then
                virthost=$1
                shift;
            fi
            ;;
        -p|--prefix)
            shift;
            if [ -n "$1" ]; then
                PREFIX=$1
                shift;
            fi
            ;;
        -e|--extra)
            shift;
            if [ -n "$1" ]; then
                extra_args=$1
                shift;
            fi
            ;;
        -v|--virt)
            shift;
            if [ -n "$1" ]; then
                platform=$1
                shift;
            fi
            ;;
        -s|--socks)
            socks="True"
            shift;
            ;;
        -t|--tempest)
            tempest="True"
            shift;
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "$1 : Wrong parameters"
            usage
            exit 1
            ;;
    esac
done

workdir=$1

[ -f ~/virtualizerc ] && source ~/virtualizerc

### Handler stuff

deploy ${workdir} ${extra_args}
call_jenkins_job "puppet"

if [ "${tempest}x" == "Truex" ]; then
    call_jenkins_job "sanity"
fi

# Dump elasticsearch logs into ${LOG_DIR},
# upload_logs will update the dump in swift.
$ORIG/dumpelastic.py --url http://${installserverip}:9200 --output-dir ${LOG_DIR}

upload_logs

#ssh $SSHOPTS -A root@$installserverip configure.sh

# virtualize.sh ends here
