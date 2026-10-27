import pandas as pd
from pathlib import Path

active_days = [1, 2, 3, 4, 7, 10, 16, 18, 19, 23, 26, 30]

print(f"{'Day':<8} | {'Date':<10} | {'Start Time':<10} | {'End Time':<10} | {'Critical Zone':<30} | {'Subject Tag'}")
print("-" * 95)

for d in active_days:
    f = Path(f"D:/facial/Day{d}_Persona_Video_Clipping_Index.csv")
    if f.exists():
        df = pd.read_csv(f)
        for _, r in df.iterrows():
            st = str(r.get('Start_WallClock_Time', ''))
            et = str(r.get('End_WallClock_Time', ''))
            time_s = st.split(' ')[1] if ' ' in st else st
            time_e = et.split(' ')[1] if ' ' in et else et
            date_s = st.split(' ')[0] if ' ' in st else f"2026-09-{d:02d}"
            
            # Morning window 07:00 - 12:30
            if any(time_s.startswith(h) for h in ['07:', '08:', '09:', '10:', '11:', '12:']):
                print(f"Day {d:02d}   | {date_s:<10} | {time_s:<10} | {time_e:<10} | {str(r.get('Critical_Zone')):<30} | {r.get('Personas_Involved')}")

