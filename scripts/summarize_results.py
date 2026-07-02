"""
탐지 결과(json)를 사람이 읽기 쉽게 요약 출력한다.
영상별로 탐지 개수와 최고 신뢰도를 보여주고, 신뢰도 기준으로 정렬한다.

사용:
    python scripts\summarize_results.py --json "C:\JOB\output\bird_md.json"
    python scripts\summarize_results.py --json "C:\JOB\output\bird_md.json" --min_conf 0.5
"""

import argparse
import json

CAT = {'1': '동물', '2': '사람', '3': '차량'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', required=True)
    ap.add_argument('--min_conf', type=float, default=0.2,
                    help='이 신뢰도 이상만 집계 (기본 0.2)')
    args = ap.parse_args()

    d = json.load(open(args.json, encoding='utf-8'))
    rows = []
    for im in d.get('images', []):
        dets = [x for x in im.get('detections', []) if x['conf'] >= args.min_conf]
        best = max((x['conf'] for x in dets), default=0.0)
        cats = sorted({CAT.get(x['category'], x['category']) for x in dets})
        rows.append((im['file'], len(dets), best, cats))

    rows.sort(key=lambda r: -r[2])  # 최고 신뢰도 순
    with_det = sum(1 for r in rows if r[1] > 0)

    print(f'\n총 영상 {len(rows)}개 | 탐지 있음 {with_det}개 | '
          f'탐지 없음 {len(rows) - with_det}개  (기준 conf>={args.min_conf})\n')
    print(f'{"영상":30} {"탐지수":>5} {"최고신뢰도":>8}  종류')
    print('-' * 60)
    for f, n, best, cats in rows:
        print(f'{f:30} {n:>5} {best:>8.2f}  {",".join(cats)}')


if __name__ == '__main__':
    main()
