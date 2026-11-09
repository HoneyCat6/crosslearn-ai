# CrossLearn AI — seeded demo release

To run the populated showcase locally, use **`run-m4.cmd`**, open **http://127.0.0.1:8000/** and use credentials from `api/.demo-access.json`. Select the **M4 showcase** class for populated histories, recommendations and evaluation reports. See [M4 walkthrough and remaining limits](docs/M4.md). Browser QA and full M3 research readiness remain outstanding.

**M2 is also available with FastAPI + PostgreSQL.** Use **`run-m2.cmd`** for the regular seeded demo, then open **http://127.0.0.1:8000/**. Both scripts generate credentials locally in `api/.demo-access.json`.

See **[M2 setup, walkthrough and verification](docs/M2.md)** for the connected teacher/pupil workflow, model configuration and known limitations. The original standalone M1 instructions are retained below.

## Run after cloning

The repository contains source code and configuration examples, but not virtual environments, credentials or PostgreSQL data. Each contributor must install the prerequisites and create their own local configuration.

The commands below are for Windows PowerShell. Run them from the cloned `crosslearn-ai` directory.

### Option 1: Run the frontend-only M1 demo

This option needs only Node.js and does not need Python, PostgreSQL or environment variables.

1. Install [Node.js 24 or newer](https://nodejs.org/).
2. Start the frontend:

   ```powershell
   cd web
   npm.cmd run dev
   ```

3. Open **http://127.0.0.1:5173/**.

The frontend uses the synthetic local-browser demo. `npm.cmd run build` creates the deployable static files in `web/dist`.

### Option 2: Run the full M2/M4 demo

The backend requires Python 3.12 or newer and PostgreSQL.

1. Install:
   - [Python 3.12 or newer](https://www.python.org/downloads/)
   - [PostgreSQL](https://www.postgresql.org/download/windows/)
   - Node.js 24 or newer if you also want to work on the frontend
2. Create a PostgreSQL database named `crosslearn` and a dedicated local user. Do not use a superuser for the application.
3. Create a virtual environment and install the backend dependencies:

   ```powershell
   python -m venv api/.venv
   api/.venv/Scripts/python.exe -m pip install -r api/requirements.txt
   ```

   For a reproducible installation, use `api/requirements.lock.txt` instead.
4. Create `api/.env` from `api/.env.example` and set `DATABASE_URL` to the connection string for the database created above. Keep `MODEL_PROVIDER=none` unless an approved, server-only model is deliberately configured.
5. Apply migrations and seed synthetic accounts and content:

   ```powershell
   api/.venv/Scripts/python.exe -m alembic upgrade head
   api/.venv/Scripts/python.exe -m app.seed
   ```

6. Start the application:

   ```powershell
   .\run-m2.cmd
   ```

   Or use `.\run-m4.cmd` for the populated M4 showcase data.
7. Open **http://127.0.0.1:8000/**. Read the generated usernames and passwords from `api/.demo-access.json`.

If a startup check fails, confirm that PostgreSQL is running, `api/.env` points to the correct database, and port 8000 is available. See [api/SETUP.md](api/SETUP.md) and [docs/M2.md](docs/M2.md) for detailed setup and verification.

### Run the tests

Frontend tests:

```powershell
cd web
npm.cmd test
npm.cmd run build
```

Backend tests:

```powershell
cd ..\api
.venv\Scripts\python.exe -m pytest -q
```

Backend tests use PostgreSQL and require a configured test-capable database user. They create and remove isolated test schemas; do not run them against a production database.

### Keep local files private

Never commit `.env`, `api/.demo-access.json`, `api/.venv`, database backups, passwords or API keys. These paths are excluded by the repository's ignore files. The included accounts and data are synthetic demo data only.

## Original M1 demo

A complete synthetic-data Science vocabulary demo, built from `../Agentic/CrossLearn_AI_Build_Specification.md`. It implements M1 only. No accounts, real pupil data, database or external AI calls are used.

## Run on Windows

Requires Node.js 24 or newer (the supplied environment has 24.14.1). No package download is necessary.

```powershell
cd P:\innovation\FOI2026\Agentic\crosslearn-ai\web
npm.cmd run dev
```

Open **http://127.0.0.1:5173/**. Stop with **Ctrl+C** in that terminal. After editing source, stop and run the command again to rebuild.

```powershell
npm.cmd test
npm.cmd run build
npm.cmd run preview
```

`web/dist` contains the deployable static app. Serve it over HTTP; do not double-click index.html, because it uses JavaScript modules. A host can serve `dist/index.html` directly without a backend or secrets.

`crosslearn-demo-static.zip` packages those static files. A private Site was registered, with its identity retained in `web/.openai/hosting.json`, but publication could not complete: this environment could not connect to the source Git host on port 443. No hosted demo URL is verified. Reuse the recorded Site ID on a later publish attempt.

## Demo walkthrough

1. Welcome → **Let’s explore**. Use the accessibility settings for larger text or high contrast.
2. Crossword: 1 Down **ROOT**, 2 Across **MOSS**, 3 Across **STEM**. Intersections share letters. Click a clue to select a word; use arrow keys and Backspace. A letter reveal is available. Wrong checks give no meaning hints.
3. Select a rotation A–F before checking the completed puzzle. Each three rotations assigns every format to every concept; D–F also shift concept exposure order. This is a demonstration rotation, not a complete balanced research protocol.
4. Answer six baseline questions. The app records selections without correctness feedback or lesson content.
5. Explore three lessons: one text, one browser speech explanation, one labeled SVG diagram. Audio has Replay and an accessible transcript; use is logged. Audio depends on available browser/device voices.
6. Answer six distinct post-test questions. All assessment items have the same optional read-aloud accommodation.
7. View before/after counts; open answer review for correct answers and explanations.
8. Open **Teacher demo** for deterministic per-concept scores, percentage point changes, insufficient-evidence interpretation and a rule-based next-step suggestion. Expand the session log or export the synthetic summary CSV.
9. **Play again** clears this session and selects the next rotation. Refresh otherwise restores the current synthetic session in local browser storage.

## Architecture and implementation choice

- `web/src/content.ts`: versioned English sample concepts, explanations and 12 keyed assessment items. Pending teacher validation; not falsely marked approved.
- `web/src/engine.ts`: crossword validation, answer-key scoring, modality rotations, summaries and saved-state validation.
- `web/src/app.js`: native DOM UI, keyboard/touch handlers, local persistence, browser speech, SVG diagrams and CSV export.
- `web/src/styles.css`: responsive styles, focus indicators, reduced-motion handling, high contrast and larger-text controls. Uses device fonts; no external asset requests.
- `web/scripts/build.mjs`: Node’s TypeScript stripping creates static modules. This Node API is experimental; no full TypeScript type checker is bundled.
- `web/scripts/serve.mjs`: small loopback-only development server, with path traversal checks.

The spec recommends React + TypeScript + Vite. Registry access was denied (`EACCES`) in the execution environment, so M1 uses maintained native browser APIs and Node’s built-in tooling instead of unavailable dependencies. Content and scoring retain TypeScript source. React migration can follow when dependency installation is available; the current demo runs without installation.

Hash routes are deliberately not implemented: the complete staged flow lives on one page with saved progress. Malay navigation/welcome is a clearly marked preview; the assessment content remains English.

## Validation

`npm.cmd test`: **7 tests passed**, covering valid intersections, bounds, unique/equivalent-intent items, deterministic/ceiling/negative scoring, rotation coverage, corrupt-state rejection, a complete event-driven journey and refresh recovery.

The journey test executes real UI event handlers with a small DOM adapter. It does **not** test browser rendering, actual speech, screen readers or viewport overflow. Build and JavaScript syntax checks passed, and the local HTTP endpoint returned 200. Browser automation was unavailable, so visual QA and the following manual checks remain:

- At 320/360 px: verify no horizontal page scroll, readable questions, accessible controls and crossword touch input.
- Solve by keyboard only, including crossings, arrow keys, Backspace, visible focus and all stage transitions.
- Confirm audio/replay works on the target device; use accessible text if no voice is installed.
- Test a screen reader, reduced motion, high contrast, and 200% browser zoom.

## Limits and next milestone

M1 is a technical demonstration, not a validated assessment or research-ready PWA. Two items produce coarse 0/50/100% concept scores. Baseline follows word discovery. No learning-style diagnosis, causal effectiveness claim, delayed retention, longitudinal learner profile, secure teacher login, offline reload/sync or research authorization is implemented. Only the current demo session is stored; CSV exports are synthetic summaries.

Next is **M2**: authenticated FastAPI backend + PostgreSQL, school-scoped access, approved/versioned content, pseudonymous records, consent and deletion controls. Backend scoring must recalculate from answer keys. A server-only model adapter may read minimal authorized evidence, call allowlisted tools and draft schema-validated recommendations for teacher review, with deterministic fallback on failures. API/service keys must never enter browser code. Ethics, permission, privacy review and security audit are required before real child data.
