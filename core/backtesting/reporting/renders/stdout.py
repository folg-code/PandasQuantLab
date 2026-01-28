class StdoutRenderer:

    def render(self, report_data: dict):
        print("\n=== GLOBAL RISK METRICS ===")
        for k, v in report_data["global"].items():
            print(f"{k:20s}: {v}")

        for ctx_name, ctx_data in report_data["by_context"].items():
            print(f"\n=== RISK BY {ctx_name.upper()} ===")
            for value, metrics in ctx_data.items():
                print(f"\n[{value}]")
                for m, val in metrics.items():
                    print(f"  {m:18s}: {val}")