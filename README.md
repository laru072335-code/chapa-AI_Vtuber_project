# AI_Vtuber_project

## Installation Method
 (Currently not supported. If you wish to run it on your own computer, refer to the Environment Setup section.)

## Overview
### This is the source code for a custom AI Vtuber.
- Currently capable of retrieving comments and speaking.
- Includes subtitle display and lip-sync functionality.
- Currently only compatible with macOS.

## Environment
### Python Side
Refer to `aienv_for_create.yml` in the Mamba environment.
### Unity Side
- Uses version 6000.2.7f2.
- Uses [NativeWebSocket](https://github.com/endel/NativeWebSocket), [Nuget](https://github.com/GlitchEnzo/NuGetForUnity), and [MessagePack](https://github.com/MessagePack-CSharp/MessagePack-CSharp).
- Also using [lilToon](https://lilxyzw.github.io/lilToon/) as the shader.
- Using [SAYO Official MMD Model](https://booth.pm/ja/items/6035432) as a temporary 3D model.
- ※ Model rights belong to their respective rights holders.  
- ※ This repository does not contain model data and is not intended for redistribution.
- ※ Please review the usage terms of the original source when using the models.
### Other
- WanComes is used to retrieve comments.
- For the local LLM, dsasai/llama3-elyza-jp-8b is used on Ollama.
- The Google Search API is also implemented for interest estimation purposes.
- VOICEVOX is used to control speech output.

## Environment Setup Method
- 1. Download [OneComme](https://onecomme.com/) and [VOICEVOX](https://voicevox.hiroshiba.jp/). Also, save your Google Search API key in a .env file named SEARCH_ENGINE.
- 2. Install [ollama](https://ollama.com/) using brew or similar, then install dsasai/llama3-elyza-jp-8b.
- 3. Set up the environment by referencing `aienv_for_create.yml`.
- 4. Download the Unity-side program (virtual_AI_roid0.1(alpha)) from the releases page. Also download the for_install.zip from the python branch.

## Startup Method
- 1. Launch OneComme and VOICEVOX.
- 2. Use OneComme's comment tester feature to add some comments. Alternatively, run comments_test.py from the python branch.
- 3. Run `AI_Vtuber_core_for_steam_voicevox_version.py` from the for_install directory in the environment specified in the environment section.
- 4. Launch the Unity-side virtual_AI_roid0.1(alpha). (Launching this before `AI_Vtuber_core_for_steam_voicevox_version.py` will cause it to fail.)

## Important Notes
- This project is under development, so various bugs may remain.

## Test Environment
- MacBook Air M4, 16GB RAM

