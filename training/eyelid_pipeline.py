"""
눈꺼풀 감지 학습 파이프라인
- 라벨DB에서 polygon 눈꺼풀 어노테이션 추출
- 각도별 방사형 밝기 프로파일 특징 추출
- Random Forest 이진 분류기 학습 (angle → occluded/visible)
- 예측 시 360개 각도 마스크 반환
"""
import os
import json
import math
import numpy as np
import cv2
import joblib

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'model', 'eyelid_rf.pkl')
N_ANGLES   = 360
N_RADIAL   = 14   # 각도당 샘플 깊이 수 (홍채 링 내 방사방향)


# ── 기하 유틸 ─────────────────────────────────────────────────────────────────

def _point_in_polygon(px, py, polygon):
    """레이 캐스팅으로 점이 다각형 안에 있는지 확인."""
    n, inside = len(polygon), False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi + 1e-9) + xi):
            inside = not inside
        j = i
    return inside


# ── 특징 추출 ─────────────────────────────────────────────────────────────────

def extract_angle_features(img_bgr, icx, icy, ir, pcx, pcy, pr):
    """
    360개 각도 × N_RADIAL 깊이의 밝기 프로파일을 특징으로 추출.
    반환: (N_ANGLES, N_RADIAL) float32, 0~1 정규화
    """
    h, w = img_bgr.shape[:2]
    features = np.zeros((N_ANGLES, N_RADIAL), dtype=np.float32)

    for ai in range(N_ANGLES):
        theta = (ai / N_ANGLES) * 2 * math.pi
        ct, st = math.cos(theta), math.sin(theta)

        for ri in range(N_RADIAL):
            # 홍채-동공 사이 40%~100% 구간 균등 샘플
            t   = 0.40 + 0.60 * ri / max(N_RADIAL - 1, 1)
            r   = pr + (ir - pr) * t
            px  = int(round(icx + r * ct))
            py  = int(round(icy + r * st))
            if 0 <= px < w and 0 <= py < h:
                b, g, rc = img_bgr[py, px]
                features[ai, ri] = (0.299 * rc + 0.587 * g + 0.114 * b) / 255.0

    return features


def polygon_to_angle_mask(coords_norm, img_w, img_h, icx, icy, ir, pr):
    """
    정규화 좌표 polygon → 360개 각도 이진 마스크 (1=차폐).

    샘플 포인트를 홍채 경계 바로 바깥(ir * 1.05)에서 검사한다.
    눈꺼풀 폴리라인을 닫으면 이미지 가장자리까지 이어지므로,
    홍채 바깥 포인트가 그 polygon 안에 있으면 해당 각도가 차폐된 것이다.
    (홍채 내부 75% 샘플링은 라인이 경계에 걸칠 때 검출 실패함)
    """
    polygon_px = [(nx * img_w, ny * img_h) for nx, ny in coords_norm]
    mask = np.zeros(N_ANGLES, dtype=np.uint8)

    for ai in range(N_ANGLES):
        theta = (ai / N_ANGLES) * 2 * math.pi
        ct, st = math.cos(theta), math.sin(theta)
        # 홍채 경계 바로 바깥에서 샘플링
        r  = ir * 1.05
        sx = icx + r * ct
        sy = icy + r * st
        if _point_in_polygon(sx, sy, polygon_px):
            mask[ai] = 1

    return mask


# ── 데이터셋 빌드 ─────────────────────────────────────────────────────────────

def _is_iris_measure(gp):
    """구버전(type 없음) / 신버전(type='iris_measure') 모두 인식."""
    if not gp:
        return False
    if gp.get('type') == 'iris_measure':
        return True
    # 구버전: type 필드 없이 iris/pupil 키만 있는 형태
    return 'iris' in gp and 'pupil' in gp and 'type' not in gp


def _polyline_to_closed_polygon(coords_norm, is_upper):
    """
    polyline 눈꺼풀 선 → 닫힌 polygon 변환.
    이미지 전체 너비(0~1)를 모서리로 닫아 빈틈 없이 닫힌 영역을 만든다.
    상안검(is_upper=True):  선 + 이미지 상단 전체 모서리
    하안검(is_upper=False): 선 + 이미지 하단 전체 모서리
    """
    if not coords_norm:
        return coords_norm
    # 끝점 x → 수직으로 가장자리 → 가장자리 따라 시작점 x → 닫기
    first_x = coords_norm[0][0]
    last_x  = coords_norm[-1][0]
    if is_upper:
        return coords_norm + [[last_x, 0.0], [first_x, 0.0]]
    else:
        return coords_norm + [[last_x, 1.0], [first_x, 1.0]]


