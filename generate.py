import math
from datetime import date, timedelta
from urllib.parse import urljoin
import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape
from tqdm import tqdm

COVID_API = "https://covid-api.com/api/"

env = Environment(
    loader=FileSystemLoader('templates'),
    autoescape=select_autoescape(['html', 'xml'])
)

class NoDataError(Exception):
    pass

def get_data(date, iso=None):
    if iso == None:
        resp = requests.get(urljoin(COVID_API, f"reports/total?date={date.isoformat()}")).json()["data"]
    else:
        resp = requests.get(urljoin(COVID_API, f"reports?iso={iso}&date={date.isoformat()}")).json()["data"]

    if isinstance(resp, list):
        if len(resp) == 0:
            raise NoDataError
        resp = max(resp, key=lambda x: x["active"])

    return resp

def render_world(regions):
    template = env.get_template("world.html")
    try:
        nowDate = (date.today() - timedelta(days = 1))
        now = get_data(nowDate)

        lastDate = (nowDate - timedelta(days = 7))
        last = get_data(lastDate)
    except NoDataError:
        print("No data for", "World")
        errorTemplate = env.get_template("error.html")
        html = errorTemplate.render(
            regionCode="world",
            regionName="World",
            regions=regions,
        )
    else:
        difference = now["active"] - last["active"]

        endOn = 100
        rwk = now["active"] / last["active"]
        endInWeeks = math.ceil(math.log(endOn / now["active"], rwk))

        html = template.render(
            now=now,
            last=last,
            difference=difference,
            endInWeeks=endInWeeks,
            regionCode="world",
            regionName="World",
            regions=regions,
            rwk=rwk,
        )
    
    with open('dist/index.html', 'w') as f:
        f.write(html)

def render_region(regions, region):
    regionCode = region["iso"]
    template = env.get_template("world.html")

    try:
        nowDate = (date.today() - timedelta(days = 1))
        now = get_data(nowDate, regionCode)

        lastDate = (nowDate - timedelta(days = 7))
        last = get_data(lastDate, regionCode)
    except NoDataError:
        print("No data for", region["name"])
        errorTemplate = env.get_template("error.html")
        html = errorTemplate.render(
            regionCode=regionCode,
            regionName=region["name"],
            regions=regions,
        )
    else:
        difference = now["active"] - last["active"]

        endOn = 100
        if last["active"] == 0:
            rwk  =1
        else:
            rwk = now["active"] / last["active"]
        if now["active"] < 1 or rwk < 1e-4:
            endInWeeks = 0
        elif rwk == 1.0:
            endInWeeks = 1000
        else:
            endInWeeks = math.ceil(math.log(endOn / now["active"], rwk))

        html = template.render(
            now=now,
            last=last,
            difference=difference,
            endInWeeks=endInWeeks,
            regionCode=regionCode,
            regionName=region["name"],
            regions=regions,
            rwk=rwk,
        )

    with open(f'dist/{regionCode}.html', 'w') as f:
        f.write(html)


def main():
    regions = requests.get(urljoin(COVID_API, "regions")).json()["data"]
    regions = sorted(regions, key=lambda x: x["name"])
    render_world(regions)
    for region in tqdm(regions[:5]):
        render_region(regions, region)

if __name__ == '__main__':
    main()