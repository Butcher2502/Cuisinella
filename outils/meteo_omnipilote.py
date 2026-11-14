#!/usr/bin/env python3
"""Prévisions météo pour OmniPilote (Extrême-Sud Corse).

Écrit un document JSON (sortie standard ou fichier donné en argument) à envoyer
dans la base de l'artifact OmniPilote : collection "meteo", document "jour".
Source principale : api.met.no (MET Norway, licence CC BY 4.0).
Secours : api.open-meteo.com.
"""
import json, sys, urllib.request, datetime
from collections import defaultdict
from zoneinfo import ZoneInfo

VILLES = [
    ("Sotta", 41.540, 9.179), ("Porto-Vecchio", 41.591, 9.279), ("Bonifacio", 41.387, 9.159),
    ("Sainte-Lucie", 41.698, 9.355), ("Solenzara", 41.855, 9.398),
    ("Sartène", 41.621, 8.975), ("Propriano", 41.676, 8.903),
]
TZ = ZoneInfo("Europe/Paris")
UA = "OmniPilote/1.0 tableau-de-bord-meteo"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def symbole(code):
    c = (code or "").split("_")[0]
    if "thunder" in c: return "orage"
    if "snow" in c or "sleet" in c: return "neige"
    if "rain" in c or "showers" in c: return "pluie"
    if c in ("fog",): return "brouillard"
    if c in ("cloudy",): return "couvert"
    if c in ("partlycloudy", "fair"): return "eclaircies"
    if c == "clearsky": return "soleil"
    return "couvert"

def metno(lat, lon):
    d = get(f"https://api.met.no/weatherapi/locationforecast/2.0/complete?lat={lat}&lon={lon}")
    jours = defaultdict(lambda: {"tmin": 99, "tmax": -99, "pluie": 0.0, "vent": 0, "rafale": 0, "sym": None, "symh": 99})
    actuel = None
    for t in d["properties"]["timeseries"]:
        dt = datetime.datetime.fromisoformat(t["time"].replace("Z", "+00:00")).astimezone(TZ)
        k = dt.date().isoformat(); j = jours[k]
        ins = t["data"]["instant"]["details"]
        tp = ins.get("air_temperature"); ws = ins.get("wind_speed", 0) * 3.6; wg = ins.get("wind_speed_of_gust", 0) * 3.6
        if tp is not None: j["tmin"] = min(j["tmin"], tp); j["tmax"] = max(j["tmax"], tp)
        j["vent"] = max(j["vent"], ws); j["rafale"] = max(j["rafale"], wg)
        n1 = t["data"].get("next_1_hours")
        if n1: j["pluie"] += n1.get("details", {}).get("precipitation_amount", 0)
        nx = n1 or t["data"].get("next_6_hours")
        if nx and abs(dt.hour - 13) < j["symh"]:
            j["symh"] = abs(dt.hour - 13); j["sym"] = nx["summary"]["symbol_code"]
        if actuel is None:
            actuel = {"temp": round(tp) if tp is not None else None, "vent": round(ws), "rafale": round(wg),
                      "ciel": symbole((nx or {}).get("summary", {}).get("symbol_code"))}
    out = []
    for k in sorted(jours)[:6]:
        j = jours[k]
        out.append({"date": k, "tmin": round(j["tmin"]), "tmax": round(j["tmax"]), "pluie": round(j["pluie"], 1),
                    "vent": round(j["vent"]), "rafale": round(j["rafale"]), "ciel": symbole(j["sym"])})
    return actuel, out

WMO = {0: "soleil", 1: "eclaircies", 2: "eclaircies", 3: "couvert", 45: "brouillard", 48: "brouillard"}
def wmo(c):
    if c in WMO: return WMO[c]
    if c >= 95: return "orage"
    if c in (71, 73, 75, 77, 85, 86): return "neige"
    return "pluie"

def openmeteo():
    lat = ",".join(str(v[1]) for v in VILLES); lon = ",".join(str(v[2]) for v in VILLES)
    d = get("https://api.open-meteo.com/v1/forecast?latitude=" + lat + "&longitude=" + lon +
            "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,wind_gusts_10m_max"
            "&current=temperature_2m,weather_code,wind_speed_10m,wind_gusts_10m&timezone=Europe%2FParis&forecast_days=6")
    if isinstance(d, dict): d = [d]
    res = []
    for (nom, _, _), x in zip(VILLES, d):
        dd = x["daily"]; c = x["current"]
        jours = [{"date": dd["time"][i], "tmin": round(dd["temperature_2m_min"][i]), "tmax": round(dd["temperature_2m_max"][i]),
                  "pluie": round(dd["precipitation_sum"][i] or 0, 1), "vent": round(dd["wind_speed_10m_max"][i]),
                  "rafale": round(dd["wind_gusts_10m_max"][i]), "ciel": wmo(dd["weather_code"][i])} for i in range(len(dd["time"]))]
        res.append({"ville": nom, "actuel": {"temp": round(c["temperature_2m"]), "vent": round(c["wind_speed_10m"]),
                    "rafale": round(c["wind_gusts_10m"]), "ciel": wmo(c["weather_code"])}, "jours": jours})
    return res

def main():
    villes, source = [], "MET Norway (api.met.no), CC BY 4.0"
    try:
        for nom, lat, lon in VILLES:
            a, j = metno(lat, lon)
            villes.append({"ville": nom, "actuel": a, "jours": j})
    except Exception as e:
        print("met.no indisponible :", e, file=sys.stderr)
        villes, source = openmeteo(), "Open-Meteo (api.open-meteo.com), CC BY 4.0"
    doc = {"maj": datetime.datetime.now(TZ).isoformat(timespec="minutes"), "source": source, "villes": villes}
    txt = json.dumps(doc, ensure_ascii=False)
    if len(sys.argv) > 1: open(sys.argv[1], "w").write(txt)
    else: print(txt)

if __name__ == "__main__":
    main()
