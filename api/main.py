"""FastAPI adapter for the Portfolio Analyzer."""

from __future__ import annotations

import json
import hashlib
import os
import secrets
import shutil
import uuid
from io import BytesIO
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from market_etl.config import Settings
from market_etl.database import build_engine
from market_etl.models import Base, ClientOnboarding, PortfolioRun, ReportConfiguration, UserAccount
from portfolio_service import PortfolioAnalysisService
from api.auth import AuthConfigurationError, Principal, hash_password, issue_token, principal_dependency, require_admin, verify_password

from api.data_center import router as data_center_router

ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "runtime" / "analyses"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
ALLOWED_SUFFIXES = {".xlsx", ".xls"}
CLIENT_ENGINE = build_engine(Settings.from_env().database_url)
Base.metadata.create_all(CLIENT_ENGINE)
get_principal = principal_dependency(CLIENT_ENGINE)


def get_admin(principal: Principal = Depends(get_principal)) -> Principal:
    return require_admin(principal)

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()] or DEFAULT_ALLOWED_ORIGINS

app = FastAPI(title="Portfolio Analyzer API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(data_center_router, dependencies=[Depends(get_admin)])


class AnalysisRequest(BaseModel):
    upload_id: str


class ClientSubmission(BaseModel):
    data: dict


class FavoriteRequest(BaseModel):
    favorite: bool


class ClientExportRequest(BaseModel):
    tokens: list[str]


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        email = value.strip().lower()
        if email.count("@") != 1 or "." not in email.rsplit("@", 1)[1]:
            raise ValueError("Enter a valid email address")
        return email


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str


class AdminClientRequest(RegisterRequest):
    pass


class CompareRequest(BaseModel):
    older_id: str
    newer_id: str


REPORT_SECTIONS = ("holdings", "sector", "industry", "market_cap", "top_holdings", "benchmarks", "insights", "performance", "risk", "style")
DEFAULT_REPORT_CONFIGURATION = {
    "title": "Portfolio Analysis Report",
    "subtitle": "A complete view of portfolio structure, risk, style, and performance.",
    "sections": {key: True for key in REPORT_SECTIONS},
}


class ReportConfigurationRequest(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    subtitle: str = Field(max_length=500)
    sections: dict[str, bool]


def _report_configuration(owner_id: str) -> dict:
    with Session(CLIENT_ENGINE) as session:
        global_config = session.get(ReportConfiguration, "__global__")
        client_config = session.get(ReportConfiguration, owner_id)
        source = client_config or global_config
        if not source:
            return {**DEFAULT_REPORT_CONFIGURATION, "scope": "default", "owner_id": owner_id}
        return {"title": source.title, "subtitle": source.subtitle, "sections": {**DEFAULT_REPORT_CONFIGURATION["sections"], **(source.sections or {})}, "scope": "client" if client_config else "global", "owner_id": owner_id}


def _configuration_payload(record: ReportConfiguration | None, owner_id: str) -> dict:
    if not record:
        return {**DEFAULT_REPORT_CONFIGURATION, "owner_id": owner_id, "exists": False}
    return {"owner_id": owner_id, "title": record.title, "subtitle": record.subtitle, "sections": {**DEFAULT_REPORT_CONFIGURATION["sections"], **(record.sections or {})}, "exists": True, "updated_at": record.updated_at}


def _user_payload(user: UserAccount) -> dict:
    return {
        "id": user.id, "email": user.email, "full_name": user.full_name,
        "role": user.role, "is_active": user.is_active, "created_at": user.created_at,
        "last_login_at": user.last_login_at,
    }


def _session_payload(principal: Principal, token: str | None = None) -> dict:
    result = {
        "user": _user_payload(principal.user),
        "workspace_owner": _user_payload(principal.owner),
        "is_impersonating": principal.is_impersonating,
    }
    if token:
        result.update({"access_token": token, "token_type": "bearer"})
    return result


@app.post("/api/auth/register", status_code=201)
def register(request: RegisterRequest) -> dict:
    email = str(request.email).strip().lower()
    with Session(CLIENT_ENGINE) as session:
        if session.scalar(select(UserAccount).where(UserAccount.email == email)):
            raise HTTPException(status_code=409, detail="An account with this email already exists")
        try:
            encoded = hash_password(request.password)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        user = UserAccount(id=str(uuid.uuid4()), email=email, full_name=request.full_name.strip(), password_hash=encoded, role="client")
        session.add(user)
        try:
            token = issue_token(user)
        except AuthConfigurationError as exc:
            session.rollback()
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        session.commit()
        session.refresh(user)
        return _session_payload(Principal(user, user), token)


@app.post("/api/auth/login")
def login(request: LoginRequest) -> dict:
    email = str(request.email).strip().lower()
    with Session(CLIENT_ENGINE) as session:
        user = session.scalar(select(UserAccount).where(UserAccount.email == email))
        if not user or not user.is_active or not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Email or password is incorrect")
        try:
            token = issue_token(user)
        except AuthConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        user.last_login_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(user)
        return _session_payload(Principal(user, user), token)


@app.get("/api/auth/me")
def current_session(principal: Principal = Depends(get_principal)) -> dict:
    return _session_payload(principal)


@app.post("/api/auth/stop-impersonating")
def stop_impersonating(principal: Principal = Depends(get_admin)) -> dict:
    return _session_payload(Principal(principal.user, principal.user), issue_token(principal.user))


@app.post("/api/admin/clients/{client_id}/impersonate")
def impersonate_client(client_id: str, principal: Principal = Depends(get_admin)) -> dict:
    with Session(CLIENT_ENGINE) as session:
        client = session.get(UserAccount, client_id)
        if not client or client.role != "client" or not client.is_active:
            raise HTTPException(status_code=404, detail="Client account not found")
        session.expunge(client)
        return _session_payload(Principal(principal.user, client, True), issue_token(principal.user, acting_as=client.id))


@app.post("/api/admin/accounts", status_code=201)
def create_client_account(request: AdminClientRequest, principal: Principal = Depends(get_admin)) -> dict:
    email = str(request.email).strip().lower()
    with Session(CLIENT_ENGINE) as session:
        if session.scalar(select(UserAccount).where(UserAccount.email == email)):
            raise HTTPException(status_code=409, detail="An account with this email already exists")
        user = UserAccount(id=str(uuid.uuid4()), email=email, full_name=request.full_name.strip(), password_hash=hash_password(request.password), role="client")
        session.add(user)
        session.commit()
        session.refresh(user)
        return _user_payload(user)


@app.get("/api/admin/accounts")
def list_client_accounts(principal: Principal = Depends(get_admin)) -> dict:
    with Session(CLIENT_ENGINE) as session:
        users = session.scalars(select(UserAccount).where(UserAccount.role == "client").order_by(UserAccount.created_at.desc())).all()
        rows = []
        for user in users:
            runs = session.scalars(select(PortfolioRun).where(PortfolioRun.owner_id == user.id).order_by(PortfolioRun.created_at.desc())).all()
            payload = _user_payload(user)
            payload.update({"portfolio_count": len(runs), "latest_portfolio": runs[0].summary if runs else None})
            rows.append(payload)
        return {"clients": rows}


@app.get("/api/report-configuration")
def effective_report_configuration(principal: Principal = Depends(get_principal)) -> dict:
    return _report_configuration(principal.owner.id)


@app.get("/api/admin/report-configurations/{owner_id}")
def get_report_configuration(owner_id: str, principal: Principal = Depends(get_admin)) -> dict:
    target = "__global__" if owner_id == "global" else owner_id
    with Session(CLIENT_ENGINE) as session:
        if target != "__global__":
            client = session.get(UserAccount, target)
            if not client or client.role != "client":
                raise HTTPException(status_code=404, detail="Client account not found")
        return _configuration_payload(session.get(ReportConfiguration, target), target)


@app.put("/api/admin/report-configurations/{owner_id}")
def save_report_configuration(owner_id: str, request: ReportConfigurationRequest, principal: Principal = Depends(get_admin)) -> dict:
    target = "__global__" if owner_id == "global" else owner_id
    sections = {key: bool(request.sections.get(key, True)) for key in REPORT_SECTIONS}
    with Session(CLIENT_ENGINE) as session:
        if target != "__global__":
            client = session.get(UserAccount, target)
            if not client or client.role != "client":
                raise HTTPException(status_code=404, detail="Client account not found")
        record = session.get(ReportConfiguration, target)
        if record:
            record.title, record.subtitle, record.sections = request.title.strip(), request.subtitle.strip(), sections
        else:
            record = ReportConfiguration(owner_id=target, title=request.title.strip(), subtitle=request.subtitle.strip(), sections=sections)
            session.add(record)
        session.commit()
        session.refresh(record)
        return _configuration_payload(record, target)


@app.delete("/api/admin/report-configurations/{owner_id}")
def delete_report_configuration(owner_id: str, principal: Principal = Depends(get_admin)) -> dict:
    if owner_id == "global":
        raise HTTPException(status_code=422, detail="The global template cannot be reset; edit it instead")
    with Session(CLIENT_ENGINE) as session:
        record = session.get(ReportConfiguration, owner_id)
        if record:
            session.delete(record)
            session.commit()
    return {"status": "reset", "effective": _report_configuration(owner_id)}


def _run_dir(run_id: str) -> Path:
    if not run_id or any(character not in "0123456789abcdef-" for character in run_id):
        raise HTTPException(status_code=400, detail="Invalid analysis identifier")
    return RUNS_DIR / run_id


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise HTTPException(status_code=404, detail="Analysis not found")
    return json.loads(path.read_text(encoding="utf-8"))


def _client_payload(record: ClientOnboarding) -> dict:
    return {
        "token": record.token,
        "status": record.status,
        "client_name": record.client_name,
        "client_email": record.client_email,
        "favorite": record.favorite,
        "created_at": record.created_at,
        "submitted_at": record.submitted_at,
        "data": record.form_data,
        "public_path": f"/client-form/{record.token}",
    }


@app.get("/health")
def health() -> dict:
    service = PortfolioAnalysisService()
    with service.engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected", "time": datetime.now(timezone.utc)}


@app.get("/api/dashboard")
def dashboard(principal: Principal = Depends(get_principal)) -> dict:
    with Session(CLIENT_ENGINE) as session:
        query = select(PortfolioRun)
        if principal.user.role != "admin" or principal.is_impersonating:
            query = query.where(PortfolioRun.owner_id == principal.owner.id)
        records = session.scalars(query.order_by(PortfolioRun.created_at.desc())).all()
        recent = []
        for record in records[:50]:
            payload = dict(record.summary or {})
            payload.update({
                "id": record.id, "status": record.status, "filename": record.filename,
                "created_at": record.created_at, "completed_at": record.completed_at,
                "owner_id": record.owner_id,
            })
            recent.append(payload)
        return {"recent_analyses": recent, "total_analyses": len(records)}


@app.post("/api/admin/clients/invitations")
def create_client_invitation(principal: Principal = Depends(get_admin)) -> dict:
    invitation = ClientOnboarding(token=secrets.token_urlsafe(32), status="pending")
    with Session(CLIENT_ENGINE) as session:
        session.add(invitation)
        session.commit()
        session.refresh(invitation)
        return _client_payload(invitation)


@app.get("/api/admin/clients")
def list_clients(principal: Principal = Depends(get_admin)) -> dict:
    with Session(CLIENT_ENGINE) as session:
        records = session.scalars(
            select(ClientOnboarding).order_by(ClientOnboarding.created_at.desc())
        ).all()
        return {"clients": [_client_payload(record) for record in records]}


@app.get("/api/admin/clients/{token}")
def client_detail(token: str, principal: Principal = Depends(get_admin)) -> dict:
    with Session(CLIENT_ENGINE) as session:
        record = session.get(ClientOnboarding, token)
        if record is None:
            raise HTTPException(status_code=404, detail="Client invitation not found")
        return _client_payload(record)


@app.patch("/api/admin/clients/{token}/favorite")
def update_client_favorite(token: str, request: FavoriteRequest, principal: Principal = Depends(get_admin)) -> dict:
    with Session(CLIENT_ENGINE) as session:
        record = session.get(ClientOnboarding, token)
        if record is None:
            raise HTTPException(status_code=404, detail="Client invitation not found")
        record.favorite = request.favorite
        session.commit()
        session.refresh(record)
        return _client_payload(record)


def _flatten_client(value: object, prefix: str = "") -> dict[str, object]:
    if isinstance(value, dict):
        flattened: dict[str, object] = {}
        for key, item in value.items():
            label = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(_flatten_client(item, label))
        return flattened
    if isinstance(value, list):
        return {prefix: ", ".join(str(item) for item in value)}
    return {prefix: value}


@app.post("/api/admin/clients/export")
def export_clients(request: ClientExportRequest, principal: Principal = Depends(get_admin)) -> StreamingResponse:
    if not request.tokens:
        raise HTTPException(status_code=422, detail="Select at least one client")
    with Session(CLIENT_ENGINE) as session:
        records = session.scalars(
            select(ClientOnboarding).where(ClientOnboarding.token.in_(request.tokens))
        ).all()
    if not records:
        raise HTTPException(status_code=404, detail="No selected clients were found")
    rows = []
    for record in records:
        row = {
            "Client Name": record.client_name or "",
            "Email": record.client_email or "",
            "Status": record.status,
            "Favorite": "Yes" if record.favorite else "No",
            "Created At": record.created_at.isoformat() if record.created_at else "",
            "Submitted At": record.submitted_at.isoformat() if record.submitted_at else "",
        }
        row.update(_flatten_client(record.form_data or {}))
        rows.append(row)
    headers = list(dict.fromkeys(key for row in rows for key in row))
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Client Details"
    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(header, "") for header in headers])
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for cell in sheet[1]:
        cell.font = cell.font.copy(bold=True, color="FFFFFF")
        cell.fill = cell.fill.copy(fill_type="solid", fgColor="153E5C")
    for column in sheet.columns:
        letter = column[0].column_letter
        width = min(max(len(str(cell.value or "")) for cell in column) + 2, 42)
        sheet.column_dimensions[letter].width = max(width, 12)
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    filename = f"client-details-{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/public/client-form/{token}")
def public_client_form(token: str) -> dict:
    with Session(CLIENT_ENGINE) as session:
        record = session.get(ClientOnboarding, token)
        if record is None:
            raise HTTPException(status_code=404, detail="This client form link is invalid")
        return {
            "token": token,
            "status": record.status,
            "submitted_at": record.submitted_at,
        }


