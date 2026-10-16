import argparse
import threading
import webbrowser
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Local recording review')
    parser.add_argument('action', choices=['prepare', 'serve', 'open'])
    parser.add_argument('--root', type=Path, default=Path('/Volumes/T7/Wingbeats detector'))
    parser.add_argument('--batch', default='waterfowl-pilot-2026-10-16')
    parser.add_argument('--port', type=int, default=8877)
    parser.add_argument('--open-browser', action='store_true')
    args = parser.parse_args()
    if Path(args.batch).name != args.batch:
        parser.error('--batch must be a folder name')
    if args.action == 'prepare':
        from .prepare import prepare
        prepare(args.root, args.batch)
    elif args.action == 'open':
        import json
        import subprocess
        import sys
        import time
        import urllib.request
        url = f'http://127.0.0.1:{args.port}'
        def ready():
            try:
                with urllib.request.urlopen(url + '/api/batch', timeout=1) as response:
                    data = json.load(response)
                if data.get('batch_id') != args.batch:
                    raise RuntimeError('This port is serving another review batch; choose another --port')
                return True
            except (OSError, ValueError):
                return False
        if not ready():
            batch = args.root / 'reviews' / args.batch
            if not (batch / 'batch.json').is_file():
                parser.error('Prepared batch not found; connect the T7 first')
            with (batch / 'server.log').open('a') as log:
                process = subprocess.Popen([sys.executable, '-m', 'nfc_tools.review', 'serve',
                    '--root', str(args.root), '--batch', args.batch, '--port', str(args.port)],
                    stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
            (batch / 'server.pid').write_text(str(process.pid))
            for _ in range(50):
                if process.poll() is not None:
                    raise RuntimeError('Review server could not start. See server.log in the batch folder.')
                if ready():
                    break
                time.sleep(.1)
            else:
                process.terminate()
                raise RuntimeError('Review server did not become ready; inspect server.log')
        if args.open_browser:
            webbrowser.open(url)
        print(url)
    else:
        import uvicorn
        from .server import create_app
        app = create_app(args.root, args.root / 'reviews' / args.batch)
        if args.open_browser:
            threading.Timer(1, lambda: webbrowser.open(f'http://127.0.0.1:{args.port}')).start()
        uvicorn.run(app, host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
