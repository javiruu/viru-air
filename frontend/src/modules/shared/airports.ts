export type Airport = {
  iata: string;
  name: string;
};

export type AirportMeta = {
  iata: string;
  name: string;
  city: string;
  country: string;
  latitude: number;
  longitude: number;
};

export type CountryAirports = {
  code: string;
  name: string;
  airports: Airport[];
};

export const COUNTRY_AIRPORTS: CountryAirports[] = [
  {
    code: "AL",
    name: "Albania",
    airports: [
      { iata: "TIA", name: "Tirana International Airport Mother Teresa" },
    ],
  },
  {
    code: "DE",
    name: "Alemania",
    airports: [
      { iata: "BER", name: "Berlin Brandenburg Airport" },
      { iata: "FDH", name: "Bodensee Airport Friedrichshafen" },
      { iata: "BRE", name: "Bremen Airport" },
      { iata: "CGN", name: "Cologne Bonn Airport" },
      { iata: "HHN", name: "Frankfurt-Hahn Airport" },
      { iata: "HAM", name: "Hamburg Helmut Schmidt Airport" },
      { iata: "FKB", name: "Karlsruhe Baden-Baden Airport" },
      { iata: "LBC", name: "Lübeck Blankensee Airport" },
      { iata: "FMM", name: "Memmingen Allgau Airport" },
      { iata: "FMO", name: "Münster Osnabrück Airport" },
      { iata: "NUE", name: "Nuremberg Airport" },
      { iata: "PAD", name: "Paderborn Lippstadt Airport" },
      { iata: "SCN", name: "Saarbrücken Airport" },
      { iata: "NRN", name: "Weeze (Niederrhein) Airport" },
    ],
  },
  {
    code: "AT",
    name: "Austria",
    airports: [
      { iata: "KLU", name: "Klagenfurt Airport" },
      { iata: "LNZ", name: "Linz-Hörsching Airport" },
      { iata: "SZG", name: "Salzburg Airport" },
      { iata: "VIE", name: "Vienna International Airport" },
    ],
  },
  {
    code: "BA",
    name: "Bosnia",
    airports: [
      { iata: "BNX", name: "Banja Luka International Airport" },
      { iata: "SJJ", name: "Sarajevo International Airport" },
    ],
  },
  {
    code: "BG",
    name: "Bulgaria",
    airports: [
      { iata: "BOJ", name: "Burgas Airport" },
      { iata: "PDV", name: "Plovdiv International Airport" },
      { iata: "SOF", name: "Sofia Airport" },
      { iata: "VAR", name: "Varna Airport" },
    ],
  },
  {
    code: "BE",
    name: "Bélgica",
    airports: [
      { iata: "BRU", name: "Brussels Airport" },
      { iata: "CRL", name: "Brussels South Charleroi Airport" },
    ],
  },
  {
    code: "CY",
    name: "Chipre",
    airports: [
      { iata: "LCA", name: "Larnaca International Airport" },
      { iata: "PFO", name: "Paphos International Airport" },
    ],
  },
  {
    code: "HR",
    name: "Croacia",
    airports: [
      { iata: "DBV", name: "Dubrovnik Ruđer Bošković Airport" },
      { iata: "OSI", name: "Osijek Airport" },
      { iata: "PUY", name: "Pula Airport" },
      { iata: "RJK", name: "Rijeka Airport" },
      { iata: "SPU", name: "Split Saint Jerome Airport" },
      { iata: "ZAD", name: "Zadar Airport" },
      { iata: "ZAG", name: "Zagreb Franjo Tuđman International Airport" },
    ],
  },
  {
    code: "DK",
    name: "Dinamarca",
    airports: [
      { iata: "AAR", name: "Aarhus Airport" },
      { iata: "CPH", name: "Copenhagen Kastrup Airport" },
    ],
  },
  {
    code: "SK",
    name: "Eslovaquia",
    airports: [
      { iata: "KSC", name: "Košice International Airport" },
      { iata: "BTS", name: "M. R. Štefánik Airport" },
    ],
  },
  {
    code: "ES",
    name: "España",
    airports: [
      { iata: "MAD", name: "Adolfo Suárez Madrid–Barajas Airport" },
      { iata: "ALC", name: "Alicante-Elche Miguel Hernández Airport" },
      { iata: "LEI", name: "Almería Airport" },
      { iata: "CDT", name: "Castellón-Costa Azahar Airport" },
      { iata: "ACE", name: "César Manrique-Lanzarote Airport" },
      { iata: "FUE", name: "Fuerteventura Airport" },
      { iata: "GRO", name: "Girona-Costa Brava Airport" },
      { iata: "LPA", name: "Gran Canaria Airport" },
      { iata: "IBZ", name: "Ibiza Airport" },
      { iata: "BCN", name: "Josep Tarradellas Barcelona-El Prat Airport" },
      { iata: "MAH", name: "Menorca Airport" },
      { iata: "AGP", name: "Málaga-Costa del Sol Airport" },
      { iata: "PMI", name: "Palma de Mallorca Airport" },
      { iata: "RMU", name: "Region of Murcia International Airport" },
      { iata: "REU", name: "Reus Airport" },
      { iata: "SCQ", name: "Santiago-Rosalía de Castro Airport" },
      { iata: "SDR", name: "Seve Ballesteros-Santander Airport" },
      { iata: "SVQ", name: "Seville Airport" },
      { iata: "TFS", name: "Tenerife Sur Airport" },
      { iata: "VLC", name: "Valencia Airport" },
      { iata: "VIT", name: "Vitoria Airport" },
      { iata: "ZAZ", name: "Zaragoza Airport" },
    ],
  },
  {
    code: "EE",
    name: "Estonia",
    airports: [
      { iata: "TLL", name: "Lennart Meri Tallinn Airport" },
    ],
  },
  {
    code: "FI",
    name: "Finlandia",
    airports: [
      { iata: "HEL", name: "Helsinki Vantaa Airport" },
      { iata: "RVN", name: "Rovaniemi Airport" },
    ],
  },
  {
    code: "FR",
    name: "Francia",
    airports: [
      { iata: "BVA", name: "Beauvais-Tillé airport" },
      { iata: "EGC", name: "Bergerac Dordogne-Périgord airport" },
      { iata: "BIQ", name: "Biarritz Pays Basque airport" },
      { iata: "BVE", name: "Brive Souillac airport" },
      { iata: "BZR", name: "Béziers Vias airport" },
      { iata: "CCF", name: "Carcassonne Salvaza Airport" },
      { iata: "XCR", name: "Chalons Vatry airport" },
      { iata: "DLE", name: "Dole Tavaux Airport" },
      { iata: "FSC", name: "Figari Sud-Corse Airport" },
      { iata: "GNB", name: "Grenoble Alpes Isère Airport" },
      { iata: "LRH", name: "La Rochelle Île de Ré Airport" },
      { iata: "LIL", name: "Lille Airport" },
      { iata: "LIG", name: "Limoges Airport" },
      { iata: "MRS", name: "Marseille Provence Airport" },
      { iata: "NTE", name: "Nantes Atlantique Airport" },
      { iata: "NCE", name: "Nice-Côte d'Azur Airport" },
      { iata: "FNI", name: "Nîmes-Arles-Camargue Airport" },
      { iata: "PGF", name: "Perpignan-Rivesaltes (Llabanère) Airport" },
      { iata: "PIS", name: "Poitiers-Biard Airport" },
      { iata: "RDZ", name: "Rodez–Aveyron Airport" },
      { iata: "LDE", name: "Tarbes-Lourdes-Pyrénées Airport" },
      { iata: "TLS", name: "Toulouse-Blagnac Airport" },
      { iata: "TUF", name: "Tours Val de Loire Airport" },
    ],
  },
  {
    code: "GR",
    name: "Grecia",
    airports: [
      { iata: "PVK", name: "Aktion National Airport" },
      { iata: "ATH", name: "Athens Eleftherios Venizelos International Airport" },
      { iata: "CHQ", name: "Chania International Airport" },
      { iata: "CFU", name: "Corfu Ioannis Kapodistrias International Airport" },
      { iata: "HER", name: "Heraklion International Nikos Kazantzakis Airport" },
      { iata: "KLX", name: "Kalamata Airport" },
      { iata: "EFL", name: "Kefallinia Airport" },
      { iata: "KGS", name: "Kos International Airport \"Ippokratis\"" },
      { iata: "LXS", name: "Limnos Airport" },
      { iata: "JMK", name: "Mykonos Island National Airport" },
      { iata: "VOL", name: "Nea Anchialos National Airport" },
      { iata: "RHO", name: "Rhodes International Airport \"Diagoras\"" },
      { iata: "JTR", name: "Santorini International Airport" },
      { iata: "JSI", name: "Skiathos Island National Airport" },
      { iata: "SKG", name: "Thessaloniki Macedonia International Airport" },
      { iata: "ZTH", name: "Zakynthos International Airport Dionysios Solomos" },
    ],
  },
  {
    code: "HU",
    name: "Hungría",
    airports: [
      { iata: "BUD", name: "Budapest Liszt Ferenc International Airport" },
    ],
  },
  {
    code: "IE",
    name: "Irlanda",
    airports: [
      { iata: "ORK", name: "Cork International Airport" },
      { iata: "DUB", name: "Dublin Airport" },
      { iata: "NOC", name: "Ireland West Airport Knock" },
      { iata: "KIR", name: "Kerry Airport" },
      { iata: "SNN", name: "Shannon Airport" },
    ],
  },
  {
    code: "IT",
    name: "Italia",
    airports: [
      { iata: "PSR", name: "Abruzzo Airport" },
      { iata: "AHO", name: "Alghero-Fertilia Airport" },
      { iata: "BRI", name: "Bari Karol Wojtyła International Airport" },
      { iata: "BLQ", name: "Bologna Guglielmo Marconi Airport" },
      { iata: "BDS", name: "Brindisi Airport" },
      { iata: "CAG", name: "Cagliari Elmas Airport" },
      { iata: "CTA", name: "Catania-Fontanarossa Airport" },
      { iata: "CIA", name: "Ciampino–G. B. Pastine International Airport" },
      { iata: "CRV", name: "Crotone Sant'Anna Pythagoras Airport" },
      { iata: "CUF", name: "Cuneo International Airport" },
      { iata: "PMO", name: "Falcone–Borsellino Airport" },
      { iata: "RMI", name: "Federico Fellini International Airport" },
      { iata: "FRL", name: "Forlì-Luigi Ridolfi International Airport" },
      { iata: "GOA", name: "Genoa Cristoforo Colombo Airport" },
      { iata: "BGY", name: "Il Caravaggio International Airport" },
      { iata: "SUF", name: "Lamezia Terme Sant'Eufemia International Airport" },
      { iata: "AOI", name: "Marche Airport" },
      { iata: "MXP", name: "Milan Malpensa International Airport" },
      { iata: "NAP", name: "Naples International Airport" },
      { iata: "OLB", name: "Olbia Costa Smeralda Airport" },
      { iata: "PMF", name: "Parma Airport" },
      { iata: "PEG", name: "Perugia San Francesco d'Assisi – Umbria International Airport" },
      { iata: "PSA", name: "Pisa International Airport" },
      { iata: "REG", name: "Reggio Calabria Airport" },
      { iata: "FCO", name: "Rome–Fiumicino Leonardo da Vinci International Airport" },
      { iata: "QSR", name: "Salerno Costa d'Amalfi Airport" },
      { iata: "TSF", name: "Treviso Airport" },
      { iata: "TRS", name: "Trieste Airport" },
      { iata: "TRN", name: "Turin Airport" },
      { iata: "VCE", name: "Venice Marco Polo Airport" },
      { iata: "VRN", name: "Verona Villafranca Valerio Catullo Airport" },
      { iata: "TPS", name: "Vincenzo Florio Airport Trapani-Birgi" },
    ],
  },
  {
    code: "JO",
    name: "Jordania",
    airports: [
      { iata: "AMM", name: "Queen Alia International Airport" },
    ],
  },
  {
    code: "LV",
    name: "Letonia",
    airports: [
      { iata: "RIX", name: "Riga International Airport" },
    ],
  },
  {
    code: "LT",
    name: "Lituania",
    airports: [
      { iata: "KUN", name: "Kaunas International Airport" },
      { iata: "PLQ", name: "Palanga International Airport" },
      { iata: "VNO", name: "Vilnius International Airport" },
    ],
  },
  {
    code: "LU",
    name: "Luxemburgo",
    airports: [
      { iata: "LUX", name: "Luxembourg-Findel International Airport" },
    ],
  },
  {
    code: "MT",
    name: "Malta",
    airports: [
      { iata: "MLA", name: "Malta International Airport" },
    ],
  },
  {
    code: "MA",
    name: "Marruecos",
    airports: [
      { iata: "AGA", name: "Al Massira Airport" },
      { iata: "BEM", name: "Beni Mellal Airport" },
      { iata: "ESU", name: "Essaouira-Mogador Airport" },
      { iata: "FEZ", name: "Fes Saïss International Airport" },
      { iata: "RAK", name: "Marrakesh Menara Airport" },
      { iata: "ERH", name: "Moulay Ali Cherif Airport" },
      { iata: "NDR", name: "Nador Al Aaroui International Airport" },
      { iata: "OZZ", name: "Ouarzazate International Airport" },
      { iata: "OUD", name: "Oujda Angads Airport" },
      { iata: "RBA", name: "Rabat-Salé Airport" },
      { iata: "TTU", name: "Sania Ramel Airport" },
      { iata: "TNG", name: "Tangier Ibn Battuta Airport" },
    ],
  },
  {
    code: "ME",
    name: "Montenegro",
    airports: [
      { iata: "TGD", name: "Podgorica Airport / Podgorica Golubovci Airbase" },
    ],
  },
  {
    code: "NO",
    name: "Noruega",
    airports: [
      { iata: "OSL", name: "Oslo-Gardermoen International Airport" },
      { iata: "TRF", name: "Sandefjord Airport, Torp" },
    ],
  },
  {
    code: "NL",
    name: "Países Bajos",
    airports: [
      { iata: "AMS", name: "Amsterdam Airport Schiphol" },
      { iata: "EIN", name: "Eindhoven Airport" },
    ],
  },
  {
    code: "PL",
    name: "Polonia",
    airports: [
      { iata: "WRO", name: "Copernicus Wrocław Airport" },
      { iata: "GDN", name: "Gdańsk Lech Wałęsa Airport" },
      { iata: "BZG", name: "Ignacy Jan Paderewski Bydgoszcz Airport" },
      { iata: "KTW", name: "Katowice Wojciech Korfanty International Airport" },
      { iata: "KRK", name: "Kraków John Paul II International Airport" },
      { iata: "LUZ", name: "Lublin Airport" },
      { iata: "SZY", name: "Olsztyn-Mazury Airport" },
      { iata: "POZ", name: "Poznań-Ławica Airport" },
      { iata: "RZE", name: "Rzeszów-Jasionka Airport" },
      { iata: "SZZ", name: "Solidarity Szczecin–Goleniów Airport" },
      { iata: "WAW", name: "Warsaw Chopin Airport" },
      { iata: "WMI", name: "Warsaw Modlin Airport" },
      { iata: "LCJ", name: "Łódź Władysław Reymont Airport" },
    ],
  },
  {
    code: "PT",
    name: "Portugal",
    airports: [
      { iata: "FNC", name: "Cristiano Ronaldo International Airport" },
      { iata: "FAO", name: "Faro - Gago Coutinho International Airport" },
      { iata: "OPO", name: "Francisco de Sá Carneiro Airport" },
      { iata: "LIS", name: "Lisbon Humberto Delgado Airport" },
    ],
  },
  {
    code: "GB",
    name: "Reino Unido",
    airports: [
      { iata: "ABZ", name: "Aberdeen International Airport" },
      { iata: "BFS", name: "Belfast International Airport" },
      { iata: "BHX", name: "Birmingham Airport" },
      { iata: "BOH", name: "Bournemouth Airport" },
      { iata: "BRS", name: "Bristol Airport" },
      { iata: "CWL", name: "Cardiff International Airport" },
      { iata: "LDY", name: "City of Derry Airport" },
      { iata: "NQY", name: "Cornwall Airport Newquay" },
      { iata: "EMA", name: "East Midlands Airport" },
      { iata: "EDI", name: "Edinburgh Airport" },
      { iata: "EXT", name: "Exeter International Airport" },
      { iata: "GLA", name: "Glasgow Airport" },
      { iata: "PIK", name: "Glasgow Prestwick Airport" },
      { iata: "LBA", name: "Leeds Bradford Airport" },
      { iata: "LPL", name: "Liverpool John Lennon Airport" },
      { iata: "LGW", name: "London Gatwick Airport" },
      { iata: "LTN", name: "London Luton Airport" },
      { iata: "STN", name: "London Stansted Airport" },
      { iata: "MAN", name: "Manchester Airport" },
      { iata: "NCL", name: "Newcastle International Airport" },
      { iata: "NWI", name: "Norwich Airport" },
      { iata: "MME", name: "Teesside International Airport" },
    ],
  },
  {
    code: "CZ",
    name: "República Checa",
    airports: [
      { iata: "BRQ", name: "Brno-Tuřany Airport" },
      { iata: "OSR", name: "Leoš Janáček Airport Ostrava" },
      { iata: "PED", name: "Pardubice Airport" },
      { iata: "PRG", name: "Václav Havel Airport Prague" },
    ],
  },
  {
    code: "RO",
    name: "Rumanía",
    airports: [
      { iata: "CLJ", name: "Avram Iancu Cluj International Airport" },
      { iata: "BBU", name: "Bucharest Băneasa Aurel Vlaicu International Airport" },
      { iata: "OTP", name: "Bucharest Henri Coandă International Airport" },
      { iata: "IAS", name: "Iaşi International Airport" },
    ],
  },
  {
    code: "RS",
    name: "Serbia",
    airports: [
      { iata: "INI", name: "Niš Constantine the Great Airport" },
    ],
  },
  {
    code: "SE",
    name: "Suecia",
    airports: [
      { iata: "GOT", name: "Göteborg Landvetter Airport" },
      { iata: "MMX", name: "Malmö Sturup Airport" },
      { iata: "SFT", name: "Skellefteå Airport" },
      { iata: "VST", name: "Stockholm Västerås Airport" },
      { iata: "ARN", name: "Stockholm-Arlanda Airport" },
      { iata: "VXO", name: "Växjö Kronoberg Airport" },
    ],
  },
  {
    code: "TR",
    name: "Turquía",
    airports: [
      { iata: "DLM", name: "Dalaman International Airport" },
      { iata: "BJV", name: "Milas Bodrum International Airport" },
    ],
  },
];

