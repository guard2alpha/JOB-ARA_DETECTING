"""
2단계: 1단계에서 만든 json 결과를 바탕으로, 박스가 그려진 '검수용' 동영상을 만든다.
사람이 직접 눈으로 보고 정상/어려운 오탐지/과탐지를 판단해야 하므로,
탐지가 하나도 없는 프레임도 전부 포함해서 렌더링한다 (trim_to_detections=False).

Windows에서 실행 예시:

    python 2_render_review_videos.py ^
        --json "D:\\camera_trap\\md_results.json" ^
        --video_dir "D:\\camera_trap\\videos" ^
        --out_dir "D:\\camera_trap\\review_videos" ^
        --confidence_threshold 0.2

--confidence_threshold 는 "화면에 박스를 그릴지 말지"만 결정한다.
1단계에서 이미 낮은 threshold로 json을 만들어 뒀기 때문에,
여기서는 재탐지 없이 --confidence_threshold 값만 바꿔가며 여러 번 다시 렌더링해볼 수 있다.
(예: 과탐지가 애매한 케이스만 더 낮은 threshold로 다시 살펴보고 싶을 때)
"""

import argparse

from megadetector.visualization.visualize_video_output import (
    VideoVisualizationOptions,
    visualize_video_output,
)


def main():
    parser = argparse.ArgumentParser(description='탐지 결과를 영상에 그려서 검수용 영상 생성')

    parser.add_argument('--json', required=True, help='1단계에서 생성한 json 결과 파일')
    parser.add_argument('--video_dir', required=True, help='원본 동영상 폴더')
    parser.add_argument('--out_dir', required=True, help='박스가 그려진 영상을 저장할 폴더')
    parser.add_argument('--confidence_threshold', type=float, default=0.2,
                         help='이 값 이상인 탐지만 화면에 박스로 표시 (기본 0.2)')
    parser.add_argument('--n_workers', type=int, default=4,
                         help='병렬 처리 워커 수 (노트북 사양에 맞게 조절, 기본 4)')

    args = parser.parse_args()

    options = VideoVisualizationOptions()
    options.confidence_threshold = args.confidence_threshold
    options.rendering_fs = 'auto'
    options.trim_to_detections = False  # 탐지 없는 구간도 그대로 보존 (미탐 여부 판단을 위해 필수)
    options.parallelize_rendering = True
    options.parallelize_rendering_n_cores = args.n_workers

    visualize_video_output(args.json, args.out_dir, args.video_dir, options)

    print('\n완료. 검수용 영상 폴더:', args.out_dir)
    print('다음 단계: 3_review_tool.py 로 직접 보면서 분류하세요.')


if __name__ == '__main__':
    main()
