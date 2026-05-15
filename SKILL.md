---
name: krairport-python-builder
description: Use this skill when building, extending, debugging, or documenting a Python client for Korean airport public APIs that combine 한국공항공사(KAC) and 인천국제공항공사(IIAC). Trigger on krairport, 한국공항공사, 인천국제공항공사, ICN/GMP/CJU airport API integration, flight status, aircraft registration, parking fee, parking status, arrival congestion, passenger forecast, KAC XML parsing, IIAC JSON/XML parsing, provider routing, or files like krairport-api.md and src/krairport/client.py.
---

# Krairport Python Library Builder

You are helping build and maintain `krairport`, a Python client that unifies Korean airport public APIs across **KAC** and **IIAC**. Read `README.md` and `krairport-api.md` before changing public behavior.

## Project invariants

1. **Provider split is real**:
   - `ICN` belongs to IIAC.
   - KAC covers nationwide airports except Incheon.
2. **One public surface, two provider adapters**:
   - keep `KrairportClient` as the user-facing entrypoint
   - implement KAC/IIAC-specific HTTP and parsing separately
3. **KAC is still XML-heavy**:
   - do not assume JSON availability across all KAC endpoints
4. **IIAC usually supports `type=json`**:
   - prefer JSON where documented, but keep XML fallback if needed
5. **Service keys are separate**:
- `KAC_SERVICE_KEY`
- `IIAC_SERVICE_KEY`
6. **All schedule timestamps are KST**:
   - naive times are interpreted as `Asia/Seoul`
   - keep `tzdata` in Windows dependencies and preserve the UTC+9 fallback in `_time.py`
7. **No silent provider mismatch**:
   - requests for `ICN` on KAC endpoints must raise `UnsupportedAirportError`
8. **Default tests are offline**:
   - fixture/mock based, no live traffic during ordinary test runs
9. **Public enums remain string-compatible**:
   - use `StrEnum` so existing string comparisons and JSON serialization keep working
10. **Coordinates are WGS84 decimal degrees**:
   - use `kraddr.base.PlaceCoordinate` directly in parameters and response models
   - do not add a `krairport` coordinate wrapper/helper
   - `as_tuple()` and `as_geojson_position()` are `(longitude, latitude)`; use `as_lat_lon()` for UI order
11. **Addresses use kraddr.base directly**:
   - use `kraddr.base.Address` directly in response models
   - do not add a `krairport` address wrapper/helper
   - keep airport-internal location text separate from address DTOs
12. **Public response models use Pydantic v2**:
   - inherit from `KrairportModel`
   - keep `ConfigDict(frozen=True, extra="forbid")`
   - serialize with `model_dump(mode="json")` / `model_dump_json()` or `to_dict()` / `to_json()`
13. **문서 경로는 프로젝트 기준 상대 경로**:
   - use `src/krairport/client.py`, not local absolute paths
14. **Python 내부 문서는 한글**:
   - write module/class/function docstrings and explanatory comments in Korean
   - preserve provider text, code identifiers, commands, and URLs as-is
15. **Windows 탐색은 PowerShell fallback 우선**:
   - if `rg` is blocked by execution permissions, use `Get-ChildItem` and `Select-String`
   - read/search Korean Markdown and Python docs with `-Encoding UTF8`
16. **불필요한 wrapper보다 직접 적용 우선**:
   - do not add a wrapper or compatibility layer unless it has a clear boundary responsibility
   - when `pykma`, `pyopinet`, `pykex`, or another maintained library already has a proven implementation pattern, port that pattern directly into `krairport`
   - minimal edits are preferred for ordinary fixes, but a larger direct adoption is acceptable when it improves long-term consistency and removes needless indirection

## Initial supported endpoints

Start with these.