const AIRPORT_BY_IATA = new Map<string, Airport>();
const COUNTRY_BY_IATA = new Map<string, CountryAirports>();

for (const country of COUNTRY_AIRPORTS) {
  for (const airport of country.airports) {
    const code = airport.iata.toUpperCase();
    AIRPORT_BY_IATA.set(code, airport);
    COUNTRY_BY_IATA.set(code, country);
  }
}

export const AIRPORT_META: Record<string, AirportMeta> = {
  AAR: { iata: "AAR", name: "Aarhus Airport", city: "Aarhus", country: "Dinamarca", latitude: 56.303331, longitude: 10.618286 },
  ABZ: { iata: "ABZ", name: "Aberdeen International Airport", city: "Aberdeen", country: "Reino Unido", latitude: 57.2019, longitude: -2.19778 },
  ACE: { iata: "ACE", name: "César Manrique-Lanzarote Airport", city: "San Bartolomé", country: "España", latitude: 28.945499, longitude: -13.6052 },
  AGA: { iata: "AGA", name: "Al Massira Airport", city: "Agadir (Temsia)", country: "Marruecos", latitude: 30.322478, longitude: -9.412003 },
  AGP: { iata: "AGP", name: "Málaga-Costa del Sol Airport", city: "Málaga", country: "España", latitude: 36.6749, longitude: -4.49911 },
  AHO: { iata: "AHO", name: "Alghero-Fertilia Airport", city: "Alghero", country: "Italia", latitude: 40.632099, longitude: 8.29077 },
  ALC: { iata: "ALC", name: "Alicante-Elche Miguel Hernández Airport", city: "Alicante", country: "España", latitude: 38.2822, longitude: -0.558156 },
  AMM: { iata: "AMM", name: "Queen Alia International Airport", city: "Amman", country: "Jordania", latitude: 31.722601, longitude: 35.993198 },
  AMS: { iata: "AMS", name: "Amsterdam Airport Schiphol", city: "Amsterdam", country: "Países Bajos", latitude: 52.308601, longitude: 4.76389 },
  AOI: { iata: "AOI", name: "Marche Airport", city: "Falconara Marittima (AN)", country: "Italia", latitude: 43.616299, longitude: 13.3623 },
  ARN: { iata: "ARN", name: "Stockholm-Arlanda Airport", city: "Stockholm", country: "Suecia", latitude: 59.64849, longitude: 17.928829 },
  ATH: { iata: "ATH", name: "Athens Eleftherios Venizelos International Airport", city: "Spata-Artemida", country: "Grecia", latitude: 37.936401, longitude: 23.9445 },
  BBU: { iata: "BBU", name: "Bucharest Băneasa Aurel Vlaicu International Airport", city: "Bucharest", country: "Rumanía", latitude: 44.503133, longitude: 26.102944 },
  BCN: { iata: "BCN", name: "Josep Tarradellas Barcelona-El Prat Airport", city: "Barcelona", country: "España", latitude: 41.2971, longitude: 2.07846 },
  BDS: { iata: "BDS", name: "Brindisi Airport", city: "Brindisi", country: "Italia", latitude: 40.6576, longitude: 17.947001 },
  BEM: { iata: "BEM", name: "Beni Mellal Airport", city: "Oulad Yaich", country: "Marruecos", latitude: 32.401895, longitude: -6.315905 },
  BER: { iata: "BER", name: "Berlin Brandenburg Airport", city: "Berlin", country: "Alemania", latitude: 52.361738, longitude: 13.502341 },
  BFS: { iata: "BFS", name: "Belfast International Airport", city: "Belfast", country: "Reino Unido", latitude: 54.657501, longitude: -6.21583 },
  BGY: { iata: "BGY", name: "Il Caravaggio International Airport", city: "Orio al Serio (BG)", country: "Italia", latitude: 45.669362, longitude: 9.708851 },
  BHX: { iata: "BHX", name: "Birmingham Airport", city: "Birmingham, West Midlands", country: "Reino Unido", latitude: 52.453899, longitude: -1.74803 },
  BIQ: { iata: "BIQ", name: "Biarritz Pays Basque airport", city: "Biarritz", country: "Francia", latitude: 43.468372, longitude: -1.523223 },
  BJV: { iata: "BJV", name: "Milas Bodrum International Airport", city: "Bodrum", country: "Turquía", latitude: 37.249314, longitude: 27.66401 },
  BLQ: { iata: "BLQ", name: "Bologna Guglielmo Marconi Airport", city: "Bologna", country: "Italia", latitude: 44.5354, longitude: 11.2887 },
  BNX: { iata: "BNX", name: "Banja Luka International Airport", city: "Mahovljani", country: "Bosnia", latitude: 44.941399, longitude: 17.297501 },
  BOH: { iata: "BOH", name: "Bournemouth Airport", city: "Bournemouth", country: "Reino Unido", latitude: 50.780483, longitude: -1.839576 },
  BOJ: { iata: "BOJ", name: "Burgas Airport", city: "Burgas", country: "Bulgaria", latitude: 42.569917, longitude: 27.515173 },
  BRE: { iata: "BRE", name: "Bremen Airport", city: "Bremen", country: "Alemania", latitude: 53.046786, longitude: 8.78932 },
  BRI: { iata: "BRI", name: "Bari Karol Wojtyła International Airport", city: "Bari", country: "Italia", latitude: 41.138901, longitude: 16.760599 },
  BRQ: { iata: "BRQ", name: "Brno-Tuřany Airport", city: "Brno", country: "República Checa", latitude: 49.151276, longitude: 16.693972 },
  BRS: { iata: "BRS", name: "Bristol Airport", city: "Bristol", country: "Reino Unido", latitude: 51.382326, longitude: -2.716453 },
  BRU: { iata: "BRU", name: "Brussels Airport", city: "Zaventem", country: "Bélgica", latitude: 50.901402, longitude: 4.48444 },
  BTS: { iata: "BTS", name: "M. R. Štefánik Airport", city: "Bratislava", country: "Eslovaquia", latitude: 48.1702, longitude: 17.2127 },
  BUD: { iata: "BUD", name: "Budapest Liszt Ferenc International Airport", city: "Budapest", country: "Hungría", latitude: 47.43018, longitude: 19.262393 },
  BVA: { iata: "BVA", name: "Beauvais-Tillé airport", city: "Beauvais", country: "Francia", latitude: 49.454399, longitude: 2.11278 },
  BVE: { iata: "BVE", name: "Brive Souillac airport", city: "Brive", country: "Francia", latitude: 45.039722, longitude: 1.485556 },
  BZG: { iata: "BZG", name: "Ignacy Jan Paderewski Bydgoszcz Airport", city: "Bydgoszcz", country: "Polonia", latitude: 53.096802, longitude: 17.977699 },
  BZR: { iata: "BZR", name: "Béziers Vias airport", city: "Béziers", country: "Francia", latitude: 43.323502, longitude: 3.3539 },
  CAG: { iata: "CAG", name: "Cagliari Elmas Airport", city: "Cagliari", country: "Italia", latitude: 39.251499, longitude: 9.05428 },
  CCF: { iata: "CCF", name: "Carcassonne Salvaza Airport", city: "Carcassonne", country: "Francia", latitude: 43.216, longitude: 2.30632 },
  CDT: { iata: "CDT", name: "Castellón-Costa Azahar Airport", city: "Castellón de la Plana", country: "España", latitude: 40.213889, longitude: 0.073333 },
  CFU: { iata: "CFU", name: "Corfu Ioannis Kapodistrias International Airport", city: "Kerkyra (Corfu)", country: "Grecia", latitude: 39.60145, longitude: 19.912179 },
  CGN: { iata: "CGN", name: "Cologne Bonn Airport", city: "Köln (Cologne)", country: "Alemania", latitude: 50.865898, longitude: 7.14274 },
  CHQ: { iata: "CHQ", name: "Chania International Airport", city: "Souda", country: "Grecia", latitude: 35.531207, longitude: 24.150673 },
  CIA: { iata: "CIA", name: "Ciampino–G. B. Pastine International Airport", city: "Rome", country: "Italia", latitude: 41.798769, longitude: 12.595331 },
  CLJ: { iata: "CLJ", name: "Avram Iancu Cluj International Airport", city: "Cluj-Napoca", country: "Rumanía", latitude: 46.786042, longitude: 23.685733 },
  CPH: { iata: "CPH", name: "Copenhagen Kastrup Airport", city: "Copenhagen", country: "Dinamarca", latitude: 55.617901, longitude: 12.656 },
  CRL: { iata: "CRL", name: "Brussels South Charleroi Airport", city: "Charleroi", country: "Bélgica", latitude: 50.461963, longitude: 4.459562 },
  CRV: { iata: "CRV", name: "Crotone Sant'Anna Pythagoras Airport", city: "Isola di Capo Rizzuto (KR)", country: "Italia", latitude: 38.9972, longitude: 17.0802 },
  CTA: { iata: "CTA", name: "Catania-Fontanarossa Airport", city: "Catania", country: "Italia", latitude: 37.466801, longitude: 15.0664 },
  CUF: { iata: "CUF", name: "Cuneo International Airport", city: "Levaldigi (CN)", country: "Italia", latitude: 44.547458, longitude: 7.623045 },
  CWL: { iata: "CWL", name: "Cardiff International Airport", city: "Cardiff", country: "Reino Unido", latitude: 51.396702, longitude: -3.34333 },
  DBV: { iata: "DBV", name: "Dubrovnik Ruđer Bošković Airport", city: "Dubrovnik", country: "Croacia", latitude: 42.562247, longitude: 18.265543 },
  DLE: { iata: "DLE", name: "Dole Tavaux Airport", city: "Dole", country: "Francia", latitude: 47.038955, longitude: 5.427589 },
  DLM: { iata: "DLM", name: "Dalaman International Airport", city: "Dalaman", country: "Turquía", latitude: 36.7131, longitude: 28.7925 },
  DUB: { iata: "DUB", name: "Dublin Airport", city: "Dublin", country: "Irlanda", latitude: 53.428713, longitude: -6.262121 },
  EDI: { iata: "EDI", name: "Edinburgh Airport", city: "Edinburgh", country: "Reino Unido", latitude: 55.950145, longitude: -3.372288 },
  EFL: { iata: "EFL", name: "Kefallinia Airport", city: "Kefallinia Island", country: "Grecia", latitude: 38.120098, longitude: 20.5005 },
  EGC: { iata: "EGC", name: "Bergerac Dordogne-Périgord airport", city: "Bergerac", country: "Francia", latitude: 44.825298, longitude: 0.518611 },
  EIN: { iata: "EIN", name: "Eindhoven Airport", city: "Eindhoven", country: "Países Bajos", latitude: 51.4501, longitude: 5.37453 },
  EMA: { iata: "EMA", name: "East Midlands Airport", city: "Nottingham, Leicestershire", country: "Reino Unido", latitude: 52.8311, longitude: -1.32806 },
  ERH: { iata: "ERH", name: "Moulay Ali Cherif Airport", city: "Errachidia", country: "Marruecos", latitude: 31.9475, longitude: -4.39833 },
  ESU: { iata: "ESU", name: "Essaouira-Mogador Airport", city: "Essaouira", country: "Marruecos", latitude: 31.397499, longitude: -9.68167 },
  EXT: { iata: "EXT", name: "Exeter International Airport", city: "Exeter, Devon", country: "Reino Unido", latitude: 50.734261, longitude: -3.413984 },
  FAO: { iata: "FAO", name: "Faro - Gago Coutinho International Airport", city: "Faro", country: "Portugal", latitude: 37.015909, longitude: -7.970939 },
  FCO: { iata: "FCO", name: "Rome–Fiumicino Leonardo da Vinci International Airport", city: "Rome", country: "Italia", latitude: 41.804532, longitude: 12.251998 },
  FDH: { iata: "FDH", name: "Bodensee Airport Friedrichshafen", city: "Friedrichshafen", country: "Alemania", latitude: 47.671299, longitude: 9.51149 },
  FEZ: { iata: "FEZ", name: "Fes Saïss International Airport", city: "Saïss", country: "Marruecos", latitude: 33.927299, longitude: -4.97796 },
  FKB: { iata: "FKB", name: "Karlsruhe Baden-Baden Airport", city: "Rheinmünster", country: "Alemania", latitude: 48.7794, longitude: 8.0805 },
  FMM: { iata: "FMM", name: "Memmingen Allgau Airport", city: "Memmingen", country: "Alemania", latitude: 47.988092, longitude: 10.238248 },
  FMO: { iata: "FMO", name: "Münster Osnabrück Airport", city: "Greven", country: "Alemania", latitude: 52.133816, longitude: 7.688482 },
  FNC: { iata: "FNC", name: "Cristiano Ronaldo International Airport", city: "Funchal", country: "Portugal", latitude: 32.697812, longitude: -16.774613 },
  FNI: { iata: "FNI", name: "Nîmes-Arles-Camargue Airport", city: "Nîmes/Garons", country: "Francia", latitude: 43.757401, longitude: 4.41635 },
  FRL: { iata: "FRL", name: "Forlì-Luigi Ridolfi International Airport", city: "Forlì (FC)", country: "Italia", latitude: 44.194801, longitude: 12.0701 },
  FSC: { iata: "FSC", name: "Figari Sud-Corse Airport", city: "Figari", country: "Francia", latitude: 41.50185, longitude: 9.097092 },
  FUE: { iata: "FUE", name: "Fuerteventura Airport", city: "El Matorral", country: "España", latitude: 28.4527, longitude: -13.8638 },
  GDN: { iata: "GDN", name: "Gdańsk Lech Wałęsa Airport", city: "Gdańsk", country: "Polonia", latitude: 54.377602, longitude: 18.4662 },
  GLA: { iata: "GLA", name: "Glasgow Airport", city: "Glasgow", country: "Reino Unido", latitude: 55.871899, longitude: -4.43306 },
  GNB: { iata: "GNB", name: "Grenoble Alpes Isère Airport", city: "Grenoble", country: "Francia", latitude: 45.3629, longitude: 5.32937 },
  GOA: { iata: "GOA", name: "Genoa Cristoforo Colombo Airport", city: "Genova (GE)", country: "Italia", latitude: 44.412039, longitude: 8.840732 },
  GOT: { iata: "GOT", name: "Göteborg Landvetter Airport", city: "Göteborg", country: "Suecia", latitude: 57.6628, longitude: 12.2798 },
  GRO: { iata: "GRO", name: "Girona-Costa Brava Airport", city: "Girona", country: "España", latitude: 41.904639, longitude: 2.761774 },
  HAM: { iata: "HAM", name: "Hamburg Helmut Schmidt Airport", city: "Hamburg", country: "Alemania", latitude: 53.630402, longitude: 9.98823 },
  HEL: { iata: "HEL", name: "Helsinki Vantaa Airport", city: "Helsinki (Vantaa)", country: "Finlandia", latitude: 60.318363, longitude: 24.963341 },
  HER: { iata: "HER", name: "Heraklion International Nikos Kazantzakis Airport", city: "Heraklion", country: "Grecia", latitude: 35.339699, longitude: 25.1803 },
  HHN: { iata: "HHN", name: "Frankfurt-Hahn Airport", city: "Frankfurt am Main (Lautzenhausen)", country: "Alemania", latitude: 49.946353, longitude: 7.261734 },
  IAS: { iata: "IAS", name: "Iaşi International Airport", city: "Iaşi", country: "Rumanía", latitude: 47.179633, longitude: 27.621431 },
  IBZ: { iata: "IBZ", name: "Ibiza Airport", city: "Ibiza (Eivissa)", country: "España", latitude: 38.872898, longitude: 1.37312 },
  INI: { iata: "INI", name: "Niš Constantine the Great Airport", city: "Niš", country: "Serbia", latitude: 43.336538, longitude: 21.856242 },
  JMK: { iata: "JMK", name: "Mykonos Island National Airport", city: "Mykonos", country: "Grecia", latitude: 37.435101, longitude: 25.348101 },
  JSI: { iata: "JSI", name: "Skiathos Island National Airport", city: "Skiathos", country: "Grecia", latitude: 39.177101, longitude: 23.5037 },
  JTR: { iata: "JTR", name: "Santorini International Airport", city: "Santorini Island", country: "Grecia", latitude: 36.400045, longitude: 25.478638 },
  KGS: { iata: "KGS", name: "Kos International Airport \"Ippokratis\"", city: "Kos Island", country: "Grecia", latitude: 36.794523, longitude: 27.09115 },
  KIR: { iata: "KIR", name: "Kerry Airport", city: "Farranfore", country: "Irlanda", latitude: 52.180901, longitude: -9.52378 },
  KLU: { iata: "KLU", name: "Klagenfurt Airport", city: "Klagenfurt am Wörthersee", country: "Austria", latitude: 46.642502, longitude: 14.3377 },
  KLX: { iata: "KLX", name: "Kalamata Airport", city: "Kalamata", country: "Grecia", latitude: 37.068298, longitude: 22.025499 },
  KRK: { iata: "KRK", name: "Kraków John Paul II International Airport", city: "Balice", country: "Polonia", latitude: 50.077702, longitude: 19.7848 },
  KSC: { iata: "KSC", name: "Košice International Airport", city: "Košice", country: "Eslovaquia", latitude: 48.663101, longitude: 21.2411 },
  KTW: { iata: "KTW", name: "Katowice Wojciech Korfanty International Airport", city: "Katowice", country: "Polonia", latitude: 50.476015, longitude: 19.080705 },
  KUN: { iata: "KUN", name: "Kaunas International Airport", city: "Kaunas", country: "Lituania", latitude: 54.963965, longitude: 24.08582 },
  LBA: { iata: "LBA", name: "Leeds Bradford Airport", city: "Leeds, West Yorkshire", country: "Reino Unido", latitude: 53.865898, longitude: -1.66057 },
  LBC: { iata: "LBC", name: "Lübeck Blankensee Airport", city: "Lübeck", country: "Alemania", latitude: 53.805401, longitude: 10.7192 },
  LCA: { iata: "LCA", name: "Larnaca International Airport", city: "Larnaca", country: "Chipre", latitude: 34.875099, longitude: 33.624901 },
  LCJ: { iata: "LCJ", name: "Łódź Władysław Reymont Airport", city: "Łódź", country: "Polonia", latitude: 51.721901, longitude: 19.3981 },
  LDE: { iata: "LDE", name: "Tarbes-Lourdes-Pyrénées Airport", city: "Tarbes/Lourdes/Pyrénées", country: "Francia", latitude: 43.178699, longitude: -0.006439 },
  LDY: { iata: "LDY", name: "City of Derry Airport", city: "Derry, Derry and Strabane", country: "Reino Unido", latitude: 55.042801, longitude: -7.16111 },
  LEI: { iata: "LEI", name: "Almería Airport", city: "Almería", country: "España", latitude: 36.843899, longitude: -2.3701 },
  LGW: { iata: "LGW", name: "London Gatwick Airport", city: "London", country: "Reino Unido", latitude: 51.148744, longitude: -0.185739 },
  LIG: { iata: "LIG", name: "Limoges Airport", city: "Limoges/Bellegarde", country: "Francia", latitude: 45.862801, longitude: 1.17944 },
  LIL: { iata: "LIL", name: "Lille Airport", city: "Lesquin", country: "Francia", latitude: 50.566564, longitude: 3.102429 },
  LIS: { iata: "LIS", name: "Lisbon Humberto Delgado Airport", city: "Lisbon", country: "Portugal", latitude: 38.7813, longitude: -9.13592 },
  LNZ: { iata: "LNZ", name: "Linz-Hörsching Airport", city: "Linz", country: "Austria", latitude: 48.235362, longitude: 14.188128 },
  LPA: { iata: "LPA", name: "Gran Canaria Airport", city: "Gran Canaria Island", country: "España", latitude: 27.9319, longitude: -15.3866 },
  LPL: { iata: "LPL", name: "Liverpool John Lennon Airport", city: "Liverpool", country: "Reino Unido", latitude: 53.334863, longitude: -2.849637 },
  LRH: { iata: "LRH", name: "La Rochelle Île de Ré Airport", city: "La Rochelle", country: "Francia", latitude: 46.179199, longitude: -1.19528 },
  LTN: { iata: "LTN", name: "London Luton Airport", city: "Luton, Luton", country: "Reino Unido", latitude: 51.874699, longitude: -0.368333 },
  LUX: { iata: "LUX", name: "Luxembourg-Findel International Airport", city: "Luxembourg", country: "Luxemburgo", latitude: 49.626845, longitude: 6.212134 },
  LUZ: { iata: "LUZ", name: "Lublin Airport", city: "Lublin", country: "Polonia", latitude: 51.240157, longitude: 22.713461 },
  LXS: { iata: "LXS", name: "Limnos Airport", city: "Limnos Island", country: "Grecia", latitude: 39.917099, longitude: 25.2363 },
  MAD: { iata: "MAD", name: "Adolfo Suárez Madrid–Barajas Airport", city: "Madrid", country: "España", latitude: 40.493407, longitude: -3.572249 },
  MAH: { iata: "MAH", name: "Menorca Airport", city: "Mahón (Maó)", country: "España", latitude: 39.862598, longitude: 4.21865 },
  MAN: { iata: "MAN", name: "Manchester Airport", city: "Manchester, Greater Manchester", country: "Reino Unido", latitude: 53.349375, longitude: -2.279521 },
  MLA: { iata: "MLA", name: "Malta International Airport", city: "Valletta", country: "Malta", latitude: 35.845932, longitude: 14.491546 },
  MME: { iata: "MME", name: "Teesside International Airport", city: "Darlington, Durham", country: "Reino Unido", latitude: 54.509201, longitude: -1.42941 },
  MMX: { iata: "MMX", name: "Malmö Sturup Airport", city: "Malmö", country: "Suecia", latitude: 55.535564, longitude: 13.376327 },
  MRS: { iata: "MRS", name: "Marseille Provence Airport", city: "Marignane, Bouches-du-Rhône", country: "Francia", latitude: 43.438088, longitude: 5.2125 },
  MXP: { iata: "MXP", name: "Milan Malpensa International Airport", city: "Ferno (VA)", country: "Italia", latitude: 45.6306, longitude: 8.72811 },
  NAP: { iata: "NAP", name: "Naples International Airport", city: "Napoli", country: "Italia", latitude: 40.886002, longitude: 14.2908 },
  NCE: { iata: "NCE", name: "Nice-Côte d'Azur Airport", city: "Nice, Alpes-Maritimes", country: "Francia", latitude: 43.658401, longitude: 7.21587 },
  NCL: { iata: "NCL", name: "Newcastle International Airport", city: "Newcastle upon Tyne, Tyne and Wear", country: "Reino Unido", latitude: 55.037958, longitude: -1.689577 },
  NDR: { iata: "NDR", name: "Nador Al Aaroui International Airport", city: "Al Aaroui", country: "Marruecos", latitude: 34.9888, longitude: -3.02821 },
  NOC: { iata: "NOC", name: "Ireland West Airport Knock", city: "Charlestown", country: "Irlanda", latitude: 53.910439, longitude: -8.817002 },
  NQY: { iata: "NQY", name: "Cornwall Airport Newquay", city: "Newquay", country: "Reino Unido", latitude: 50.440601, longitude: -4.99541 },
  NRN: { iata: "NRN", name: "Weeze (Niederrhein) Airport", city: "Weeze", country: "Alemania", latitude: 51.601362, longitude: 6.141228 },
  NTE: { iata: "NTE", name: "Nantes Atlantique Airport", city: "Nantes", country: "Francia", latitude: 47.153198, longitude: -1.61073 },
  NUE: { iata: "NUE", name: "Nuremberg Airport", city: "Nuremberg", country: "Alemania", latitude: 49.498699, longitude: 11.078056 },
  NWI: { iata: "NWI", name: "Norwich Airport", city: "Norwich, Norfolk", country: "Reino Unido", latitude: 52.6758, longitude: 1.28278 },
  OLB: { iata: "OLB", name: "Olbia Costa Smeralda Airport", city: "Olbia (SS)", country: "Italia", latitude: 40.898953, longitude: 9.518457 },
  OPO: { iata: "OPO", name: "Francisco de Sá Carneiro Airport", city: "Porto", country: "Portugal", latitude: 41.2481, longitude: -8.68139 },
  ORK: { iata: "ORK", name: "Cork International Airport", city: "Cork", country: "Irlanda", latitude: 51.841301, longitude: -8.49111 },
  OSI: { iata: "OSI", name: "Osijek Airport", city: "Osijek(Klisa)", country: "Croacia", latitude: 45.462355, longitude: 18.811278 },
  OSL: { iata: "OSL", name: "Oslo-Gardermoen International Airport", city: "Oslo (Gardermoen)", country: "Noruega", latitude: 60.193901, longitude: 11.1004 },
  OSR: { iata: "OSR", name: "Leoš Janáček Airport Ostrava", city: "Mošnov", country: "República Checa", latitude: 49.696301, longitude: 18.111099 },
  OTP: { iata: "OTP", name: "Bucharest Henri Coandă International Airport", city: "Otopeni", country: "Rumanía", latitude: 44.571792, longitude: 26.103285 },
  OUD: { iata: "OUD", name: "Oujda Angads Airport", city: "Ahl Angad", country: "Marruecos", latitude: 34.789558, longitude: -1.926041 },
  OZZ: { iata: "OZZ", name: "Ouarzazate International Airport", city: "Ouarzazate", country: "Marruecos", latitude: 30.9391, longitude: -6.90943 },
  PAD: { iata: "PAD", name: "Paderborn Lippstadt Airport", city: "Büren", country: "Alemania", latitude: 51.612527, longitude: 8.617459 },
  PDV: { iata: "PDV", name: "Plovdiv International Airport", city: "Plovdiv", country: "Bulgaria", latitude: 42.067799, longitude: 24.8508 },
  PED: { iata: "PED", name: "Pardubice Airport", city: "Pardubice", country: "República Checa", latitude: 50.015049, longitude: 15.73981 },
  PEG: { iata: "PEG", name: "Perugia San Francesco d'Assisi – Umbria International Airport", city: "Perugia (PG)", country: "Italia", latitude: 43.095901, longitude: 12.5132 },
  PFO: { iata: "PFO", name: "Paphos International Airport", city: "Paphos", country: "Chipre", latitude: 34.717999, longitude: 32.485699 },
  PGF: { iata: "PGF", name: "Perpignan-Rivesaltes (Llabanère) Airport", city: "Perpignan/Rivesaltes", country: "Francia", latitude: 42.740398, longitude: 2.87067 },
  PIK: { iata: "PIK", name: "Glasgow Prestwick Airport", city: "Prestwick, South Ayrshire", country: "Reino Unido", latitude: 55.501499, longitude: -4.577182 },
  PIS: { iata: "PIS", name: "Poitiers-Biard Airport", city: "Poitiers/Biard", country: "Francia", latitude: 46.5877, longitude: 0.306666 },
  PLQ: { iata: "PLQ", name: "Palanga International Airport", city: "Palanga", country: "Lituania", latitude: 55.973202, longitude: 21.093901 },
  PMF: { iata: "PMF", name: "Parma Airport", city: "Parma (PR)", country: "Italia", latitude: 44.826351, longitude: 10.29705 },
  PMI: { iata: "PMI", name: "Palma de Mallorca Airport", city: "Palma de Mallorca", country: "España", latitude: 39.551701, longitude: 2.73881 },
  PMO: { iata: "PMO", name: "Falcone–Borsellino Airport", city: "Palermo", country: "Italia", latitude: 38.175999, longitude: 13.091 },
  POZ: { iata: "POZ", name: "Poznań-Ławica Airport", city: "Poznań", country: "Polonia", latitude: 52.421598, longitude: 16.823359 },
  PRG: { iata: "PRG", name: "Václav Havel Airport Prague", city: "Prague", country: "República Checa", latitude: 50.100874, longitude: 14.259911 },
  PSA: { iata: "PSA", name: "Pisa International Airport", city: "Pisa (PI)", country: "Italia", latitude: 43.683899, longitude: 10.3927 },
  PSR: { iata: "PSR", name: "Abruzzo Airport", city: "Pescara", country: "Italia", latitude: 42.431079, longitude: 14.182981 },
  PUY: { iata: "PUY", name: "Pula Airport", city: "Pula", country: "Croacia", latitude: 44.893501, longitude: 13.9222 },
  PVK: { iata: "PVK", name: "Aktion National Airport", city: "Preveza", country: "Grecia", latitude: 38.925499, longitude: 20.765301 },
  QSR: { iata: "QSR", name: "Salerno Costa d'Amalfi Airport", city: "Salerno", country: "Italia", latitude: 40.620399, longitude: 14.9113 },
  RAK: { iata: "RAK", name: "Marrakesh Menara Airport", city: "Marrakesh", country: "Marruecos", latitude: 31.604807, longitude: -8.035788 },
  RBA: { iata: "RBA", name: "Rabat-Salé Airport", city: "Rabat", country: "Marruecos", latitude: 34.051498, longitude: -6.75152 },
  RDZ: { iata: "RDZ", name: "Rodez–Aveyron Airport", city: "Rodez/Marcillac", country: "Francia", latitude: 44.407902, longitude: 2.48267 },
  REG: { iata: "REG", name: "Reggio Calabria Airport", city: "Reggio Calabria", country: "Italia", latitude: 38.071201, longitude: 15.6516 },
  REU: { iata: "REU", name: "Reus Airport", city: "Reus", country: "España", latitude: 41.147509, longitude: 1.168354 },
  RHO: { iata: "RHO", name: "Rhodes International Airport \"Diagoras\"", city: "Rhodes", country: "Grecia", latitude: 36.405399, longitude: 28.086201 },
  RIX: { iata: "RIX", name: "Riga International Airport", city: "Riga", country: "Letonia", latitude: 56.920752, longitude: 23.970711 },
  RJK: { iata: "RJK", name: "Rijeka Airport", city: "Rijeka(Omišalj)", country: "Croacia", latitude: 45.216376, longitude: 14.57085 },
  RMI: { iata: "RMI", name: "Federico Fellini International Airport", city: "Rimini (RN)", country: "Italia", latitude: 44.020024, longitude: 12.612198 },
  RMU: { iata: "RMU", name: "Region of Murcia International Airport", city: "Corvera", country: "España", latitude: 37.802852, longitude: -1.124884 },
  RVN: { iata: "RVN", name: "Rovaniemi Airport", city: "Rovaniemi", country: "Finlandia", latitude: 66.563327, longitude: 25.829751 },
  RZE: { iata: "RZE", name: "Rzeszów-Jasionka Airport", city: "Jasionka", country: "Polonia", latitude: 50.109791, longitude: 22.024155 },
  SCN: { iata: "SCN", name: "Saarbrücken Airport", city: "Saarbrücken", country: "Alemania", latitude: 49.214545, longitude: 7.109735 },
  SCQ: { iata: "SCQ", name: "Santiago-Rosalía de Castro Airport", city: "Santiago de Compostela", country: "España", latitude: 42.896301, longitude: -8.41514 },
  SDR: { iata: "SDR", name: "Seve Ballesteros-Santander Airport", city: "Santander", country: "España", latitude: 43.427101, longitude: -3.82001 },
  SFT: { iata: "SFT", name: "Skellefteå Airport", city: "Skellefteå", country: "Suecia", latitude: 64.624802, longitude: 21.0769 },
  SJJ: { iata: "SJJ", name: "Sarajevo International Airport", city: "Sarajevo", country: "Bosnia", latitude: 43.8246, longitude: 18.331499 },
  SKG: { iata: "SKG", name: "Thessaloniki Macedonia International Airport", city: "Thessaloniki", country: "Grecia", latitude: 40.51928, longitude: 22.970009 },
  SNN: { iata: "SNN", name: "Shannon Airport", city: "Shannon", country: "Irlanda", latitude: 52.702, longitude: -8.92482 },
  SOF: { iata: "SOF", name: "Sofia Airport", city: "Sofia", country: "Bulgaria", latitude: 42.696357, longitude: 23.417671 },
  SPU: { iata: "SPU", name: "Split Saint Jerome Airport", city: "Split", country: "Croacia", latitude: 43.538898, longitude: 16.298 },
  STN: { iata: "STN", name: "London Stansted Airport", city: "London, Essex", country: "Reino Unido", latitude: 51.884998, longitude: 0.235 },
  SUF: { iata: "SUF", name: "Lamezia Terme Sant'Eufemia International Airport", city: "Lamezia Terme (CZ)", country: "Italia", latitude: 38.906214, longitude: 16.246007 },
  SVQ: { iata: "SVQ", name: "Seville Airport", city: "Seville", country: "España", latitude: 37.417999, longitude: -5.89311 },
  SZG: { iata: "SZG", name: "Salzburg Airport", city: "Salzburg", country: "Austria", latitude: 47.793301, longitude: 13.0043 },
  SZY: { iata: "SZY", name: "Olsztyn-Mazury Airport", city: "Szymany", country: "Polonia", latitude: 53.481899, longitude: 20.9377 },
  SZZ: { iata: "SZZ", name: "Solidarity Szczecin–Goleniów Airport", city: "Szczecin(Glewice)", country: "Polonia", latitude: 53.584702, longitude: 14.9022 },
  TFS: { iata: "TFS", name: "Tenerife Sur Airport", city: "Tenerife", country: "España", latitude: 28.0445, longitude: -16.5725 },
  TGD: { iata: "TGD", name: "Podgorica Airport / Podgorica Golubovci Airbase", city: "Podgorica", country: "Montenegro", latitude: 42.359402, longitude: 19.2519 },
  TIA: { iata: "TIA", name: "Tirana International Airport Mother Teresa", city: "Rinas", country: "Albania", latitude: 41.4147, longitude: 19.7206 },
  TLL: { iata: "TLL", name: "Lennart Meri Tallinn Airport", city: "Tallinn", country: "Estonia", latitude: 59.413246, longitude: 24.83264 },
  TLS: { iata: "TLS", name: "Toulouse-Blagnac Airport", city: "Toulouse/Blagnac", country: "Francia", latitude: 43.629101, longitude: 1.36382 },
  TNG: { iata: "TNG", name: "Tangier Ibn Battuta Airport", city: "Tangier", country: "Marruecos", latitude: 35.731741, longitude: -5.921459 },
  TPS: { iata: "TPS", name: "Vincenzo Florio Airport Trapani-Birgi", city: "Trapani (TP)", country: "Italia", latitude: 37.9114, longitude: 12.488 },
  TRF: { iata: "TRF", name: "Sandefjord Airport, Torp", city: "Sandefjord(Torp)", country: "Noruega", latitude: 59.186699, longitude: 10.2586 },
  TRN: { iata: "TRN", name: "Turin Airport", city: "Caselle Torinese (TO)", country: "Italia", latitude: 45.200802, longitude: 7.64963 },
  TRS: { iata: "TRS", name: "Trieste Airport", city: "Ronchi dei Legionari/Trieste", country: "Italia", latitude: 45.827499, longitude: 13.4722 },
  TSF: { iata: "TSF", name: "Treviso Airport", city: "Treviso (TV)", country: "Italia", latitude: 45.648399, longitude: 12.1944 },
  TTU: { iata: "TTU", name: "Sania Ramel Airport", city: "Tétouan", country: "Marruecos", latitude: 35.594299, longitude: -5.32002 },
  TUF: { iata: "TUF", name: "Tours Val de Loire Airport", city: "Tours, Indre-et-Loire", country: "Francia", latitude: 47.432201, longitude: 0.727606 },
  VAR: { iata: "VAR", name: "Varna Airport", city: "Varna", country: "Bulgaria", latitude: 43.232101, longitude: 27.8251 },
  VCE: { iata: "VCE", name: "Venice Marco Polo Airport", city: "Venezia (VE)", country: "Italia", latitude: 45.505299, longitude: 12.3519 },
  VIE: { iata: "VIE", name: "Vienna International Airport", city: "Vienna", country: "Austria", latitude: 48.110298, longitude: 16.5697 },
  VIT: { iata: "VIT", name: "Vitoria Airport", city: "Alava", country: "España", latitude: 42.882801, longitude: -2.72447 },
  VLC: { iata: "VLC", name: "Valencia Airport", city: "Valencia", country: "España", latitude: 39.489162, longitude: -0.480961 },
  VNO: { iata: "VNO", name: "Vilnius International Airport", city: "Vilnius", country: "Lituania", latitude: 54.634102, longitude: 25.285801 },
  VOL: { iata: "VOL", name: "Nea Anchialos National Airport", city: "Nea Anchialos", country: "Grecia", latitude: 39.219601, longitude: 22.7943 },
  VRN: { iata: "VRN", name: "Verona Villafranca Valerio Catullo Airport", city: "Caselle (VR)", country: "Italia", latitude: 45.394955, longitude: 10.887303 },
  VST: { iata: "VST", name: "Stockholm Västerås Airport", city: "Stockholm / Västerås", country: "Suecia", latitude: 59.589401, longitude: 16.6336 },
  VXO: { iata: "VXO", name: "Växjö Kronoberg Airport", city: "Växjö", country: "Suecia", latitude: 56.9291, longitude: 14.728 },
  WAW: { iata: "WAW", name: "Warsaw Chopin Airport", city: "Warsaw", country: "Polonia", latitude: 52.165699, longitude: 20.9671 },
  WMI: { iata: "WMI", name: "Warsaw Modlin Airport", city: "Nowy Dwór Mazowiecki", country: "Polonia", latitude: 52.451099, longitude: 20.6518 },
  WRO: { iata: "WRO", name: "Copernicus Wrocław Airport", city: "Wrocław", country: "Polonia", latitude: 51.103719, longitude: 16.882096 },
  XCR: { iata: "XCR", name: "Chalons Vatry airport", city: "Chalons en Champagne", country: "Francia", latitude: 48.77333, longitude: 4.20611 },
  ZAD: { iata: "ZAD", name: "Zadar Airport", city: "Zadar", country: "Croacia", latitude: 44.096986, longitude: 15.353565 },
  ZAG: { iata: "ZAG", name: "Zagreb Franjo Tuđman International Airport", city: "Velika Gorica", country: "Croacia", latitude: 45.742901, longitude: 16.0688 },
  ZAZ: { iata: "ZAZ", name: "Zaragoza Airport", city: "Zaragoza", country: "España", latitude: 41.666199, longitude: -1.04155 },
  ZTH: { iata: "ZTH", name: "Zakynthos International Airport Dionysios Solomos", city: "Zakynthos", country: "Grecia", latitude: 37.7509, longitude: 20.8843 },
};

