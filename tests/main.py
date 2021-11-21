import json
import os
import shutil
import glob
import datetime
import sys
import tempfile

import gi

gi.require_version("OSTree", "1.0")

from fastapi.testclient import TestClient
from gi.repository import Gio, OSTree
from lxml import etree

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

workspace = None
client = None


def _get_expected_json_result(test_name):
    path = os.path.join("tests", "results", f"{test_name}.json")
    with open(path) as result:
        return json.load(result)


def _get_expected_xml_result(test_name):
    path = os.path.join("tests", "results", f"{test_name}.xml")
    with open(path) as result:
        return etree.fromstring(result.read().encode("utf-8"))


def setup_module():
    global workspace, client

    workspace = tempfile.TemporaryDirectory()

    installation_path = os.path.join(workspace.name, "flatpak")
    repo_path = os.path.join(installation_path, "repo")

    os.mkdir(installation_path)
    os.environ["FLATPAK_USER_DIR"] = installation_path

    file = Gio.File.new_for_path(repo_path)
    repo = OSTree.Repo.new(file)
    repo.create(OSTree.RepoMode.BARE, None)
    remote_path = os.path.join(os.getcwd(), "tests/ostree/repo")
    repo.remote_add("flathub", f"file://{remote_path}")

    for i, test_stats_json in enumerate(
        sorted(glob.glob("tests/stats/*.json"), reverse=True)
    ):
        date = datetime.date.today() - datetime.timedelta(days=i)
        stats_file = os.path.join(workspace.name, date.strftime("%Y/%m/%d.json"))
        os.makedirs(os.path.dirname(stats_file), exist_ok=True)
        print(f"Copy {test_stats_json} to {stats_file}")
        shutil.copy(test_stats_json, stats_file)

    from app import config

    config.settings.appstream_repos = "tests/appstream"
    config.settings.datadir = "tests/data"
    config.settings.stats_baseurl = "file://" + workspace.name

    from app import main

    with TestClient(main.app) as client_:
        client = client_


def teardown_module():
    workspace.cleanup()


def test_update():
    response = client.post("/update")
    assert response.status_code == 200


def test_apps_by_category():
    response = client.get("/category/Game")
    assert response.status_code == 200
    assert response.json() == _get_expected_json_result("test_apps_by_category")


def test_apps_by_non_existent_category():
    response = client.get("/category/NonExistent")
    assert response.status_code == 422


def test_appstream_by_appid():
    response = client.get("/appstream/org.sugarlabs.Maze")
    assert response.status_code == 200
    assert response.json() == _get_expected_json_result("test_appstream_by_appid")


def test_appstream_by_non_existent_appid():
    response = client.get("/appstream/NonExistent")
    assert response.status_code == 404
    assert response.json() == None


def test_search_query_by_appid():
    response = client.get("/search/org.sugarlabs.Maze")
    assert response.status_code == 200
    assert response.json() == _get_expected_json_result("test_search_query_by_appid")


def test_search_query_by_name():
    response = client.get("/search/Maze")
    assert response.status_code == 200
    assert response.json() == _get_expected_json_result("test_search_query_by_appid")


def test_search_query_by_summary():
    response = client.get("/search/maze%20game")
    assert response.status_code == 200
    assert response.json() == _get_expected_json_result("test_search_query_by_appid")


def test_search_query_by_description():
    response = client.get("/search/finding%20your%20way%20out")
    assert response.status_code == 200
    assert response.json() == _get_expected_json_result("test_search_query_by_appid")


def test_search_query_by_non_existent():
    response = client.get("/search/NonExistent")
    assert response.status_code == 200
    assert response.json() == _get_expected_json_result(
        "test_search_query_by_non_existent"
    )


def test_collection_by_recently_updated():
    response = client.get("/collection/recently-updated")
    assert response.status_code == 200
    assert response.json() == _get_expected_json_result(
        "test_collection_by_recently_updated"
    )


def test_collection_by_one_recently_updated():
    response = client.get("/collection/recently-updated/1")
    assert response.status_code == 200
    assert response.json() == _get_expected_json_result(
        "test_collection_by_one_recently_updated"
    )


def test_feed_by_recently_updated():
    response = client.get("/feed/recently-updated")
    assert response.status_code == 200

    feed = etree.fromstring(response.text.encode("utf-8"))
    expected = _get_expected_xml_result("test_feed_by_recently_updated")

    # Remove runtime-generated dates
    for component in [feed, expected]:
        channel = component.find("channel")
        date = channel.find("lastBuildDate")
        channel.remove(date)

    assert etree.tostring(feed) == etree.tostring(expected)


def test_feed_by_new():
    response = client.get("/feed/new")
    assert response.status_code == 200

    feed = etree.fromstring(response.text.encode("utf-8"))
    expected = _get_expected_xml_result("test_feed_by_new")

    # Remove runtime-generated dates
    for component in [feed, expected]:
        channel = component.find("channel")
        date = channel.find("lastBuildDate")
        channel.remove(date)

    assert etree.tostring(feed) == etree.tostring(expected)


def test_picked_apps():
    response = client.get("/picks/apps")
    assert response.status_code == 200


def test_picked_games():
    response = client.get("/picks/games")
    assert response.status_code == 200


def test_picked_non_existent():
    response = client.get("/picks/NonExistent")
    assert response.status_code == 404
    assert response.json() == None


def test_popular():
    response = client.get("/popular")
    assert response.status_code == 200
    assert response.json() == _get_expected_json_result("test_popular")


def test_status():
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json() == _get_expected_json_result("test_status")


def test_list_appstream():
    response = client.get("/appstream")
    assert response.status_code == 200
    assert response.json() == _get_expected_json_result("test_list_appstream")


def test_summary_by_id():
    response = client.get("/summary/org.sugarlabs.Maze")
    assert response.status_code == 200
    assert response.json() == _get_expected_json_result("test_summary_by_appid")


def test_summary_by_non_existent_id():
    response = client.get("/summary/does.not.exist")
    assert response.status_code == 404
    assert response.json() == None


def test_stats():
    response = client.get("/stats")
    expected = {}
    expected["countries"] = {"AD": 30, "BR": 60}
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    day_before_yesterday = today - datetime.timedelta(days=2)
    expected["delta_downloads"] = {}
    expected["delta_downloads"][day_before_yesterday.isoformat()] = 15
    expected["delta_downloads"][yesterday.isoformat()] = 15
    expected["delta_downloads"][today.isoformat()] = 15
    expected["downloads"] = {}
    expected["downloads"][day_before_yesterday.isoformat()] = 10
    expected["downloads"][yesterday.isoformat()] = 10
    expected["downloads"][today.isoformat()] = 10
    expected["updates"] = {}
    expected["updates"][day_before_yesterday.isoformat()] = 5
    expected["updates"][yesterday.isoformat()] = 5
    expected["updates"][today.isoformat()] = 5

    assert response.status_code == 200
    assert response.json() == expected


def test_app_stats_by_id():
    response = client.get("/stats/org.sugarlabs.Maze")
    assert response.status_code == 200
    assert response.json() == _get_expected_json_result("test_app_stats")


def test_app_stats_by_non_existent_id():
    response = client.get("/stats/does.not.exist")
    assert response.status_code == 404
    assert response.json() == None
