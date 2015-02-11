#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015 eNovance SAS <licensing@enovance.com>
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

import argparse
import logging
import os.path
import random
import re
import string
import subprocess
import sys
import tempfile
import time
import uuid

import ipaddress
import jinja2
import libvirt
import six
import yaml

logging.basicConfig(level=logging.DEBUG)


def random_mac():
    return "52:54:00:%02x:%02x:%02x" % (
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255))


def canical_size(size):
    """Convert size to GB or MB

    Convert GiB to MB or return the original string.

    """
    gi = re.search('^(\d+)Gi', size)
    if gi:
        new_size = "%i" % (int(gi.group(1)) * 1000 ** 3)
    else:
        new_size = size
    return new_size


def get_conf(argv=sys.argv):
    def check_prefix(value):
        if not re.match('^[a-zA-Z\d]+$', value):
            sys.stderr.write("Invalid value for --prefix parameter\n")
            sys.exit(1)
        return value
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Deploy a virtual infrastructure.')
    parser.add_argument('--replace', action='store_true',
                        help='existing conflicting resources will be remove '
                        'recreated.')
    parser.add_argument('input_file', type=str,
                        help='the YAML input file, as generated by '
                        'collector.py.')
    parser.add_argument('target_host', type=str,
                        help='the name of the libvirt server. The local user '
                        'must be able to connect to the root account with no '
                        'password authentification.')
    parser.add_argument('--pub-key-file', type=str,
                        default=os.path.expanduser(
                            '~/.ssh/id_rsa.pub'),
                        help='the path to the SSH public key file that must '
                        'be injected in the install-server root and jenkins '
                        'account')
    parser.add_argument('--prefix', default='default', type=check_prefix,
                        help='optional prefix to put in the machine and '
                        'network to avoid conflict with resources create by '
                        'another virtualizor instance. Thanks to this '
                        'parameter, the user can run as virtualizor as '
                        'needed on the same machine.')
    parser.add_argument('--public_network', default='nat', type=str,
                        help='allow the user to pass the name of a libvirt '
                        'NATed network that will be used as a public network '
                        'for the install-server. This public network will by '
                        'attached to eth1 interface and IP address is '
                        'associated using the DHCP.')

    conf = parser.parse_args(argv)
    return conf


class Hypervisor(object):
    def __init__(self, conf):
        self.target_host = conf.target_host
        self.conn = libvirt.open('qemu+ssh://root@%s/system' %
                                 conf.target_host)

    def create_networks(self, conf, install_server_info):
        net_definitions = {
            ("%s_sps" % conf.prefix): {},
            ("%s" % conf.public_network):
                {"dhcp": {"address": "192.168.140.1",
                          "netmask": "255.255.255.0",
                          "range": {
                                 "ipstart": "192.168.140.2",
                                 "ipend": "192.168.140.254"}}}
        }

        existing_networks = ([n.name() for n in self.conn.listAllNetworks()])
        for netname in net_definitions:
            exists = netname in existing_networks
            if exists and conf.replace:
                self.conn.networkLookupByName(netname).destroy()
                logging.info("Cleaning network %s." % netname)
                exists = False
            if not exists:
                logging.info("Creating network %s." % netname)
                network = Network(netname, net_definitions[netname])
                self.conn.networkCreateXML(network.dump_libvirt_xml())
        self.public_net = self.conn.networkLookupByName(
                                conf.public_network)

    def wait_for_install_server(self, hypervisor, mac):
        while True:
            for lease in hypervisor.public_net.DHCPLeases():
                if lease['mac'] == mac:
                    return lease['ipaddr']
            time.sleep(1)

    def push(self, source, dest):
        subprocess.call(['scp', '-q', '-r', source,
                         'root@%s' % self.target_host + ':' + dest])

    def call(self, *kargs):
        subprocess.call(['ssh', 'root@%s' % self.target_host] +
                        list(kargs))

    class MissingPublicNetwork(Exception):
        pass


