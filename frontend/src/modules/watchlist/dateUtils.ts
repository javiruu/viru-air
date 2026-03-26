export function toIsoMonth(dateLike: string): string {
  if (!dateLike) return "";
  return dateLike.slice(0, 7);
}

export function monthLabel(month: string, locale = "es-ES"): string {
  if (!month) return "Sin datos";
  const [year, monthPart] = month.split("-");
  const d = new Date(Number(year), Number(monthPart) - 1, 1);
  return d.toLocaleDateString(locale, { month: "long", year: "numeric" });
}

export function shiftMonth(month: string, offset: number): string {
  if (!month) return "";
  const [y, m] = month.split("-").map(Number);
  const d = new Date(y, m - 1 + offset, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export function monthDays(month: string): string[] {
  if (!month) return [];
  const [y, m] = month.split("-").map(Number);
  const start = new Date(y, m - 1, 1);
  const end = new Date(y, m, 0);
  const out: string[] = [];
  for (let day = 1; day <= end.getDate(); day += 1) {
    out.push(`${y}-${String(m).padStart(2, "0")}-${String(day).padStart(2, "0")}`);
  }
  const mondayIndex = (start.getDay() + 6) % 7;
  for (let i = 0; i < mondayIndex; i += 1) {
    out.unshift("");
  }
  while (out.length % 7 !== 0) {
    out.push("");
  }
  return out;
}
