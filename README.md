# Reimbursement Claims — Multi-Agent PoC

A standalone, offline-first prototype for the reimbursement business case. The
editable Python source, Jupyter notebook, Streamlit interface, architecture
diagram, and evaluation examples are all in this folder.

## What the PoC demonstrates

- Digital intake of **synthetic, already-extracted** claim information.
- Separate agents for document completeness, plan coverage, and inconsistency
  signals.
- Deterministic routing to approval, rejection, a request for more information,
  or human review.
- In-memory case status lookup for customer support.
- Local structured logs and bounded workflow metrics.
- A Streamlit interface and a Jupyter notebook using the same editable modules.
- A small labeled evaluation set with decision agreement, approval precision,
  eligible-approval recall/F1, a confusion matrix, and operational routing rates.
- An optional OpenAI-compatible LLM adapter for rewriting an explanation. The
  LLM never determines coverage, fraud, or claim approval.

This is a workflow prototype, not an OCR/document-upload system or production
claims engine. A risk signal means "review this case", not "fraud detected".
All plans, people, policies, and claims are fictional.

## Run the Streamlit app

Python 3.12 is recommended. From this directory:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[app,notebook,dev]"
if [ ! -f .env ]; then cp .env.example .env; fi
streamlit run streamlit_app.py
```

Streamlit opens at http://localhost:8501. The `.env` file is local and ignored by
Git; the provided `.env.example` is a template. The app does not make an LLM
request unless you explicitly click **Generate LLM explanation (optional)**.
The conditional copy command creates `.env` only when absent and will not
overwrite credentials you have already configured.

On Windows PowerShell, activate the environment with
`.\.venv\Scripts\Activate.ps1`, install the same extras, then run:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
streamlit run streamlit_app.py
```

## Run the notebook

```bash
jupyter lab notebooks/reimbursement_demo.ipynb
```

In VS Code, open the notebook and select the Python 3.12 kernel from this
environment. All business logic remains visible and editable in `src/`; neither
Cursor nor Streamlit hides or replaces that code.

## Optional LLM explanation

Configure `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` in your local `.env` only
after reviewing provider approval and data-handling rules. For the OpenAI API,
`LLM_BASE_URL=https://api.openai.com/v1` is the base URL; do not append
`/chat/completions`. The adapter sends only a status and generic reason codes,
never documents, names, member IDs, or the claim payload. No external call is
made by the deterministic demo or evaluation. Never use real health, financial,
or personally identifiable information.

If a request fails, the interface displays the provider's HTTP status and a
sanitized error message (without the API key). For HTTP 400, check that the model
name is available to the configured provider/account and that the endpoint
supports the OpenAI Chat Completions API. The adapter deliberately omits optional
sampling parameters for better compatibility across models. Do not paste secrets
into issue reports or chat.

Use only credentials and providers approved for the machine and organization
where the PoC runs. Do not transfer personal API credentials to a work device.

## Evaluation

The **Evaluation** tab runs 12 hand-labeled synthetic workflow cases. It reports:

- **Exact decision agreement:** predicted route matches the authored label.
- **Approval precision:** correctly approved examples divided by all approvals.
- **Eligible-approval recall:** correctly approved examples divided by all
  examples labeled as eligible for approval.
- **Approval F1**, a confusion matrix, false approvals, and missed eligible
  approvals.
- **Straight-through approval, human review, and more-information rates** as
  illustrative business/workflow metrics.

These small deterministic examples are a smoke test of rule wiring, **not** a
statistical estimate of model performance, fraud recall, customer outcomes, or
production business value. A real pilot needs a representative, governance-
approved labeled dataset, an agreed labeling guide, held-out evaluation, subgroup
analysis, appeal/overturn tracking, analyst time, end-to-end cycle time, and
reliability/cost baselines before setting targets. Avoid optimizing approval rate
alone; monitor incorrect approvals, unnecessary denials, and harmful delays.
Download the scenario-level results from the Evaluation tab as CSV.

## Tests and lint

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

## Architecture

```text
Streamlit / Jupyter intake
          |
  case orchestrator -------- synthetic policy catalogue
    /       |       \
documents coverage risk signals
    \       |       /
      deterministic router ------> approve / reject / more info / human review
                  |
           case status / support
                  |
          redacted events + metrics
```

See the [editable Excalidraw diagram](presentations/architecture.excalidraw),
[business case and talk track](docs/business-case.md),
[evaluation approach](docs/evaluation.md), and
[architecture, controls, and limitations](docs/architecture.md).

## Portability and limitations

All source, notebook, tests, and sample data are ordinary files. Copy this folder
to an approved machine and recreate the Python environment; do not copy `.venv`
or personal API credentials. Case state is in memory and telemetry is local.
There is no durable storage, user authentication, real document parsing,
production availability, or regulatory certification. These are explicit
production gaps, not implied capabilities.
