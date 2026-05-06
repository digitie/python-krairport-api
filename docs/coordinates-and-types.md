# 타입과 좌표 표준화

확인 기준일: 2026-05-06

`pykrairport`는 외부 프로그램에서 안정적으로 사용할 수 있도록 문자열 API를 유지하면서 `StrEnum`, 타입 alias, WGS84 좌표 모델을 함께 제공합니다.

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
| `CoordinateTuple` | `(latitude, longitude)` |
| `GeoJsonPosition` | `(longitude, latitude)` |

## Coordinate

`Coordinate`는 WGS84 decimal degrees를 표준으로 사용합니다.

```python
from pykrairport import Coordinate

coord = Coordinate.from_values("37° 33' 29.88\" N", "126° 47' 27.6\" E")
coord.as_tuple()             # (latitude, longitude)
coord.as_geojson_position()  # (longitude, latitude)
```

규칙:

- 내부 표준은 항상 WGS84 decimal degrees입니다.
- 사람이 읽는 순서는 `(latitude, longitude)`입니다.
- GeoJSON은 표준대로 `(longitude, latitude)`를 반환합니다.
- 위도는 `-90..90`, 경도는 `-180..180` 범위를 벗어나면 `ValueError`를 발생시킵니다.
- DMS 문자열과 `N/E/S/W` hemisphere 표기를 decimal degrees로 변환합니다.

## Airport Metadata

번들 공항 레지스트리는 외부 앱의 지도, 검색, 근접 공항 계산에 사용할 수 있습니다.

```python
from pykrairport import get_airport, list_airports, nearest_airport

icn = get_airport("ICN")
icn.coordinate.as_geojson_position()

kac_active = list_airports(provider="kac", active=True)
nearest = nearest_airport("37.56 N", "126.79 E")
```

`AirportMetadata` 필드:

| Field | 의미 |
|---|---|
| `code` | IATA 공항코드 |
| `provider` | `Provider.KAC` 또는 `Provider.IIAC` |
| `name_english`, `name_korean` | 공항명 |
| `icao_code` | ICAO 코드 |
| `municipality` | 도시/지역 |
| `coordinate` | `Coordinate | None` |
| `timezone` | 기본 `Asia/Seoul` |
| `airport_type` | `AirportType` |
| `active` | 운영/비운영 메타데이터 |
| `source` | 좌표/메타데이터 출처 |

좌표 출처:

- 활성 공항 좌표와 ICAO/고도/공항 유형은 OurAirports `airports.csv`를 기준으로 넣었습니다. OurAirports는 CSV 데이터 덤프를 제공하며, 2026-05-06 확인 시 `airports.csv`가 2026-05-05에 갱신된 것으로 표시되어 있었습니다.
- `MPK`는 현재 활성 여객공항이 아니므로 `active=False`, `AirportType.CLOSED`로 표시했습니다. 좌표는 historic reference로 분리해 `source`에 남깁니다.

주의:

- 번들 좌표는 사용자 앱의 지도/검색 편의용입니다. 항공 운항, 관제, 항법 목적의 공식 원천으로 사용하지 마세요.
- provider API가 좌표 필드를 직접 반환하는 경우 `Coordinate.from_mapping()` 또는 `coordinate_from_mapping()`으로 같은 표준 모델에 맞춥니다.
