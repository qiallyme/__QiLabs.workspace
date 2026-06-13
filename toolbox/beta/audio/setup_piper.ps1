# Setup Piper TTS for Windows
$PiperVersion = "2023.11.14-2" # Latest as of search or similar
$Url = "https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_windows_amd64.zip" 
# Note: Version numbers might need adjustment based on latest releases

Write-Host "Creating bin directory..."
If (!(Test-Path -Path "bin")) { New-Item -ItemType Directory -Path "bin" }
If (!(Test-Path -Path "bin/models")) { New-Item -ItemType Directory -Path "bin/models" }

Write-Host "Downloading Piper..."
Invoke-WebRequest -Uri $Url -OutFile "bin/piper.zip"

Write-Host "Extracting Piper..."
Expand-Archive -Path "bin/piper.zip" -DestinationPath "bin/temp"
Move-Item -Path "bin/temp/piper/*" -DestinationPath "bin/"
Remove-Item -Path "bin/temp" -Recurse
Remove-Item -Path "bin/piper.zip"

Write-Host "Downloading default voice models (Medium quality)..."
# Narrator: Lessac
Invoke-WebRequest -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" -OutFile "bin/models/en_US-lessac-medium.onnx"
Invoke-WebRequest -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" -OutFile "bin/models/en_US-lessac-medium.onnx.json"

# Female: Amy
Invoke-WebRequest -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx" -OutFile "bin/models/en_US-amy-medium.onnx"
Invoke-WebRequest -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json" -OutFile "bin/models/en_US-amy-medium.onnx.json"

# Male: Bryce
Invoke-WebRequest -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/bryce/medium/en_US-bryce-medium.onnx" -OutFile "bin/models/en_US-bryce-medium.onnx"
Invoke-WebRequest -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/bryce/medium/en_US-bryce-medium.onnx.json" -OutFile "bin/models/en_US-bryce-medium.onnx.json"

Write-Host "Setup complete. Piper is ready in bin/piper.exe"
Write-Host "FFmpeg must be installed on your system PATH for normalization to work."
