#!/usr/bin/env python3
"""Inspect an Antigravity app conversation or send one follow-up via its local RPC.

Python standard library only. Local UI protocol observed on 2026-10-29.
This is an unofficial, version-dependent helper, not an official Google SDK.
"""
import argparse
import hashlib
import json
import re
import sqlite3
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SERVICE = '/exa.language_server_pb.LanguageServerService/'
DEFAULT_ID = 'feca2faf-c8c5-4c07-8293-c9f0c9e553e4'


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def default_log():
    return Path.home() / 'AppData/Roaming/Antigravity/logs/language_server.log'


def find_base_url(explicit=None, log_file=None):
    if explicit:
        base = explicit.rstrip('/')
    else:
        log = Path(log_file) if log_file else default_log()
        if not log.exists():
            raise ValueError('Cannot find the app log; supply --base-url https://127.0.0.1:PORT')
        text = log.read_text(encoding='utf-8', errors='replace')
        ports = re.findall(r'listening on \w+ port at (\d+) for HTTPS\b', text, re.I)
        if not ports:
            raise ValueError('No HTTPS port found in app log; supply --base-url explicitly')
        base = 'https://127.0.0.1:' + ports[-1]
    parsed = urllib.parse.urlsplit(base)
    if (parsed.scheme != 'https' or parsed.hostname not in ('127.0.0.1', '::1')
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ('', '/') or not parsed.port):
        raise ValueError('Only an explicit HTTPS loopback app origin with a port is accepted')
    return base


class AppClient:
    def __init__(self, base):
        self.base = base
        # Scope the self-signed-certificate exception to this validated loopback origin.
        self.context = ssl._create_unverified_context()
        self.token = None

    def token_for_page(self):
        if self.token is None:
            request = urllib.request.Request(self.base + '/', headers={'Cache-Control': 'no-cache'})
            with urllib.request.urlopen(request, context=self.context, timeout=15) as response:
                html = response.read().decode('utf-8')
            match = re.search(r'"?csrfToken"?\s*:\s*"([^"\s]+)"', html)
            if not match:
                raise ValueError('The local app page did not supply its CSRF token')
            self.token = match[1]
        return self.token

    def rpc(self, method, payload):
        request = urllib.request.Request(
            self.base + SERVICE + method,
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Connect-Protocol-Version': '1',
                     'x-codeium-csrf-token': self.token_for_page()}, method='POST')
        try:
            with urllib.request.urlopen(request, context=self.context, timeout=30) as response:
                raw = response.read()
                return json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as error:
            raw = error.read()
            try:
                code = json.loads(raw).get('code', 'unknown')
            except (ValueError, AttributeError):
                code = 'unknown'
            # Do not echo the response body, headers, CSRF token or credentials.
            raise RuntimeError(f'{method}: HTTP {error.code}, code={code}') from None

    def trajectory(self, conversation):
        data = self.rpc('GetCascadeTrajectory', {'cascadeId': conversation})
        returned = data.get('trajectory', {}).get('cascadeId')
        if returned != conversation:
            raise ValueError('The app returned a different or missing conversation ID')
        return data


def prompt_matches(data, expected_hash):
    matches = []
    for index, step in enumerate(data.get('trajectory', {}).get('steps', [])):
        if step.get('type') != 'CORTEX_STEP_TYPE_USER_INPUT':
            continue
        user = step.get('userInput', {})
        texts = [item['text'] for item in user.get('items', [])
                 if isinstance(item, dict) and isinstance(item.get('text'), str)]
        candidates = texts + [''.join(texts), '\n'.join(texts)]
        candidates += [user.get('userResponse', ''), user.get('query', '')]
        if any(isinstance(text, str) and digest(text.strip()) == expected_hash for text in candidates):
            matches.append({'loaded_step_index': index, 'step_status': step.get('status')})
    return matches


def summarize(data, conversation):
    trajectory = data.get('trajectory', {})
    executions = trajectory.get('executorMetadatas', [])
    latest = executions[-1] if executions else {}
    planner = latest.get('cascadeConfig', {}).get('plannerConfig', {})
    return {
        'conversation_id': conversation, 'status': data.get('status'),
        'num_total_steps': data.get('numTotalSteps'),
        'loaded_steps': len(trajectory.get('steps', [])),
        'last_step_types': [step.get('type') for step in trajectory.get('steps', [])[-5:]],
        'last_model_name': planner.get('modelName'),
    }


def make_payload(data, conversation, prompt):
    executions = data.get('trajectory', {}).get('executorMetadatas', [])
    if not executions:
        raise ValueError('No previous app execution configuration; this helper supports existing chats only')
    previous = executions[-1]
    payload = {'cascadeId': conversation, 'items': [{'text': prompt}]}
    config = previous.get('requestOverrideConfig')
    spec = previous.get('agentConfigResolution', {}).get('requestedAgentSpec')
    if not config or not spec:
        raise ValueError('Previous UI configuration is incomplete; refusing to guess model or agent settings')
    payload['cascadeConfig'] = config
    payload['customAgentSpec'] = spec
    return payload


