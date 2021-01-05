import math
from datetime import date, datetime, timedelta
from urllib.parse import urljoin, urlencode
from jinja2 import Environment, FileSystemLoader, select_autoescape
from tqdm import tqdm
import pandas as pd


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

def render_world(regions):
    template = env.get_template("world.html")
    try:
        now = get_data(None)
        nowDate = now["date"]

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
            nowDate=nowDate
        )
    
    with open('dist/index.html', 'w') as f:
        f.write(html)

def render_region(regions, region):
    regionCode = region["iso"]
    template = env.get_template("world.html")

    try:
        now = get_data(None, regionCode)
        nowDate = now["date"]

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
            nowDate=nowDate
        )

    with open(f'dist/{regionCode}.html', 'w') as f:
        f.write(html)


def main():
    regions = list(map(lambda x: {"iso": x, "name": x}, active.index))
    render_world(regions)
    for region in tqdm(regions):
        render_region(regions, region)

if __name__ == '__main__':
    main()