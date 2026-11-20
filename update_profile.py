"""Regenerate dark_mode.svg / light_mode.svg with live GitHub stats.

Runs daily via GitHub Actions. Stdlib only, no dependencies.
Layout inspired by github.com/DietrichGebert/DietrichGebert (neofetch-style card).
"""
import calendar
import html
import json
import os
import urllib.request
from datetime import date, datetime, timezone

USER = "cienkowd"
BIRTHDAY = date(2003, 5, 29)
JOINED_YEAR = 2023                # GitHub account creation year
W = 56                            # info column width in characters

ART = r"""

                    -===--====-
                -===+=:-:.:::.--=--
              :-+--=-:.:--:--::-----:
             -------:=-=:--:=-::-===:-
            --:::::-=**+--+-=--=::==-=-
           :-:..--:-++#=+*+=**=-+=+*+--+
           :..++=++*==#**#*##*+#*#@#=+-=
           :.=%##%%%%#%%%%%@@%@@@@@%##+=
           ..##**++==*##%%%###*#%%@@@@=-
           -:#*++++++==*%@%**+*##%%%%@-.
           +=#**++**#***%@@@**+**#%%@%*#=
          =#=###%%%%%%##%@%@@@@@@@@@@%#%=
           %**####%%%#**%%%%%@@@@@@@%##%
           =#+**######--+#*#@%%@@@%%#%@-
             +#****#####%%@@@@%%%%%%%+
              #***#**+***###%%%%%%%@+
              -***##**+***#%%%%%%%@*
                =+*##%%##%%@@@@%#%=
                 +-=+*#%%#%%%%###@:
                 *==------=**##%%@-
                 *++==--+*#%%%%%%%%:
              .-**++*++=*##%%%%%%%#=:-::
          .:::.:*##**#%##%%@@@@%#--=:--:::--:::
 :.:::::::..:--:=-=++*#######*+-::+----::--::::--:
-=--------::.-====..::----==-----+------:--::---::
:+==-:===--=-.-*==+---==++++====+-=--==--=-:-----:
:*=++:++==+=+=.-*++==--=======+=-+=:===:==::=-----
:*+++:=+==++=+=.=*+++++==+++++--+=:===--=-:==-----
:*+=*:=*=+++++*=.+++++++=+++=-=+=:=+==-+-:===---=:
:*+=+:+++++++++*--+*+++++++=-++=:=+====-:=====-=:-
"""

PROFILE = [
    ("OS", "Windows, macOS"),
    ("Host", "Xperi"),
    ("Kernel", "Associate Engineer, SDET"),
    ("Uptime", None),  # filled with age from BIRTHDAY
    ("IDE", "Claude Code, JetBrains IDEs, VS Code"),
    None,
    ("Languages.Programming", "Python, TypeScript, Java, C/C++"),
    ("Languages.Real", "Polish, English"),
    ("Education", "Applied CS @ Warsaw Univ. of Tech."),
    ("Hobbies", "Running, football, finance"),
    None,
    ("Work account", "github.com/dcienkowski"),
]

# Shown only when non-empty, e.g. [("LinkedIn", "in/your-handle"), ("Email", "you@example.com")]
CONTACT = []

TOKEN = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""


def gh(url, payload=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode() if payload else None,
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or "{}")


def graphql(query, variables=None):
    resp = gh("https://api.github.com/graphql", {"query": query, "variables": variables or {}})
    if resp.get("errors"):
        raise RuntimeError(resp["errors"])
    return resp["data"]


def duration(start, today):
    years = today.year - start.year - ((today.month, today.day) < (start.month, start.day))
    months = (today.month - start.month - (today.day < start.day)) % 12
    if today.day >= start.day:
        days = today.day - start.day
    else:
        pm_year, pm = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
        days = calendar.monthrange(pm_year, pm)[1] - start.day + today.day
    return years, months, days


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def fetch_stats():
    years = "\n".join(
        f'y{y}: contributionsCollection(from: "{y}-01-01T00:00:00Z", to: "{y + 1}-01-01T00:00:00Z")'
        " { totalCommitContributions restrictedContributionsCount }"
        for y in range(JOINED_YEAR, datetime.now(timezone.utc).year + 1)
    )
    contrib = graphql(f'query {{ user(login: "{USER}") {{ {years} }} }}')["user"]
    commits = sum(v["totalCommitContributions"] + v["restrictedContributionsCount"] for v in contrib.values())

    u = graphql(f"""
    query {{
      user(login: "{USER}") {{
        id
        repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {{
          nodes {{
            name
          }}
        }}
      }}
    }}""")["user"]
    repos = [n for n in u["repositories"]["nodes"] if n["name"] != USER]

    stats = {"repos": len(repos), "commits": commits}
    stats.update(loc([r["name"] for r in repos], u["id"]))
    return stats


