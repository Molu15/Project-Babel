# Project Babel

**Project Babel** is a Semantic Action Mapper that unifies your shortcuts across different design applications. It allows you to use your preferred muscle memory (e.g., "Figma Style" or "Photoshop Style") in any supported application by dynamically translating your inputs.

## Features

- **Semantic Actions**: Define *what* you want to do (e.g., "Duplicate", "Layer Up") rather than just remapping keys.
- **Context Awareness**: Automatically detects if you are using **Photoshop (Desktop/Web)** or **Figma (Desktop/Web)**.
- **Dynamic Profiles**:
  - **Figma -> Photoshop**: Use Figma shortcuts in Photoshop (and everywhere else).
  - **Photoshop -> Figma**: Use Photoshop shortcuts in Figma.
  - **Custom**: Mix and match your favorite shortcuts.
- **Browser Bridge**: A Chrome/Edge extension that allows Babel to detect context inside your web browser.

## Installation

### Prerequisites
- Python 3.7+
- Windows OS (Required for low-level hooks)

### Setup
1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Browser Extension Setup (Babel Bridge)

To enable context detection for web apps (like Figma in the browser), you must install the local bridge extension:

1.  Open Chrome, Edge, or Brave.
2.  Navigate to `chrome://extensions`.
3.  Enable **Developer Mode** (toggle in the top right).
4.  Click **Load Unpacked**.
5.  Select the `babel_bridge` folder inside this project directory.
6.  Ensure the "Babel Bridge" extension is enabled and the icon is visible.

## Usage

### Running the Application
Project Babel requires Administrator privileges to intercept and inject global keyboard events.

1.  Open your terminal as **Administrator**.
2.  Run the main script:
    ```bash
    python src/main.py
    ```
    *(Or allow the UAC prompt if it requests elevation automatically)*

### System Tray Controls
Babel runs in the background. Right-click the **Feather Icon** in your system tray to control it:

-   **Figma -> Photoshop**: Forces the system to expect Figma-style inputs.
-   **Photoshop -> Figma**: Forces the system to expect Photoshop-style inputs.
-   **Custom**: Activates your personal configuration.
-   **Edit Custom Config**: Opens a live editor to tweak your "Custom" profile settings.
    -   *Note: Saving changes here automatically switches you to the Custom profile.*

### Configuration
You can technically edit `src/config/semantic_config.json` manually, but it is recommended to use the Tray Icon's **Edit Custom Config** feature for safety.

### Supported Actions
The following semantic actions are currently supported and mapped:

| Action ID | Description |
| :--- | :--- |
| `duplicate` | Duplicate selected layer/object |
| `deselect` | Deselect current selection |
| `layer_up` | Move selected layer up in the stack |
| `layer_down` | Move selected layer down in the stack |
| `zoom` | Smart Zoom (Mouse Wheel integration) |
| `redo` | Redo last action |
| `undo` | Undo last action |
| `group` | Group selected layers |
| `ungroup` | Ungroup selected layers |
