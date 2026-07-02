"""
'프레임별 bbox 개수'와 '파일명 개체수(GT)'가 일치하는 영상의 비율을 계산한다.

전제: 동영상 파일명이  <숫자>_<개체수>.확장자  형식이고, 언더바(_) 뒤 숫자가
사람이 직접 센 총 등장 개체수(GT)이다. (예: 01180120_11.MP4 -> GT=11)

판정: 어떤 영상의 '샘플링된 프레임' 중, (신뢰도 임계값 이상인) 동물 bbox 개수가
GT와 정확히 같은 프레임이 하나라도 있으면 그 영상은 '완전탐지(full_detect)'로 본다.
= 그 순간 모든 개체가 동시에 잡힌 프레임이 존재한다는 의미.

사용:
    python scripts\analyze_counts.py --json "C:\JOB\output\bird_md.json"
    python scripts\analyze_counts.py --json "C:\JOB\output\bird_md.json" --conf 0.5
    python scripts\analyze_counts.py --json "C:\JOB\output\bird_md.json" --conf 0.5 --category all --verbose
"""

import argparse
import json
import os
from collections import defaultdict


def parse_gt(filename):
    """파일명 마지막 '_' 뒤의 정수를 GT로 파싱. 실패 시 None."""
    stem = os.path.splitext(filename)[0]
    if '_' not in stem:
        return None
    tail = stem.rsplit('_', 1)[1]
    return int(tail) if tail.isdigit() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', required=True)
    ap.add_argument('--conf', type=float, default=0.2,
                    help='이 신뢰도 이상인 bbox만 개수에 포함 (기본 0.2)')
    ap.add_argument('--category', default='1',
                    help="셀 카테고리. '1'=동물(기본), '2'=사람, '3'=차량, 'all'=전부")
    ap.add_argument('--verbose', action='store_true',
                    help='영상별 상세(GT / 프레임최대개수 / 일치여부) 출력')
    args = ap.parse_args()

    d = json.load(open(args.json, encoding='utf-8'))

    total = 0
    no_gt = []            # GT 파싱 실패
    with_det = 0          # bbox 1개 이상 탐지된 영상
    full_detect = 0       # GT와 일치하는 프레임이 있는 영상
    rows = []

    for im in d.get('images', []):
        fname = os.path.basename(im['file'])
        gt = parse_gt(fname)
        total += 1
        if gt is None:
            no_gt.append(fname)
            continue

        # 프레임별 bbox 개수 집계 (신뢰도/카테고리 필터)
        per_frame = defaultdict(int)
        for det in im.get('detections', []):
            if det['conf'] < args.conf:
                continue
            if args.category != 'all' and det.get('category') != args.category:
                continue
            per_frame[det['frame_number']] += 1

        counts = list(per_frame.values())
        max_count = max(counts, default=0)
        has_any = max_count > 0
        matched = any(c == gt for c in counts)

        if has_any:
            with_det += 1
        if matched:
            full_detect += 1

        rows.append((fname, gt, max_count, matched, has_any))

    # ----- 결과 출력 -----
    n_gt = total - len(no_gt)
    print(f'\n=== 분석 대상: {args.json} ===')
    print(f'조건: 동물bbox conf>={args.conf}, category={args.category}\n')
    print(f'전체 영상            : {total}')
    print(f'GT 파싱 성공         : {n_gt}')
    if no_gt:
        print(f'GT 파싱 실패(제외)   : {len(no_gt)}  {no_gt[:5]}{" ..." if len(no_gt) > 5 else ""}')
    print(f'bbox 탐지된 영상     : {with_det}')
    print(f'완전탐지(GT일치 프레임 존재): {full_detect}')

    print('\n--- 비율 ---')
    if n_gt:
        print(f'완전탐지 / 전체(GT있는것)  : {full_detect}/{n_gt} = {full_detect / n_gt:.1%}')
    if with_det:
        print(f'완전탐지 / bbox탐지된영상  : {full_detect}/{with_det} = {full_detect / with_det:.1%}')

    if args.verbose:
        print('\n--- 영상별 상세 (GT=정답, max=프레임최대bbox, 일치=완전탐지) ---')
        rows.sort(key=lambda r: (r[3], -abs(r[2] - r[1])))  # 불일치/차이큰 것 위로
        print(f'{"영상":30} {"GT":>3} {"max":>4} {"일치":>4}')
        for fname, gt, mx, matched, _ in rows:
            print(f'{fname:30} {gt:>3} {mx:>4} {"O" if matched else "X":>4}')


if __name__ == '__main__':
    main()
