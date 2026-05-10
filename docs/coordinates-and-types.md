# 타입과 좌표 표준화

확인 기준일: 2026-05-06

`pykrairport`는 외부 프로그램에서 안정적으로 사용할 수 있도록 문자열 API를 유지하면서 `StrEnum`, 타입 alias, `pykrtour.PlaceCoordinate`와 `pykrtour.Address` 기반 장소 타입을 함께 제공합니다.

## Pydantic Models

Public 응답 모델은 Pydantic v2 `BaseModel` 기반의 immutable 모델입니다. 문자열 입력은 `Provider`, `Direction`, `AirportType` 같은 `StrEnum`으로 검증되고, 출력은 Pydantic 표준 직렬화 API를 사용할 수 있습니다.

```python
from pykrairport import Flight

flight = Flight(
    provider="kac",
    airport_code="GMP",
    flight_id="KE1",
    flight_unique_id=None,
    direction="departure",
    airline_name=None,
    airline_code=None,
    departure_airport_code=None,
    arrival_airport_code=None,
    scheduled_at=None,
    estimated_at=None,
    status_korean=None,
    status_english=None,
    terminal=None,
    gate=None,
    codeshare=None,
)

flight.provider == "kac"
flight.model_dump(mode="json")
flight.to_dict()
```

규칙:

- 모델은 `ConfigDict(frozen=True, extra="forbid")`로 고정합니다.
- `to_dict()`는 `model_dump(mode="json")`의 얇은 wrapper입니다.
- `to_json()`은 `model_dump_json()`의 얇은 wrapper입니다.
- 기존 문자열 비교 호환성을 위해 enum은 `StrEnum`을 유지합니다.

## Enum

모든 enum은 `StrEnum`입니다. 기존처럼 문자열 비교와 JSON 직렬화가 가능하면서, IDE 자동완성과 타입 힌트를 얻을 수 있습니다.

```python
from pykrairport import Airport, Direction, Provider

Airport.ICN == "ICN"
Direction.ARRIVAL == "arrival"
Provider.KAC == "kac"
```

주요 enum:

| Enum | 값 |
|---|---|
| `Provider` | `KAC`, `IIAC` |
| `Direction` | `ARRIVAL`, `DEPARTURE` |
| `Airport` | `ICN`, `GMP`, `PUS`, `CJU`, `TAE`, `CJJ`, `KWJ`, `RSU`, `USN`, `MWX`, `YNY`, `KUV`, `HIN`, `WJU`, `KPO`, `MPK` |
| `AirportType` | `LARGE`, `MEDIUM`, `SMALL`, `CLOSED`, `UNKNOWN` |
| `ApiLanguage` | `KOREAN`, `ENGLISH`, `JAPANESE`, `CHINESE` |
| `ScheduleType` | `DOMESTIC`, `INTERNATIONAL` |

## Type Alias

`pykrairport.types`는 외부 패키지의 wrapper나 adapter에서 재사용할 수 있는 alias를 제공합니다.

```python
from pykrairport.types import AirportCodeLike, DirectionLike, ProviderLike

def load_airport(code: AirportCodeLike) -> None:
    ...
```

주요 alias:

| Alias | 의미 |
|---|---|
| `AirportCodeLike` | `str | Airport` |
| `DirectionLike` | `str | Direction` |
| `ProviderLike` | `str | Provider` |
| `RawRecord` | provider raw 응답 mapping |
| `CoordinateTuple` | `(longitude, latitude)` |
| `GeoJsonPosition` | `(longitude, latitude)` |

## PlaceCoordinate

좌표 public surface는 `pykrtour.PlaceCoordinate`를 직접 사용합니다. `pykrairport` 안에 별도 좌표 wrapper나 helper를 두지 않습니다.

```python
from pykrairport import PlaceCoordinate

coord = PlaceCoordinate.from_values("37° 33' 29.88\" N", "126° 47' 27.6\" E")
coord.as_tuple()             # (longitude, latitude)
coord.as_geojson_position()  # (longitude, latitude)
coord.as_lat_lon()           # (latitude, longitude)
```

규칙:

- 내부 표준은 항상 WGS84 decimal degrees입니다.
- 저장/geometry/GeoJSON 순서는 `(longitude, latitude)`입니다.
- 사람이 읽는 UI나 일부 provider 요청에 `(latitude, longitude)`가 필요하면 `as_lat_lon()`을 사용합니다.
- 위도는 `-90..90`, 경도는 `-180..180` 범위를 벗어나면 `ValueError`를 발생시킵니다.
- DMS 문자열과 `N/E/S/W` hemisphere 표기를 decimal degrees로 변환합니다.

## Airport Metadata

번들 공항 레지스트리는 외부 앱의 지도, 검색, 근접 공항 계산에 사용할 수 있습니다.

```python
from pykrairport import PlaceCoordinate, get_airport, list_airports, nearest_airport

icn = get_airport("ICN")
icn.coordinate.as_geojson_position()

kac_active = list_airports(provider="kac", active=True)
nearest = nearest_airport(PlaceCoordinate.from_values("37.56 N", "126.79 E"))
```

`AirportMetadata` 필드:

| Field | 의미 |
|---|---|
| `code` | IATA 공항코드 |
| `provider` | `Provider.KAC` 또는 `Provider.IIAC` |
| `name_english`, `name_korean` | 공항명 |
| `icao_code` | ICAO 코드 |
| `municipality` | 도시/지역 |
| `coordinate` | `PlaceCoordinate | None` |
| `timezone` | 기본 `Asia/Seoul` |
| `airport_type` | `AirportType` |
| `active` | 운영/비운영 메타데이터 |
| `source` | 좌표/메타데이터 출처 |

좌표 출처:

- 활성 공항 좌표와 ICAO/고도/공항 유형은 OurAirports `airports.csv`를 기준으로 넣었습니다. OurAirports는 CSV 데이터 덤프를 제공하며, 2026-05-06 확인 시 `airports.csv`가 2026-05-05에 갱신된 것으로 표시되어 있었습니다.
- `MPK`는 현재 활성 여객공항이 아니므로 `active=False`, `AirportType.CLOSED`로 표시했습니다. 좌표는 historic reference로 분리해 `source`에 남깁니다.

주의:

- 번들 좌표는 사용자 앱의 지도/검색 편의용입니다. 항공 운항, 관제, 항법 목적의 공식 원천으로 사용하지 마세요.
- provider API가 좌표 필드를 직접 반환하는 경우 `PlaceCoordinate.from_mapping()`을 모델 생성 경계에서 바로 사용합니다.

## Address

주소 public surface는 `pykrtour.Address`를 직접 사용합니다. `pykrairport` 안에 주소 wrapper나 helper를 두지 않습니다.

```python
from pykrairport import Address

address = Address.from_mapping({"address": "서울특별시 강서구 하늘길 112"})
address.display_address
```

규칙:

- provider row에 주소 계열 필드가 있으면 모델 생성 경계에서 `Address.from_mapping()`을 바로 호출합니다.
- 공항 내부 층/구역/게이트 같은 위치 설명은 주소로 추정하지 않고 기존 `location` 문자열에 둡니다.
- 자유 주소 문자열만으로 법정동코드를 임의 추정하지 않습니다.
