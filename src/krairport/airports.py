"""번들 한국 공항 메타데이터와 좌표 도우미."""

from __future__ import annotations

from types import MappingProxyType

from krairport._convert import normalize_airport_code
from krairport.enums import Airport, AirportType, Provider, normalize_provider
from krairport.exceptions import UnsupportedAirportError
from krairport.geo import Coordinate, CoordinateTuple, coerce_coordinate
from krairport.models import AirportMetadata
from krairport.types import ProviderLike

_OURAIRPORTS_SOURCE = "OurAirports airports.csv, last checked 2026-05-06"
_HISTORIC_SOURCE = "Historic airport coordinate reference, last checked 2026-05-06"


def _airport(
    code: Airport,
    provider: Provider,
    name_english: str,
    *,
    name_korean: str,
    icao_code: str | None,
    municipality: str,
    latitude: float | None,
    longitude: float | None,
    elevation_ft: int | None,
    airport_type: AirportType,
    active: bool = True,
    source: str = _OURAIRPORTS_SOURCE,
) -> AirportMetadata:
    coordinate = None
    if latitude is not None and longitude is not None:
        coordinate = Coordinate(lat=latitude, lon=longitude)
    return AirportMetadata(
        code=code.value,
        provider=provider,
        name_english=name_english,
        name_korean=name_korean,
        icao_code=icao_code,
        municipality=municipality,
        coordinate=coordinate,
        elevation_ft=elevation_ft,
        airport_type=airport_type,
        active=active,
        source=source,
    )


AIRPORTS: MappingProxyType[str, AirportMetadata] = MappingProxyType(
    {
        Airport.ICN.value: _airport(
            Airport.ICN,
            Provider.IIAC,
            "Incheon International Airport",
            name_korean="인천국제공항",
            icao_code="RKSI",
            municipality="Seoul/Incheon",
            latitude=37.469101,
            longitude=126.450996,
            elevation_ft=23,
            airport_type=AirportType.LARGE,
        ),
        Airport.GMP.value: _airport(
            Airport.GMP,
            Provider.KAC,
            "Gimpo International Airport",
            name_korean="김포국제공항",
            icao_code="RKSS",
            municipality="Seoul",
            latitude=37.5583,
            longitude=126.791,
            elevation_ft=59,
            airport_type=AirportType.LARGE,
        ),
        Airport.PUS.value: _airport(
            Airport.PUS,
            Provider.KAC,
            "Gimhae International Airport",
            name_korean="김해국제공항",
            icao_code="RKPK",
            municipality="Busan",
            latitude=35.179501,
            longitude=128.938004,
            elevation_ft=6,
            airport_type=AirportType.LARGE,
        ),
        Airport.CJU.value: _airport(
            Airport.CJU,
            Provider.KAC,
            "Jeju International Airport",
            name_korean="제주국제공항",
            icao_code="RKPC",
            municipality="Jeju City",
            latitude=33.512058,
            longitude=126.492548,
            elevation_ft=118,
            airport_type=AirportType.LARGE,
        ),
        Airport.TAE.value: _airport(
            Airport.TAE,
            Provider.KAC,
            "Daegu International Airport",
            name_korean="대구국제공항",
            icao_code="RKTN",
            municipality="Daegu",
            latitude=35.894394,
            longitude=128.656989,
            elevation_ft=116,
            airport_type=AirportType.LARGE,
        ),
        Airport.CJJ.value: _airport(
            Airport.CJJ,
            Provider.KAC,
            "Cheongju International Airport",
            name_korean="청주국제공항",
            icao_code="RKTU",
            municipality="Cheongju",
            latitude=36.71556,
            longitude=127.500289,
            elevation_ft=191,
            airport_type=AirportType.LARGE,
        ),
        Airport.KWJ.value: _airport(
            Airport.KWJ,
            Provider.KAC,
            "Gwangju Airport",
            name_korean="광주공항",
            icao_code="RKJJ",
            municipality="Gwangju",
            latitude=35.123173,
            longitude=126.805444,
            elevation_ft=39,
            airport_type=AirportType.MEDIUM,
        ),
        Airport.RSU.value: _airport(
            Airport.RSU,
            Provider.KAC,
            "Yeosu Airport",
            name_korean="여수공항",
            icao_code="RKJY",
            municipality="Yeosu",
            latitude=34.84230041503906,
            longitude=127.61699676513672,
            elevation_ft=53,
            airport_type=AirportType.MEDIUM,
        ),
        Airport.USN.value: _airport(
            Airport.USN,
            Provider.KAC,
            "Ulsan Airport",
            name_korean="울산공항",
            icao_code="RKPU",
            municipality="Ulsan",
            latitude=35.59349823,
            longitude=129.352005005,
            elevation_ft=45,
            airport_type=AirportType.MEDIUM,
        ),
        Airport.MWX.value: _airport(
            Airport.MWX,
            Provider.KAC,
            "Muan International Airport",
            name_korean="무안국제공항",
            icao_code="RKJB",
            municipality="Muan",
            latitude=34.991406,
            longitude=126.382814,
            elevation_ft=35,
            airport_type=AirportType.LARGE,
        ),
        Airport.YNY.value: _airport(
            Airport.YNY,
            Provider.KAC,
            "Yangyang International Airport",
            name_korean="양양국제공항",
            icao_code="RKNY",
            municipality="Yangyang",
            latitude=38.060481,
            longitude=128.669822,
            elevation_ft=241,
            airport_type=AirportType.LARGE,
        ),
        Airport.KUV.value: _airport(
            Airport.KUV,
            Provider.KAC,
            "Gunsan Airport",
            name_korean="군산공항",
            icao_code="RKJK",
            municipality="Gunsan",
            latitude=35.903801,
            longitude=126.615997,
            elevation_ft=29,
            airport_type=AirportType.MEDIUM,
        ),
        Airport.HIN.value: _airport(
            Airport.HIN,
            Provider.KAC,
            "Sacheon Airport",
            name_korean="사천공항",
            icao_code="RKPS",
            municipality="Sacheon",
            latitude=35.088591,
            longitude=128.071747,
            elevation_ft=25,
            airport_type=AirportType.MEDIUM,
        ),
        Airport.WJU.value: _airport(
            Airport.WJU,
            Provider.KAC,
            "Wonju Airport",
            name_korean="원주공항",
            icao_code="RKNW",
            municipality="Wonju",
            latitude=37.437113,
            longitude=127.960051,
            elevation_ft=329,
            airport_type=AirportType.MEDIUM,
        ),
        Airport.KPO.value: _airport(
            Airport.KPO,
            Provider.KAC,
            "Pohang Gyeongju Airport",
            name_korean="포항경주공항",
            icao_code="RKTH",
            municipality="Pohang",
            latitude=35.987955,
            longitude=129.420383,
            elevation_ft=70,
            airport_type=AirportType.MEDIUM,
        ),
        Airport.MPK.value: _airport(
            Airport.MPK,
            Provider.KAC,
            "Mokpo Airport",
            name_korean="목포공항",
            icao_code="RKJM",
            municipality="Mokpo",
            latitude=34.76,
            longitude=126.38027777,
            elevation_ft=None,
            airport_type=AirportType.CLOSED,
            active=False,
            source=_HISTORIC_SOURCE,
        ),
    }
)

