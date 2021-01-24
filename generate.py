import math
from datetime import date, datetime, timedelta
from urllib.parse import urljoin, urlencode
from jinja2 import Environment, FileSystemLoader, select_autoescape
from tqdm import tqdm
import pandas as pd
import numpy as np


env = Environment(
    loader=FileSystemLoader('templates'),
    autoescape=select_autoescape(['html', 'xml'])
)

class NoDataError(Exception):
    pass


deaths = pd.read_csv("https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv").groupby(["Country/Region"]).sum()
recovered = pd.read_csv("https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_recovered_global.csv").groupby(["Country/Region"]).sum()
confirmed = pd.read_csv("https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv").groupby(["Country/Region"]).sum()
active = confirmed - recovered - deaths

def get_data(date=None, iso=None):
    result = {}
    if not date:
        result["date"] = datetime.strptime(active.columns[-1], "%m/%d/%y").date()
    else:
        result["date"] = date

    col = result["date"].strftime("%m/%d/%y").lstrip("0").replace("/0", "/")

    if iso == None:
        result["active"] = active[col].sum()
    else:
        result["active"] = active.loc[iso, col]

    return result

def get_statistics(iso):
    now = get_data(None, iso=iso)
    nowDate = now["date"]

    data = []
    for i in range(0, 7):
        point_a = (nowDate - timedelta(days = i))
        point_b = (nowDate - timedelta(days = i + 7))
        data.append(get_data(point_a, iso=iso)["active"] - get_data(point_b, iso=iso)["active"])

    past = []
    for i in range(-5, 0, 1):
        p = (nowDate + timedelta(days = i * 7))
        past.append(get_data(p, iso=iso))

    mean = np.mean(data)
    std = np.std(data)
    return now, mean, std, past

def render_page(now, mean, std, past, regionCode, regionName, regions, endOn=100, vaccination=None):
    template = env.get_template("world.html")
    if now["active"] == 0:
        rwk = 1
        rwkLow = 1
        rwkHigh = 1
    else:
        active = now["active"] + 5
        rwk = active / (active - mean)
        rwkLow = active / (active - (mean - std))
        rwkHigh = active / (active - (mean + std))

    if now["active"] < 1 or rwk < 1e-4:
        endInWeeks = 0
    elif rwk == 1.0:
        endInWeeks = 1000
    else:
        endInWeeks = math.ceil(math.log(endOn / now["active"], rwk))

    if now["active"] < 1 or rwkLow < 1e-4:
        endInWeeksLow = 0
    elif rwkLow == 1.0:
        endInWeeksLow = 1000
    else:
        endInWeeksLow = math.ceil(math.log(endOn / now["active"], rwkLow))

    if now["active"] < 1 or rwkHigh < 1e-4:
        endInWeeksHigh = 0
    elif rwkHigh == 1.0:
        endInWeeksHigh = 1000
    else:
        endInWeeksHigh = math.ceil(math.log(endOn / now["active"], rwkHigh))

    html = template.render(
        endOn=endOn,
        now=now,
        mean=int(mean),
        std=int(std),
        past=past,
        endInWeeks=endInWeeks,
        endInWeeksLow=endInWeeksLow,
        endInWeeksHigh=endInWeeksHigh,
        rwk=rwk,
        rwkHigh=rwkHigh,
        rwkLow=rwkLow,
        regionCode=regionCode,
        regionName=regionName,
        regions=regions,
        vaccination=vaccination
    )
    return html

def render_world(regions):
    try:
        now, mean, std, past = get_statistics(None)
    except NoDataError:
        print("No data for", "World")
        errorTemplate = env.get_template("error.html")
        html = errorTemplate.render(
            regionCode="world",
            regionName="World",
            regions=regions,
        )
    else:
        html = render_page(
            now=now,
            mean=mean,
            std=std,
            past=past,
            regionCode="world",
            regionName="World",
            regions=regions,
        )

    with open('dist/index.html', 'w') as f:
        f.write(html)

def render_region(regions, region):
    regionCode = region["iso"]
    template = env.get_template("world.html")

    try:
        now, mean, std, past = get_statistics(regionCode)
    except NoDataError:
        print("No data for", region["name"])
        errorTemplate = env.get_template("error.html")
        html = errorTemplate.render(
            regionCode=regionCode,
            regionName=region["name"],
            regions=regions,
        )
    else:
        html = render_page(
            now=now,
            mean=mean,
            std=std,
            past=past,
            regionCode=regionCode,
            regionName=region["name"],
            regions=regions,
            vaccination=get_region_vaccination_data(region["name"])
        )

    with open(f'dist/{regionCode}.html', 'w') as f:
        f.write(html)

def get_region_vaccination_data(region):
    if region == "Germany":
        df = pd.read_csv("https://impfdashboard.de/static/data/germany_vaccinations_timeseries_v2.tsv", sep='\t')
        vac = {
            "data": [],
            "source": {
                "url": "https://impfdashboard.de/",
                "name": "impfdashboard.de, RKI, BMG.",
            }
        }
        for i, r in df.iterrows():
            vac["data"].append({
                "date": r["date"],
                "first": r["impf_quote_erst"],
                "full": r["impf_quote_voll"],
            })
        return vac
    else:
        return None


def main():
    regions = list(map(lambda x: {"iso": x, "name": x}, active.index))
    render_world(regions)
    for region in tqdm(regions):
        render_region(regions, region)

if __name__ == '__main__':
    main()