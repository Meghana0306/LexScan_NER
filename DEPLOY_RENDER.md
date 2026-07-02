# Deploy LexScan

This project should be deployed as one web service.

- Frontend: already served by `app.py`
- Backend: already served by `app.py`
- Public URL: comes from the hosting platform

You do not need a separate frontend deployment for the current app.

## Before You Deploy

1. Push the repo to GitHub.
2. Make sure these files are committed:
   - `app.py`
   - `.python-version`
   - `render.yaml`
   - `.gitattributes`
   - the `LexScan/` folder
   - the `models/general_best_model/` folder
   - the `models/legal_best_model/` folder
   - the `models/medical_best_model/` folder
3. Large model files must be pushed with Git LFS.

## GitHub First

Run these locally in the repo:

```powershell
git lfs install
git lfs track "models/general_best_model/model.safetensors"
git lfs track "models/legal_best_model/model.safetensors"
git lfs track "models/medical_best_model/model.safetensors"
git add .gitattributes
git add app.py render.yaml DEPLOY_RENDER.md .gitignore
git add models/general_best_model models/legal_best_model models/medical_best_model
git status --short
git commit -m "Prepare LexScan for deployment"
git push origin main
```

## Render Steps

1. Open `https://dashboard.render.com/`
2. Click `New`
3. Click `Blueprint`
4. Connect the GitHub repo `Meghana0306/LexScan_NER`
5. Select the branch you pushed
6. Render will detect `render.yaml`
7. Click `Apply`

## Render Values

The repo already contains the main deployment settings in `render.yaml`.
It also includes `.python-version` so Render uses Python 3.11 instead of an unsupported newer version.

Fill these secrets in Render when asked:

- `GROQ_API_KEY` = your real Groq key
- `GEMINI_API_KEY` = your real Gemini key if you use Gemini features

## If You Deploy Using Render's Web Service Form Instead

Use these values:

- Service type: `Web Service`
- Runtime: `Python`
- Name: `lexscan`
- Branch: `main`
- Root directory: leave blank if the repo root is the app
- Build command:

```bash
pip install --upgrade pip && pip install -r requirements-docker.txt --extra-index-url https://download.pytorch.org/whl/cpu && python -m spacy download en_core_web_sm --no-deps || true
```

- Start command:

```bash
python app.py
```

- Health check path:

```text
/
```

Add these environment variables:

- `APP_HOST` = `0.0.0.0`
- `NER_SKIP_BOOTSTRAP` = `1`
- `PYTHONUNBUFFERED` = `1`
- `GROQ_API_KEY` = your real Groq key
- `GEMINI_API_KEY` = your real Gemini key if needed

Do not set `APP_PORT` on Render unless you have a special reason. The app now reads Render's `PORT` automatically.

## Final Link

After deployment, Render will give you a public link like:

```text
https://lexscan.onrender.com
```

That is the shareable link you can send to other people.
