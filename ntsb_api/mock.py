"""Synthetic sample data for offline development, demos and tests.

These records are INVENTED. They mimic the *shape* of CAROL export JSON so the
whole stack (normalizer, API, UI) can run without network access. Every NTSB
number starts with ``DEMO`` so they can never be mistaken for real cases.
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any

_MAKES = [("BOEING", ["737-800", "737-9", "777-200ER", "787-9", "767-300"]),
          ("AIRBUS", ["A320-214", "A321-231", "A220-300", "A330-300"]),
          ("EMBRAER", ["ERJ 170-200 LR", "ERJ 175", "EMB-145"]),
          ("BOMBARDIER", ["CL-600-2D24", "DHC-8-402"]),
          ("CESSNA", ["172S", "208B"]), ("PIPER", ["PA-28-181"])]
_OPERATORS = ["Example Air Lines", "Sample Airways", "Demo Regional", "Test Cargo Co",
              "Placeholder Air", "Private owner"]
_PLACES = [("Seattle", "WA"), ("Chicago", "IL"), ("Denver", "CO"), ("Atlanta", "GA"),
           ("Dallas", "TX"), ("Anchorage", "AK"), ("Phoenix", "AZ"), ("Newark", "NJ"),
           ("San Francisco", "CA"), ("Miami", "FL")]
_AIRPORTS = {"Seattle": "SEA", "Chicago": "ORD", "Denver": "DEN", "Atlanta": "ATL",
             "Dallas": "DFW", "Anchorage": "ANC", "Phoenix": "PHX", "Newark": "EWR",
             "San Francisco": "SFO", "Miami": "MIA"}
_SCENARIOS = [
    ("turbulence encounter during descent; a flight attendant was seriously injured",
     "The airplane's encounter with convective turbulence during descent.",
     ["Environmental issues-Weather-Turbulence (convective)-Effect on operation",
      "Personnel issues-Task performance-Use of equip/system-Cabin crew"]),
    ("runway excursion after landing on a contaminated runway",
     "The flight crew's failure to maintain directional control during the landing roll on a contaminated runway.",
     ["Environmental issues-Conditions/weather-Runway contamination", "Personnel issues-Action/decision-Directional control"]),
    ("engine failure shortly after takeoff followed by a return to the departure airport",
     "A fatigue fracture of a fan blade, which resulted in an uncontained engine failure.",
     ["Aircraft-Aircraft power plant-Engine (turbofan)-Fan section-Fatigue/wear/corrosion"]),
    ("thrust reverser did not deploy normally during landing rollout",
     "Slow deployment of the left thrust reverser due to a degraded actuator, resulting in asymmetric deceleration.",
     ["Aircraft-Aircraft power plant-Thrust reverser system-Malfunction"]),
    ("loss of separation with another aircraft on the taxiway",
     "The ground controller's failure to ensure separation between taxiing aircraft.",
     ["Personnel issues-Action/decision-ATC personnel-Clearance"]),
    ("hard landing in gusty crosswind conditions resulting in substantial damage",
     "The pilot's improper flare in gusting crosswind conditions, which resulted in a hard landing.",
     ["Environmental issues-Conditions/weather-Gusts", "Personnel issues-Task performance-Landing flare"]),
]


def _make_cases(n: int = 60, seed: int = 7) -> list[dict[str, Any]]:
    rnd = random.Random(seed)
    out = []
    start = date(2015, 1, 1)
    for k in range(n):
        make, models = rnd.choice(_MAKES)
        model = rnd.choice(models)
        city, st = rnd.choice(_PLACES)
        when = start + timedelta(days=rnd.randint(0, 3950))
        scen = rnd.choice(_SCENARIOS)
        injury = rnd.choices(["None", "Minor", "Serious", "Fatal"], [5, 3, 3, 1])[0]
        part = "Part 91: General aviation" if make in ("CESSNA", "PIPER") else rnd.choice(
            ["Part 121: Air carrier", "Part 121: Air carrier", "Part 135: Air taxi & commuter"])
        fatal = rnd.randint(1, 4) if injury == "Fatal" else 0
        serious = rnd.randint(1, 3) if injury in ("Serious", "Fatal") else 0
        code = "DCA" if part.startswith("Part 121") else rnd.choice(["WPR", "CEN", "ERA"])
        ntsb = f"DEMO{str(when.year)[2:]}{code}{k:03d}"
        out.append({
            "cm_mkey": 900000 + k,
            "cm_ntsbNum": ntsb,
            "cm_eventDate": when.isoformat() + "T12:00:00Z",
            "cm_eventType": rnd.choices(["ACC", "INC"], [3, 1])[0],
            "cm_mode": "Aviation",
            "cm_city": city, "cm_state": st, "cm_country": "USA",
            "cm_Latitude": round(rnd.uniform(25, 61), 4),
            "cm_Longitude": round(rnd.uniform(-150, -75), 4),
            "airportId": _AIRPORTS[city], "airportName": f"{city} (sample)",
            "cm_highestInjury": injury,
            "cm_fatalInjuryCount": fatal, "cm_seriousInjuryCount": serious,
            "cm_minorInjuryCount": rnd.randint(0, 5) if injury != "None" else 0,
            "cm_completionStatus": rnd.choice(["Completed", "Completed", "In work"]),
            "cm_reportType": "Final" if k % 3 else "Preliminary",
            "cm_originalPublishedDate": (when + timedelta(days=rnd.randint(200, 700))).isoformat(),
            "cm_hasSafetyRec": rnd.random() < 0.2,
            "cm_probableCause": scen[1],
            "prelimNarrative": f"SYNTHETIC SAMPLE. On {when:%B %d, %Y}, a {make.title()} {model} "
                               f"experienced a {scen[0]} near {city}, {st}.",
            "factualNarrative": f"SYNTHETIC SAMPLE. The flight was operating under {part}. "
                                f"The crew reported a {scen[0]}. Data from the flight data recorder "
                                f"and crew interviews were reviewed.",
            "analysisNarrative": "SYNTHETIC SAMPLE. Analysis text would appear here for completed investigations.",
            "cm_findings": [{"findingText": t, "causeFactor": "C" if j == 0 else "F"}
                            for j, t in enumerate(scen[2])],
            "cm_vehicles": [{
                "make": make, "model": model,
                "registrationNumber": f"N{rnd.randint(100, 999)}{rnd.choice('ABCDEFGHJK')}{rnd.choice('ABCDEFGHJK')}",
                "aircraftCategory": "AIR",
                "damageLevel": rnd.choice(["None", "Minor", "Substantial", "Destroyed"]),
                "operatorName": rnd.choice(_OPERATORS[:5]) if part.startswith("Part 1") else "Private owner",
                "regulationFlightConductedUnder": part,
                "numberOfEngines": 2 if make not in ("CESSNA", "PIPER") else 1,
            }],
        })
    return sorted(out, key=lambda c: c["cm_eventDate"], reverse=True)


MOCK_CASES = _make_cases()


def mock_docket_html(ntsb_number: str) -> str:
    rows = "".join(
        f'<tr><td>{i}</td><td><a href="Document/docBLOB?ID={4000 + i}&FileExtension=pdf&FileName={t.replace(" ", "_")}">'
        f"{t} (sample)</a></td><td>{p}</td></tr>"
        for i, (t, p) in enumerate([("Operational Factors Factual Report", 24),
                                     ("Airworthiness Group Chairman Factual Report", 41),
                                     ("Flight Data Recorder Specialist's Factual Report", 33),
                                     ("Interview Summaries", 18),
                                     ("Photographs", 12)], start=1))
    return f"<html><body><h1>Docket {ntsb_number}</h1><table>{rows}</table></body></html>"