class Host(object):
    host_template_string = """
<domain type='kvm'>
  <name>{{ hostname_with_prefix }}</name>
  <uuid>{{ uuid }}</uuid>
  <memory unit='KiB'>{{ memory }}</memory>
  <currentmemory unit='KiB'>{{ memory }}</currentmemory>
  <vcpu>{{ ncpus }}</vcpu>
  <os>
    <smbios mode='sysinfo'/>
    <type arch='x86_64' machine='pc'>hvm</type>
    <bios useserial='yes' rebootTimeout='5000'/>
  </os>
  <sysinfo type='smbios'>
    <bios>
      <entry name='vendor'>eNovance</entry>
    </bios>
    <system>
      <entry name='manufacturer'>QEMU</entry>
      <entry name='product'>virtualizor</entry>
      <entry name='version'>1.0</entry>
    </system>
  </sysinfo>
  <features>
    <acpi/>
    <apic/>
    <pae/>
  </features>
  <clock offset='utc'/>
  <on_poweroff>restart</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>restart</on_crash>
  <devices>
    <emulator>/usr/bin/qemu-system-x86_64</emulator>
{% for disk in disks %}
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source file='{{ disk.path }}'/>
      <target dev='{{ disk.name }}' bus='virtio'/>
{% if disk.boot_order is defined %}
      <boot order='{{ disk.boot_order }}'/>
{% endif %}
    </disk>
{% endfor %}
{% if is_install_server is defined %}
    <disk type='file' device='disk'>
      <driver name='qemu' type='raw'/>
      <source
        file='/var/lib/libvirt/images/{{
          hostname_with_prefix }}_cloud-init.iso'/>
      <target dev='vdz' bus='virtio'/>
    </disk>
{% endif %}
{% for nic in nics %}
{% if nic.network_name is defined %}
    <interface type='network'>
      <mac address='{{ nic.mac }}'/>
      <source network='{{ nic.network_name }}'/>
      <model type='virtio'/>
{% if nic.boot_order is defined %}
      <boot order='{{ nic.boot_order }}'/>
{% endif %}
    </interface>
{% endif %}
{% endfor %}
    <serial type='pty'>
      <target port='0'/>
    </serial>
    <console type='pty'>
      <target type='serial' port='0'/>
    </console>
    <input type='mouse' bus='ps2'/>
    <graphics type='vnc' port='-1' autoport='yes'/>
    <video>
      <model type='cirrus' vram='9216' heads='1'/>
    </video>
  </devices>
</domain>
    """
    host_libvirt_image_dir = "/var/lib/libvirt/images"
    user_data_template_string = """#cloud-config
users:
 - default
 - name: jenkins
   ssh-authorized-keys:
{% for ssh_key in ssh_keys %}   - {{ ssh_key|trim }}
{% endfor %}
 - name: root
   ssh-authorized-keys:
{% for ssh_key in ssh_keys %}   - {{ ssh_key|trim }}
{% endfor %}

write_files:
  - path: /etc/resolv.conf
    content: |
      nameserver 8.8.8.8
      options rotate timeout:1
  - path: /etc/sudoers.d/jenkins-cloud-init
    permissions: 0440
    content: |
      Defaults:jenkins !requiretty
      jenkins ALL=(ALL) NOPASSWD:ALL
  - path: /etc/sysconfig/network-scripts/ifcfg-eth0
    content: |
      DEVICE=eth0
      BOOTPROTO=none
      ONBOOT=yes
      IPADDR={{ ip }}
      NETWORK={{ network }}
      NETMASK={{ netmask }}
# Do not set the default GW to avoid conflict
# with the outgoing route on eth1
#      GATEWAY={{ gateway }}
  - path: /etc/sysconfig/network-scripts/ifcfg-eth1
    content: |
      DEVICE=eth1
      BOOTPROTO=dhcp
      ONBOOT=yes
  - path: /etc/sysconfig/network
    content: |
      NETWORKING=yes
      NOZEROCONF=no
      HOSTNAME={{ hostname }}
#      GATEWAY={{ gateway }}
  - path: /etc/sysctl.conf
    content: |
      net.ipv4.ip_forward = 1

runcmd:
 - /usr/sbin/sysctl -p
 - /usr/sbin/iptables -t nat -A POSTROUTING -o eth1 -j MASQUERADE
 - /bin/rm -f /etc/yum.repos.d/*.repo
 - /usr/bin/systemctl restart network

"""
    meta_data_template_string = """
instance-id: id-install-server
local-hostname: {{ hostname }}

"""

    def __init__(self, hypervisor, conf, definition, install_server_info):
        self.hypervisor = hypervisor
        self.conf = conf
        self.hostname = definition['hostname']
        self.hostname_with_prefix = definition['hostname_with_prefix']
        self.meta = {'hostname': definition['hostname'],
                     'hostname_with_prefix':
                         definition['hostname_with_prefix'],
                     'uuid': str(uuid.uuid1()),
                     'memory': 4194304,
                     'ncpus': 1,
                     'cpus': [], 'disks': [], 'nics': []}

        for k in ('uuid', 'serial', 'product_name',
                  'memory', 'ncpus', 'is_install_server'):
            if k not in definition:
                continue
            self.meta[k] = definition[k]

        if definition['profile'] == 'install-server':
            logging.info("  This is the install-server")
            self.meta['is_install_server'] = True
            definition['disks'] = [
                {'name': 'vda',
                 'size': '30G',
                 'clone_from':
                     '/var/lib/libvirt/images/install-server-%s.img.qcow2' %
                         install_server_info['version']}
            ]
            definition['nics'].append({
                'mac': install_server_info['mac'],
                'network_name': conf.public_network
            })
            self.prepare_cloud_init(
                ip=install_server_info['ip'],
                network=install_server_info['network'],
                netmask=install_server_info['netmask'],
                gateway=install_server_info['gateway'])

        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        self.template = env.from_string(Host.host_template_string)

        self.register_disks(definition)
        self.register_nics(definition)

        self.meta['nics'][0]['boot_order'] = 2
        self.meta['disks'][0]['boot_order'] = 1

    def prepare_cloud_init(self, ip, network, netmask, gateway):

        ssh_key_file = self.conf.pub_key_file
        meta = {
            'ssh_keys': open(ssh_key_file).readlines(),
            'hostname': self.hostname,
            'ip': ip,
            'network': network,
            'netmask': netmask,
            'gateway': gateway
        }
        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        contents = {
            'user-data': env.from_string(Host.user_data_template_string),
            'meta-data': env.from_string(Host.meta_data_template_string)}
        # TODO(Gonéri): use mktemp
        data_dir = "/tmp/%s_data" % self.hostname_with_prefix
        self.hypervisor.call("mkdir", "-p", data_dir)
        for name in sorted(contents):
            fd = tempfile.NamedTemporaryFile()
            fd.write(contents[name].render(meta))
            fd.seek(0)
            fd.flush()
            self.hypervisor.push(fd.name, data_dir + '/' + name)

        self.hypervisor.call(
            'genisoimage', '-quiet', '-output',
            "%s/%s_cloud-init.iso" % (
                Host.host_libvirt_image_dir,
                self.hostname_with_prefix),
            '-volid', 'cidata', '-joliet', '-rock',
            data_dir + '/user-data', data_dir + '/meta-data')

    def register_disks(self, definition):
        cpt = 0
        for info in definition['disks']:
            filename = "%s-%03d.qcow2" % (self.hostname_with_prefix, cpt)
            if 'clone_from' in info:
                self.hypervisor.call(
                    'qemu-img', 'create', '-q', '-f', 'qcow2',
                    '-b', info['clone_from'],
                    Host.host_libvirt_image_dir + '/' + filename,
                    info['size'])
                self.hypervisor.call(
                    'qemu-img', 'resize', '-q',
                    Host.host_libvirt_image_dir + '/' + filename,
                    canical_size(info['size']))
            else:
                self.hypervisor.call(
                    'qemu-img', 'create', '-q', '-f', 'qcow2',
                    Host.host_libvirt_image_dir + '/' + filename,
                    canical_size(info['size']))

            info.update({
                'name': 'vd' + string.ascii_lowercase[cpt],
                'path': Host.host_libvirt_image_dir + '/' + filename})
            self.meta['disks'].append(info)
            cpt += 1

    def register_nics(self, definition):
        i = 0

        for info in definition['nics']:
            self.meta['nics'].append({
                'mac': info.get('mac', random_mac()),
                'name': info.get('name', 'noname%i' % i),
                'network_name': info.get(
                    'network_name', '%s_sps' % self.conf.prefix)})
            i += 1

    def dump_libvirt_xml(self):
        return self.template.render(self.meta)


