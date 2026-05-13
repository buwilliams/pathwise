from __future__ import annotations

import json
from dataclasses import asdict
from typing import Annotated

import typer

from pathwise.config import get_settings
from pathwise.core.auth import (
    AuthError,
    AuthService,
)
from pathwise.core.checkin import CheckinError, CheckinService
from pathwise.core.ids import normalize_phone, user_id_for_phone
from pathwise.core.plan import PlanError, generate_plan, list_plans, read_plan
from pathwise.core.profile import ProfileService
from pathwise.core.questionnaire import AnswerValidationError, QuestionnaireService
from pathwise.core.season import (
    get_pack,
    latest_revision,
    list_packs,
    list_revisions,
)
from pathwise.core.store import FileStore
from pathwise.sms.factory import build_sms_sender
from pathwise.verify.factory import build_verifier

app = typer.Typer(
    name="pathwise",
    help="Pathwise — life-strategy planner CLI. Build momentum, live well.",
    no_args_is_help=True,
)


def _store() -> FileStore:
    return FileStore(get_settings().users_dir)


def _auth() -> AuthService:
    settings = get_settings()
    store = _store()
    return AuthService(store, settings, build_verifier(settings, store))


def _profiles() -> ProfileService:
    return ProfileService(_store())


def _print_json(obj: object) -> None:
    typer.echo(json.dumps(obj, indent=2, sort_keys=True, default=str))


# ----------------------------------------------------------------------
# serve
# ----------------------------------------------------------------------


@app.command()
def serve(
    host: Annotated[str, typer.Option(help="Bind host")] = "",
    port: Annotated[int, typer.Option(help="Bind port")] = 0,
    reload: Annotated[bool, typer.Option(help="Auto-reload on changes")] = False,
    log_level: Annotated[str, typer.Option(help="DEBUG | INFO | WARNING | ERROR")] = "INFO",
) -> None:
    """Run the Pathwise web server (FastAPI + uvicorn)."""
    import logging

    import uvicorn

    # Route pathwise.* loggers through the root logger so plan/research/auth
    # messages show up alongside uvicorn's request log. Without this, anything
    # below WARNING is dropped silently and slow LLM calls look like a hang.
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    settings = get_settings()
    uvicorn.run(
        "pathwise.api.app:app",
        host=host or settings.pathwise_host,
        port=port or settings.pathwise_port,
        reload=reload,
    )


# ----------------------------------------------------------------------
# user
# ----------------------------------------------------------------------

user_app = typer.Typer(help="Manage user profiles.", no_args_is_help=True)
app.add_typer(user_app, name="user")


@user_app.command("create")
def user_create(
    phone: Annotated[str, typer.Option(help="Phone, any reasonable format")],
    name: Annotated[str, typer.Option(help="First name")],
    gender: Annotated[str, typer.Option(help="male | female | non-binary")],
    zip_code: Annotated[str, typer.Option("--zip", help="ZIP code (optional)")] = "",
) -> None:
    """Create a profile (skips OTP — for dev only)."""
    if gender not in ("male", "female", "non-binary"):
        raise typer.BadParameter("gender must be one of: male, female, non-binary")
    phone_e164 = normalize_phone(phone)
    profile = _profiles().create(
        phone_e164=phone_e164,
        first_name=name,
        gender=gender,  # type: ignore[arg-type]
        zip_code=zip_code or None,
    )
    _print_json(asdict(profile))


@user_app.command("show")
def user_show(
    phone: Annotated[str, typer.Option(help="Phone, any reasonable format")],
) -> None:
    phone_e164 = normalize_phone(phone)
    user_id = user_id_for_phone(phone_e164)
    profile = _profiles().get(user_id)
    if profile is None:
        typer.echo(f"No profile for {phone_e164}", err=True)
        raise typer.Exit(code=1)
    _print_json(asdict(profile))


@user_app.command("delete")
def user_delete(
    phone: Annotated[str, typer.Option(help="Phone, any reasonable format")],
    yes: Annotated[bool, typer.Option("--yes", help="Skip confirmation")] = False,
) -> None:
    phone_e164 = normalize_phone(phone)
    user_id = user_id_for_phone(phone_e164)
    if not yes:
        typer.confirm(f"Delete all data for {phone_e164}?", abort=True)
    _profiles().delete(user_id)
    typer.echo(f"Deleted user {user_id}")


# ----------------------------------------------------------------------
# auth
# ----------------------------------------------------------------------

auth_app = typer.Typer(help="Phone-based OTP auth.", no_args_is_help=True)
app.add_typer(auth_app, name="auth")


@auth_app.command("send-code")
def auth_send_code(
    phone: Annotated[str, typer.Option(help="Phone, any reasonable format")],
) -> None:
    """Send an OTP code. In dev (no Twilio creds) the code prints to the server log."""
    phone_e164 = normalize_phone(phone)
    try:
        _auth().start(phone_e164)
    except AuthError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Code sent to {phone_e164}")


