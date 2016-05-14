import http.server
import socketserver
from urllib.parse import urlparse
import json
from searchPath import searchPath
PORT = 80

# arguments are two ints
# returns a str
def solve(id1, id2):
    paths = searchPath(id1,id2)
    return json.dumps(paths)

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        if parsed_url.path == '/semifinal':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            query = dict(kv_pair.split('=') for kv_pair in parsed_url.query.split('&'))
            id1 = int(query['id1'])
            id2 = int(query['id2'])
            result = solve(id1, id2)
            self.wfile.write(result.encode('utf-8'))

httpd = socketserver.TCPServer(('', PORT), Handler)

print('serving at port', PORT)
httpd.serve_forever()