class Network(object):
    network_template_string = """
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

    def __init__(self, name, definition):
        self.name = name
        self.meta = {
            'name': name,
            'uuid': str(uuid.uuid1()),
            'mac': random_mac(),
            'bridge_name': 'virbr%d' % random.randrange(0, 0xffffffff)}

        for k in ('uuid', 'mac', 'ips', 'dhcp'):
            if k not in definition:
                continue
            self.meta[k] = definition[k]

        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        self.template = env.from_string(Network.network_template_string)

    def dump_libvirt_xml(self):
        return self.template.render(self.meta)


def get_install_server_info(hosts_definition):
    for hostname, definition in six.iteritems(hosts_definition['hosts']):
        if definition.get('profile', '') == 'install-server':
            break

    logging.info("install-server (%s)" % (hostname))
    admin_nic_info = definition['nics'][0]
    network = ipaddress.ip_network(
        unicode(
            admin_nic_info['network'] + '/' + admin_nic_info['netmask']))
    admin_nic_info = definition['nics'][0]
    return {
        'mac': admin_nic_info.get('mac', random_mac()),
        'hostname': hostname,
        'ip': admin_nic_info['ip'],
        'gateway': str(network.network_address + 1),
        'netmask': str(network.netmask),
        'network': str(network.network_address),
        'version': hosts_definition.get('version', 'RH7.0-I.1.2.1'),
    }


def main(argv=sys.argv[1:]):
    conf = get_conf(argv)
    hosts_definition = yaml.load(open(conf.input_file, 'r'))
    hypervisor = Hypervisor(conf)
    install_server_info = get_install_server_info(hosts_definition)
    hypervisor.create_networks(conf, install_server_info)

    hosts = hosts_definition['hosts']
    existing_hosts = ([n.name() for n in hypervisor.conn.listAllDomains()])
    for hostname in sorted(hosts):
        definition = hosts[hostname]
        hostname_with_prefix = "%s_%s" % (conf.prefix, hostname)
        definition['hostname'] = hostname
        definition['hostname_with_prefix'] = hostname_with_prefix
        exists = hostname_with_prefix in existing_hosts
        if exists and conf.replace:
            dom = hypervisor.conn.lookupByName(hostname_with_prefix)
            if dom.info()[0] in [libvirt.VIR_DOMAIN_RUNNING,
                                 libvirt.VIR_DOMAIN_PAUSED]:
                dom.destroy()
            if dom.info()[0] in [libvirt.VIR_DOMAIN_SHUTOFF]:
                dom.undefine()
            exists = False
        if not exists:
            host = Host(hypervisor, conf, definition, install_server_info)
            hypervisor.conn.defineXML(host.dump_libvirt_xml())
            dom = hypervisor.conn.lookupByName(hostname_with_prefix)
            dom.create()
        else:
            logging.info("a host called %s is already defined, skipping "
                         "(see: --replace)." % hostname_with_prefix)

    ip = hypervisor.wait_for_install_server(
        hypervisor, install_server_info['mac'])

    logging.info("Install-server up and running with IP: %s" % ip)


if __name__ == '__main__':
    main()