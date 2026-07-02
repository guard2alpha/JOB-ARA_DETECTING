"""
손상된 동영상 사전 검사기.

일부 파일이 'moov atom not found' 등으로 깨져 있으면 MegaDetector 처리 중 프로세스가
멈춘다(hang). 탐지 전에 모든 영상을 빠르게 열어보고, 정상적으로 열리지 않거나 검사가
멈추는(hang) 파일을 격리 폴더로 옮긴다.

손상 파일은 검사 중에도 cv2가 멈출 수 있으므로, 파일마다 '별도 프로세스 + 타임아웃'으로
검사한다.

사용:
    python scripts\scan_and_quarantine.py ^
        --input_dir "C:\JOB\data\bird" ^
        --quarantine_dir "C:\JOB\data\_corrupt" ^
        --timeout 25
"""

import argparse
import os
import shutil
import subprocess
import sys

# 서브프로세스에서 실행할 검사 코드: 열기 + 프레임수 + 첫 프레임 + 중간 프레임 읽기
CHECK_CODE = r"""
import cv2, sys
p = sys.argv[1]
cap = cv2.VideoCapture(p)
if not cap.isOpened():
    print('BAD_OPEN'); sys.exit(2)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
if n <= 0:
    print('BAD_FRAMECOUNT'); sys.exit(3)
ret, fr = cap.read()
if not ret or fr is None:
    print('BAD_FIRST_FRAME'); sys.exit(4)
# 중간 프레임도 확인 (뒷부분 손상 탐지)
cap.set(cv2.CAP_PROP_POS_FRAMES, n // 2)
ret2, fr2 = cap.read()
cap.release()
if not ret2 or fr2 is None:
    print('BAD_MID_FRAME'); sys.exit(5)
print('OK', n)
"""

VIDEO_EXTS = ('.mp4', '.mov', '.avi', '.mkv', '.asf', '.wmv')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input_dir', required=True)
    ap.add_argument('--quarantine_dir', required=True)
    ap.add_argument('--timeout', type=int, default=25, help='파일당 검사 제한시간(초)')
    args = ap.parse_args()

    vids = sorted(f for f in os.listdir(args.input_dir)
                  if f.lower().endswith(VIDEO_EXTS))
    os.makedirs(args.quarantine_dir, exist_ok=True)

    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    bad = []
    for i, name in enumerate(vids, 1):
        p = os.path.join(args.input_dir, name)
        try:
            r = subprocess.run(
                [sys.executable, '-c', CHECK_CODE, p],
                capture_output=True, text=True, timeout=args.timeout, env=env)
            ok = (r.returncode == 0)
            reason = r.stdout.strip().split()[0] if r.stdout.strip() else 'ERR'
        except subprocess.TimeoutExpired:
            ok = False
            reason = 'TIMEOUT(hang)'

        print(f'[{i}/{len(vids)}] {"OK " if ok else "BAD"} {name}'
              + ('' if ok else f'  -> {reason}'), flush=True)

        if not ok:
            bad.append((name, reason))
            shutil.move(p, os.path.join(args.quarantine_dir, name))

    print(f'\n검사 완료: 전체 {len(vids)}개 중 손상 {len(bad)}개 격리 '
          f'→ {args.quarantine_dir}')
    for name, reason in bad:
        print(f'  - {name} ({reason})')


if __name__ == '__main__':
    main()
