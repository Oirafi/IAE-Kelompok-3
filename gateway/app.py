import os
from dotenv import load_dotenv
import requests
from flask import Flask, request, Response
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)

# Service URLs
SERVICES = {
    '/api/auth':       os.getenv('AUTH_SERVICE_URL',      'http://auth-service:3001'),
    '/api/courts':     os.getenv('COURT_SERVICE_URL',     'http://court-service:3002'),
    '/api/bookings':   os.getenv('BOOKING_SERVICE_URL',   'http://booking-service:3003'),
    '/api/equipments': os.getenv('EQUIPMENT_SERVICE_URL', 'http://equipment-service:3004'),
    '/api/payments':   os.getenv('PAYMENT_SERVICE_URL',   'http://payment-service:3005'),
}


def _proxy(prefix, target_url):
    """Generic proxy function — strips the prefix and forwards to target."""
    path = request.full_path[len(prefix):]  # remove prefix, keep query string
    if not path or path == '?':
        path = '/'
    url = target_url.rstrip('/') + path

    # Forward the request
    resp = requests.request(
        method=request.method,
        url=url,
        headers={k: v for k, v in request.headers if k.lower() != 'host'},
        data=request.get_data(),
        params=request.args,
        allow_redirects=False,
        timeout=30
    )

    # Build the response
    excluded_headers = {'content-encoding', 'content-length', 'transfer-encoding', 'connection'}
    headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded_headers}
    return Response(resp.content, status=resp.status_code, headers=headers)


# Register one route per service prefix, forwarding all HTTP methods
for prefix, target in SERVICES.items():
    # Capture via default arg to avoid late-binding closure issue
    def make_proxy(p, t):
        def proxy_view(**kwargs):
            return _proxy(p, t)
        proxy_view.__name__ = f'proxy_{p.replace("/", "_")}'
        return proxy_view

    app.add_url_rule(
        prefix,
        view_func=make_proxy(prefix, target),
        methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS']
    )
    app.add_url_rule(
        prefix + '/<path:subpath>',
        view_func=make_proxy(prefix, target),
        methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS']
    )


@app.route('/health')
def health():
    return {'status': 'Gateway OK'}


if __name__ == '__main__':
    PORT = int(os.getenv('PORT', 3000))
    print(f'API Gateway running on port {PORT}')
    app.run(host='0.0.0.0', port=PORT)
