import datetime
import json
from collections import defaultdict
from urllib.parse import urlparse, urlunparse
from typing import Dict, List, Optional

import requests

from . import config
from . import db


StatsType = Dict[str, Dict[str, List[int]]]
POPULAR_ITEMS_NUM = 30
POPULAR_DAYS_NUM = 7


def get_stats_for_date(
    date: datetime.date, session: requests.Session
) -> Optional[StatsType]:
    stats_json_url = urlparse(
        config.settings.stats_baseurl + date.strftime("/%Y/%m/%d.json")
    )
    if stats_json_url.scheme == "file":
        try:
            with open(stats_json_url.path, "r") as stats_file:
                stats = json.load(stats_file)
        except FileNotFoundError:
            return None
        return stats["refs"]
    redis_key = f"stats:date:{date.isoformat()}"
    stats_txt = db.redis_conn.get(redis_key)
    if stats_txt is None:
        response = session.get(urlunparse(stats_json_url))
        if response.status_code == 404:
            return None
        response.raise_for_status()
        stats = response.json()
        if date == datetime.date.today():
            expire = 60 * 60
        else:
            expire = 24 * 60 * 60
        db.redis_conn.set(redis_key, json.dumps(stats), ex=expire)
    else:
        stats = json.loads(stats_txt)
    return stats["refs"]


def get_stats_for_period(sdate: datetime.date, edate: datetime.date) -> StatsType:
    totals: StatsType = {}
    with requests.Session() as session:
        for i in range((edate - sdate).days + 1):
            date = sdate + datetime.timedelta(days=i)
            stats = get_stats_for_date(date, session)
            if stats is None:
                continue
            for app_id, app_stats in stats.items():
                if app_id not in totals:
                    totals[app_id] = {}
                app_totals = totals[app_id]
                for arch, downloads in app_stats.items():
                    if arch not in app_totals:
                        app_totals[arch] = [0, 0]
                    app_totals[arch][0] += downloads[0]
                    app_totals[arch][1] += downloads[1]
    return totals


def _sort_key(
    app_stats: Dict[str, List[int]], for_arches: Optional[List[str]] = None
) -> int:
    new_dls = 0
    for arch, dls in app_stats.items():
        if for_arches is not None and arch not in for_arches:
            continue
        new_dls += dls[0] - dls[1]
    return new_dls


def _is_app(app_id: str) -> bool:
    return "/" not in app_id


def get_popular(days: Optional[int]):
    if days is None:
        days = POPULAR_DAYS_NUM

    edate = datetime.date.today()
    sdate = edate - datetime.timedelta(days=days - 1)
    redis_key = f"popular:{sdate}-{edate}"

    if popular := db.get_json_key(redis_key):
        return popular

    stats = get_stats_for_period(sdate, edate)
    sorted_apps = sorted(
        filter(lambda a: _is_app(a[0]), stats.items()),
        key=lambda a: _sort_key(a[1]),
        reverse=True,
    )

    popular = [k for k, v in sorted_apps[:POPULAR_ITEMS_NUM]]
    db.redis_conn.set(redis_key, json.dumps(popular), ex=60 * 60)
    return popular


def update():
    stats_dict = defaultdict(lambda: {})

    days = 30

    edate = datetime.date.today()
    sdate = edate - datetime.timedelta(days=days - 1)

    stats = get_stats_for_period(sdate, edate)

    for appid, dict in stats.items():
        # Index 0 is install and update count index 1 would be the update count
        stats_dict[appid]["downloads_last_month"] = sum([i[0] for i in dict.values()])

    db.redis_conn.mset(
        {f"app_stats:{appid}": json.dumps(stats_dict[appid]) for appid in stats_dict}
    )
