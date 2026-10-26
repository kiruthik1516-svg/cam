import re

def main():
    try:
        with open("/app/stage2_day02.log", "rb") as f:
            raw = f.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"Error reading log: {e}")
        return

    workers = {}
    for line in raw.split("\n"):
        m = re.search(r"\[Worker (\d+) \| [^\]]+\] (\d+)/(\d+) frames \(([\d\.]+) FPS\) \| Faces: (\d+)", line)
        if m:
            w_id = int(m.group(1))
            workers[w_id] = {
                "done": int(m.group(2)),
                "total": int(m.group(3)),
                "fps": float(m.group(4)),
                "faces": int(m.group(5)),
            }

    if not workers:
        print("No worker progress found yet.")
        return

    total_done = sum(w["done"] for w in workers.values())
    total_frames = sum(w["total"] for w in workers.values())
    total_faces = sum(w["faces"] for w in workers.values())
    agg_fps = sum(w["fps"] for w in workers.values())

    print(f"--- DAY 2 VECTORIZATION LIVE TELEMETRY ---")
    print(f"Total Progress: {total_done}/{total_frames} frames ({total_done/max(1, total_frames)*100:.1f}%)")
    print(f"Aggregate Processing Speed: {agg_fps:.2f} FPS across {len(workers)} workers")
    print(f"Total Faces Extracted & Stored: {total_faces}")
    for w_id in sorted(workers.keys()):
        w = workers[w_id]
        print(f"  Worker {w_id}: {w['done']}/{w['total']} ({w['done']/w['total']*100:.1f}%) @ {w['fps']:.2f} FPS | Faces: {w['faces']}")

if __name__ == "__main__":
    main()