@app.post("/api/public/client-form/{token}")
def submit_client_form(token: str, submission: ClientSubmission) -> dict:
    data = submission.data
    personal = data.get("personal", {})
    contact = data.get("contact", {})
    required = {
        "Full name": personal.get("full_name"),
        "Date of birth": personal.get("date_of_birth"),
        "Mobile number": contact.get("mobile"),
        "Email address": contact.get("email"),
        "Residential address": contact.get("residential_address"),
    }
    missing = [label for label, value in required.items() if not str(value or "").strip()]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Complete the required fields: {', '.join(missing)}",
        )
    with Session(CLIENT_ENGINE) as session:
        record = session.get(ClientOnboarding, token)
        if record is None:
            raise HTTPException(status_code=404, detail="This client form link is invalid")
        if record.status == "submitted":
            raise HTTPException(status_code=409, detail="This client form was already submitted")
        record.form_data = data
        record.client_name = str(personal["full_name"]).strip()
        record.client_email = str(contact["email"]).strip().lower()
        record.status = "submitted"
        record.submitted_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(record)
        return {"status": "submitted", "submitted_at": record.submitted_at}


@app.post("/api/analyses/preview")
def preview(file: UploadFile = File(...), principal: Principal = Depends(get_principal)) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="Upload an Excel .xlsx or .xls file")
    run_id = str(uuid.uuid4())
    run_dir = _run_dir(run_id)
    run_dir.mkdir(parents=True)
    upload_path = run_dir / f"holdings{suffix}"
    with upload_path.open("wb") as destination:
        shutil.copyfileobj(file.file, destination)
    if upload_path.stat().st_size > MAX_UPLOAD_BYTES:
        shutil.rmtree(run_dir)
        raise HTTPException(status_code=413, detail="Workbook exceeds the 20 MB upload limit")
    try:
        result = PortfolioAnalysisService().preview(upload_path)
    except Exception as exc:
        shutil.rmtree(run_dir)
        raise HTTPException(status_code=422, detail=f"Could not read holdings: {exc}") from exc
    with Session(CLIENT_ENGINE) as session:
        session.add(PortfolioRun(
            id=run_id, owner_id=principal.owner.id, created_by_id=principal.user.id,
            filename=file.filename or f"holdings{suffix}", status="uploaded",
        ))
        session.commit()
    return {"upload_id": run_id, **result}


