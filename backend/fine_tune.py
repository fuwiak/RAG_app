import sys
import time
import json


def main():
    config = sys.argv[1] if len(sys.argv) > 1 else "{}"
    for i in range(1, 6):
        payload = {"step": i, "message": f"Step {i} completed"}
        print(json.dumps(payload), flush=True)
        time.sleep(1)


if __name__ == "__main__":
    main()
