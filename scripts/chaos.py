#!/usr/bin/env python3
"""
Chaos Engineering CLI for Agentic AIOps RCA Copilot.
Injects deterministic faults into target microservices to simulate real incidents.
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

ORDER_SVC = "http://localhost:8001"
PAYMENT_SVC = "http://localhost:8002"

def print_banner(text: str):
    print("\n" + "=" * 65)
    print(f" 🔥 CHAOS DRILL: {text}")
    print("=" * 65)

def inject_downstream_latency(payment_url: str, delay: float = 5.0):
    print_banner(f"Scenario 1 - Downstream Payment Latency ({delay}s)")
    print(f"[*] Calling {payment_url}/chaos/latency?delay={delay}...")
    try:
        r = requests.post(f"{payment_url}/chaos/latency", params={"delay": delay}, timeout=5.0)
        print(f"[+] Status: {r.status_code} | {r.json()}")
        print("[!] Injected artificial latency. Order service requests will now experience 504 timeouts.")
        print("[*] To verify, send a request: curl -X POST http://localhost:8001/order")
    except Exception as e:
        print(f"[-] Failed to inject latency: {e}")

def inject_error_spike(payment_url: str, order_url: str):
    print_banner("Scenario 2 - Database Deadlock & 500 Error Cascade")
    print(f"[*] Enabling 100% error rate on {payment_url}/chaos/error...")
    try:
        r = requests.post(f"{payment_url}/chaos/error", params={"rate": 1.0}, timeout=5.0)
        print(f"[+] Status: {r.status_code} | {r.json()}")
        print("[*] Triggering an immediate unhandled fail-fast order transaction...")
        r2 = requests.post(f"{order_url}/order/fail-fast", timeout=5.0)
        print(f"[+] Order fail-fast response: {r2.status_code}")
    except Exception as e:
        print(f"[-] Fault triggered (expected failure observed): {e}")
    print("[!] High error rate active. Loki logs will capture Python tracebacks.")

def inject_resource_exhaustion(payment_url: str, duration: int = 12):
    print_banner(f"Scenario 3 - CPU Saturation ({duration}s)")
    print(f"[*] Calling {payment_url}/chaos/resource?duration={duration}...")
    try:
        r = requests.post(f"{payment_url}/chaos/resource", params={"duration": duration}, timeout=duration + 5)
        print(f"[+] Status: {r.status_code} | {r.json()}")
    except Exception as e:
        print(f"[-] Failed to trigger CPU burn: {e}")

def reset_all(payment_url: str):
    print_banner("Resetting All Chaos Faults")
    try:
        r = requests.post(f"{payment_url}/chaos/reset", timeout=5.0)
        print(f"[+] Status: {r.status_code} | System restored to healthy baseline: {r.json()}")
    except Exception as e:
        print(f"[-] Failed to reset faults: {e}")

def main():
    parser = argparse.ArgumentParser(description="Deterministic Chaos Fault Injector")
    parser.add_argument(
        "--scenario",
        choices=["1", "2", "3", "latency", "error", "resource", "reset"],
        required=True,
        help="1/latency: Downstream Delay, 2/error: 500 Spike, 3/resource: CPU Burn, reset: Restore healthy"
    )
    parser.add_argument("--delay", type=float, default=5.0, help="Latency in seconds for Scenario 1")
    parser.add_argument("--duration", type=int, default=12, help="Resource burn duration for Scenario 3")
    parser.add_argument("--payment-url", default=PAYMENT_SVC, help="Payment service base URL")
    parser.add_argument("--order-url", default=ORDER_SVC, help="Order service base URL")
    args = parser.parse_args()

    choice = args.scenario.lower()
    if choice in ["1", "latency"]:
        inject_downstream_latency(args.payment_url, args.delay)
    elif choice in ["2", "error"]:
        inject_error_spike(args.payment_url, args.order_url)
    elif choice in ["3", "resource"]:
        inject_resource_exhaustion(args.payment_url, args.duration)
    elif choice == "reset":
        reset_all(args.payment_url)

if __name__ == "__main__":
    main()
