import { sharedEs } from "./shared";
import { accountEs } from "./domains/account";
import { preferencesEs } from "./domains/preferences";
import { supportEs } from "./domains/support";
import { publicEs } from "./domains/public";
import { dashboardEs } from "./domains/dashboard";
import { alertsEs } from "./domains/alerts";
import { recommendationsEs } from "./domains/recommendations";
import { suggestionsEs } from "./domains/suggestions";
import { adminEs } from "./domains/admin";
import { watchlistEs } from "./domains/watchlist";

const es = {
  shared: sharedEs,
  account: accountEs,
  preferences: preferencesEs,
  support: supportEs,
  public: publicEs,
  dashboard: dashboardEs,
  alerts: alertsEs,
  recommendations: recommendationsEs,
  suggestions: suggestionsEs,
  admin: adminEs,
  watchlist: watchlistEs,
};

export default es;
