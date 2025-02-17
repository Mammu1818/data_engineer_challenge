from utils import scrape_countries, enrich_countries, get_country_code_mapping
from fastapi import HTTPException # type: ignore
from bs4 import BeautifulSoup # type: ignore
import requests # type: ignore


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
