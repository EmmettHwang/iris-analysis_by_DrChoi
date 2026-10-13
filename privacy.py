"""개인정보 동의·처리방침 — 한 곳에서 정의한다 (2026-10-13).

홍채 이미지는 **생체정보**, 진단·소견은 **건강정보**다. 둘 다 개인정보 보호법 제23조의
민감정보 성격이라 일반 수집·이용 동의와 **별도로** 동의를 받아야 한다.

- 화면(업로드 모달·처리방침 페이지)과 서버 검증이 모두 이 파일의 값을 쓴다.
  페이지마다 문구를 복붙하지 않는다.
- 동의 기록은 SQLite `privacy_consents` 에 **추가만** 한다(기존 테이블은 건드리지 않음).
  시각은 DB 한 시계로 — 컨테이너 TZ=Asia/Seoul 이므로 `datetime('now','localtime')` = KST.
- 보호책임자 이름·연락처는 **지어내지 않는다.** 환경변수로 받고, 비어 있으면 «지정 전» 으로 표시.
"""
import os
import sqlite3

TERMS_VERSION = "2026-10-13"   # 처리방침 시행일 = 동의서 버전. 문구를 바꾸면 이것도 바꾼다.

SERVICE_NAME = "홍채 AI 분석 연구 시스템"


def officer():
    """개인정보 보호책임자 — 설정이 없으면 None 을 돌려 화면이 «지정 전» 으로 보여 준다."""
    name = os.environ.get("IRIS_PRIVACY_OFFICER_NAME", "").strip()
    if not name:
        return None
    return {
        "name": name,
        "title": os.environ.get("IRIS_PRIVACY_OFFICER_TITLE", "").strip(),
        "email": os.environ.get("IRIS_PRIVACY_OFFICER_EMAIL", "").strip(),
        "phone": os.environ.get("IRIS_PRIVACY_OFFICER_PHONE", "").strip(),
        "org": os.environ.get("IRIS_PRIVACY_ORG", "").strip(),
    }


# 업로드 화면의 두 동의. 화면은 /api/privacy/consent-terms 로 받아서 그린다.
CONSENT_TERMS = {
    "version": TERMS_VERSION,
    "items": [
        {
            "key": "privacy",
            "required": True,
            "label": "[필수] 개인정보 수집·이용 동의",
            "checkbox": "피검자에게 아래 개인정보 수집·이용 내용을 알리고 동의를 받았습니다(본인 업로드 포함).",
            "rows": [
                ["수집 항목", "피검자 ID, 눈 구분(좌/우), 메모 · (피검자 정보에 입력하는 경우) 이름, 출생연도, 성별"],
                ["수집·이용 목적", "홍채 이미지 기반 라벨링·AI 학습·분석 연구, 피검자별 이미지 묶음 관리"],
                ["보유·이용 기간", "연구 목적을 달성하거나 피검자가 삭제(동의 철회)를 요청하면 지체 없이 파기"],
                ["거부할 권리와 불이익", "동의를 거부할 수 있습니다. 거부하면 이미지를 업로드·분석할 수 없습니다."],
            ],
        },
        {
            "key": "sensitive",
            "required": True,
            "label": "[필수] 민감정보(생체·건강정보) 처리 동의",
            "checkbox": "피검자에게 아래 민감정보 처리 내용을 일반 개인정보와 별도로 알리고 동의를 받았습니다.",
            "rows": [
                ["처리 항목", "홍채 사진(생체정보) · 진단/소견 메모(건강정보)"],
                ["처리 목적", "홍채 부위 라벨링, AI 모델 학습·예측, 연구용 비교 분석"],
                ["보유·이용 기간", "연구 목적을 달성하거나 피검자가 삭제(동의 철회)를 요청하면 지체 없이 파기"],
                ["거부할 권리와 불이익", "동의를 거부할 수 있습니다. 거부하면 홍채 이미지를 업로드·분석할 수 없습니다."],
                ["제3자 제공", "하지 않습니다. 사진은 이 서버 안에서만 분석하며 외부 AI 서비스로 보내지 않습니다."],
            ],
        },
    ],
}

_DDL = """
CREATE TABLE IF NOT EXISTS privacy_consents (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_type      TEXT    NOT NULL,          -- iris_upload / subject_info
    subject_id        TEXT,                      -- 피검자 ID (비어 있을 수 있음)
    image_ids         TEXT,                      -- 이번에 올린 이미지 id 들 (쉼표)
    consent_privacy   INTEGER NOT NULL,
    consent_sensitive INTEGER NOT NULL,
    terms_version     TEXT    NOT NULL,
    ip                TEXT,
    user_agent        TEXT,
    agreed_at         TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
)
"""


def _connect(db_path):
    return sqlite3.connect(db_path, timeout=10)


def ensure_table(db_path):
    with _connect(db_path) as c:
        c.execute(_DDL)
        c.execute("CREATE INDEX IF NOT EXISTS ix_privacy_consents_subject ON privacy_consents(subject_id)")


def check(form_get):
    """필수 동의가 다 있으면 None, 없으면 한국어 이유를 돌려준다."""
    def truthy(k):
        return str(form_get(k) or "").lower() in ("1", "true", "on", "yes")
    if not truthy("consent_privacy"):
        return "개인정보 수집·이용(필수)에 동의해야 홍채 이미지를 올릴 수 있습니다."
    if not truthy("consent_sensitive"):
        return "민감정보(홍채 생체정보) 처리(필수)에 별도로 동의해야 홍채 이미지를 올릴 수 있습니다."
    return None


def record(db_path, subject_type, subject_id, image_ids, ip, user_agent, terms_version=None):
    with _connect(db_path) as c:
        cur = c.execute(
            "INSERT INTO privacy_consents (subject_type, subject_id, image_ids, consent_privacy,"
            " consent_sensitive, terms_version, ip, user_agent) VALUES (?,?,?,?,?,?,?,?)",
            (subject_type, subject_id or None, ",".join(str(i) for i in image_ids) or None,
             1, 1, terms_version or TERMS_VERSION, (ip or "")[:64], (user_agent or "")[:255]),
        )
        return cur.lastrowid


def has_consent(db_path, subject_id):
    if not subject_id:
        return False
    with _connect(db_path) as c:
        return c.execute("SELECT 1 FROM privacy_consents WHERE subject_id=? LIMIT 1",
                         (subject_id,)).fetchone() is not None


def list_records(db_path, subject_id=None, limit=200):
    with _connect(db_path) as c:
        c.row_factory = sqlite3.Row
        if subject_id:
            rows = c.execute("SELECT * FROM privacy_consents WHERE subject_id=? ORDER BY id DESC LIMIT ?",
                             (subject_id, limit)).fetchall()
        else:
            rows = c.execute("SELECT * FROM privacy_consents ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
