"""Download endpoints for CSV / eBird exports."""
from __future__ import annotations
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import Response

from .. import detections as det
from ..config import load as load_cfg
from ..exporters import to_rich_csv, to_ebird_csv

router = APIRouter()


def _fetch(session_date: str, min_conf: float,
		   analyzer: Optional[str], species: Optional[str]):
	return det.collect_for_night(session_date, min_confidence=min_conf,
								 analyzer=analyzer or None,
								 species=species or None)


@router.get("/export/{session_date}.csv")
def export_rich(session_date: str, min_conf: float = 0.0,
				analyzer: Optional[str] = None, species: Optional[str] = None):
	rows = _fetch(session_date, min_conf, analyzer, species)
	body = to_rich_csv(rows)
	return Response(
		body, media_type="text/csv",
		headers={"Content-Disposition": f'attachment; filename="nfc-{session_date}.csv"'},
	)


@router.get("/export/{session_date}-ebird.csv")
def export_ebird(session_date: str, min_conf: float = 0.7,
				 analyzer: Optional[str] = None, species: Optional[str] = None):
	cfg = load_cfg()
	rows = _fetch(session_date, min_conf, analyzer, species)
	body = to_ebird_csv(rows, cfg, min_confidence=min_conf)
	return Response(
		body, media_type="text/csv",
		headers={"Content-Disposition": f'attachment; filename="nfc-{session_date}-ebird.csv"'},
	)
