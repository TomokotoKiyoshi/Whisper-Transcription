cd .

mkdir third_party_wheels 2>NUL

python -m pip wheel openai-whisper ^
       --no-deps --no-binary :all: ^
       --wheel-dir third_party_wheels
pause