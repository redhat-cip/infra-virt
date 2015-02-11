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

data1 = {u'hits': {u'hits': [{u'_score': 1.0, u'_type': u'fluentd',
                              u'_id': u'4',
                              u'_source': {u'host': u'host2',
                                           u'message': u'message1'},
                   u'_index': u'logstash-2015.02.09'},
                  {u'_score': 1.0, u'_type': u'fluentd', u'_id': u'5',
                   u'_source': {u'host': u'host2', u'message': u'message2'},
                   u'_index': u'logstash-2015.02.09'},
                  {u'_score': 1.0, u'_type': u'fluentd', u'_id': u'1',
                   u'_source': {u'host': u'host1', u'message': u'message1'},
                   u'_index': u'logstash-2015.02.09'},
                  {u'_score': 1.0, u'_type': u'fluentd', u'_id': u'2',
                   u'_source': {u'host': u'host1', u'message': u'message2'},
                   u'_index': u'logstash-2015.02.09'},
                  {u'_score': 1.0, u'_type': u'fluentd', u'_id': u'10000',
                   u'_source': {u'host': u'host2', u'message': u'message2'},
                   u'_index': u'logstash-2015.02.09'},
                  {u'_score': 1.0, u'_type': u'fluentd', u'_id': u'3',
                   u'_source': {u'host': u'host1', u'message': u'message2'},
                   u'_index': u'logstash-2015.02.09'}],
             u'total': 6, u'max_score': 1.0},
        u'_shards': {u'successful': 5, u'failed': 0, u'total': 5},
        u'took': 3, u'timed_out': False}

data2 = {u'hits': {u'hits': [], u'total': 6, u'max_score': 1.0},
         u'_shards': {u'successful': 5, u'failed': 0, u'total': 5},
         u'took': 3, u'timed_out': False}
