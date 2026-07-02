"""
배치 탐지 실행기.

MegaDetector video 처리를 한 프로세스로 오래 돌리면 ~50개 영상 이후 hang이 발생하는
문제가 있어서(자원 누적), 폴더 안의 영상을 CHUNK개씩 나눠 '매 배치마다 새 파이썬
프로세스'로 1_run_detection.py 를 돌리고, 마지막에 결과 json을 하나로 병합한다.

임시 폴더는 하드링크(os.link, 관리자 권한 불필요, 같은 드라이브)로 구성하므로
영상 파일을 실제로 복사하지 않는다.

사용:
    python scripts\batch_run_detection.py ^
        --input_dir "C:\JOB\data\bird" ^
        --output_json "C:\JOB\output\bird_md.json" ^
        --chunk 40 ^
        --model MDV5A
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

PY = sys.executable
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DETECT_SCRIPT = os.path.join(THIS_DIR, '1_run_detection.py')
VIDEO_EXTS = ('.mp4', '.mov', '.avi', '.mkv', '.asf', '.wmv')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input_dir', required=True)
    ap.add_argument('--output_json', required=True)
    ap.add_argument('--chunk', type=int, default=40, help='배치당 영상 개수 (hang 임계치 51보다 작게)')
    ap.add_argument('--model', default='redwood', help='기본 redwood = MegaDetector v6')
    args = ap.parse_args()

    vids = sorted(f for f in os.listdir(args.input_dir)
                  if f.lower().endswith(VIDEO_EXTS))
    total = len(vids)
    print(f'전체 {total}개 영상, 배치당 {args.chunk}개로 처리\n', flush=True)

    stage = os.path.join(os.path.dirname(args.input_dir), '_batch_stage')
    out_dir = os.path.dirname(args.output_json)
    os.makedirs(out_dir, exist_ok=True)

    all_images = []
    cats = None
    info = None

    n_batches = (total + args.chunk - 1) // args.chunk
    for b in range(n_batches):
        chunk = vids[b * args.chunk:(b + 1) * args.chunk]

        # 스테이지 폴더 초기화
        if os.path.isdir(stage):
            shutil.rmtree(stage)
        os.makedirs(stage)

        # 하드링크(복사 없이) 구성, 실패 시 복사로 폴백
        for name in chunk:
            target = os.path.join(args.input_dir, name)
            link = os.path.join(stage, name)
            try:
                os.link(target, link)
            except OSError:
                shutil.copy2(target, link)

        batch_json = os.path.join(out_dir, f'_batch_{b}.json')
        print(f'\n===== 배치 {b + 1}/{n_batches} ({len(chunk)}개) =====', flush=True)

        # 매 배치마다 새 프로세스 (-u: 실시간 출력)
        rc = subprocess.run(
            [PY, '-u', DETECT_SCRIPT,
             '--input_dir', stage,
             '--output_json', batch_json,
             '--model', args.model,
             '--checkpoint_frequency', '100000'],
        ).returncode

        if rc != 0:
            print(f'[경고] 배치 {b + 1} 비정상 종료 (rc={rc}) — 부분 결과라도 병합 시도', flush=True)

        if os.path.exists(batch_json):
            d = json.load(open(batch_json, encoding='utf-8'))
            all_images.extend(d.get('images', []))
            cats = d.get('detection_categories', cats)
            info = d.get('info', info)

    if os.path.isdir(stage):
        shutil.rmtree(stage)

    merged = {'images': all_images, 'detection_categories': cats, 'info': info}
    with open(args.output_json, 'w', encoding='utf-8') as f:
        json.dump(merged, f)

    print(f'\n완료. 병합된 영상 {len(all_images)}개 → {args.output_json}', flush=True)


if __name__ == '__main__':
    main()