@app.post("/api/analyses")
def create_analysis(request: AnalysisRequest, principal: Principal = Depends(get_principal)) -> dict:
    run_dir = _run_dir(request.upload_id)
    with Session(CLIENT_ENGINE) as session:
        record = session.get(PortfolioRun, request.upload_id)
        if not record or record.owner_id != principal.owner.id:
            raise HTTPException(status_code=404, detail="Uploaded workbook not found")
    uploads = list(run_dir.glob("holdings.*"))
    if not uploads:
        raise HTTPException(status_code=404, detail="Uploaded workbook not found")
    status = {
        "id": request.upload_id,
        "status": "processing",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "filename": uploads[0].name,
    }
    _write_json(run_dir / "status.json", status)
    with Session(CLIENT_ENGINE) as session:
        record = session.get(PortfolioRun, request.upload_id)
        record.status = "processing"
        session.commit()
    try:
        result = PortfolioAnalysisService().analyze(uploads[0], run_dir / "portfolio-report.pdf", _report_configuration(principal.owner.id))
        _write_json(run_dir / "result.json", result)
        status.update(
            {
                "status": "complete",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "portfolio_value": result["summary"]["total_portfolio_value"],
                "holdings": result["summary"]["total_holdings"],
                "risk_score": result["risk"]["overall_score"],
                "risk_level": result["risk"]["overall_level"],
            }
        )
    except Exception as exc:
        status.update({"status": "failed", "error": str(exc)})
        _write_json(run_dir / "status.json", status)
        with Session(CLIENT_ENGINE) as session:
            record = session.get(PortfolioRun, request.upload_id)
            record.status = "failed"
            record.summary = {"error": str(exc)}
            session.commit()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc
    _write_json(run_dir / "status.json", status)
    with Session(CLIENT_ENGINE) as session:
        record = session.get(PortfolioRun, request.upload_id)
        record.status = "complete"
        record.completed_at = datetime.now(timezone.utc)
        record.summary = {
            "portfolio_value": result["summary"]["total_portfolio_value"],
            "holdings": result["summary"]["total_holdings"],
            "risk_score": result["risk"]["overall_score"],
            "risk_level": result["risk"]["overall_level"],
        }
        session.commit()
    return {"status": status, "result": result}


