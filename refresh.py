#!/usr/bin/env python3
"""Fetch job data from Feishu Base and update jobs_data.js"""
import json, urllib.request, urllib.error, re, os, sys

TOKEN = os.environ.get("FEISHU_TOKEN", "")
if not TOKEN:
    print("Error: FEISHU_TOKEN not set")
    sys.exit(1)

BASE_TOKEN = "ISNobVuXAagJBFssvszcYeqQnfb"
TABLE_ID = "tblh7J5ONBOMBEK8"
FIELDS = ["公司", "招聘岗位", "简历投递链接", "工作地点", "批次", "开始时间", "截止时间"]

def api_get(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    resp = json.loads(urllib.request.urlopen(req).read())
    if resp.get("code") != 0:
        raise Exception(f"API error: {resp}")
    return resp["data"]

# Fetch all records
field_params = "&".join(f"field_id={f}" for f in FIELDS)
all_records = []
offset = 0
field_names = None
while True:
    url = f"https://open.feishu.cn/open-apis/base/v3/bases/{BASE_TOKEN}/tables/{TABLE_ID}/records?limit=200&offset={offset}&{field_params}"
    data = api_get(url)
    if field_names is None:
        field_names = data["fields"]
    rids = data.get("record_id_list", [])
    for i, row in enumerate(data.get("data", [])):
        rid = rids[i] if i < len(rids) else f"unk_{offset}_{i}"
        rec = {"_id": rid}
        for fi, fn in enumerate(field_names):
            rec[fn] = row[fi] if fi < len(row) else None
        all_records.append(rec)
    if not data.get("has_more"):
        break
    offset += 200
print(f"Total: {len(all_records)} records")

# Process
def fmt_date(v):
    if not v: return ""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(v))
    return m.group(1) if m else str(v)

def fmt_deadline(v):
    if not v: return ""
    s = str(v).strip()
    m = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})", s)
    if m: return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m: return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return s

def clean_link(link):
    if not link: return ""
    m = re.match(r"^\[.*?\]\((.*?)\)$", link.strip())
    if m: return m.group(1)
    m = re.search(r"\[.*?\]\((https?://[^\)]+)\)", link)
    if m: return m.group(1)
    return link.strip()

def clean_loc(loc):
    if isinstance(loc, list): return ", ".join(str(x) for x in loc if x)
    return str(loc) if loc else ""

jobs = []
for r in all_records:
    company = r.get("公司", "")
    if not company or any(x in company for x in ["必看", "如何筛选", "使用说明", "⬆️", "⬇️", "👈"]):
        continue
    position = r.get("招聘岗位", "") or ""
    link = r.get("简历投递链接", "") or ""
    if not position and not link: continue
    batch = r.get("批次", "") or ""
    if isinstance(batch, list): batch = ",".join(batch)
    elif not isinstance(batch, str): batch = str(batch)
    jobs.append([
        r["_id"], company, position, clean_link(link),
        clean_loc(r.get("工作地点", "")), batch,
        fmt_date(r.get("开始时间", "")), fmt_deadline(r.get("截止时间", ""))
    ])

with open("jobs_data.js", "w", encoding="utf-8") as f:
    f.write("const JD=")
    json.dump(jobs, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";")
print(f"Generated {len(jobs)} jobs")
