"""Streamlit interface for the synthetic reimbursement triage PoC."""

import csv
import io
import os
from datetime import date
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv

from reimbursement_poc.domain import CaseRecord, ClaimRequest
from reimbursement_poc.evaluation import (
    SYNTHETIC_POLICIES,
    evaluate_synthetic_cases,
)
from reimbursement_poc.llm import LLMRequestError, explain_decision
from reimbursement_poc.orchestrator import CaseOrchestrator

load_dotenv(override=False)

st.set_page_config(page_title="Claims triage PoC", page_icon="🧾", layout="wide")
st.title("Reimbursement claims — multi-agent PoC")
st.warning(
    "Local demonstration with synthetic data. Do not enter real personal, "
    "medical, or financial information. This is not a production claims system."
)

if "case_orchestrator" not in st.session_state:
    st.session_state.case_orchestrator = CaseOrchestrator(SYNTHETIC_POLICIES)
if "case_records" not in st.session_state:
    st.session_state.case_records = {}
if "case_id" not in st.session_state:
    st.session_state.case_id = f"DEMO-{uuid4().hex[:8].upper()}"

intake_tab, evaluation_tab, support_tab = st.tabs(
    ["New claim", "Evaluation", "Track a claim"]
)

with intake_tab:
    st.subheader("Simulated digital intake")
    if st.button("Generate a new demo ID"):
        st.session_state.case_id = f"DEMO-{uuid4().hex[:8].upper()}"

    with st.form("claim_intake"):
        case_id = st.text_input("Synthetic case ID", key="case_id")
        plan_id = st.selectbox("Synthetic plan", list(SYNTHETIC_POLICIES))
        procedure = st.selectbox(
            "Procedure",
            sorted(
                {
                    procedure_code
                    for policy in SYNTHETIC_POLICIES.values()
                    for procedure_code in policy.get("covered_procedures", [])
                }
            ),
        )
        amount = st.number_input(
            "Invoice amount (synthetic units)",
            min_value=0.01,
            value=400.0,
            step=25.0,
        )
        invoice_id = st.text_input(
            "Synthetic invoice ID",
            value=f"INV-{case_id}",
            help="Reuse an ID in another claim to simulate a duplicate invoice.",
        )
        service_date = st.date_input("Procedure date", value=date(2026, 9, 1))
        invoice_submitted = st.checkbox("Invoice submitted", value=True)
        request_submitted = st.checkbox("Medical request submitted", value=True)
        physician_present = st.checkbox("Physician ID is present", value=True)
        dates_match = st.checkbox("Document dates match", value=True)
        invoice_procedure_matches = st.checkbox(
            "Invoice procedure matches the medical request", value=True
        )
        submitted = st.form_submit_button("Analyze claim")

    if submitted:
        medical_request: dict[str, object] = {}
        if request_submitted:
            medical_request = {
                "procedure_code": procedure,
                "service_date": (
                    service_date.isoformat()
                    if dates_match
                    else date(2026, 9, 2).isoformat()
                ),
            }
            if physician_present:
                medical_request["physician_id"] = "DOCTOR-SYNTHETIC"

        documents: dict[str, dict[str, object]] = {}
        if invoice_submitted:
            documents["invoice"] = {
                "invoice_id": invoice_id,
                "amount": amount,
                "provider": "SYNTHETIC CLINIC",
                "service_date": service_date.isoformat(),
                "procedure_code": (
                    procedure if invoice_procedure_matches else "OTHER-PROCEDURE"
                ),
            }
        if request_submitted:
            documents["medical_request"] = medical_request

        request = ClaimRequest(
            case_id=case_id,
            member_id=f"MEMBER-{case_id}",
            plan_id=plan_id,
            documents=documents,
        )
        try:
            record = st.session_state.case_orchestrator.submit(request)
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state.case_records[case_id] = record
            st.success(f"Claim submitted: {record.status.value}")

    records: dict[str, CaseRecord] = st.session_state.case_records
    if records:
        latest_case_id = next(reversed(records))
        latest_record = records[latest_case_id]
        st.markdown(f"**Latest claim:** `{latest_case_id}`")
        st.write(f"**Decision:** {latest_record.status.value}")
        st.write(f"**Reason codes:** {', '.join(latest_record.reasons)}")
        st.write(
            "**Customer update:** "
            + st.session_state.case_orchestrator.customer_update(latest_case_id)
        )
        if latest_record.approved_amount is not None:
            st.metric("Eligible amount (synthetic)", latest_record.approved_amount)

        if st.button("Generate LLM explanation (optional)", key="explain_latest"):
            if not all(os.environ.get(name) for name in ("LLM_API_KEY", "LLM_MODEL")):
                st.error("Set LLM_API_KEY and LLM_MODEL in .env first.")
            else:
                with st.spinner("Sending only the status and generic reason codes..."):
                    try:
                        explanation = explain_decision(
                            latest_record.status.value, latest_record.reasons
                        )
                    except LLMRequestError as error:
                        st.error(f"Could not generate explanation: {error}")
                    else:
                        st.info(explanation)
        st.caption(
            "The optional LLM only rewrites an explanation from the status and "
            "generic reason codes; it never decides coverage or approval."
        )

