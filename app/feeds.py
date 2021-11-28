from datetime import datetime
from feedgen.feed import FeedGenerator

from . import db


def generate_feed(
    key: str,
    title: str,
    description: str,
    link: str,
    repo: str,
):
    feed = FeedGenerator()
    feed.title(title)
    feed.description(description)
    feed.link(href=link)
    feed.language("en")

    # get 15, as we might have some that don't exist, due to summary knowing about consale-applications
    appids = db.redis_conn.zrevrange(key, 0, 15, withscores=True)
    app_score_tuple = [
        (db.get_json_key(f"apps:{appid[0]}"), appid[1]) for appid in appids
    ]
    apps = [(item[0][repo], item[1]) for item in app_score_tuple if item[0] is not None]

    for app, timestamp in reversed(apps[:10]):
        if not app.get("name"):
            continue

        entry = feed.add_entry()
        entry.title(app["name"])
        entry.link(href=f"https://flathub.org/apps/details/{app['id']}")

        timestamp = int(timestamp)
        entry_date = datetime.utcfromtimestamp(timestamp).strftime(
            "%a, %d %b %Y %H:%M:%S"
        )
        entry.pubDate(f"{entry_date} UTC")

        content = [
            '<img src="{}">'.format(app["icon"]),
            f"<p>{app['summary']}</p>",
            f"<p>{app['description']}</p>",
            "<h3>Additional information:</h3>",
            "<ul>",
        ]

        if developer_name := app.get("developer_name"):
            content.append(f"<li>Developer: {developer_name}</li>")

        if license := app.get("license"):
            content.append(f"<li>License: {license}")

        if app_releases := app.get("releases"):
            release = app_releases[0] if len(app_releases) else None
            if release:
                content.append(f"<li>Version: {release['version']}")

        content.append("</ul>")

        if screenshots := app.get("screenshots"):
            screenshots = screenshots[0:3]

            for screenshot in screenshots:
                if image := screenshot.get("624x351"):
                    content.append('<img src="{}">'.format(image))

        entry.description("".join(content))

    return feed.rss_str()


def get_recently_updated_apps_feed(repo: str = "stable"):
    return generate_feed(
        "recently_updated_zset" if repo == "stable" else "recently_updated_beta_zset",
        "Flathub – recently updated applications",
        "Recently updated applications published on Flathub",
        "https://flathub.org/apps/collection/recently-updated",
        repo,
    )


def get_new_apps_feed(repo: str = "stable"):
    return generate_feed(
        "new_apps_zset" if repo == "stable" else "new_apps_beta_zset",
        "Flathub – recently added applications",
        "Applications recently published on Flathub",
        "https://flathub.org/apps/collection/new",
        repo,
    )
