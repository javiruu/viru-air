import { sharedEs } from "./shared";
import { accountEs } from "./domains/account";
import { preferencesEs } from "./domains/preferences";
import { supportEs } from "./domains/support";
import { publicEs } from "./domains/public";
import { dashboardEs } from "./domains/dashboard";
import { alertsEs } from "./domains/alerts";
import { recommendationsEs } from "./domains/recommendations";
import { notificationsEs } from "./domains/notifications";
import { adminEs } from "./domains/admin";
import { watchlistEs } from "./domains/watchlist";
import { doorToDoorEs } from "./domains/doorToDoor";
import { hotelsEs } from "./domains/hotels";

const es = {
  shared: sharedEs,
  account: accountEs,
  preferences: preferencesEs,
  support: supportEs,
  public: publicEs,
  dashboard: dashboardEs,
  alerts: alertsEs,
  recommendations: recommendationsEs,
  notifications: notificationsEs,
  admin: adminEs,
  watchlist: watchlistEs,
  doorToDoor: doorToDoorEs,
  hotels: hotelsEs,
};

export default es;
