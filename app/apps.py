import re
import json

from . import utils
from . import db


def load_appstream():
    apps_stable = utils.appstream2dict("repo")
    apps_beta = utils.appstream2dict("beta-repo")

    apps = merge_apps(apps_beta, apps_stable)

    current_apps = db.get_apps("stable")
    current_apps_beta = db.get_apps("beta")
    current_categories = db.redis_conn.smembers("categories:index")
    current_developers = db.redis_conn.smembers("developers:index")

    db.initialize()
    with db.redis_conn.pipeline() as p:
        p.delete("categories:index", *current_categories)
        p.delete("developers:index", *current_developers)

        for appid in apps:
            redis_key = f"apps:{appid}"

            clean_html_re = re.compile("<.*?>")
            if "stable" in apps[appid]:
                search_description = re.sub(
                    clean_html_re, "", apps[appid]["stable"]["description"]
                )

                if search_keywords := apps[appid]["stable"].get("keywords"):
                    search_keywords = " ".join(search_keywords)
                else:
                    search_keywords = ""

                fts = {
                    "id": appid,
                    "name": apps[appid]["stable"]["name"],
                    "summary": apps[appid]["stable"]["summary"],
                    "description": search_description,
                    "keywords": search_keywords,
                }
                p.hset(f"fts:{appid}", mapping=fts)
                if categories := apps[appid]["stable"].get("categories"):
                    for category in categories:
                        p.sadd("categories:index", category)
                        p.sadd(f"categories:{category}", redis_key)

                if developer_name := apps[appid]["stable"].get("developer_name"):
                    p.sadd("developers:index", developer_name)
                    p.sadd(f"developers:{developer_name}", redis_key)

            p.set(f"apps:{appid}", json.dumps(apps[appid]))

        for appid in current_apps - set(apps_stable):
            p.delete(
                f"apps:{appid}",
                f"fts:{appid}",
                f"summary:{appid}",
                f"app_stats:{appid}",
            )
            db.redis_search.delete_document(f"fts:{appid}")

        new_apps = set(apps_stable) - current_apps
        if not len(new_apps):
            new_apps = None

        new_apps_beta = set(apps_beta) - current_apps_beta
        if not len(new_apps_beta):
            new_apps_beta = None

        p.delete("apps:index")
        p.sadd("apps:index", *[f"apps:{appid}" for appid in apps_stable])
        p.delete("apps:index_beta")
        p.sadd("apps:index_beta", *[f"apps:{appid}" for appid in apps_beta])
        p.execute()

    return new_apps, new_apps_beta


def merge_apps(apps_beta, apps_stable):
    apps = {}
    for appid in apps_stable:
        apps[appid] = {"stable": apps_stable[appid]}

    for appid in apps_beta:
        if appid not in apps:
            apps[appid] = {"beta": apps_beta[appid]}
        else:
            apps[appid] = {"stable": apps_stable[appid], "beta": apps_beta[appid]}

    return apps


def list_appstream(repo: str = "stable"):
    return sorted(db.get_apps(repo))


def get_recently_updated(limit: int = 100, repo: str = "stable"):
    if repo == "stable":
        zset = db.redis_conn.zrevrange("recently_updated_zset", 0, limit - 1)
    if repo == "beta":
        zset = db.redis_conn.zrevrange("recently_updated_beta_zset", 0, limit - 1)

    return [appid for appid in zset if db.redis_conn.exists(f"apps:{appid}")]


def get_category(category: str, repo: str = "stable"):
    if index := db.redis_conn.smembers(f"categories:{category}"):
        json_appdata = db.redis_conn.mget(index)
        appdata = [json.loads(app) for app in json_appdata]

        return [(app[repo]["id"]) for app in appdata if repo in app]
    else:
        return None


def get_developer(developer: str, repo: str = "stable"):
    if index := db.redis_conn.smembers(f"developers:{developer}"):
        json_appdata = db.redis_conn.mget(index)
        appdata = [json.loads(app) for app in json_appdata]

        return [(app[repo]["id"]) for app in appdata if repo in app]
    else:
        return None


def search(query: str, repo: str = "stable"):
    if results := db.search(query):
        appids = tuple(doc_id.replace("fts", "apps") for doc_id in results)
        apps = [json.loads(x) for x in db.redis_conn.mget(appids)]

        ret = []
        for app in apps:
            if repo in app:
                entry = {
                    "id": app[repo]["id"],
                    "name": app[repo]["name"],
                    "summary": app[repo]["summary"],
                    "icon": app[repo].get("icon"),
                }
                ret.append(entry)

        return ret

    return []