with evaluation_tab:
    st.subheader("Evaluation on labeled synthetic examples")
    st.info(
        "Expected labels were authored manually for these deterministic examples. "
        "Recall measures recovery of the APPROVED class in this small set; it is "
        "not fraud recall or evidence of real-world performance."
    )
    report = evaluate_synthetic_cases()
    metrics = report["metrics"]
    metric_columns = st.columns(4)
    metric_columns[0].metric(
        "Exact decision agreement",
        f"{metrics['exact_decision_agreement']:.0%}",
        help="Predicted decisions matching the manual labels.",
    )
    metric_columns[1].metric(
        "Eligible approval recall",
        f"{metrics['eligible_approval_recall']:.0%}",
        help="Correct approvals / all examples labeled as eligible for approval.",
    )
    metric_columns[2].metric(
        "Approval precision",
        f"{metrics['approval_precision']:.0%}",
        help="Correct approvals / all rule-approved examples.",
    )
    metric_columns[3].metric("Approval F1", f"{metrics['eligible_approval_f1']:.0%}")

    operation_columns = st.columns(4)
    operation_columns[0].metric(
        "Straight-through approval",
        f"{metrics['straight_through_approval_rate']:.0%}",
    )
    operation_columns[1].metric("Human review", f"{metrics['human_review_rate']:.0%}")
    operation_columns[2].metric(
        "More information requested", f"{metrics['needs_information_rate']:.0%}"
    )
    operation_columns[3].metric("Evaluation cases", metrics["evaluation_cases"])

    st.markdown("#### Scenarios, predictions, and expected labels")
    rows: list[dict[str, object]] = report["rows"]
    st.dataframe(rows, width="stretch", hide_index=True)

    st.markdown("#### Multiclass confusion matrix")
    matrix: dict[str, dict[str, int]] = report["confusion_matrix"]
    matrix_rows = [
        {"Expected": expected, **predictions}
        for expected, predictions in matrix.items()
    ]
    st.dataframe(matrix_rows, width="stretch", hide_index=True)
    st.caption(
        f"False approvals: {metrics['false_approval_count']} · "
        f"Eligible approvals not recovered: "
        f"{metrics['missed_eligible_approval_count']}"
    )

    csv_buffer = io.StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    st.download_button(
        "Download synthetic evaluation results as CSV",
        csv_buffer.getvalue(),
        file_name="reimbursement-poc-evaluation.csv",
        mime="text/csv",
    )

with support_tab:
    st.subheader("Claim status and support")
    records: dict[str, CaseRecord] = st.session_state.case_records
    if not records:
        st.caption("Submit a synthetic claim to enable status tracking.")
    else:
        selected_case = st.selectbox("Claim", list(records))
        record = records[selected_case]
        st.write(f"**Status:** {record.status.value}")
        st.write(st.session_state.case_orchestrator.customer_update(selected_case))

st.divider()
st.caption(
    "Local PoC: session-only state, synthetic policies, no OCR, authentication, "
    "durable storage, or production SLOs."
)