def build_dataset(app):
    """
    DB에서 눈꺼풀 라벨(polygon/polyline)을 모두 읽어 (X, y) 반환.
    X: (N_samples, N_RADIAL)  — 각 행이 한 각도의 특징
    y: (N_samples,)           — 0=가시, 1=차폐
    """
    from database import IrisImage, Label, LabelCategory

    with app.app_context():
        cats = LabelCategory.query.filter(
            LabelCategory.name.ilike('%눈꺼풀%') |
            LabelCategory.name.ilike('%eyelid%')
        ).all()
        if not cats:
            return None, None, "눈꺼풀 카테고리 라벨이 없습니다."
        cat_map = {c.id: c.name for c in cats}

        # polygon 또는 polyline 모두 허용
        eyelid_labels = [
            l for l in Label.query.filter(Label.category_id.in_(cat_map.keys())).all()
            if l.geometry_parsed and l.geometry_parsed.get('type') in ('polygon', 'polyline')
        ]
        if not eyelid_labels:
            return None, None, "눈꺼풀 라벨(polygon/polyline)이 없습니다."

        # image_id별로 그룹화 (한 이미지의 라벨을 합산)
        from collections import defaultdict
        by_image = defaultdict(list)
        for l in eyelid_labels:
            by_image[l.image_id].append(l)

        X_list, y_list = [], []
        skipped = 0
        reasons = []

        for image_id, labels in by_image.items():
            image = IrisImage.query.get(image_id)
            if not image or not os.path.exists(image.file_path):
                skipped += 1; reasons.append(f"img{image_id}:파일없음"); continue

            # iris_measure 탐색 (구버전/신버전 모두)
            all_labels = Label.query.filter_by(image_id=image_id).all()
            iris_geom  = next(
                (l.geometry_parsed for l in all_labels if _is_iris_measure(l.geometry_parsed)),
                None
            )
            if not iris_geom:
                skipped += 1; reasons.append(f"img{image_id}:iris_measure없음"); continue

            img = cv2.imread(image.file_path)
            if img is None:
                skipped += 1; reasons.append(f"img{image_id}:이미지읽기실패"); continue

            h, w = img.shape[:2]
            icx = iris_geom['iris']['center'][0]  * w
            icy = iris_geom['iris']['center'][1]  * h
            ir  = iris_geom['iris']['radius']     * w
            pcx = iris_geom['pupil']['center'][0] * w
            pcy = iris_geom['pupil']['center'][1] * h
            pr  = iris_geom['pupil']['radius']    * w

            feats     = extract_angle_features(img, icx, icy, ir, pcx, pcy, pr)
            combined  = np.zeros(N_ANGLES, dtype=np.uint8)

            for label in labels:
                gp       = label.geometry_parsed
                coords   = gp['coords']
                is_upper = 'upper' in cat_map[label.category_id].lower() or '위' in cat_map[label.category_id]

                # polyline은 닫힌 polygon으로 변환
                if gp['type'] == 'polyline':
                    coords = _polyline_to_closed_polygon(coords, is_upper)

                mask = polygon_to_angle_mask(coords, w, h, icx, icy, ir, pr)
                combined = np.maximum(combined, mask)  # 여러 라벨 OR 합산

            X_list.append(feats)
            y_list.append(combined)

        if not X_list:
            detail = ', '.join(reasons[:5])
            return None, None, f"처리 가능한 이미지가 없습니다 (건너뜀: {skipped}개 — {detail})."

        X = np.vstack(X_list)
        y = np.concatenate(y_list)
        msg = f"{len(X_list)}개 이미지 · {len(X):,}개 각도 샘플 (차폐 {y.mean()*100:.1f}%)"
        return X, y, msg


# ── 학습 ─────────────────────────────────────────────────────────────────────

def train(X, y):
    """Random Forest 이진 분류기 학습 및 모델 저장."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import StratifiedKFold, cross_val_score

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=4,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X, y)

    # 3-폴드 교차검증 F1
    cv   = StratifiedKFold(n_splits=3, shuffle=True, random_state=0)
    f1   = cross_val_score(model, X, y, cv=cv, scoring='f1').mean()
    acc  = cross_val_score(model, X, y, cv=cv, scoring='accuracy').mean()

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    return model, {'f1': round(f1, 3), 'accuracy': round(acc, 3)}


# ── 예측 ─────────────────────────────────────────────────────────────────────

def load_model():
    if not os.path.exists(MODEL_PATH):
        return None
    return joblib.load(MODEL_PATH)


def predict(img_bgr, icx, icy, ir, pcx, pcy, pr, threshold=0.45):
    """
    학습된 모델로 눈꺼풀 차폐 각도 마스크 예측.
    반환: (mask: list[int], probs: list[float])
    """
    model = load_model()
    if model is None:
        raise FileNotFoundError("학습된 모델이 없습니다. 먼저 학습을 실행하세요.")

    feats = extract_angle_features(img_bgr, icx, icy, ir, pcx, pcy, pr)
    probs = model.predict_proba(feats)[:, 1]  # 차폐 확률

    mask = (probs >= threshold).astype(np.uint8)

    # 형태학적 닫힘: 작은 빈틈 메우기
    CLOSE_R = 6
    closed  = mask.copy()
    for ai in range(N_ANGLES):
        if closed[ai]:
            continue
        l = sum(mask[(ai - k) % N_ANGLES] for k in range(1, CLOSE_R + 1))
        r = sum(mask[(ai + k) % N_ANGLES] for k in range(1, CLOSE_R + 1))
        if l >= 3 and r >= 3:
            closed[ai] = 1

    return closed.tolist(), probs.tolist()


def model_exists():
    return os.path.exists(MODEL_PATH)
