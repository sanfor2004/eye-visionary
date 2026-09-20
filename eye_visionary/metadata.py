from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from fractions import Fraction
from typing import Any

from PIL import ExifTags, Image


GPS_INFO_TAG = 34853


@dataclass(frozen=True)
class ExtractedMetadata:
    width: int
    height: int
    mime_type: str
    capture_time: datetime | None
    camera_make: str | None
    camera_model: str | None
    orientation: str | None
    software: str | None
    camera_settings: dict[str, Any]
    raw_metadata: dict[str, Any]
    latitude: float | None
    longitude: float | None
    altitude: float | None
    gps_timestamp: datetime | None


def _json_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return str(value)


def _number(value: Any) -> float:
    if isinstance(value, Fraction):
        return float(value)
    if isinstance(value, tuple) and len(value) == 2:
        return float(value[0]) / float(value[1])
    return float(value)


def _gps_coordinate(value: Any, reference: str | None) -> float | None:
    if not value or not reference:
        return None
    degrees, minutes, seconds = (_number(part) for part in value)
    coordinate = degrees + minutes / 60 + seconds / 3600
    if reference.upper() in {"S", "W"}:
        coordinate *= -1
    return coordinate


def extract_metadata(image: Image.Image, mime_type: str) -> ExtractedMetadata:
    exif = image.getexif()
    named: dict[str, Any] = {}
    for key, value in exif.items():
        name = ExifTags.TAGS.get(key, str(key))
        named[name] = _json_value(value)

    gps = exif.get(GPS_INFO_TAG, {})
    gps_named = {ExifTags.GPSTAGS.get(key, str(key)): value for key, value in gps.items()} if gps else {}
    capture_time = None
    raw_capture = named.get("DateTimeOriginal") or named.get("DateTime")
    if raw_capture:
        try:
            capture_time = datetime.strptime(str(raw_capture), "%Y:%m:%d %H:%M:%S")
        except ValueError:
            pass

    gps_time = None
    date_stamp = gps_named.get("GPSDateStamp")
    time_stamp = gps_named.get("GPSTimeStamp")
    if date_stamp and time_stamp:
        try:
            hour, minute, second = (_number(value) for value in time_stamp)
            gps_time = datetime.strptime(str(date_stamp), "%Y:%m:%d").replace(hour=int(hour), minute=int(minute), second=int(second))
        except (TypeError, ValueError):
            pass

    return ExtractedMetadata(
        width=image.width,
        height=image.height,
        mime_type=mime_type,
        capture_time=capture_time,
        camera_make=str(named["Make"]) if named.get("Make") else None,
        camera_model=str(named["Model"]) if named.get("Model") else None,
        orientation=str(named["Orientation"]) if named.get("Orientation") else None,
        software=str(named["Software"]) if named.get("Software") else None,
        camera_settings={key: named[key] for key in ("FNumber", "ExposureTime", "ISOSpeedRatings", "FocalLength") if key in named},
        raw_metadata=named,
        latitude=_gps_coordinate(gps_named.get("GPSLatitude"), gps_named.get("GPSLatitudeRef")),
        longitude=_gps_coordinate(gps_named.get("GPSLongitude"), gps_named.get("GPSLongitudeRef")),
        altitude=_number(gps_named["GPSAltitude"]) if gps_named.get("GPSAltitude") else None,
        gps_timestamp=gps_time,
    )
