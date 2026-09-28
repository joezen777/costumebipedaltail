# Repository ground rules

These instructions apply throughout this repository.

## Execution environment
- Never use PowerShell.
- Run all coding, execution commands, and scripts in the user's WSL2 Ubuntu environment.
- When a Windows tool requires a launcher, use cmd.exe only to invoke wsl.exe; execute the actual command or script inside Ubuntu.
- WSL repository path: /mnt/c/Users/josep/OneDrive/Documents/angularmomflyer.

## Preferred stack
- Prefer Python for application logic, scripts, and backend work.
- When UI work is needed, prefer React with Vite and MUI.
- Prefer a Python FastAPI backend for the UI.

## Git and documentation
- Initialize Git when starting the repository (already completed here).
- Maintain a .gitignore suitable for the Python workspace and extend it as the stack grows.
- After each logical change, make a Git commit.
- Prefix each commit message with the number of tokens used for that operation, followed by an underscore and the descriptive commit message.
- Use actual token usage when available. When exact per-operation usage is unavailable, do not invent an exact count: clearly label an estimate, e.g. estimated-1500-tokens_Describe the change.
- Keep design decisions, architecture, and relevant scientific reasoning up to date in docs/ as work proceeds.

## Local compute and image generation
- Python is already installed in WSL2 Ubuntu, and CUDA is working.
- The GPU is an NVIDIA RTX 5070 with 12 GB VRAM. Assess memory needs before selecting or running local models.
- Many LLMs are already downloaded locally; consider existing models when local inference is needed.
- ComfyUI is available in WSL2. Use it only when pictures need to be generated with zImageTurbo models.
- Start ComfyUI with ~/comfyuiinstall.sh when needed.
- Consult ~/cradleai for reference code using ComfyUI with zImageTurbo.

## Credentials and paid services
- Never store secrets. Do not search for or otherwise pursue secrets.
- Never use API or cloud-platform tokens merely because they are present on disk.
- Use non-free services only when the user has explicitly provided a token for that use in this conversation.
- If that token expires, notify the user and wait for an updated token before continuing use of the service.

## Mechanical design and 3D printing
- FreeCAD, OpenSCAD, and Open STEP Viewer are available for mechanical design and inspection.
- Design mechanical parts with the intent to print them on one of the following available setups:
  - Anycubic Photon Mono 5s using Anycubic ABS Pro 2 resin.
  - Ender 3 V2 with a Sprite Pro extruder and a 0.2 mm nozzle; select filament appropriate to the application.
- Account for the selected printer, material, print orientation, supports, tolerances, and mechanical requirements when designing printable parts.
