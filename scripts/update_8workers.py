with open('scripts/stage2_cloud_worker.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update threads in worker
text = text.replace('os.environ["OMP_NUM_THREADS"] = "2"', 'os.environ["OMP_NUM_THREADS"] = "1"\n    os.environ["ONNXRUNTIME_NUM_THREADS"] = "1"')
text = text.replace('os.environ["OPENBLAS_NUM_THREADS"] = "2"', 'os.environ["OPENBLAS_NUM_THREADS"] = "1"')
text = text.replace('os.environ["MKL_NUM_THREADS"] = "2"', 'os.environ["MKL_NUM_THREADS"] = "1"')

# 2. Update det-size parser
old_parser = """    parser.add_argument(
        "--det-size",
        type=int,
        default=640,
        help="SCRFD detection dimension (default: 640)",
    )"""

new_parser = """    parser.add_argument(
        "--det-size",
        type=int,
        nargs="+",
        default=[1280, 800],
        help="SCRFD detection dimension (default: 1280 800 for native 1:1 scale)",
    )"""

if old_parser in text:
    text = text.replace(old_parser, new_parser)

# 3. Handle det_size tuple in main
old_main = """    engine = create_engine(args.db_url)
    ensure_camera_exists(engine, args.camera_id)

    app = None
    if args.workers <= 1:
        app = load_insightface_app(device_id=0, det_size=(args.det_size, args.det_size))"""

new_main = """    det_size = tuple(args.det_size) if len(args.det_size) == 2 else (args.det_size[0], args.det_size[0])

    engine = create_engine(args.db_url)
    ensure_camera_exists(engine, args.camera_id)

    app = None
    if args.workers <= 1:
        app = load_insightface_app(device_id=0, det_size=det_size)"""

if old_main in text:
    text = text.replace(old_main, new_main)

text = text.replace("det_size=(args.det_size, args.det_size)", "det_size=det_size")
text = text.replace('f"# Detection Size:    ({args.det_size}, {args.det_size})"', 'f"# Detection Size:    {det_size}"')

with open('scripts/stage2_cloud_worker.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated stage2_cloud_worker.py successfully")