@auth_app.command("test-sms")
def auth_test_sms(
    phone: Annotated[str, typer.Option(help="Phone, any reasonable format")],
    body: Annotated[
        str, typer.Option(help="Custom body")
    ] = "Pathwise test message — if you got this, SMS is working.",
) -> None:
    """Send a one-off SMS via the configured sender (Twilio if creds set,
    console otherwise). Doesn't touch OTP state — purely for verifying the
    SMS path end-to-end after pasting Twilio credentials."""
    settings = get_settings()
    sender = build_sms_sender(settings)
    phone_e164 = normalize_phone(phone)
    backend = sender.__class__.__name__
    typer.echo(f"Sending via {backend} → {phone_e164} …")
    try:
        sender.send(phone_e164, body)
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if backend == "ConsoleSmsSender":
        typer.echo(
            "Done — message printed to the server log "
            "(no Twilio creds configured; set TWILIO_* env vars to send for real)."
        )
    else:
        typer.echo("Done — Twilio accepted the message. Check your phone.")


@auth_app.command("verify")
def auth_verify(
    phone: Annotated[str, typer.Option(help="Phone, any reasonable format")],
    code: Annotated[str, typer.Option(help="6-digit code")],
) -> None:
    phone_e164 = normalize_phone(phone)
    try:
        result = _auth().verify(phone_e164, code)
    except AuthError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    _print_json(
        {
            "session_token": result.session_token,
            "user_id": result.user_id,
            "needs_onboarding": result.needs_onboarding,
        }
    )


# ----------------------------------------------------------------------
# season
# ----------------------------------------------------------------------

season_app = typer.Typer(help="Inspect season packs.", no_args_is_help=True)
app.add_typer(season_app, name="season")


@season_app.command("list")
def season_list() -> None:
    packs = list_packs()
    if not packs:
        typer.echo("(no packs found)")
        return
    for p in packs:
        revs = list_revisions(p.id)
        suffix = f" ({len(revs)} revisions)" if len(revs) > 1 else ""
        typer.echo(f"{p.id}\tv{p.version}\t{p.name}{suffix}")


@season_app.command("show")
def season_show(
    season_id: Annotated[str, typer.Argument()],
    revision: Annotated[
        str | None,
        typer.Option(help="Specific revision (defaults to latest)"),
    ] = None,
) -> None:
    try:
        pack = get_pack(season_id, revision=revision)
    except KeyError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    q = pack.questionnaire
    _print_json(
        {
            "id": pack.id,
            "name": pack.name,
            "summary": pack.summary,
            "version": pack.version,
            "revision": pack.revision,
            "available_revisions": list_revisions(pack.id),
            "latest_revision": latest_revision(pack.id),
            "schema_version": q.schema_version,
            "data_model_keys": sorted(q.data_model.keys()),
            "step_count": len(q.steps),
            "question_count": len(q.questions),
            "scenarios": [s.id for s in pack.scenarios],
            "weights": pack.weights,
        }
    )


# ----------------------------------------------------------------------
# question / answer
# ----------------------------------------------------------------------

question_app = typer.Typer(help="Inspect questions in a season pack.", no_args_is_help=True)
app.add_typer(question_app, name="question")


@question_app.command("list")
def question_list(
    season: Annotated[str, typer.Option(help="Season id")] = "build-independence",
    keys_only: Annotated[bool, typer.Option("--keys-only")] = False,
) -> None:
    pack = get_pack(season)
    qn = pack.questionnaire
    if keys_only:
        for step in qn.steps:
            for qkey in step.questions:
                typer.echo(qkey)
        return
    for step in qn.steps:
        for qkey in step.questions:
            q = qn.questions[qkey]
            field = qn.data_model[qkey]
            marker = "*" if q.required else " "
            typer.echo(f"{marker} [{step.id}] {qkey} ({field.type}): {q.prompt}")


answer_app = typer.Typer(help="Get/set questionnaire answers.", no_args_is_help=True)
app.add_typer(answer_app, name="answer")


def _resolve_user_id(phone: str) -> str:
    return user_id_for_phone(normalize_phone(phone))


@answer_app.command("show")
def answer_show(
    phone: Annotated[str, typer.Option()],
    season: Annotated[str, typer.Option()] = "build-independence",
) -> None:
    pack = get_pack(season)
    qs = QuestionnaireService(_store())
    user_id = _resolve_user_id(phone)
    answers = qs.get_answers(user_id, pack.id)
    completion = qs.completion(user_id, pack)
    _print_json(
        {
            "answers": answers,
            "completion": {
                "answered": completion.answered,
                "required_total": completion.required_total,
                "missing_required": completion.missing_required,
                "percent": completion.percent,
                "is_complete": completion.is_complete,
            },
        }
    )


@answer_app.command("set")
def answer_set(
    phone: Annotated[str, typer.Option()],
    key: Annotated[str, typer.Option()],
    value: Annotated[str, typer.Option(help="Raw value (string, will be coerced)")],
    season: Annotated[str, typer.Option()] = "build-independence",
) -> None:
    pack = get_pack(season)
    qs = QuestionnaireService(_store())
    user_id = _resolve_user_id(phone)
    try:
        coerced = qs.set_answer(user_id, pack, key, value)
    except (AnswerValidationError, KeyError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"{key} = {coerced!r}")


