#!/usr/bin/env python

"""Palantir: JIRA CLI reporting tool to make your life easier as a project controller"""

__author__      = "Sergej Braznikov"
__copyright__   = "Copyright 2016, Sergej Braznikov"


import yaml
import argparse
import requests
import json
import urllib

from tabulate import tabulate
from termcolor import colored
from datetime import date, timedelta


def merge_dicts(*dict_args):
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def get_week_days(year, week):
    d = date(year, 1, 1)
    if(d.weekday() > 3):
        d = d + timedelta(7-d.weekday())
    else:
        d = d - timedelta(d.weekday())
    dlt = timedelta(days = (week-1) * 7)
    return d + dlt,  d + dlt + timedelta(days=6)


def print_fatal(message):
    print colored("[FATAL]: %s" % message, "red")


def print_warning(message):
    print colored("[WARNING]: %s" % message, "yellow")


def print_info(message):
    print colored("[INFO]: %s" % message, "green")


def print_url(jira_url, jql):
    print "%s%s/issues/?jql=%s%s" % ("\n", jira_url, urllib.quote(jql, safe=''), "\n")


def get_jira_data(url, user, password, jql, limits):
    dump = []
    url = '%s/rest/api/2/search/' % url
    for limit in limits:
        payload = {"jql": "%s" % jql, "startAt": "%s" % limit, "maxResults": 1000,
                   "fields": ["*all", "-comment", "-description"]}
        headers = {'content-type': 'application/json'}
        r = requests.post(url, auth=(user, password),
                          data=json.dumps(payload),
                          headers=headers, verify=False)
        issues = json.loads(r.text)['issues']
        if limit == 0:
            dump = issues
        else:
            for issue in issues:
                dump.insert(0, issue)
    return dump


def print_report(jira_url, name, reports, query, tables, filters, data):
    def apply_filters(filters, item):
        def get_name(v):
            if isinstance(v, dict) and v.has_key('name'):
                return v['name']
            return v
        issue = {k:v for k, v in item.items() if k in filters['issue']}
        fields = {k:get_name(v) for k, v in item['fields'].items() if k in filters['fields']}
        timetracking = {k:v for k, v in item['fields']['timetracking'].items() if k in filters['timetracking']}
        return merge_dicts(issue, fields, timetracking)

    def short_report(name, query, tickets):
        count = len(tickets)
        message = "%s %s" % (name, count)
        if len(tickets) > 0:
            print_fatal(message)
            print_url(jira_url, query)
        else:
            print_info(message)

    def times_report(fields, tickets):
        for issue in tickets:
            for name, val in issue.iteritems():
                if name in fields and val:
                    fields[name] += val
        for key, val in fields.iteritems():
            fields[key] = val / 60 / 60 / 8
        table_times = []
        for key, val in fields.iteritems():
            table_times.insert(0, [key, val])
        print tabulate(table_times, headers=['Time', 'PD'])
        print "\n"

    def tasks_report(table_fields, states, tasks):
        fields = table_fields.copy()
        for issue in tasks:
            for status in states:
                if issue['status'] in status.values():
                    fields[status.keys()[0]] += 1
        table_tasks = []
        for key, val in fields.iteritems():
            table_tasks.insert(0, [key, val])
        print tabulate(table_tasks, headers=['Tasks', 'Count'])
        print "\n"

    if 'short' in reports:
        short_report(name, query, [apply_filters(filters, item) for item in data])
    if 'times' in reports:
        times_report(tables['times'], [apply_filters(filters, item) for item in data])
    if 'tasks' in reports:
        tasks_report(tables['tasks'], filters['states'], [apply_filters(filters, item) for item in data])


def exec_jqls(data):
    [print_report(data[0]['url'],
                  jql['name'],
                  jql['reports'],
                  jql['query'],
                  data[0]['tables'],
                  data[0]['filters'],
                  get_jira_data(data[0]['url'],
                                data[0]['user'],
                                data[0]['password'],
                                jql['query'],
                                [1]))
     for jql in data[0]['jqls']]


def get_config(path):
    with open(path, 'r') as stream:
        try:
            return yaml.load(stream)
        except yaml.YAMLError as exc:
            print exc


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="+", help="path to the config file")
    args = parser.parse_args()
    exec_jqls(get_config(args.path[0]))
