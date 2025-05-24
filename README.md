# srt-term-converter
GUI App for auto-correcting SRT subtitles with a user-editable regex dictionary while preserving timestamps.

## Overview

- **Objective**: Automatically correct transcription errors in SRT subtitle files by replacing text using a user-editable regex dictionary.
- **Functionality**:
  - Parse the SRT file to extract blocks with an identifier, timestamp, and text.
  - Allow users to edit a regex dictionary in the GUI using the "pattern => replacement" format.
  - Process each regex pair sequentially, handling replacements one occurrence at a time.
  - **New**: Fill gaps between subtitles when the interval is below a specified threshold.
  - Reassemble the updated content into SRT format and save it to a user-selected folder.

## Installation

1. Clone the repository:
   ```sh
   git clone <repository-url>
   cd srt-term-converter
   ```

2. Python 3.11 or later is required.

3. Install dependencies using Poetry:
   ```sh
   poetry install
   ```

## Usage

1. Launch the application:
   ```sh
   poetry run python src/main.py
   ```
   Alternatively, use the Visual Studio Code debugger (see `.vscode/launch.json` if available).

2. In the GUI:
   - **SRT File Input**: Click the "Browse" button to select an SRT file.
   - **Output Folder**: Select the folder where the processed file will be saved.
   - **Dictionary Editor**: Edit regex pairs in the format "pattern => replacement". These entries are saved in a CSV file (`replace_terms.csv`).
   - **Block Columns**: Maximum characters per line (default: 28).
   - **Block Rows**: Maximum lines per subtitle block (default: 2).
   - **Gap Threshold**: Fill gaps between subtitles if the interval is below this threshold in seconds (default: 0.5, set to 0 to disable).
   - **Execute Conversion**: Click the "Execute" button to start the conversion. Status messages and errors will be displayed in the message area.

## License

MIT