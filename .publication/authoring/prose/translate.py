#!/usr/bin/env python3
"""Prepare and validate translations performed by the host's native subagent.

Python never selects or invokes a model. The coordinator dispatches each prepared
prompt to a subagent inheriting its active model, then accepts the raw response.
The actual parent-model identifier is provenance, not a provider selection flag.

Usage:
    python3 translate.py JOB.json OUT.json --parent-model ACTUAL_MODEL --prepare REQUEST_DIR
    python3 translate.py JOB.json OUT.json --parent-model ACTUAL_MODEL --accept REQUEST.json --response RESPONSE.json --agent-id NATIVE_AGENT_ID
    python3 translate.py JOB.json OUT.json --parent-model ACTUAL_MODEL --check-only
    python3 translate.py --selftest
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_STYLE = SCRIPT_DIR / "translate-style.md"
ENGINE_VERSION = "2026-09-23.native-1"
BACKEND = "native-subagent"
DEFAULT_BATCH = 12
DEFAULT_MAX_PROMPT_CHARS = 50000
VALID_MODES = {"plain", "elevated", "mixed"}
ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", nargs="?", type=Path)
    parser.add_argument("out", nargs="?", type=Path)
    parser.add_argument("--style", type=Path, default=DEFAULT_STYLE)
    parser.add_argument("--parent-model", dest="model", help="Actual model reported by the running host; inherited by the native child.")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--prepare", type=Path, help="New directory for native-subagent request batches.")
    action.add_argument("--accept", type=Path, help="Accept a response to this prepared request.")
    action.add_argument("--check-only", action="store_true")
    parser.add_argument("--response", type=Path)
    parser.add_argument("--agent-id", help="Identifier returned by the native subagent tool, not an invented label.")
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH)
    parser.add_argument("--max-prompt-chars", type=int, default=DEFAULT_MAX_PROMPT_CHARS)
    parser.add_argument("--force", action="store_true", help="Prepare all units again, invalidating prior output cache.")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:return args
    if args.job is None or args.out is None:parser.error("JOB.json and OUT.json are required")
    if not args.model or args.model.strip().lower() in {'inherit','default','unknown'}:
        parser.error("--parent-model must record the actual running model; never guess its identity")
    if not (args.prepare or args.accept or args.check_only):
        parser.error("use --prepare REQUEST_DIR, dispatch native subagents, then --accept; this helper does not launch a provider")
    if args.accept and (not args.response or not args.agent_id or not args.agent_id.strip()):
        parser.error("--accept requires --response and the native --agent-id")
    if not args.accept and (args.response or args.agent_id):parser.error("--response/--agent-id require --accept")
    if args.force and not args.prepare:parser.error("--force requires --prepare")
    if args.batch < 1:parser.error("--batch must be at least 1")
    if args.max_prompt_chars < 5000:parser.error("--max-prompt-chars must be at least 5000")
    if args.job.resolve()==args.out.resolve():parser.error("input job and output must be different files")
    return args


def strict_json(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate JSON key: '+key)
            result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=unique)


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        data = strict_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return data


def validate_job(job: dict[str, Any]) -> list[dict[str, str]]:
    blocks = job.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        raise ValueError("job must contain a non-empty 'blocks' list")

    seen: set[str] = set()
    clean: list[dict[str, str]] = []
    for index, raw in enumerate(blocks):
        if not isinstance(raw, dict):
            raise ValueError(f"blocks[{index}] must be an object")

        uid = raw.get("id")
        if 'arabic' in raw and ('source' in raw or 'source_language' in raw):
            raise ValueError('Use either legacy arabic or source plus source_language, never both')
        arabic = raw.get('source',raw.get('arabic'))
        language = raw.get('source_language','ar' if 'arabic' in raw else None)
        if not isinstance(language,str) or not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z0-9]+)*',language):
            raise ValueError('source_language must identify the actual source, for example grc, he, arc, la, ar')
        mode = raw.get("mode", "plain")
        note = raw.get("note", "")

        if not isinstance(uid, str) or not uid.strip():
            raise ValueError(f"blocks[{index}].id must be a non-empty string")
        uid = uid.strip()
        if uid in seen:
            raise ValueError(f"duplicate block id: {uid}")
        seen.add(uid)

        if not isinstance(arabic, str) or not arabic.strip():
            raise ValueError(f"{uid}: source must be a non-empty string")
        scripts={'ar':r'[\u0621-\u063a\u0641-\u064a\u066e-\u06d3]','grc':r'[Ͱ-Ͽἀ-῿]','he':r'[֐-׿]','la':r'[A-Za-zÀ-ž]','syr':r'[܀-ݏ]'}
        if language in scripts and not re.search(scripts[language],arabic):
            raise ValueError(f'{uid}: source script does not match source_language {language}')
        if mode not in VALID_MODES:
            raise ValueError(f"{uid}: mode must be one of {sorted(VALID_MODES)}")
        if not isinstance(note, str):
            raise ValueError(f"{uid}: note must be a string")

        clean.append({"id": uid, "source": arabic, "source_language": language, "mode": mode, "note": note})
    return clean


def build_prompt(style_text: str, units: list[dict[str, str]], repair_notes: dict[str, list[str]] | None = None) -> str:
    repair_notes = repair_notes or {}
    input_units: list[dict[str, str]] = []
    for unit in units:
        item = dict(unit)
        if "arabic" in item:
            item["source"]=item.pop("arabic");item["source_language"]="ar"
        if repair_notes.get(unit["id"]):
            failures = "; ".join(repair_notes[unit["id"]])
            extra = f"Previous attempt failed these mechanical checks: {failures}. Rewrite the translation to fix them."
            item["note"] = " ".join(x for x in [item.get("note", ""), extra] if x).strip()
        input_units.append(item)

    ids = [u["id"] for u in units]
    output_shape = {uid: "<complete English translation>" for uid in ids}
    payload = {"units": input_units}

    return (
        style_text.rstrip()
        + "\n\nTASK\n"
        + "Translate every unit directly from its identified source_language into complete, natural English. Do not use an Arabic or other intermediary.  Follow the style card above and the unit mode. "
        + "Preserve every name, number, condition, negation, sequence, and qualification. Do not summarize. "
        + "Return only one valid JSON object. Use exactly the requested keys. Every value must be a string. "
        + "Do not include markdown fences, commentary, or Arabic script in the output.\n\n"
        + "REQUIRED OUTPUT SHAPE\n"
        + json.dumps(output_shape, ensure_ascii=False, indent=2)
        + "\n\nINPUT UNITS\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )



def parse_json_object(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if not text:
        return None

    direct = text
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        direct = fence.group(1).strip()

    for candidate in (direct, text):
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            pass

    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            value, _ = decoder.raw_decode(text[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def validate_response(data: dict[str, Any], expected_ids: list[str]) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    expected = set(expected_ids)
    actual = set(data)

    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        errors.append(f"missing ids: {missing}")
    if extra:
        errors.append(f"unexpected ids: {extra}")

    clean: dict[str, str] = {}
    for uid in expected_ids:
        if uid not in data:
            continue
        value = data[uid]
        if not isinstance(value, str):
            errors.append(f"{uid}: translation must be a string")
            continue
        value = value.strip()
        if not value:
            errors.append(f"{uid}: empty translation")
            continue
        clean[uid] = value
    return clean, errors


def check_translation(text: str, uid: str, mode: str) -> list[str]:
    bad: list[str] = []
    if "—" in text or "–" in text:
        bad.append("em/en dash")
    if ARABIC_RE.search(text):
        bad.append("Arabic characters in output")
    if ":" in re.sub(r"\b\d+:\d+\b|https?://\S+", "", text):
        bad.append("colon in translation prose")

    return [f"{uid}: {item}" for item in bad]


def translation_warnings(text: str, mode: str) -> list[str]:
    """Style cues require source-aware judgment; never erase a source negation."""
    cues = []
    for label, pattern in [
        ("check contrast against source", r"(?i)\b(?:rather than|instead of|not merely|not simply)\b|\bnot\b[^.!?]{0,90}\bbut\b"),
        ("check understatement against source", r"(?i)\b(?:hardly|scarcely|not un\w+|no small|by no means)\b"),
        ("check tone against source", r"(?i)\b(?:of course|naturally|predictably|how convenient)\b"),
    ]:
        if re.search(pattern, text):
            cues.append(label)
    grade = fk_grade(text)
    if mode == "plain" and grade is not None and grade > 11:
        cues.append(f"readability grade {grade:.1f}; inspect clarity without losing meaning")
    return cues


def _syllables(word: str) -> int:
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    groups = len(re.findall(r"[aeiouy]+", word))
    if word.endswith("e") and groups > 1 and not word.endswith(("le", "ye")):
        groups -= 1
    return max(1, groups)


def fk_grade(text: str) -> float | None:
    """Approximate Flesch-Kincaid grade, excluding obvious isnad chains."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    sentences = [s for s in sentences if len(re.findall(r"(?i),\s*from\s+|\band from\b", s)) < 2]
    if not sentences:
        return None

    words = re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)?", " ".join(sentences))
    if not words:
        return None

    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = sum(_syllables(w) for w in words) / len(words)
    return 0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59