| Public method | Provider | Endpoint |
|---|---|---|
| `KrairportClient.departures()` | KAC | `getDepFlightStatusList` |
| `KrairportClient.arrivals()` | KAC | `getArrFlightStatusList` |
| `KrairportClient.departures()` | IIAC | `getPassengerDeparturesDeOdp` or `getPassengerDeparturesOdp` |
| `KrairportClient.arrivals()` | IIAC | `getPassengerArrivalsDeOdp` or `getPassengerArrivalsOdp` |
| `KrairportClient.aircraft_assignments()` | KAC | `getFlightStatusAPLList` |
| `KrairportClient.parking_fees()` | KAC | `parkingfee` |
| `KrairportClient.parking_status()` | IIAC | `getTrackingParking` |
| `KrairportClient.arrival_congestion()` | IIAC | `getArrivalsCongestion` |
| `KrairportClient.passenger_forecast()` | IIAC | `getfPassengerNoticeIKR` |
| `KrairportClient.airport_codes()` | KAC | `getAirportCodeList` |
| `KrairportClient.flight_schedules()` | KAC/IIAC | KAC `FlightScheduleList`, IIAC `PaxFltSched` |
| `KrairportClient.airport_facilities()` | KAC/IIAC | KAC `AirportFacilities`, IIAC `StatusOfFacility` |
| `KrairportClient.bus_routes()` | KAC/IIAC | KAC `AirportBusInfo`, IIAC `BusInformation` |
| `KrairportClient.taxi_status()` | KAC/IIAC | KAC `taxiWaitInfo`, IIAC `StatusOfTaxi` |
| `KrairportClient.world_weather()` | IIAC | `StatusOfPassengerWorldWeatherInfo` |
| `KrairportClient.service_destinations()` | IIAC | `StatusOfSrvDestinations` |
| `KrairportClient.kac_raw_items()` | KAC | unmodeled KAC REST operations |
| `KrairportClient.iiac_raw_items()` | IIAC | unmodeled B551177 REST operations |
| `KrairportClient.airport_metadata()` | local | bundled airport metadata |
| `KrairportClient.airports()` | local | provider/active-filtered airport metadata |
| `KrairportClient.nearest_airport()` | local | nearest WGS84 airport lookup |

Do not widen scope until the routing, parsing, and model layer are stable.

For coverage decisions, read `docs/api-coverage.md`. Prefer typed models for high-use APIs and `raw_items` for broad official API access until a fixture-backed parser exists.

## Required deliverables when implementing from scratch

```text
src/krairport/
├── __init__.py
├── client.py              # KrairportClient
├── providers/
│   ├── __init__.py
│   ├── kac.py             # KacClient or adapter
│   └── iiac.py            # IiacClient or adapter
├── airports.py            # bundled airport metadata and nearest lookup
├── models.py              # Pydantic response models
├── enums.py
├── types.py               # public type aliases
├── exceptions.py
├── _http.py
├── _xml.py
├── _time.py
├── _routing.py
└── cli.py
tests/
├── fixtures/
├── test_client.py
├── test_kac.py
├── test_iiac.py
├── test_parsing.py
└── test_routing.py
README.md
krairport-api.md
SKILL.md
docs/testing.md
docs/coordinates-and-types.md
docs/repeated-mistakes.md
docs/troubleshooting.md
```

## Public API rules

### `KrairportClient`

```python
KrairportClient(
    kac_service_key=None,
    iiac_service_key=None,
    *,
    timeout=10.0,
    retries=3,
    session=None,
)

KrairportClient.from_env(
    kac_name="KAC_SERVICE_KEY",
    iiac_name="IIAC_SERVICE_KEY",
)
```

Every public search method must accept an explicit `airport_code` unless it is an IIAC-only congestion API.

### Routing

- `ICN` -> IIAC
- anything else supported by KAC -> KAC
- IIAC-only methods ignore/validate `airport_code`
- unsupported combinations raise `UnsupportedAirportError`

### Flights

Support these fields across providers:

- `provider`
- `airport_code`
- `flight_id`
- `flight_unique_id`
- `direction`
- `airline_name`
- `airline_code`
- `departure_airport_code`
- `arrival_airport_code`
- `scheduled_at`
- `estimated_at`
- `status_korean`
- `status_english`
- `terminal`
- `gate`
- `codeshare`
- `raw`

KAC and IIAC use different field names. Normalize them at the model boundary.

### Enums, types, coordinates