def save_receipt(path, receipt):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def send_once(client, conversation, prompt_path, receipt_path, wait_seconds):
    if receipt_path.exists():
        raise ValueError('Receipt already exists. Use verify; do not delete it just to resend.')
    prompt = prompt_path.read_text(encoding='utf-8-sig').strip()
    if not prompt:
        raise ValueError('Prompt file is empty')
    before = client.trajectory(conversation)
    if before.get('status') != 'CASCADE_RUN_STATUS_IDLE':
        raise ValueError('Conversation is not idle; no message was sent')
    prompt_hash = digest(prompt)
    if prompt_matches(before, prompt_hash):
        raise ValueError('This exact prompt is already in the conversation; inspect it before sending again')
    payload = make_payload(before, conversation, prompt)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {'format_version': 1, 'created_at_utc': now(), 'base_url': client.base,
               'conversation_id': conversation, 'prompt_file': str(prompt_path.resolve()),
               'prompt_sha256': prompt_hash, 'prompt_characters': len(prompt),
               'rpc': 'SendUserCascadeMessage', 'steps_before': before.get('numTotalSteps'),
               'state': 'attempt_started'}
    # Exclusive creation protects against launching this command twice at once.
    with receipt_path.open('x', encoding='utf-8') as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=2)
    try:
        result = client.rpc('SendUserCascadeMessage', payload)
    except Exception:
        receipt['state'] = 'outcome_unknown'
        save_receipt(receipt_path, receipt)
        raise RuntimeError('Send outcome is unknown. Use verify with this receipt; do not resend.') from None
    receipt.update(state='accepted', accepted_at_utc=now(), response_keys=list(result))
    save_receipt(receipt_path, receipt)
    return verify_receipt(client, receipt_path, wait_seconds)


def verify_receipt(client, path, wait_seconds):
    receipt = json.loads(path.read_text(encoding='utf-8'))
    conversation = receipt['conversation_id']
    deadline = time.monotonic() + wait_seconds
    while True:
        data = client.trajectory(conversation)
        matches = prompt_matches(data, receipt['prompt_sha256'])
        if matches or time.monotonic() >= deadline:
            break
        time.sleep(min(2, max(0, deadline - time.monotonic())))
    proof = summarize(data, conversation)
    proof.update(prompt_present=bool(matches), matching_user_steps=matches,
                 checked_at_utc=now(), checked_base_url=client.base)
    if matches:
        receipt['state'] = 'confirmed_in_conversation'
    receipt['verification'] = proof
    save_receipt(path, receipt)
    return receipt


def list_chats(state_dir, query):
    path = state_dir / 'conversation_summaries.db'
    if not path.exists():
        raise ValueError('Cannot find app conversation index: ' + str(path))
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as connection:
        connection.row_factory = sqlite3.Row
        records = connection.execute(
            'SELECT conversation_id, title, status, project_id, last_modified_time '
            'FROM conversation_summaries ORDER BY last_modified_time DESC').fetchall()
    return [dict(row) for row in records if not query or query.casefold() in row['title'].casefold()][:30]


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    listing = sub.add_parser('list', help='Read the app conversation index without sending anything')
    listing.add_argument('--query', default='')
    listing.add_argument('--state-dir', type=Path, default=Path.home() / '.gemini/antigravity')
    for action in ('status', 'send', 'verify'):
        command = sub.add_parser(action)
        command.add_argument('--base-url', help='Current HTTPS loopback origin; otherwise read the app log')
        command.add_argument('--log-file', type=Path)
        if action != 'verify':
            command.add_argument('--conversation', required=True)
        if action in ('send', 'verify'):
            command.add_argument('--receipt', type=Path, required=True)
            command.add_argument('--wait-seconds', type=float, default=10)
        if action == 'send':
            command.add_argument('--prompt-file', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == 'list':
            emit(list_chats(args.state_dir.resolve(), args.query))
            return 0
        if hasattr(args, 'wait_seconds') and not 0 <= args.wait_seconds <= 60:
            raise ValueError('--wait-seconds must be between 0 and 60')
        client = AppClient(find_base_url(args.base_url, args.log_file))
        if args.action == 'status':
            emit(summarize(client.trajectory(args.conversation), args.conversation))
        elif args.action == 'send':
            emit(send_once(client, args.conversation, args.prompt_file.resolve(),
                           args.receipt.resolve(), args.wait_seconds))
        else:
            emit(verify_receipt(client, args.receipt.resolve(), args.wait_seconds))
        return 0
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as error:
        emit({'error': str(error), 'action': args.action})
        return 1


if __name__ == '__main__':
    sys.exit(main())
