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

HOST = """
<domain type='kvm'>
  <name>{{ hostname_with_prefix }}</name>
  <uuid>{{ uuid }}</uuid>
  <memory unit='KiB'>{{ memory }}</memory>
  <currentmemory unit='KiB'>{{ memory }}</currentmemory>
  <vcpu>{{ ncpus }}</vcpu>
  <cpu mode='host-passthrough'>
  </cpu>
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
    <emulator>{{ emulator }}</emulator>
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

HOST_LIBVIRT_IMAGES_LOCATION = "/var/lib/libvirt/images"

USER_DATA = """
#cloud-config
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
{% for nic in nics %}
  - path: /etc/sysconfig/network-scripts/ifcfg-{{ nic.name }}
    content: |
      DEVICE={{ nic.name }}
      ONBOOT=yes
{% if nic.ip is defined %}
      BOOTPROTO=none
      IPADDR={{ nic.ip }}
      NETWORK={{ nic.network }}
      NETMASK={{ nic.netmask }}
{% if nic.gateway is defined %}
      GATEWAY={{ nic.gateway }}
{% endif %}
{% else %}
      BOOTPROTO=dhcp
{% endif %}
{% endfor %}
  - path: /etc/sysconfig/network
    content: |
      NETWORKING=yes
      NOZEROCONF=no
      HOSTNAME={{ hostname }}
  - path: /etc/sysctl.conf
    content: |
      net.ipv4.ip_forward = 1
  - path: /root/.ssh/id_rsa
    permissions: 0400
    owner: root:root
    content: |
        -----BEGIN RSA PRIVATE KEY-----
        MIIEowIBAAKCAQEA47rZ0qSOqzLIspnMFvfwSYsms00nJkmsLHLem/9JsvqM2brk
        0nfUDzr/6BbieH4HoC+GZMnhh21gX0C/nk/fYFLP+0fY2KbRObbCbdZGlOCguMcJ
        QgcKz0sU9mms4+bPcmnil+j8ljP+KjrBDXiZtl6sYj0CnoD3MlVZfHmLI20xa0aO
        CUvjLDsgTjVFhtRDdEHXcl4XHPJ5RKT9sEBlKbhCmI/6O1pNxEGEWvwwQE08+9Xl
        9rJ08/nb/hIuzhTGJdEX/u7jwidxnYbzFyPdgs4jCHDAciqUorlgd/yw6Hs0z2IY
        GxD9CPs6shx8aRmVLGMf+YnOUQHVD1Hi0FrBFwIDAQABAoIBAQDXekZ/DJu+G7hR
        XjsBhKrFO7hrsdYYYV9bU3mVS7I1euNpZXD8QMvTeXUI6xZxAnc+t5lHpsoSNYkZ
        uA9XwaXP46vNzQa+wOF55ZcFDNoOJpmNHS+CXV16FUYJfqZLomqpjM0OBjNyAFI/
        LQbcMz/mkqAz+ByRU+ASrTWWFP91jSRSWAO/xmRcgqmh02TWlVJRROS3CsWz9C47
        Ag1diZ4r2d1gFwnc6ZfSTNActLgUNU2NyDsFL4qHipWssGqoclfhsIdL1CLmhTix
        t8tO0QBSw60H2XqQ0Y77MNfEYgdqvp6XRlB+Uw9Qjf3Y0ukA6ekD3BGfTcaNcq4b
        4N1WUmTpAoGBAPYCzaWRcXHCJ/0WAUhggvy1kKbAdEtoJfkS3lva9pPgyRx+cTrW
        98az6NhdD774O3F1GT8RemoX/9JpX0Z2HG3+f0r2vcSqhsyjJSJF6dEU3DMFte+G
        A67iHnmmfelc1tZKrGuqfrGnFeMQgrmj3ugekKAoyeybPXkd7YTC9cidAoGBAOz6
        Bbpmvrqr41TOgZCssFjteBNDvDU9NfHtpkgAx7HYkNp4xaWPwlBBydS6Ubsx5RQJ
        EXf6y5OfCuNkmHTFvubeaG6rg450YKWLO95F5TYfRJdQ6/lkFjhPpsIe9q/QFLP3
        ZOu+nE2ONCIlUKY7cpLOpYPs+RvYBMETYnSBYEBDAoGAI/ra+tkfv2SHFrPOMjiz
        T6R6aHkDSTgNPbVtwf9vSsd4gmtXwiRIjs4nQuWxdNu3Teuzao7y2WtzJeH1ZkfF
        9qxfD6awsH/EQU+nEbEp9kNXxTqTllmCVmSJ0n7wMV47qZG4T/Lanr7yK4hxphb6
        dfZqbpIonitCPWGMKHufGN0CgYB8yCZuAZ4a01nQFTEaSiRNnzVkB326FvIp4vZ0
        4ZxFZIDZ2VBRnoI2Gn45eqaAyIQUabX+FFxP7iYgmJ7ClkGwdZpN9BhA0bz2TnuG
        zg0k05AdkWnAF1iv7BkmDIHfD9Vm8jT9AZByMhf3huiRr6nj7dYvwn9ljvjp5dgo
        +tsA2wKBgF7pLURG7z1TAM3jKikqjs2UUgPBW+Fd9gpzpgVnujoQnC30/aZvUzUL
        ZPICIuMYWuFGC/KCrq/X+pMqH6t9WmpX6SFW3TMjKrPOkqf5m7nJHTiHX+DmBfGr
        bzgHWb/BDGyPxBbv34G6TdlZo64M3pQhz9Yr9DB1QQjkgJpVVds0
        -----END RSA PRIVATE KEY-----
  - path: /var/lib/jenkins/.ssh/id_rsa
    permissions: 0400
    owner: jenkins:jenkins
    content: |
        -----BEGIN RSA PRIVATE KEY-----
        MIIEowIBAAKCAQEA47rZ0qSOqzLIspnMFvfwSYsms00nJkmsLHLem/9JsvqM2brk
        0nfUDzr/6BbieH4HoC+GZMnhh21gX0C/nk/fYFLP+0fY2KbRObbCbdZGlOCguMcJ
        QgcKz0sU9mms4+bPcmnil+j8ljP+KjrBDXiZtl6sYj0CnoD3MlVZfHmLI20xa0aO
        CUvjLDsgTjVFhtRDdEHXcl4XHPJ5RKT9sEBlKbhCmI/6O1pNxEGEWvwwQE08+9Xl
        9rJ08/nb/hIuzhTGJdEX/u7jwidxnYbzFyPdgs4jCHDAciqUorlgd/yw6Hs0z2IY
        GxD9CPs6shx8aRmVLGMf+YnOUQHVD1Hi0FrBFwIDAQABAoIBAQDXekZ/DJu+G7hR
        XjsBhKrFO7hrsdYYYV9bU3mVS7I1euNpZXD8QMvTeXUI6xZxAnc+t5lHpsoSNYkZ
        uA9XwaXP46vNzQa+wOF55ZcFDNoOJpmNHS+CXV16FUYJfqZLomqpjM0OBjNyAFI/
        LQbcMz/mkqAz+ByRU+ASrTWWFP91jSRSWAO/xmRcgqmh02TWlVJRROS3CsWz9C47
        Ag1diZ4r2d1gFwnc6ZfSTNActLgUNU2NyDsFL4qHipWssGqoclfhsIdL1CLmhTix
        t8tO0QBSw60H2XqQ0Y77MNfEYgdqvp6XRlB+Uw9Qjf3Y0ukA6ekD3BGfTcaNcq4b
        4N1WUmTpAoGBAPYCzaWRcXHCJ/0WAUhggvy1kKbAdEtoJfkS3lva9pPgyRx+cTrW
        98az6NhdD774O3F1GT8RemoX/9JpX0Z2HG3+f0r2vcSqhsyjJSJF6dEU3DMFte+G
        A67iHnmmfelc1tZKrGuqfrGnFeMQgrmj3ugekKAoyeybPXkd7YTC9cidAoGBAOz6
        Bbpmvrqr41TOgZCssFjteBNDvDU9NfHtpkgAx7HYkNp4xaWPwlBBydS6Ubsx5RQJ
        EXf6y5OfCuNkmHTFvubeaG6rg450YKWLO95F5TYfRJdQ6/lkFjhPpsIe9q/QFLP3
        ZOu+nE2ONCIlUKY7cpLOpYPs+RvYBMETYnSBYEBDAoGAI/ra+tkfv2SHFrPOMjiz
        T6R6aHkDSTgNPbVtwf9vSsd4gmtXwiRIjs4nQuWxdNu3Teuzao7y2WtzJeH1ZkfF
        9qxfD6awsH/EQU+nEbEp9kNXxTqTllmCVmSJ0n7wMV47qZG4T/Lanr7yK4hxphb6
        dfZqbpIonitCPWGMKHufGN0CgYB8yCZuAZ4a01nQFTEaSiRNnzVkB326FvIp4vZ0
        4ZxFZIDZ2VBRnoI2Gn45eqaAyIQUabX+FFxP7iYgmJ7ClkGwdZpN9BhA0bz2TnuG
        zg0k05AdkWnAF1iv7BkmDIHfD9Vm8jT9AZByMhf3huiRr6nj7dYvwn9ljvjp5dgo
        +tsA2wKBgF7pLURG7z1TAM3jKikqjs2UUgPBW+Fd9gpzpgVnujoQnC30/aZvUzUL
        ZPICIuMYWuFGC/KCrq/X+pMqH6t9WmpX6SFW3TMjKrPOkqf5m7nJHTiHX+DmBfGr
        bzgHWb/BDGyPxBbv34G6TdlZo64M3pQhz9Yr9DB1QQjkgJpVVds0
        -----END RSA PRIVATE KEY-----

runcmd:
 - /usr/sbin/sysctl -p
{% for nic in nics %}{% if nic.nat is defined %}
 - /usr/sbin/iptables -t nat -A POSTROUTING -o {{ nic.name }} -j MASQUERADE
{% endif %}{% endfor %}
 - /bin/rm -f /etc/yum.repos.d/*.repo
 - /usr/bin/systemctl restart network

"""

META_DATA = """
instance-id: {{ hostname }}
local-hostname: {{ hostname }}
"""