# ----------------------------------------------------------------------
# plan
# ----------------------------------------------------------------------

plan_app = typer.Typer(help="Generate, list, and read plans.", no_args_is_help=True)
app.add_typer(plan_app, name="plan")


@plan_app.command("generate")
def plan_generate(
    phone: Annotated[str, typer.Option()],
    season: Annotated[str, typer.Option()] = "build-independence",
    skip_research: Annotated[
        bool,
        typer.Option(
            "--skip-research",
            help="Skip the LLM web-search call (uses defaults). Useful for offline tests.",
        ),
    ] = False,
) -> None:
    user_id = _resolve_user_id(phone)
    try:
        result = generate_plan(
            user_id=user_id,
            season_id=season,
            store=_store(),
            skip_research=skip_research,
        )
    except PlanError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Generated plan v{result.version} → {result.plan_path}")


@plan_app.command("list")
def plan_list(
    phone: Annotated[str, typer.Option()],
    season: Annotated[str, typer.Option()] = "build-independence",
) -> None:
    user_id = _resolve_user_id(phone)
    versions = list_plans(user_id, season, _store())
    if not versions:
        typer.echo("(no plans yet)")
        return
    for v in versions:
        typer.echo(f"v{v}")


@plan_app.command("show")
def plan_show(
    phone: Annotated[str, typer.Option()],
    version: Annotated[int, typer.Option()] = 0,
    season: Annotated[str, typer.Option()] = "build-independence",
    meta: Annotated[bool, typer.Option("--meta", help="Print metadata JSON instead of the markdown plan")] = False,
) -> None:
    user_id = _resolve_user_id(phone)
    versions = list_plans(user_id, season, _store())
    if not versions:
        typer.echo("(no plans)", err=True)
        raise typer.Exit(code=1)
    chosen = version or versions[-1]
    if chosen not in versions:
        typer.echo(f"v{chosen} not found. available: {versions}", err=True)
        raise typer.Exit(code=1)
    text, m = read_plan(user_id, season, chosen, _store())
    if meta:
        _print_json(m)
    else:
        typer.echo(text)


# ----------------------------------------------------------------------
# checkin
# ----------------------------------------------------------------------

checkin_app = typer.Typer(
    help="Record and inspect weekly check-ins (roadmap.md #1).",
    no_args_is_help=True,
)
app.add_typer(checkin_app, name="checkin")


@checkin_app.command("record")
def checkin_record(
    phone: Annotated[str, typer.Option(help="Phone, any reasonable format")],
    season: Annotated[str, typer.Option()] = "build-independence",
    b: Annotated[
        float | None,
        typer.Option("--buffer-hours", help="Buffer hours this week (0–168)"),
    ] = None,
    eta: Annotated[
        float | None,
        typer.Option("--eta", help="Net emotional impact (-2..+2)"),
    ] = None,
    zeta: Annotated[
        float | None,
        typer.Option("--zeta", help="Fitness practice (1..5)"),
    ] = None,
    q: Annotated[
        float | None,
        typer.Option("--q", help="Quality of time / energy (1..5)"),
    ] = None,
    note: Annotated[str, typer.Option(help="Optional free-text note")] = "",
) -> None:
    """Append a new check-in. Pass at least one observation."""
    obs = {
        k: v
        for k, v in (("b", b), ("eta", eta), ("zeta", zeta), ("q", q))
        if v is not None
    }
    if not obs:
        typer.echo(
            "Error: pass at least one of --buffer-hours, --eta, --zeta, --q",
            err=True,
        )
        raise typer.Exit(code=1)
    user_id = _resolve_user_id(phone)
    svc = CheckinService(_store())
    try:
        checkin = svc.record(
            user_id=user_id,
            season_id=season,
            observations=obs,
            note=note or None,
        )
    except CheckinError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    _print_json(
        {
            "at": checkin.at,
            "observations": checkin.observations,
            "note": checkin.note,
        }
    )


@checkin_app.command("list")
def checkin_list(
    phone: Annotated[str, typer.Option()],
    season: Annotated[str, typer.Option()] = "build-independence",
    limit: Annotated[int, typer.Option(help="Most recent N to show")] = 50,
) -> None:
    user_id = _resolve_user_id(phone)
    checkins = CheckinService(_store()).list(user_id, season)
    if not checkins:
        typer.echo("(no check-ins yet)")
        return
    _print_json(
        [
            {"at": c.at, "observations": c.observations, "note": c.note}
            for c in checkins[-limit:]
        ]
    )


@checkin_app.command("drift")
def checkin_drift(
    phone: Annotated[str, typer.Option()],
    season: Annotated[str, typer.Option()] = "build-independence",
    falling_streak: Annotated[
        int,
        typer.Option(help="Consecutive falls needed for an alert"),
    ] = 3,
) -> None:
    """Per-component direction + alerts on consecutive declines."""
    user_id = _resolve_user_id(phone)
    report = CheckinService(_store()).drift(
        user_id, season, falling_streak=falling_streak
    )
    _print_json(report.to_jsonable())


if __name__ == "__main__":
    app()
