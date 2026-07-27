import json
import os
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

# Repos to monitor (owner/repo)
REPOS = [
    "sndsh404/summer-2027-internships",
    "northwesternfintech/2027QuantInternships",
    "zapplyjobs/Research-Internships-for-Undergraduates",
    "acmalexandria/internships",
    "SimplifyJobs/Summer2026-Internships",
    "vanshb03/Summer2027-Internships",
]

# Only notify when a new line contains one of these (case-insensitive). also note I am interested in aerospace + embedded
KEYWORDS = [
    "firmware", "embedded", "hardware", "pcb", "fpga", "asic", "rtl",
    "electrical", "avionics", "circuit", "semiconductor", "verilog",
    "vhdl", "chip design", "analog", "mixed signal",
    "rtos", "microcontroller", "schematic", "altium", "layout engineer", 
    "flight software", "guidance navigation", "satellite", "spacecraft", "propulsion",
    "power electronics", "battery management", "bms", "motor controller", "inverter",
    "electrical engineer intern", "hardware engineer intern", "swe", "software engineer intern", 
    "software engineering intern", "swe intern", "full stack", "software developer intern",
]

# Your ntfy.sh topic - install the ntfy app and subscribe to this exact topic name
NTFY_TOPIC = "sophia-hwfw-intern-x7k2p9"

STATE_FILE = "state.json"
BRANCHES_TO_TRY = ["main", "dev", "master"]


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "internship-notifier"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_readme(repo, known_branch=None):
    # try the branch that worked last time first, so most runs make one request instead of up to three
    branches = [known_branch] + [b for b in BRANCHES_TO_TRY if b != known_branch] if known_branch else BRANCHES_TO_TRY
    for branch in branches:
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/README.md"
        try:
            return http_get(url), branch
        except urllib.error.HTTPError as e:
            if e.code != 404:
                print(f"{repo}@{branch}: HTTP {e.code}")
        except urllib.error.URLError as e:
            print(f"{repo}@{branch}: {e}")
    print(f"Could not fetch README for {repo}")
    return None, None


def extract_rows(text):
    lines = [l.strip() for l in text.splitlines()]
    return [l for l in lines if l.startswith("|") or l.startswith("- ") or l.startswith("* ")]


def matches_keywords(line):
    low = line.lower()
    return any(k in low for k in KEYWORDS)


def send_notification(repo, row):
    title = f"New role: {repo.split('/')[-1]}"
    message = row[:250]
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": title.encode("utf-8"), "Priority": "default"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=20)


def process_repo(repo, state):
    known_branch = state.get(repo, {}).get("branch") if isinstance(state.get(repo), dict) else None
    text, branch = fetch_readme(repo, known_branch)
    return repo, text, branch


def main():
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)

    new_state = {}

    with ThreadPoolExecutor(max_workers=len(REPOS)) as pool:
        results = pool.map(lambda repo: process_repo(repo, state), REPOS)

    for repo, text, branch in results:
        if text is None:
            # keep old state for this repo if fetch failed
            if repo in state:
                new_state[repo] = state[repo]
            continue

        rows = extract_rows(text)
        old_entry = state.get(repo)
        old_rows = set(old_entry["rows"] if isinstance(old_entry, dict) else old_entry or [])
        new_state[repo] = {"branch": branch, "rows": rows}

        is_first_run_for_repo = old_entry is None
        if is_first_run_for_repo:
            # seed state only, don't spam notifications on first run
            continue

        added = [r for r in rows if r not in old_rows]

        for row in added:
            if matches_keywords(row):
                send_notification(repo, row)

    with open(STATE_FILE, "w") as f:
        json.dump(new_state, f)


if __name__ == "__main__":
    main()