export function findCountryByIata(iata: string): CountryAirports | null {
  const code = iata.toUpperCase();
  return COUNTRY_BY_IATA.get(code) || null;
}

export function findAirportByIata(iata: string): Airport | null {
  const code = iata.toUpperCase();
  return AIRPORT_BY_IATA.get(code) || null;
}

export function getAirportMeta(iata: string): AirportMeta | null {
  const code = iata.toUpperCase();
  return AIRPORT_META[code] || null;
}

import { apiFetchWithStatus } from "@/modules/shared/api";

export async function searchAirportsAsync(query: string): Promise<AirportMeta[]> {
  if (!query || query.trim().length < 2) return [];
  const response = await apiFetchWithStatus<{ items: any[] }>(`/airports/seeds?q=${encodeURIComponent(query)}`);
  if (!response.ok) return [];
  return response.data.items.map(item => ({
    iata: item.iata,
    name: item.name,
    city: item.municipality,
    country: item.country_code,
    latitude: Number(item.latitude),
    longitude: Number(item.longitude),
  }));
}

export async function getAirportMetaAsync(iata: string): Promise<AirportMeta | null> {
  const code = iata.toUpperCase();
  if (AIRPORT_META[code]) {
    return AIRPORT_META[code];
  }
  const results = await searchAirportsAsync(code);
  const match = results.find(r => r.iata === code);
  if (match) {
    AIRPORT_META[code] = match; // cache it
    return match;
  }
  return null;
}



