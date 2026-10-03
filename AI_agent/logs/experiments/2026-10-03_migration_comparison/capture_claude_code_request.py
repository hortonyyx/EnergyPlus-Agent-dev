"""Record which thinking/effort fields Claude Code sends to the GLM Anthropic-compatible endpoint.

The 10-02 baseline ran Claude Code with ``--effort medium`` through Zhipu's Anthropic-compatible
endpoint; how that reaches the service was never captured. This local relay forwards one Claude Code
request unchanged to ``GLM_ANTHROPIC_BASE_URL`` and saves the request body (headers other than auth
names are kept, auth values never), so the new runtime can be set to the same thinking level.

Usage: ``python capture_claude_code_request.py --port 18765`` in one shell, then run Claude Code with
``ANTHROPIC_BASE_URL=http://127.0.0.1:18765``. The relay exits after ``--max-requests`` requests.
"""
import argparse
import http.server
import json
from pathlib import Path
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = HERE / "evidence/claude_code_request_capture"
SECRET = {"authorization", "x-api-key"}


def upstream_base():
    from dotenv import dotenv_values
    values = dotenv_values(ROOT / ".env", interpolate=False)
    return values["GLM_ANTHROPIC_BASE_URL"].rstrip("/")


class Relay(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"  # close after each response; SSE is relayed until upstream ends

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        index = len(list(OUT.glob("request_*.json"))) + 1
        try:
            parsed = json.loads(body)
        except ValueError:
            parsed = {"unparsed_bytes": len(body)}
        headers = {k: ("<redacted>" if k.lower() in SECRET else v) for k, v in self.headers.items()}
        (OUT / f"request_{index:02d}.json").write_text(json.dumps(
            dict(path=self.path, headers=headers, body=parsed), ensure_ascii=False, indent=1) + "\n")
        forward = {k: v for k, v in self.headers.items() if k.lower() not in {"host", "content-length", "accept-encoding"}}
        request = urllib.request.Request(self.server.upstream + self.path, data=body, method="POST", headers=forward)
        try:
            response = urllib.request.urlopen(request, timeout=600)
            status, reply_headers = response.status, response.getheaders()
        except urllib.error.HTTPError as error:
            response, status, reply_headers = error, error.code, error.headers.items()
        self.send_response(status)
        for key, value in reply_headers:
            if key.lower() not in {"transfer-encoding", "content-length", "connection", "content-encoding"}:
                self.send_header(key, value)
        self.end_headers()
        while chunk := response.read(4096):
            self.wfile.write(chunk)
            self.wfile.flush()
        self.server.handled += 1

    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18765)
    parser.add_argument("--max-requests", type=int, default=4)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Relay)
    server.upstream, server.handled = upstream_base(), 0
    server.timeout = 1
    while server.handled < args.max_requests:
        server.handle_request()


if __name__ == "__main__":
    main()
