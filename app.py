from fastapi import FastAPI, HTTPException, Request # type: ignore
from fastapi.responses import JSONResponse # type: ignore
from fastapi.templating import Jinja2Templates # type: ignore

from fastapi.staticfiles import StaticFiles # type: ignore
import requests # type: ignore
from bs4 import BeautifulSoup # type: ignore
import uvicorn # type: ignore

app = FastAPI(title="World Bank Countries API")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

countries_data = []

def scrape_countries():
    """
    Scrapes the list of countries (name and detail link) from the World Bank country page.
    """
    url = "https://data.worldbank.org/country"
    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch country page")
    soup = BeautifulSoup(response.text, 'html.parser')
    seen = set()
    countries = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/country/' in href:
            name = a.get_text(strip=True)
            if name and name not in seen:
                seen.add(name)
                # Build the link from the scraped URL.
                link = "https://data.worldbank.org" + href + "?view=chart"
                countries.append({
                    "name": name,
                    "link": link,
                    "profile": {}  # To be filled on demand.
                })
    return sorted(countries, key=lambda x: x["name"])

def get_country_code_mapping():
    """
    Fetches the list of countries from the World Bank API and returns a mapping of country name (lowercase)
    to its three-letter country code.
    """
    url = "https://api.worldbank.org/v2/country?format=json&per_page=300"
    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch country codes from API")
    try:
        data = response.json()
        mapping = {}
        for item in data[1]:
            # Using lowercase for case-insensitive matching.
            mapping[item["name"].lower()] = item["id"]
        return mapping
    except Exception:
        raise HTTPException(status_code=500, detail="Error parsing country code data")

def enrich_countries(scraped):
    """
    Enriches the scraped country list with country codes by matching names.
    """
    mapping = get_country_code_mapping()
    for country in scraped:
        country_name = country["name"].lower()
        if country_name in mapping:
            country["id"] = mapping[country_name]
        else:
            # Fallback if no match is found.
            country["id"] = ""
    return scraped

def fetch_indicator(country_code: str, indicator_code: str):
    """
    Fetch the most recent value for a given indicator and country using the World Bank API.
    """
    url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator_code}?format=json&mrv=1"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    try:
        data = response.json()
        if data and len(data) > 1 and data[1]:
            record = data[1][0]
            return {
                "indicator": indicator_code,
                "value": record.get("value", "No data"),
                "year": record.get("date", "")
            }
        else:
            return {"indicator": indicator_code, "value": "No data", "year": ""}
    except Exception:
        return {"indicator": indicator_code, "value": "No data", "year": ""}

def scrape_country_profile(country_code: str):
    """
    Fetches a country’s profile by gathering data from several major indicators via the API.
    """
    indicators_by_section = {
        "Social": [
            {"name": "Population, total", "code": "SP.POP.TOTL"},
            {"name": "Life expectancy at birth, total (years)", "code": "SP.DYN.LE00.IN"},
            {"name": "Poverty headcount ratio at $2.15 a day (2017 PPP)", "code": "SI.POV.DDAY"}
        ],
        "Economic": [
            {"name": "GDP (current US$)", "code": "NY.GDP.MKTP.CD"},
            {"name": "GDP per capita (current US$)", "code": "NY.GDP.PCAP.CD"}
        ],
        "Environment": [
            {"name": "Access to electricity (% of population)", "code": "EG.ELC.ACCS.ZS"}
        ],
        "Institutions": [
            {"name": "Individuals using the Internet (% of population)", "code": "IT.NET.USER.ZS"}
        ]
    }
    profile = {}
    for section, indicators in indicators_by_section.items():
        profile[section] = []
        for indicator in indicators:
            result = fetch_indicator(country_code, indicator["code"])
            if result is None:
                result = {"indicator": indicator["name"], "value": "No data", "year": ""}
            else:
                result["indicator"] = indicator["name"]
            profile[section].append(result)
    return profile

def fetch_and_enrich_countries():
    """
    Scrapes the basic list of countries and enriches it with country codes from the API.
    """
    scraped = scrape_countries()
    enriched = enrich_countries(scraped)
    return enriched

print("Fetching countries data at startup (hybrid scraping + API)...")
countries_data = fetch_and_enrich_countries()

@app.get("/api/countries", response_class=JSONResponse)
def get_countries():
    """
    Returns the list of countries with basic information.
    """
    return {"countries": countries_data}

@app.get("/api/countries/{country_name}", response_class=JSONResponse)
def get_country_details(country_name: str):
    """
    Returns the full profile for a given country. If not yet fetched, the profile is built on demand
    by retrieving selected indicators via the API.
    """
    for country in countries_data:
        if country["name"].lower() == country_name.lower():
            if not country.get("profile"):
                if not country.get("id"):
                    raise HTTPException(status_code=404, detail="Country code not found for profile lookup")
                country["profile"] = scrape_country_profile(country["id"])
            return {"country": country}
    raise HTTPException(status_code=404, detail="Country not found")

@app.get("/", response_class=JSONResponse)
def index(request: Request):
    """
    Serves the external HTML page.
    """
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
