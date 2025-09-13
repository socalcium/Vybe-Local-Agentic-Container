#!/usr/bin/env python3
"""
Full-app functional tests for Vybe.
Performs a sequence of checks and minimal interactions to validate critical paths.

This is designed to be safe (no heavy jobs). It avoids image/video generation
but validates service status and a minimal chat roundtrip.
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, List, Tuple

import requests


BASE = os.environ.get('VYBE_BASE_URL', 'http://127.0.0.1:8000')


def call(ep: str, method: str = 'GET', payload: Dict[str, Any] | None = None, timeout: int = 12) -> Tuple[bool, int, str]:
    url = f"{BASE}{ep}"
    try:
        if method == 'GET':
            r = requests.get(url, timeout=timeout)
        else:
            r = requests.post(url, json=payload or {}, timeout=timeout)
        return True, r.status_code, r.text
    except Exception as e:
        return False, 0, str(e)


def ensure_backend_running(results: List[Dict[str, Any]]):
    ok, code, text = call('/api/models/backend_status')
    results.append({'endpoint': '/api/models/backend_status', 'ok': ok, 'code': code, 'sample': text[:500]})
    if not ok or code >= 500:
        return False
    if '"running":true' in text.replace(' ', '').lower():
        return True
    _ok, _code, _text = call('/api/models/backend_start', 'POST')
    results.append({'endpoint': '/api/models/backend_start', 'ok': _ok, 'code': _code, 'sample': _text[:500]})
    
    # Poll with exponential backoff
    max_attempts = 10
    base_delay = 0.5
    for attempt in range(max_attempts):
        delay = base_delay * (2 ** min(attempt, 3))  # Cap at 4 second intervals
        time.sleep(delay)
        ok2, code2, text2 = call('/api/models/backend_status')
        if ok2 and '"running":true' in text2.replace(' ', '').lower():
            return True
    return False


def main() -> int:
    results: List[Dict[str, Any]] = []
    print('Running full functional tests...')

    # Splash readiness
    for ep in ('/api/splash/status', '/api/splash/readiness'):
        ok, code, text = call(ep)
        print(f"[{ 'OK' if ok and code < 500 else 'FAIL' }] {ep} -> {code}")
        results.append({'endpoint': ep, 'ok': ok, 'code': code, 'sample': text[:500]})

    # Ensure backend
    backend_ok = ensure_backend_running(results)
    print('Backend ready:', backend_ok)
    if not backend_ok:
        print('Backend failed to start.')
        with open('functional_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        return 2

    # Minimal chat roundtrip (REST)
    ok, code, text = call('/api/chat', 'POST', payload={'message': 'Functional test ping', 'temperature': 0.2})
    print(f"[{ 'OK' if ok and code < 400 else 'FAIL' }] /api/chat -> {code}")
    results.append({'endpoint': '/api/chat', 'ok': ok, 'code': code, 'sample': text[:500]})
    if not ok or code >= 400:
        with open('functional_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        return 3

    # Image/Video status (tolerate disabled)
    for ep in ('/api/images/status', '/api/video/status'):
        ok, code, text = call(ep)
        print(f"[{ 'OK' if ok and code in (200, 400) else 'WARN' }] {ep} -> {code}")
        results.append({'endpoint': ep, 'ok': ok, 'code': code, 'sample': text[:500]})

    # Models endpoints
    for ep in ('/api/models/detailed', '/api/models/recommended'):
        ok, code, text = call(ep)
        print(f"[{ 'OK' if ok and code < 500 else 'FAIL' }] {ep} -> {code}")
        results.append({'endpoint': ep, 'ok': ok, 'code': code, 'sample': text[:500]})

    with open('functional_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print('Functional results written to functional_results.json')
    print('All critical tests passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())