- Keep public response models as Pydantic v2 `BaseModel` subclasses through `KrairportModel`.
- Keep models immutable and reject unknown fields.
- Do not use dataclass `asdict()` for public responses; use `model_dump(mode="json")`.
- Keep `Provider`, `Direction`, `Airport`, `AirportType`, `ApiLanguage`, `ScheduleType` as `StrEnum`.
- Keep public type aliases in `krairport.types`; wrappers should be able to import `AirportCodeLike`, `DirectionLike`, and `ProviderLike`.
- Use `kraddr.base.PlaceCoordinate` directly for WGS84 decimal degree coordinates.
- `PlaceCoordinate.as_tuple()` returns `(longitude, latitude)`.
- `PlaceCoordinate.as_lat_lon()` returns `(latitude, longitude)`.
- Use `kraddr.base.Address` directly for provider address fields.
- Keep interior terminal/floor/area text as `location`; do not guess it as an address.
- Bundled airport metadata is convenience data for app maps/search, not aviation navigation data.

## Type conversion policy

### Keep as `str`

- airport codes: `ICN`, `GMP`, `CJU`
- flight numbers: `KE123`, `7C1101`
- flight unique ids: `f_id`, `schFID`
- `searchday`, `from_time`, `to_time`
- `T1`, `T2`, gate letters

### Convert to `datetime`

- scheduled / estimated / changed timestamps
- interpret as KST
- support:
  - `YYYYMMDDHHMM`
  - `YYYYMMDDHHMMSS`
  - scientific-looking numeric strings from IIAC examples such as `2.02112E+11`

### Convert to `int`

- parking counts
- passenger counts
- parking fees
- total counts

### Convert to `bool`

- codeshare flags like `Y` / `N`

### Convert to `float`

- temperature
- wind speed
- coordinate components
- ratio or decimal quantities

### Normalize empties

- blank strings
- single spaces
- `-`

to `None`.

## Provider-specific request rules

### KAC `StatusOfFlights`

Arrival request params can include:

- `searchday`
- `from_time`
- `to_time`
- `airport_code`
- `f_id`
- `flight_id`
- `line`
- `airport`
- `dep_airport_code`
- `dep_airport`
- `fgenTime`
- `serviceKey`
- `pageNo`
- `numOfRows`

Departure request params can include:

- `searchday`
- `from_time`
- `to_time`
- `airport_code`
- `f_id`
- `flight_id`
- `line`
- `airport`
- `arr_airport_code`
- `arr_airport`
- `fgenTime`
- `serviceKey`
- `pageNo`
- `numOfRows`

### KAC `FlightStatusAPLList`

- `schStTime`
- `schEdTime`
- `schAirCode`
- `schFID`
- `schFln`
- `Line`
- `schAPLno`
- `schAPM`
- `serviceKey`
- `pageNo`
- `numOfRows`

### IIAC detailed passenger flight

- `serviceKey`
- `pageNo`
- `numOfRows`
- `type`
- `searchday`
- `from_time`
- `to_time`
- `airport_code`
- `f_id`
- `flight_id`
- `lang`
- `inqtimechcd`

### IIAC arrival congestion

- `serviceKey`
- `numOfRows`
- `pageNo`
- `terno`
- `airport`
- `type`

### IIAC passenger forecast

- `selectdate`
- `type`
- `serviceKey`
- `numOfRows`
- `pageNo`

## HTTP and parsing rules

1. Keep session/retry setup in one place.
2. Do not log service keys.
3. Retry only transient errors such as `429`, `500`, `502`, `503`, `504`.
4. KAC XML parsing belongs in one parser layer, not scattered through client methods.
5. Normalize `items.item` whether it arrives as one dict or a list.
6. Preserve `raw` payloads only after normalization, not as the public surface.

## Exception hierarchy

```text
KrairportError
├── KrairportAuthError
├── KrairportRequestError
├── KrairportRateLimitError
├── KrairportNetworkError
├── KrairportServerError
├── KrairportParseError
└── UnsupportedAirportError
```

Map provider-specific weirdness into these common exceptions.

## Testing rules

Required offline tests:

