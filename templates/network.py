#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 eNovance SAS <licensing@enovance.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

NETWORK = """
<network>
  <name>{{ name }}</name>
  <uuid>{{ uuid }}</uuid>
  <bridge name='{{ bridge_name }}' stp='on' delay='0'/>
  <mac address='{{ mac }}'/>
{% if dhcp is defined %}
  <forward mode='nat'>
    <nat>
      <port start='1024' end='65535'/>
    </nat>
  </forward>
  <ip address='{{ dhcp.address }}' netmask='{{ dhcp.netmask }}'>
    <dhcp>
{%if dhcp.range is defined %}
      <range start='{{ dhcp.range.ipstart }}' end='{{ dhcp.range.ipend }}' />
{% endif %}
    </dhcp>
  </ip>
{% endif %}
</network>
"""
