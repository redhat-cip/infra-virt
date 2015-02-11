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

import dumpelastic
from tests.data.elasticdatas import mockdata

import mock
import testtools


class TestDumpElastic(testtools.TestCase):

    @mock.patch("dumpelastic.requests")
    def test_get_indices(self, m_request):
        m_return_value = mock.Mock()
        m_return_value.json.return_value = ['logstash-2015.02.09', 'noop']
        m_request.get.return_value = m_return_value
        indices = dumpelastic._get_indices("url")
        self.assertEqual(['logstash-2015.02.09'], indices)

    @mock.patch("dumpelastic.requests")
    def test_dump_elasticsearch(self, m_request):
        m_return_value = mock.Mock()
        m_return_value.json = mock.MagicMock(side_effect=[mockdata.data1,
                                                          mockdata.data2])
        m_request.get.return_value = m_return_value

        dumpelastic._save_docs = mock.Mock()
        dumpelastic._dump_elasticsearch("url", "output_dir")
