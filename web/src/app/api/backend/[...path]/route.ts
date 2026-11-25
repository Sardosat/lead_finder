import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000";

async function proxyRequest(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const subPath = path.join("/");
  const search = req.nextUrl.search || "";
  const targetUrl = `${BACKEND_URL.replace(/\/$/, "")}/${subPath}${search}`;

  const forwardHeaders = new Headers();
  const cookie = req.headers.get("cookie");
  if (cookie) forwardHeaders.set("cookie", cookie);
  const auth = req.headers.get("authorization");
  if (auth) forwardHeaders.set("authorization", auth);
  const apiKey = req.headers.get("x-api-key");
  if (apiKey) forwardHeaders.set("x-api-key", apiKey);
  const contentType = req.headers.get("content-type");
  if (contentType) forwardHeaders.set("content-type", contentType);

  let body: ArrayBuffer | undefined;
  if (req.method !== "GET" && req.method !== "HEAD") {
    const ab = await req.arrayBuffer();
    if (ab.byteLength > 0) body = ab;
  }

  let upstream: Response;
  try {
    upstream = await fetch(targetUrl, {
      method: req.method,
      headers: forwardHeaders,
      body,
      redirect: "manual",
    });
  } catch (err) {
    return NextResponse.json(
      { detail: `Backend API non raggiungibile su ${BACKEND_URL}`, error: String(err) },
      { status: 502 }
    );
  }

  const outHeaders = new Headers();
  const upType = upstream.headers.get("content-type");
  if (upType) outHeaders.set("content-type", upType);
  const upDisp = upstream.headers.get("content-disposition");
  if (upDisp) outHeaders.set("content-disposition", upDisp);

  const getSetCookie = (upstream.headers as Headers & { getSetCookie?: () => string[] }).getSetCookie;
  if (typeof getSetCookie === "function") {
    for (const sc of getSetCookie.call(upstream.headers)) {
      outHeaders.append("set-cookie", sc);
    }
  } else {
    const sc = upstream.headers.get("set-cookie");
    if (sc) outHeaders.set("set-cookie", sc);
  }

  const buf = await upstream.arrayBuffer();
  return new NextResponse(buf, {
    status: upstream.status,
    headers: outHeaders,
  });
}

export { proxyRequest as GET, proxyRequest as POST, proxyRequest as PUT, proxyRequest as PATCH, proxyRequest as DELETE };
