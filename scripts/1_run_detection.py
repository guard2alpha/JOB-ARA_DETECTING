"""
1단계: 폴더 안의 모든 동영상에 MegaDetector를 돌려서 탐지 결과를 JSON으로 저장한다.

Windows에서 실행 예시:

    python 1_run_detection.py ^
        --input_dir "D:\\camera_trap\\videos" ^
        --output_json "D:\\camera_trap\\md_results.json"

시간이 오래 걸리는 작업이므로 --checkpoint_frequency 옵션으로 중간 저장을 하고,
중단 후 같은 명령을 다시 실행하면 자동으로 이어서 처리한다(resume_from_checkpoint='auto').
"""

import argparse

from megadetector.detection.process_video import ProcessVideoOptions, process_videos


def main():
    parser = argparse.ArgumentParser(description='폴더 내 모든 동영상에 MegaDetector 실행')

    parser.add_argument('--input_dir', required=True,
                         help='원본 동영상이 들어있는 폴더 (하위 폴더까지 재귀적으로 탐색)')
    parser.add_argument('--output_json', required=True,
                         help='탐지 결과를 저장할 json 파일 경로')
    parser.add_argument('--model', default='redwood',
                         help='사용할 모델 (기본 redwood = MegaDetector v6 / MDv1000). '
                              'v5로 쓰려면 --model MDV5A')
    parser.add_argument('--time_sample', type=float, default=1.0,
                         help='N초에 한 프레임씩 샘플링 (기본 1초당 1프레임)')
    parser.add_argument('--confidence_threshold', type=float, default=0.05,
                         help='json에 기록할 최소 confidence. 나중에 렌더링 단계에서 '
                              '더 높은 threshold로 필터링할 수 있으니 여기서는 낮게 잡아둔다')
    parser.add_argument('--checkpoint_frequency', type=int, default=10,
                         help='N개 동영상마다 체크포인트 저장 (중단 후 재시작 대비)')

    args = parser.parse_args()

    options = ProcessVideoOptions()
    options.model_file = args.model
    options.input_video_file = args.input_dir
    options.output_json_file = args.output_json
    options.recursive = True
    options.time_sample = args.time_sample
    options.json_confidence_threshold = args.confidence_threshold
    options.checkpoint_frequency = args.checkpoint_frequency
    options.resume_from_checkpoint = 'auto'
    options.verbose = True

    process_videos(options)

    print('\n완료. 결과 json:', args.output_json)
    print('다음 단계: 2_render_review_videos.py 로 박스가 그려진 검수용 영상을 만드세요.')


if __name__ == '__main__':
    main()