def _authorized_run(run_id: str, principal: Principal) -> PortfolioRun:
    with Session(CLIENT_ENGINE) as session:
        record = session.get(PortfolioRun, run_id)
        if not record:
            raise HTTPException(status_code=404, detail="Analysis not found")
        allowed = principal.user.role == "admin" and not principal.is_impersonating
        if record.owner_id != principal.owner.id and not allowed:
            raise HTTPException(status_code=404, detail="Analysis not found")
        session.expunge(record)
        return record


@app.get("/api/analyses/{run_id}")
def get_analysis(run_id: str, principal: Principal = Depends(get_principal)) -> dict:
    _authorized_run(run_id, principal)
    run_dir = _run_dir(run_id)
    return {
        "status": _read_json(run_dir / "status.json"),
        "result": _read_json(run_dir / "result.json") if (run_dir / "result.json").exists() else None,
    }


@app.get("/api/analyses/{run_id}/report")
def get_report(run_id: str, principal: Principal = Depends(get_principal)) -> FileResponse:
    record = _authorized_run(run_id, principal)
    run_dir = _run_dir(run_id)
    configuration = _report_configuration(record.owner_id)
    signature = hashlib.sha256(json.dumps(configuration, sort_keys=True, default=str).encode()).hexdigest()[:12]
    report = run_dir / f"portfolio-report-{signature}.pdf"
    if not report.exists():
        uploads = list(run_dir.glob("holdings.*"))
        if not uploads:
            raise HTTPException(status_code=404, detail="Report source not found")
        try:
            PortfolioAnalysisService().analyze(uploads[0], report, configuration)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Could not build customized report: {exc}") from exc
    return FileResponse(report, media_type="application/pdf", filename=f"portfolio-analysis-{run_id[:8]}.pdf")