LOC_QUERY = """
query($owner: String!, $name: String!, $id: ID!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    defaultBranchRef { target { ... on Commit {
      history(first: 100, author: {id: $id}, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes { additions deletions }
      }
    } } }
  }
}"""


def loc(repo_names, user_id):
    add = rem = 0
    for name in repo_names:
        cursor = None
        try:
            while True:
                ref = graphql(LOC_QUERY, {"owner": USER, "name": name, "id": user_id, "cursor": cursor})["repository"]["defaultBranchRef"]
                if ref is None:
                    break
                h = ref["target"]["history"]
                add += sum(n["additions"] for n in h["nodes"])
                rem += sum(n["deletions"] for n in h["nodes"])
                if not h["pageInfo"]["hasNextPage"]:
                    break
                cursor = h["pageInfo"]["endCursor"]
        except Exception as e:
            print(f"loc {name}: {e}")
    return {"loc_add": add, "loc_del": rem, "loc": add - rem}


PALETTES = {
    "dark": {"bg": "#0d1117", "border": "#30363d", "art": "#8b949e", "h": "#58a6ff",
             "k": "#ffa657", "v": "#c9d1d9", "d": "#484f58", "g": "#3fb950", "r": "#f85149"},
    "light": {"bg": "#ffffff", "border": "#d0d7de", "art": "#57606a", "h": "#0969da",
              "k": "#953800", "v": "#24292f", "d": "#afb8c1", "g": "#1a7f37", "r": "#cf222e"},
}


def kv(key, val, width=W):
    dots = "." * max(width - len(key) - len(str(val)) - 3, 1)
    return [(f"{key}: ", "k"), (dots + " ", "d"), (str(val), "v")]


def kv2(k1, v1, k2, v2):
    return kv(k1, v1, 26) + [(" | ", "d")] + kv(k2, v2, W - 29)


def rule(title=""):
    label = f"─ {title} " if title else ""
    return [(label, "h"), ("─" * (W - len(label)), "d")]


def info_lines(s):
    y, m, d = duration(BIRTHDAY, date.today())
    uptime = f"{plural(y, 'year')}, {plural(m, 'month')}, {plural(d, 'day')}"
    n = lambda x: f"{x:,}"
    lines = [[(f"{USER}@github ", "h"), ("─" * (W - len(USER) - 8), "d")], []]
    for item in PROFILE:
        if item is None:
            lines.append([])
        else:
            key, val = item
            lines.append(kv(key, uptime if key == "Uptime" else val))
    if CONTACT:
        lines += [[], rule("Contact")] + [kv(k, v) for k, v in CONTACT]
    lines += [
        [],
        rule("GitHub Stats"),
        kv2("Repos", s["repos"], "Commits", n(s["commits"])),
        [("Lines of Code: ", "k"), (n(s["loc"]), "v"), (" ( ", "d"),
         (n(s["loc_add"]) + "++", "g"), (", ", "d"), (n(s["loc_del"]) + "--", "r"), (" )", "d")],
    ]
    return lines


def render(mode, stats):
    p = PALETTES[mode]
    art = ART.strip("\n").split("\n")
    info = info_lines(stats)
    height = max(40 + len(art) * 15, 45 + len(info) * 21) + 25
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="840" height="{height}" viewBox="0 0 840 {height}" '
        'font-family="Consolas, Menlo, monospace" font-size="13px">',
        f'<rect x="0.5" y="0.5" width="839" height="{height - 1}" rx="10" fill="{p["bg"]}" stroke="{p["border"]}"/>',
    ]
    for i, line in enumerate(art):
        out.append(f'<text x="20" y="{40 + i * 15}" fill="{p["art"]}" xml:space="preserve">{html.escape(line)}</text>')
    for i, segs in enumerate(info):
        if not segs:
            continue
        spans = "".join(f'<tspan fill="{p[c]}">{html.escape(t)}</tspan>' for t, c in segs)
        out.append(f'<text x="400" y="{45 + i * 21}" xml:space="preserve">{spans}</text>')
    out.append("</svg>")
    return "\n".join(out)


def selfcheck():
    assert duration(date(2003, 5, 29), date(2026, 11, 20)) == (23, 5, 22)
    assert duration(date(2003, 5, 29), date(2026, 5, 29)) == (23, 0, 0)
    assert duration(date(2000, 3, 31), date(2026, 4, 1)) == (26, 0, 1)
    assert len("".join(t for t, _ in kv("OS", "Windows, Linux"))) == W
    assert len("".join(t for t, _ in kv2("Repos", 9, "Commits", "1,234"))) == W


if __name__ == "__main__":
    selfcheck()
    stats = fetch_stats()
    print("stats:", stats)
    for mode in PALETTES:
        with open(f"{mode}_mode.svg", "w", encoding="utf-8") as f:
            f.write(render(mode, stats))
    print("wrote dark_mode.svg, light_mode.svg")
