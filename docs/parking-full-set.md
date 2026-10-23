# 주차장 전체 원시 집합의 완결성

`await KrairportClient.parking_raw_set(provider="kac"|"iiac", page_size=100, max_pages=10)`는
기관 전체 주차장 현재 현황을 읽는다. KAC는 AirportParking/airportparkingRT XML,
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
