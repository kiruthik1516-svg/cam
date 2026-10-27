import pandas as pd
from pathlib import Path

df = pd.read_csv("D:/facial/incident_evidence/extracted_incident_manifest.csv")
print("=== ALL 5 SEVERE INCIDENTS (Zone 2 Power Switch) ===")
for _, r in df[df["Hazard_Level"] == "SEVERE"].iterrows():
    print(f"Day {r['Day']:02d} ({r['WallClock_Start']}) | Event: {r['Event_ID']} | Duration: {r['Duration_Sec']}s | Subjects: {r['Personas']}")

print("\n=== CRITICAL INCIDENTS (Zone 1A/B Multiport Valves) DISTRIBUTION ===")
print("Total Critical Events:", len(df[df["Hazard_Level"] == "CRITICAL"]))
df["Week"] = (df["Day"] - 1) // 7 + 1
for w, wdf in df[df["Hazard_Level"] == "CRITICAL"].groupby("Week"):
    days = sorted(wdf["Day"].unique())
    print(f"Week {w} (Days {days[0]:02d}-{days[-1]:02d}): {len(wdf)} events across days {days}")

print("\n=== MULTI-PERSON HIGH-ACTIVITY VALVE DAYS ===")
crit = df[df["Hazard_Level"] == "CRITICAL"]
for day, ddf in crit.groupby("Day"):
    if len(ddf) >= 3:
        all_p = set()
        for p_list in ddf["Personas"].dropna():
            all_p.update(p_list.split(";"))
        print(f"Day {day:02d}: {len(ddf)} critical events, {len(all_p)} distinct unknown subjects ({', '.join(sorted(all_p)[:5])}...)")

print("\n=== 30-DAY TIMELINE SPAN ===")
print("First event:", df.iloc[0]["WallClock_Start"], "Day", df.iloc[0]["Day"])
print("Last event:", df.iloc[-1]["WallClock_Start"], "Day", df.iloc[-1]["Day"])

