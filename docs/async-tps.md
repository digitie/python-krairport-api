# 비동기 전용 사용과 TPS

KrairportClient, KacClient, IiacClient는 비동기 전용이다. 조회·debug는 await,
iter_pages는 async for, 종료는 async with 또는 await client.aclose()를 사용한다.
Async 접두사 별칭, aio(), 동기 context manager/close는 제거했다. 공항 메타데이터와
좌표 계산은 I/O가 없는 일반 함수다. API 라우팅과 모델·페이지 인자 계약은 유지한다.

```python
from krairport import AsyncTokenBucket, KrairportClient

async def collect():
    bucket = AsyncTokenBucket(max_rps=2, capacity=1)
    async with KrairportClient.from_env(rate_limiter=bucket) as client:
        fees = await client.parking_fees(airport_code="GMP")
        parking = await client.parking_status(airport_code="ICN")
        return fees, parking
```

기본 max_rps는 5다. KAC와 IIAC를 합산해 같은 버킷을 사용한다. standalone provider도
max_rps/rate_limiter를 받으며, 통합 클라이언트에 provider를 주입하면 통합 클라이언트의
버킷으로 설정된다. 같은 provider를 여러 통합 클라이언트에 주입하려면 처음부터 같은
버킷을 사용한다. 여러 독립 클라이언트에도 같은 버킷 객체를 주입해 예산을 공유할 수 있다.

max_rps는 유한한 양수만 받으며 0·음수·NaN·무한대·bool은 거부한다. 주입한 버킷이
max_rps보다 우선한다. 용량 기본값은 max(1, max_rps)이며 처음에는 가득 차 있다.
capacity=1로 초기 burst를 줄일 수 있고, 0.5 TPS도 지원한다. 고정된 1초 구간별
최대 건수 제한이 아니다. 하나의 이벤트 루프 안에서만 버킷을 사용한다.

실제 요청·재시도·redirect 추가 송신은 각각 토큰을 소비한다. 토큰 대기 취소는
토큰을 소비하지 않고 후속 대기자가 진행한다. 사용자 정의 인증 흐름/transport 내부의
추가 송신은 과금 범위에 포함하지 않는다.

자체 HTTP 세션은 종료 시 닫고, 외부에서 주입한 HTTP 세션은 호출자가 닫는다.
CLI/Streamlit은 경계에서 asyncio.run을 한 번 호출하고 같은 루프에서 사용·종료한다.
