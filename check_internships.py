import requests
import os
import json

# Repos to monitor (owner/repo)
REPOS = [
    "sndsh404/summer-2027-internships",
    "northwesternfintech/2027QuantInternships",
    "zapplyjobs/Research-Internships-for-Undergraduates",
    "acmalexandria/internships",
    "SimplifyJobs/Summer2026-Internships",
    "vanshb03/Summer2027-Internships",
]

# Only notify when a new line contains one of these (case-insensitive)
KEYWORDS = [
    "firmware", "embedded", "hardware", "pcb", "fpga", "asic", "rtl",
    "electrical", "avionics", "circuit", "semiconductor", "verilog",
    "vhdl", "chip design", "analog", "mixed signal",
]

# Your ntfy.sh topic - install the ntfy app and subscribe to this exact topic name
NTFY_TOPIC = "sophia-hwfw-intern-x7k2p9"

STATE_FILE = "state.json"
BRANCHES_TO_TRY = ["main", "dev", "master"]


def fetch_readme(repo):
    for branch in BRANCHES_TO_TRY:
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/README.md"
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            return r.text
    print(f"Could not fetch README for {repo}")
    return None


def extract_rows(text):
    lines = [l.strip() for l in text.splitlines()]
    return [l for l in lines if l.startswith("|") or l.startswith("- ") or l.startswith("* ")]


def matches_keywords(line):
    low = line.lower()
    return any(k in low for k in KEYWORDS)


def send_notification(repo, row):
    title = f"New role: {repo.split('/')[-1]}"
    message = row[:250]
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": title.encode("utf-8"), "Priority": "default"},
    )


def main():
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)

    new_state = {}

    for repo in REPOS:
        text = fetch_readme(repo)
        if text is None:
            # keep old state for this repo if fetch failed
            if repo in state:
                new_state[repo] = state[repo]
            continue

        rows = extract_rows(text)
        new_state[repo] = rows

        is_first_run_for_repo = repo not in state
        if is_first_run_for_repo:
            # seed state only, don't spam notifications on first run
            continue

        old_rows = set(state[repo])
        added = [r for r in rows if r not in old_rows]

        for row in added:
            if matches_keywords(row):
                send_notification(repo, row)

    with open(STATE_FILE, "w") as f:
        json.dump(new_state, f)


if __name__ == "__main__":
    main()