- provider routing for `ICN` vs non-`ICN`
- rejection of `ICN` on KAC-only methods
- rejection of non-`ICN` on IIAC-only methods
- KAC XML single-item and multi-item normalization
- IIAC JSON single-item and multi-item normalization
- timestamp parsing, including scientific notation examples
- Windows timezone fallback when `ZoneInfo("Asia/Seoul")` is unavailable
- type assertions for every public model
- flight code-share boolean mapping
- parking fee integer conversion
- passenger forecast integer conversion
- result-code / HTTP error mapping
- CLI JSON serialization
- Pydantic model validation, frozen behavior, and JSON-ready dumps
- raw endpoint path validation
- enum string compatibility
- `kraddr.base.PlaceCoordinate` parsing/range validation
- `kraddr.base.Address` parsing and serialization in facility models
- GeoJSON coordinate order
- bundled airport metadata provider/active filtering
- nearest airport lookup
- coverage gate: `pytest --cov=krairport --cov-fail-under=85`

Optional live tests:

- mark with `live_kac` or `live_iiac`
- require matching env vars
- assert response shape/types only
- do not assert volatile traffic or flight counts

## Common pitfalls

1. Treating `ICN` as just another KAC airport.
2. Assuming every endpoint supports JSON.
3. Mixing up `airport_code`, `airport`, and `schAirCode`.
4. Confusing `flight_id` with `f_id`.
5. Parsing `2400` as a normal wall-clock time without day-boundary logic.
6. Treating passenger forecast as real-time congestion.
7. Treating parking fee and parking status as the same schema.
8. Trusting one provider's field names to exist on the other provider.
9. Returning provider-native names like `terno` or `schAPLno` to users.
10. Assuming Windows always has IANA timezone data installed.
11. Raising test count without covering parser and error branches.
12. Claiming API coverage without updating `docs/api-coverage.md`.
13. Allowing arbitrary raw endpoint path strings.
14. Ignoring data.go.kr change notices before adding or documenting IIAC endpoints.
15. Mixing GeoJSON `(lon, lat)` with human/geodesic `(lat, lon)`.
16. Breaking string compatibility when adding enum types.
17. Keeping dataclass serialization after switching public models to Pydantic.
18. Writing document file locations as local absolute paths.
19. Reintroducing English Python docstrings or explanatory comments.
20. Retrying blocked `rg` instead of using PowerShell file enumeration.
21. Reading UTF-8 Korean docs through PowerShell without `-Encoding UTF8`.
22. Adding a thin wrapper around an already proven implementation instead of adopting the implementation shape directly.
23. Moving to `src/krairport` without updating setuptools package discovery, pytest `pythonpath`, and validation commands.
24. Saving debug UI fixtures without passing request/response/input through sensitive-value redaction.
25. Adding a fixture-generating public function without adding the matching replay parser to `tests/runners.py`.

When one of these is fixed, update `docs/repeated-mistakes.md`.

## Documentation update rules

- Update `README.md` for user-facing API changes.
- Update `krairport-api.md` for endpoint scope, parameter differences, and model rules.
- Update `docs/testing.md` when fixture policy or live markers change.
- Update `docs/coordinates-and-types.md` when enum/type/coordinate policy changes.
- Update `docs/troubleshooting.md` when a user-visible failure gains a known fix.
- Update `CHANGELOG.md` for release-facing changes.
- Write file locations in docs as project-root-relative paths.
- Write Python docstrings and explanatory comments in Korean unless preserving provider text, code identifiers, commands, or URLs.
- In this Windows workspace, use PowerShell fallback commands such as `Get-ChildItem -Recurse -File` and `Select-String -Encoding UTF8` when `rg` is blocked.

## Debug UI fixture rules

- Keep Streamlit and UI-only dependencies outside the `krairport` library package.
- Use `KrairportClient.debug()` or a `debug_*` convenience method to build `DebugRun`.
- Store generated cases in `tests/fixtures/{function}/{case}.json`.
- Default pytest replay must call no external API; replay uses `tests/runners.py`.
- Add or update `docs/debug-fixtures.md` whenever the fixture schema, assertion mode, or runner contract changes.
