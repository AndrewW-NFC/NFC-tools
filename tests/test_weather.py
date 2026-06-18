from nfc_tools.weather import append_environment_text, environment_text_line


def test_environment_text_line_is_paste_ready_conditions_only():
    row = {
        "surface_temp_f": 63.4,
        "surface_wind_mph": 4.8,
        "surface_wind_dir_deg": 210,
        "wind_950hpa_mph": 11.2,
        "wind_950hpa_dir_deg": 235,
        "cloud_cover_pct": 18,
        "source": "Open-Meteo",
        "notes": "not included",
    }

    assert environment_text_line(row) == (
        "Temperature (F): 63.4° | Wind speed: 4.8 mph | Wind direction: 210° | "
        "950 hPa wind speed: 11.2 mph | 950 hPa wind direction: 235° | Cloud cover: 18%"
    )


def test_append_environment_text_writes_one_line_per_snapshot(tmp_path):
    row = {
        "surface_temp_f": "",
        "surface_wind_mph": None,
        "surface_wind_dir_deg": "",
        "wind_950hpa_mph": "",
        "wind_950hpa_dir_deg": "",
        "cloud_cover_pct": "",
    }

    path = append_environment_text(tmp_path, row)

    assert path == tmp_path / "logs" / "environmental_conditions.txt"
    assert path.read_text(encoding="utf-8") == (
        "Temperature (F): unavailable | Wind speed: unavailable | Wind direction: unavailable | "
        "950 hPa wind speed: unavailable | 950 hPa wind direction: unavailable | Cloud cover: unavailable\n"
    )
