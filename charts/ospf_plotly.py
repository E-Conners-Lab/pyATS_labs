import json
from pathlib import Path
import pandas as pd
import plotly.express as px

DATA_DIR = Path("outputs/ospf_ops")  # where your multi-device JSONs land
files = sorted(DATA_DIR.glob("*_ospf_ops_*.json"))

def hms_to_seconds(s):
    if not isinstance(s, str) or s.count(":") != 2:
        return None
    h, m, sec = s.split(":")
    return int(h) * 3600 + int(m) * 60 + int(sec)

neighbors = []
lsa_counts = []
spf = []

for f in files:
    dev = f.name.split("_")[0].upper()  # "r1" -> "R1"
    data = json.loads(f.read_text())

    inst = data["vrf"]["default"]["address_family"]["ipv4"]["instance"]
    for inst_id, inst_d in inst.items():
        router_id = inst_d.get("router_id")
        for area_id, area in inst_d.get("areas", {}).items():

            # SPF stats
            stats = area.get("statistics", {}) or {}
            spf.append({
                "device": dev, "router_id": router_id, "area_id": area_id,
                "spf_runs_count": stats.get("spf_runs_count")
            })

            # Neighbors
            for ifname, ifd in (area.get("interfaces", {}) or {}).items():
                for _, nbr in (ifd.get("neighbors", {}) or {}).items():
                    neighbors.append({
                        "device": dev,
                        "router_id": router_id,
                        "area_id": area_id,
                        "interface": ifname,
                        "neighbor_router_id": nbr.get("neighbor_router_id"),
                        "nbr_state": nbr.get("state"),
                        "dead_timer_sec": hms_to_seconds(nbr.get("dead_timer")),
                    })

            # LSAs by type
            lsa_types = (area.get("database", {}) or {}).get("lsa_types", {}) or {}
            for lsa_type, lsa_type_d in lsa_types.items():
                lsas = (lsa_type_d.get("lsas", {}) or {})
                lsa_counts.append({
                    "device": dev,
                    "router_id": router_id,
                    "area_id": area_id,
                    "lsa_type": int(lsa_type),
                    "lsa_count": len(lsas)
                })

df_n = pd.DataFrame(neighbors)
df_l = pd.DataFrame(lsa_counts)
df_s = pd.DataFrame(spf)

# Chart 1: neighbor state counts (stacked)
state_counts = df_n.groupby(["device", "nbr_state"]).size().reset_index(name="count")
fig1 = px.bar(state_counts, x="device", y="count", color="nbr_state",
              title="OSPF Neighbor States per Device")
fig1.show()

# Chart 2: LSA counts by type (grouped)
fig2 = px.bar(df_l, x="device", y="lsa_count", color="lsa_type", barmode="group",
              title="OSPF LSA Counts by Type (per device)")
fig2.show()

# Chart 3: SPF runs (bar)
fig3 = px.bar(df_s, x="device", y="spf_runs_count",
              hover_data=["router_id", "area_id"],
              title="OSPF SPF Runs (per device)")
fig3.show()