SUPPORTED_AIRPORT_CODES = frozenset(AIRPORTS)
KAC_AIRPORTS = frozenset(
    code for code, airport in AIRPORTS.items() if airport.provider is Provider.KAC
)
IIAC_AIRPORTS = frozenset(
    code for code, airport in AIRPORTS.items() if airport.provider is Provider.IIAC
)


def get_airport(airport_code: str | Airport) -> AirportMetadata:
    """지원 공항코드의 번들 메타데이터를 반환합니다."""

    code = normalize_airport_code(str(airport_code))
    try:
        return AIRPORTS[code]
    except KeyError as exc:
        raise UnsupportedAirportError(f"unsupported Korean airport code: {airport_code!r}") from exc


def get_airport_or_none(airport_code: str | Airport | None) -> AirportMetadata | None:
    """공항코드가 없거나 지원하지 않으면 `None`을 반환합니다."""

    if airport_code is None:
        return None
    try:
        return get_airport(airport_code)
    except (UnsupportedAirportError, ValueError):
        return None


def list_airports(
    *,
    provider: ProviderLike | None = None,
    active: bool | None = None,
) -> tuple[AirportMetadata, ...]:
    """공급자와 활성 상태로 필터링한 번들 공항 목록을 반환합니다."""

    provider_value = normalize_provider(provider) if provider is not None else None
    airports = list(AIRPORTS.values())
    if provider_value is not None:
        airports = [airport for airport in airports if airport.provider is provider_value]
    if active is not None:
        airports = [airport for airport in airports if airport.active is active]
    return tuple(sorted(airports, key=lambda airport: airport.code))


def nearest_airport(
    coordinate: Coordinate | CoordinateTuple,
    *,
    provider: ProviderLike | None = None,
    active: bool | None = True,
) -> AirportMetadata | None:
    """WGS84 좌표 기준 가장 가까운 번들 공항을 반환합니다."""

    origin = coerce_coordinate(coordinate)

    candidates = [
        airport
        for airport in list_airports(provider=provider, active=active)
        if airport.coordinate is not None
    ]
    if not candidates:
        return None

    def distance_to_origin(airport: AirportMetadata) -> float:
        assert airport.coordinate is not None
        return origin.distance_to_km(airport.coordinate)

    return min(candidates, key=distance_to_origin)
