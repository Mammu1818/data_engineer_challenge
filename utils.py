import requests # type: ignore
from fastapi import HTTPException # type: ignore
from bs4 import BeautifulSoup # type: ignore

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

def fetch_and_enrich_countries():
    """
    This function combines scraping countries and enriching them with their codes.
    It first scrapes the country data, then enriches it with the country codes.
    """
    # Step 1: Scrape countries
    scraped_countries = scrape_countries()
    
    # Step 2: Enrich the scraped data with country codes
    enriched_countries = enrich_countries(scraped_countries)
    
    return enriched_countries

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
