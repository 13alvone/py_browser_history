#!/usr/local/bin/python3

import os
import re
import subprocess
import tempfile
import shutil
import sqlite3
import argparse
import datetime


browser_paths = {}
default_paths = {
    "safari": "~/Library/Safari/History.db",
    "firefox": "~/Library/Application Support/Firefox/Profiles/",
    "chrome": "~/Library/Application Support/Google/Chrome/Default/History",
    "edge": "~/Library/Application Support/Microsoft Edge/Default/History",
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--event_count', help='Count by browser', default=100, type=str, required=False)
    arguments = parser.parse_args()
    return arguments


def get_users():
    _data = subprocess.check_output(('dscl', '.', '-ls', '/Users'))
    return [x for x in _data.decode('utf-8').split('\n') if os.path.exists(f"/Users/{x}") and x != ""]


def create_temporary_copy(path):
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, 'temp_file_name')
    shutil.copy2(path, temp_path)
    return temp_path


def populate_browser_paths(_users):
    global default_paths, browser_paths
    for user in _users:
        for default_path in default_paths:
            if default_path != f"firefox" and default_paths[default_path].replace("~", f"/Users/{user}"):
                browser_paths[default_paths[default_path].replace("~", f"/Users/{user}")] = f"{default_path}"
            else:
                for _root, _dirs, _files in os.walk(default_paths[default_path].replace("~", f"/Users/{user}")):
                    for _dir in _dirs:
                        if os.path.exists(f"{_root}{_dir}/places.sqlite"):
                            browser_paths[f"{_root}{_dir}/places.sqlite"] = default_path


def create_connection(db_file):
    try:
        return sqlite3.connect(db_file)
    except Exception as e:
        print(e)
        return None


def date_from_webkit(webkit_timestamp):
    epoch_start = datetime.datetime(1601, 1, 1)
    delta = datetime.timedelta(microseconds=int(webkit_timestamp))
    return epoch_start + delta


def date_from_firefox(firefox_timestamp):
    epoch_start = datetime.datetime(1970, 1, 1)
    delta = datetime.timedelta(microseconds=int(firefox_timestamp))
    return epoch_start + delta


def date_from_cocoa(cocoa_timestamp):
    unix = datetime.datetime(1970, 1, 1)  # UTC
    cocoa = datetime.datetime(2001, 1, 1)  # UTC
    delta = cocoa - unix  # timedelta instance
    timestamp = datetime.datetime.fromtimestamp(int(cocoa_timestamp)) + delta
    return timestamp.strftime('%Y-%m-%d %H:%M:%S')


def execute_sql(_browser_path, _sql_query, _browser):
    temp_sql_obj = create_connection(create_temporary_copy(_browser_path))
    cur = temp_sql_obj.cursor().execute(_sql_query)
    if re.search(r"\/Users\/(.*?)\/", _browser_path):
        action_user = re.search(r"\/Users\/(.*?)\/", _browser_path).group(1)
    else:
        action_user = "Unknown"
    for row in cur.fetchall():
        url = row[0].replace(f".", f"[.]").replace(f":", f"[:]")
        visit_count = row[1]
        visit_time = row[2]
        if _browser == "chrome" or _browser == "edge":
            visit_time = date_from_webkit(visit_time)
        elif _browser == "firefox":
            visit_time = date_from_firefox(visit_time)
        elif _browser == "safari":
            visit_time = date_from_cocoa(visit_time)
        print(f"{visit_time}|{visit_count}|{url}|{_browser}|{action_user}")


def main():
    global browser_paths
    args = parse_args()
    sql_limit = parse_args().event_count if args else sql_limit
    populate_browser_paths(get_users())
    for browser_path in browser_paths:
        if browser_paths[browser_path] == "firefox":
            sql_query = f"SELECT url, visit_count, last_visit_date " \
                        f"FROM moz_places " \
                        f"ORDER BY last_visit_date " \
                        f"DESC LIMIT {sql_limit};"
            execute_sql(browser_path, sql_query, f"firefox")
        elif browser_paths[browser_path] == "safari":
            sql_query = f"SELECT history_items.url, history_items.visit_count, " \
                        f"history_visits.visit_time " \
                        f"FROM history_items " \
                        f"INNER JOIN history_visits on history_items.id=history_visits.history_item " \
                        f"ORDER BY history_visits.visit_time " \
                        f"DESC LIMIT {sql_limit};"
            execute_sql(browser_path, sql_query, f"safari")
        elif browser_paths[browser_path] == "edge":
            sql_query = f"SELECT url, visit_count, last_visit_time " \
                        f"FROM urls " \
                        f"ORDER BY last_visit_time " \
                        f"DESC LIMIT {sql_limit};"
            execute_sql(browser_path, sql_query, f"edge")
        elif browser_paths[browser_path] == "chrome":
            sql_query = f"SELECT url, visit_count, last_visit_time " \
                        f"FROM urls " \
                        f"ORDER BY last_visit_time " \
                        f"DESC LIMIT {sql_limit};"
            execute_sql(browser_path, sql_query, f"chrome")


if __name__ == "__main__":
    main()
