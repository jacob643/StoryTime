@echo off

set DEBUG = true

set HTML_FILE = "storytime.html"
set NAME-"dolphin-llama3"
set PORT="11434"
set IPADRESS = "localhost:%PORT%"

start "" "%HTML_FILE%"

if "%DEBUG%"=="true" (
	cmd /k "ollama serve & ollama run %NAME%"
) else (
	cmd /c "ollama serve & ollama run %NAME%"
)