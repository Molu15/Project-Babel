# Project Babel - Phase 1: Core Script (MVP) Tasks

- [x] **Project Setup**
    - [x] Create `requirements.txt` (keyboard, mouse, pygetwindow, pywin32)
    - [x] Create directory structure (`src/`, `src/core`, `src/config`, `tests/`)
    - [x] Create `README.md` with setup instructions

- [x] **Mapping Configuration**
    - [x] Create `src/config/mappings/figma_to_photoshop.json`
    - [x] Implement German QWERTZ mapping rules

- [x] **Core Components Implementation**
    - [x] `observer.py`: Implement `InputObserver` using `keyboard` hook
    - [x] `context.py`: Implement `ContextManager` using `pygetwindow` to detect "Adobe Photoshop"
    - [x] `translator.py`: Implement `TranslationEngine` to load JSON and translate keys
    - [x] `injector.py`: Implement `InjectionModule` using `keyboard.send`

- [x] **Integration**
    - [x] `main.py`: Assemble the pipeline
    - [x] Verify <50ms latency constraint

- [x] **Verification**
    - [x] Unit tests for translation logic
    - [ ] Manual verification with Notepad/Photoshop
