import pandas as pd
from pathlib import Path

# 1. Update Day1_Persona_Video_Clipping_Index.csv
p_clip = Path("D:/facial/Day1_Persona_Video_Clipping_Index.csv")
df_clip = pd.read_csv(p_clip)

if not (df_clip["Event_ID"] == "EVT-D01-009").any():
    new_evt = {
        "Event_ID": "EVT-D01-009",
        "Clip_Filename": "Day_01_Footage",
        "Start_WallClock_Time": "2026-09-01 09:53:20",
        "End_WallClock_Time": "2026-09-01 09:54:15",
        "Buffered_Start_Time": "2026-09-01 09:52:20",
        "Buffered_End_Time": "2026-09-01 09:55:15",
        "Duration_Seconds": 175,
        "Critical_Zone": "Two Multiport Backwash Valves",
        "Hazard_Level": "CRITICAL",
        "Personas_Involved": "OP-VALVE-01",
        "Detections_Count": 28,
        "FFmpeg_Extraction_Command": 'ffmpeg -ss 09:52:20 -to 09:55:15 -i "E:\\RO WATER SEP\\1\\..." -c copy "incident_evidence\\day_01\\Day01_0953_Manual_Incident_Audit.mp4"'
    }
    df_clip = pd.concat([df_clip, pd.DataFrame([new_evt])], ignore_index=True)
    df_clip.sort_values(by="Start_WallClock_Time", inplace=True)
    df_clip.to_csv(p_clip, index=False)
    df_clip.to_csv("D:/facial/incident_evidence/day_01/Day1_Persona_Video_Clipping_Index.csv", index=False)

# 2. Update Day1_Manual_Surveillance_Audit_Sheet.csv (Clip 14)
p_audit = Path("D:/facial/Day1_Manual_Surveillance_Audit_Sheet.csv")
df_audit = pd.read_csv(p_audit)
for col in ["Manual_Human_Present (YES/NO)", "Manual_Start_Player_Time (MM:SS)", "Manual_End_Player_Time (MM:SS)",
            "Manual_Activity_Observed", "Equipment_Touched (Valves/Switch/None)", "Audit_Verdict (MATCH/MISSED/FALSE_ALARM)", "Reviewer_Comments"]:
    df_audit[col] = df_audit[col].astype(object)

mask_c14 = df_audit["Video_File_Name"].astype(str).str.contains("094423")
if mask_c14.any():
    idx = df_audit[mask_c14].index[0]
    df_audit.at[idx, "Manual_Human_Present (YES/NO)"] = "YES"
    df_audit.at[idx, "Manual_Start_Player_Time (MM:SS)"] = "09:00"
    df_audit.at[idx, "Manual_End_Player_Time (MM:SS)"] = "10:00"
    df_audit.at[idx, "Manual_Person_Count"] = 1
    df_audit.at[idx, "Manual_Activity_Observed"] = "Operator entered terrace, turned yellow multiport valve on RO skid deck"
    df_audit.at[idx, "Equipment_Touched (Valves/Switch/None)"] = "Valves (Zone 1A)"
    df_audit.at[idx, "Audit_Verdict (MATCH/MISSED/FALSE_ALARM)"] = "RECOVERED (Manual Sentry Audit)"
    df_audit.at[idx, "Reviewer_Comments"] = "Enrolled as OP-VALVE-01. Continuous incident clip extracted: Day01_0953_Manual_Incident_Audit.mp4"
    df_audit.to_csv(p_audit, index=False)
    df_audit.to_csv("D:/facial/incident_evidence/day_01/Day1_Manual_Surveillance_Audit_Sheet.csv", index=False)
    print(f"[OK] Updated Day 1 Manual Audit Sheet for Clip 14")

# 3. Update extracted_incident_manifest.csv
p_man = Path("D:/facial/incident_evidence/extracted_incident_manifest.csv")
df_man = pd.read_csv(p_man)
if not (df_man["Event_ID"] == "EVT-D01-009").any():
    new_man = {
        "Event_ID": "EVT-D01-009",
        "Day": 1,
        "Hazard_Level": "CRITICAL",
        "Facility_Zone": "Two Multiport Backwash Valves",
        "Personas": "OP-VALVE-01",
        "WallClock_Start": "2026-09-01 09:53:20",
        "WallClock_End": "2026-09-01 09:54:15",
        "Buffered_Start": "2026-09-01 09:52:20",
        "Buffered_End": "2026-09-01 09:55:15",
        "Duration_Sec": 175,
        "Extracted_Clip_File": "D:/facial/incident_evidence/day_01/Day01_0953_Manual_Incident_Audit.mp4",
        "File_Size_MB": 12.8,
        "Status": "EXTRACTED_SUCCESS"
    }
    df_man = pd.concat([df_man, pd.DataFrame([new_man])], ignore_index=True)
    df_man.sort_values(by=["Day", "WallClock_Start"], inplace=True)
    df_man.to_csv(p_man, index=False)
    print(f"[OK] Updated extracted_incident_manifest.csv with EVT-D01-009 (total: {len(df_man)} events)")
