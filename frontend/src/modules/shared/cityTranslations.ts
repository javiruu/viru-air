export const CITY_TRANSLATIONS: Record<string, { en: string; es: string }> = {
  "London": { en: "London", es: "Londres" },
  "New York": { en: "New York", es: "Nueva York" },
  "Paris": { en: "Paris", es: "París" },
  "Berlin": { en: "Berlin", es: "Berlín" },
  "Rome": { en: "Rome", es: "Roma" },
  "Milan": { en: "Milan", es: "Milán" },
  "Venice": { en: "Venice", es: "Venecia" },
  "Florence": { en: "Florence", es: "Florencia" },
  "Naples": { en: "Naples", es: "Nápoles" },
  "Turin": { en: "Turin", es: "Turín" },
  "Genoa": { en: "Genoa", es: "Génova" },
  "Athens": { en: "Athens", es: "Atenas" },
  "Munich": { en: "Munich", es: "Múnich" },
  "Frankfurt": { en: "Frankfurt", es: "Fráncfort" },
  "Cologne": { en: "Cologne", es: "Colonia" },
  "Geneva": { en: "Geneva", es: "Ginebra" },
  "Zurich": { en: "Zurich", es: "Zúrich" },
  "Vienna": { en: "Vienna", es: "Viena" },
  "Prague": { en: "Prague", es: "Praga" },
  "Warsaw": { en: "Warsaw", es: "Varsovia" },
  "Krakow": { en: "Krakow", es: "Cracovia" },
  "Moscow": { en: "Moscow", es: "Moscú" },
  "Saint Petersburg": { en: "Saint Petersburg", es: "San Petersburgo" },
  "Lisbon": { en: "Lisbon", es: "Lisboa" },
  "Porto": { en: "Porto", es: "Oporto" },
  "Brussels": { en: "Brussels", es: "Bruselas" },
  "Antwerp": { en: "Antwerp", es: "Amberes" },
  "Bruges": { en: "Bruges", es: "Brujas" },
  "Amsterdam": { en: "Amsterdam", es: "Ámsterdam" },
  "The Hague": { en: "The Hague", es: "La Haya" },
  "Copenhagen": { en: "Copenhagen", es: "Copenhague" },
  "Stockholm": { en: "Stockholm", es: "Estocolmo" },
  "Gothenburg": { en: "Gothenburg", es: "Gotemburgo" },
  "Edinburgh": { en: "Edinburgh", es: "Edimburgo" },
  "Dublin": { en: "Dublin", es: "Dublín" },
  "Bucharest": { en: "Bucharest", es: "Bucarest" },
  "Budapest": { en: "Budapest", es: "Budapest" },
  "Belgrade": { en: "Belgrade", es: "Belgrado" },
  "Sofia": { en: "Sofia", es: "Sofía" },
  "Istanbul": { en: "Istanbul", es: "Estambul" },
  "Ankara": { en: "Ankara", es: "Ankara" },
  "Damascus": { en: "Damascus", es: "Damasco" },
  "Beirut": { en: "Beirut", es: "Beirut" },
  "Jerusalem": { en: "Jerusalem", es: "Jerusalén" },
  "Cairo": { en: "Cairo", es: "El Cairo" },
  "Alexandria": { en: "Alexandria", es: "Alejandría" },
  "Cape Town": { en: "Cape Town", es: "Ciudad del Cabo" },
  "Havana": { en: "Havana", es: "La Habana" },
  "Bogota": { en: "Bogota", es: "Bogotá" },
  "Panama City": { en: "Panama City", es: "Ciudad de Panamá" },
  "Mexico City": { en: "Mexico City", es: "Ciudad de México" },
  "Los Angeles": { en: "Los Angeles", es: "Los Ángeles" },
  "Philadelphia": { en: "Philadelphia", es: "Filadelfia" },
  "Tokyo": { en: "Tokyo", es: "Tokio" },
  "Beijing": { en: "Beijing", es: "Pekín" },
  "Seoul": { en: "Seoul", es: "Seúl" },
  "Singapore": { en: "Singapore", es: "Singapur" },
  "Bangkok": { en: "Bangkok", es: "Bangkok" },
  "New Delhi": { en: "New Delhi", es: "Nueva Delhi" },
  "Mumbai": { en: "Mumbai", es: "Bombay" },
  "Kolkata": { en: "Kolkata", es: "Calcuta" },
  "Jakarta": { en: "Jakarta", es: "Yakarta" },
  "Manila": { en: "Manila", es: "Manila" },
  "Sydney": { en: "Sydney", es: "Sídney" },
  "Melbourne": { en: "Melbourne", es: "Melbourne" },
};

export function getTranslatedCityName(cityName: string, targetLanguage: string): string {
  if (!cityName) return cityName;
  
  const lang = targetLanguage.toLowerCase().startsWith("es") ? "es" : "en";
  const normalizedSearch = cityName.trim().toLowerCase();
  
  for (const translations of Object.values(CITY_TRANSLATIONS)) {
    if (translations.en.toLowerCase() === normalizedSearch || translations.es.toLowerCase() === normalizedSearch) {
      return translations[lang];
    }
  }
  
  return cityName;
}

export function getApiSearchQuery(query: string): string {
  if (!query) return query;
  
  const q = query.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
  
  for (const translations of Object.values(CITY_TRANSLATIONS)) {
    const nEn = translations.en.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    const nEs = translations.es.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    
    // If the partial query matches the beginning of a Spanish or English translation
    if (nEs.startsWith(q) || nEn.startsWith(q)) {
      // return the english full name, or the query itself if it's too short
      if (q.length >= 3) {
        return translations.en;
      }
    }
  }
  
  return query;
}

export function matchesCityTranslation(cityName: string, query: string): boolean {
  if (!cityName || !query) return false;
  
  const q = query.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
  
  // Direct match
  const nCity = cityName.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  if (nCity.includes(q)) return true;
  
  // Translation match
  for (const translations of Object.values(CITY_TRANSLATIONS)) {
    const nEn = translations.en.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    const nEs = translations.es.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    
    // If the actual city name matches one of the translations
    if (nEn === nCity || nEs === nCity) {
      // And the query matches any of the translations
      if (nEn.includes(q) || nEs.includes(q)) {
        return true;
      }
    }
  }
  
  return false;
}
