"""
MCP (Model Context Protocol) server integration for Azure DNS Manager.

Implements JSON-RPC over SSE transport directly in Flask,
no external MCP SDK dependency required.
"""

import json
import uuid
import hmac
import queue
import threading

from flask import request, jsonify, Response

# ---------------------------------------------------------------------------
# Tool catalogue
# ---------------------------------------------------------------------------

MCP_TOOLS = [
    {
        "name": "list_records",
        "description": "List all DNS records in the configured Azure DNS zone",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "create_record",
        "description": "Create a new DNS record in the Azure DNS zone",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Record name (subdomain) or @ for the root domain"
                },
                "type": {
                    "type": "string",
                    "description": "DNS record type",
                    "enum": ["A", "AAAA", "CNAME", "MX", "TXT"]
                },
                "values": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Record values (IP addresses, hostnames, etc.)"
                },
                "ttl": {
                    "type": "integer",
                    "description": "TTL in seconds (default 3600)",
                    "default": 3600
                }
            },
            "required": ["name", "type", "values"]
        }
    },
    {
        "name": "update_record",
        "description": "Update an existing DNS record in the Azure DNS zone",
        "inputSchema": {
            "type": "object",
            "properties": {
                "record_type": {
                    "type": "string",
                    "description": "DNS record type",
                    "enum": ["A", "AAAA", "CNAME", "MX", "TXT"]
                },
                "record_name": {
                    "type": "string",
                    "description": "Current record name (subdomain) or @ for root"
                },
                "values": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New record values"
                },
                "ttl": {
                    "type": "integer",
                    "description": "TTL in seconds (default 3600)",
                    "default": 3600
                },
                "new_name": {
                    "type": "string",
                    "description": "New record name if renaming (optional)"
                }
            },
            "required": ["record_type", "record_name", "values"]
        }
    },
    {
        "name": "delete_record",
        "description": "Delete a DNS record from the Azure DNS zone",
        "inputSchema": {
            "type": "object",
            "properties": {
                "record_type": {
                    "type": "string",
                    "description": "DNS record type",
                    "enum": ["A", "AAAA", "CNAME", "MX", "TXT"]
                },
                "record_name": {
                    "type": "string",
                    "description": "Record name (subdomain) or @ for root"
                }
            },
            "required": ["record_type", "record_name"]
        }
    },
    {
        "name": "health_check",
        "description": "Check the health status of the Azure DNS Manager and return the configured zone",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _tool_list_records():
    from app import get_dns_client, config, is_config_complete

    if not is_config_complete():
        return {"error": "Azure configuration is incomplete. Please configure credentials first."}

    try:
        client = get_dns_client()
        record_sets = client.record_sets.list_by_dns_zone(
            config['RESOURCE_GROUP'],
            config['DNS_ZONE']
        )

        records = []
        for rs in record_sets:
            rec = {
                'name': rs.name,
                'type': rs.type.split('/')[-1],
                'ttl': rs.ttl,
                'fqdn': rs.fqdn,
            }
            if rs.a_records:
                rec['values'] = [r.ipv4_address for r in rs.a_records]
            elif rs.aaaa_records:
                rec['values'] = [r.ipv6_address for r in rs.aaaa_records]
            elif rs.cname_record:
                rec['values'] = [rs.cname_record.cname]
            elif rs.mx_records:
                rec['values'] = [f"{r.preference} {r.exchange}" for r in rs.mx_records]
            elif rs.txt_records:
                rec['values'] = [' '.join(r.value) for r in rs.txt_records]
            elif rs.ns_records:
                rec['values'] = [r.nsdname for r in rs.ns_records]
            elif rs.ptr_records:
                rec['values'] = [r.ptrdname for r in rs.ptr_records]
            elif rs.srv_records:
                rec['values'] = [f"{r.priority} {r.weight} {r.port} {r.target}" for r in rs.srv_records]
            else:
                rec['values'] = []
            records.append(rec)

        return {"records": records, "zone": config['DNS_ZONE']}
    except Exception as e:
        return {"error": str(e)}


def _tool_create_record(name, type, values, ttl=3600):
    from app import get_dns_client, config, is_config_complete
    from azure.mgmt.dns.models import RecordSet, ARecord, AaaaRecord, CnameRecord, MxRecord, TxtRecord

    if not is_config_complete():
        return {"error": "Azure configuration is incomplete."}

    if not name or not type or not values:
        return {"error": "Missing required fields: name, type, values"}

    try:
        client = get_dns_client()
        record_set = RecordSet(ttl=ttl)

        if type == 'A':
            record_set.a_records = [ARecord(ipv4_address=v) for v in values]
        elif type == 'AAAA':
            record_set.aaaa_records = [AaaaRecord(ipv6_address=v) for v in values]
        elif type == 'CNAME':
            if len(values) > 1:
                return {"error": "CNAME records can only have one value"}
            cname_val = values[0] if values[0].endswith('.') else values[0] + '.'
            record_set.cname_record = CnameRecord(cname=cname_val)
        elif type == 'MX':
            mx_records = []
            for v in values:
                parts = v.split(' ', 1)
                if len(parts) == 2:
                    exchange = parts[1] if parts[1].endswith('.') else parts[1] + '.'
                    mx_records.append(MxRecord(preference=int(parts[0]), exchange=exchange))
            record_set.mx_records = mx_records
        elif type == 'TXT':
            record_set.txt_records = [TxtRecord(value=[v]) for v in values]
        else:
            return {"error": f"Unsupported record type: {type}"}

        client.record_sets.create_or_update(
            config['RESOURCE_GROUP'],
            config['DNS_ZONE'],
            name,
            type,
            record_set
        )
        return {"message": "Record created successfully", "name": name}
    except Exception as e:
        return {"error": str(e)}


def _tool_update_record(record_type, record_name, values, ttl=3600, new_name=None):
    from app import get_dns_client, config, is_config_complete
    from azure.mgmt.dns.models import RecordSet, ARecord, AaaaRecord, CnameRecord, MxRecord, TxtRecord

    if not is_config_complete():
        return {"error": "Azure configuration is incomplete."}

    if not values:
        return {"error": "Missing required field: values"}

    try:
        client = get_dns_client()
        target_name = new_name if new_name and new_name != record_name else record_name

        # If renaming, check target doesn't already exist
        if target_name != record_name:
            try:
                client.record_sets.get(
                    config['RESOURCE_GROUP'],
                    config['DNS_ZONE'],
                    target_name,
                    record_type
                )
                return {"error": f'A {record_type} record named "{target_name}" already exists'}
            except Exception:
                pass

        record_set = RecordSet(ttl=ttl)

        if record_type == 'A':
            record_set.a_records = [ARecord(ipv4_address=v) for v in values]
        elif record_type == 'AAAA':
            record_set.aaaa_records = [AaaaRecord(ipv6_address=v) for v in values]
        elif record_type == 'CNAME':
            if len(values) > 1:
                return {"error": "CNAME records can only have one value"}
            cname_val = values[0] if values[0].endswith('.') else values[0] + '.'
            record_set.cname_record = CnameRecord(cname=cname_val)
        elif record_type == 'MX':
            mx_records = []
            for v in values:
                parts = v.split(' ', 1)
                if len(parts) == 2:
                    exchange = parts[1] if parts[1].endswith('.') else parts[1] + '.'
                    mx_records.append(MxRecord(preference=int(parts[0]), exchange=exchange))
            record_set.mx_records = mx_records
        elif record_type == 'TXT':
            record_set.txt_records = [TxtRecord(value=[v]) for v in values]
        else:
            return {"error": f"Unsupported record type: {record_type}"}

        client.record_sets.create_or_update(
            config['RESOURCE_GROUP'],
            config['DNS_ZONE'],
            target_name,
            record_type,
            record_set
        )

        # If renaming, delete old record
        if target_name != record_name:
            client.record_sets.delete(
                config['RESOURCE_GROUP'],
                config['DNS_ZONE'],
                record_name,
                record_type
            )

        return {"message": "Record updated successfully", "name": target_name}
    except Exception as e:
        return {"error": str(e)}


def _tool_delete_record(record_type, record_name):
    from app import get_dns_client, config, is_config_complete

    if not is_config_complete():
        return {"error": "Azure configuration is incomplete."}

    try:
        client = get_dns_client()
        client.record_sets.delete(
            config['RESOURCE_GROUP'],
            config['DNS_ZONE'],
            record_name,
            record_type
        )
        return {"message": "Record deleted successfully", "name": record_name}
    except Exception as e:
        return {"error": str(e)}


def _tool_health_check():
    from app import config
    return {"status": "healthy", "zone": config.get('DNS_ZONE')}


TOOL_DISPATCH = {
    "list_records": lambda args: _tool_list_records(),
    "create_record": lambda args: _tool_create_record(
        name=args.get("name"),
        type=args.get("type"),
        values=args.get("values"),
        ttl=args.get("ttl", 3600),
    ),
    "update_record": lambda args: _tool_update_record(
        record_type=args.get("record_type"),
        record_name=args.get("record_name"),
        values=args.get("values"),
        ttl=args.get("ttl", 3600),
        new_name=args.get("new_name"),
    ),
    "delete_record": lambda args: _tool_delete_record(
        record_type=args.get("record_type"),
        record_name=args.get("record_name"),
    ),
    "health_check": lambda args: _tool_health_check(),
}

# ---------------------------------------------------------------------------
# MCP session management
# ---------------------------------------------------------------------------

SERVER_INFO = {
    "name": "azure-dns-manager",
    "version": "1.0.0",
}

SERVER_CAPABILITIES = {
    "tools": {"listChanged": False},
}


class McpSession:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.message_queue = queue.Queue()
        self.initialized = False


sessions = {}
_sessions_lock = threading.Lock()


# ---------------------------------------------------------------------------
# JSON-RPC message handling
# ---------------------------------------------------------------------------

def _jsonrpc_response(id, result):
    return {"jsonrpc": "2.0", "id": id, "result": result}


def _jsonrpc_error(id, code, message):
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


def handle_mcp_message(mcp_session, message):
    """Process an incoming JSON-RPC message and return a response (or None for notifications)."""
    method = message.get("method")
    msg_id = message.get("id")
    params = message.get("params", {})

    # --- Lifecycle ---
    if method == "initialize":
        mcp_session.initialized = True
        return _jsonrpc_response(msg_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": SERVER_CAPABILITIES,
            "serverInfo": SERVER_INFO,
        })

    if method == "notifications/initialized":
        # Client notification, no response needed
        return None

    # Guard: must be initialized for anything else
    if not mcp_session.initialized:
        return _jsonrpc_error(msg_id, -32600, "Session not initialized")

    # --- Tool methods ---
    if method == "tools/list":
        return _jsonrpc_response(msg_id, {"tools": MCP_TOOLS})

    if method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        handler = TOOL_DISPATCH.get(tool_name)
        if not handler:
            return _jsonrpc_response(msg_id, {
                "content": [{"type": "text", "text": json.dumps({"error": f"Unknown tool: {tool_name}"})}],
                "isError": True,
            })
        try:
            result = handler(tool_args)
            is_error = "error" in result and len(result) == 1
            return _jsonrpc_response(msg_id, {
                "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                "isError": is_error,
            })
        except Exception as exc:
            return _jsonrpc_response(msg_id, {
                "content": [{"type": "text", "text": json.dumps({"error": str(exc)})}],
                "isError": True,
            })

    # --- Ping ---
    if method == "ping":
        return _jsonrpc_response(msg_id, {})

    # Unknown method
    return _jsonrpc_error(msg_id, -32601, f"Method not found: {method}")


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def _check_mcp_auth():
    """Validate Bearer token. Returns None on success, or a (response, status) tuple on failure."""
    from app import API_TOKEN
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer ') or not API_TOKEN:
        return jsonify({'error': 'Authentication required'}), 401
    token = auth_header[7:]
    if not hmac.compare_digest(token, API_TOKEN):
        return jsonify({'error': 'Invalid token'}), 401
    return None


