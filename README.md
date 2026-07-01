# MegaDetector 오탐지/과탐지 분류 파이프라인

카메라 트랩 동영상을 MegaDetector로 돌린 뒤, 사람이 직접 보면서 다음 3가지로 분류하기 위한 도구.

- 정상 오탐지 (쉬운데 못 찾음)
- 어려운 오탐지 (위장색, 풀숲)
- 과탐지

## 1. Windows 환경 준비

1. Python 3.9~3.13 설치 (https://www.python.org/downloads/windows/ 에서 "Add python.exe to PATH" 체크)
2. 이 폴더 전체를 윈도우 노트북으로 복사 (USB 말고, 아래 3번 항목 참고해서 내부 저장장치로)
3. VSCode에서 이 폴더 열기
4. 터미널(PowerShell)에서:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

- `megadetector` 패키지가 PyTorch까지 같이 설치합니다. GPU(NVIDIA)가 있는 노트북이면 설치 후
  `pip install torch --index-url https://download.pytorch.org/whl/cu121` 같은 식으로 CUDA 버전 torch로 교체하면
  속도가 훨씬 빠릅니다 (없어도 CPU로 동작은 함, 그냥 느림).

## 2. 실행 순서

```powershell
# 1단계: 동영상 폴더 전체에 MegaDetector 실행 (제일 오래 걸림)
python scripts\1_run_detection.py --input_dir "D:\camera_trap\videos" --output_json "D:\camera_trap\md_results.json"

# 2단계: 박스 그려진 검수용 영상 생성
python scripts\2_render_review_videos.py --json "D:\camera_trap\md_results.json" --video_dir "D:\camera_trap\videos" --out_dir "D:\camera_trap\review_videos"

# 3단계: 직접 보면서 분류 (중단해도 CSV 기준으로 이어서 진행됨)
python scripts\3_review_tool.py --rendered_dir "D:\camera_trap\review_videos" --original_dir "D:\camera_trap\videos" --sorted_dir "D:\camera_trap\sorted" --log_csv "D:\camera_trap\review_log.csv"
```

3단계 영상 창에서: `1`=정상 오탐지, `2`=어려운 오탐지, `3`=과탐지, `4`=정상(문제없음), `r`=다시재생, `space`=일시정지, `q`=저장 후 종료.

각 스크립트는 `--help`로 옵션을 볼 수 있습니다. 특히:
- 1단계 `--time_sample`: 몇 초마다 한 프레임을 볼지 (기본 1초). 동물이 빠르게 지나가는 영상이 많으면 0.5로 낮추세요.
- 2단계 `--confidence_threshold`: 화면에 박스를 그릴 기준. 재탐지 없이 이 값만 바꿔서 여러 번 다시 렌더링 가능.
- 3단계 `--move`: 기본은 원본을 복사(copy)함. 원본을 그대로 폴더별로 정리하고 싶으면 `--move` 추가 (되돌리기 어려우니 처음엔 복사로 해보고 확인 후 전환 권장).

## 3. USB냐 내장 HDD/SSD냐

USB에 꽂힌 상태로 바로 처리하지 말고, **먼저 내장 저장장치(HDD/SSD)로 복사한 뒤 거기서 처리하는 걸 권장**합니다.

이유:
- MegaDetector 영상 처리는 같은 파일을 여러 번 읽습니다(1단계 프레임 추출, 2단계 다시 프레임 추출해서 렌더링). USB 연결은 특히 USB 2.0이거나 외장 HDD일 경우 순차 읽기 속도가 내장 드라이브보다 훨씬 느려서 전체 처리 시간이 크게 늘어납니다.
- 긴 배치 작업 도중 USB 연결이 살짝이라도 끊기면(케이블 흔들림, 절전모드 등) 그 시점 파일이 깨지거나 프로세스가 멈출 수 있습니다. 내장 드라이브는 이런 위험이 없습니다.
- 3단계에서 원본을 폴더별로 복사/이동하는데, USB 위에서 이 작업을 하면 쓰기 속도까지 느려서 체감이 큽니다.

권장 순서: USB의 원본 영상을 통째로 내장 HDD(SSD면 더 좋음)의 작업 폴더로 복사 → 그 폴더를 대상으로 1~3단계 실행 → 결과(json, review_videos, sorted, csv)도 내장 드라이브에 쌓임. 필요하면 최종 결과만 다시 USB나 외장 드라이브로 백업.

주의: 원본 데이터 용량만큼, 그리고 검수용 렌더링 영상(원본과 비슷한 용량) + 분류 시 복사본까지 감안하면 여유 공간이 원본의 2~3배 정도 필요할 수 있습니다. 내장 드라이브 여유 공간을 먼저 확인하세요.
