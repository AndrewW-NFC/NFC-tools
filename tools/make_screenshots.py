"""Generate documentation screenshots from the live templates.

Run:
  python tools/make_screenshots.py            # writes HTML mockups
  python tools/make_screenshots.py --png      # also renders PNG via Playwright
"""
from __future__ import annotations
import argparse
import asyncio
from datetime import date, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "src" / "nfc_tools" / "web" / "templates"
STATIC = ROOT / "src" / "nfc_tools" / "web" / "static"
OUT = ROOT / "docs" / "screenshots"


def fake_data():
	today = date.today()
	night = today.isoformat()
	return {
		"cfg": {
			"site": {"name": "Backyard, Arlington MA",
					 "latitude": 42.415, "longitude": -71.156,
					 "timezone": "America/New_York"},
			"schedule": {"start_time": "21:00", "end_time": "06:15", "segment_minutes": 60},
			"recording": {"device": "avfoundation:0"},
			"analyzers": {"enabled": ["birdnet", "nighthawk"], "birdnet_min_conf": 0.5},
		},
		"status": {
			"state": "recording", "session_date": night,
			"started_at": "2026-05-10T21:00:00", "ends_at": "2026-05-11T06:15:00",
			"recordings": [
				f"NFC_{night}_{night}_21-00-03.wav",
				f"NFC_{night}_{night}_22-00-04.wav",
			],
			"level_db": -28.4,
			"weather": {"available": True, "temp_f": 54.2,
						"wind_mph": 6.1, "cloud_pct": 22.0},
			"enabled": False, "backend": "launchd", "detail": "Not enabled",
		},
		"checks": [
			{"name": "Audio engine (ffmpeg)", "ok": True, "detail": "Found"},
			{"name": "Microphone", "ok": True, "detail": "USB Mic selected"},
			{"name": "Internet (weather)", "ok": True, "detail": "Reachable"},
			{"name": "Analyzer: birdnet", "ok": True, "detail": "Installed"},
			{"name": "Analyzer: nighthawk", "ok": True, "detail": "Installed"},
		],
		"nights": [(today - timedelta(days=i)).isoformat() for i in range(5)],
		"selected": night,
		"rows": [],
		"summary": [
			{"analyzer": "nighthawk", "species": "Catharus ustulatus",
			 "common_name": "Swainson's Thrush", "count": 12, "max_conf": 0.91,
			 "first": "2026-05-11T01:14:08", "last": "2026-05-11T04:51:30"},
			{"analyzer": "birdnet", "species": "Zonotrichia albicollis",
			 "common_name": "White-throated Sparrow", "count": 7, "max_conf": 0.84,
			 "first": "2026-05-11T02:02:11", "last": "2026-05-11T05:02:22"},
		],
		"filters": {"min_conf": 0.5, "analyzer": "", "species": ""},
		"devices": [{"id": "avfoundation:0", "name": "Built-in Microphone"},
					{"id": "avfoundation:1", "name": "USB Audio Interface"}],
		"analyzers_status": {"birdnet": {"installed": True}, "nighthawk": {"installed": True}},
	}


def render(env, name, data):
	tpl = env.get_template(name)
	css = (STATIC / "style.css").read_text()
	html = tpl.render(request=None, **data)
	head_inject = f"<style>{css}</style>"
	return html.replace('<link rel="stylesheet" href="/static/style.css" />', head_inject)


async def to_png(html_path, png_path):
	from playwright.async_api import async_playwright
	async with async_playwright() as p:
		b = await p.chromium.launch()
		ctx = await b.new_context(viewport={"width": 1100, "height": 800})
		page = await ctx.new_page()
		await page.goto(html_path.as_uri())
		await page.screenshot(path=str(png_path), full_page=True)
		await b.close()


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--png", action="store_true")
	args = parser.parse_args()

	OUT.mkdir(parents=True, exist_ok=True)
	env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape())
	data = fake_data()
	pages = ["dashboard.html", "wizard.html", "results.html",
			 "detections.html", "settings.html", "schedule.html"]
	html_paths = []
	for name in pages:
		try:
			html = render(env, name, data)
		except Exception as e:
			print(f"skip {name}: {e}")
			continue
		out = OUT / name
		out.write_text(html)
		html_paths.append(out)
		print(f"wrote {out}")
	if args.png:
		async def _all():
			for h in html_paths:
				await to_png(h, h.with_suffix(".png"))
				print(f"wrote {h.with_suffix('.png')}")
		asyncio.run(_all())


if __name__ == "__main__":
	main()