def fingerprint(unit: dict[str, str], *, style_hash: str, model: str) -> str:
    material = {
        "engine_version": ENGINE_VERSION,
        "backend": BACKEND,
        "model_policy": "inherit-parent",
        "source": unit.get("source",unit.get("arabic")),
        "source_language": unit.get("source_language","ar"),
        "mode": unit["mode"],
        "note": unit.get("note", ""),
        "style_hash": style_hash,
        "model": model,
    }
    blob = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def cache_record(unit: dict[str, str], text: str, *, style_hash: str, model: str) -> dict[str, str]:
    """Bind accepted output bytes to all inputs; reject edited or legacy caches."""
    return {
        "fingerprint": fingerprint(unit, style_hash=style_hash, model=model),
        "translation_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def state_path_for(out_path: Path) -> Path:
    return out_path.with_name(out_path.name + ".state.json")


def load_cache(out_path: Path, blocks_by_id: dict[str, dict[str, str]], *, style_hash: str, model: str, force: bool) -> tuple[dict[str, str], dict[str, Any]]:
    if force or not out_path.exists():
        return {}, {}

    raw_done = read_json_object(out_path)
    state_path = state_path_for(out_path)
    state = read_json_object(state_path) if state_path.exists() else {}

    done: dict[str, str] = {}
    fingerprints: dict[str, Any] = {}
    for uid, value in raw_done.items():
        if uid not in blocks_by_id or not isinstance(value, str) or not value.strip() or value != value.strip():
            continue
        unit = blocks_by_id[uid]
        cached_fp = state.get(uid)
        violations = check_translation(value.strip(), uid, unit["mode"])

        if violations:
            continue
        expected_record = cache_record(unit, value.strip(), style_hash=style_hash, model=model)
        if cached_fp != expected_record:
            continue
        done[uid] = value.strip()
        fingerprints[uid] = expected_record

    return done, fingerprints


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def batches(blocks: list[dict[str, str]], *, style_text: str, batch_size: int, max_prompt_chars: int) -> Iterable[list[dict[str, str]]]:
    current: list[dict[str, str]] = []
    for unit in blocks:
        if len(build_prompt(style_text, [unit])) > max_prompt_chars:
            raise ValueError(f"{unit['id']}: a single unit exceeds --max-prompt-chars")
        trial = current + [unit]
        prompt_len = len(build_prompt(style_text, trial))
        if current and (len(trial) > batch_size or prompt_len > max_prompt_chars):
            yield current
            current = [unit]
            if len(build_prompt(style_text, current)) > max_prompt_chars:
                raise ValueError(f"{unit['id']}: a single unit exceeds --max-prompt-chars")
        else:
            current = trial
    if current:
        yield current


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def review_path_for(out_path: Path) -> Path:
    return out_path.with_name(out_path.name + ".review.json")


def write_review(args, blocks, style_hash, done, invocation=None, errors=None):
    by_id={b['id']:b for b in blocks}
    missing=[uid for uid in by_id if uid not in done]
    atomic_write_json(review_path_for(args.out), {
        "status":"translation-incomplete" if missing or errors else "fidelity-review-required",
        "backend":BACKEND,"model_policy":"inherit-parent","parent_model":args.model,
        "engine_version":ENGINE_VERSION,"style_sha256":style_hash,"job_sha256":digest(blocks),
        "output_sha256":hashlib.sha256(args.out.read_bytes()).hexdigest() if args.out.exists() else None,
        "missing_ids":missing,"errors":errors or [],"last_invocation":invocation,
        "warnings":{uid:translation_warnings(text,by_id[uid]['mode']) for uid,text in done.items()},
    })


def save_output(args, blocks, style_hash, done, state, invocation=None):
    atomic_write_json(args.out, done)
    atomic_write_json(state_path_for(args.out), state)
    write_review(args,blocks,style_hash,done,invocation)


def dispatch_path_for(out_path):
    return out_path.with_name(out_path.name+'.dispatch.json')


def prepare_requests(args, blocks, style_text, style_hash, done, state):
    pending=[b for b in blocks if b['id'] not in done]
    work=list(batches(pending,style_text=style_text,batch_size=args.batch,max_prompt_chars=args.max_prompt_chars))
    # Validate all batches before touching output. Preserve previous request directories.
    args.prepare.mkdir(parents=True,exist_ok=False)
    dispatch_id=uuid.uuid4().hex
    manifest={"dispatch_id":dispatch_id,"schema":1,"backend":BACKEND,"model_policy":"inherit-parent",
              "parent_model":args.model,"requests":[],"cached_ids":list(done)}
    for number,units in enumerate(work,1):
        request={"dispatch_id":dispatch_id,"schema":1,"engine_version":ENGINE_VERSION,"backend":BACKEND,
                 "model_policy":"inherit-parent","parent_model":args.model,
                 "job_path":str(args.job.resolve()),"output_path":str(args.out.resolve()),
                 "job_sha256":digest(blocks),"style_sha256":style_hash,
                 "units":units,"prompt":build_prompt(style_text,units)}
        request['request_sha256']=digest(request)
        path=args.prepare/f'batch-{number:03d}.request.json'
        atomic_write_json(path,request)
        manifest['requests'].append(str(path.resolve()))
    atomic_write_json(args.prepare/'manifest.json',manifest)
    atomic_write_json(dispatch_path_for(args.out),manifest)
    save_output(args,blocks,style_hash,done,state)
    print(f"Prepared {len(work)} native-subagent batches; {len(done)} verified cached units.")
    print("Coordinator must dispatch each prompt with the active parent model inherited, then accept each raw response. Fidelity review remains required.")
    return 0


def accept_response(args, blocks, style_text, style_hash, done, state):
    request=read_json_object(args.accept)
    dispatch=read_json_object(dispatch_path_for(args.out))
    if request.get('dispatch_id')!=dispatch.get('dispatch_id') or str(args.accept.resolve()) not in dispatch.get('requests',[]):
        raise ValueError('request was superseded by a later preparation')
    expected_hash=digest({k:v for k,v in request.items() if k!='request_sha256'})
    if request.get('request_sha256')!=expected_hash:raise ValueError('prepared request was edited')
    required={"schema":1,"engine_version":ENGINE_VERSION,"backend":BACKEND,
              "model_policy":"inherit-parent","parent_model":args.model,
              "job_path":str(args.job.resolve()),"output_path":str(args.out.resolve()),
              "job_sha256":digest(blocks),"style_sha256":style_hash}
    for key,value in required.items():
        if request.get(key)!=value:raise ValueError('stale or mismatched request: '+key)
    units=request.get('units',[]);by_id={b['id']:b for b in blocks}
    if not units or any(not isinstance(u,dict) or u.get('id') not in by_id or u!=by_id[u['id']] for u in units):
        raise ValueError('request units differ from current verified job')
    ids=[u['id'] for u in units]
    if len(set(ids))!=len(ids) or request.get('prompt')!=build_prompt(style_text,units):
        raise ValueError('request prompt or unit IDs changed')
    receipt_path=args.accept.with_name(args.accept.name+'.receipt.json')
    if receipt_path.exists():raise ValueError('request already consumed; preserve receipt and prepare a new attempt')
    raw_bytes=args.response.read_bytes()
    raw=raw_bytes.decode('utf-8')
    receipt={"backend":BACKEND,"model_policy":"inherit-parent","parent_model":args.model,
             "agent_id":args.agent_id,"request_sha256":request['request_sha256'],
             "response_path":str(args.response.resolve()),"response_sha256":hashlib.sha256(raw_bytes).hexdigest(),
             "provenance":"Agent identity/model inheritance recorded by host coordinator; not provider-authenticated by this helper."}
    try:
        parsed=strict_json(raw)
        if not isinstance(parsed,dict):raise ValueError('response must be one JSON object')
        returned,errors=validate_response(parsed,ids)
    except (ValueError,TypeError) as exc:returned={};errors=[str(exc)]
    # Reject missing/extra keys as a batch. Never salvage JSON from commentary.
    failures={uid:list(errors) for uid in ids} if errors else {}
    if errors:returned={}
    clean={}
    for uid,text in returned.items():
        violations=check_translation(text,uid,by_id[uid]['mode'])
        if violations:failures[uid]=violations
        else:clean[uid]=text
    for uid in ids:
        # A failed fresh attempt must not leave an older value apparently accepted.
        done.pop(uid,None);state.pop(uid,None)
    for uid,text in clean.items():
        done[uid]=text;state[uid]=cache_record(by_id[uid],text,style_hash=style_hash,model=args.model)
    receipt.update(status='mechanically-accepted' if not failures else 'needs-repair',accepted_ids=list(clean),failures=failures)
    # Preserve the original reply alongside each attempt, including failures.
    archived=args.accept.with_name(args.accept.name+'.response.txt')
    if archived.exists():raise ValueError('archived response already exists; use a new request directory')
    archived.write_bytes(raw_bytes)
    atomic_write_json(receipt_path,receipt)
    save_output(args,blocks,style_hash,done,state,str(receipt_path.resolve()))
    print(f"Accepted {len(clean)} units; {len(failures)} need repair. Receipt: {receipt_path}")
    for uid,reasons in failures.items():print(uid+': '+'; '.join(reasons),file=sys.stderr)
    return 1 if failures else 0


def run_selftest() -> int:
    style = "Translate fully."
    units = [
        {"id": "a", "arabic": "نص", "mode": "plain", "note": ""},
        {"id": "b", "arabic": "نص آخر", "mode": "elevated", "note": ""},
    ]
    prompt = build_prompt(style, units)
    assert '"a"' in prompt and '"b"' in prompt

    assert parse_json_object('{"a":"One","b":"Two"}') == {"a": "One", "b": "Two"}
    assert parse_json_object('```json\n{"a":"One"}\n```') == {"a": "One"}
    assert parse_json_object('prefix {"a":"One"} suffix') == {"a": "One"}
    assert parse_json_object("no json") is None

    valid, errors = validate_response({"a": "One", "b": "Two"}, ["a", "b"])
    assert not errors and valid["a"] == "One"
    _, errors = validate_response({"a": "One", "x": "Extra"}, ["a", "b"])
    assert errors

    assert check_translation("A clear sentence.", "a", "plain") == []
    assert not check_translation("This is not simple but clear.", "a", "plain")
    assert translation_warnings("This is not simple but clear.", "plain")
    assert check_translation("Arabic نص remains.", "a", "plain")

    job = validate_job({"blocks": units})
    assert len(job) == 2
    try:
        validate_job({"blocks": [units[0], units[0]]})
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate ids should fail")

    print("selftest: OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    args=parse_args(argv)
    if args.selftest:return run_selftest()
    try:
        blocks=validate_job(read_json_object(args.job))
        style_text=args.style.read_text(encoding='utf-8')
        style_hash=hashlib.sha256(style_text.encode()).hexdigest()
        done,state=load_cache(args.out,{b['id']:b for b in blocks},style_hash=style_hash,model=args.model,force=args.force)
        if args.check_only:
            previous=read_json_object(review_path_for(args.out)) if review_path_for(args.out).exists() else {}
            raw_output=read_json_object(args.out) if args.out.exists() else {}
            extras=sorted(set(raw_output)-{b['id'] for b in blocks})
            errors=['unexpected cached IDs: '+', '.join(extras)] if extras else []
            write_review(args,blocks,style_hash,done,previous.get('last_invocation'),errors)
            if errors:print('FAILED: '+'; '.join(errors),file=sys.stderr);return 1
            missing=[b['id'] for b in blocks if b['id'] not in done]
            if missing:
                print('FAILED: missing, stale, edited, or invalid translations: '+', '.join(missing),file=sys.stderr);return 1
            print('Native-subagent cache provenance and mechanical checks pass; fidelity review still required.');return 0
        if args.prepare:return prepare_requests(args,blocks,style_text,style_hash,done,state)
        return accept_response(args,blocks,style_text,style_hash,done,state)
    except (OSError,ValueError,TypeError,KeyError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr);return 2


if __name__ == "__main__":
    raise SystemExit(main())