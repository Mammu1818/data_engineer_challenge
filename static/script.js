let allCountries = [];
let currentPage = 1;
const itemsPerPage = 10;

async function fetchCountries() {
  const response = await fetch('/api/countries');
  const data = await response.json();
  return data.countries;
}

function createCountryElement(country) {
  const container = document.createElement('div');
  container.className = 'country';
  let html = `<strong>${country.name}</strong><br>`;
  if (country.capitalCity) {
    html += `Capital: ${country.capitalCity}<br>`;
  }
  if (country.region) {
    html += `Region: ${country.region}<br>`;
  }
  if (country.incomeLevel) {
    html += `Income Level: ${country.incomeLevel}<br>`;
  }
  html += `<button class="view-more" onclick="viewMore('${country.name}')">View More</button>`;
  container.innerHTML = html;
  return container;
}

async function viewMore(countryName) {
  const countryElements = document.getElementsByClassName('country');
  let targetElement;
  for (let el of countryElements) {
    if (el.innerText.includes(countryName)) {
      targetElement = el;
      break;
    }
  }
  if (!targetElement) return;
  
  // Toggle profile display: if already open, remove it.
  const existingProfile = targetElement.querySelector('.profile');
  if (existingProfile) {
    targetElement.removeChild(existingProfile);
    return;
  }
  
  // Create and add the loader spinner.
  const loaderDiv = document.createElement('div');
  loaderDiv.className = 'loader';
  targetElement.appendChild(loaderDiv);
  
  // Fetch full profile details on demand.
  try {
    const response = await fetch(`/api/countries/${encodeURIComponent(countryName)}`);
    const data = await response.json();
    const profile = data.country.profile;
    
    // Remove loader once data is fetched.
    targetElement.removeChild(loaderDiv);
    
    // Create a div for the full profile display.
    const profileDiv = document.createElement('div');
    profileDiv.className = 'profile';
    let profileHtml = "";
    for (const section in profile) {
      profileHtml += `<h3>${section}</h3><ul>`;
      profile[section].forEach(item => {
        profileHtml += `<li><strong>${item.indicator}</strong>: ${item.value} (${item.year})</li>`;
      });
      profileHtml += "</ul>";
    }
    profileDiv.innerHTML = profileHtml;
    targetElement.appendChild(profileDiv);
  } catch (error) {
    targetElement.removeChild(loaderDiv);
    console.error("Error loading profile", error);
  }
}

function displayCountriesPage(countries, page) {
  const start = (page - 1) * itemsPerPage;
  const end = start + itemsPerPage;
  const pagedCountries = countries.slice(start, end);
  const listDiv = document.getElementById('countries-list');
  listDiv.innerHTML = '';
  pagedCountries.forEach(function(country) {
    const el = createCountryElement(country);
    listDiv.appendChild(el);
  });
  updatePaginationControls(countries.length, page);
}

function updatePaginationControls(totalItems, page) {
  const paginationDiv = document.getElementById('pagination');
  paginationDiv.innerHTML = '';
  const totalPages = Math.ceil(totalItems / itemsPerPage);
  if(totalPages <= 1) return;
  const prev = document.createElement('button');
  prev.textContent = 'Prev';
  prev.disabled = (page === 1);
  prev.onclick = () => {
    currentPage--;
    filterAndDisplay();
  };
  paginationDiv.appendChild(prev);
  for(let i = 1; i <= totalPages; i++){
    const btn = document.createElement('button');
    btn.textContent = i;
    if(i === page) btn.disabled = true;
    btn.onclick = () => {
      currentPage = i;
      filterAndDisplay();
    };
    paginationDiv.appendChild(btn);
  }
  const next = document.createElement('button');
  next.textContent = 'Next';
  next.disabled = (page === totalPages);
  next.onclick = () => {
    currentPage++;
    filterAndDisplay();
  };
  paginationDiv.appendChild(next);
}

async function filterAndDisplay() {
  const query = document.getElementById('search').value.toLowerCase();
  const filtered = allCountries.filter(country => country.name.toLowerCase().includes(query));
  const totalPages = Math.ceil(filtered.length / itemsPerPage);
  if(currentPage > totalPages) currentPage = 1;
  displayCountriesPage(filtered, currentPage);
}

window.onload = async () => {
  allCountries = await fetchCountries();
  filterAndDisplay();
}