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

import argparse
import os
import sys

import requests


def _save_docs(docs, output_dir):
    """Save the documents in their respective log file.

    :param docs: list of json documents
    :type docs: list
    :param output_dir: path of the directory to store the logs.
    :type output_dir: str
    :return: None
    """

    files_already_open = {}
    for doc in docs:
        if doc["_source"]["host"] not in files_already_open:
            file_log_path = "%s/%s" % (output_dir, doc["_source"]["host"])
            log_file = open(file_log_path, "a")
            files_already_open[doc["_source"]["host"]] = log_file
        log_file = files_already_open.get(doc["_source"]["host"])
        del doc["_source"]["host"]
        log_file.write(str(doc["_source"]) + "\n")

    for log_file in files_already_open:
        files_already_open[log_file].close()


def _get_indices(url):

    json_indices = requests.get("%s/_aliases?pretty" % url).json()
    indices = [indice for indice in json_indices
               if indice.startswith("logstash")]
    indices.sort()

    return indices


def _dump_elasticsearch(url, output_dir, paging=10000):
    """Dump elasticsearch database.

    :param url: url of elasticsearch rest api
    :type url: str
    :param output_dir: path of the directory to store the datas
    :type output_dir: str
    :param paging: number of documents to request per query
    :type: int
    :return: None
    """

    indices = _get_indices(url)

    for indice in indices:
        offset = 0

        if not os.path.exists("%s/%s" % (output_dir, indice)):
            os.makedirs("%s/%s" % (output_dir, indice))

        while True:
            docs_url = "%s/%s/fluentd/_search?from=%s&size=%s&pretty" %\
                       (url, indice, offset, paging)
            json_docs = requests.get(docs_url).json()
            if not json_docs["hits"]["hits"]:
                break
            _save_docs(json_docs["hits"]["hits"], "%s/%s" %
                      (output_dir, indice))
            offset += paging


def _verify_server_running(url):
    try:
        requests.get(url)
    except requests.exceptions.MissingSchema:
        print("Invalid url '%s'." % url)
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("Elasticsearch '%s' not running." % url)
        sys.exit(1)


def _verify_output_dir(output_dir):
    if not os.path.exists(output_dir):
        print("'%s' does not exist." % output_dir)
        sys.exit(1)


def main():
    cli_parser = argparse.ArgumentParser(
        description='Dump elasticsearch database into a directory')
    cli_parser.add_argument('--url',
                            default="http://localhost:9200",
                            help='The elasticsearch rest api url.')
    cli_parser.add_argument('--output-dir',
                            default="/var/log/elasticdump",
                            help='The output directory of the dump.')
    cli_arguments = cli_parser.parse_args()

    _verify_server_running(cli_arguments.url)
    _verify_output_dir(cli_arguments.output_dir)

    _dump_elasticsearch(cli_arguments.url, cli_arguments.output_dir)

if __name__ == '__main__':
    main()
