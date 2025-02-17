from fastapi import FastAPI, HTTPException, Request # type: ignore
from fastapi.responses import JSONResponse  # type: ignore
from fastapi.templating import Jinja2Templates # type: ignore
from fastapi.staticfiles import StaticFiles # type: ignore 
import uvicorn # type: ignore
from utils import fetch_and_enrich_countries, scrape_country_profile


app = FastAPI(title="World Bank Countries API")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

countries_data = []

# Fetch countries data at startup
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
