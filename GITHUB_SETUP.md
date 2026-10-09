# 🌐 GitHub Repository Configuration & Publication Guide

When creating your GitHub repository for **Free Media Engine (FME)**, use the following verified metadata to ensure high discoverability, professional branding, and SEO ranking on GitHub Explore and search engines.

---

## 📋 1. Repository Details & Metadata

In your GitHub repository home page, click the ⚙️ gear icon next to **"About"** on the right sidebar and enter:

### **Description / Tagline**
```text
Self-hosted, unattended REST API & CLI for Google Flow. Generate Gemini Omni 1.1 Flash & Veo videos and 2K images on your own VPS with zero bot blocks.
```

### **Website**
Point this to your repository's README or docs index:
```text
https://github.com/AbdulWaheedorg/Free-Media-Engine#readme
```
*(Or your custom domain / portfolio if you choose to publish one).*

### **Topics (Search Tags)**
Paste each of the following tags into the GitHub Topics input:
```text
google-flow
gemini-omni-flash
veo
ai-video-generator
text-to-video
image-to-video
text-to-image
rest-api
fastapi
docker
self-hosted
automation
unofficial-api
reverse-proxy
caddy
```

---

## 📁 2. Initial Git Push Instructions

Run the following commands inside this `public/` directory (or after moving its contents to your clean repo root):

```bash
# Initialize clean git repository
git init -b main

# Stage all sanitized files
git add .

# Create initial release commit
git commit -m "feat: initial public release of Free Media Engine (v1.0.0)"

# Link to your remote GitHub repository
git remote add origin https://github.com/AbdulWaheedorg/Free-Media-Engine.git

# Push to GitHub
git push -u origin main
```

---

## 🛡️ 3. Recommended Repository Settings

1. **Discussions**: Enable **Discussions** under `Settings` -> `General` -> `Features` to give users a community forum for prompt engineering tips and setup questions.
2. **Issues**: Ensure **Issues** is enabled. Standard bug report and feature request templates are included in `.github/ISSUE_TEMPLATE/`.
3. **Releases**: Create a new Release tagged `v1.0.0` titled `v1.0.0 - Initial Production Release`.
