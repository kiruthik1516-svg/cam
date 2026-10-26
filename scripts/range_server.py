import os
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

class RangeHTTPRequestHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def send_head(self):
        if 'Range' not in self.headers:
            self.range = None
            return super().send_head()

        path = self.translate_path(self.path)
        f = None
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(404, "File not found")
            return None

        fs = os.fstat(f.fileno())
        total_length = fs.st_size

        range_header = self.headers['Range']
        match = re.match(r'bytes=(\d+)-(\d*)', range_header)
        if not match:
            self.send_error(400, "Bad Request")
            return None

        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else total_length - 1
        if start >= total_length:
            self.send_error(416, "Requested Range Not Satisfiable")
            return None

        length = end - start + 1
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', f'bytes {start}-{end}/{total_length}')
        self.send_header('Content-Length', str(length))
        self.end_headers()

        f.seek(start)
        self.range = (start, length)
        return f

    def copyfile(self, source, outputfile):
        if not hasattr(self, 'range') or not self.range:
            return super().copyfile(source, outputfile)
        start, length = self.range
        left = length
        while left > 0:
            chunk = source.read(min(left, 256 * 1024))
            if not chunk:
                break
            try:
                outputfile.write(chunk)
            except (ConnectionResetError, BrokenPipeError):
                break
            left -= len(chunk)

if __name__ == '__main__':
    os.chdir('D:/facial')
    server = ThreadingHTTPServer(('0.0.0.0', 8888), RangeHTTPRequestHandler)
    print("Multi-Threaded Range HTTP Server running on port 8888...")
    server.serve_forever()

