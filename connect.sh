#!/bin/bash
#
# Copyright (C) 2015 eNovance SAS <licensing@enovance.com>
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

# usage ./connect.sh "prefix"
# default prefix is $USER

SSHOPTS="-oBatchMode=yes -oCheckHostIP=no -oHashKnownHosts=no -oStrictHostKeyChecking=no -oPreferredAuthentications=publickey -oChallengeResponseAuthentication=no -oKbdInteractiveDevices=no -oUserKnownHostsFile=/dev/null"
PREFIX=${1:-$USER}
virthost=${virthost:-"localhost"}
role=${2:-"install-server"}
hostname=""

source common/infra-virt.function

node_name=$(find_host_by_profile ${role})
mac=$(get_mac ${node_name})
ip=$(get_ip ${mac})
echo "Connecting to ${role} (${mac}) at ${ip}"
ssh $SSHOPTS root@$ip
