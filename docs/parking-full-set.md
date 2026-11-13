# 주차장 전체 원시 집합의 완결성

`await KrairportClient.parking_raw_set(provider="kac"|"iiac", page_size=100, max_pages=10)`는
기관 전체 주차장 현재 현황을 읽는다. KAC는 공식 15158681의 parking-realtime-status/info XML,
IIAC는 StatusOfParking/getTrackingParking JSON을 사용한다. 공항 필터나 요금 호출을 섞지 않는다.
기존 parking_status/raw_items의 반환·요청 계약은 바꾸지 않는다.

`ParkingRawSet`은 items, provider, total_count, page_count, page_size, wire_page_metadata를 보존한다.
source totalCount는 필수이며 누락·음수·bool·변동·전체수신량 불일치는 KrairportParseError다.
pageNo/numOfRows가 존재하면 요청과 같아야 한다. 누락 시 요청값을 원문 echo로 주장하지 않고
wire_page_metadata=false로 표시한다. 정상 total=0은 완결된 빈 응답의 증거일 뿐이다.
소비자는 삭제 승인 전에 원천 재확인 및 이전 성공집합 보존 정책을 별도로 적용해야 한다.

page_size 1~1000, max_pages 1~20, 누적 raw JSON 8MiB로 제한한다. 상한을 넘는 total은
다음 페이지를 호출하기 전에 거부한다. 동일 raw행/반복페이지와 중간 빈 페이지도 거부한다.
HTTP·재시도·redirect·공통 TPS 및 resultCode 판정은 기존 SDK 경계를 그대로 사용한다.
페이지 사이 total이 같더라도 원천 전체 snapshot의 강한 동일성을 보장하지는 않는다.
Transport는 별도로 주차장 identity·관측시각·범위·급감 여부를 검증해야 한다.

기본 테스트는 fixture로 KAC XML/IIAC JSON 두 실제 public 경로와 페이지 메타를 검증하며,
실제 API 키를 사용하거나 운영 배포하지 않는다.

적대 리뷰 회귀로 malformed nonempty items/예상 밖 키를 빈 성공으로 승인하지 않으며, 메타 숫자는 변환 전에 5자리로 제한한다. 정상 빈 XML items와 JSON empty만 빈 receipt 후보가 된다.

신규 full-set은 header.resultCode의 명시 성공과 items 키 존재를 추가로 요구한다. resultMsg만 있는 응답을 성공으로 해석하지 않는다. 비정상 JSON 값/Unicode/직렬화 오류는 원문 없는 ParseError로 변환한다. 기존 HTTP의 느슨한 응답 호환 정책은 유지한다.

## 수집 승인용 엄격한 현황 값

`parse_parking_snapshot_values(raw, provider="kac"|"iiac")`는 `ParkingSnapshotValues`로
총면수·점유면수·timezone-aware KST 관측시각을 반환한다. 숫자의 오류문자열/음수/bool/
소수/상한초과와 없거나 유효하지 않은 원천시각을 원문 없는 KrairportParseError로 거부한다.
기존 status API의 느슨한 숫자·시각 변환은 바꾸지 않는다. HTTP를 호출하지 않는 public
원천검증 함수이므로 수집 승인 전에 raw와 canonical 값의 대응을 확인할 수 있다.

### IIAC의 0 밀리초 관측시각

실제 `datetm="20261113181600.000"`처럼 14자리 시각 뒤 정확히 `.000`인 입력은
`2026-11-13T18:16:00+09:00`으로 해석한다. 저장된 공개 원문 19행의 초는
18:16:00~18:16:05로 서로 다르며, 이를 동일 시각이나 현재시각으로 바꾸지 않는다.
공통 `_time`은 소수부를 버릴 수 있으므로 비영 소수부·다른 소수부 길이·과학적 표기는
이 엄격한 경계에서 새로 허용하지 않는다. 원문 숫자·행·날짜와 기존 KAC/페이지 검증은 보존한다.
이는 오프라인 파서 정정이며 실제 수집 성공·현재 집합 게시·운영 최신성을 뜻하지 않는다.

## KAC 공식 15158681 GW

주차 현황/완결 raw 집합만 `https://apis.data.go.kr/B551178/parking-realtime-status/info`로
전환한다. 기존 KAC HTTP host의 접속 실패와 새 서비스 등록 전의 인증 거부는 별개의 실패다.
새 [활용신청 안내](https://www.data.go.kr/data/15158681/openapi.do)를 사용하며 다른 운항·요금
서비스의 base나 raw path 검증을 일괄 변경하지 않는다.

공식 포털의 embedded Swagger ASCII 계약 SHA256은
`51ad76fe25d97b7314c66f0aa4f29c5f8b0a9f2b878c0745a821be94e45484bb`이다.
`tests/fixtures/kac_parking_realtime_contract.json`에는 operation·허용/필수 query와 응답 구조만
투영했다. 손상된 한글 description이나 인증 예시는 복사하지 않는다. GET/XML과
`serviceKey`/`pageNo`/`numOfRows`/`schAirportCode`/`type`을 검산한다.

`tests/fixtures/kac_parking_realtime_observed.json`은 서비스 등록 후 별도 읽기 진단에서 얻은
성공 메타와 공개 검증 7필드 25행의 투영이다. 원 HTTP XML 바이트 전체라고 주장하지 않는다.
메타의 문자열 타입·행 값·원문·점유 0·KST 시각을 보존해 XML 경로에서 오프라인 재생한다.
합성 2페이지 fixture는 별도로 원천 total·pageNo·numOfRows와 공항 필터 없는 완결 조회를 검증한다.
SDK 시험 자체는 외부 API·실키·DB를 사용하지 않으며 운영 수집 복구는 소비자의 정규 job으로 확인한다.
