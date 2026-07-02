"""
3단계: 박스가 그려진 검수용 영상을 하나씩 재생하면서, 사람이 직접 보고
아래 4가지 중 하나로 분류하는 도구.

영상 재생 창에서 키 입력:
    1 : 정상 오탐지   - 화면에 동물이 뚜렷하게 보이는데 MegaDetector가 놓침 (쉬운 케이스)
    2 : 어려운 오탐지 - 위장색/풀숲 등으로 인해 놓침 (어려운 케이스)
    3 : 과탐지        - MegaDetector가 박스를 그렸는데 실제로는 동물이 없거나 엉뚱한 위치
    4 : 정상          - 문제 없음 (원본은 이동/복사하지 않고, 로그에만 기록)
    r : 처음부터 다시 재생
    space : 일시정지 / 재생
    q : 지금까지 진행한 것을 저장하고 종료 (다음 실행 시 이어서 검수)

Windows에서 실행 예시:

    python 3_review_tool.py ^
        --rendered_dir "D:\\camera_trap\\review_videos" ^
        --original_dir "D:\\camera_trap\\videos" ^
        --sorted_dir  "D:\\camera_trap\\sorted" ^
        --log_csv     "D:\\camera_trap\\review_log.csv"

기본은 원본을 복사(copy)한다 (원본 보존). 이동시키고 싶으면 --move 를 추가한다.
"""

import argparse
import csv
import os
import shutil
import time
from pathlib import Path

import cv2

VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.asf', '.wmv'}

CATEGORY_MAP = {
    ord('1'): ('easy_miss', '01_정상오탐지_쉬운데못찾음'),
    ord('2'): ('hard_miss', '02_어려운오탐지_위장풀숲'),
    ord('3'): ('false_positive', '03_과탐지'),
    ord('4'): ('ok', '04_정상_문제없음'),
}

LOG_FIELDS = ['relative_path', 'category_code', 'category_name', 'reviewed_at']


def load_reviewed(log_path):
    reviewed = set()
    if os.path.exists(log_path):
        with open(log_path, newline='', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                reviewed.add(row['relative_path'])
    return reviewed


def append_log(log_path, row):
    is_new = not os.path.exists(log_path)
    with open(log_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def find_rendered_videos(rendered_dir):
    result = []
    for root, _, files in os.walk(rendered_dir):
        for fn in files:
            if Path(fn).suffix.lower() in VIDEO_EXTS:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, rendered_dir)
                result.append(rel)
    return sorted(result)


def find_original(original_dir, rel):
    """렌더링본과 같은 상대 경로의 원본을 찾는다. 확장자가 다를 경우를 대비해 stem으로도 검색."""
    direct = os.path.join(original_dir, rel)
    if os.path.exists(direct):
        return direct

    stem = os.path.splitext(rel)[0]
    parent = os.path.join(original_dir, os.path.dirname(rel))
    if os.path.isdir(parent):
        for fn in os.listdir(parent):
            if os.path.splitext(fn)[0] == os.path.basename(stem):
                return os.path.join(parent, fn)

    return None


def review_one_video(rendered_path, window_name):
    """영상을 반복 재생하며 키 입력을 기다린다. 눌린 키 코드 또는 'quit'/'skip'을 반환."""
    cap = cv2.VideoCapture(rendered_path)
    if not cap.isOpened():
        print(f'  [경고] 영상을 열 수 없음: {rendered_path}')
        return 'skip'

    fps = cap.get(cv2.CAP_PROP_FPS) or 15
    delay_ms = max(1, int(1000 / fps))
    paused = False
    instructions = '1:easy-miss  2:hard-miss  3:false-pos  4:ok   r:replay  space:pause  q:quit'

    try:
        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                display = frame.copy()
                cv2.putText(display, instructions, (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1, cv2.LINE_AA)
                cv2.imshow(window_name, display)

            key = cv2.waitKey(delay_ms) & 0xFF

            if key in CATEGORY_MAP:
                return key
            elif key == ord('r'):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            elif key == ord(' '):
                paused = not paused
            elif key == ord('q'):
                return 'quit'
    finally:
        cap.release()


def main():
    parser = argparse.ArgumentParser(description='MegaDetector 검수 분류 도구')
    parser.add_argument('--rendered_dir', required=True,
                         help='박스 그려진 검수용 영상 폴더 (2_render_review_videos.py 출력)')
    parser.add_argument('--original_dir', required=True,
                         help='원본 영상 폴더 (분류 시 이 폴더의 영상을 복사/이동)')
    parser.add_argument('--sorted_dir', required=True,
                         help='분류 결과를 저장할 폴더')
    parser.add_argument('--log_csv', required=True,
                         help='진행 상황과 결과를 기록할 CSV (재실행 시 이어서 진행하기 위해 사용)')
    parser.add_argument('--move', action='store_true',
                         help='지정하면 원본을 복사 대신 이동(move). 기본은 복사(원본 보존)')
    args = parser.parse_args()

    reviewed = load_reviewed(args.log_csv)
    videos = find_rendered_videos(args.rendered_dir)
    todo = [v for v in videos if v not in reviewed]

    print(f'전체 {len(videos)}개 중 {len(reviewed)}개 검수 완료, {len(todo)}개 남음\n')

    window_name = 'MegaDetector Review'
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    for i, rel in enumerate(todo):
        rendered_path = os.path.join(args.rendered_dir, rel)
        print(f'[{i + 1}/{len(todo)}] {rel}')

        key = review_one_video(rendered_path, window_name)

        if key == 'quit':
            print('\n중단하고 저장했습니다. 다음에 다시 실행하면 이어서 진행됩니다.')
            break
        if key == 'skip':
            continue

        code, folder_name = CATEGORY_MAP[key]

        if code != 'ok':
            original_path = find_original(args.original_dir, rel)
            if original_path is None:
                print(f'  [경고] 원본을 찾지 못해 파일 이동/복사는 건너뜀: {rel}')
            else:
                dest_dir = os.path.join(args.sorted_dir, folder_name, os.path.dirname(rel))
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, os.path.basename(original_path))
                if args.move:
                    shutil.move(original_path, dest_path)
                else:
                    shutil.copy2(original_path, dest_path)

        append_log(args.log_csv, {
            'relative_path': rel,
            'category_code': code,
            'category_name': folder_name,
            'reviewed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        })

    cv2.destroyAllWindows()
    print('검수 세션 종료.')


if __name__ == '__main__':
    main()
