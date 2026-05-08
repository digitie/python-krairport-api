"""pykrairport 예외 계층."""

from __future__ import annotations


class KrairportError(Exception):
    """모든 pykrairport 오류의 기본 예외."""


class KrairportAuthError(KrairportError):
    """인증 실패 또는 서비스키 누락/오류."""


class KrairportRequestError(KrairportError):
    """선택한 공급자에 맞지 않는 요청 파라미터 오류."""


class KrairportRateLimitError(KrairportError):
    """공급자가 quota/rate limit 때문에 요청을 거부한 오류."""


class KrairportNetworkError(KrairportError):
    """공급자 호출 중 발생한 네트워크 오류."""


class KrairportServerError(KrairportError):
    """공급자가 서버 측 또는 예상하지 못한 오류를 반환한 경우."""


class KrairportParseError(KrairportError):
    """공급자 응답을 기대 구조로 파싱하지 못한 경우."""


class UnsupportedAirportError(KrairportRequestError):
    """요청한 공항/공급자 조합을 지원하지 않는 경우."""
