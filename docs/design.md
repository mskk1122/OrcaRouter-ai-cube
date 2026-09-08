# AI Cube — 설계 기준 (2026-09-07)

사용자가 부품 선정·외형·구현을 위임한 새 프로젝트. 현재 작업 폴더는 파일과 커밋이 없는 초기 저장소이므로 이 폴더에 제작물을 만든다.

## 제품

- 책상용 둥근 모서리 큐브. 약 82 × 78 × 82 mm, 유선 5V 전원, 배터리 없음.
- Raspberry Pi Zero 2 W + Raspberry Pi OS Lite 64-bit, Python 3.11 이상.
- 전면 Waveshare 1.3inch LCD Module, ST7789 240×240 SPI: 검정 배경에 두 눈. 대기/듣기/추론/말하기/오류 표정.
- 머리 외부는 구멍이나 센서가 없는 불투명 비금속 플라스틱. 안쪽 35×35 mm 구리 전극, AT42QT1010 Adafruit #1374, 3.3V 동작. 접촉·초근접 감지를 목표로 하고 공중 감지 거리 보장 없음. 상판 센서 영역 1.0 mm, 그 외 2 mm. 센서 감지 후 손을 떼도 녹음 유지.
- Adafruit Mini USB Microphone #3367 + 짧은 Micro USB OTG 케이블. MAX98357A #3006 + 40 mm 4Ω 3W 스피커.
- USB 마이크는 입력, I2S는 출력 전용으로 나누어 GPIO 충돌 및 커스텀 전이중 오디오 드라이버를 피한다.

## 상태·개인정보

idle → listening → thinking → speaking → idle. 예외 시 error → idle.
대기 중 마이크 장치를 열지 않는다. 감지 후 최대 12초 녹음, 5초 무발화 취소, 발화 후 1초 무음 종료. 녹음 시작 전 스피커 알림음 사용 안 함. 듣기 중 화면으로 알린다.
한 번 감지당 한 대화만 실행. 처리 중 새 감지는 버리며, 대기 복귀 후 손을 떼고 다시 감지해야 재실행. 시작 시 손을 떼야 활성화. 키·음성·대화 본문은 로그에 쓰지 않고 오디오는 메모리/임시 디렉터리에서 처리 후 제거한다.

## API

공식 https://docs.orcarouter.ai/advanced/audio-input 과 /other-apis/tts 확인.
base URL https://api.orcarouter.ai/v1. POST /chat/completions에 WAV base64 input_audio를 보내 음성 이해+응답을 한 번에 요청. 기본 google/gemini-2.5-flash (공식 음성 입력 예시), 모델은 환경변수로 교체. 자동 라우터가 음성 지원 모델을 고른다고 가정하지 않는다.
POST /audio/speech, openai/tts-1, voice alloy, response_format wav. 동일 OrcaRouter 키 사용. 유한 timeout, HTTP 오류·잘못된 응답·오디오 오류 시 복귀. 클라이언트 자동 재시도 없음(중복 과금 방지). 실제 키가 없으므로 유료 API 성공 주장은 하지 않는다.

## GPIO 계약 (BCM)

LCD MOSI 10, SCLK 11, CS 8, DC 25, RST 27, BL 24.
AT42QT1010 OUT 17 (active high, 3.3V).
MAX98357A BCLK 18, LRC 19, DIN 21, VIN 5V, GND 공통.
스피커는 앰프 +/− 사이에만 연결한다.

## 산출물과 검증

Python 실행 코드, 오프라인 시뮬레이션, 오류·상태·무음·API 페이로드 테스트, systemd 예제, 한국어 설치/배선/BOM/제작 안내, 편집 가능한 CAD 및 STL, 실제 CAD 기반 미리보기.
실물 조립·GPIO·음성 품질·센서 거리·열·최종 끼움 공차는 미검증으로 명시한다. CAD 치수의 제조사 출처와 설계 여유/가정은 분리한다.
