import http.server
import socketserver
from urllib.parse import urlparse
import json

PORT = 80

# arguments are two ints
# returns a str
def solve(id1, id2):
    return json.dumps([id1, id2])

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        print('Got a request:', self.path)
        parsed_url = urlparse(self.path)
        if parsed_url.path == '/semifinal':
            self.send_response(200)
            self.send_header('Content-type', 'text/json')
            self.end_headers()
            id1, id2 = [int(kv_pair[4:]) for kv_pair in parsed_url.query.split('&')]
            result = solve(id1, id2)
            print(result)
            self.wfile.write(result.encode('utf-8'))

httpd = socketserver.TCPServer(('', PORT), Handler)

print('serving at port', PORT)
httpd.serve_forever()
