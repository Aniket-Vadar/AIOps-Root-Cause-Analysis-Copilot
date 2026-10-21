#!/usr/bin/env python3
"""
Baseline Traffic Generator for Agentic AIOps RCA Copilot.
Sends continuous healthy HTTP requests to order-service to generate baseline telemetry.
"""

import sys
import time
import requests
import argparse

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def generate_traffic(target_url: str, interval: float, count: int):
    print(f"[*] Starting baseline traffic generator -> {target_url}")
    print(f"[*] Interval: {interval}s | Total Requests: {'Infinite' if count <= 0 else count}")
    
    sent = 0
    success = 0
    failed = 0
    
    try:
        while count <= 0 or sent < count:
            sent += 1
            try:
                resp = requests.post(f"{target_url}/order", timeout=4.0)
                if resp.status_code == 200:
                    success += 1
                    status_tag = f"[200 OK] Order {resp.json().get('order_id')}"
                else:
                    failed += 1
                    status_tag = f"[{resp.status_code} ERROR] {resp.text[:40]}"
            except requests.exceptions.RequestException as e:
                failed += 1
                status_tag = f"[NET ERR] {type(e).__name__}"
            
            print(f"[{sent:04d}] {status_tag} (Success: {success}, Failed: {failed})")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[!] Traffic generator stopped by user.")

def main():
    parser = argparse.ArgumentParser(description="Baseline Traffic Generator")
    parser.add_argument("--url", default="http://localhost:8001", help="Order service base URL")
    parser.add_argument("--interval", type=float, default=1.5, help="Seconds between requests")
    parser.add_argument("--count", type=int, default=0, help="Total requests to send (0 = infinite)")
    args = parser.parse_args()
    
    generate_traffic(args.url, args.interval, args.count)

if __name__ == "__main__":
    main()
