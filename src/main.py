from agent.graph import build_graph
from logger import HistoryLogger
import os
import re
import argparse
import sys

def load_input_file(path: str) -> str:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Input file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Rust ICE Minimizer Agent"
    )
    parser.add_argument(
        "input_file",
        help="Path to the input document containing trigger code"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("🚀 Starting Rust ICE-Triggering Code Simiplifier...")
    print(f"Input file: {args.input_file}")

    try:
        input_doc = load_input_file(args.input_file)
    except Exception as e:
        print(f"❌ Failed to load input file: {e}")
        sys.exit(1)

    issue_id = os.path.splitext(os.path.basename(args.input_file))[0]

    output_dir = os.path.join("output", issue_id)
    os.makedirs(output_dir, exist_ok=True)
    logger = HistoryLogger()
    app = build_graph()

    inputs = {"input_doc": input_doc, "issue_id": issue_id}

    final_best_code = None

    try:
        for output in app.stream(inputs, config={"recursion_limit": 100}):
            for node_name, state_update in output.items():
                print(f"\n--- Node: {node_name} ---")
                if isinstance(state_update, dict):
                    if "logs" in state_update:
                        for log in state_update["logs"]:
                            logger.add_log(f"[{node_name}] {log}")
                            print(f"📄 {log}")

                    if "failed_attempts" in state_update and state_update["failed_attempts"]:
                        latest_diff = state_update["failed_attempts"][-1]
                        logger.add_failed_diff(latest_diff)

                    if "best_code" in state_update:
                        final_best_code = state_update["best_code"]
                        logger.set_final_code(final_best_code)
                        print(f"🎯 New Best Code Found! Length: {len(final_best_code)}")

            output_path = os.path.join(output_dir, "minimized_code.rs")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_best_code)

    except Exception as e:
        logger.add_log(f"ERROR: {str(e)}")
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()

    finally:
        logger.save_to_file(os.path.join(output_dir, "agent_history.log"), 
                            os.path.join(output_dir, "failed_simplifications.log"))
        

if __name__ == "__main__":
    main()
