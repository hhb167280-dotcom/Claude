import os
import hmac
import uvicorn

from openai import OpenAI
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


# API configuration
client = OpenAI(
    base_url=os.environ["UPSTREAM_BASE_URL"],
    api_key=os.environ["UPSTREAM_API_KEY"]
)

MODEL = os.getenv("MODEL", "claude-opus-4-6")
ACCESS_TOKEN = os.environ["MCP_ACCESS_TOKEN"]

# MCP server
mcp = FastMCP("Claude Opus Bridge")


@mcp.tool()
def ask_opus(prompt: str) -> str:
    """Send a prompt to the configured AI model."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content or "No response"


# Allow Railway's public hostname
security = TransportSecuritySettings(
    allowed_hosts=[
        "claude-production-352548e2.up.railway.app",
        "claude-production-352548e2.up.railway.app:*"
    ]
)

app = mcp.streamable_http_app(
    transport_security=security
)


# Protect MCP endpoint with your secret token
class AuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request, call_next):

        if request.url.path == "/mcp":

            auth_header = request.headers.get(
                "authorization", ""
            )

            expected = f"Bearer {ACCESS_TOKEN}"

            if not hmac.compare_digest(
                auth_header, expected
            ):
                return JSONResponse(
                    {"error": "Unauthorized"},
                    status_code=401
                )

        return await call_next(request)


app.add_middleware(AuthMiddleware)


if __name__ == "__main__":

    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
    
