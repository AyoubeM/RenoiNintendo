import asyncio
import json
from http.server import BaseHTTPRequestHandler
from cron_check import run_cron_analysis


class handler(BaseHTTPRequestHandler):
    """Handler Vercel Serverless pour déclencher l'analyse de tous les prix."""

    def do_GET(self):
        try:
            result = asyncio.run(run_cron_analysis())
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "error": str(e)}).encode("utf-8"))

    def do_POST(self):
        self.do_GET()


app = handler
