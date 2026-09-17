"""Weather-only adaptation of NFC acoustic environment forecast v2.2.12.

Upstream: https://github.com/AndrewW-NFC/nfc-acoustic-environment-forecast
Copyright (c) 2026 Andrew Whitacre, MIT license (see LICENSE).
Foliage and insect effects are neutral (zero), not favorable assumptions.
"""

from math import floor, isfinite

REPOSITORY = "https://github.com/AndrewW-NFC/nfc-acoustic-environment-forecast"
MODEL_VERSION = "2.2.12-weather-only-1"
QUALIFICATION = "weather-only estimate; foliage and insect noise not assessed"
WEATHER_INPUTS = {
    "relative_humidity_pct": "relative_humidity_2m",
    "precipitation_mm": "precipitation",
    "surface_gust_mph": "wind_gusts_10m",
    "surface_pressure_hpa": "surface_pressure",
    "visibility_m": "visibility",
}
ACOUSTIC_FIELDS = [
    *WEATHER_INPUTS,
    "acoustic_score",
    "acoustic_descriptor",
    "acoustic_model_version",
]


def descriptor(score: float) -> str:
    displayed = floor(score * 2 + 0.5) / 2
    for threshold, label in [
        (9, "Excellent"),
        (8, "Very Good"),
        (7, "Good"),
        (6, "Fair"),
        (5, "Marginal"),
        (3, "Poor"),
        (1.5, "Very Poor"),
    ]:
        if displayed >= threshold:
            return label
    return "Unusable"


def _gust(wind: float, gust: float) -> float:
    if gust == 0:
        return wind
    if gust > 22.4:
        return 22.4
    return min(gust, wind * 2) if wind > 0 else gust


def score_weather(row: dict) -> dict:
    result = {
        "acoustic_score": "",
        "acoustic_descriptor": "unavailable",
        "acoustic_model_version": MODEL_VERSION,
    }
    try:

        def number(key):
            value = float(row[key])
            if not isfinite(value):
                raise ValueError(key)
            return value

        temp = (number("surface_temp_f") - 32) * 5 / 9
        wind = number("surface_wind_mph") * 0.44704
        gust = _gust(wind, number("surface_gust_mph") * 0.44704)
        humidity = number("relative_humidity_pct")
        rain = number("precipitation_mm")
        cloud = number("cloud_cover_pct")
        pressure = number("surface_pressure_hpa")
        # Preserve upstream's visibility estimate when this field is unavailable.
        visibility = (
            number("visibility_m")
            if row.get("visibility_m") not in (None, "")
            else 3000
            if rain > 2
            else 5000
            if rain > 0.5
            else 7000
            if cloud > 80
            else 10000
        )
        if (
            wind < 0
            or gust < 0
            or rain < 0
            or visibility < 0
            or pressure <= 0
            or not 0 <= humidity <= 100
            or not 0 <= cloud <= 100
        ):
            raise ValueError("Invalid weather")
    except (KeyError, TypeError, ValueError):
        return result

    ground = wind * (2 / 10) ** 0.20
    ground_gust = _gust(ground, gust * (2 / 10) ** 0.20)
    wind_d = next(
        (
            d
            for limit, d in [
                (1, 0),
                (1.5, 0.2),
                (3, 0.6),
                (4.5, 1.2),
                (6, 1.8),
                (8, 2.3),
            ]
            if ground < limit
        ),
        2.8,
    )
    wind_d = min(
        2.8,
        wind_d
        + (
            0.7
            if ground_gust >= 22.4
            else 0.5
            if ground_gust > 10
            else 0.3
            if ground_gust > 7
            else 0
        ),
    )
    rain_d = next(
        (
            d
            for limit, d in [(0.02, 0), (0.25, 0.25), (1, 0.65), (2.5, 1.2), (5, 1.7)]
            if rain < limit
        ),
        2,
    )
    diff = abs(humidity - 72)
    humidity_d = (
        0
        if diff < 3
        else 0.2
        if diff < 8
        else 0.4
        if 68 <= humidity <= 85
        else 0.7
        if 85 < humidity <= 92
        else 1.1
        if humidity > 92
        else 0.8
    )
    visibility_d = next(
        (
            d
            for limit, d in [
                (10000, 0),
                (8000, 0.1),
                (6000, 0.25),
                (4000, 0.45),
                (2000, 0.7),
            ]
            if visibility >= limit
        ),
        0.9,
    )
    cloud_d = (
        0
        if abs(cloud - 50) < 15
        else 0.15
        if cloud >= 70
        else 0.1
        if cloud >= 50
        else 0.2
        if cloud >= 30
        else 0.35
        if cloud >= 10
        else 0.6
    )
    pressure_d = next(
        (
            d
            for limit, d in [
                (1035, 0.3),
                (1030, 0.1),
                (1020, 0),
                (1015, 0.15),
                (1010, 0.3),
                (1005, 0.45),
            ]
            if pressure >= limit
        ),
        0.6,
    )
    temp_d = (
        0
        if abs(temp - 10) < 2
        else 0.15
        if 2 <= temp <= 18
        else 0.3
        if -1 <= temp <= 21
        else 0.5
    )
    # Seven weather effects total +4.25 at best; the two unknown site effects are zero.
    score = max(
        0,
        min(
            10,
            5
            + sum(
                [
                    1.4 - wind_d,
                    1 - rain_d,
                    0.55 - humidity_d,
                    0.45 - visibility_d,
                    0.3 - cloud_d,
                    0.3 - pressure_d,
                    0.25 - temp_d,
                ]
            ),
        ),
    )
    result.update(
        acoustic_score=round(score, 6), acoustic_descriptor=descriptor(score * 10 / 10)
    )
    return result


def acoustic_comment(row: dict) -> str:
    label = row.get("acoustic_descriptor") or "unavailable"
    return f"Acoustic conditions: {label} ({QUALIFICATION}) | Acoustic scoring: {REPOSITORY}"
