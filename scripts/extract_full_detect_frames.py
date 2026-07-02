"""
'완전탐지' 프레임을 이미지로 추출·저장한다.

완전탐지 프레임 = 그 프레임의 (신뢰도 임계값 이상) 동물 bbox 개수가 파일명 개체수(GT)와
정확히 같은 프레임. (파일명 형식: <숫자>_<개체수>.확장자, 예: 01180120_11.MP4 -> GT=11)

각 영상에서 조건을 만족하는 프레임을 원본 동영상에서 뽑아, bbox를 그려서 저장한다.
저장 파일명: <원본이름>__f<프레임번호>_n<bbox개수>.jpg

사용:
    python scripts\extract_full_detect_frames.py ^
        --json "C:\JOB\output\bird_md.json" ^
        --video_dir "C:\JOB\data\bird" ^
        --out_dir "C:\JOB\output\full_detect_frames\bird" ^
        --conf 0.4
"""

import argparse
import json
import os
from collections import defaultdict

import cv2

VIDEO_EXTS = ('.mp4', '.mov', '.avi', '.mkv', '.asf', '.wmv')
CAT_COLOR = {'1': (0, 255, 0), '2': (255, 128, 0), '3': (0, 128, 255)}  # BGR


def parse_gt(filename):
    stem = os.path.splitext(filename)[0]
    if '_' not in stem:
        return None
    tail = stem.rsplit('_', 1)[1]
    return int(tail) if tail.isdigit() else None


def find_video(video_dir, fname):
    """json의 file(보통 파일명)로 원본 경로를 찾는다."""
    direct = os.path.join(video_dir, fname)
    if os.path.exists(direct):
        return direct
    stem = os.path.splitext(os.path.basename(fname))[0]
    parent = os.path.join(video_dir, os.path.dirname(fname))
    if os.path.isdir(parent):
        for f in os.listdir(parent):
            if os.path.splitext(f)[0] == stem:
                return os.path.join(parent, f)
    return None


def draw_boxes(frame, dets, conf):
    h, w = frame.shape[:2]
    for det in dets:
        if det['conf'] < conf:
            continue
        x, y, bw, bh = det['bbox']
        p1 = (int(x * w), int(y * h))
        p2 = (int((x + bw) * w), int((y + bh) * h))
        color = CAT_COLOR.get(det.get('category'), (0, 255, 0))
        cv2.rectangle(frame, p1, p2, color, 2)
        cv2.putText(frame, f"{det['conf']:.2f}", (p1[0], max(0, p1[1] - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    return frame


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', required=True)
    ap.add_argument('--video_dir', required=True)
    ap.add_argument('--out_dir', required=True)
    ap.add_argument('--conf', type=float, default=0.2)
    ap.add_argument('--category', default='1', help="셀 카테고리 ('1'=동물 기본, 'all'=전부)")
    ap.add_argument('--first_only', action='store_true',
                    help='영상당 첫 번째 완전탐지 프레임만 저장 (기본은 모든 일치 프레임)')
    ap.add_argument('--no_boxes', action='store_true', help='박스 없이 원본 프레임만 저장')
    args = ap.parse_args()

    d = json.load(open(args.json, encoding='utf-8'))
    os.makedirs(args.out_dir, exist_ok=True)

    n_videos_saved = 0
    n_frames_saved = 0
    n_missing = 0

    for im in d.get('images', []):
        fname = os.path.basename(im['file'])
        gt = parse_gt(fname)
        if gt is None:
            continue

        # 프레임별로 (조건 통과) detection 모으기
        per_frame = defaultdict(list)
        for det in im.get('detections', []):
            if det['conf'] < args.conf:
                continue
            if args.category != 'all' and det.get('category') != args.category:
                continue
            per_frame[det['frame_number']].append(det)

        # GT와 개수가 일치하는 프레임들 (프레임번호 순)
        match_frames = sorted(fn for fn, dets in per_frame.items() if len(dets) == gt)
        if not match_frames:
            continue
        if args.first_only:
            match_frames = match_frames[:1]

        video_path = find_video(args.video_dir, im['file'])
        if video_path is None:
            print(f'[경고] 원본 없음, 건너뜀: {fname}')
            n_missing += 1
            continue

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f'[경고] 영상 열기 실패: {fname}')
            n_missing += 1
            continue

        stem = os.path.splitext(fname)[0]
        saved_this = 0
        for fn in match_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, fn)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
            if not args.no_boxes:
                frame = draw_boxes(frame, per_frame[fn], args.conf)
                cv2.putText(frame, f'{stem}  GT={gt}  bbox={len(per_frame[fn])}  frame={fn}',
                            (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
            out_name = f'{stem}__f{fn}_n{len(per_frame[fn])}.jpg'
            # 유니코드/한글 경로 안전하게 저장
            ok, buf = cv2.imencode('.jpg', frame)
            if ok:
                buf.tofile(os.path.join(args.out_dir, out_name))
                saved_this += 1
                n_frames_saved += 1
        cap.release()

        if saved_this:
            n_videos_saved += 1

    print(f'\n완료: 완전탐지 영상 {n_videos_saved}개에서 프레임 {n_frames_saved}장 저장')
    if n_missing:
        print(f'원본 못 찾음/열기실패: {n_missing}개')
    print(f'저장 위치: {args.out_dir}')


if __name__ == '__main__':
    main()
