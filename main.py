name: Gerar APK com Link Direto

on:
  push:
    branches: [ "main" ]

jobs:
  build:
    runs-on: ubuntu-22.04

    steps:
    - name: Baixar o código do projeto
      uses: actions/checkout@v4

    - name: Configurar o Java 17
      uses: actions/setup-java@v4
      with:
        distribution: 'temurin'
        java-version: '17'

    - name: Configurar o Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Instalar dependências de compilação
      run: |
        sudo apt-get update
        sudo apt-get install -y build-essential libsqlite3-dev ffmpeg libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libportmidi-dev libswscale-dev libavformat-dev libavcodec-dev zlib1g-dev
        sudo apt-get install -y libunwind-dev libgstreamer1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-good libmtdev-dev xclip xsel libjpeg-dev
        pip install --upgrade pip
        pip install buildozer cython virtualenv

    - name: Compilar o APK com Buildozer
      run: |
        yes | buildozer android debug

    - name: Criar Release e Link Direto do APK
      uses: softprops/action-gh-release@v1
      with:
        tag_name: v1.0.${{ github.run_number }}
        name: App Controle de Custos v1.0.${{ github.run_number }}
        files: bin/*.apk
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
