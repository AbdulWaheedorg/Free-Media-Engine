# Contributing to Free Media Engine

Thank you for your interest in contributing to **Free Media Engine (FME)**! We welcome bug fixes, documentation improvements, new generation mode support, and feature enhancements.

---

## 🛠️ Development Workflow

1. **Fork the Repository** on GitHub: Go to [https://github.com/AbdulWaheedorg/Free-Media-Engine](https://github.com/AbdulWaheedorg/Free-Media-Engine) and click **Fork**.
2. **Clone your repository locally**:
   ```bash
   # Clone the repository:
   git clone https://github.com/AbdulWaheedorg/Free-Media-Engine.git
   cd Free-Media-Engine
   ```
3. **Set up a Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
4. **Create a Feature Branch**:
   ```bash
   git checkout -b feature/my-new-feature
   ```

---

## 📜 Code Guidelines

- **Strict DRY Principles**: Avoid duplicate logic across the daemon, CLI, and database layers.
- **Pydantic Schemas**: All API inputs and outputs must be strongly typed in `fme_engine/models/schemas.py`.
- **Formatting**: Run code formatters before submitting changes:
  ```bash
  black fme_engine
  flake8 fme_engine
  ```
- **Documentation**: If adding a new mode or endpoint, update the corresponding documentation files in `docs/api/` and `docs/development/`.

---

## 🧪 Testing Your Changes

Ensure your local daemon boots and API endpoints respond correctly:
```bash
uvicorn fme_engine.api.app:app --host 127.0.0.1 --port 8120 --reload
```
Test that `/api/v1/health` returns `200 OK`.

---

## 📥 Submitting Pull Requests

1. Commit your changes with clear, descriptive commit messages:
   ```bash
   git commit -m "feat(api): add support for 4k video upscaling mode"
   ```
2. Push your branch to GitHub:
   ```bash
   git push origin feature/my-new-feature
   ```
3. Open a Pull Request against the `main` branch with a clear description of the problem solved.