@app.post("/api/analyses/compare")
def compare_analyses(request: CompareRequest, principal: Principal = Depends(get_principal)) -> dict:
    older = _authorized_run(request.older_id, principal)
    newer = _authorized_run(request.newer_id, principal)
    if older.owner_id != newer.owner_id:
        raise HTTPException(status_code=422, detail="Only portfolios belonging to the same client can be compared")
    old_result = _read_json(_run_dir(older.id) / "result.json")
    new_result = _read_json(_run_dir(newer.id) / "result.json")
    old_holdings = {row["isin"]: row for row in old_result.get("portfolio", [])}
    new_holdings = {row["isin"]: row for row in new_result.get("portfolio", [])}
    added = [new_holdings[key] for key in new_holdings.keys() - old_holdings.keys()]
    removed = [old_holdings[key] for key in old_holdings.keys() - new_holdings.keys()]
    changed = []
    for isin in old_holdings.keys() & new_holdings.keys():
        old_row, new_row = old_holdings[isin], new_holdings[isin]
        quantity_delta = float(new_row.get("quantity") or 0) - float(old_row.get("quantity") or 0)
        value_delta = float(new_row.get("value") or 0) - float(old_row.get("value") or 0)
        if quantity_delta or value_delta:
            changed.append({"isin": isin, "security_name": new_row.get("security_name"), "quantity_delta": quantity_delta, "value_delta": value_delta})
    old_summary, new_summary = old_result["summary"], new_result["summary"]
    return {
        "older": {"id": older.id, "created_at": older.created_at, "summary": old_summary},
        "newer": {"id": newer.id, "created_at": newer.created_at, "summary": new_summary},
        "changes": {
            "portfolio_value": new_summary["total_portfolio_value"] - old_summary["total_portfolio_value"],
            "holdings": new_summary["total_holdings"] - old_summary["total_holdings"],
            "risk_score": float(new_result["risk"]["overall_score"]) - float(old_result["risk"]["overall_score"]),
            "added": added, "removed": removed, "changed": changed,
        },
    }
