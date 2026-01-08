# Product Definition Review: Project Babel (v2.1)

## Document Metadata

| Key | Value |
| :--- | :--- |
| **Project Name** | Project Babel |
| **Owner** | Vanessa Scherer |
| **Status** | Implementation Ready |

**Objective**: Unify fragmented design tool inputs via an extensible translation layer.

---

## 1. Executive Summary
Project Babel is a background utility designed to eliminate the friction caused by inconsistent shortcut schemes across professional design software. By acting as an intelligent middleware between the user's hardware input and the active application, Babel allows designers to use a single "native" set of muscle-memory controls (e.g., Figma style) across different environments like Adobe Photoshop and Illustrator.

## 2. Problem Statement
*   **The Muscle Memory Gap**: Professional designers frequently switch between tools like Figma, Photoshop, and Illustrator. Each application utilizes unique, often conflicting control schemes for identical functions.
*   **Inefficiency**: Muscle memory fails during context switching, leading to operational latency.
*   **Error Prone**: Users accidentally trigger unwanted actions (e.g., "Deselecting" instead of "Duplicating" when pressing `Ctrl + D`).

## 3. Core Functionality: The "Universal Translator"
Project Babel functions as a translation layer. It intercepts keystrokes, identifies the active window context, and translates the input into the target application's specific shortcut language before injecting it back into the system.

### 3.1 Mapping Rules (German/QWERTZ Layout)
The following mapping table defines the initial translation logic, specifically tailored for a Windows environment using a German (QWERTZ) keyboard layout.

**Legend**: `Strg` = `Ctrl`.

| Action | Input (Figma Style) | Output (Photoshop Target) | Notes |
| :--- | :--- | :--- | :--- |
| **Zoom** | `Strg + MouseWheel` | `Alt + MouseWheel` | |
| **Duplicate** | `Strg + D` | `Strg + J` | |
| **Deselect** | `Esc` | `Strg + D` | |
| **Layer Up** | `Strg + Ö` | `Strg + ]` | |
| **Layer Down** | `Strg + Ä` | `[` | |
| **Opacity** | `1 - 9` | `1 - 9` | No translation needed |
| **Pan** | `Space + Drag` | `Space + Drag` | No translation needed |
| **Redo** | `Strg + Shift + z` | `Strg + Shift + Z` | |
| **Undo** | `Strg + z` | `Strg + z` | |
| **Group** | `Strg + G` | `Strg + G` | No translation needed |
| **Ungroup** | `Strg + Shift + G` | `Strg + Shift + G` | No translation needed |

## 4. Scalable System Architecture
The architecture is designed as a Modular Event Pipeline. This decoupling ensures that adding new applications (like Illustrator) or new platforms (like a Chrome Extension) does not require rewriting the core logic.

### 4.1 Core Components

#### Input Observer (The "Ear")
*   **Function**: Listens for raw Hardware Events.
*   **Library**: `keyboard` (for global hooks) and `mouse` (for scrolling/clicking).
*   **Extensibility**: This module is agnostic to the source. Currently, it listens to OS hooks, but it is structured to accept input messages from a future Chrome Extension via a local server or Native Messaging API.

#### Context Manager (The "Eyes")
*   **Function**: Determines where the user is working.
*   **Library**: `pygetwindow` (or `pywin32`).
*   **Logic**: Polls the active window title.
*   **Scalability**: Implements a ContextStrategy interface.
    *   *Strategy A (Desktop)*: Detects "Adobe Photoshop".
    *   *Strategy B (Web)*: Detects "Google Chrome". If Chrome is active, it queries the window title for "Figma".

#### Translation Engine (The "Brain")
*   **Function**: Pure Python logic that holds the Mapping Dictionary (JSON).
*   **Flow**: Input + Context $\rightarrow$ Lookup Rule $\rightarrow$ Output Command.
*   **Configurability**: Rules are stored in external JSON files, allowing users to switch profiles (e.g., "Figma to Photoshop" vs. "Figma to Illustrator") without code changes.

#### Injection Module (The "Hand")
*   **Function**: Executes the translated command.
*   **Library**: `keyboard.send`.
*   **Latency Constraint**: Must execute within <50ms to prevent input lag.

### 4.2 Chrome Extension Integration Strategy
To support the "Chrome supported" requirement effectively in future iterations:
*   **Challenge**: Desktop scripts often cannot distinguish tabs within a browser, only the browser window itself.
*   **Solution**: The Architecture includes a Local WebSocket / Native Messaging Host.
    1.  A lightweight Chrome Extension will inject a content script into Figma web tabs.
    2.  This extension sends a "Focus Active" signal to the Project Babel Python backend.
    3.  The Python backend then switches its Context to `WEB_FIGMA`, applying the relevant translation rules to the browser window.

## 5. Implementation Roadmap

### Phase 1: The Core Script (MVP)
*   **Goal**: Stand-alone Python script functioning on Windows.
*   **Focus**: Fixed "Figma to Photoshop" mapping.
*   **Hardware**: QWERTZ Keyboard optimization.

### Phase 2: Dynamic Context
*   **Goal**: Auto-switching between Photoshop and Illustrator contexts.
*   **Feature**: Introduction of the JSON-based Mapping Dictionary for easy rule additions.

### Phase 3: The Web Bridge
*   **Goal**: Chrome Extension support.
*   **Feature**: Browser extension that communicates tab focus to the Python backend.