# ---------------------------------------------------------------------------
# /mcpdocs page
# ---------------------------------------------------------------------------

def _build_mcpdocs_html():
    tools_json = json.dumps(MCP_TOOLS, indent=2)
    tool_cards = ""
    for tool in MCP_TOOLS:
        props = tool["inputSchema"].get("properties", {})
        required = tool["inputSchema"].get("required", [])
        if props:
            param_rows = ""
            for pname, pschema in props.items():
                req_badge = '<span class="req">required</span>' if pname in required else '<span class="opt">optional</span>'
                ptype = pschema.get("type", "any")
                if "enum" in pschema:
                    ptype += " (" + ", ".join(pschema["enum"]) + ")"
                desc = pschema.get("description", "")
                default = ""
                if "default" in pschema:
                    default = f' <span class="default">default: {pschema["default"]}</span>'
                param_rows += f"""
                <tr>
                    <td><code>{pname}</code> {req_badge}</td>
                    <td><code>{ptype}</code>{default}</td>
                    <td>{desc}</td>
                </tr>"""
            params_html = f"""
            <table class="params">
                <thead><tr><th>Parameter</th><th>Type</th><th>Description</th></tr></thead>
                <tbody>{param_rows}</tbody>
            </table>"""
        else:
            params_html = '<p class="no-params">No parameters required</p>'

        tool_cards += f"""
        <div class="tool-card">
            <h2><code>{tool["name"]}</code></h2>
            <p class="desc">{tool["description"]}</p>
            {params_html}
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Azure DNS Manager &mdash; MCP Tools</title>
<style>
    *,*::before,*::after{{box-sizing:border-box}}
    body{{
        font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Oxygen,Ubuntu,sans-serif;
        background:#0d1117;color:#c9d1d9;margin:0;padding:2rem;line-height:1.6;
    }}
    h1{{color:#58a6ff;margin-bottom:.25rem}}
    .subtitle{{color:#8b949e;margin-bottom:2rem;font-size:.95rem}}
    .tool-card{{
        background:#161b22;border:1px solid #30363d;border-radius:8px;
        padding:1.5rem;margin-bottom:1.25rem;
    }}
    .tool-card h2{{margin:0 0 .5rem;color:#58a6ff;font-size:1.15rem}}
    .desc{{color:#8b949e;margin:0 0 1rem}}
    table.params{{
        width:100%;border-collapse:collapse;font-size:.9rem;
    }}
    table.params th{{
        text-align:left;padding:.5rem .75rem;border-bottom:1px solid #30363d;
        color:#8b949e;font-weight:600;
    }}
    table.params td{{
        padding:.5rem .75rem;border-bottom:1px solid #21262d;
        vertical-align:top;
    }}
    code{{
        background:#1c2128;padding:.15em .35em;border-radius:4px;font-size:.9em;
        color:#e6edf3;
    }}
    .req{{
        background:#1f6feb33;color:#58a6ff;font-size:.75rem;padding:.1em .45em;
        border-radius:3px;margin-left:.4em;
    }}
    .opt{{
        background:#30363d;color:#8b949e;font-size:.75rem;padding:.1em .45em;
        border-radius:3px;margin-left:.4em;
    }}
    .default{{color:#8b949e;font-size:.85em}}
    .no-params{{color:#484f58;font-style:italic}}
    .connection-info{{
        background:#161b22;border:1px solid #30363d;border-radius:8px;
        padding:1.25rem 1.5rem;margin-bottom:2rem;
    }}
    .connection-info h3{{color:#58a6ff;margin:0 0 .75rem}}
    .connection-info pre{{
        background:#0d1117;padding:.75rem 1rem;border-radius:6px;
        overflow-x:auto;font-size:.85rem;color:#e6edf3;
    }}
    .connection-info p{{color:#8b949e;margin:.5rem 0 0;font-size:.9rem}}
</style>
</head>
<body>
<h1>Azure DNS Manager &mdash; MCP Server</h1>
<p class="subtitle">Model Context Protocol tools for managing Azure DNS records</p>

<div class="connection-info">
    <h3>Connection</h3>
    <pre>SSE endpoint:  /mcp/sse
Messages:      /mcp/messages?session_id=&lt;id&gt;</pre>
    <p>Authenticate with <code>Authorization: Bearer &lt;API_TOKEN&gt;</code></p>
</div>

{tool_cards}

<div class="connection-info">
    <h3>Raw Tool Schema</h3>
    <pre>{tools_json}</pre>
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

def register_mcp_routes(app):
    """Register /mcp/sse, /mcp/messages, and /mcpdocs routes on the Flask app."""

    @app.route('/mcp/sse')
    def mcp_sse():
        from app import is_mcp_enabled
        if not is_mcp_enabled():
            return jsonify({'error': 'MCP is not enabled. Enable it in Settings or set MCP_ENABLED=true'}), 404

        auth_err = _check_mcp_auth()
        if auth_err:
            return auth_err

        mcp_session = McpSession()
        with _sessions_lock:
            sessions[mcp_session.id] = mcp_session

        def generate():
            try:
                # First event: tell the client where to POST messages
                yield f"event: endpoint\ndata: /mcp/messages?session_id={mcp_session.id}\n\n"
                while True:
                    try:
                        msg = mcp_session.message_queue.get(timeout=30)
                        if msg is None:
                            break
                        yield f"event: message\ndata: {json.dumps(msg)}\n\n"
                    except queue.Empty:
                        yield ": keepalive\n\n"
            finally:
                with _sessions_lock:
                    sessions.pop(mcp_session.id, None)

        resp = Response(generate(), mimetype='text/event-stream')
        resp.headers['Cache-Control'] = 'no-cache'
        resp.headers['X-Accel-Buffering'] = 'no'
        resp.headers['Connection'] = 'keep-alive'
        return resp

    @app.route('/mcp/messages', methods=['POST'])
    def mcp_messages():
        from app import is_mcp_enabled
        if not is_mcp_enabled():
            return jsonify({'error': 'MCP is not enabled. Enable it in Settings or set MCP_ENABLED=true'}), 404

        auth_err = _check_mcp_auth()
        if auth_err:
            return auth_err

        session_id = request.args.get('session_id')
        with _sessions_lock:
            mcp_session = sessions.get(session_id)
        if not mcp_session:
            return jsonify({'error': 'Invalid or expired session'}), 404

        message = request.get_json()
        if not message:
            return jsonify({'error': 'Invalid JSON body'}), 400

        response = handle_mcp_message(mcp_session, message)
        if response is not None:
            mcp_session.message_queue.put(response)

        return '', 202

    @app.route('/mcpdocs')
    def mcp_docs():
        return Response(_build_mcpdocs_html(), mimetype='text/html')
