# 라즈베리파이 설치·동작 점검

실물 없는 PC에서 검증된 부분과 Pi에서 직접 확인해야 하는 부분을 구분한다. 아래 명령은 **라즈베리파이의 터미널**에서 실행한다. PC 시뮬레이션은 맨 아래에 있다.

## 1. OS와 파일

Raspberry Pi Imager로 Zero2W에 Raspberry Pi OS Lite **64-bit**를 설치한다. Python3.11 이상이 있는 배포판을 사용한다. Imager에서 사용자 이름,2.4GHz Wi-Fi, SSH를 설정한다. 이 안내는 최신 부트 경로 `/boot/firmware/config.txt` 기준이다.

프로젝트 전체를 Pi의 `~/ai-cube`에 복사한다. `.tools`, `.git`, `__pycache__`는 복사할 필요가 없다.

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-setuptools python3-pil python3-numpy python3-gpiozero python3-lgpio python3-spidev alsa-utils rsync
cd ~/ai-cube
python3 -m venv --system-site-packages .venv
.venv/bin/python -m unittest discover -s tests -v
```

실행은 프로젝트 폴더에서 `python -m ai_cube`로 하므로 pip 패키지 설치는 필수가 아니다. 다른 경로에서 `ai-cube` 명령을 사용하려면 `.venv/bin/pip install --no-deps --no-build-isolation -e .`로 설치할 수 있다.

## 2. SPI와 스피커 overlay

먼저 [배선표](hardware.md)에 따라 연결한다. `/boot/firmware/config.txt`를 편집하고 기존 설정과 중복되지 않도록 `[all]` 아래에 다음을 넣는다. 기존 `dtparam=audio=on`은 주석 처리한다.

```ini
[all]
dtparam=spi=on
dtparam=audio=off
dtoverlay=max98357a,no-sdmode
```

`no-sdmode`는 이 프로젝트처럼 앰프의 SD 핀을 배선하지 않을 때 사용한다. 공식 Adafruit #3006의 기본 풀업을 전제로 한다. 다른 제조사의 MAX98357 보드는 SD 회로가 다를 수 있다.

```bash
dtoverlay -h max98357a
sudo usermod -aG audio,gpio,spi "$USER"
sudo reboot
```

재접속 후 확인한다.

```bash
ls /dev/spidev0.0
arecord -l
aplay -l
```

목록에 USB 마이크와 MAX98357A가 각각 있어야 한다. 카드 순번0/1은 부팅마다 달라질 수 있어 이름을 사용한다. 예를 들어 `card 1: Device [...]`라면 입력은 `plughw:CARD=Device,DEV=0`, `card 0: MAX98357A [...]`라면 출력은 `plughw:CARD=MAX98357A,DEV=0`이다. 실제 이름이 다르면 그대로 바꾼다. **예시 이름은 모든 USB 마이크에서 같지 않다.**

## 3. 설정

```bash
cd ~/ai-cube
cp .env.example .env
chmod 600 .env
nano .env
```

OrcaRouter 콘솔에서 발급받은 키를 `ORCAROUTER_API_KEY=`에 입력한다. 키는 채팅에 보내지 말고 기기에만 저장한다. 부품 테스트 전에는 비워두어도 된다.

| 값 | 기본값 | 의미 |
|---|---|---|
| ORCAROUTER_MODEL | google/gemini-2.5-flash | 공식 음성 입력 예시의 모델. 계정에서 사용 가능한 음성 지원 모델인지 확인 |
| ORCAROUTER_TTS_MODEL | openai/tts-1 | OrcaRouter의 `/audio/speech`로 호출 |
| ORCAROUTER_VOICE | alloy | TTS 목소리 |
| CUBE_CAPTURE_DEVICE | plughw:CARD=Device,DEV=0 | `arecord -l` 결과에 맞게 수정 |
| CUBE_PLAYBACK_DEVICE | plughw:CARD=MAX98357A,DEV=0 | `aplay -l` 결과에 맞게 수정 |
| CUBE_VOLUME | 0.25 | 0~1, PCM 볼륨 배율. 처음에는 낮게 유지 |
| CUBE_RMS_THRESHOLD | 550 | 1~20000, 음성 시작 판정의 PCM 에너지 기준. 정전식 감도와 무관 |
| CUBE_MAX_RECORD_SECONDS | 12 | 1~12초 녹음 상한 |
| CUBE_API_TIMEOUT | 45 | 각 API 요청의 전체 제한시간, 1~120초. 초과 시 요청 프로세스 종료 |
| CUBE_ROTATION | 0 | LCD 회전0/90/180/270 |

`.env`의 기존 운영체제 환경변수가 우선한다. 값은 단순 `KEY=VALUE` 형태이며 셸 명령·변수 치환은 실행하지 않는다.

## 4. 부품별 확인 — API 호출 없음

```bash
.venv/bin/python -m ai_cube --doctor
.venv/bin/python -m ai_cube --display-test
.venv/bin/python -m ai_cube --sensor-test
```

센서 테스트는 `detected` / `released`만 표시하고 녹음하지 않는다. 종료는 Ctrl+C. 화면 테스트는 대기/듣기/생각/말하기/오류를 차례로 표시한 뒤 꺼진다. 센서를 건드린 상태로 부팅하면 앱은 손을 떼기 전까지 대화를 시작하지 않는다.

아래 녹음 검사는 **명시적으로3초간 녹음**하므로 직접 말하며 실행한다. 장치명은 본인 기기에 맞게 바꾼다.

```bash
arecord -D plughw:CARD=Device,DEV=0 -f S16_LE -r 16000 -c 1 -d 3 /tmp/cube-mic-test.wav
```

앱과 같은25% 볼륨 변환·스테레오 변환을 적용해 스피커로 확인한다.

```bash
.venv/bin/python -c "from pathlib import Path; from ai_cube.__main__ import load_env; from ai_cube.config import Settings; from ai_cube.audio import AlsaAudio; load_env('.env'); AlsaAudio(Settings.from_env()).play(Path('/tmp/cube-mic-test.wav').read_bytes())"
rm /tmp/cube-mic-test.wav
```

화면 색상·방향·그림 잘림이 있으면 회전 설정과 **정확한 SKU15867** 여부를 먼저 확인한다. 다른 ST7789 모듈은 좌표 오프셋/초기화가 다를 수 있다.

## 5. 전체 동작

```bash
.venv/bin/python -m ai_cube
```

1. 머리에서 손을 떼고 기다린다. 대기 중에는 마이크 장치가 열리지 않는다.
2. 머리를 가볍게 건드린다. 민트색 듣기 표정이 되면 손을 떼고 말한다.
3. 약0.12초 이상 연속 소리가 나면 발화로 인식한다. 이후1초 무음이면 종료한다.5초 동안 말을 안 하면 취소하고, 계속 말해도12초에 종료한다.
4. 보라색 생각 표정에서 음성 이해·추론·TTS를 요청한다. 답변이 준비되면 입이 움직이며 재생한다.
5. 다시 머리에서 손을 뗀 상태를 거쳐야 다음 질문을 받는다. 처리 중의 접촉은 예약되지 않는다.

이 프로젝트의 무음 종료는 **간단한 음량 기반 판정**이다. 음악·팬 소음·긴 타격음도 발화로 오인할 수 있다. 조용한 환경에서 말소리가 잘리는 경우 기준을 조금 낮추고, 주변 소음으로 녹음이 끝나지 않으면 높인다. 화면의 듣기 막대와 말하기 입은 상태 애니메이션이며 실제 파형/입모양 동기화가 아니다.

현재 대화는 질문마다 독립적이다. 장기 기억과 이전 대화 전송은 없다. 녹음은 메모리에서 WAV로 만들어 OrcaRouter에 전송한다. TTS 음성은 재생용 임시 파일에만 두고 작업 종료 시 삭제한다. 강제 전원 차단까지 삭제를 보장하지는 않는다. 일반 로그에는 키·녹음·사용자 발언·답변 본문을 남기지 않는다. 인터넷 연결 및 OrcaRouter의 해당 모델 이용 권한·잔액이 필요하다.

## 6. 부팅 자동 실행 (부품 테스트 후)

서비스는 전용 계정과 `/opt/ai-cube`, `/etc/ai-cube.env`를 사용한다. 아래 계정 생성은 최초1회 실행한다. 이미 같은 이름의 계정이 있으면 재사용 여부를 먼저 확인한다.

```bash
sudo useradd --system --home-dir /opt/ai-cube --no-create-home --groups audio,gpio,spi ai-cube
sudo mkdir -p /opt/ai-cube
sudo rsync -a --exclude=.git --exclude=.env --exclude=.venv --exclude=.tools --exclude=__pycache__ ./ /opt/ai-cube/
sudo python3 -m venv --system-site-packages /opt/ai-cube/.venv
sudo install -m 600 -o ai-cube -g ai-cube .env /etc/ai-cube.env
sudo install -m 644 deploy/ai-cube.service /etc/systemd/system/ai-cube.service
sudo systemctl daemon-reload
sudo systemctl enable --now ai-cube
sudo systemctl status ai-cube
```

수동 실행 중인 앱은 Ctrl+C로 종료한 다음 서비스를 켠다. 두 프로세스가 GPIO와 오디오를 동시에 점유하면 안 된다.

```bash
journalctl -u ai-cube -n 50 --no-pager
sudo systemctl restart ai-cube
sudo systemctl stop ai-cube
```

서비스의 개인 임시 폴더는 tmpfs를 사용한다. 재부팅 시 임시 음성은 사라진다. 재생 중 전원을 바로 뽑지 말고 `sudo poweroff`로 종료한다.

## 문제 진단

| 증상 | 먼저 확인할 것 |
|---|---|
| LCD가 안 켜짐 | 3V3/GND, BL은GPIO24, SPI 활성화, gpio/spi 그룹, 단자 순서 |
| 감지 안 됨 | 센서VIN3.3V, OUT GPIO17, 외부 전극 패드 연결, 상판 공극·두께, 케이스 닫은 뒤 재보정 |
| 계속 감지됨 | 손을 떼고 재부팅, 전극과 접지/전원선 거리, 도전성 소재 여부 |
| 마이크 실패 | USB 포트와OTG 데이터 케이블, `arecord -l`, 카드 이름, 다른 녹음 프로그램 점유 |
| 소리가 안 남 | overlay 및재부팅, 앰프VIN5V, BCLK18/LRC19/DIN21, SPK 두 단자, 카드 이름 |
| 듣고 나서 오류 | 기기 시각/NTP, Wi-Fi, OrcaRouter 키·잔액·음성 모델 사용 권한, TTS 모델 |
| 소음이 질문으로 전송됨 | RMS 기준을 높이고 마이크 위치 조정. 현재 음량 게이트의 한계 |
| 재부팅/딱딱거림 | 전원 전압강하, 케이블, 볼륨, 앰프 전원 배선. 클록 시작/종료 팝은 실물에서 평가 |

```bash
vcgencmd measure_temp
vcgencmd get_throttled
```

조립 후30분 동작,50회 터치, 무발화10회, Wi-Fi 단절 후 복구를 시험한다. 자세한 합격 기준은 [검증 기록](verification.md)을 따른다.

## PC 오프라인 시뮬레이션

Python3.11 이상과 Pillow/numpy가 필요하다. Pi용 패키지는 설치하지 않아도 된다.

```bash
python -m pip install Pillow numpy
python -m unittest discover -s tests -v
python -m ai_cube --simulate
```

`artifacts/faces/`에 PNG/GIF를 만들고 상태 전이를 출력한다. 실제 API·녹음·스피커·GPIO를 사용하지 않는 시뮬레이션이다.

## API 근거

[OrcaRouter 음성 입력](https://docs.orcarouter.ai/advanced/audio-input)의 OpenAI형 `input_audio` 경로와 [TTS](https://docs.orcarouter.ai/other-apis/tts)의 `/audio/speech`를 사용한다. 음성 모델 선택을 보장할 수 없는 `orcarouter/auto`를 기본 입력 모델로 사용하지 않는다. 한 질문에 음성 포함 Chat 요청1회와 TTS 요청1회를 보내며, 클라이언트 자동 재시도는 하지 않는다. 서버의 과금 정책과 모델 목록은 콘솔에서 확인한다.
